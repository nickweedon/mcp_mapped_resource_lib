"""Lazy cleanup mechanisms for expired blobs."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .path import get_metadata_path, get_shard_directories
from .types import CleanupResult


def maybe_cleanup_expired_blobs(
    storage_root: str,
    ttl_hours: int,
    cleanup_interval_minutes: int = 5
) -> Optional[CleanupResult]:
    """Run cleanup only if interval has elapsed since last cleanup.

    This is the main entry point for lazy cleanup. It checks if enough time
    has passed since the last cleanup, and if so, runs the cleanup operation.

    Args:
        storage_root: Root directory for blob storage
        ttl_hours: Time-to-live in hours (blobs older than this are deleted)
        cleanup_interval_minutes: Minimum interval between cleanup runs

    Returns:
        CleanupResult if cleanup was performed, None if skipped

    Example:
        >>> result = maybe_cleanup_expired_blobs("/mnt/blob-storage", ttl_hours=24)
        >>> if result:
        ...     print(f"Deleted {result['deleted_count']} blobs")
    """
    if not should_run_cleanup(storage_root, cleanup_interval_minutes):
        return None

    result = cleanup_expired_blobs(storage_root, ttl_hours)
    mark_cleanup_timestamp(storage_root)
    return result


def should_run_cleanup(storage_root: str, interval_minutes: int) -> bool:
    """Check if enough time has elapsed since last cleanup.

    Args:
        storage_root: Root directory for blob storage
        interval_minutes: Minimum interval in minutes between cleanups

    Returns:
        True if cleanup should run, False otherwise

    Example:
        >>> should_run_cleanup("/mnt/blob-storage", interval_minutes=5)
        True
    """
    timestamp_file = Path(storage_root) / ".last_cleanup"

    if not timestamp_file.exists():
        return True  # First cleanup, always run

    try:
        last_cleanup = timestamp_file.stat().st_mtime
        elapsed_minutes = (time.time() - last_cleanup) / 60

        return elapsed_minutes >= interval_minutes
    except Exception:
        # If we can't read the timestamp, run cleanup
        return True


def mark_cleanup_timestamp(storage_root: str) -> None:
    """Update the last cleanup timestamp file.

    Creates or touches the .last_cleanup file to record when cleanup ran.

    Args:
        storage_root: Root directory for blob storage

    Example:
        >>> mark_cleanup_timestamp("/mnt/blob-storage")
    """
    timestamp_file = Path(storage_root) / ".last_cleanup"
    try:
        timestamp_file.touch()
    except Exception:
        # If we can't write the timestamp, log but don't fail
        pass


def get_last_cleanup_timestamp(storage_root: str) -> Optional[float]:
    """Get the timestamp of the last cleanup operation.

    Args:
        storage_root: Root directory for blob storage

    Returns:
        Unix timestamp of last cleanup, or None if never run

    Example:
        >>> ts = get_last_cleanup_timestamp("/mnt/blob-storage")
        >>> ts is None or isinstance(ts, float)
        True
    """
    timestamp_file = Path(storage_root) / ".last_cleanup"

    if not timestamp_file.exists():
        return None

    try:
        return timestamp_file.stat().st_mtime
    except Exception:
        return None


def cleanup_expired_blobs(storage_root: str, ttl_hours: int) -> CleanupResult:
    """Scan and delete expired blobs based on TTL.

    Args:
        storage_root: Root directory for blob storage
        ttl_hours: Time-to-live in hours (blobs older than this are deleted)

    Returns:
        CleanupResult with deletion statistics

    Example:
        >>> result = cleanup_expired_blobs("/mnt/blob-storage", ttl_hours=24)
        >>> result['deleted_count'] >= 0
        True
    """
    start_time = time.time()
    deleted_count = 0
    freed_bytes = 0

    # Scan for expired blobs
    expired_blob_ids = scan_for_expired_blobs(storage_root, ttl_hours)

    # Delete each expired blob
    for blob_id in expired_blob_ids:
        try:
            blob_size = delete_blob_files(blob_id, storage_root)
            deleted_count += 1
            freed_bytes += blob_size
        except Exception:
            # Log error but continue with other blobs
            continue

    elapsed_seconds = time.time() - start_time

    return CleanupResult(
        deleted_count=deleted_count,
        freed_bytes=freed_bytes,
        elapsed_seconds=elapsed_seconds
    )


def scan_for_expired_blobs(storage_root: str, ttl_hours: int) -> list[str]:
    """Scan storage for expired blobs based on TTL.

    Args:
        storage_root: Root directory for blob storage
        ttl_hours: Time-to-live in hours

    Returns:
        List of blob IDs that have expired

    Example:
        >>> expired = scan_for_expired_blobs("/mnt/blob-storage", ttl_hours=24)
        >>> isinstance(expired, list)
        True
    """
    expired_blob_ids = []
    now = datetime.now(timezone.utc)

    # Iterate through all shard directories
    shard_dirs = get_shard_directories(storage_root)

    for shard_dir in shard_dirs:
        # Look for metadata files
        for meta_file in shard_dir.glob("*.meta.json"):
            try:
                # Read metadata
                with open(meta_file, 'r') as f:
                    metadata = json.load(f)

                # Check if blob has expired
                created_at = datetime.fromisoformat(metadata.get('created_at', ''))
                blob_ttl = metadata.get('ttl_hours', ttl_hours)
                blob_age_hours = (now - created_at).total_seconds() / 3600

                if blob_age_hours > blob_ttl:
                    expired_blob_ids.append(metadata['blob_id'])

            except Exception:
                # Skip malformed metadata files
                continue

    return expired_blob_ids


def delete_blob_files(blob_id: str, storage_root: str) -> int:
    """Delete a blob and its metadata file.

    Args:
        blob_id: Blob identifier to delete
        storage_root: Root directory for blob storage

    Returns:
        Size in bytes of the deleted blob

    Raises:
        FileNotFoundError: If blob or metadata file doesn't exist

    Example:
        >>> size = delete_blob_files("blob://1733437200-a3f9d8c2b1e4f6a7.png", "/mnt/blob-storage")
        >>> size >= 0
        True
    """
    from .path import blob_id_to_path

    # Get paths
    blob_path = blob_id_to_path(blob_id, storage_root)
    meta_path = get_metadata_path(blob_id, storage_root)

    # Get size before deletion
    blob_size = 0
    if blob_path.exists():
        blob_size = blob_path.stat().st_size

    # Delete blob file
    if blob_path.exists():
        blob_path.unlink()

    # Delete metadata file
    if meta_path.exists():
        meta_path.unlink()

    # Try to remove empty parent directories
    try:
        # Remove second-level shard directory if empty
        if blob_path.parent.exists() and not any(blob_path.parent.iterdir()):
            blob_path.parent.rmdir()

        # Remove first-level shard directory if empty
        if blob_path.parent.parent.exists() and not any(blob_path.parent.parent.iterdir()):
            blob_path.parent.parent.rmdir()
    except Exception:
        # Ignore errors when removing directories
        pass

    return blob_size
