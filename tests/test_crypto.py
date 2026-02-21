"""
Unit tests for cryptographic module
"""

import pytest
import tempfile
import os
from pathlib import Path

from execution_boundary.crypto import (
    KeyManager,
    sign_data,
    verify_signature
)


class TestKeyManager:
    """Test key management"""

    def test_key_generation(self):
        """Should generate new key if not exists"""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = os.path.join(tmpdir, "test_key.pem")
            manager = KeyManager(key_file)

            # Generate key
            key1 = manager.get_or_create_key()
            assert key1 is not None

            # File should exist
            assert os.path.exists(key_file)

    def test_key_persistence(self):
        """Should load existing key"""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = os.path.join(tmpdir, "test_key.pem")
            manager1 = KeyManager(key_file)

            # Generate and get public key
            key1 = manager1.get_or_create_key()
            pub1 = manager1.get_public_key()

            # Create new manager, should load same key
            manager2 = KeyManager(key_file)
            key2 = manager2.get_or_create_key()
            pub2 = manager2.get_public_key()

            # Public keys should match
            pub1_bytes = pub1.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            pub2_bytes = pub2.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )

            assert pub1_bytes == pub2_bytes

    def test_public_key_derivation(self):
        """Should derive public key from private key"""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = os.path.join(tmpdir, "test_key.pem")
            manager = KeyManager(key_file)

            private_key = manager.get_or_create_key()
            public_key = manager.get_public_key()

            # Public key should be derivable
            assert public_key is not None


class TestSigning:
    """Test data signing and verification"""

    def test_sign_and_verify_valid(self):
        """Valid signature should verify"""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = os.path.join(tmpdir, "test_key.pem")
            manager = KeyManager(key_file)

            private_key = manager.get_or_create_key()
            public_key = manager.get_public_key()

            # Sign data
            data = {"decision": "ALLOW", "risk_score": 10}
            signature = sign_data(data, private_key)

            # Verify
            assert verify_signature(data, signature, public_key)

    def test_verify_invalid_signature(self):
        """Invalid signature should not verify"""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = os.path.join(tmpdir, "test_key.pem")
            manager = KeyManager(key_file)

            private_key = manager.get_or_create_key()
            public_key = manager.get_public_key()

            # Sign data
            data = {"decision": "ALLOW", "risk_score": 10}
            signature = sign_data(data, private_key)

            # Modify data
            data["risk_score"] = 99

            # Should not verify
            assert not verify_signature(data, signature, public_key)

    def test_verify_wrong_signature(self):
        """Wrong signature should not verify"""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = os.path.join(tmpdir, "test_key.pem")
            manager = KeyManager(key_file)

            private_key = manager.get_or_create_key()
            public_key = manager.get_public_key()

            data = {"decision": "ALLOW"}

            # Create wrong signature
            wrong_signature = "0" * 128

            # Should not verify
            assert not verify_signature(data, wrong_signature, public_key)

    def test_canonical_json_ordering(self):
        """Signature should be independent of key order"""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = os.path.join(tmpdir, "test_key.pem")
            manager = KeyManager(key_file)

            private_key = manager.get_or_create_key()

            # Same data, different key order
            data1 = {"b": 2, "a": 1}
            data2 = {"a": 1, "b": 2}

            sig1 = sign_data(data1, private_key)
            sig2 = sign_data(data2, private_key)

            # Should produce same signature
            assert sig1 == sig2


# Add missing import for test
from cryptography.hazmat.primitives import serialization
