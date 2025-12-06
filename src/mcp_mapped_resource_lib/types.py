"""Type definitions for the MCP Mapped Resource Library."""

from typing import TypedDict


class BlobMetadata(TypedDict, total=False):
    """Metadata for a stored blob.

    Attributes:
        blob_id: Unique identifier for the blob (e.g., "blob://1733437200-a3f9d8c2b1e4f6a7.png")
        filename: Original filename from upload
        mime_type: MIME type of the blob (e.g., "image/png")
        size_bytes: Size of the blob in bytes
        created_at: ISO 8601 UTC timestamp of creation (e.g., "2025-12-05T21:00:00Z")
        sha256: SHA256 hash of the blob content
        uploaded_by: Optional identifier of the uploader
        tags: Optional list of tags for categorization
        ttl_hours: Time-to-live in hours for cleanup purposes
    """
    blob_id: str
    filename: str
    mime_type: str
    size_bytes: int
    created_at: str
    sha256: str
    uploaded_by: str | None
    tags: list[str] | None
    ttl_hours: int


class BlobUploadResult(TypedDict):
    """Result of a successful blob upload.

    Attributes:
        blob_id: Unique identifier for the uploaded blob
        size_bytes: Size of the uploaded blob in bytes
        mime_type: MIME type of the uploaded blob
        file_path: Filesystem path where the blob is stored
        sha256: SHA256 hash of the blob content
    """
    blob_id: str
    size_bytes: int
    mime_type: str
    file_path: str
    sha256: str


class BlobListResult(TypedDict):
    """Result of a blob listing operation with pagination.

    Attributes:
        blobs: List of blob metadata matching the query
        total: Total number of blobs matching the query
        page: Current page number (1-indexed)
        page_size: Number of items per page
    """
    blobs: list[BlobMetadata]
    total: int
    page: int
    page_size: int


class BlobStorageConfig(TypedDict, total=False):
    """Configuration for blob storage.

    Attributes:
        storage_root: Root directory for blob storage
        max_size_mb: Maximum blob size in megabytes
        default_ttl_hours: Default time-to-live in hours for blobs
        allowed_mime_types: List of allowed MIME types (None = allow all)
        enable_deduplication: Whether to enable content-based deduplication
    """
    storage_root: str
    max_size_mb: int
    default_ttl_hours: int
    allowed_mime_types: list[str] | None
    enable_deduplication: bool


class CleanupResult(TypedDict):
    """Result of a cleanup operation.

    Attributes:
        deleted_count: Number of blobs deleted
        freed_bytes: Total bytes freed by deletion
        elapsed_seconds: Time taken for cleanup operation
    """
    deleted_count: int
    freed_bytes: int
    elapsed_seconds: float


class BlobIdComponents(TypedDict):
    """Components of a parsed blob ID.

    Attributes:
        timestamp: Unix timestamp from the blob ID
        hash: Hexadecimal hash component
        extension: Optional file extension
    """
    timestamp: int
    hash: str
    extension: str | None
