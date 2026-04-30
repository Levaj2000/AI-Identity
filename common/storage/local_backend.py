"""Local filesystem storage backend for development and testing."""

import hashlib
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

from common.storage.backend import StorageBackend


class LocalStorageBackend(StorageBackend):
    """Store files on local filesystem.

    Used for development and testing. Signed URLs are authenticated API
    endpoints that serve files from disk.
    """

    def __init__(self, base_dir: str | Path):
        """Initialize local storage backend.

        Args:
            base_dir: Base directory for file storage
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_full_path(self, storage_path: str) -> Path:
        """Convert storage path to full filesystem path."""
        return self.base_dir / storage_path

    async def upload(
        self,
        source_path: Path,
        destination_path: str,
        content_type: str,
    ) -> str:
        """Upload file to local storage."""
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        dest = self._get_full_path(destination_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Copy file
        shutil.copy2(source_path, dest)

        return destination_path

    async def download(
        self,
        storage_path: str,
        destination_path: Path,
    ) -> None:
        """Download file from local storage."""
        source = self._get_full_path(storage_path)

        if not source.exists():
            raise FileNotFoundError(f"Storage file not found: {storage_path}")

        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination_path)

    async def generate_signed_url(
        self,
        storage_path: str,
        expiration: timedelta = timedelta(hours=1),
    ) -> tuple[str, datetime]:
        """Generate signed URL for local storage.

        For local storage, this returns an authenticated API endpoint URL
        that will serve the file. The actual authentication is handled by
        the API endpoint, not by the URL itself.
        """
        if not await self.exists(storage_path):
            raise FileNotFoundError(f"Storage file not found: {storage_path}")

        # Generate a simple token based on storage path and expiration
        # This is NOT cryptographically secure - it's just for dev/test
        expires_at = datetime.now(UTC) + expiration
        token = hashlib.sha256(f"{storage_path}:{expires_at.isoformat()}".encode()).hexdigest()[:16]

        # In production, this would be replaced by the API endpoint
        # For now, return a placeholder URL
        url = f"/api/v1/storage/download/{token}/{storage_path}"

        return url, expires_at

    async def delete(self, storage_path: str) -> None:
        """Delete file from local storage."""
        file_path = self._get_full_path(storage_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Storage file not found: {storage_path}")

        file_path.unlink()

        # Clean up empty parent directories
        try:
            parent = file_path.parent
            while parent != self.base_dir and not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent
        except (OSError, RuntimeError):
            # Directory not empty or other error - ignore
            pass

    async def exists(self, storage_path: str) -> bool:
        """Check if file exists in local storage."""
        return self._get_full_path(storage_path).exists()


# Made with Bob
