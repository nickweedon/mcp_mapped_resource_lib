# MCP Mapped Resource Library - API Documentation

Complete API reference for the MCP Mapped Resource Library.

## Table of Contents

- [BlobStorage Class](#blobstorage-class)
- [Blob ID Functions](#blob-id-functions)
- [Cleanup Functions](#cleanup-functions)
- [Path Functions](#path-functions)
- [MIME Functions](#mime-functions)
- [Hash Functions](#hash-functions)
- [Type Definitions](#type-definitions)
- [Exceptions](#exceptions)

## BlobStorage Class

Main class for managing blob storage operations.

### Constructor

```python
BlobStorage(
    storage_root: str,
    max_size_mb: int = 100,
    allowed_mime_types: Optional[list[str]] = None,
    enable_deduplication: bool = True,
    default_ttl_hours: int = 24
)
```

**Parameters:**
- `storage_root`: Root directory for blob storage
- `max_size_mb`: Maximum blob size in megabytes (default: 100)
- `allowed_mime_types`: List of allowed MIME types, supports wildcards (default: None = allow all)
- `enable_deduplication`: Enable SHA256-based deduplication (default: True)
- `default_ttl_hours`: Default time-to-live for blobs in hours (default: 24)

**Example:**
```python
storage = BlobStorage(
    storage_root="/mnt/blob-storage",
    max_size_mb=50,
    allowed_mime_types=["image/*", "application/pdf"],
    enable_deduplication=True,
    default_ttl_hours=48
)
```

### upload_blob()

Upload binary data and receive a resource identifier.

```python
def upload_blob(
    data: bytes,
    filename: str,
    mime_type: Optional[str] = None,
    tags: Optional[list[str]] = None,
    ttl_hours: Optional[int] = None,
    uploaded_by: Optional[str] = None
) -> BlobUploadResult
```

**Parameters:**
- `data`: Binary data to store
- `filename`: Original filename (used for extension and MIME detection)
- `mime_type`: MIME type (auto-detected if None)
- `tags`: Optional tags for categorization
- `ttl_hours`: Time-to-live in hours (uses default if None)
- `uploaded_by`: Optional identifier of uploader

**Returns:** `BlobUploadResult` with `blob_id`, `size_bytes`, `mime_type`, `file_path`, `sha256`

**Raises:**
- `BlobSizeLimitError`: If data exceeds max_size_mb
- `InvalidMimeTypeError`: If MIME type is not allowed

**Example:**
```python
result = storage.upload_blob(
    data=b"Hello, world!",
    filename="hello.txt",
    tags=["greeting", "example"],
    ttl_hours=48
)

print(result['blob_id'])  # "blob://1733437200-a3f9d8c2b1e4f6a7.txt"
```

### get_metadata()

Retrieve metadata for a blob without downloading content.

```python
def get_metadata(blob_id: str) -> BlobMetadata
```

**Parameters:**
- `blob_id`: Blob identifier

**Returns:** `BlobMetadata` dictionary

**Raises:**
- `InvalidBlobIdError`: If blob_id format is invalid
- `BlobNotFoundError`: If blob doesn't exist

**Example:**
```python
metadata = storage.get_metadata("blob://1733437200-a3f9d8c2b1e4f6a7.txt")

print(metadata['filename'])      # "hello.txt"
print(metadata['size_bytes'])    # 13
print(metadata['created_at'])    # "2025-12-05T21:00:00Z"
print(metadata['tags'])          # ["greeting", "example"]
```

### list_blobs()

List blobs with optional filtering and pagination.

```python
def list_blobs(
    mime_type: Optional[str] = None,
    tags: Optional[list[str]] = None,
    created_after: Optional[str] = None,
    created_before: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
) -> BlobListResult
```

**Parameters:**
- `mime_type`: Filter by MIME type (supports wildcards like "image/*")
- `tags`: Filter by tags (blob must have all specified tags)
- `created_after`: Filter by creation date (ISO 8601 format)
- `created_before`: Filter by creation date (ISO 8601 format)
- `page`: Page number (1-indexed)
- `page_size`: Number of items per page

**Returns:** `BlobListResult` with `blobs`, `total`, `page`, `page_size`

**Example:**
```python
# List all image blobs
result = storage.list_blobs(mime_type="image/*", page=1, page_size=10)

for blob in result['blobs']:
    print(f"{blob['blob_id']}: {blob['filename']}")

print(f"Total: {result['total']} images")

# List blobs with specific tags
result = storage.list_blobs(tags=["screenshot", "ui"])

# List recent blobs
result = storage.list_blobs(created_after="2025-12-01T00:00:00Z")
```

### delete_blob()

Delete a blob and its metadata.

```python
def delete_blob(blob_id: str) -> None
```

**Parameters:**
- `blob_id`: Blob identifier

**Raises:**
- `InvalidBlobIdError`: If blob_id format is invalid
- `BlobNotFoundError`: If blob doesn't exist

**Example:**
```python
storage.delete_blob("blob://1733437200-a3f9d8c2b1e4f6a7.txt")
```

### get_file_path()

Get the filesystem path for a blob (for direct file access).

```python
def get_file_path(blob_id: str) -> Path
```

**Parameters:**
- `blob_id`: Blob identifier

**Returns:** `Path` object pointing to the blob file

**Raises:**
- `InvalidBlobIdError`: If blob_id format is invalid
- `BlobNotFoundError`: If blob doesn't exist

**Example:**
```python
file_path = storage.get_file_path("blob://1733437200-a3f9d8c2b1e4f6a7.png")

# Read directly from filesystem
with open(file_path, 'rb') as f:
    data = f.read()

# Use with PIL
from PIL import Image
image = Image.open(file_path)
```

## Blob ID Functions

### create_blob_id()

Generate a unique blob identifier.

```python
def create_blob_id(extension: Optional[str] = None) -> str
```

**Parameters:**
- `extension`: Optional file extension (with or without leading dot)

**Returns:** Unique blob identifier string in format `blob://TIMESTAMP-HASH.EXT`

**Example:**
```python
blob_id = create_blob_id("png")
# "blob://1733437200-a3f9d8c2b1e4f6a7.png"

blob_id = create_blob_id()
# "blob://1733437200-a3f9d8c2b1e4f6a7"
```

### validate_blob_id()

Validate blob ID format and security.

```python
def validate_blob_id(blob_id: str) -> bool
```

**Parameters:**
- `blob_id`: Blob identifier to validate

**Returns:** True if valid, False otherwise

**Example:**
```python
validate_blob_id("blob://1733437200-a3f9d8c2b1e4f6a7.png")  # True
validate_blob_id("blob://../../../etc/passwd")              # False
validate_blob_id("invalid")                                 # False
```

### parse_blob_id()

Parse a blob ID into its components.

```python
def parse_blob_id(blob_id: str) -> BlobIdComponents
```

**Parameters:**
- `blob_id`: Blob identifier to parse

**Returns:** Dictionary with `timestamp`, `hash`, and `extension` components

**Raises:**
- `InvalidBlobIdError`: If blob_id format is invalid

**Example:**
```python
components = parse_blob_id("blob://1733437200-a3f9d8c2b1e4f6a7.png")

print(components['timestamp'])   # 1733437200
print(components['hash'])         # "a3f9d8c2b1e4f6a7"
print(components['extension'])    # "png"
```

### strip_blob_protocol()

Remove the "blob://" protocol prefix.

```python
def strip_blob_protocol(blob_id: str) -> str
```

**Parameters:**
- `blob_id`: Blob identifier with or without protocol

**Returns:** Blob ID without protocol prefix

**Example:**
```python
strip_blob_protocol("blob://1733437200-a3f9d8c2b1e4f6a7.png")
# "1733437200-a3f9d8c2b1e4f6a7.png"
```

## Cleanup Functions

### maybe_cleanup_expired_blobs()

Run cleanup only if interval has elapsed since last cleanup (lazy cleanup).

```python
def maybe_cleanup_expired_blobs(
    storage_root: str,
    ttl_hours: int,
    cleanup_interval_minutes: int = 5
) -> Optional[CleanupResult]
```

**Parameters:**
- `storage_root`: Root directory for blob storage
- `ttl_hours`: Time-to-live in hours (blobs older than this are deleted)
- `cleanup_interval_minutes`: Minimum interval between cleanup runs (default: 5)

**Returns:** `CleanupResult` if cleanup was performed, None if skipped

**Example:**
```python
# Call this after blob operations (upload, list, etc.)
result = maybe_cleanup_expired_blobs(
    storage_root="/mnt/blob-storage",
    ttl_hours=24,
    cleanup_interval_minutes=5
)

if result:
    print(f"Deleted {result['deleted_count']} expired blobs")
    print(f"Freed {result['freed_bytes']} bytes")
    print(f"Took {result['elapsed_seconds']:.2f} seconds")
```

### cleanup_expired_blobs()

Force cleanup of expired blobs (ignores interval).

```python
def cleanup_expired_blobs(
    storage_root: str,
    ttl_hours: int
) -> CleanupResult
```

**Parameters:**
- `storage_root`: Root directory for blob storage
- `ttl_hours`: Time-to-live in hours

**Returns:** `CleanupResult` with deletion statistics

**Example:**
```python
result = cleanup_expired_blobs("/mnt/blob-storage", ttl_hours=24)

print(f"Deleted {result['deleted_count']} blobs")
print(f"Freed {result['freed_bytes']} bytes")
```

### should_run_cleanup()

Check if enough time has elapsed since last cleanup.

```python
def should_run_cleanup(
    storage_root: str,
    interval_minutes: int
) -> bool
```

**Parameters:**
- `storage_root`: Root directory for blob storage
- `interval_minutes`: Minimum interval in minutes

**Returns:** True if cleanup should run, False otherwise

### scan_for_expired_blobs()

Scan storage for expired blobs based on TTL.

```python
def scan_for_expired_blobs(
    storage_root: str,
    ttl_hours: int
) -> list[str]
```

**Parameters:**
- `storage_root`: Root directory for blob storage
- `ttl_hours`: Time-to-live in hours

**Returns:** List of blob IDs that have expired

## Path Functions

### blob_id_to_path()

Translate blob ID to filesystem path.

```python
def blob_id_to_path(blob_id: str, storage_root: str) -> Path
```

**Parameters:**
- `blob_id`: Blob identifier
- `storage_root`: Root directory for blob storage

**Returns:** Path object pointing to the blob file

**Raises:**
- `InvalidBlobIdError`: If blob_id is invalid

**Example:**
```python
path = blob_id_to_path("blob://1733437200-a3f9d8c2b1e4f6a7.png", "/mnt/blob-storage")
# Path("/mnt/blob-storage/17/33/1733437200-a3f9d8c2b1e4f6a7.png")
```

### sanitize_filename()

Sanitize a filename for safe storage.

```python
def sanitize_filename(filename: str) -> str
```

**Parameters:**
- `filename`: Original filename

**Returns:** Sanitized filename

**Example:**
```python
sanitize_filename("../../etc/passwd")            # "etc_passwd"
sanitize_filename("my file (1).txt")             # "my_file__1_.txt"
sanitize_filename("<script>alert(1)</script>")   # "script_alert_1_script_"
```

### validate_path_safety()

Verify path is within storage root (prevent path traversal).

```python
def validate_path_safety(path: Path, storage_root: str) -> bool
```

**Parameters:**
- `path`: Path to validate
- `storage_root`: Storage root directory

**Returns:** True if path is safe, False otherwise

## MIME Functions

### detect_mime_type()

Detect MIME type from data and filename.

```python
def detect_mime_type(data: bytes, filename: str) -> str
```

**Parameters:**
- `data`: Binary data to analyze
- `filename`: Filename to use for extension-based detection

**Returns:** Detected MIME type (e.g., "image/png", "application/pdf")

**Example:**
```python
mime = detect_mime_type(b"\x89PNG\r\n...", "image.png")
# "image/png"
```

### validate_mime_type()

Validate MIME type against allowed list.

```python
def validate_mime_type(
    mime_type: str,
    allowed: Optional[list[str]]
) -> bool
```

**Parameters:**
- `mime_type`: MIME type to validate
- `allowed`: List of allowed MIME types (None = allow all)

**Returns:** True if allowed, False otherwise

**Example:**
```python
validate_mime_type("image/png", ["image/*", "application/pdf"])  # True
validate_mime_type("text/plain", ["image/*"])                    # False
validate_mime_type("anything", None)                             # True
```

## Hash Functions

### calculate_sha256()

Calculate SHA256 hash of data.

```python
def calculate_sha256(data: bytes) -> str
```

**Parameters:**
- `data`: Binary data to hash

**Returns:** Hexadecimal SHA256 hash string

**Example:**
```python
hash_digest = calculate_sha256(b"test data")
# "916f0027a575074ce72a331777c3478d6513f786a591bd892da1a577bf2335f9"
```

## Type Definitions

### BlobMetadata

```python
class BlobMetadata(TypedDict, total=False):
    blob_id: str              # Unique identifier
    filename: str             # Original filename
    mime_type: str            # MIME type
    size_bytes: int           # Size in bytes
    created_at: str           # ISO 8601 UTC timestamp
    sha256: str               # SHA256 hash
    uploaded_by: str | None   # Uploader identifier
    tags: list[str] | None    # Tags
    ttl_hours: int            # Time-to-live
```

### BlobUploadResult

```python
class BlobUploadResult(TypedDict):
    blob_id: str              # Unique identifier
    size_bytes: int           # Size in bytes
    mime_type: str            # MIME type
    file_path: str            # Filesystem path
    sha256: str               # SHA256 hash
```

### BlobListResult

```python
class BlobListResult(TypedDict):
    blobs: list[BlobMetadata] # List of blob metadata
    total: int                # Total number of blobs
    page: int                 # Current page (1-indexed)
    page_size: int            # Items per page
```

### CleanupResult

```python
class CleanupResult(TypedDict):
    deleted_count: int        # Number of blobs deleted
    freed_bytes: int          # Bytes freed
    elapsed_seconds: float    # Time taken
```

## Exceptions

All exceptions inherit from `BlobStorageError`.

### BlobStorageError

Base exception for all blob storage errors.

### InvalidBlobIdError

Raised when a blob ID is invalid or malformed.

### BlobNotFoundError

Raised when a requested blob does not exist.

### BlobSizeLimitError

Raised when a blob exceeds the maximum allowed size.

### InvalidMimeTypeError

Raised when a blob's MIME type is not allowed.

### PathTraversalError

Raised when a path traversal attempt is detected.

### StorageInitializationError

Raised when storage initialization fails.

**Example:**
```python
from mcp_mapped_resource_lib.exceptions import (
    BlobNotFoundError,
    InvalidBlobIdError
)

try:
    metadata = storage.get_metadata("invalid-id")
except InvalidBlobIdError:
    print("Invalid blob ID format")
except BlobNotFoundError:
    print("Blob not found")
```
