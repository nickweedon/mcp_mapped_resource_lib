"""Blob storage operations - upload, retrieve, list, delete."""

import json
from datetime import datetime, timezone
from pathlib import Path

from .blob_id import create_blob_id, validate_blob_id
from .exceptions import (
    BlobNotFoundError,
    BlobSizeLimitError,
    InvalidBlobIdError,
    InvalidMimeTypeError,
)
from .hash import calculate_sha256
from .mime import detect_mime_type, validate_mime_type
from .path import (
    blob_id_to_path,
    ensure_storage_directories,
    get_metadata_path,
    sanitize_filename,
    validate_path_safety,
)
from .types import BlobListResult, BlobMetadata, BlobUploadResult


class BlobStorage:
    """Blob storage manager for handling binary file uploads and retrieval.

    This class provides a high-level interface for storing and managing binary
    blobs (files) in a filesystem-based storage system with metadata tracking.

    Example:
        >>> storage = BlobStorage(storage_root="/mnt/blob-storage", max_size_mb=100)
        >>> result = storage.upload_blob(
        ...     data=b"test data",
        ...     filename="test.txt",
        ...     mime_type="text/plain"
        ... )
        >>> print(result['blob_id'])
        blob://1733437200-a3f9d8c2b1e4f6a7.txt
    """

    def __init__(
        self,
        storage_root: str,
        max_size_mb: int = 100,
        allowed_mime_types: list[str] | None = None,
        enable_deduplication: bool = True,
        default_ttl_hours: int = 24
    ):
        """Initialize blob storage.

        Args:
            storage_root: Root directory for blob storage
            max_size_mb: Maximum blob size in megabytes
            allowed_mime_types: List of allowed MIME types (None = allow all)
            enable_deduplication: Whether to enable SHA256-based deduplication
            default_ttl_hours: Default time-to-live for blobs in hours
        """
        self.storage_root = storage_root
        self.max_size_mb = max_size_mb
        self.allowed_mime_types = allowed_mime_types
        self.enable_deduplication = enable_deduplication
        self.default_ttl_hours = default_ttl_hours

        # Ensure storage directory exists
        ensure_storage_directories(storage_root)

    def upload_blob(
        self,
        data: bytes,
        filename: str,
        mime_type: str | None = None,
        tags: list[str] | None = None,
        ttl_hours: int | None = None,
        uploaded_by: str | None = None
    ) -> BlobUploadResult:
        """Upload a binary blob and receive a resource identifier.

        Args:
            data: Binary data to store
            filename: Original filename
            mime_type: MIME type (auto-detected if None)
            tags: Optional tags for categorization
            ttl_hours: Time-to-live in hours (uses default if None)
            uploaded_by: Optional identifier of uploader

        Returns:
            BlobUploadResult with blob_id, size, mime_type, file_path, sha256

        Raises:
            BlobSizeLimitError: If data exceeds max_size_mb
            InvalidMimeTypeError: If MIME type is not allowed

        Example:
            >>> result = storage.upload_blob(
            ...     data=b"test",
            ...     filename="test.txt",
            ...     tags=["example"]
            ... )
        """
        # Validate size
        size_bytes = len(data)
        max_bytes = self.max_size_mb * 1024 * 1024
        if size_bytes > max_bytes:
            raise BlobSizeLimitError(
                f"Blob size {size_bytes} bytes exceeds limit of {max_bytes} bytes"
            )

        # Detect/validate MIME type
        if mime_type is None:
            mime_type = detect_mime_type(data, filename)

        if not validate_mime_type(mime_type, self.allowed_mime_types):
            raise InvalidMimeTypeError(
                f"MIME type '{mime_type}' is not allowed"
            )

        # Calculate SHA256 hash
        sha256 = calculate_sha256(data)

        # Check for deduplication
        if self.enable_deduplication:
            existing_blob = self._find_blob_by_hash(sha256)
            if existing_blob:
                # Return existing blob instead of creating duplicate
                return BlobUploadResult(
                    blob_id=existing_blob['blob_id'],
                    size_bytes=existing_blob['size_bytes'],
                    mime_type=existing_blob['mime_type'],
                    file_path=str(blob_id_to_path(existing_blob['blob_id'], self.storage_root)),
                    sha256=existing_blob['sha256']
                )

        # Extract file extension
        extension = None
        if '.' in filename:
            extension = filename.rsplit('.', 1)[1]

        # Generate blob ID
        blob_id = create_blob_id(extension)

        # Get file paths
        blob_path = blob_id_to_path(blob_id, self.storage_root)
        meta_path = get_metadata_path(blob_id, self.storage_root)

        # Ensure parent directory exists
        blob_path.parent.mkdir(parents=True, exist_ok=True)

        # Write blob data
        with open(blob_path, 'wb') as f:
            f.write(data)

        # Create metadata
        metadata: BlobMetadata = {
            'blob_id': blob_id,
            'filename': sanitize_filename(filename),
            'mime_type': mime_type,
            'size_bytes': size_bytes,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'sha256': sha256,
            'uploaded_by': uploaded_by,
            'tags': tags,
            'ttl_hours': ttl_hours or self.default_ttl_hours
        }

        # Write metadata
        with open(meta_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        return BlobUploadResult(
            blob_id=blob_id,
            size_bytes=size_bytes,
            mime_type=mime_type,
            file_path=str(blob_path),
            sha256=sha256
        )

    def get_metadata(self, blob_id: str) -> BlobMetadata:
        """Retrieve metadata for a blob.

        Args:
            blob_id: Blob identifier

        Returns:
            BlobMetadata dictionary

        Raises:
            InvalidBlobIdError: If blob_id format is invalid
            BlobNotFoundError: If blob doesn't exist

        Example:
            >>> metadata = storage.get_metadata("blob://1733437200-a3f9d8c2b1e4f6a7.png")
            >>> print(metadata['filename'])
        """
        if not validate_blob_id(blob_id if blob_id.startswith("blob://") else f"blob://{blob_id}"):
            raise InvalidBlobIdError(f"Invalid blob ID: {blob_id}")

        meta_path = get_metadata_path(blob_id, self.storage_root)

        if not meta_path.exists():
            raise BlobNotFoundError(f"Blob not found: {blob_id}")

        with open(meta_path) as f:
            metadata: BlobMetadata = json.load(f)
            return metadata

    def list_blobs(
        self,
        mime_type: str | None = None,
        tags: list[str] | None = None,
        created_after: str | None = None,
        created_before: str | None = None,
        page: int = 1,
        page_size: int = 20
    ) -> BlobListResult:
        """List blobs with optional filtering and pagination.

        Args:
            mime_type: Filter by MIME type (supports wildcards like "image/*")
            tags: Filter by tags (blob must have all specified tags)
            created_after: Filter by creation date (ISO 8601 format)
            created_before: Filter by creation date (ISO 8601 format)
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            BlobListResult with blobs, total, page, page_size

        Example:
            >>> result = storage.list_blobs(mime_type="image/*", page=1, page_size=10)
            >>> print(f"Found {result['total']} images")
        """
        from .path import get_shard_directories

        all_blobs: list[BlobMetadata] = []

        # Scan all shard directories
        shard_dirs = get_shard_directories(self.storage_root)

        for shard_dir in shard_dirs:
            for meta_file in shard_dir.glob("*.meta.json"):
                try:
                    with open(meta_file) as f:
                        metadata: BlobMetadata = json.load(f)

                    # Apply filters
                    if mime_type and not self._matches_mime_filter(metadata.get('mime_type', ''), mime_type):
                        continue

                    if tags and not self._matches_tags_filter(metadata.get('tags'), tags):
                        continue

                    if created_after:
                        created_at = datetime.fromisoformat(metadata.get('created_at', ''))
                        filter_date = datetime.fromisoformat(created_after)
                        if created_at < filter_date:
                            continue

                    if created_before:
                        created_at = datetime.fromisoformat(metadata.get('created_at', ''))
                        filter_date = datetime.fromisoformat(created_before)
                        if created_at > filter_date:
                            continue

                    all_blobs.append(metadata)

                except Exception:
                    # Skip malformed metadata files
                    continue

        # Sort by creation date (newest first)
        all_blobs.sort(key=lambda b: b.get('created_at', ''), reverse=True)

        # Pagination
        total = len(all_blobs)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_blobs = all_blobs[start_idx:end_idx]

        return BlobListResult(
            blobs=page_blobs,
            total=total,
            page=page,
            page_size=page_size
        )

    def delete_blob(self, blob_id: str) -> None:
        """Delete a blob and its metadata.

        Args:
            blob_id: Blob identifier

        Raises:
            InvalidBlobIdError: If blob_id format is invalid
            BlobNotFoundError: If blob doesn't exist

        Example:
            >>> storage.delete_blob("blob://1733437200-a3f9d8c2b1e4f6a7.png")
        """
        if not validate_blob_id(blob_id if blob_id.startswith("blob://") else f"blob://{blob_id}"):
            raise InvalidBlobIdError(f"Invalid blob ID: {blob_id}")

        blob_path = blob_id_to_path(blob_id, self.storage_root)
        meta_path = get_metadata_path(blob_id, self.storage_root)

        if not blob_path.exists() and not meta_path.exists():
            raise BlobNotFoundError(f"Blob not found: {blob_id}")

        # Delete files
        if blob_path.exists():
            blob_path.unlink()

        if meta_path.exists():
            meta_path.unlink()

        # Try to remove empty parent directories
        try:
            if blob_path.parent.exists() and not any(blob_path.parent.iterdir()):
                blob_path.parent.rmdir()

            if blob_path.parent.parent.exists() and not any(blob_path.parent.parent.iterdir()):
                blob_path.parent.parent.rmdir()
        except Exception:
            pass

    def get_file_path(self, blob_id: str) -> Path:
        """Get the filesystem path for a blob.

        Args:
            blob_id: Blob identifier

        Returns:
            Path object pointing to the blob file

        Raises:
            InvalidBlobIdError: If blob_id format is invalid
            BlobNotFoundError: If blob doesn't exist

        Example:
            >>> path = storage.get_file_path("blob://1733437200-a3f9d8c2b1e4f6a7.png")
            >>> with open(path, 'rb') as f:
            ...     data = f.read()
        """
        if not validate_blob_id(blob_id if blob_id.startswith("blob://") else f"blob://{blob_id}"):
            raise InvalidBlobIdError(f"Invalid blob ID: {blob_id}")

        blob_path = blob_id_to_path(blob_id, self.storage_root)

        if not blob_path.exists():
            raise BlobNotFoundError(f"Blob not found: {blob_id}")

        # Validate path safety
        if not validate_path_safety(blob_path, self.storage_root):
            raise InvalidBlobIdError(f"Path traversal detected: {blob_id}")

        return blob_path

    def _find_blob_by_hash(self, sha256: str) -> BlobMetadata | None:
        """Find a blob by its SHA256 hash (for deduplication).

        Args:
            sha256: SHA256 hash to search for

        Returns:
            BlobMetadata if found, None otherwise
        """
        from .path import get_shard_directories

        shard_dirs = get_shard_directories(self.storage_root)

        for shard_dir in shard_dirs:
            for meta_file in shard_dir.glob("*.meta.json"):
                try:
                    with open(meta_file) as f:
                        metadata: BlobMetadata = json.load(f)

                    if metadata.get('sha256') == sha256:
                        return metadata

                except Exception:
                    continue

        return None

    def _matches_mime_filter(self, mime_type: str, filter_mime: str) -> bool:
        """Check if MIME type matches filter (supports wildcards).

        Args:
            mime_type: MIME type to check
            filter_mime: Filter pattern (e.g., "image/*")

        Returns:
            True if matches, False otherwise
        """
        if filter_mime.endswith("/*"):
            prefix = filter_mime[:-2]
            return mime_type.startswith(prefix + "/")
        return mime_type == filter_mime

    def _matches_tags_filter(
        self,
        blob_tags: list[str] | None,
        filter_tags: list[str]
    ) -> bool:
        """Check if blob has all required tags.

        Args:
            blob_tags: Tags associated with the blob
            filter_tags: Required tags

        Returns:
            True if blob has all required tags, False otherwise
        """
        if not blob_tags:
            return False

        return all(tag in blob_tags for tag in filter_tags)
