"""Storage backend factory - creates appropriate backend based on configuration."""

from common.config.settings import Settings
from common.storage.backend import StorageBackend
from common.storage.local_backend import LocalStorageBackend


def get_storage_backend(settings: Settings) -> StorageBackend:
    """Get storage backend instance based on configuration.

    Args:
        settings: Application settings

    Returns:
        StorageBackend instance (LocalStorageBackend or GCSStorageBackend)

    Raises:
        ValueError: If storage_backend setting is invalid
    """
    if settings.storage_backend == "local":
        return LocalStorageBackend(base_dir=settings.storage_local_base_dir)
    elif settings.storage_backend == "gcs":
        # Import GCS backend only when needed
        try:
            from common.storage.gcs_backend import GCSStorageBackend
        except ImportError as e:
            raise ImportError(
                "GCS storage backend requires gcloud-aio-storage. "
                "Install with: pip install gcloud-aio-storage"
            ) from e

        return GCSStorageBackend(
            bucket_name=settings.storage_gcs_bucket,
            project_id=settings.storage_gcs_project_id,
            credentials_path=settings.storage_gcs_credentials_path or None,
        )
    else:
        raise ValueError(
            f"Invalid storage_backend: {settings.storage_backend}. Must be 'local' or 'gcs'"
        )


# Made with Bob
