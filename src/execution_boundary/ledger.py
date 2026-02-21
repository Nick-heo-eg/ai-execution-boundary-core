"""
Append-only ledger with hash chain integrity.

This module implements:
- NDJSON ledger format
- Hash chain (each entry references previous hash)
- Integrity verification
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any


DEFAULT_LEDGER_FILE = "judgment_ledger.ndjson"
GENESIS_HASH = "0" * 64


class Ledger:
    """
    Append-only ledger with hash chain.

    Properties:
    - Each entry contains hash of previous entry
    - Entries cannot be modified after append
    - Full chain verification possible
    - NDJSON format for easy parsing
    """

    def __init__(self, ledger_file: Optional[str] = None):
        """
        Initialize ledger.

        Args:
            ledger_file: Path to ledger file (default: judgment_ledger.ndjson)
        """
        self.ledger_file = ledger_file or DEFAULT_LEDGER_FILE

    def get_previous_hash(self) -> str:
        """
        Get hash of most recent ledger entry.

        Returns:
            Hash of last entry, or genesis hash if ledger empty
        """
        if not os.path.exists(self.ledger_file):
            return GENESIS_HASH

        try:
            with open(self.ledger_file, "r") as f:
                lines = f.readlines()

            if not lines:
                return GENESIS_HASH

            last_entry = json.loads(lines[-1])
            return last_entry.get("entry_hash", GENESIS_HASH)

        except Exception:
            return GENESIS_HASH

    def compute_entry_hash(self, entry: dict) -> str:
        """
        Compute SHA256 hash of ledger entry.

        Args:
            entry: Ledger entry dict (must NOT contain 'entry_hash' field)

        Returns:
            Hex-encoded SHA256 hash
        """
        # Exclude entry_hash itself from hash calculation
        hashable = {k: v for k, v in entry.items() if k != "entry_hash"}

        # Canonical JSON
        canonical = json.dumps(hashable, sort_keys=True).encode('utf-8')

        # SHA256
        return hashlib.sha256(canonical).hexdigest()

    def append(self, entry: dict) -> str:
        """
        Append entry to ledger with hash chain.

        Args:
            entry: Entry to append (will be modified to add entry_hash)

        Returns:
            Entry hash

        Side effects:
            - Writes to ledger file
            - Modifies entry dict to add entry_hash
        """
        # Ensure directory exists
        Path(self.ledger_file).parent.mkdir(parents=True, exist_ok=True)

        # Compute hash (before adding entry_hash field)
        entry_hash = self.compute_entry_hash(entry)

        # Add hash to entry
        entry["entry_hash"] = entry_hash

        # Append to file
        with open(self.ledger_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

        return entry_hash

    def read_all(self) -> List[Dict[str, Any]]:
        """
        Read all entries from ledger.

        Returns:
            List of ledger entries
        """
        if not os.path.exists(self.ledger_file):
            return []

        with open(self.ledger_file, "r") as f:
            lines = f.readlines()

        return [json.loads(line) for line in lines if line.strip()]

    def verify_integrity(self) -> Dict[str, Any]:
        """
        Verify complete ledger integrity.

        Checks:
        - Hash chain continuity
        - Entry hash correctness
        - No missing entries

        Returns:
            {
                "valid": bool,
                "total_entries": int,
                "error": str (if invalid),
                "last_hash": str (if valid)
            }
        """
        if not os.path.exists(self.ledger_file):
            return {
                "valid": False,
                "error": "Ledger file does not exist",
                "total_entries": 0
            }

        try:
            entries = self.read_all()

            if not entries:
                return {
                    "valid": False,
                    "error": "Ledger is empty",
                    "total_entries": 0
                }

            previous_hash = GENESIS_HASH

            for idx, entry in enumerate(entries):
                # Check hash chain continuity
                if entry.get("previous_hash") != previous_hash:
                    return {
                        "valid": False,
                        "error": f"Hash chain broken at entry {idx}",
                        "total_entries": len(entries)
                    }

                # Check entry hash correctness
                computed_hash = self.compute_entry_hash(entry)
                stored_hash = entry.get("entry_hash")

                if computed_hash != stored_hash:
                    return {
                        "valid": False,
                        "error": f"Entry hash mismatch at entry {idx}",
                        "total_entries": len(entries)
                    }

                # Update for next iteration
                previous_hash = stored_hash

            # All checks passed
            return {
                "valid": True,
                "total_entries": len(entries),
                "last_hash": previous_hash
            }

        except Exception as e:
            return {
                "valid": False,
                "error": f"Verification failed: {str(e)}",
                "total_entries": 0
            }
