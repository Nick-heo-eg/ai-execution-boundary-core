"""
Cryptographic signing module using ED25519.

This module handles:
- Private key generation and loading
- Digital signatures for decisions
- Public key verification
"""

import json
import os
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey
)
from cryptography.hazmat.primitives import serialization


DEFAULT_KEY_FILE = ".private_key.pem"


class KeyManager:
    """
    Manages ED25519 key pair for signing decisions.

    Responsibilities:
    - Generate new key pair if not exists
    - Load existing private key
    - Persist keys securely
    """

    def __init__(self, key_file: Optional[str] = None):
        """
        Initialize key manager.

        Args:
            key_file: Path to private key file (default: .private_key.pem)
        """
        self.key_file = key_file or DEFAULT_KEY_FILE
        self._private_key: Optional[Ed25519PrivateKey] = None

    def get_or_create_key(self) -> Ed25519PrivateKey:
        """
        Load existing private key or generate new one.

        Returns:
            ED25519 private key

        Side effects:
            - Creates key file if not exists
            - Writes to disk on first generation
        """
        if self._private_key is not None:
            return self._private_key

        if os.path.exists(self.key_file):
            self._private_key = self._load_key()
        else:
            self._private_key = self._generate_and_save_key()

        return self._private_key

    def _load_key(self) -> Ed25519PrivateKey:
        """Load private key from file."""
        with open(self.key_file, "rb") as f:
            return serialization.load_pem_private_key(
                f.read(),
                password=None
            )

    def _generate_and_save_key(self) -> Ed25519PrivateKey:
        """Generate new key pair and save to file."""
        private_key = Ed25519PrivateKey.generate()

        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        # Ensure directory exists
        Path(self.key_file).parent.mkdir(parents=True, exist_ok=True)

        with open(self.key_file, "wb") as f:
            f.write(pem)

        return private_key

    def get_public_key(self) -> Ed25519PublicKey:
        """
        Get public key from private key.

        Returns:
            ED25519 public key
        """
        private_key = self.get_or_create_key()
        return private_key.public_key()


def sign_data(data: dict, private_key: Ed25519PrivateKey) -> str:
    """
    Sign data dictionary with private key.

    Args:
        data: Dictionary to sign
        private_key: ED25519 private key

    Returns:
        Hex-encoded signature string
    """
    # Canonical JSON representation (sorted keys)
    canonical = json.dumps(data, sort_keys=True).encode('utf-8')

    # Sign
    signature = private_key.sign(canonical)

    # Return hex string
    return signature.hex()


def verify_signature(
    data: dict,
    signature_hex: str,
    public_key: Ed25519PublicKey
) -> bool:
    """
    Verify signature of data.

    Args:
        data: Dictionary that was signed
        signature_hex: Hex-encoded signature
        public_key: ED25519 public key

    Returns:
        True if signature is valid, False otherwise
    """
    try:
        # Canonical JSON
        canonical = json.dumps(data, sort_keys=True).encode('utf-8')

        # Decode signature
        signature = bytes.fromhex(signature_hex)

        # Verify (raises exception if invalid)
        public_key.verify(signature, canonical)

        return True

    except Exception:
        return False
