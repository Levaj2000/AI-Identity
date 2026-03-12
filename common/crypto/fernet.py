"""Fernet encryption for upstream API credentials.

Security properties:
  - AES-128-CBC encryption with HMAC-SHA256 authentication (via Fernet)
  - Built-in timestamp in every token (enables age-based verification)
  - Master key from CREDENTIAL_ENCRYPTION_KEY env var
  - All functions are stateless — key is passed as a parameter
  - Plaintext is never logged or persisted
"""

import logging

from cryptography.fernet import Fernet, InvalidToken

from common.crypto.exceptions import (
    DecryptionError,
    InvalidMasterKeyError,
    MasterKeyNotConfiguredError,
)

logger = logging.getLogger("ai_identity.crypto")


def validate_master_key(key: str) -> Fernet:
    """Validate and return a Fernet instance for the given key.

    Args:
        key: URL-safe base64-encoded 32-byte Fernet key.

    Returns:
        Fernet instance ready for encrypt/decrypt.

    Raises:
        MasterKeyNotConfiguredError: If key is empty/missing.
        InvalidMasterKeyError: If key is not a valid Fernet key.
    """
    if not key or not key.strip():
        raise MasterKeyNotConfiguredError(
            "CREDENTIAL_ENCRYPTION_KEY is not configured. "
            "Generate one with: python -c "
            "'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )
    try:
        return Fernet(key.encode())
    except (ValueError, Exception) as e:
        raise InvalidMasterKeyError(
            f"CREDENTIAL_ENCRYPTION_KEY is not a valid Fernet key: {e}"
        ) from e


def generate_master_key() -> str:
    """Generate a new Fernet master key (URL-safe base64, 32 bytes).

    Returns:
        String suitable for CREDENTIAL_ENCRYPTION_KEY env var.
    """
    return Fernet.generate_key().decode()


def encrypt_credential(plaintext: str, master_key: str) -> str:
    """Encrypt an upstream API credential for storage.

    Args:
        plaintext: The raw API key (e.g., "sk-abc123...").
        master_key: The CREDENTIAL_ENCRYPTION_KEY value.

    Returns:
        Fernet token as a string (URL-safe base64 ciphertext).

    Raises:
        MasterKeyNotConfiguredError: If master_key is empty.
        InvalidMasterKeyError: If master_key is not a valid Fernet key.
    """
    f = validate_master_key(master_key)
    token = f.encrypt(plaintext.encode())
    return token.decode()


def decrypt_credential(ciphertext: str, master_key: str) -> str:
    """Decrypt an upstream API credential from storage.

    Args:
        ciphertext: Fernet token from the database.
        master_key: The CREDENTIAL_ENCRYPTION_KEY value.

    Returns:
        Plaintext API key (only held in memory, never persisted).

    Raises:
        MasterKeyNotConfiguredError: If master_key is empty.
        InvalidMasterKeyError: If master_key is not a valid Fernet key.
        DecryptionError: If ciphertext is invalid, tampered, or wrong key.
    """
    f = validate_master_key(master_key)
    try:
        plaintext_bytes = f.decrypt(ciphertext.encode())
        return plaintext_bytes.decode()
    except InvalidToken as e:
        raise DecryptionError(
            "Failed to decrypt credential — wrong key, corrupted, or tampered ciphertext"
        ) from e


def re_encrypt_credential(ciphertext: str, old_master_key: str, new_master_key: str) -> str:
    """Re-encrypt a credential from old key to new key (for rotation).

    Args:
        ciphertext: Existing Fernet token encrypted with old_master_key.
        old_master_key: Current CREDENTIAL_ENCRYPTION_KEY.
        new_master_key: New CREDENTIAL_ENCRYPTION_KEY to rotate to.

    Returns:
        New Fernet token encrypted with new_master_key.

    Raises:
        DecryptionError: If old key cannot decrypt.
        InvalidMasterKeyError: If either key is invalid.
    """
    plaintext = decrypt_credential(ciphertext, old_master_key)
    return encrypt_credential(plaintext, new_master_key)
