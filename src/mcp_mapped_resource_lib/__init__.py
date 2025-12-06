"""MCP Mapped Resource Library - Reusable utilities for blob storage in MCP servers.

This library provides utilities for MCP servers to handle binary blob transfers
through shared Docker volumes with unique resource identifiers, metadata tracking,
and lazy cleanup mechanisms.

Example:
    >>> from mcp_mapped_resource_lib import BlobStorage, maybe_cleanup_expired_blobs
    >>>
    >>> storage = BlobStorage(storage_root="/mnt/blob-storage")
    >>> result = storage.upload_blob(data=b"test", filename="test.txt")
    >>> print(result['blob_id'])
    blob://1733437200-a3f9d8c2b1e4f6a7.txt
    >>>
    >>> cleanup_result = maybe_cleanup_expired_blobs(
    ...     storage_root="/mnt/blob-storage",
    ...     ttl_hours=24
    ... )
"""

__version__ = "0.1.0"

# Core storage class
from .storage import BlobStorage

# Blob ID utilities
from .blob_id import (
    create_blob_id,
    parse_blob_id,
    strip_blob_protocol,
    validate_blob_id,
)

# Cleanup utilities
from .cleanup import (
    cleanup_expired_blobs,
    delete_blob_files,
    get_last_cleanup_timestamp,
    mark_cleanup_timestamp,
    maybe_cleanup_expired_blobs,
    scan_for_expired_blobs,
    should_run_cleanup,
)

# Exceptions
from .exceptions import (
    BlobNotFoundError,
    BlobSizeLimitError,
    BlobStorageError,
    InvalidBlobIdError,
    InvalidMimeTypeError,
    PathTraversalError,
    StorageInitializationError,
)

# Hash utilities
from .hash import calculate_sha256

# MIME utilities
from .mime import detect_mime_type, validate_mime_type

# Path utilities
from .path import (
    blob_id_to_path,
    ensure_storage_directories,
    get_metadata_path,
    get_shard_directories,
    sanitize_filename,
    validate_path_safety,
)

# Type definitions
from .types import (
    BlobIdComponents,
    BlobListResult,
    BlobMetadata,
    BlobStorageConfig,
    BlobUploadResult,
    CleanupResult,
)

__all__ = [
    # Version
    "__version__",
    # Core
    "BlobStorage",
    # Blob ID
    "create_blob_id",
    "parse_blob_id",
    "strip_blob_protocol",
    "validate_blob_id",
    # Cleanup
    "cleanup_expired_blobs",
    "delete_blob_files",
    "get_last_cleanup_timestamp",
    "mark_cleanup_timestamp",
    "maybe_cleanup_expired_blobs",
    "scan_for_expired_blobs",
    "should_run_cleanup",
    # Exceptions
    "BlobNotFoundError",
    "BlobSizeLimitError",
    "BlobStorageError",
    "InvalidBlobIdError",
    "InvalidMimeTypeError",
    "PathTraversalError",
    "StorageInitializationError",
    # Hash
    "calculate_sha256",
    # MIME
    "detect_mime_type",
    "validate_mime_type",
    # Path
    "blob_id_to_path",
    "ensure_storage_directories",
    "get_metadata_path",
    "get_shard_directories",
    "sanitize_filename",
    "validate_path_safety",
    # Types
    "BlobIdComponents",
    "BlobListResult",
    "BlobMetadata",
    "BlobStorageConfig",
    "BlobUploadResult",
    "CleanupResult",
]
