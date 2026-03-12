"""Unit tests for Fernet encryption module — common/crypto/fernet.py.

Tests the stateless encrypt/decrypt/rotate functions in isolation.
No database or API dependencies.
"""

import pytest
from cryptography.fernet import Fernet

from common.crypto.exceptions import (
    DecryptionError,
    InvalidMasterKeyError,
    MasterKeyNotConfiguredError,
)
from common.crypto.fernet import (
    decrypt_credential,
    encrypt_credential,
    generate_master_key,
    re_encrypt_credential,
    validate_master_key,
)


@pytest.fixture
def master_key():
    """Generate a fresh Fernet key for each test."""
    return Fernet.generate_key().decode()


# ── generate_master_key ──────────────────────────────────────────────────


class TestGenerateMasterKey:
    def test_returns_valid_fernet_key(self):
        """Generated key should be accepted by Fernet()."""
        key = generate_master_key()
        # Fernet keys are 44 chars (32 bytes base64-encoded + padding)
        assert len(key) == 44
        # Should not raise
        Fernet(key.encode())

    def test_generates_unique_keys(self):
        """Each call should produce a different key."""
        keys = {generate_master_key() for _ in range(10)}
        assert len(keys) == 10


# ── validate_master_key ──────────────────────────────────────────────────


class TestValidateMasterKey:
    def test_valid_key_returns_fernet(self, master_key):
        result = validate_master_key(master_key)
        assert isinstance(result, Fernet)

    def test_empty_string_raises(self):
        with pytest.raises(MasterKeyNotConfiguredError):
            validate_master_key("")

    def test_whitespace_only_raises(self):
        with pytest.raises(MasterKeyNotConfiguredError):
            validate_master_key("   ")

    def test_invalid_format_raises(self):
        with pytest.raises(InvalidMasterKeyError):
            validate_master_key("not-a-valid-fernet-key")

    def test_too_short_raises(self):
        with pytest.raises(InvalidMasterKeyError):
            validate_master_key("dG9vc2hvcnQ=")  # "tooshort" base64


# ── encrypt_credential / decrypt_credential ──────────────────────────────


class TestEncryptDecrypt:
    def test_roundtrip(self, master_key):
        """encrypt → decrypt should return the original plaintext."""
        plaintext = "sk-proj-abc123def456ghi789"
        ciphertext = encrypt_credential(plaintext, master_key)
        result = decrypt_credential(ciphertext, master_key)
        assert result == plaintext

    def test_encrypt_produces_different_tokens(self, master_key):
        """Two encryptions of the same plaintext should differ (random IV)."""
        plaintext = "sk-test-same-input"
        token_a = encrypt_credential(plaintext, master_key)
        token_b = encrypt_credential(plaintext, master_key)
        assert token_a != token_b

    def test_ciphertext_is_not_plaintext(self, master_key):
        """The encrypted output must not contain the plaintext."""
        plaintext = "sk-proj-secretkey12345"
        ciphertext = encrypt_credential(plaintext, master_key)
        assert plaintext not in ciphertext

    def test_decrypt_wrong_key_raises(self, master_key):
        """Decrypting with a different key should raise DecryptionError."""
        plaintext = "sk-test-wrongkey"
        ciphertext = encrypt_credential(plaintext, master_key)

        other_key = Fernet.generate_key().decode()
        with pytest.raises(DecryptionError):
            decrypt_credential(ciphertext, other_key)

    def test_decrypt_tampered_ciphertext_raises(self, master_key):
        """Modifying ciphertext should raise DecryptionError (HMAC check)."""
        ciphertext = encrypt_credential("sk-test-tamper", master_key)
        # Flip a character in the middle of the token
        tampered = ciphertext[:20] + ("A" if ciphertext[20] != "A" else "B") + ciphertext[21:]
        with pytest.raises(DecryptionError):
            decrypt_credential(tampered, master_key)

    def test_encrypt_empty_master_key_raises(self):
        with pytest.raises(MasterKeyNotConfiguredError):
            encrypt_credential("sk-test-nokey", "")

    def test_encrypt_invalid_master_key_raises(self):
        with pytest.raises(InvalidMasterKeyError):
            encrypt_credential("sk-test-badkey", "not-valid")

    def test_decrypt_empty_master_key_raises(self):
        with pytest.raises(MasterKeyNotConfiguredError):
            decrypt_credential("some-ciphertext", "")

    def test_unicode_credential(self, master_key):
        """Non-ASCII characters should roundtrip correctly."""
        plaintext = "sk-test-\u00fc\u00f1\u00ee\u00e7\u00f8\u00f0\u00e9-key"
        ciphertext = encrypt_credential(plaintext, master_key)
        assert decrypt_credential(ciphertext, master_key) == plaintext

    def test_long_credential(self, master_key):
        """Credentials up to 500 chars should roundtrip."""
        plaintext = "sk-" + "a" * 497
        assert len(plaintext) == 500
        ciphertext = encrypt_credential(plaintext, master_key)
        assert decrypt_credential(ciphertext, master_key) == plaintext


# ── re_encrypt_credential ────────────────────────────────────────────────


class TestReEncrypt:
    def test_re_encrypt_roundtrip(self, master_key):
        """Re-encrypt from old to new key; new key should decrypt."""
        new_key = Fernet.generate_key().decode()
        plaintext = "sk-test-rotation"

        old_ciphertext = encrypt_credential(plaintext, master_key)
        new_ciphertext = re_encrypt_credential(old_ciphertext, master_key, new_key)

        # New ciphertext should differ from old
        assert new_ciphertext != old_ciphertext

        # New key decrypts to original plaintext
        assert decrypt_credential(new_ciphertext, new_key) == plaintext

        # Old key cannot decrypt the new ciphertext
        with pytest.raises(DecryptionError):
            decrypt_credential(new_ciphertext, master_key)

    def test_re_encrypt_wrong_old_key_raises(self, master_key):
        """Re-encrypting with the wrong old key should raise DecryptionError."""
        new_key = Fernet.generate_key().decode()
        wrong_old_key = Fernet.generate_key().decode()

        ciphertext = encrypt_credential("sk-test-wrongold", master_key)
        with pytest.raises(DecryptionError):
            re_encrypt_credential(ciphertext, wrong_old_key, new_key)
