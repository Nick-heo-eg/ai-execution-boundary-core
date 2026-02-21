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

__all__ = [
    "ExecutionBoundary",
    "ExecutionIntent",
    "Decision",
    "Proof",
    "VerificationResult",
    "DecisionType",
]
