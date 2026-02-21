"""
Core data models for Execution Boundary
"""

from dataclasses import dataclass
from typing import Literal, Optional
from datetime import datetime


DecisionType = Literal["ALLOW", "HALT", "HOLD"]


@dataclass
class ExecutionIntent:
    """
    Represents an execution request that needs boundary evaluation.

    Attributes:
        actor: Identifier of who/what is requesting execution
        action: Type of action being requested
        payload: The actual command/operation details
        timestamp: When this intent was created
    """
    actor: str
    action: str
    payload: str
    timestamp: datetime


@dataclass
class Decision:
    """
    The boundary decision result.

    Attributes:
        decision: ALLOW, HALT, or HOLD
        risk_score: Numeric risk assessment (0-100)
        reason: Human-readable explanation
        timestamp: When this decision was made
    """
    decision: DecisionType
    risk_score: int
    reason: str
    timestamp: datetime


@dataclass
class Proof:
    """
    Cryptographic proof of a boundary decision.

    Attributes:
        decision_hash: SHA256 hash of the decision
        signature: ED25519 signature
        ledger_index: Position in the immutable ledger
    """
    decision_hash: str
    signature: str
    ledger_index: int


@dataclass
class VerificationResult:
    """
    Result of proof verification.

    Attributes:
        valid: Whether the proof is valid
        message: Details about the verification result
    """
    valid: bool
    message: str
