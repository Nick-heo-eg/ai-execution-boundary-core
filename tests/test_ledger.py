"""
Unit tests for ledger module
"""

import pytest
import tempfile
import os
import json

from execution_boundary.ledger import Ledger, GENESIS_HASH


class TestLedger:
    """Test ledger operations"""

    def test_genesis_hash_for_empty_ledger(self):
        """Empty ledger should return genesis hash"""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_file = os.path.join(tmpdir, "test.ndjson")
            ledger = Ledger(ledger_file)

            prev_hash = ledger.get_previous_hash()
            assert prev_hash == GENESIS_HASH

    def test_append_first_entry(self):
        """Should append first entry with genesis hash"""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_file = os.path.join(tmpdir, "test.ndjson")
            ledger = Ledger(ledger_file)

            entry = {
                "decision": "ALLOW",
                "risk_score": 10,
                "previous_hash": GENESIS_HASH
            }

            entry_hash = ledger.append(entry)

            # Should return hash
            assert entry_hash is not None
            assert len(entry_hash) == 64

            # Entry should have hash
            assert entry["entry_hash"] == entry_hash

    def test_hash_chain_continuity(self):
        """Second entry should reference first entry hash"""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_file = os.path.join(tmpdir, "test.ndjson")
            ledger = Ledger(ledger_file)

            # First entry
            entry1 = {
                "decision": "ALLOW",
                "previous_hash": GENESIS_HASH
            }
            hash1 = ledger.append(entry1)

            # Second entry should reference first
            prev_hash = ledger.get_previous_hash()
            assert prev_hash == hash1

            entry2 = {
                "decision": "HALT",
                "previous_hash": prev_hash
            }
            hash2 = ledger.append(entry2)

            # Verify chain
            entries = ledger.read_all()
            assert len(entries) == 2
            assert entries[0]["entry_hash"] == hash1
            assert entries[1]["previous_hash"] == hash1
            assert entries[1]["entry_hash"] == hash2

    def test_compute_entry_hash_excludes_entry_hash(self):
        """Entry hash should not include itself"""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_file = os.path.join(tmpdir, "test.ndjson")
            ledger = Ledger(ledger_file)

            entry = {
                "decision": "ALLOW",
                "previous_hash": GENESIS_HASH
            }

            # Compute without entry_hash
            hash1 = ledger.compute_entry_hash(entry)

            # Add entry_hash and compute again
            entry["entry_hash"] = hash1
            hash2 = ledger.compute_entry_hash(entry)

            # Should be same
            assert hash1 == hash2

    def test_verify_integrity_valid_chain(self):
        """Valid chain should verify"""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_file = os.path.join(tmpdir, "test.ndjson")
            ledger = Ledger(ledger_file)

            # Add entries
            for i in range(5):
                entry = {
                    "decision": "ALLOW",
                    "index": i,
                    "previous_hash": ledger.get_previous_hash()
                }
                ledger.append(entry)

            # Verify
            result = ledger.verify_integrity()
            assert result["valid"]
            assert result["total_entries"] == 5

    def test_verify_integrity_broken_chain(self):
        """Broken chain should fail verification"""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_file = os.path.join(tmpdir, "test.ndjson")
            ledger = Ledger(ledger_file)

            # Add entries normally
            entry1 = {"data": "entry1", "previous_hash": GENESIS_HASH}
            ledger.append(entry1)

            entry2 = {"data": "entry2", "previous_hash": ledger.get_previous_hash()}
            ledger.append(entry2)

            # Manually corrupt ledger file
            with open(ledger_file, "r") as f:
                lines = f.readlines()

            # Break the chain by changing previous_hash of second entry
            entry2_corrupted = json.loads(lines[1])
            entry2_corrupted["previous_hash"] = "0" * 64

            with open(ledger_file, "w") as f:
                f.write(lines[0])
                f.write(json.dumps(entry2_corrupted) + "\n")

            # Verify should fail
            result = ledger.verify_integrity()
            assert not result["valid"]
            assert "Hash chain broken" in result["error"]

    def test_verify_integrity_corrupted_entry(self):
        """Corrupted entry should fail verification"""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_file = os.path.join(tmpdir, "test.ndjson")
            ledger = Ledger(ledger_file)

            # Add entry
            entry = {"data": "test", "previous_hash": GENESIS_HASH}
            ledger.append(entry)

            # Manually corrupt entry
            with open(ledger_file, "r") as f:
                line = f.read()

            corrupted = json.loads(line)
            corrupted["data"] = "corrupted"  # Change data without updating hash

            with open(ledger_file, "w") as f:
                f.write(json.dumps(corrupted) + "\n")

            # Verify should fail
            result = ledger.verify_integrity()
            assert not result["valid"]
            assert "hash mismatch" in result["error"].lower()

    def test_read_all_empty_ledger(self):
        """Empty ledger should return empty list"""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_file = os.path.join(tmpdir, "test.ndjson")
            ledger = Ledger(ledger_file)

            entries = ledger.read_all()
            assert entries == []
