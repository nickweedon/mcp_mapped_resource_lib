# Integration Guide for MCP Servers

This guide shows how to integrate the MCP Mapped Resource Library into your MCP servers for handling binary blob transfers through shared Docker volumes.

## Important: Use Tools, Not Resource Endpoints

**Note**: This library uses MCP **tools** for blob retrieval instead of MCP **resource endpoints** (e.g., `@mcp.resource("blob://{blob_id}")`). Template resources are not well-supported by some MCP clients and can cause compatibility issues. The tool-based approach provides better compatibility across all MCP clients.

For blob retrieval, use the `get_blob_content()` tool which returns base64-encoded data, or `get_blob_file_path()` for direct filesystem access when using shared Docker volumes.

## Table of Contents

- [Quick Start](#quick-start)
- [FastMCP Integration](#fastmcp-integration)
- [Docker Volume Configuration](#docker-volume-configuration)
- [Complete Workflow Examples](#complete-workflow-examples)
- [Security Best Practices](#security-best-practices)
- [Performance Optimization](#performance-optimization)
- [Troubleshooting](#troubleshooting)

## Quick Start

### 1. Install the Library

```bash
pip install mcp-mapped-resource-lib
```

### 2. Initialize BlobStorage

```python
from mcp_mapped_resource_lib import BlobStorage

storage = BlobStorage(
    storage_root="/mnt/blob-storage",
    max_size_mb=100,
    allowed_mime_types=["image/*", "application/pdf"],
    enable_deduplication=True
)
```

### 3. Use in Your MCP Server

```python
from fastmcp import FastMCP
import base64

mcp = FastMCP("my-server")

@mcp.tool()
def upload_file(data: str, filename: str) -> dict:
    """Upload a file and get a blob ID."""
    binary_data = base64.b64decode(data)
    result = storage.upload_blob(data=binary_data, filename=filename)
    return result
```

## FastMCP Integration

### Complete Server Example

```python
from mcp_mapped_resource_lib import (
    BlobStorage,
    maybe_cleanup_expired_blobs,
    BlobNotFoundError,
    InvalidBlobIdError
)
from fastmcp import FastMCP
import base64

# Initialize MCP server
mcp = FastMCP("blob-storage-server")

# Initialize blob storage
storage = BlobStorage(
    storage_root="/mnt/blob-storage",
    max_size_mb=100,
    allowed_mime_types=None,  # Allow all types
    enable_deduplication=True,
    default_ttl_hours=24
)

@mcp.tool()
def upload_blob(
    data: str,  # base64-encoded binary data
    filename: str,
    mime_type: str | None = None,
    tags: list[str] | None = None,
    ttl_hours: int = 24
) -> dict:
    """Upload a binary blob and receive a resource identifier.

    Args:
        data: Base64-encoded binary data
        filename: Original filename
        mime_type: MIME type (auto-detected if None)
        tags: Optional tags for categorization
        ttl_hours: Time-to-live in hours

    Returns:
        Dictionary with blob_id, size_bytes, mime_type, file_path, sha256
    """
    # Decode base64 data
    binary_data = base64.b64decode(data)

    # Upload to storage
    result = storage.upload_blob(
        data=binary_data,
        filename=filename,
        mime_type=mime_type,
        tags=tags,
        ttl_hours=ttl_hours
    )

    # Trigger lazy cleanup after upload
    maybe_cleanup_expired_blobs(
        storage_root="/mnt/blob-storage",
        ttl_hours=24,
        cleanup_interval_minutes=5
    )

    return result


@mcp.tool()
def get_blob_metadata(blob_id: str) -> dict:
    """Retrieve metadata for a blob.

    Args:
        blob_id: Blob identifier

    Returns:
        Dictionary with blob metadata
    """
    try:
        return storage.get_metadata(blob_id)
    except (InvalidBlobIdError, BlobNotFoundError) as e:
        return {"error": str(e)}


@mcp.tool()
def list_blobs(
    mime_type: str | None = None,
    tags: list[str] | None = None,
    page: int = 1,
    page_size: int = 20
) -> dict:
    """List blobs with optional filtering.

    Args:
        mime_type: Filter by MIME type (supports wildcards)
        tags: Filter by tags
        page: Page number (1-indexed)
        page_size: Items per page

    Returns:
        Dictionary with blobs, total, page, page_size
    """
    result = storage.list_blobs(
        mime_type=mime_type,
        tags=tags,
        page=page,
        page_size=page_size
    )

    # Trigger lazy cleanup
    maybe_cleanup_expired_blobs(
        storage_root="/mnt/blob-storage",
        ttl_hours=24,
        cleanup_interval_minutes=5
    )

    return result


@mcp.tool()
def delete_blob(blob_id: str) -> dict:
    """Delete a blob and its metadata.

    Args:
        blob_id: Blob identifier

    Returns:
        Dictionary with status
    """
    try:
        storage.delete_blob(blob_id)
        return {"status": "deleted", "blob_id": blob_id}
    except (InvalidBlobIdError, BlobNotFoundError) as e:
        return {"error": str(e)}


@mcp.tool()
def get_blob_content(blob_id: str) -> str:
    """Retrieve blob content as base64-encoded data.

    Note: This is implemented as a tool instead of an MCP resource endpoint
    because template resources (blob://{blob_id}) are not well-supported
    by all MCP clients.

    Args:
        blob_id: Blob identifier

    Returns:
        Base64-encoded blob content
    """
    try:
        file_path = storage.get_file_path(blob_id)
        with open(file_path, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    except (InvalidBlobIdError, BlobNotFoundError) as e:
        return f"Error: {str(e)}"


@mcp.tool()
def get_blob_file_path(blob_id: str) -> dict:
    """Get filesystem path for direct blob access.

    Useful when multiple MCP servers share the same Docker volume
    and need to access blobs directly from the filesystem.

    Args:
        blob_id: Blob identifier

    Returns:
        Dictionary with blob_id, file_path, and exists flag
    """
    try:
        file_path = storage.get_file_path(blob_id)
        return {"blob_id": blob_id, "file_path": str(file_path), "exists": True}
    except (InvalidBlobIdError, BlobNotFoundError) as e:
        return {"error": str(e), "exists": False}


if __name__ == "__main__":
    mcp.run()
```

## Docker Volume Configuration

### Single Server Setup

```yaml
# docker-compose.yml
services:
  blob-server:
    build: .
    volumes:
      - blob-storage:/mnt/blob-storage
    environment:
      - BLOB_STORAGE_ROOT=/mnt/blob-storage
      - BLOB_MAX_SIZE_MB=100
      - BLOB_DEFAULT_TTL_HOURS=24
    ports:
      - "8000:8000"

volumes:
  blob-storage:
    driver: local
```

### Multi-Server Setup (Shared Volume)

```yaml
# docker-compose.yml
services:
  # Server that uploads blobs (read-write)
  blob-upload-server:
    build: .
    volumes:
      - blob-storage:/mnt/blob-storage
    environment:
      - BLOB_STORAGE_ROOT=/mnt/blob-storage

  # Server that reads blobs (read-only recommended)
  blob-consumer-server-1:
    build: .
    volumes:
      - blob-storage:/mnt/blob-storage:ro
    environment:
      - BLOB_STORAGE_ROOT=/mnt/blob-storage

  # Another consumer server
  blob-consumer-server-2:
    build: .
    volumes:
      - blob-storage:/mnt/blob-storage:ro
    environment:
      - BLOB_STORAGE_ROOT=/mnt/blob-storage

volumes:
  blob-storage:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: ${BLOB_STORAGE_HOST_PATH:-./blob-storage-data}
```

### Accessing Blobs from Consumer Servers

```python
# In consumer MCP servers (read-only access)
from mcp_mapped_resource_lib import blob_id_to_path
from pathlib import Path

# Translate blob ID to filesystem path
blob_id = "blob://1733437200-a3f9d8c2b1e4f6a7.png"
file_path = blob_id_to_path(blob_id, "/mnt/blob-storage")

# Read directly from shared volume
if file_path.exists():
    with open(file_path, 'rb') as f:
        data = f.read()
else:
    print("Blob not found")
```

## Complete Workflow Examples

### Example 1: Image Processing Pipeline

```python
from mcp_mapped_resource_lib import BlobStorage, blob_id_to_path
from PIL import Image
import base64

storage = BlobStorage(
    storage_root="/mnt/blob-storage",
    allowed_mime_types=["image/*"]
)

# Server A: Upload image
def upload_image(image_data: bytes, filename: str) -> str:
    """Upload image and return blob ID."""
    result = storage.upload_blob(
        data=image_data,
        filename=filename,
        tags=["image", "original"]
    )
    return result['blob_id']

# Server B: Process image (read-only volume)
def process_image(blob_id: str) -> bytes:
    """Process image from shared volume."""
    # Get file path
    file_path = blob_id_to_path(blob_id, "/mnt/blob-storage")

    # Open with PIL
    with Image.open(file_path) as img:
        # Process (e.g., resize)
        img_resized = img.resize((800, 600))

        # Save processed version
        from io import BytesIO
        buffer = BytesIO()
        img_resized.save(buffer, format=img.format)
        return buffer.getvalue()

# Server C: Store processed image
def store_processed(original_blob_id: str, processed_data: bytes) -> str:
    """Store processed image."""
    # Get original metadata
    metadata = storage.get_metadata(original_blob_id)

    # Upload processed version
    result = storage.upload_blob(
        data=processed_data,
        filename=f"processed_{metadata['filename']}",
        tags=["image", "processed"]
    )
    return result['blob_id']
```

### Example 2: Document Upload and Retrieval

```python
@mcp.tool()
def upload_document(
    document_data: str,  # base64
    filename: str,
    document_type: str,
    project_id: str
) -> dict:
    """Upload a document with project metadata."""
    binary_data = base64.b64decode(document_data)

    result = storage.upload_blob(
        data=binary_data,
        filename=filename,
        tags=[document_type, f"project:{project_id}"],
        ttl_hours=720  # 30 days
    )

    return {
        "blob_id": result['blob_id'],
        "project_id": project_id,
        "document_type": document_type,
        "size_bytes": result['size_bytes']
    }


@mcp.tool()
def get_project_documents(project_id: str) -> dict:
    """Get all documents for a project."""
    result = storage.list_blobs(
        tags=[f"project:{project_id}"],
        page=1,
        page_size=100
    )

    return {
        "project_id": project_id,
        "document_count": result['total'],
        "documents": [
            {
                "blob_id": blob['blob_id'],
                "filename": blob['filename'],
                "size_bytes": blob['size_bytes'],
                "created_at": blob['created_at']
            }
            for blob in result['blobs']
        ]
    }
```

## Security Best Practices

### 1. MIME Type Filtering

```python
# Restrict to specific file types
storage = BlobStorage(
    storage_root="/mnt/blob-storage",
    allowed_mime_types=[
        "image/png",
        "image/jpeg",
        "image/gif",
        "application/pdf"
    ]
)

# Or use wildcards
storage = BlobStorage(
    storage_root="/mnt/blob-storage",
    allowed_mime_types=["image/*", "application/pdf"]
)
```

### 2. Size Limits

```python
# Set appropriate size limits
storage = BlobStorage(
    storage_root="/mnt/blob-storage",
    max_size_mb=10  # Limit to 10MB per blob
)
```

### 3. Input Validation

```python
@mcp.tool()
def upload_blob_safe(data: str, filename: str) -> dict:
    """Upload with additional validation."""
    # Validate filename
    if not filename or len(filename) > 255:
        return {"error": "Invalid filename"}

    # Validate data size before decoding
    if len(data) > 100 * 1024 * 1024:  # ~100MB base64
        return {"error": "Data too large"}

    try:
        binary_data = base64.b64decode(data)
    except Exception:
        return {"error": "Invalid base64 data"}

    result = storage.upload_blob(data=binary_data, filename=filename)
    return result
```

### 4. Read-Only Volumes for Consumers

```yaml
# Consumer servers should use read-only mounts
services:
  consumer:
    volumes:
      - blob-storage:/mnt/blob-storage:ro  # Read-only
```

### 5. Path Validation

```python
from mcp_mapped_resource_lib import validate_path_safety, blob_id_to_path

# Always validate paths
blob_id = user_provided_blob_id
file_path = blob_id_to_path(blob_id, "/mnt/blob-storage")

if not validate_path_safety(file_path, "/mnt/blob-storage"):
    raise ValueError("Invalid path")
```

## Performance Optimization

### 1. Enable Deduplication

```python
# Save space with deduplication
storage = BlobStorage(
    storage_root="/mnt/blob-storage",
    enable_deduplication=True  # Default
)
```

### 2. Optimize Cleanup Interval

```python
# Adjust cleanup frequency based on usage
maybe_cleanup_expired_blobs(
    storage_root="/mnt/blob-storage",
    ttl_hours=24,
    cleanup_interval_minutes=15  # Less frequent for high-traffic servers
)
```

### 3. Pagination for Large Lists

```python
# Use pagination for large blob collections
result = storage.list_blobs(page=1, page_size=50)

# Fetch next page as needed
next_page = storage.list_blobs(page=2, page_size=50)
```

### 4. Direct File Access

```python
# For local servers, access files directly (faster than base64 transfer)
file_path = storage.get_file_path(blob_id)
with open(file_path, 'rb') as f:
    data = f.read()
```

## Troubleshooting

### Issue: "Blob not found"

**Solution:**
```python
from mcp_mapped_resource_lib import BlobNotFoundError, blob_id_to_path

try:
    metadata = storage.get_metadata(blob_id)
except BlobNotFoundError:
    # Check if blob file exists on filesystem
    file_path = blob_id_to_path(blob_id, "/mnt/blob-storage")
    if file_path.exists():
        print("Blob file exists but metadata is missing")
    else:
        print("Blob file does not exist")
```

### Issue: "Invalid blob ID"

**Solution:**
```python
from mcp_mapped_resource_lib import validate_blob_id

if not validate_blob_id(blob_id):
    print(f"Invalid blob ID format: {blob_id}")
    # Expected format: blob://TIMESTAMP-HASH.EXT
```

### Issue: "Storage initialization failed"

**Solution:**
```python
from pathlib import Path

storage_root = "/mnt/blob-storage"

# Check if directory exists and is writable
if not Path(storage_root).exists():
    print("Storage root does not exist")
elif not os.access(storage_root, os.W_OK):
    print("Storage root is not writable")
```

### Issue: "Cleanup not running"

**Solution:**
```python
from mcp_mapped_resource_lib import (
    should_run_cleanup,
    get_last_cleanup_timestamp
)

# Check cleanup status
if should_run_cleanup("/mnt/blob-storage", interval_minutes=5):
    print("Cleanup should run")
else:
    last_cleanup = get_last_cleanup_timestamp("/mnt/blob-storage")
    print(f"Last cleanup: {last_cleanup}")
```

### Issue: "Path traversal detected"

**Solution:**
```python
# This is a security feature - the blob ID is likely malformed
# Only use blob IDs generated by create_blob_id() or returned by upload_blob()

# Don't construct blob IDs manually
# Bad: blob_id = f"blob://../../../etc/passwd"

# Good: blob_id from upload
result = storage.upload_blob(data=data, filename="file.txt")
blob_id = result['blob_id']  # Safe blob ID
```

## Additional Resources

- [Full API Documentation](README.md)
- [Main README](../README.md)
- [Examples](../examples/)
