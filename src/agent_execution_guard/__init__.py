"""
agent-execution-guard
=====================

A lightweight execution guard for AI agents.
Decide ALLOW / HOLD / DENY before your agent performs real actions.

    from agent_execution_guard import ExecutionGuard, Intent

Public API
----------
ExecutionGuard      — main guard class (evaluate, verify)
Intent              — execution request (actor, action, payload, timestamp)
SystemSeverity      — severity signal [0.0–1.0] from any source
GuardResult         — result of evaluate() on ALLOW path
GuardDeniedError    — raised on DENY
GuardHeldError      — raised on HOLD
GuardExpiredError   — raised on HOLD past deadline
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from execution_boundary import (
    ExecutionBoundaryEngine,
    ExecutionIntent,
    BoundaryRecord,
    ExecutionDeniedError,
    ExecutionHeldError,
    ExecutionExpiredError,
    SeverityGate,
    SystemSeverity,
    enforce_boundary,
)
from execution_boundary.policy_guard import PolicyViolation


# ── Public re-exports (renamed for clarity) ───────────────────────────────────

Intent         = ExecutionIntent
GuardDeniedError  = ExecutionDeniedError
GuardHeldError    = ExecutionHeldError
GuardExpiredError = ExecutionExpiredError
GuardResult       = BoundaryRecord


# ── ExecutionGuard — main entry point ─────────────────────────────────────────

class ExecutionGuard:
    """
    Lightweight execution guard for AI agents.

    Usage::

        guard = ExecutionGuard()

        intent = Intent(
            actor="agent.finance",
            action="wire_transfer",
            payload="wire_transfer amount=50000",
            timestamp=datetime.now(timezone.utc),
        )

        try:
            result = guard.evaluate(intent)
            # ALLOW — proceed
        except GuardDeniedError as e:
            # DENY — blocked, signed proof issued
            print(e.reason)
        except GuardHeldError as e:
            # HOLD — awaiting human approval
            print(e.deadline_ts)
    """

    def __init__(
        self,
        *,
        halt_threshold: int = 80,
        key_file: Optional[str] = None,
        ledger_file: Optional[str] = None,
    ) -> None:
        self._engine = ExecutionBoundaryEngine(
            halt_threshold=halt_threshold,
            key_file=key_file,
            ledger_file=ledger_file,
        )
        self._severity_gate = SeverityGate()

    def evaluate(
        self,
        intent: Intent,
        *,
        severity: Optional[SystemSeverity] = None,
        policy: Any = None,
        hold_deadline_seconds: int = 300,
    ) -> GuardResult:
        """
        Evaluate an execution intent.

        Args:
            intent:               The execution request.
            severity:             Current system severity [0.0–1.0]. None = ACTIVE.
            policy:               Policy dict (from policy.yaml). None = no identity check.
            hold_deadline_seconds: HOLD window in seconds (default 5 min).

        Returns:
            GuardResult (BoundaryRecord) — only on ALLOW.

        Raises:
            GuardDeniedError  — DENY (risk, policy violation, or unknown agent/action)
            GuardHeldError    — HOLD (awaiting human approval)
            GuardExpiredError — HOLD deadline passed
        """
        if severity is not None:
            # Severity-adaptive path: state machine adjusts threshold
            result = self._severity_gate.evaluate(
                intent,
                engine=self._engine,
                system_severity=severity,
                policy=policy,
                hold_deadline_seconds=hold_deadline_seconds,
            )
            # Re-raise exceptions from the gate result
            if result.error is not None:
                raise result.error
            return result.record
        else:
            # Direct path: fixed threshold
            return enforce_boundary(
                intent,
                engine=self._engine,
                policy=policy,
                hold_deadline_seconds=hold_deadline_seconds,
            )

    def verify(self, proof) -> Any:
        """Verify a past decision proof against the ledger."""
        return self._engine.verify(proof)


__all__ = [
    "ExecutionGuard",
    "Intent",
    "SystemSeverity",
    "GuardResult",
    "GuardDeniedError",
    "GuardHeldError",
    "GuardExpiredError",
]
