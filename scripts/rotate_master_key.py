"""Rotate the Fernet master encryption key for all upstream credentials.

Usage:
    python -m scripts.rotate_master_key --old-key <old> --new-key <new> [--dry-run]

This script:
  1. Reads all active upstream credentials from the DB
  2. Decrypts each with the old key
  3. Re-encrypts each with the new key
  4. Updates the DB in a single transaction
  5. Reports the count of re-encrypted credentials

After running, update CREDENTIAL_ENCRYPTION_KEY in your environment to the new key.

Generate a new key:
    python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
"""

import argparse
import sys

from sqlalchemy.orm import Session

from common.crypto.fernet import re_encrypt_credential, validate_master_key
from common.models import CredentialStatus, UpstreamCredential
from common.models.base import SessionLocal


def rotate_all_credentials(
    db: Session,
    old_key: str,
    new_key: str,
    dry_run: bool = False,
) -> int:
    """Re-encrypt all active credentials from old_key to new_key.

    Returns the count of credentials re-encrypted.
    Rolls back on any failure (atomic operation).
    """
    # Validate both keys upfront before touching any data
    validate_master_key(old_key)
    validate_master_key(new_key)

    credentials = (
        db.query(UpstreamCredential)
        .filter(UpstreamCredential.status == CredentialStatus.active.value)
        .all()
    )

    count = 0
    for cred in credentials:
        new_ciphertext = re_encrypt_credential(cred.encrypted_key, old_key, new_key)
        if not dry_run:
            cred.encrypted_key = new_ciphertext
        count += 1

    if not dry_run:
        db.commit()

    return count


def main():
    parser = argparse.ArgumentParser(
        description="Rotate Fernet master encryption key for all upstream credentials"
    )
    parser.add_argument("--old-key", required=True, help="Current master key")
    parser.add_argument("--new-key", required=True, help="New master key to rotate to")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and count without writing changes",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        count = rotate_all_credentials(db, args.old_key, args.new_key, args.dry_run)
        action = "Would re-encrypt" if args.dry_run else "Re-encrypted"
        print(f"{action} {count} credential(s).")
        if not args.dry_run and count > 0:
            print("SUCCESS: Update CREDENTIAL_ENCRYPTION_KEY in your environment to the new key.")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
