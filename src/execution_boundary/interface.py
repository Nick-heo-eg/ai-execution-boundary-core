"""
Execution Boundary Core Interface

This is the contract that all boundary implementations must satisfy.
"""

from .models import ExecutionIntent, Decision, Proof, VerificationResult


class ExecutionBoundary:
    """
    Core execution boundary engine.

    Responsibilities:
    - Evaluate execution intent and make ALLOW/HALT/HOLD decision
    - Issue cryptographic proof for decisions
    - Verify proof integrity

    This is a pure decision engine with no external dependencies:
    - No UI
    - No Telegram
    - No LLM dependency
    - No network calls
    - No database connections

    Implementations should be:
    - Deterministic (same input → same output)
    - Offline-capable
    - Stateless (except for ledger append)
    """

    def evaluate(self, intent: ExecutionIntent) -> Decision:
        """
        Evaluate an execution intent and return a decision.

        Args:
            intent: The execution request to evaluate

        Returns:
            Decision object with ALLOW/HALT/HOLD and reasoning

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError

    def issue_proof(self, decision: Decision) -> Proof:
        """
        Issue cryptographic proof for a decision.

        This creates:
        - SHA256 hash of the decision
        - ED25519 signature
        - Ledger entry with hash chain

        Args:
            decision: The decision to prove

        Returns:
            Proof object with signature and ledger reference

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError

    def verify(self, proof: Proof) -> VerificationResult:
        """
        Verify the integrity of a proof.

        This checks:
        - Signature validity
        - Hash chain integrity
        - Ledger consistency

        Args:
            proof: The proof to verify

        Returns:
            VerificationResult indicating validity

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError
