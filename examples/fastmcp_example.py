"""Example FastMCP server using mcp-mapped-resource-lib for blob storage.

This example demonstrates how to integrate the MCP Mapped Resource Library
into a FastMCP server for handling binary blob uploads, retrieval, and management.

Usage:
    python fastmcp_example.py
"""

import base64
import os

from fastmcp import FastMCP

from mcp_mapped_resource_lib import (
    BlobNotFoundError,
    BlobSizeLimitError,
    BlobStorage,
    InvalidBlobIdError,
    InvalidMimeTypeError,
    maybe_cleanup_expired_blobs,
)

# Initialize MCP server
mcp = FastMCP("blob-storage-example")

# Configure storage
STORAGE_ROOT = os.getenv("BLOB_STORAGE_ROOT", "/tmp/blob-storage")
MAX_SIZE_MB = int(os.getenv("BLOB_MAX_SIZE_MB", "100"))
DEFAULT_TTL_HOURS = int(os.getenv("BLOB_DEFAULT_TTL_HOURS", "24"))

# Initialize blob storage
storage = BlobStorage(
    storage_root=STORAGE_ROOT,
    max_size_mb=MAX_SIZE_MB,
    allowed_mime_types=None,  # Allow all MIME types
    enable_deduplication=True,
    default_ttl_hours=DEFAULT_TTL_HOURS,
)


@mcp.tool()
def upload_blob(
    data: str,
    filename: str,
    mime_type: str | None = None,
    tags: list[str] | None = None,
    ttl_hours: int | None = None,
) -> dict:
    """Upload a binary blob and receive a resource identifier.

    Args:
        data: Base64-encoded binary data
        filename: Original filename (used for extension and MIME detection)
        mime_type: Optional MIME type (auto-detected if not provided)
        tags: Optional list of tags for categorization
        ttl_hours: Optional time-to-live in hours (defaults to server setting)

    Returns:
        Dictionary containing:
        - blob_id: Unique identifier for the blob
        - size_bytes: Size of the uploaded blob in bytes
        - mime_type: MIME type of the blob
        - file_path: Filesystem path where the blob is stored
        - sha256: SHA256 hash of the blob content

    Example:
        >>> import base64
        >>> data = base64.b64encode(b"Hello, world!").decode()
        >>> result = upload_blob(data, "hello.txt", tags=["greeting"])
        >>> print(result['blob_id'])
        blob://1733437200-a3f9d8c2b1e4f6a7.txt
    """
    try:
        # Decode base64 data
        binary_data = base64.b64decode(data)

        # Upload to storage
        result = storage.upload_blob(
            data=binary_data,
            filename=filename,
            mime_type=mime_type,
            tags=tags,
            ttl_hours=ttl_hours,
        )

        # Trigger lazy cleanup after upload
        maybe_cleanup_expired_blobs(
            storage_root=STORAGE_ROOT,
            ttl_hours=DEFAULT_TTL_HOURS,
            cleanup_interval_minutes=5,
        )

        return dict(result)

    except BlobSizeLimitError as e:
        return {"error": f"Blob too large: {str(e)}"}
    except InvalidMimeTypeError as e:
        return {"error": f"Invalid MIME type: {str(e)}"}
    except Exception as e:
        return {"error": f"Upload failed: {str(e)}"}


@mcp.tool()
def get_blob_metadata(blob_id: str) -> dict:
    """Retrieve metadata for a blob without downloading its content.

    Args:
        blob_id: Blob identifier (e.g., "blob://1733437200-a3f9d8c2b1e4f6a7.txt")

    Returns:
        Dictionary containing blob metadata:
        - blob_id: Unique identifier
        - filename: Original filename
        - mime_type: MIME type
        - size_bytes: Size in bytes
        - created_at: ISO 8601 UTC timestamp
        - sha256: SHA256 hash
        - tags: List of tags (if any)
        - ttl_hours: Time-to-live in hours

    Example:
        >>> metadata = get_blob_metadata("blob://1733437200-a3f9d8c2b1e4f6a7.txt")
        >>> print(metadata['filename'])
        hello.txt
    """
    try:
        return dict(storage.get_metadata(blob_id))
    except InvalidBlobIdError as e:
        return {"error": f"Invalid blob ID: {str(e)}"}
    except BlobNotFoundError as e:
        return {"error": f"Blob not found: {str(e)}"}
    except Exception as e:
        return {"error": f"Failed to get metadata: {str(e)}"}


@mcp.tool()
def list_blobs(
    mime_type: str | None = None,
    tags: list[str] | None = None,
    created_after: str | None = None,
    created_before: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List blobs with optional filtering and pagination.

    Args:
        mime_type: Filter by MIME type (supports wildcards like "image/*")
        tags: Filter by tags (blob must have all specified tags)
        created_after: Filter by creation date (ISO 8601 format)
        created_before: Filter by creation date (ISO 8601 format)
        page: Page number (1-indexed)
        page_size: Number of items per page

    Returns:
        Dictionary containing:
        - blobs: List of blob metadata dictionaries
        - total: Total number of blobs matching the filter
        - page: Current page number
        - page_size: Number of items per page

    Example:
        >>> result = list_blobs(mime_type="image/*", page=1, page_size=10)
        >>> print(f"Found {result['total']} images")
        >>> for blob in result['blobs']:
        ...     print(blob['filename'])
    """
    try:
        result = storage.list_blobs(
            mime_type=mime_type,
            tags=tags,
            created_after=created_after,
            created_before=created_before,
            page=page,
            page_size=page_size,
        )

        # Trigger lazy cleanup
        maybe_cleanup_expired_blobs(
            storage_root=STORAGE_ROOT,
            ttl_hours=DEFAULT_TTL_HOURS,
            cleanup_interval_minutes=5,
        )

        return dict(result)

    except Exception as e:
        return {"error": f"Failed to list blobs: {str(e)}"}


@mcp.tool()
def delete_blob(blob_id: str) -> dict:
    """Delete a blob and its metadata.

    Args:
        blob_id: Blob identifier

    Returns:
        Dictionary with status and blob_id

    Example:
        >>> result = delete_blob("blob://1733437200-a3f9d8c2b1e4f6a7.txt")
        >>> print(result['status'])
        deleted
    """
    try:
        storage.delete_blob(blob_id)
        return {"status": "deleted", "blob_id": blob_id}
    except InvalidBlobIdError as e:
        return {"error": f"Invalid blob ID: {str(e)}"}
    except BlobNotFoundError as e:
        return {"error": f"Blob not found: {str(e)}"}
    except Exception as e:
        return {"error": f"Failed to delete blob: {str(e)}"}


@mcp.tool()
def get_blob_file_path(blob_id: str) -> dict:
    """Get the filesystem path for a blob (for local server access).

    This is useful when multiple MCP servers share the same Docker volume
    and need to access blobs directly from the filesystem.

    Args:
        blob_id: Blob identifier

    Returns:
        Dictionary containing:
        - blob_id: The blob identifier
        - file_path: Absolute filesystem path to the blob
        - exists: Whether the blob file exists

    Example:
        >>> result = get_blob_file_path("blob://1733437200-a3f9d8c2b1e4f6a7.txt")
        >>> if result['exists']:
        ...     with open(result['file_path'], 'rb') as f:
        ...         data = f.read()
    """
    try:
        file_path = storage.get_file_path(blob_id)
        return {"blob_id": blob_id, "file_path": str(file_path), "exists": True}
    except InvalidBlobIdError as e:
        return {"error": f"Invalid blob ID: {str(e)}", "exists": False}
    except BlobNotFoundError as e:
        return {"error": f"Blob not found: {str(e)}", "exists": False}
    except Exception as e:
        return {"error": f"Failed to get file path: {str(e)}", "exists": False}


@mcp.resource("blob://{blob_id}")
def get_blob_content(blob_id: str) -> str:
    """Retrieve blob content as base64-encoded data.

    This is an MCP resource that allows clients to fetch blob content
    by using the blob:// URI scheme.

    Args:
        blob_id: Blob identifier (without "blob://" prefix)

    Returns:
        Base64-encoded blob content

    Example:
        In an MCP client:
        >>> content = client.read_resource("blob://1733437200-a3f9d8c2b1e4f6a7.txt")
        >>> data = base64.b64decode(content)
    """
    try:
        # Add protocol prefix if not present
        if not blob_id.startswith("blob://"):
            blob_id = f"blob://{blob_id}"

        file_path = storage.get_file_path(blob_id)
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception as e:
        # Return error as base64
        return base64.b64encode(f"Error: {str(e)}".encode()).decode()


@mcp.prompt()
def blob_storage_info() -> str:
    """Get information about the blob storage system.

    Returns a summary of the storage configuration and current state.
    """
    from pathlib import Path

    storage_path = Path(STORAGE_ROOT)

    # Count blobs
    result = storage.list_blobs(page=1, page_size=1)
    total_blobs = result["total"]

    # Calculate storage size
    total_size = 0
    if storage_path.exists():
        for file_path in storage_path.rglob("*"):
            if file_path.is_file() and not file_path.name.endswith(".meta.json"):
                total_size += file_path.stat().st_size

    return f"""# Blob Storage Information

## Configuration
- Storage Root: {STORAGE_ROOT}
- Max Size: {MAX_SIZE_MB} MB
- Default TTL: {DEFAULT_TTL_HOURS} hours
- Deduplication: Enabled

## Current State
- Total Blobs: {total_blobs}
- Total Size: {total_size / (1024 * 1024):.2f} MB
- Storage Path Exists: {storage_path.exists()}
- Storage Path Writable: {storage_path.exists() and os.access(STORAGE_ROOT, os.W_OK)}

## Available Tools
- upload_blob: Upload binary data
- get_blob_metadata: Get blob metadata
- list_blobs: List blobs with filtering
- delete_blob: Delete a blob
- get_blob_file_path: Get filesystem path

## Available Resources
- blob://<blob_id>: Retrieve blob content
"""


if __name__ == "__main__":
    print(f"Starting blob storage MCP server...")
    print(f"Storage root: {STORAGE_ROOT}")
    print(f"Max size: {MAX_SIZE_MB} MB")
    print(f"Default TTL: {DEFAULT_TTL_HOURS} hours")

    mcp.run()
