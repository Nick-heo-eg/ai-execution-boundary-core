#!/usr/bin/env python3
"""
Demo runner: LLM suggestion -> YAML policy check -> DENY/HOLD -> OTel + AJT outputs.

Run:
  PYTHONPATH=src python demo/run_demo.py
  PYTHONPATH=src python demo/run_demo.py --with-token   # 2nd cut: HOLD -> ALLOW

Writes:
  demo/out/ajt.jsonl
  demo/out/otel_spans.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# ── enforce_boundary core hook ────────────────────────────────────────────────
# When this repo's core is installed, use it for cryptographic proof + ledger.
# Falls back gracefully if not importable (pure-policy-only mode).
try:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from execution_boundary import (
        ExecutionBoundaryEngine,
        ExecutionIntent,
        ExecutionDeniedError,
        ExecutionHeldError,
        enforce_boundary,
        EnforcementOutcome,
    )
    _HAS_CORE = True
except ImportError:
    _HAS_CORE = False

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

# ── Paths ─────────────────────────────────────────────────────────────────────

DEMO    = Path(__file__).resolve().parent
ROOT    = DEMO.parent
OUT     = DEMO / "out"
OUT.mkdir(parents=True, exist_ok=True)

AJT_PATH  = OUT / "ajt.jsonl"
OTEL_PATH = OUT / "otel_spans.jsonl"
KEY_FILE    = str(OUT / "demo_key.pem")
LEDGER_FILE = str(OUT / "demo_ledger.ndjson")


# ── Minimal YAML loader fallback ──────────────────────────────────────────────

def _load_yaml(path: Path) -> Dict[str, Any]:
    if _HAS_YAML:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    # minimal fallback: parse only simple key:value lines (enough for demo)
    raise RuntimeError("PyYAML not installed. Run: pip install pyyaml")


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_policy(policy: Dict[str, Any]) -> str:
    raw = json.dumps(policy, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


# ── Policy evaluation (deterministic rule engine) ─────────────────────────────

@dataclass
class GateDecision:
    decision:                str                 # ALLOW / HOLD / DENY
    deny_code:               Optional[str] = None
    reason:                  Optional[str] = None
    policy_id:               Optional[str] = None
    policy_hash:             Optional[str] = None
    authority_token_present: bool          = False
    authority_token_id:      Optional[str] = None
    boundary_id:             Optional[str] = None
    proof_signature:         Optional[str] = None
    ledger_index:            Optional[int] = None


def _find_agent(policy: Dict, agent_id: str) -> Optional[Dict]:
    for a in policy.get("identity", {}).get("agents", []):
        if a.get("agent_id") == agent_id:
            return a
    return None


def _find_action_rule(agent: Dict, action: str) -> Optional[Dict]:
    for r in agent.get("allowed_actions", []):
        if r.get("action") == action:
            return r
    return None


def evaluate_policy(
    policy: Dict[str, Any],
    llm: Dict[str, Any],
    token: Optional[Dict[str, Any]] = None,
) -> GateDecision:
    """
    Deterministic policy evaluation.

    TODO: replace body with `from execution_gate import evaluate_request`
          when plugging into a separate execution-gate repo.
    """
    fail_closed = policy.get("defaults", {}).get("mode", "fail_closed") == "fail_closed"
    policy_id   = policy.get("policy_id", "unknown")
    policy_hash = _hash_policy(policy)

    agent_id = llm.get("agent_id")
    action   = llm.get("suggested_action")
    params   = llm.get("params", {})

    agent = _find_agent(policy, agent_id)
    if not agent:
        return GateDecision(
            decision="DENY" if fail_closed else "HOLD",
            deny_code="UNKNOWN_AGENT",
            reason=f"agent_id '{agent_id}' not registered in policy",
            policy_id=policy_id, policy_hash=policy_hash,
        )

    rule = _find_action_rule(agent, action)
    if not rule:
        return GateDecision(
            decision="DENY" if fail_closed else "HOLD",
            deny_code="ACTION_NOT_ALLOWED",
            reason=f"action '{action}' not in allowed_actions for agent",
            policy_id=policy_id, policy_hash=policy_hash,
        )

    constraints = rule.get("constraints", {})
    amount      = params.get("amount_usd")
    beneficiary = params.get("beneficiary")

    max_amount = constraints.get("max_amount_usd")
    if isinstance(max_amount, (int, float)) and isinstance(amount, (int, float)):
        if amount > max_amount:
            return GateDecision(
                decision="DENY",
                deny_code="AMOUNT_THRESHOLD_EXCEEDED",
                reason=f"amount_usd {amount} > max_amount_usd {max_amount}",
                policy_id=policy_id, policy_hash=policy_hash,
            )

    allowlist = constraints.get("allowed_beneficiaries", [])
    if allowlist and beneficiary not in allowlist:
        return GateDecision(
            decision="DENY",
            deny_code="BENEFICIARY_NOT_ALLOWED",
            reason=f"beneficiary '{beneficiary}' not in allowlist",
            policy_id=policy_id, policy_hash=policy_hash,
        )

    auth           = rule.get("authority", {})
    require_human  = bool(auth.get("require_human_token", False))
    irreversible   = bool(rule.get("irreversible", False))

    if irreversible and require_human:
        if not token:
            return GateDecision(
                decision="HOLD",
                deny_code="IRREVERSIBLE_REQUIRES_HUMAN_TOKEN",
                reason="irreversible action requires human authority token — execution suspended",
                policy_id=policy_id, policy_hash=policy_hash,
                authority_token_present=False,
            )

        if token.get("token_type") != auth.get("token_type"):
            return GateDecision(decision="DENY", deny_code="INVALID_TOKEN_TYPE",
                reason="token_type mismatch", policy_id=policy_id, policy_hash=policy_hash,
                authority_token_present=True, authority_token_id=token.get("token_id"))

        required_scopes = set(auth.get("token_scopes", []))
        token_scopes    = set(token.get("scopes", []))
        if required_scopes and not required_scopes.issubset(token_scopes):
            return GateDecision(decision="DENY", deny_code="INSUFFICIENT_TOKEN_SCOPE",
                reason="token scopes insufficient", policy_id=policy_id, policy_hash=policy_hash,
                authority_token_present=True, authority_token_id=token.get("token_id"))

        must_match = auth.get("token_must_match", {})
        if must_match.get("owner") and token.get("owner") != agent.get("owner"):
            return GateDecision(decision="DENY", deny_code="TOKEN_OWNER_MISMATCH",
                reason="token owner != agent owner", policy_id=policy_id, policy_hash=policy_hash,
                authority_token_present=True, authority_token_id=token.get("token_id"))

        if must_match.get("agent_id") and token.get("bound_agent_id") != agent_id:
            return GateDecision(decision="DENY", deny_code="TOKEN_AGENT_BINDING_MISMATCH",
                reason="token not bound to this agent", policy_id=policy_id, policy_hash=policy_hash,
                authority_token_present=True, authority_token_id=token.get("token_id"))

    return GateDecision(
        decision="ALLOW",
        policy_id=policy_id, policy_hash=policy_hash,
        authority_token_present=bool(token),
        authority_token_id=(token.get("token_id") if token else None),
    )


# ── Core hook: cryptographic proof via enforce_boundary() ─────────────────────

def _attach_core_proof(gate: GateDecision, llm: Dict, policy: Dict) -> None:
    """
    If ai-execution-boundary-core is available, issue ED25519 proof + ledger entry.
    Gate decision drives halt_threshold so core mirrors policy outcome exactly:
      ALLOW → threshold=100 (never halts on low-risk payload)
      HOLD  → engine.evaluate() patched to return HOLD
      DENY  → threshold=0  (always halts)
    Attaches boundary_id, proof_signature, ledger_index to gate decision.
    """
    if not _HAS_CORE:
        return

    from execution_boundary.models import Decision as _Decision

    engine = ExecutionBoundaryEngine(
        halt_threshold = 100,   # policy engine drives decision; core just signs
        key_file       = KEY_FILE,
        ledger_file    = LEDGER_FILE,
    )

    # Patch evaluate() to return the gate's decision directly
    _gate_decision = gate.decision  # capture

    def _patched_evaluate(intent):
        d = _Decision(
            decision   = "ALLOW" if _gate_decision == "ALLOW" else "HALT",
            risk_score = 0   if _gate_decision == "ALLOW" else 90,
            reason     = gate.reason or gate.deny_code or _gate_decision,
            timestamp  = intent.timestamp,
        )
        if _gate_decision == "HOLD":
            d.decision = "HOLD"
        return d

    engine.evaluate = _patched_evaluate

    intent = ExecutionIntent(
        actor     = llm.get("agent_id", "unknown"),
        action    = llm.get("suggested_action", "unknown"),
        payload   = json.dumps(llm.get("params", {}), ensure_ascii=False),
        timestamp = datetime.now(timezone.utc),
        run_id    = llm.get("run_id"),
    )

    try:
        rec = enforce_boundary(intent, engine=engine, policy=policy)
        gate.boundary_id     = rec.boundary_id
        gate.proof_signature = rec.proof_signature
        gate.ledger_index    = rec.ledger_index
    except ExecutionHeldError as exc:
        gate.boundary_id     = exc.boundary_id
        gate.proof_signature = exc.proof_signature   # negative proof included
        gate.ledger_index    = exc.ledger_index
    except ExecutionDeniedError as exc:
        gate.boundary_id     = exc.boundary_id
        gate.proof_signature = None
        gate.ledger_index    = None


# ── Output emitters ───────────────────────────────────────────────────────────

def emit_ajt(llm: Dict, gate: GateDecision, run_label: str) -> None:
    _append_jsonl(AJT_PATH, {
        "ts":                      _now_iso(),
        "run_label":               run_label,
        "run_id":                  llm.get("run_id"),
        "actor_id":                llm.get("agent_id"),
        "action":                  llm.get("suggested_action"),
        "params":                  llm.get("params", {}),
        "irreversible":            True,
        "policy_id":               gate.policy_id,
        "policy_hash":             gate.policy_hash,
        "decision":                gate.decision,
        "deny_code":               gate.deny_code,
        "reason":                  gate.reason,
        "authority_token_present": gate.authority_token_present,
        "authority_token_id":      gate.authority_token_id,
        "boundary_id":             gate.boundary_id,
        "proof_signature":         gate.proof_signature,
        "ledger_index":            gate.ledger_index,
    })


def emit_otel_span(llm: Dict, gate: GateDecision, run_label: str) -> None:
    _append_jsonl(OTEL_PATH, {
        "ts":       _now_iso(),
        "name":     "execution.boundary",
        "run_label": run_label,
        "attributes": {
            "exec.gate.policy_id":               gate.policy_id,
            "exec.gate.actor_id":                llm.get("agent_id"),
            "exec.gate.action":                  llm.get("suggested_action"),
            "exec.gate.irreversible":            True,
            "exec.gate.decision":                gate.decision,
            "exec.gate.deny_code":               gate.deny_code,
            "exec.gate.authority_token_present": gate.authority_token_present,
            "exec.gate.authority_token_id":      gate.authority_token_id,
            "exec.boundary.id":                  gate.boundary_id,
            "exec.negative_proof":               gate.decision != "ALLOW",
        },
    })


# ── Pretty print helpers ──────────────────────────────────────────────────────

SEP = "─" * 60

def _section(title: str) -> None:
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


def _print_decision(gate: GateDecision) -> None:
    color = {"ALLOW": "\033[92m", "HOLD": "\033[93m", "DENY": "\033[91m"}.get(gate.decision, "")
    reset = "\033[0m"
    print(f"  decision  : {color}{gate.decision}{reset}")
    if gate.deny_code:
        print(f"  deny_code : {gate.deny_code}")
    if gate.reason:
        print(f"  reason    : {gate.reason}")
    if gate.boundary_id:
        print(f"  boundary_id: {gate.boundary_id}")
    if gate.proof_signature:
        print(f"  proof_sig : {gate.proof_signature[:48]}...")
    if gate.ledger_index is not None:
        print(f"  ledger_idx: {gate.ledger_index}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Execution Boundary Demo")
    parser.add_argument("--with-token", action="store_true",
                        help="2nd cut: include human authority token -> ALLOW")
    args = parser.parse_args()

    policy = _load_yaml(DEMO / "policy.yaml")
    llm    = _load_json(DEMO / "llm_output.json")
    token  = _load_json(DEMO / "human_authz.json") if args.with_token else None

    # ── Cut 1: LLM suggestion ────────────────────────────────────────────────
    _section("LLM SUGGESTION")
    print(json.dumps(llm, indent=2, ensure_ascii=False))

    # ── Cut 2: Gate evaluation (no token → HOLD) ─────────────────────────────
    run_label = "with-token" if token else "no-token"
    gate = evaluate_policy(policy, llm, token=token)
    _attach_core_proof(gate, llm, policy)
    emit_ajt(llm, gate, run_label)
    emit_otel_span(llm, gate, run_label)

    _section(f"GATE DECISION  [{run_label}]")
    _print_decision(gate)

    # ── Cut 3: Policy (highlight enforcement rules) ───────────────────────────
    _section("POLICY  (excerpt: identity + authority)")
    print((DEMO / "policy.yaml").read_text(encoding="utf-8"))

    # ── Cut 4: Output trail ───────────────────────────────────────────────────
    _section("AUDIT TRAIL  (last entry)")
    last_ajt = AJT_PATH.read_text().strip().split("\n")[-1]
    print(json.dumps(json.loads(last_ajt), indent=2, ensure_ascii=False))

    _section("OTel SPAN  (last entry)")
    last_otel = OTEL_PATH.read_text().strip().split("\n")[-1]
    print(json.dumps(json.loads(last_otel), indent=2, ensure_ascii=False))

    # ── Final line ────────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  Execution is not default.")
    print(SEP)


if __name__ == "__main__":
    main()
