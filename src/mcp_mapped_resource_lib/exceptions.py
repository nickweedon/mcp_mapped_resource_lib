"""Custom exceptions for the MCP Mapped Resource Library."""


class BlobStorageError(Exception):
    """Base exception for all blob storage errors."""
    pass


class InvalidBlobIdError(BlobStorageError):
    """Raised when a blob ID is invalid or malformed."""
    pass


class BlobNotFoundError(BlobStorageError):
    """Raised when a requested blob does not exist."""
    pass


class BlobSizeLimitError(BlobStorageError):
    """Raised when a blob exceeds the maximum allowed size."""
    pass


class InvalidMimeTypeError(BlobStorageError):
    """Raised when a blob's MIME type is not allowed."""
    pass


class PathTraversalError(BlobStorageError):
    """Raised when a path traversal attempt is detected."""
    pass


class StorageInitializationError(BlobStorageError):
    """Raised when storage initialization fails."""
    pass
