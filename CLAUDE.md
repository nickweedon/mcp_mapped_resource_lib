# Claude Code Development Guide

This document provides comprehensive instructions for Claude Code when working on the **mcp-mapped-resource-lib** project.

## Project Overview

**mcp-mapped-resource-lib** is a production-ready Python library for handling binary blob storage in MCP (Model Context Protocol) servers through shared Docker volumes.

### Key Characteristics
- **Framework-Agnostic**: No MCP dependencies, works with any framework (FastMCP, etc.)
- **Type-Safe**: Full TypedDict definitions, strict mypy type checking enabled
- **Security-First**: Built-in path traversal prevention, MIME validation, size limits
- **Performance-Optimized**: Two-level directory sharding, lazy cleanup, optional deduplication
- **Well-Documented**: 89% test coverage, comprehensive API docs and integration guides

### Target Users
- MCP server developers needing binary blob transfer capabilities
- Developers working with shared Docker volumes across multiple containers
- Projects requiring secure, validated file storage with metadata tracking

## Project Structure

```
mcp_mapped_resource_lib/
├── src/mcp_mapped_resource_lib/    # Main source code (9 modules, ~2,500 LOC)
│   ├── __init__.py                  # Public API exports (all importable functions/classes)
│   ├── storage.py                   # BlobStorage class (main interface)
│   ├── blob_id.py                   # Blob ID generation/validation/parsing
│   ├── cleanup.py                   # TTL-based lazy cleanup mechanisms
│   ├── path.py                      # Path utilities and security validation
│   ├── mime.py                      # MIME type detection/validation
│   ├── hash.py                      # SHA256 hashing utilities
│   ├── types.py                     # TypedDict definitions (BlobMetadata, etc.)
│   └── exceptions.py                # Custom exception hierarchy
├── tests/                           # Unit tests (76 tests, 89% coverage)
│   ├── test_storage.py              # BlobStorage class tests
│   ├── test_blob_id.py              # Blob ID utility tests
│   ├── test_cleanup.py              # Cleanup mechanism tests
│   ├── test_path.py                 # Path and security tests
│   ├── test_mime.py                 # MIME detection tests
│   └── test_hash.py                 # Hash calculation tests
├── docs/                            # Comprehensive documentation
│   ├── README.md                    # Full API reference (612 lines)
│   └── INTEGRATION_GUIDE.md         # MCP server integration examples (601 lines)
├── examples/                        # Working examples
│   ├── fastmcp_example.py           # Complete FastMCP server integration
│   ├── docker_compose.yml           # Multi-container volume sharing
│   └── Dockerfile                   # Container setup example
├── .github/workflows/               # CI/CD
│   ├── test.yml                     # Runs ruff, mypy, pytest on push/PR
│   └── publish.yml                  # PyPI publishing workflow
├── .devcontainer/                   # VS Code DevContainer setup
├── .claude/commands/                # Custom slash commands
│   └── commitpush.md                # Git commit/push guidelines
├── Makefile                         # Development workflow commands
├── pyproject.toml                   # Package config, dependencies, tool settings
├── README.md                        # Main library documentation (337 lines)
├── IMPLEMENTATION_SUMMARY.md        # Architecture and design decisions
├── CHANGELOG.md                     # Version history and release notes
└── CLAUDE.md                        # This file
```

## Core Architecture

### Blob ID Format
- Pattern: `blob://TIMESTAMP-HASH.EXT`
- Example: `blob://1733437200-a3f9d8c2b1e4f6a7.png`
- Components: Unix timestamp (10 digits) + 16-char hex hash + optional extension
- Security: Strict regex validation prevents path traversal

### Storage Structure (Two-Level Sharding)
```
/mnt/blob-storage/
├── 17/                                   # Shard 1: First 2 digits of timestamp
│   ├── 33/                              # Shard 2: Digits 3-4 of timestamp
│   │   ├── 1733437200-a3f9d8c2b1e4f6a7.png
│   │   └── 1733437200-a3f9d8c2b1e4f6a7.png.meta.json
│   └── 34/
├── 18/
└── .last_cleanup                         # Cleanup timestamp tracking
```

### Key Design Principles
1. **Stateless Operations**: Each function call is independent
2. **Security by Default**: All inputs validated, paths sanitized
3. **Lazy Cleanup**: Interval-based, runs alongside normal operations
4. **Metadata Separation**: JSON files alongside blobs for querying without reading files
5. **Deduplication**: Optional SHA256-based content deduplication

## Testing and Quality Assurance

### CRITICAL: Always Run All Checks Before Committing

**Use the Makefile for ALL testing workflows:**

```bash
# REQUIRED before every commit
make all

# This runs (in order):
# 1. ruff check src/ tests/     - Linting
# 2. mypy src/                   - Type checking
# 3. pytest tests/ -v --cov...   - Unit tests with coverage
```

### Individual Commands

```bash
make install     # Install package with dev dependencies (first time)
make lint        # Run ruff linting only
make typecheck   # Run mypy type checking only
make test        # Run pytest with coverage only
make clean       # Remove build artifacts and cache
make help        # Show available commands
```

### Direct Commands (if Makefile unavailable)

```bash
# Linting
ruff check src/ tests/

# Type checking
mypy src/

# Tests with coverage
pytest tests/ -v --cov=mcp_mapped_resource_lib --cov-report=term-missing --cov-report=html
```

### Type Checking Requirements

**CRITICAL**: This project has strict type checking enabled:
- `disallow_untyped_defs = true` in pyproject.toml
- ALL functions MUST have complete type annotations
- Use `TypedDict` for structured dictionaries (see `types.py`)
- Use modern syntax: `str | None` instead of `Optional[str]`
- When loading JSON, add explicit type annotations:
  ```python
  # Good
  metadata: BlobMetadata = json.load(f)
  return metadata

  # Bad (mypy error: returning Any from typed function)
  return json.load(f)
  ```

## Development Workflow

### Before Making Changes
1. Read relevant files to understand existing patterns
2. Check `docs/README.md` for API documentation
3. Review `IMPLEMENTATION_SUMMARY.md` for architecture decisions
4. Run `make all` to ensure baseline passes

### During Development
1. Follow existing code patterns (see similar functions)
2. Add type annotations to ALL new functions
3. Update tests in parallel with code changes
4. Run `make lint` and `make typecheck` frequently
5. Never skip type checking - fix errors immediately

### Before Committing
1. Run `make all` - ALL checks MUST pass
2. Update CHANGELOG.md if adding features
3. Update docs/ if changing public API
4. Ensure test coverage remains high (target: >85%)

### Common Development Tasks

#### Adding a New Feature
1. **Read** existing similar code (e.g., if adding storage method, read `storage.py`)
2. **Design** the function signature with complete types
3. **Implement** following existing patterns (security, validation, error handling)
4. **Test** - add tests to appropriate `test_*.py` file
5. **Document** - add docstring with Args, Returns, Raises, Example
6. **Verify** - run `make all`

#### Fixing a Bug
1. **Reproduce** - write a test that demonstrates the bug
2. **Fix** - make minimal changes to fix the issue
3. **Verify** - ensure the new test passes
4. **Regression** - run `make all` to prevent breaking other code
5. **Document** - update CHANGELOG.md with bug fix

#### Refactoring Code
1. **Baseline** - run `make test` to ensure all tests pass
2. **Incremental** - make small, testable changes
3. **Frequent** - run `make all` after each change
4. **No Scope Creep** - only refactor what's necessary
5. **Preserve** - ensure all tests still pass

## Code Quality Standards

### Python Version Support
- **Minimum**: Python 3.10
- **Primary**: Python 3.12 (tested in CI)
- **Type Hints**: Use Python 3.10+ syntax (`str | None`, not `Optional[str]`)

### Linting (Ruff)
- Line length: 100 characters
- Target version: Python 3.10
- Enabled rules: pycodestyle (E/W), pyflakes (F), isort (I), bugbear (B), comprehensions (C4), pyupgrade (UP)
- Auto-formatted with ruff format

### Security Patterns

**ALWAYS validate inputs:**
```python
# Blob IDs
if not validate_blob_id(blob_id):
    raise InvalidBlobIdError(f"Invalid blob ID: {blob_id}")

# File paths
if not validate_path_safety(path, storage_root):
    raise PathTraversalError(f"Unsafe path: {path}")

# MIME types
if not validate_mime_type(mime_type, allowed_mime_types):
    raise InvalidMimeTypeError(f"MIME type not allowed: {mime_type}")
```

**NEVER trust user input:**
- All filenames are sanitized (`sanitize_filename()`)
- All blob IDs are validated against strict regex
- All paths are checked for traversal attempts
- All file sizes are checked against limits

### Error Handling Patterns

```python
# Use specific exceptions from exceptions.py
from mcp_mapped_resource_lib.exceptions import (
    BlobNotFoundError,
    InvalidBlobIdError,
    BlobSizeLimitError
)

# Check conditions before operations
if not meta_path.exists():
    raise BlobNotFoundError(f"Blob not found: {blob_id}")

# Validate early, fail fast
if size_bytes > max_bytes:
    raise BlobSizeLimitError(f"Blob size {size_bytes} exceeds {max_bytes}")
```

## Documentation Standards

### Docstring Format
```python
def function_name(arg1: str, arg2: int | None = None) -> ReturnType:
    """Brief one-line description.

    Longer description if needed, explaining the purpose
    and behavior in more detail.

    Args:
        arg1: Description of arg1
        arg2: Description of arg2 (optional)

    Returns:
        Description of return value

    Raises:
        ExceptionType: When and why this is raised

    Example:
        >>> result = function_name("test", 42)
        >>> print(result)
    """
```

### When to Update Documentation
- **Always**: Update docstrings when changing function signatures
- **Public API Changes**: Update `docs/README.md` with new/changed functions
- **Breaking Changes**: Update `CHANGELOG.md` under [Unreleased]
- **New Features**: Add examples to `docs/INTEGRATION_GUIDE.md` if relevant
- **Bug Fixes**: Document in `CHANGELOG.md` under [Unreleased]

## Git Commit Guidelines

**IMPORTANT**: Use the `/commitpush` slash command which follows these rules:

### Commit Message Format
```
Brief summary of changes (imperative mood)

* First notable change or feature
* Second notable change or feature
* Third notable change or feature
```

### Rules (from .claude/commands/commitpush.md)
1. ❌ **NO** "Generated with Claude Code" or AI attribution
2. ❌ **NO** "Co-Authored-By: Claude" tags
3. ✅ **YES** Ask about untracked files before committing
4. ✅ **YES** Use `git commit -a` to include all modified files
5. ✅ **YES** Descriptive summary + bullet points for each change
6. ✅ **YES** Write as if authored solely by developer

### Before Every Commit
1. Run `make all` - ensure ALL checks pass
2. Review changes with `git diff`
3. Check for untracked files that should be included
4. Create clear, descriptive commit message

## CI/CD Pipeline

### GitHub Actions Workflow (.github/workflows/test.yml)
**Triggers**: Push to main, Pull Requests
**Steps**:
1. Install system dependencies (libmagic1)
2. Install Python package with dev dependencies
3. **Run ruff linting** ← Must pass
4. **Run mypy type checking** ← Must pass
5. **Run pytest with coverage** ← Must pass
6. Upload coverage to Codecov

**Your local `make all` replicates steps 3-5 exactly.**

### Publishing Workflow (.github/workflows/publish.yml)
- Publishes to PyPI on version tags
- Builds with hatchling backend
- Uses PyPI trusted publisher

## Dependencies

### Runtime Dependencies
- `python-magic>=0.4.27` - MIME type detection (requires libmagic system library)

### Development Dependencies
- `pytest>=7.4.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async test support
- `pytest-cov>=4.1.0` - Coverage reporting
- `ruff>=0.1.0` - Linting and formatting
- `mypy>=1.5.0` - Static type checking

### System Dependencies
```bash
# Ubuntu/Debian (DevContainer already has this)
sudo apt-get install libmagic1

# macOS
brew install libmagic
```

## Common Patterns and Examples

### Reading Files to Understand Context
Before implementing anything, read related files:
```python
# Adding blob storage feature? Read:
- src/mcp_mapped_resource_lib/storage.py
- tests/test_storage.py
- docs/README.md (search for BlobStorage)

# Adding blob ID utility? Read:
- src/mcp_mapped_resource_lib/blob_id.py
- tests/test_blob_id.py

# Adding security validation? Read:
- src/mcp_mapped_resource_lib/path.py (validate_path_safety)
- tests/test_path.py
```

### Following Existing Patterns

**Pattern: BlobStorage methods**
```python
def method_name(self, blob_id: str, ...) -> ReturnType:
    """Description with Args, Returns, Raises, Example."""
    # 1. Validate blob_id
    if not validate_blob_id(blob_id if blob_id.startswith("blob://") else f"blob://{blob_id}"):
        raise InvalidBlobIdError(f"Invalid blob ID: {blob_id}")

    # 2. Get paths
    blob_path = get_blob_path(blob_id, self.storage_root)

    # 3. Check existence
    if not blob_path.exists():
        raise BlobNotFoundError(f"Blob not found: {blob_id}")

    # 4. Perform operation
    # ... implementation ...

    # 5. Return typed result
    return result
```

**Pattern: Utility functions**
```python
def utility_function(param: str) -> ReturnType:
    """Brief description.

    Args:
        param: Description

    Returns:
        Description

    Raises:
        ExceptionType: When this happens

    Example:
        >>> result = utility_function("test")
        >>> print(result)
    """
    # Implementation
    return result
```

## Troubleshooting

### Common Issues

**Issue**: Mypy error "Returning Any from function declared to return X"
```python
# Problem:
return json.load(f)  # json.load returns Any

# Solution:
metadata: BlobMetadata = json.load(f)
return metadata
```

**Issue**: Tests failing locally but not in your changes
```bash
# Some tests have pre-existing failures
# Focus on: Did YOUR changes break anything new?
make all  # Check if YOUR code passes lint/typecheck
pytest tests/test_your_module.py  # Test your specific changes
```

**Issue**: Import errors after adding new function
```python
# Did you export it in __init__.py?
# Check src/mcp_mapped_resource_lib/__init__.py
# Add your function to __all__ and import it
```

### Quick Reference Commands

```bash
# Start development session
make install

# During development (fast feedback)
make lint          # Quick style check
make typecheck     # Quick type check

# Before committing (required)
make all          # Run everything

# Clean up artifacts
make clean

# View all commands
make help
```

## Key Files Reference

### Must Read First
- `README.md` - Library overview, quick start, configuration
- `docs/README.md` - Complete API reference with examples
- `IMPLEMENTATION_SUMMARY.md` - Architecture decisions and design

### Implementation Reference
- `src/mcp_mapped_resource_lib/storage.py` - Main BlobStorage class
- `src/mcp_mapped_resource_lib/types.py` - All TypedDict definitions
- `src/mcp_mapped_resource_lib/exceptions.py` - Exception hierarchy

### Testing Reference
- `tests/test_storage.py` - BlobStorage test patterns
- `pyproject.toml` - Configuration for pytest, mypy, ruff

### Integration Reference
- `docs/INTEGRATION_GUIDE.md` - How to use in MCP servers
- `examples/fastmcp_example.py` - Complete working example

## Critical Reminders

### ALWAYS
✅ Run `make all` before committing
✅ Add type annotations to all functions
✅ Validate all user inputs (blob IDs, paths, MIME types)
✅ Write tests for new functionality
✅ Update documentation for API changes
✅ Follow existing code patterns
✅ Use specific exceptions from `exceptions.py`

### NEVER
❌ Skip type checking or ignore mypy errors
❌ Return `Any` from typed functions
❌ Trust user input without validation
❌ Create files without reading similar code first
❌ Commit without running `make all`
❌ Use `Optional[str]` instead of `str | None`
❌ Add code without corresponding tests

## Notes for Claude Code

When working on this project:

1. **Context is King**: This is a security-focused library. Always validate inputs.
2. **Type Safety**: mypy is VERY strict. All functions need complete type annotations.
3. **Test Coverage**: High coverage (89%) is expected. Add tests for new code.
4. **Documentation**: Users rely on docstrings and examples. Keep them updated.
5. **Patterns**: Follow existing patterns in similar functions. Don't reinvent.
6. **Security**: Path traversal, MIME validation, size limits are critical. Don't skip.
7. **Performance**: Two-level sharding and lazy cleanup are design features. Preserve them.
8. **Makefile**: Use `make all` - it's the single source of truth for quality checks.

## Success Checklist

Before claiming any task is complete:

- [ ] Code follows existing patterns (checked similar files)
- [ ] All functions have complete type annotations
- [ ] `make lint` passes (ruff check)
- [ ] `make typecheck` passes (mypy)
- [ ] `make test` passes (pytest)
- [ ] Tests added for new functionality
- [ ] Docstrings updated with Args/Returns/Raises/Example
- [ ] No security issues (validation, sanitization, path safety)
- [ ] Documentation updated if API changed
- [ ] CHANGELOG.md updated if user-visible change
- [ ] Ready to commit with descriptive message

---

**Remember**: This library is used in production for secure binary storage. Quality and security are non-negotiable. When in doubt, read existing code and follow the established patterns.
