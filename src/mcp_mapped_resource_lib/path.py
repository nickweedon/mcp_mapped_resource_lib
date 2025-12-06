"""Path resolution and validation utilities for blob storage."""

import re
from pathlib import Path

from .blob_id import strip_blob_protocol, validate_blob_id
from .exceptions import InvalidBlobIdError, StorageInitializationError


def blob_id_to_path(blob_id: str, storage_root: str) -> Path:
    """Translate blob ID to filesystem path.

    Uses two-level directory sharding based on timestamp:
    - First level: First 2 digits of timestamp
    - Second level: Digits 3-4 of timestamp
    - Example: blob://1733437200-hash.png -> {root}/17/33/1733437200-hash.png

    Args:
        blob_id: Blob identifier (with or without "blob://" prefix)
        storage_root: Root directory for blob storage

    Returns:
        Path object pointing to the blob file

    Raises:
        InvalidBlobIdError: If blob_id is invalid

    Example:
        >>> path = blob_id_to_path("blob://1733437200-a3f9d8c2b1e4f6a7.png", "/mnt/blob-storage")
        >>> str(path)
        '/mnt/blob-storage/17/33/1733437200-a3f9d8c2b1e4f6a7.png'
    """
    if not validate_blob_id(blob_id if blob_id.startswith("blob://") else f"blob://{blob_id}"):
        raise InvalidBlobIdError(f"Invalid blob ID: {blob_id}")

    # Strip protocol prefix
    blob_id_clean = strip_blob_protocol(blob_id)

    # Extract timestamp (first 10 digits before the dash)
    timestamp = blob_id_clean.split("-")[0]

    # Create shard path (2-level directory sharding)
    shard1 = timestamp[:2]  # First 2 digits
    shard2 = timestamp[2:4]  # Digits 3-4

    # Construct full path
    return Path(storage_root) / shard1 / shard2 / blob_id_clean


def get_metadata_path(blob_id: str, storage_root: str) -> Path:
    """Get the path to a blob's metadata file.

    Metadata files are stored alongside blob files with .meta.json extension.

    Args:
        blob_id: Blob identifier
        storage_root: Root directory for blob storage

    Returns:
        Path object pointing to the metadata file

    Example:
        >>> path = get_metadata_path("blob://1733437200-a3f9d8c2b1e4f6a7.png", "/mnt/blob-storage")
        >>> str(path)
        '/mnt/blob-storage/17/33/1733437200-a3f9d8c2b1e4f6a7.meta.json'
    """
    blob_path = blob_id_to_path(blob_id, storage_root)
    # Replace or add .meta.json extension
    return blob_path.parent / f"{blob_path.name}.meta.json"


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename for safe storage.

    Removes path traversal attempts and dangerous characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename safe for filesystem storage

    Example:
        >>> sanitize_filename("../../etc/passwd")
        'etc_passwd'
        >>> sanitize_filename("my file (1).txt")
        'my_file_1.txt'
        >>> sanitize_filename("<script>alert(1)</script>.html")
        'scriptalert1script.html'
    """
    # Remove or replace dangerous characters
    # Keep alphanumeric, dots, dashes, underscores
    sanitized = re.sub(r'[^\w\.\-]', '_', filename)

    # Remove leading dots and path separators
    sanitized = sanitized.lstrip('./')

    # Collapse multiple underscores
    sanitized = re.sub(r'_+', '_', sanitized)

    # Ensure it's not empty
    if not sanitized:
        sanitized = "unnamed"

    return sanitized


def ensure_storage_directories(storage_root: str) -> None:
    """Ensure storage root directory exists with proper structure.

    Creates the storage root directory if it doesn't exist.

    Args:
        storage_root: Root directory for blob storage

    Raises:
        StorageInitializationError: If directory creation fails

    Example:
        >>> ensure_storage_directories("/tmp/blob-storage")
    """
    try:
        root_path = Path(storage_root)
        root_path.mkdir(parents=True, exist_ok=True)

        # Verify the directory is writable
        test_file = root_path / ".write_test"
        try:
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            raise StorageInitializationError(
                f"Storage root is not writable: {storage_root}"
            ) from e

    except StorageInitializationError:
        raise
    except Exception as e:
        raise StorageInitializationError(
            f"Failed to initialize storage root: {storage_root}"
        ) from e


def validate_path_safety(path: Path, storage_root: str) -> bool:
    """Verify path is within storage root (prevent path traversal).

    Args:
        path: Path to validate
        storage_root: Storage root directory

    Returns:
        True if path is safe (within storage root), False otherwise

    Example:
        >>> from pathlib import Path
        >>> validate_path_safety(Path("/mnt/blob-storage/17/33/file.png"), "/mnt/blob-storage")
        True
        >>> validate_path_safety(Path("/etc/passwd"), "/mnt/blob-storage")
        False
    """
    try:
        # Resolve both paths to absolute
        resolved_path = path.resolve()
        resolved_root = Path(storage_root).resolve()

        # Check if path starts with storage root
        return str(resolved_path).startswith(str(resolved_root))
    except Exception:
        # If resolution fails, consider it unsafe
        return False


def get_shard_directories(storage_root: str) -> list[Path]:
    """Get all shard directories in the storage root.

    Useful for cleanup and listing operations.

    Args:
        storage_root: Root directory for blob storage

    Returns:
        List of shard directory paths (e.g., [/storage/17/33, /storage/17/34, ...])

    Example:
        >>> dirs = get_shard_directories("/mnt/blob-storage")
        >>> len(dirs) > 0
        True
    """
    root_path = Path(storage_root)
    if not root_path.exists():
        return []

    shard_dirs = []

    # Iterate through first-level shards (00-99)
    for first_level in root_path.iterdir():
        if not first_level.is_dir() or first_level.name.startswith('.'):
            continue

        # Iterate through second-level shards (00-99)
        for second_level in first_level.iterdir():
            if second_level.is_dir() and not second_level.name.startswith('.'):
                shard_dirs.append(second_level)

    return shard_dirs
