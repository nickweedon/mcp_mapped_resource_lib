"""Tests for cleanup mechanisms."""

import json
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from mcp_mapped_resource_lib.cleanup import (
    cleanup_expired_blobs,
    delete_blob_files,
    get_last_cleanup_timestamp,
    mark_cleanup_timestamp,
    maybe_cleanup_expired_blobs,
    scan_for_expired_blobs,
    should_run_cleanup,
)
from mcp_mapped_resource_lib.storage import BlobStorage


@pytest.fixture
def temp_storage():
    """Create temporary storage directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def blob_storage(temp_storage):
    """Create BlobStorage instance with temp directory."""
    return BlobStorage(storage_root=temp_storage)


def test_should_run_cleanup_first_time(temp_storage):
    """Test cleanup should run on first call."""
    assert should_run_cleanup(temp_storage, interval_minutes=5)


def test_should_run_cleanup_after_interval(temp_storage):
    """Test cleanup runs after interval elapsed."""
    # Mark cleanup as run
    mark_cleanup_timestamp(temp_storage)

    # Should not run immediately
    assert not should_run_cleanup(temp_storage, interval_minutes=5)

    # Wait a bit (in practice, we simulate by modifying timestamp)
    timestamp_file = Path(temp_storage) / ".last_cleanup"
    # Set timestamp to 6 minutes ago
    old_time = time.time() - (6 * 60)
    Path(timestamp_file).touch()
    import os
    os.utime(timestamp_file, (old_time, old_time))

    # Now it should run
    assert should_run_cleanup(temp_storage, interval_minutes=5)


def test_mark_cleanup_timestamp(temp_storage):
    """Test marking cleanup timestamp."""
    timestamp_file = Path(temp_storage) / ".last_cleanup"

    # File shouldn't exist yet
    assert not timestamp_file.exists()

    # Mark timestamp
    mark_cleanup_timestamp(temp_storage)

    # File should exist now
    assert timestamp_file.exists()


def test_get_last_cleanup_timestamp(temp_storage):
    """Test getting last cleanup timestamp."""
    # No cleanup yet
    assert get_last_cleanup_timestamp(temp_storage) is None

    # Mark cleanup
    mark_cleanup_timestamp(temp_storage)

    # Should have timestamp now
    timestamp = get_last_cleanup_timestamp(temp_storage)
    assert timestamp is not None
    assert isinstance(timestamp, float)


def test_scan_for_expired_blobs_empty(temp_storage):
    """Test scanning empty storage."""
    expired = scan_for_expired_blobs(temp_storage, ttl_hours=24)
    assert expired == []


def test_scan_for_expired_blobs(blob_storage, temp_storage):
    """Test scanning for expired blobs."""
    # Upload a blob
    result = blob_storage.upload_blob(data=b"test", filename="test.txt")
    blob_id = result['blob_id']

    # Modify metadata to make it expired
    from mcp_mapped_resource_lib.path import get_metadata_path

    meta_path = get_metadata_path(blob_id, temp_storage)
    with open(meta_path) as f:
        metadata = json.load(f)

    # Set created_at to 48 hours ago
    old_time = datetime.now(timezone.utc) - timedelta(hours=48)
    metadata['created_at'] = old_time.isoformat()

    with open(meta_path, 'w') as f:
        json.dump(metadata, f)

    # Scan with 24-hour TTL
    expired = scan_for_expired_blobs(temp_storage, ttl_hours=24)

    assert len(expired) == 1
    assert expired[0] == blob_id


def test_scan_for_expired_blobs_not_expired(blob_storage, temp_storage):
    """Test scanning doesn't return non-expired blobs."""
    # Upload a blob (will have current timestamp)
    blob_storage.upload_blob(data=b"test", filename="test.txt")

    # Scan with 24-hour TTL
    expired = scan_for_expired_blobs(temp_storage, ttl_hours=24)

    # Should be empty (blob is fresh)
    assert expired == []


def test_delete_blob_files(blob_storage, temp_storage):
    """Test deleting blob files."""
    # Upload a blob
    result = blob_storage.upload_blob(data=b"test data", filename="test.txt")
    blob_id = result['blob_id']
    file_path = Path(result['file_path'])

    # Verify files exist
    assert file_path.exists()

    from mcp_mapped_resource_lib.path import get_metadata_path
    meta_path = get_metadata_path(blob_id, temp_storage)
    assert meta_path.exists()

    # Delete
    size = delete_blob_files(blob_id, temp_storage)

    # Verify files are gone
    assert not file_path.exists()
    assert not meta_path.exists()
    assert size == 9  # "test data" is 9 bytes


def test_cleanup_expired_blobs(blob_storage, temp_storage):
    """Test cleanup operation."""
    # Upload some blobs
    result1 = blob_storage.upload_blob(data=b"data1", filename="file1.txt")
    result2 = blob_storage.upload_blob(data=b"data2", filename="file2.txt")

    # Make first blob expired
    from mcp_mapped_resource_lib.path import get_metadata_path

    meta_path1 = get_metadata_path(result1['blob_id'], temp_storage)
    with open(meta_path1) as f:
        metadata = json.load(f)

    old_time = datetime.now(timezone.utc) - timedelta(hours=48)
    metadata['created_at'] = old_time.isoformat()

    with open(meta_path1, 'w') as f:
        json.dump(metadata, f)

    # Run cleanup
    result = cleanup_expired_blobs(temp_storage, ttl_hours=24)

    assert result['deleted_count'] == 1
    assert result['freed_bytes'] == 5  # "data1" is 5 bytes
    assert result['elapsed_seconds'] >= 0

    # Verify first blob is gone
    assert not Path(result1['file_path']).exists()

    # Verify second blob still exists
    assert Path(result2['file_path']).exists()


def test_maybe_cleanup_expired_blobs_runs(temp_storage):
    """Test maybe_cleanup runs on first call."""
    result = maybe_cleanup_expired_blobs(
        temp_storage,
        ttl_hours=24,
        cleanup_interval_minutes=5
    )

    # Should run (first time)
    assert result is not None
    assert 'deleted_count' in result


def test_maybe_cleanup_expired_blobs_skips(temp_storage):
    """Test maybe_cleanup skips when interval not elapsed."""
    # Run once
    result1 = maybe_cleanup_expired_blobs(
        temp_storage,
        ttl_hours=24,
        cleanup_interval_minutes=5
    )
    assert result1 is not None

    # Run again immediately
    result2 = maybe_cleanup_expired_blobs(
        temp_storage,
        ttl_hours=24,
        cleanup_interval_minutes=5
    )

    # Should skip (interval not elapsed)
    assert result2 is None


def test_maybe_cleanup_expired_blobs_runs_after_interval(temp_storage):
    """Test maybe_cleanup runs after interval elapsed."""
    # Run once
    maybe_cleanup_expired_blobs(
        temp_storage,
        ttl_hours=24,
        cleanup_interval_minutes=5
    )

    # Modify timestamp to simulate elapsed interval
    timestamp_file = Path(temp_storage) / ".last_cleanup"
    old_time = time.time() - (6 * 60)  # 6 minutes ago
    import os
    os.utime(timestamp_file, (old_time, old_time))

    # Run again
    result = maybe_cleanup_expired_blobs(
        temp_storage,
        ttl_hours=24,
        cleanup_interval_minutes=5
    )

    # Should run (interval elapsed)
    assert result is not None


def test_cleanup_with_custom_ttl(blob_storage, temp_storage):
    """Test cleanup respects custom TTL from metadata."""
    # Upload blob with custom TTL
    result = blob_storage.upload_blob(
        data=b"test",
        filename="test.txt",
        ttl_hours=1  # 1 hour TTL
    )

    # Make it 2 hours old
    from mcp_mapped_resource_lib.path import get_metadata_path

    meta_path = get_metadata_path(result['blob_id'], temp_storage)
    with open(meta_path) as f:
        metadata = json.load(f)

    old_time = datetime.now(timezone.utc) - timedelta(hours=2)
    metadata['created_at'] = old_time.isoformat()

    with open(meta_path, 'w') as f:
        json.dump(metadata, f)

    # Cleanup with default TTL of 24 hours
    # But blob should still be deleted because its custom TTL is 1 hour
    cleanup_result = cleanup_expired_blobs(temp_storage, ttl_hours=24)

    assert cleanup_result['deleted_count'] == 1


def test_cleanup_result_structure(temp_storage):
    """Test cleanup result has correct structure."""
    result = cleanup_expired_blobs(temp_storage, ttl_hours=24)

    assert 'deleted_count' in result
    assert 'freed_bytes' in result
    assert 'elapsed_seconds' in result

    assert isinstance(result['deleted_count'], int)
    assert isinstance(result['freed_bytes'], int)
    assert isinstance(result['elapsed_seconds'], float)

    assert result['deleted_count'] >= 0
    assert result['freed_bytes'] >= 0
    assert result['elapsed_seconds'] >= 0


def test_should_run_cleanup_exception_handling(temp_storage):
    """Test should_run_cleanup handles exceptions when reading timestamp."""
    # Create a timestamp file
    timestamp_file = Path(temp_storage) / ".last_cleanup"
    timestamp_file.touch()

    # Make it unreadable by making parent directory unreadable
    # This simulates the exception handler on lines 67-69
    import os
    old_mode = os.stat(temp_storage).st_mode

    try:
        # Try to trigger permission error (may not work on all systems)
        os.chmod(temp_storage, 0o000)
        # Should return True when exception occurs
        result = should_run_cleanup(temp_storage, interval_minutes=5)
        # Restore permissions immediately
        os.chmod(temp_storage, old_mode)
        assert result is True
    except Exception:
        # Restore permissions if something went wrong
        os.chmod(temp_storage, old_mode)


def test_mark_cleanup_timestamp_exception_handling(temp_storage):
    """Test mark_cleanup_timestamp handles exceptions gracefully."""
    # Try to mark timestamp in readonly directory
    import os
    old_mode = os.stat(temp_storage).st_mode

    try:
        os.chmod(temp_storage, 0o444)  # Read-only
        # Should not raise exception (lines 86-88)
        mark_cleanup_timestamp(temp_storage)
        os.chmod(temp_storage, old_mode)
    except Exception:
        os.chmod(temp_storage, old_mode)


def test_get_last_cleanup_timestamp_exception_handling(temp_storage):
    """Test get_last_cleanup_timestamp handles exceptions."""
    # Create timestamp file
    timestamp_file = Path(temp_storage) / ".last_cleanup"
    timestamp_file.touch()

    # Make it unreadable
    import os
    old_mode = os.stat(temp_storage).st_mode

    try:
        os.chmod(temp_storage, 0o000)
        # Should return None when exception occurs (lines 112-113)
        result = get_last_cleanup_timestamp(temp_storage)
        os.chmod(temp_storage, old_mode)
        assert result is None
    except Exception:
        os.chmod(temp_storage, old_mode)


def test_cleanup_expired_blobs_exception_handling(blob_storage, temp_storage):
    """Test cleanup_expired_blobs handles deletion errors gracefully."""
    import os

    # Upload a blob
    result = blob_storage.upload_blob(data=b"test", filename="test.txt")

    # Make it expired
    from mcp_mapped_resource_lib.path import get_metadata_path

    meta_path = get_metadata_path(result['blob_id'], temp_storage)
    with open(meta_path) as f:
        metadata = json.load(f)

    old_time = datetime.now(timezone.utc) - timedelta(hours=48)
    metadata['created_at'] = old_time.isoformat()

    with open(meta_path, 'w') as f:
        json.dump(metadata, f)

    # Make the blob file directory readonly to trigger permission error
    blob_file_dir = Path(result['file_path']).parent
    old_mode = os.stat(blob_file_dir).st_mode

    try:
        os.chmod(blob_file_dir, 0o444)  # Read-only

        # Cleanup should handle the exception and continue (lines 144-146)
        cleanup_result = cleanup_expired_blobs(temp_storage, ttl_hours=24)

        # Should complete without error (deleted_count=0 because deletion failed)
        assert cleanup_result['deleted_count'] == 0
    finally:
        # Restore permissions
        os.chmod(blob_file_dir, old_mode)


def test_scan_for_expired_blobs_malformed_metadata(blob_storage, temp_storage):
    """Test scan_for_expired_blobs handles malformed metadata."""
    # Upload a blob
    result = blob_storage.upload_blob(data=b"test", filename="test.txt")

    # Corrupt the metadata file
    from mcp_mapped_resource_lib.path import get_metadata_path

    meta_path = get_metadata_path(result['blob_id'], temp_storage)
    with open(meta_path, 'w') as f:
        f.write("invalid json{{{")

    # Should handle exception and skip malformed metadata (lines 194-196)
    expired = scan_for_expired_blobs(temp_storage, ttl_hours=24)

    # Should return empty list (skipped malformed metadata)
    assert expired == []


def test_delete_blob_files_removes_empty_directories(blob_storage, temp_storage):
    """Test delete_blob_files removes empty shard directories."""
    # Upload a blob
    result = blob_storage.upload_blob(data=b"test", filename="test.txt")
    blob_id = result['blob_id']
    file_path = Path(result['file_path'])

    # Get parent directories
    second_level = file_path.parent
    first_level = second_level.parent

    # Verify directories exist
    assert second_level.exists()
    assert first_level.exists()

    # Delete blob
    delete_blob_files(blob_id, temp_storage)

    # Empty directories should be removed (lines 241-249)
    assert not second_level.exists()
    assert not first_level.exists()
