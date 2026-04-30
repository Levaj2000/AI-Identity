"""Google Cloud Storage backend for production."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import aiofiles
from gcloud.aio.storage import Storage

from common.storage.backend import StorageBackend


class GCSStorageBackend(StorageBackend):
    """Store files in Google Cloud Storage.

    Used in production. Provides true signed URLs for direct client downloads.
    """

    def __init__(self, bucket_name: str, project_id: str, credentials_path: str | None = None):
        """Initialize GCS storage backend.

        Args:
            bucket_name: GCS bucket name
            project_id: GCP project ID
            credentials_path: Path to service account JSON (optional, uses ADC if not provided)
        """
        self.bucket_name = bucket_name
        self.project_id = project_id
        self.credentials_path = credentials_path
        self._client = None

    async def _get_client(self) -> Storage:
        """Get or create GCS client."""
        if self._client is None:
            if self.credentials_path:
                # Load service account credentials
                with open(self.credentials_path) as f:
                    service_file = json.load(f)
                self._client = Storage(service_file=service_file)
            else:
                # Use Application Default Credentials
                self._client = Storage(project=self.project_id)
        return self._client

    async def upload(
        self,
        source_path: Path,
        destination_path: str,
        content_type: str,
    ) -> str:
        """Upload file to GCS."""
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        client = await self._get_client()

        # Read file asynchronously to avoid blocking event loop
        async with aiofiles.open(source_path, "rb") as f:
            data = await f.read()

        # Upload to GCS
        await client.upload(
            self.bucket_name,
            destination_path,
            data,
            content_type=content_type,
        )

        return destination_path

    async def download(
        self,
        storage_path: str,
        destination_path: Path,
    ) -> None:
        """Download file from GCS."""
        client = await self._get_client()

        # Download from GCS
        data = await client.download(self.bucket_name, storage_path)

        # Write file asynchronously
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(destination_path, "wb") as f:
            await f.write(data)

    async def generate_signed_url(
        self,
        storage_path: str,
        expiration: timedelta = timedelta(hours=1),
    ) -> tuple[str, datetime]:
        """Generate signed URL for GCS object.

        Returns a time-limited URL that allows direct download from GCS
        without authentication.
        """
        client = await self._get_client()

        # Check if object exists
        if not await self.exists(storage_path):
            raise FileNotFoundError(f"Storage file not found: {storage_path}")

        # Calculate expiration
        expires_at = datetime.now(UTC) + expiration
        expiration_seconds = int(expiration.total_seconds())

        # Generate signed URL
        signed_url = await client.get_signed_url(
            self.bucket_name,
            storage_path,
            expiration=expiration_seconds,
            method="GET",
        )

        return signed_url, expires_at

    async def delete(self, storage_path: str) -> None:
        """Delete file from GCS."""
        client = await self._get_client()

        # Check if object exists
        if not await self.exists(storage_path):
            raise FileNotFoundError(f"Storage file not found: {storage_path}")

        # Delete from GCS
        await client.delete(self.bucket_name, storage_path)

    async def exists(self, storage_path: str) -> bool:
        """Check if file exists in GCS."""
        client = await self._get_client()

        try:
            # Try to get object metadata
            await client.download_metadata(self.bucket_name, storage_path)
            return True
        except Exception:
            return False


# Made with Bob
