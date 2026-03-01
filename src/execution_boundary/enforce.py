"""
enforce_boundary() — Unified Execution Runtime Boundary v0.1

단일 진입점. boundary_id 생성 → decision_hash → OTel span →
policy evaluation → outcome → exception(DENY/HOLD) or return(ALLOW) →
legal proof 발급(ALLOW·DENY 모두).

OTel 의존성은 선택적(opentelemetry-api가 없으면 no-op).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Optional

from .models import (
    BoundaryRecord,
    Decision,
    EnforcementOutcome,
    ExecutionDeniedError,
    ExecutionExpiredError,
    ExecutionHeldError,
    ExecutionIntent,
    new_boundary_id,
)
from .policy_guard import PolicyViolation, check_policy

# ── OTel optional import ──────────────────────────────────────────────────────
try:
    from opentelemetry import trace as _otel_trace
    from opentelemetry.trace import StatusCode as _StatusCode
    _HAS_OTEL = True
except ImportError:
    _HAS_OTEL = False


# ── Policy hash helper ────────────────────────────────────────────────────────

def _hash_policy(policy: Any) -> str:
    """Stable SHA-256 over a policy object (dict, str, or None)."""
    if policy is None:
        raw = "null"
    elif isinstance(policy, str):
        raw = policy
    else:
        raw = json.dumps(policy, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ── OTel span helper ──────────────────────────────────────────────────────────

def _start_boundary_span(name: str = "execution.boundary"):
    """Start OTel span or return no-op context manager."""
    if not _HAS_OTEL:
        return _NoOpSpanCtx()
    tracer = _otel_trace.get_tracer("execution-boundary-core")
    return tracer.start_as_current_span(name)


class _NoOpSpanCtx:
    """Minimal no-op context manager when OTel is absent."""
    def __enter__(self):
        return self
    def __exit__(self, *_):
        pass
    def set_attribute(self, *_):
        pass
    def set_status(self, *_):
        pass
    def record_exception(self, *_):
        pass
    def add_event(self, *_):
        pass


def _get_current_span():
    if not _HAS_OTEL:
        return _NoOpSpanCtx()
    return _otel_trace.get_current_span()


# ── enforce_boundary() ────────────────────────────────────────────────────────

def enforce_boundary(
    intent: ExecutionIntent,
    *,
    engine,                         # ExecutionBoundaryEngine instance
    policy: Any = None,             # policy snapshot for policy_hash
    hold_deadline_seconds: int = 300,
    # Severity context — injected by SeverityGate for OTel attrs
    _severity_state: Optional[str] = None,
    _severity_score: Optional[float] = None,
    _severity_threshold: Optional[int] = None,
) -> BoundaryRecord:
    """
    Unified execution boundary enforcement.

    Flow
    ----
    0. PolicyGuard  — identity check (unknown agent/action → DENY immediately)
    1. boundary_id  — new unique ID (≠ trace_id)
    2. policy_hash  — SHA-256 over policy snapshot
    3. OTel span    — "execution.boundary" (or no-op)
    4. evaluate()   — risk/policy decision
    5. decision_hash — canonical SHA-256
    6. OTel attrs   — exec.boundary.id, exec.decision.outcome, severity.*
    7. outcome      — ALLOW / DENY / HOLD
    8. exception    — ExecutionDeniedError or ExecutionHeldError (non-ALLOW)
    9. proof        — issue_proof() for ALLOW *and* DENY/HOLD (negative proof)
    10. return      — BoundaryRecord (ALLOW path only; exceptions for rest)

    Parameters
    ----------
    intent:               ExecutionIntent from caller
    engine:               ExecutionBoundaryEngine (or compatible)
    policy:               Policy snapshot (for deterministic policy_hash)
    hold_deadline_seconds: Seconds from now until HOLD expires
    _severity_state:      ACTIVE | OBSERVE | COOLDOWN (from SeverityGate)
    _severity_score:      float [0.0–1.0] (from SeverityGate)
    _severity_threshold:  effective halt_threshold (from SeverityGate)

    Returns
    -------
    BoundaryRecord  (only on ALLOW — otherwise raises)

    Raises
    ------
    ExecutionDeniedError  — outcome DENY (including policy violations)
    ExecutionHeldError    — outcome HOLD
    ExecutionExpiredError — HOLD past deadline_ts
    """
    # ── 0. PolicyGuard — identity check ───────────────────────────────────────
    # Fail-closed: unknown agent or unknown action → immediate DENY.
    # This runs before severity/risk scoring — policy identity is not
    # state-dependent. An unknown agent is denied at ACTIVE just as at COOLDOWN.
    try:
        check_policy(intent.actor, intent.action, policy)
    except PolicyViolation as pv:
        # Issue a minimal DENY without going through the full engine path.
        # We still need a signed negative proof — use engine.evaluate() with
        # a synthetic risk=100 so the engine produces HALT, then override reason.
        boundary_id = new_boundary_id()
        policy_hash = _hash_policy(policy)
        ts_now      = datetime.now(timezone.utc)
        ts_iso      = ts_now.isoformat()

        # Synthesize a DENY decision for the proof trail
        deny_decision = Decision(
            decision   = "HALT",
            risk_score = 100,
            reason     = f"policy_violation:{pv.reason_code}",
            timestamp  = ts_now,
        )
        deny_decision.boundary_id            = boundary_id
        deny_decision.decision_id            = boundary_id
        deny_decision.policy_hash            = policy_hash
        deny_decision.decision_hash          = deny_decision._compute_hash()
        deny_decision.decision_instance_hash = deny_decision._compute_instance_hash()

        proof = engine.issue_proof(deny_decision)

        with _start_boundary_span("execution.boundary") as span:
            _write_span_attrs(
                span, deny_decision, EnforcementOutcome.DENY, intent, None,
                severity_state=_severity_state,
                severity_score=_severity_score,
                severity_threshold=_severity_threshold,
            )
            span.add_event(
                "exec.negative_proof",
                {
                    "exec.boundary.id":        boundary_id,
                    "exec.block.reason":       deny_decision.reason,
                    "exec.negative_proof":     "true",
                    "exec.policy.violation":   pv.reason_code,
                },
            )
            if _HAS_OTEL:
                span.set_status(_StatusCode.ERROR, f"DENY: {deny_decision.reason}")

        raise ExecutionDeniedError(
            boundary_id = boundary_id,
            reason      = deny_decision.reason,
            risk_score  = 100,
        )

    boundary_id = new_boundary_id()
    policy_hash = _hash_policy(policy)
    ts_now      = datetime.now(timezone.utc)
    ts_iso      = ts_now.isoformat()

    with _start_boundary_span("execution.boundary") as span:
        # ── 4. evaluate ───────────────────────────────────────────────────────
        decision: Decision = engine.evaluate(intent)

        # Inject boundary_id and policy_hash into Decision
        # decision_hash = fingerprint (recompute now policy_hash is set)
        # decision_instance_hash = per-boundary tamper-evident ID (recompute after boundary_id set)
        decision.boundary_id            = boundary_id
        decision.decision_id            = boundary_id
        decision.policy_hash            = policy_hash
        decision.decision_hash          = decision._compute_hash()
        decision.decision_instance_hash = decision._compute_instance_hash()

        # ── 5+6. Map to EnforcementOutcome + OTel attrs ───────────────────────
        outcome = _map_outcome(decision.decision)

        deadline_ts: Optional[str] = None
        if outcome == EnforcementOutcome.HOLD:
            from datetime import timedelta
            deadline_ts = (
                ts_now + timedelta(seconds=hold_deadline_seconds)
            ).isoformat()
            decision.deadline_ts = deadline_ts

            # Check if already expired (for replay/re-evaluation scenarios)
            # (fresh evaluations are never expired; this is a guard for callers
            #  that re-invoke enforce_boundary with an existing deadline_ts passed in)

        _write_span_attrs(
            span, decision, outcome, intent, deadline_ts,
            severity_state=_severity_state,
            severity_score=_severity_score,
            severity_threshold=_severity_threshold,
        )

        # ── 9. issue_proof (ALLOW and negative proof) ─────────────────────────
        proof = engine.issue_proof(decision)

        record = BoundaryRecord(
            boundary_id            = boundary_id,
            run_id                 = intent.run_id,
            actor                  = intent.actor,
            action                 = intent.action,
            outcome                = outcome,
            risk_score             = decision.risk_score,
            reason                 = decision.reason,
            policy_hash            = policy_hash,
            decision_hash          = decision.decision_hash,
            decision_instance_hash = decision.decision_instance_hash,
            ts                     = ts_iso,
            deadline_ts            = deadline_ts,
            negative_proof         = outcome != EnforcementOutcome.ALLOW,
            proof_signature        = proof.signature,
            ledger_index           = proof.ledger_index,
        )

        # ── 10. DENY/HOLD → exception (execution NEVER proceeds) ──────────────
        if outcome == EnforcementOutcome.DENY:
            span.add_event(
                "exec.negative_proof",
                {
                    "exec.boundary.id":    boundary_id,
                    "exec.block.reason":   decision.reason,
                    "exec.negative_proof": "true",
                },
            )
            if _HAS_OTEL:
                span.set_status(
                    _StatusCode.ERROR,
                    f"DENY: {decision.reason}",
                )
            raise ExecutionDeniedError(
                boundary_id = boundary_id,
                reason      = decision.reason,
                risk_score  = decision.risk_score,
            )

        if outcome == EnforcementOutcome.HOLD:
            span.add_event(
                "exec.negative_proof",
                {
                    "exec.boundary.id":     boundary_id,
                    "exec.block.reason":    "awaiting_approval",
                    "exec.approval.deadline": deadline_ts or "",
                    "exec.negative_proof":  "true",
                },
            )
            raise ExecutionHeldError(
                boundary_id     = boundary_id,
                reason          = decision.reason,
                deadline_ts     = deadline_ts,
                proof_signature = proof.signature,
                ledger_index    = proof.ledger_index,
            )

        # ALLOW — return record; caller may proceed
        return record


# ── HOLD timeout checker ──────────────────────────────────────────────────────

def check_hold_expired(
    boundary_id: str,
    deadline_ts: str,
    *,
    engine,
    intent: ExecutionIntent,
    policy: Any = None,
) -> BoundaryRecord:
    """
    Call this when re-evaluating a HOLD boundary after potential timeout.

    If deadline_ts has passed, records EXPIRED negative proof and raises
    ExecutionExpiredError.  Otherwise raises ExecutionHeldError (still pending).
    """
    now = datetime.now(timezone.utc)
    deadline = datetime.fromisoformat(deadline_ts)
    if deadline.tzinfo is None:
        from datetime import timezone as _tz
        deadline = deadline.replace(tzinfo=_tz.utc)

    policy_hash = _hash_policy(policy)

    if now >= deadline:
        # Issue negative proof with EXPIRED outcome
        decision = engine.evaluate(intent)
        decision.boundary_id   = boundary_id
        decision.decision_id   = boundary_id
        decision.policy_hash   = policy_hash
        decision.negative_proof = True
        decision.deadline_ts   = deadline_ts
        decision.decision_hash = decision._compute_hash()

        proof = engine.issue_proof(decision)

        with _start_boundary_span("execution.boundary.expired") as span:
            span.add_event(
                "exec.negative_proof",
                {
                    "exec.boundary.id":    boundary_id,
                    "exec.block.reason":   "approval_timeout",
                    "exec.negative_proof": "true",
                    "exec.expired_at":     now.isoformat(),
                },
            )
            if _HAS_OTEL:
                span.set_status(_StatusCode.ERROR, "approval_timeout")

        raise ExecutionExpiredError(
            boundary_id = boundary_id,
            deadline_ts = deadline_ts,
        )

    raise ExecutionHeldError(
        boundary_id = boundary_id,
        reason      = "awaiting_approval",
        deadline_ts = deadline_ts,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _map_outcome(decision_type: str) -> EnforcementOutcome:
    mapping = {
        "ALLOW": EnforcementOutcome.ALLOW,
        "HALT":  EnforcementOutcome.DENY,
        "HOLD":  EnforcementOutcome.HOLD,
    }
    return mapping.get(decision_type, EnforcementOutcome.DENY)


def _write_span_attrs(
    span,
    decision: "Decision",
    outcome: EnforcementOutcome,
    intent: ExecutionIntent,
    deadline_ts: Optional[str],
    *,
    severity_state: Optional[str] = None,
    severity_score: Optional[float] = None,
    severity_threshold: Optional[int] = None,
) -> None:
    """Write exec.* and severity.* attributes to the active OTel span (or no-op)."""
    span.set_attribute("exec.boundary.id",              decision.boundary_id)
    span.set_attribute("exec.decision.id",              decision.decision_id)
    span.set_attribute("exec.decision.hash",            decision.decision_hash)            # fingerprint
    span.set_attribute("exec.decision.instance_hash",   decision.decision_instance_hash)  # per-boundary
    span.set_attribute("exec.policy.hash",              decision.policy_hash)
    span.set_attribute("exec.decision.outcome",         outcome.value)
    span.set_attribute("exec.decision.risk_score",      decision.risk_score)
    span.set_attribute("exec.actor.id",                 intent.actor)
    span.set_attribute("exec.action",                   intent.action)
    span.set_attribute("exec.negative_proof",           outcome != EnforcementOutcome.ALLOW)
    if intent.run_id:
        span.set_attribute("exec.run.id", intent.run_id)
    if deadline_ts:
        span.set_attribute("exec.approval.deadline", deadline_ts)
    # ── Severity context (set by SeverityGate) ────────────────────────────────
    if severity_state is not None:
        span.set_attribute("execution.state",     severity_state)
    if severity_score is not None:
        span.set_attribute("severity.score",      round(severity_score, 4))
    if severity_threshold is not None:
        span.set_attribute("severity.threshold",  severity_threshold)
