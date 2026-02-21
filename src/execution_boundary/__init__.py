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
from .models import ExecutionIntent, Decision, Proof, VerificationResult, DecisionType
from .engine import ExecutionBoundaryEngine
from .risk import calculate_risk_score

__all__ = [
    "ExecutionBoundary",
    "ExecutionBoundaryEngine",
    "ExecutionIntent",
    "Decision",
    "Proof",
    "VerificationResult",
    "DecisionType",
    "calculate_risk_score",
]
