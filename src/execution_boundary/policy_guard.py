"""
PolicyGuard — Identity-based fail-closed gate.

Evaluated BEFORE severity/risk scoring.
Unknown agent or unknown action → immediate DENY.

This is not a risk heuristic.
This is a structural identity check at the boundary.

Policy schema (subset relevant to PolicyGuard):

    version: 1
    defaults:
      unknown_agent:  DENY   # or ALLOW (not recommended)
      unknown_action: DENY

    identity:
      agents:
        - agent_id: "agent.finance"
          allowed_actions:
            - action: "wire_transfer"
            - action: "read_ledger"

Behavior:
    - If policy is None: fail-open (no identity constraint — all agents/actions pass).
    - If policy.defaults.unknown_agent == DENY and actor not in agents → PolicyViolation("unknown_agent")
    - If policy.defaults.unknown_action == DENY and action not in agent's allowed_actions → PolicyViolation("unknown_action")
    - Otherwise: pass-through (let severity/risk gate decide).

Raises:
    PolicyViolation — structural identity violation, carries reason code.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


# ── Exception ─────────────────────────────────────────────────────────────────

class PolicyViolation(RuntimeError):
    """
    Raised by PolicyGuard when identity check fails.

    reason_code: "unknown_agent" | "unknown_action"
    actor:       intent.actor
    action:      intent.action
    """
    def __init__(self, reason_code: str, actor: str, action: str) -> None:
        self.reason_code = reason_code
        self.actor       = actor
        self.action      = action
        super().__init__(
            f"[POLICY_VIOLATION] reason={reason_code} actor={actor} action={action}"
        )


# ── Policy loader ─────────────────────────────────────────────────────────────

def _extract_agents(policy: Dict) -> Dict[str, List[str]]:
    """
    Returns { agent_id: [allowed_action, ...] } from policy dict.
    Empty dict if no identity section.
    """
    identity = policy.get("identity", {})
    agents_list: List[Dict] = identity.get("agents", [])
    result: Dict[str, List[str]] = {}
    for agent_cfg in agents_list:
        agent_id = agent_cfg.get("agent_id", "")
        allowed  = [
            a["action"] for a in agent_cfg.get("allowed_actions", [])
            if isinstance(a, dict) and "action" in a
        ]
        result[agent_id] = allowed
    return result


def _default_deny(policy: Dict, key: str) -> bool:
    """True if policy.defaults.<key> resolves to DENY (case-insensitive)."""
    defaults = policy.get("defaults", {})
    val = defaults.get(key, "DENY")
    return str(val).upper() == "DENY"


# ── Guard ─────────────────────────────────────────────────────────────────────

class PolicyGuard:
    """
    Structural identity check at the execution boundary.

    Call check(actor, action, policy) before any risk/severity evaluation.

    Fail-closed contract:
        - Unknown agent  → PolicyViolation("unknown_agent")  if defaults.unknown_agent == DENY
        - Unknown action → PolicyViolation("unknown_action") if defaults.unknown_action == DENY
        - policy is None → pass-through (identity check skipped)
    """

    def check(
        self,
        actor:  str,
        action: str,
        policy: Any,
    ) -> None:
        """
        Check actor/action against policy identity rules.

        Args:
            actor:  intent.actor (e.g. "agent.finance")
            action: intent.action (e.g. "wire_transfer")
            policy: policy dict (loaded from YAML), or None to skip.

        Returns:
            None — if identity check passes.

        Raises:
            PolicyViolation — if actor or action is not authorized.
        """
        if policy is None:
            # No policy provided → identity check disabled (fail-open)
            return

        if not isinstance(policy, dict):
            # Unsupported policy format → fail-closed
            raise PolicyViolation(
                reason_code="invalid_policy",
                actor=actor,
                action=action,
            )

        agents = _extract_agents(policy)

        # ── Agent check ───────────────────────────────────────────────────────
        deny_unknown_agent = _default_deny(policy, "unknown_agent")

        if deny_unknown_agent and actor not in agents:
            raise PolicyViolation(
                reason_code="unknown_agent",
                actor=actor,
                action=action,
            )

        # ── Action check ──────────────────────────────────────────────────────
        deny_unknown_action = _default_deny(policy, "unknown_action")

        if deny_unknown_action:
            allowed_actions = agents.get(actor, [])
            if action not in allowed_actions:
                raise PolicyViolation(
                    reason_code="unknown_action",
                    actor=actor,
                    action=action,
                )


# ── Module-level singleton ────────────────────────────────────────────────────

_guard = PolicyGuard()


def check_policy(actor: str, action: str, policy: Any) -> None:
    """
    Module-level convenience wrapper around PolicyGuard.check().

    Raises PolicyViolation on identity failure.
    Pass policy=None to disable identity check.
    """
    _guard.check(actor, action, policy)
