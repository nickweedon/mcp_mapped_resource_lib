# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **BREAKING**: Documentation now recommends using MCP tools instead of resource endpoints for blob retrieval
  - Updated `README.md` to show `get_blob_content()` as a tool instead of `@mcp.resource()`
  - Updated `docs/INTEGRATION_GUIDE.md` with a note explaining why tools are preferred over template resources
  - Updated `examples/fastmcp_example.py` to implement `get_blob_content()` as a tool
  - Reason: Template resources (e.g., `blob://{blob_id}`) are not well-supported by some MCP clients
  - Migration: Replace `@mcp.resource("blob://{blob_id}")` with `@mcp.tool()` decorator for `get_blob_content()`

## [0.1.0] - TBD

### Added
- Initial release of MCP Mapped Resource Library
- `BlobStorage` class for managing binary blob storage operations
  - `upload_blob()` - Upload binary data with automatic ID generation
  - `get_metadata()` - Retrieve blob metadata
  - `list_blobs()` - List blobs with filtering by MIME type, tags, and pagination
  - `delete_blob()` - Delete blobs and associated metadata
  - `get_file_path()` - Get filesystem path for direct blob access
- Blob ID utilities for working with resource identifiers
  - `create_blob_id()` - Generate unique blob IDs in format `blob://TIMESTAMP-HASH.EXT`
  - `validate_blob_id()` - Validate blob ID format and security
  - `parse_blob_id()` - Parse blob ID into components
  - `strip_blob_protocol()` - Remove `blob://` prefix
- Cleanup utilities for blob lifecycle management
  - `maybe_cleanup_expired_blobs()` - Lazy cleanup with interval checking
  - `cleanup_expired_blobs()` - Force cleanup of expired blobs
  - `should_run_cleanup()` - Check if cleanup interval has elapsed
  - `scan_for_expired_blobs()` - Find expired blobs based on TTL
- Path utilities for filesystem operations
  - `blob_id_to_path()` - Translate blob ID to filesystem path with sharding
  - `get_metadata_path()` - Get metadata JSON file path
  - `sanitize_filename()` - Sanitize user-provided filenames
  - `validate_path_safety()` - Prevent path traversal attacks
- MIME type utilities
  - `detect_mime_type()` - Detect MIME type from data and filename
  - `validate_mime_type()` - Validate MIME type against allowed list with wildcard support
- Hash utilities
  - `calculate_sha256()` - Calculate SHA256 hash of binary data
- Security features
  - Path traversal prevention with strict validation
  - MIME type filtering with configurable whitelist
  - Configurable blob size limits
  - Input sanitization for filenames
- Storage features
  - Two-level directory sharding for performance (e.g., `17/33/blob-id.ext`)
  - JSON-based metadata storage alongside blobs
  - TTL-based expiration with configurable defaults
  - Optional content-based deduplication using SHA256
  - Docker volume support for multi-container deployments
- Comprehensive type hints for all public APIs
- Full test coverage with pytest
- Type checking with mypy
- Linting with ruff
- Documentation with examples and integration guides

### Security
- Path traversal protection using strict regex validation
- MIME type validation to prevent malicious file uploads
- Size limits to prevent storage exhaustion
- Filename sanitization to prevent directory traversal

[Unreleased]: https://github.com/nickweedon/mcp_mapped_resource_lib/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/nickweedon/mcp_mapped_resource_lib/releases/tag/v0.1.0
