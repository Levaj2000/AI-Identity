"""Abstract storage backend interface."""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path


class StorageBackend(ABC):
    """Abstract storage backend for file operations.

    Implementations:
    - LocalStorageBackend: Stores files on local disk (dev/test)
    - GCSStorageBackend: Stores files in Google Cloud Storage (production)
    """

    @abstractmethod
    async def upload(
        self,
        source_path: Path,
        destination_path: str,
        content_type: str,
    ) -> str:
        """Upload file to storage.

        Args:
            source_path: Local file path to upload
            destination_path: Storage path (e.g., "org_id/tickets/file.png")
            content_type: MIME type of the file

        Returns:
            Storage path where file was uploaded

        Raises:
            FileNotFoundError: If source_path doesn't exist
            IOError: If upload fails
        """
        pass

    @abstractmethod
    async def download(
        self,
        storage_path: str,
        destination_path: Path,
    ) -> None:
        """Download file from storage to local path.

        Args:
            storage_path: Storage path to download from
            destination_path: Local path to save file

        Raises:
            FileNotFoundError: If storage_path doesn't exist
            IOError: If download fails
        """
        pass

    @abstractmethod
    async def generate_signed_url(
        self,
        storage_path: str,
        expiration: timedelta = timedelta(hours=1),
    ) -> tuple[str, datetime]:
        """Generate signed URL for file access.

        Args:
            storage_path: Storage path to generate URL for
            expiration: How long the URL should be valid

        Returns:
            Tuple of (signed_url, expires_at_datetime)

        Raises:
            FileNotFoundError: If storage_path doesn't exist
        """
        pass

    @abstractmethod
    async def delete(self, storage_path: str) -> None:
        """Delete file from storage.

        Args:
            storage_path: Storage path to delete

        Raises:
            FileNotFoundError: If storage_path doesn't exist
            IOError: If delete fails
        """
        pass

    @abstractmethod
    async def exists(self, storage_path: str) -> bool:
        """Check if file exists in storage.

        Args:
            storage_path: Storage path to check

        Returns:
            True if file exists, False otherwise
        """
        pass


# Made with Bob
