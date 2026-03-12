"""Generate a cryptographically secure INTERNAL_SERVICE_KEY.

Usage:
    python scripts/generate_internal_key.py

Output:
    A 64-byte URL-safe base64-encoded random string suitable for the
    INTERNAL_SERVICE_KEY environment variable.
"""

import secrets

if __name__ == "__main__":
    key = secrets.token_urlsafe(64)
    print(f"INTERNAL_SERVICE_KEY={key}")
    print(f"\nKey length: {len(key)} characters")
    print("Add this to your .env file for both API and Gateway services.")
