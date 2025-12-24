# MCP Mapped Resource Library

[![PyPI version](https://badge.fury.io/py/mcp-mapped-resource-lib.svg)](https://badge.fury.io/py/mcp-mapped-resource-lib)
[![Python Versions](https://img.shields.io/pypi/pyversions/mcp-mapped-resource-lib.svg)](https://pypi.org/project/mcp-mapped-resource-lib/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/nickweedon/mcp_mapped_resource_lib/actions/workflows/test.yml/badge.svg)](https://github.com/nickweedon/mcp_mapped_resource_lib/actions/workflows/test.yml)

A pip-installable Python library providing reusable utilities for MCP servers handling binary blob transfers through shared Docker volumes.

## Features

- **Blob Storage**: Upload, retrieve, list, and delete binary files with unique identifiers
- **Resource Identifiers**: Unique blob IDs in the format `blob://TIMESTAMP-HASH.EXT`
- **Metadata Tracking**: JSON-based metadata storage alongside blobs
- **Lazy Cleanup**: Automatic TTL-based expiration with configurable cleanup intervals
- **Security**: Path traversal prevention, MIME type validation, size limits
- **Deduplication**: Optional content-based deduplication using SHA256 hashing
- **Docker Volume Support**: Designed for shared Docker volumes across multiple MCP servers

## Installation

### From PyPI (Recommended)

```bash
pip install mcp-mapped-resource-lib
```

### System Dependencies

The library requires `libmagic` for MIME type detection:

```bash
# Ubuntu/Debian
sudo apt-get install libmagic1

# macOS
brew install libmagic

# Windows (using conda)
conda install -c conda-forge python-magic
```

### From Source (Development)

```bash
git clone https://github.com/nickweedon/mcp_mapped_resource_lib.git
cd mcp_mapped_resource_lib
pip install -e ".[dev]"
```

## Quick Start

```python
from mcp_mapped_resource_lib import BlobStorage, maybe_cleanup_expired_blobs

# Initialize storage
storage = BlobStorage(
    storage_root="/mnt/blob-storage",
    max_size_mb=100,
    allowed_mime_types=["image/*", "application/pdf"],
    enable_deduplication=True
)

# Upload a blob
result = storage.upload_blob(
    data=b"Hello, world!",
    filename="hello.txt",
    tags=["example"],
    ttl_hours=24
)

print(f"Blob ID: {result['blob_id']}")
print(f"File path: {result['file_path']}")
print(f"SHA256: {result['sha256']}")

# Retrieve metadata
metadata = storage.get_metadata(result['blob_id'])
print(f"Created: {metadata['created_at']}")

# List blobs with filtering
results = storage.list_blobs(
    mime_type="text/*",
    tags=["example"],
    page=1,
    page_size=20
)

print(f"Found {results['total']} blobs")

# Get filesystem path for direct access
file_path = storage.get_file_path(result['blob_id'])
with open(file_path, 'rb') as f:
    data = f.read()

# Delete a blob
storage.delete_blob(result['blob_id'])

# Lazy cleanup (run periodically)
cleanup_result = maybe_cleanup_expired_blobs(
    storage_root="/mnt/blob-storage",
    ttl_hours=24,
    cleanup_interval_minutes=5
)

if cleanup_result:
    print(f"Deleted {cleanup_result['deleted_count']} expired blobs")
    print(f"Freed {cleanup_result['freed_bytes']} bytes")
```

## Integration with MCP Servers

This library is designed to be imported into MCP servers (built with FastMCP or other frameworks):

```python
from mcp_mapped_resource_lib import BlobStorage, maybe_cleanup_expired_blobs
from fastmcp import FastMCP
import base64

mcp = FastMCP("my-mcp-server")
storage = BlobStorage(storage_root="/mnt/blob-storage")

@mcp.tool()
def upload_blob(
    data: str,  # base64-encoded
    filename: str,
    mime_type: str | None = None,
    tags: list[str] | None = None
) -> dict:
    """Upload a binary blob and receive a resource identifier."""
    binary_data = base64.b64decode(data)

    result = storage.upload_blob(
        data=binary_data,
        filename=filename,
        mime_type=mime_type,
        tags=tags
    )

    # Trigger lazy cleanup
    maybe_cleanup_expired_blobs(
        storage_root="/mnt/blob-storage",
        ttl_hours=24
    )

    return result

@mcp.tool()
def get_blob_content(blob_id: str) -> str:
    """Retrieve blob content as base64-encoded string."""
    file_path = storage.get_file_path(blob_id)
    with open(file_path, 'rb') as f:
        return base64.b64encode(f.read()).decode()

@mcp.tool()
def get_blob_file_path(blob_id: str) -> dict:
    """Get filesystem path for direct blob access (for shared volumes)."""
    file_path = storage.get_file_path(blob_id)
    return {"blob_id": blob_id, "file_path": str(file_path)}
```

## Core Modules

### BlobStorage

Main class for blob storage operations:

- `upload_blob()` - Upload binary data and receive resource identifier
- `get_metadata()` - Retrieve blob metadata
- `list_blobs()` - List blobs with filtering and pagination
- `delete_blob()` - Delete a blob
- `get_file_path()` - Get filesystem path for direct access

### Blob ID Utilities

Functions for working with blob identifiers:

- `create_blob_id()` - Generate unique blob identifier
- `validate_blob_id()` - Validate blob ID format and security
- `parse_blob_id()` - Parse blob ID into components
- `strip_blob_protocol()` - Remove "blob://" prefix

### Cleanup Utilities

Functions for managing blob lifecycle:

- `maybe_cleanup_expired_blobs()` - Lazy cleanup with interval checking
- `cleanup_expired_blobs()` - Force cleanup of expired blobs
- `should_run_cleanup()` - Check if cleanup interval has elapsed
- `scan_for_expired_blobs()` - Find expired blobs

### Path Utilities

Functions for path resolution and security:

- `blob_id_to_path()` - Translate blob ID to filesystem path
- `get_metadata_path()` - Get metadata file path
- `sanitize_filename()` - Sanitize user-provided filenames
- `validate_path_safety()` - Prevent path traversal attacks

### MIME & Hash Utilities

Functions for content handling:

- `detect_mime_type()` - Detect MIME type from data and filename
- `validate_mime_type()` - Validate MIME type against allowed list
- `calculate_sha256()` - Calculate SHA256 hash

## Configuration Options

### BlobStorage Configuration

```python
storage = BlobStorage(
    storage_root="/mnt/blob-storage",      # Storage directory
    max_size_mb=100,                       # Max blob size in MB
    allowed_mime_types=["image/*"],        # Allowed MIME types (None = all)
    enable_deduplication=True,             # Enable SHA256 deduplication
    default_ttl_hours=24                   # Default TTL for blobs
)
```

### Cleanup Configuration

```python
result = maybe_cleanup_expired_blobs(
    storage_root="/mnt/blob-storage",
    ttl_hours=24,                          # Time-to-live in hours
    cleanup_interval_minutes=5             # Min interval between cleanups
)
```

## Directory Structure

The library uses two-level directory sharding for performance:

```
/mnt/blob-storage/
├── 17/                                   # First 2 digits of timestamp
│   ├── 33/                              # Digits 3-4 of timestamp
│   │   ├── 1733437200-a3f9d8c2b1e4f6a7.png
│   │   └── 1733437200-a3f9d8c2b1e4f6a7.png.meta.json
│   └── 34/
├── 18/
└── .last_cleanup                         # Cleanup tracking file
```

## Security Features

- **Path Traversal Prevention**: Strict validation regex prevents directory traversal
- **MIME Type Filtering**: Configurable whitelist of allowed MIME types
- **Size Limits**: Configurable maximum blob size
- **Input Sanitization**: Filenames are sanitized before storage
- **Path Safety Validation**: Ensures resolved paths stay within storage root

## Docker Volume Configuration

Example Docker Compose configuration for shared volumes:

```yaml
services:
  mcp-server-1:
    build: .
    volumes:
      - blob-storage:/mnt/blob-storage    # Read-write access
    environment:
      - BLOB_STORAGE_ROOT=/mnt/blob-storage

  mcp-server-2:
    build: .
    volumes:
      - blob-storage:/mnt/blob-storage:ro # Read-only access
    environment:
      - BLOB_STORAGE_ROOT=/mnt/blob-storage

volumes:
  blob-storage:
    driver: local
```

## Documentation

- [Full API Documentation](docs/README.md)
- [Integration Guide](docs/INTEGRATION_GUIDE.md)
- [Examples](examples/)

## Development

### Using DevContainer (Recommended)

This project includes a complete DevContainer setup for VS Code:

1. Install [Docker](https://www.docker.com/get-started) and [VS Code](https://code.visualstudio.com/)
2. Install the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
3. Open the project in VS Code
4. Click "Reopen in Container" when prompted (or run "Dev Containers: Reopen in Container" from the command palette)

The DevContainer includes:
- Python 3.12 with uv package manager
- All development dependencies pre-installed
- Docker CLI for testing containerized MCP servers
- Claude Code CLI for AI-assisted development
- Pre-configured extensions (Python, Pylance, Ruff, Claude Code)

### Local Development

```bash
# Install development dependencies
make install
# or: pip install -e ".[dev]"

# Run all checks (recommended - runs lint, typecheck, and test)
make all

# Run individual checks
make lint       # Run ruff linting
make typecheck  # Run mypy type checking
make test       # Run pytest with coverage

# Clean build artifacts
make clean

# Show available commands
make help
```

#### Direct Commands (without Makefile)

```bash
# Lint code
ruff check src/ tests/

# Type check
mypy src/

# Run tests with coverage
pytest tests/ --cov=mcp_mapped_resource_lib --cov-report=html
```

## Releasing New Versions

This project includes a simple release automation workflow for creating new versions and publishing to PyPI.

### Prerequisites

1. **Install GitHub CLI** (`gh`):
   ```bash
   # macOS
   brew install gh

   # Ubuntu/Debian
   sudo apt install gh

   # Windows
   winget install GitHub.cli
   ```

2. **Authenticate with GitHub**:
   ```bash
   gh auth login
   ```

### Creating a Release

Use the Makefile target to create a new release:

```bash
# Auto-increment patch version (e.g., 0.1.0 → 0.1.1)
make release

# Or specify a version explicitly for minor/major releases
make release VERSION=0.2.0
```

Or use the script directly:

```bash
# Auto-increment patch version
./release.sh

# Or specify version explicitly
./release.sh 0.2.0
```

### What Happens During Release

The release script performs the following steps automatically:

1. **Detects** the latest version from git tags (not `pyproject.toml`)
2. **Validates** version format (must be semver: X.Y.Z)
3. **Checks** that GitHub CLI is installed and authenticated
4. **Verifies** working directory is clean (no uncommitted changes)
5. **Updates** version in `pyproject.toml`
6. **Runs** `make all` (lint + typecheck + test) to ensure quality
7. **Commits** the version bump
8. **Creates** a git tag (e.g., `v0.2.0`)
9. **Pushes** commit and tag to GitHub
10. **Creates** GitHub release with auto-generated release notes
11. **Triggers** automatic PyPI publishing via GitHub Actions

### Important Notes

- ⚠️ The `release` target is **not** part of the regular build process (`make all`)
- ⚠️ Releases must be created **explicitly** - they never happen automatically
- ✅ If no version is specified, the patch version is auto-incremented from the **latest git tag** (not `pyproject.toml`)
- ✅ Run `git fetch --tags` before releasing to ensure you have the latest tags from GitHub
- ✅ For minor/major releases, specify the version explicitly (e.g., `VERSION=0.2.0` or `VERSION=1.0.0`)
- ✅ All tests must pass before a release can be created
- ✅ PyPI publishing happens automatically via GitHub Actions (using Trusted Publishers)
- ✅ You can monitor the publishing workflow at: https://github.com/nickweedon/mcp_mapped_resource_lib/actions

### Versioning

This project follows [Semantic Versioning](https://semver.org/):

- **PATCH** (0.0.X): Bug fixes, backwards compatible - `make release` (auto-increment)
- **MINOR** (0.X.0): New features, backwards compatible - `make release VERSION=0.2.0`
- **MAJOR** (X.0.0): Breaking changes - `make release VERSION=1.0.0`

### Troubleshooting

**Error: GitHub CLI is not installed**
- Install `gh` using the instructions above

**Error: GitHub CLI is not authenticated**
- Run `gh auth login` and follow the prompts

**Error: Working directory has uncommitted changes**
- Commit or stash your changes before releasing: `git status`

**Error: Tests failed**
- Fix the failing tests before creating a release
- The version change in `pyproject.toml` will be automatically reverted

## License

MIT License - see LICENSE file for details

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and release notes.

## Contributing

Contributions are welcome! Please see CONTRIBUTING.md for guidelines.

## Support

- Issues: https://github.com/nickweedon/mcp_mapped_resource_lib/issues
- Documentation: https://github.com/nickweedon/mcp_mapped_resource_lib/docs
- PyPI: https://pypi.org/project/mcp-mapped-resource-lib/
