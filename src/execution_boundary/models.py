"""
Core data models for Execution Boundary
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Literal, Optional


DecisionType = Literal["ALLOW", "HALT", "HOLD"]


class EnforcementOutcome(str, Enum):
    """Deterministic enforcement result — used by enforce_boundary()."""
    ALLOW   = "ALLOW"
    HOLD    = "HOLD"
    DENY    = "DENY"
    EXPIRED = "EXPIRED"


# ── Exceptions ───────────────────────────────────────────────────────────────

class ExecutionDeniedError(RuntimeError):
    """
    Raised by enforce_boundary() when outcome == DENY.
    Caller MUST NOT proceed with the action after catching this.
    """
    def __init__(self, boundary_id: str, reason: str, risk_score: int = 0) -> None:
        self.boundary_id = boundary_id
        self.reason      = reason
        self.risk_score  = risk_score
        super().__init__(
            f"[DENY] boundary={boundary_id} risk={risk_score} reason={reason}"
        )


class ExecutionHeldError(RuntimeError):
    """
    Raised by enforce_boundary() when outcome == HOLD.
    Caller MUST NOT proceed with the action; await human approval.
    """
    def __init__(
        self,
        boundary_id: str,
        reason: str,
        deadline_ts: Optional[str] = None,
        proof_signature: Optional[str] = None,
        ledger_index: Optional[int] = None,
    ) -> None:
        self.boundary_id     = boundary_id
        self.reason          = reason
        self.deadline_ts     = deadline_ts      # ISO-8601 UTC string
        self.proof_signature = proof_signature  # ED25519 hex — negative proof
        self.ledger_index    = ledger_index
        super().__init__(
            f"[HOLD] boundary={boundary_id} deadline={deadline_ts} reason={reason}"
        )


class ExecutionExpiredError(RuntimeError):
    """Raised when a HOLD boundary has passed its deadline_ts."""
    def __init__(self, boundary_id: str, deadline_ts: str) -> None:
        self.boundary_id = boundary_id
        self.deadline_ts = deadline_ts
        super().__init__(
            f"[EXPIRED] boundary={boundary_id} deadline={deadline_ts}"
        )


# ── Helper: boundary_id (UUIDv4 — uuid7 not in stdlib, fallback is fine) ────

def new_boundary_id() -> str:
    """Generate a new unique boundary_id (UUIDv4-based)."""
    return str(uuid.uuid4())


# ── Core dataclasses ─────────────────────────────────────────────────────────

@dataclass
class ExecutionIntent:
    """
    Represents an execution request that needs boundary evaluation.

    Attributes:
        actor:    Identifier of who/what is requesting execution
        action:   Type of action being requested
        payload:  The actual command/operation details (str or dict)
        timestamp: When this intent was created
        run_id:   Logical run context (groups multiple boundaries)
        metadata: Optional extra context
    """
    actor:     str
    action:    str
    payload:   str
    timestamp: datetime
    run_id:    Optional[str] = None
    metadata:  Optional[dict] = None


@dataclass
class Decision:
    """
    The boundary decision result.

    Attributes:
        decision:     ALLOW, HALT, or HOLD
        risk_score:   Numeric risk assessment (0-100)
        reason:       Human-readable explanation
        timestamp:    When this decision was made
        boundary_id:  Unique ID for this boundary crossing (≠ trace_id)
        decision_id:  Alias for boundary_id (explicit field)
        decision_hash: SHA-256 over canonical decision fields
        policy_hash:  SHA-256 over policy snapshot used for this decision
        deadline_ts:  ISO-8601 UTC — only for HOLD outcomes
        negative_proof: True when decision is DENY/HOLD/EXPIRED
    """
    decision:      DecisionType
    risk_score:    int
    reason:        str
    timestamp:     datetime

    boundary_id:            str          = field(default_factory=new_boundary_id)
    decision_id:            str          = field(default="")   # set = boundary_id post-init
    decision_hash:          str          = field(default="")   # fingerprint, computed post-init
    decision_instance_hash: str          = field(default="")   # per-boundary tamper-evident ID
    policy_hash:            str          = field(default="")   # set by engine
    deadline_ts:            Optional[str] = None
    negative_proof:         bool         = False

    def __post_init__(self) -> None:
        if not self.decision_id:
            self.decision_id = self.boundary_id
        if not self.decision_hash:
            self.decision_hash = self._compute_hash()
        if not self.decision_instance_hash:
            self.decision_instance_hash = self._compute_instance_hash()
        self.negative_proof = self.decision in ("HALT", "HOLD")

    def _compute_hash(self) -> str:
        """
        decision_hash = DecisionFingerprint (content-based, deterministic).

        Excludes boundary_id and timestamp so that identical decisions
        under the same policy always produce the same fingerprint.
        Tamper-evidence is provided by the ledger hash chain + ED25519.

        Canonical fields: decision, risk_score, policy_hash, action_digest,
                          actor_id (if available via __post_init__ caller).
        Reason is excluded — use exec.block.reason / ledger field instead.
        """
        action_digest = hashlib.sha256(
            self.reason.encode("utf-8")
        ).hexdigest()  # placeholder: reason_code will replace this in v0.2
        canonical = json.dumps(
            {
                "decision":      self.decision,
                "risk_score":    self.risk_score,
                "policy_hash":   self.policy_hash,
                "action_digest": action_digest,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _compute_instance_hash(self) -> str:
        """
        decision_instance_hash = per-boundary tamper-evident ID.

        Includes boundary_id + timestamp + decision_hash (fingerprint).
        Changes on every boundary crossing even if content is identical.
        Used for ledger chaining and OTel exec.decision.instance_hash.
        """
        canonical = json.dumps(
            {
                "boundary_id":   self.boundary_id,
                "timestamp":     self.timestamp.isoformat(),
                "decision_hash": self.decision_hash,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class Proof:
    """
    Cryptographic proof of a boundary decision.

    Attributes:
        decision_hash:  SHA256 hash of the decision
        signature:      ED25519 signature
        ledger_index:   Position in the immutable ledger
        boundary_id:    boundary_id from the Decision (for cross-referencing)
        negative_proof: True when this proof covers a DENY/HOLD decision
    """
    decision_hash:  str
    signature:      str
    ledger_index:   int
    boundary_id:    str  = ""
    negative_proof: bool = False


@dataclass
class VerificationResult:
    """
    Result of proof verification.

    Attributes:
        valid:   Whether the proof is valid
        message: Details about the verification result
    """
    valid:   bool
    message: str


@dataclass
class BoundaryRecord:
    """
    Full record of a boundary crossing — stored in ledger and OTel span.
    This is the single source of truth for legal traceability.
    """
    boundary_id:            str
    run_id:                 Optional[str]
    actor:                  str
    action:                 str
    outcome:                EnforcementOutcome
    risk_score:             int
    reason:                 str
    policy_hash:            str
    decision_hash:          str   # fingerprint (deterministic, content-based)
    ts:                     str   # ISO-8601 UTC
    decision_instance_hash: str   = ""   # per-boundary tamper-evident ID
    deadline_ts:            Optional[str] = None
    negative_proof:         bool = False
    proof_signature:        Optional[str] = None
    ledger_index:           Optional[int] = None
