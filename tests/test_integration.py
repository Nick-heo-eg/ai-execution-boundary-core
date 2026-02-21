"""
Integration tests for complete flow: evaluate → proof → verify
"""

import pytest
import tempfile
import os
from datetime import datetime

from execution_boundary import (
    ExecutionBoundaryEngine,
    ExecutionIntent
)


class TestEndToEnd:
    """Test complete execution boundary flow"""

    def test_full_flow_allow_decision(self):
        """Test complete flow for ALLOW decision"""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = os.path.join(tmpdir, "key.pem")
            ledger_file = os.path.join(tmpdir, "ledger.ndjson")

            engine = ExecutionBoundaryEngine(
                key_file=key_file,
                ledger_file=ledger_file
            )

            # Create intent
            intent = ExecutionIntent(
                actor="test_user",
                action="shell.exec",
                payload="ls -la",
                timestamp=datetime.now()
            )

            # Evaluate
            decision = engine.evaluate(intent)
            assert decision.decision == "ALLOW"
            assert decision.risk_score == 10

            # Issue proof
            proof = engine.issue_proof(decision)
            assert proof.signature is not None
            assert proof.decision_hash is not None
            assert proof.ledger_index == 0

            # Verify proof
            result = engine.verify(proof)
            assert result.valid
            assert "verified" in result.message.lower()

    def test_full_flow_halt_decision(self):
        """Test complete flow for HALT decision"""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = os.path.join(tmpdir, "key.pem")
            ledger_file = os.path.join(tmpdir, "ledger.ndjson")

            engine = ExecutionBoundaryEngine(
                key_file=key_file,
                ledger_file=ledger_file
            )

            # Create dangerous intent
            intent = ExecutionIntent(
                actor="test_user",
                action="shell.exec",
                payload="rm -rf /",
                timestamp=datetime.now()
            )

            # Evaluate
            decision = engine.evaluate(intent)
            assert decision.decision == "HALT"
            assert decision.risk_score == 95

            # Issue proof
            proof = engine.issue_proof(decision)
            assert proof is not None

            # Verify proof
            result = engine.verify(proof)
            assert result.valid

    def test_multiple_decisions_chain(self):
        """Test multiple decisions create valid chain"""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = os.path.join(tmpdir, "key.pem")
            ledger_file = os.path.join(tmpdir, "ledger.ndjson")

            engine = ExecutionBoundaryEngine(
                key_file=key_file,
                ledger_file=ledger_file
            )

            commands = [
                "ls",
                "cat file.txt",
                "rm file.txt",
                "rm -rf /"
            ]

            proofs = []

            # Create multiple decisions
            for cmd in commands:
                intent = ExecutionIntent(
                    actor="test_user",
                    action="shell.exec",
                    payload=cmd,
                    timestamp=datetime.now()
                )

                decision = engine.evaluate(intent)
                proof = engine.issue_proof(decision)
                proofs.append(proof)

            # Verify all proofs
            for proof in proofs:
                result = engine.verify(proof)
                assert result.valid

            # Check ledger integrity
            ledger_check = engine.ledger.verify_integrity()
            assert ledger_check["valid"]
            assert ledger_check["total_entries"] == 4

    def test_verify_invalid_proof(self):
        """Invalid proof should fail verification"""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = os.path.join(tmpdir, "key.pem")
            ledger_file = os.path.join(tmpdir, "ledger.ndjson")

            engine = ExecutionBoundaryEngine(
                key_file=key_file,
                ledger_file=ledger_file
            )

            # Create and prove decision
            intent = ExecutionIntent(
                actor="test_user",
                action="shell.exec",
                payload="ls",
                timestamp=datetime.now()
            )

            decision = engine.evaluate(intent)
            proof = engine.issue_proof(decision)

            # Corrupt proof
            from execution_boundary.models import Proof
            corrupted_proof = Proof(
                decision_hash="0" * 64,  # Wrong hash
                signature=proof.signature,
                ledger_index=0
            )

            # Verification should fail
            result = engine.verify(corrupted_proof)
            assert not result.valid

    def test_custom_threshold(self):
        """Engine should respect custom halt threshold"""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = os.path.join(tmpdir, "key.pem")
            ledger_file = os.path.join(tmpdir, "ledger.ndjson")

            # Lower threshold
            engine = ExecutionBoundaryEngine(
                halt_threshold=50,
                key_file=key_file,
                ledger_file=ledger_file
            )

            # Command with risk score 60
            intent = ExecutionIntent(
                actor="test_user",
                action="shell.exec",
                payload="rm file.txt",  # Risk score: 60
                timestamp=datetime.now()
            )

            decision = engine.evaluate(intent)

            # Should be HALT with threshold=50
            assert decision.decision == "HALT"
            assert decision.risk_score == 60
