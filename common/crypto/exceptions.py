"""Crypto-specific exceptions for upstream credential encryption."""


class EncryptionError(Exception):
    """Raised when encryption or decryption fails."""


class MasterKeyNotConfiguredError(EncryptionError):
    """Raised when CREDENTIAL_ENCRYPTION_KEY is empty or missing."""


class InvalidMasterKeyError(EncryptionError):
    """Raised when the master key is not a valid Fernet key."""


class DecryptionError(EncryptionError):
    """Raised when ciphertext cannot be decrypted (wrong key, tampered, etc.)."""
