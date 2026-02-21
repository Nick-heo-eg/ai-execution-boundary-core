"""
Execution Boundary Engine Implementation
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Optional

from .interface import ExecutionBoundary
from .models import ExecutionIntent, Decision, Proof, VerificationResult, DecisionType
from .risk import calculate_risk_score
from .crypto import KeyManager, sign_data, verify_signature
from .ledger import Ledger


class ExecutionBoundaryEngine(ExecutionBoundary):
    """
    Core implementation of the execution boundary engine.

    This implementation provides:
    - Rule-based risk scoring
    - ALLOW/HALT decision logic
    - ED25519 cryptographic proof
    - Append-only ledger with hash chain

    Configuration:
    - Risk threshold: 80 (HALT if >= 80)
    - No HOLD state in v0.1
    """

    def __init__(
        self,
        halt_threshold: int = 80,
        key_file: Optional[str] = None,
        ledger_file: Optional[str] = None
    ):
        """
        Initialize the boundary engine.

        Args:
            halt_threshold: Risk score threshold for HALT decision (default: 80)
            key_file: Path to private key file (optional)
            ledger_file: Path to ledger file (optional)
        """
        self.halt_threshold = halt_threshold
        self.key_manager = KeyManager(key_file)
        self.ledger = Ledger(ledger_file)

    def evaluate(self, intent: ExecutionIntent) -> Decision:
        """
        Evaluate an execution intent and return a decision.

        Logic:
        1. Calculate risk score using rule-based engine
        2. Compare against threshold
        3. Return ALLOW or HALT

        Args:
            intent: Execution request containing payload (shell command)

        Returns:
            Decision with ALLOW or HALT and risk reasoning
        """
        # Calculate risk score from payload
        risk_score, reason = calculate_risk_score(intent.payload)

        # Determine decision based on threshold
        if risk_score >= self.halt_threshold:
            decision_type: DecisionType = "HALT"
        else:
            decision_type: DecisionType = "ALLOW"

        return Decision(
            decision=decision_type,
            risk_score=risk_score,
            reason=reason,
            timestamp=datetime.now(timezone.utc)
        )

    def issue_proof(self, decision: Decision) -> Proof:
        """
        Issue cryptographic proof for a decision.

        Process:
        1. Get previous ledger hash
        2. Create ledger entry
        3. Sign entry with ED25519
        4. Compute entry hash
        5. Append to ledger
        6. Return proof

        Args:
            decision: The decision to prove

        Returns:
            Proof object with signature and ledger reference
        """
        # Get previous hash for chain
        previous_hash = self.ledger.get_previous_hash()

        # Create ledger entry
        entry = {
            "timestamp": decision.timestamp.isoformat(),
            "decision": decision.decision,
            "risk_score": decision.risk_score,
            "reason": decision.reason,
            "previous_hash": previous_hash
        }

        # Sign entry
        private_key = self.key_manager.get_or_create_key()
        signature = sign_data(entry, private_key)
        entry["signature"] = signature

        # Append to ledger (adds entry_hash)
        entry_hash = self.ledger.append(entry)

        # Get ledger index
        all_entries = self.ledger.read_all()
        ledger_index = len(all_entries) - 1

        return Proof(
            decision_hash=entry_hash,
            signature=signature,
            ledger_index=ledger_index
        )

    def verify(self, proof: Proof) -> VerificationResult:
        """
        Verify proof integrity.

        Checks:
        1. Ledger integrity (hash chain)
        2. Signature validity
        3. Entry existence at claimed index

        Args:
            proof: The proof to verify

        Returns:
            VerificationResult with validity and message
        """
        # First verify overall ledger integrity
        ledger_check = self.ledger.verify_integrity()

        if not ledger_check["valid"]:
            return VerificationResult(
                valid=False,
                message=f"Ledger integrity check failed: {ledger_check['error']}"
            )

        # Get all entries
        entries = self.ledger.read_all()

        # Check if ledger index is valid
        if proof.ledger_index >= len(entries):
            return VerificationResult(
                valid=False,
                message=f"Invalid ledger index: {proof.ledger_index}"
            )

        # Get entry at claimed index
        entry = entries[proof.ledger_index]

        # Verify entry hash matches proof
        if entry.get("entry_hash") != proof.decision_hash:
            return VerificationResult(
                valid=False,
                message="Entry hash mismatch"
            )

        # Verify signature
        public_key = self.key_manager.get_public_key()

        # Reconstruct signed data (without signature and entry_hash)
        signed_data = {
            k: v for k, v in entry.items()
            if k not in ["signature", "entry_hash"]
        }

        signature_valid = verify_signature(
            signed_data,
            proof.signature,
            public_key
        )

        if not signature_valid:
            return VerificationResult(
                valid=False,
                message="Signature verification failed"
            )

        # All checks passed
        return VerificationResult(
            valid=True,
            message=f"Proof verified at ledger index {proof.ledger_index}"
        )
