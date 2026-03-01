"""
AI Execution Boundary - Core Engine

This package contains the core execution boundary engine.

Scope:
- Pre-execution evaluation
- Cryptographic proof issuance
- Immutable ledger entry
- Offline verification

Out of Scope:
- UI/UX
- Transport layer (Telegram, HTTP, etc.)
- Agent adapters
- Multi-tenant support
"""

from .interface import ExecutionBoundary
from .models import (
    ExecutionIntent,
    Decision,
    Proof,
    VerificationResult,
    BoundaryRecord,
    DecisionType,
    EnforcementOutcome,
    ExecutionDeniedError,
    ExecutionHeldError,
    ExecutionExpiredError,
    new_boundary_id,
)
from .engine import ExecutionBoundaryEngine
from .risk import calculate_risk_score
from .enforce import enforce_boundary, check_hold_expired
from .severity_gate import SeverityGate, SystemSeverity, SeverityGateResult
from .policy_guard import PolicyGuard, PolicyViolation, check_policy

__all__ = [
    # Core
    "ExecutionBoundary",
    "ExecutionBoundaryEngine",
    # Models
    "ExecutionIntent",
    "Decision",
    "Proof",
    "VerificationResult",
    "BoundaryRecord",
    # Types / Enums
    "DecisionType",
    "EnforcementOutcome",
    # Exceptions
    "ExecutionDeniedError",
    "ExecutionHeldError",
    "ExecutionExpiredError",
    # Helpers
    "new_boundary_id",
    "calculate_risk_score",
    # Enforcement
    "enforce_boundary",
    "check_hold_expired",
    # Severity gate
    "SeverityGate",
    "SystemSeverity",
    "SeverityGateResult",
    # Policy guard
    "PolicyGuard",
    "PolicyViolation",
    "check_policy",
]
