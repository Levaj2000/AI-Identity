"""Fernet encryption utilities for upstream API credential storage."""

from common.crypto.exceptions import (
    DecryptionError,
    EncryptionError,
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

__all__ = [
    "DecryptionError",
    "EncryptionError",
    "InvalidMasterKeyError",
    "MasterKeyNotConfiguredError",
    "decrypt_credential",
    "encrypt_credential",
    "generate_master_key",
    "re_encrypt_credential",
    "validate_master_key",
]
