"""Tests for blob storage."""

import tempfile
from pathlib import Path

import pytest

from mcp_mapped_resource_lib.exceptions import (
    BlobNotFoundError,
    BlobSizeLimitError,
    InvalidBlobIdError,
    InvalidMimeTypeError,
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


def test_blob_storage_init(temp_storage):
    """Test BlobStorage initialization."""
    storage = BlobStorage(
        storage_root=temp_storage,
        max_size_mb=50,
        allowed_mime_types=["image/*"],
        enable_deduplication=False,
        default_ttl_hours=48
    )

    assert storage.storage_root == temp_storage
    assert storage.max_size_mb == 50
    assert storage.allowed_mime_types == ["image/*"]
    assert storage.enable_deduplication is False
    assert storage.default_ttl_hours == 48


def test_upload_blob(blob_storage):
    """Test basic blob upload."""
    result = blob_storage.upload_blob(
        data=b"test data",
        filename="test.txt"
    )

    assert result['blob_id'].startswith("blob://")
    assert result['size_bytes'] == 9
    assert result['mime_type'] == "text/plain"
    assert result['sha256'] is not None
    assert Path(result['file_path']).exists()


def test_upload_blob_with_extension(blob_storage):
    """Test blob upload preserves extension."""
    result = blob_storage.upload_blob(
        data=b"PNG data",
        filename="image.png"
    )

    assert result['blob_id'].endswith(".png")


def test_upload_blob_with_tags(blob_storage):
    """Test blob upload with tags."""
    result = blob_storage.upload_blob(
        data=b"test data",
        filename="test.txt",
        tags=["tag1", "tag2"]
    )

    # Verify metadata includes tags
    metadata = blob_storage.get_metadata(result['blob_id'])
    assert metadata['tags'] == ["tag1", "tag2"]


def test_upload_blob_with_ttl(blob_storage):
    """Test blob upload with custom TTL."""
    result = blob_storage.upload_blob(
        data=b"test data",
        filename="test.txt",
        ttl_hours=48
    )

    # Verify metadata includes custom TTL
    metadata = blob_storage.get_metadata(result['blob_id'])
    assert metadata['ttl_hours'] == 48


def test_upload_blob_size_limit(blob_storage):
    """Test blob upload respects size limit."""
    # Create data larger than limit (100MB default)
    large_data = b"x" * (101 * 1024 * 1024)

    with pytest.raises(BlobSizeLimitError):
        blob_storage.upload_blob(
            data=large_data,
            filename="large.bin"
        )


def test_upload_blob_mime_type_validation(temp_storage):
    """Test blob upload validates MIME types."""
    storage = BlobStorage(
        storage_root=temp_storage,
        allowed_mime_types=["image/*"]
    )

    # This should work (image) - explicitly set MIME type
    result = storage.upload_blob(
        data=b"PNG data",
        filename="image.png",
        mime_type="image/png"
    )
    assert result['blob_id'] is not None

    # This should fail (text)
    with pytest.raises(InvalidMimeTypeError):
        storage.upload_blob(
            data=b"text data",
            filename="file.txt",
            mime_type="text/plain"
        )


def test_upload_blob_deduplication(temp_storage):
    """Test blob deduplication."""
    storage = BlobStorage(
        storage_root=temp_storage,
        enable_deduplication=True
    )

    # Upload same data twice
    result1 = storage.upload_blob(
        data=b"test data",
        filename="file1.txt"
    )

    result2 = storage.upload_blob(
        data=b"test data",
        filename="file2.txt"
    )

    # Should return same blob ID
    assert result1['blob_id'] == result2['blob_id']
    assert result1['sha256'] == result2['sha256']


def test_upload_blob_no_deduplication(temp_storage):
    """Test blob upload without deduplication."""
    storage = BlobStorage(
        storage_root=temp_storage,
        enable_deduplication=False
    )

    # Upload same data twice
    result1 = storage.upload_blob(
        data=b"test data",
        filename="file1.txt"
    )

    result2 = storage.upload_blob(
        data=b"test data",
        filename="file2.txt"
    )

    # Should create different blobs
    assert result1['blob_id'] != result2['blob_id']
    assert result1['sha256'] == result2['sha256']  # Same content hash


def test_get_metadata(blob_storage):
    """Test retrieving blob metadata."""
    # Upload a blob
    result = blob_storage.upload_blob(
        data=b"test data",
        filename="test.txt",
        tags=["test"]
    )

    # Get metadata
    metadata = blob_storage.get_metadata(result['blob_id'])

    assert metadata['blob_id'] == result['blob_id']
    assert metadata['filename'] == "test.txt"
    assert metadata['mime_type'] == "text/plain"
    assert metadata['size_bytes'] == 9
    assert metadata['sha256'] == result['sha256']
    assert metadata['tags'] == ["test"]


def test_get_metadata_not_found(blob_storage):
    """Test getting metadata for non-existent blob."""
    with pytest.raises(BlobNotFoundError):
        blob_storage.get_metadata("blob://9999999999-0123456789abcdef.txt")


def test_get_metadata_invalid_id(blob_storage):
    """Test getting metadata with invalid blob ID."""
    with pytest.raises(InvalidBlobIdError):
        blob_storage.get_metadata("invalid")


def test_list_blobs_empty(blob_storage):
    """Test listing blobs in empty storage."""
    result = blob_storage.list_blobs()

    assert result['blobs'] == []
    assert result['total'] == 0
    assert result['page'] == 1
    assert result['page_size'] == 20


def test_list_blobs(blob_storage):
    """Test listing blobs."""
    # Upload some blobs
    blob_storage.upload_blob(data=b"data1", filename="file1.txt")
    blob_storage.upload_blob(data=b"data2", filename="file2.txt")
    blob_storage.upload_blob(data=b"data3", filename="file3.png")

    result = blob_storage.list_blobs()

    assert result['total'] == 3
    assert len(result['blobs']) == 3


def test_list_blobs_filter_mime_type(blob_storage):
    """Test listing blobs filtered by MIME type."""
    # Upload different types with explicit MIME types
    blob_storage.upload_blob(data=b"text", filename="file.txt", mime_type="text/plain")
    blob_storage.upload_blob(data=b"png", filename="image.png", mime_type="image/png")

    # Filter for text
    result = blob_storage.list_blobs(mime_type="text/plain")
    assert result['total'] == 1
    assert result['blobs'][0]['mime_type'] == "text/plain"


def test_list_blobs_filter_mime_wildcard(blob_storage):
    """Test listing blobs with MIME wildcard filter."""
    # Upload different types with explicit MIME types
    blob_storage.upload_blob(data=b"png", filename="image1.png", mime_type="image/png")
    blob_storage.upload_blob(data=b"jpg", filename="image2.jpg", mime_type="image/jpeg")
    blob_storage.upload_blob(data=b"text", filename="file.txt", mime_type="text/plain")

    # Filter for images
    result = blob_storage.list_blobs(mime_type="image/*")
    assert result['total'] == 2


def test_list_blobs_filter_tags(blob_storage):
    """Test listing blobs filtered by tags."""
    blob_storage.upload_blob(data=b"data1", filename="file1.txt", tags=["tag1"])
    blob_storage.upload_blob(data=b"data2", filename="file2.txt", tags=["tag1", "tag2"])
    blob_storage.upload_blob(data=b"data3", filename="file3.txt", tags=["tag2"])

    # Filter for tag1
    result = blob_storage.list_blobs(tags=["tag1"])
    assert result['total'] == 2


def test_list_blobs_pagination(blob_storage):
    """Test blob listing pagination."""
    # Upload 25 blobs
    for i in range(25):
        blob_storage.upload_blob(data=f"data{i}".encode(), filename=f"file{i}.txt")

    # Get first page
    result1 = blob_storage.list_blobs(page=1, page_size=10)
    assert len(result1['blobs']) == 10
    assert result1['total'] == 25
    assert result1['page'] == 1

    # Get second page
    result2 = blob_storage.list_blobs(page=2, page_size=10)
    assert len(result2['blobs']) == 10
    assert result2['page'] == 2

    # Get third page
    result3 = blob_storage.list_blobs(page=3, page_size=10)
    assert len(result3['blobs']) == 5
    assert result3['page'] == 3


def test_delete_blob(blob_storage):
    """Test deleting a blob."""
    # Upload a blob
    result = blob_storage.upload_blob(data=b"test data", filename="test.txt")
    blob_id = result['blob_id']

    # Verify it exists
    assert Path(result['file_path']).exists()
    metadata = blob_storage.get_metadata(blob_id)
    assert metadata is not None

    # Delete it
    blob_storage.delete_blob(blob_id)

    # Verify it's gone
    assert not Path(result['file_path']).exists()
    with pytest.raises(BlobNotFoundError):
        blob_storage.get_metadata(blob_id)


def test_delete_blob_not_found(blob_storage):
    """Test deleting non-existent blob."""
    with pytest.raises(BlobNotFoundError):
        blob_storage.delete_blob("blob://9999999999-0123456789abcdef.txt")


def test_delete_blob_invalid_id(blob_storage):
    """Test deleting with invalid blob ID."""
    with pytest.raises(InvalidBlobIdError):
        blob_storage.delete_blob("invalid")


def test_get_file_path(blob_storage):
    """Test getting filesystem path for a blob."""
    # Upload a blob
    result = blob_storage.upload_blob(data=b"test data", filename="test.txt")
    blob_id = result['blob_id']

    # Get file path
    file_path = blob_storage.get_file_path(blob_id)

    assert file_path.exists()
    assert file_path.is_file()

    # Verify content
    with open(file_path, 'rb') as f:
        assert f.read() == b"test data"


def test_get_file_path_not_found(blob_storage):
    """Test getting file path for non-existent blob."""
    with pytest.raises(BlobNotFoundError):
        blob_storage.get_file_path("blob://9999999999-0123456789abcdef.txt")


def test_get_file_path_invalid_id(blob_storage):
    """Test getting file path with invalid blob ID."""
    with pytest.raises(InvalidBlobIdError):
        blob_storage.get_file_path("invalid")


def test_list_blobs_with_date_filters(blob_storage):
    """Test listing blobs with created_after and created_before filters."""
    from datetime import datetime, timedelta, timezone

    # Upload some blobs
    result1 = blob_storage.upload_blob(data=b"data1", filename="file1.txt", mime_type="text/plain")
    blob_storage.upload_blob(data=b"data2", filename="file2.txt", mime_type="text/plain")

    # Modify metadata for result1 to be older
    import json

    from mcp_mapped_resource_lib.path import get_metadata_path

    meta_path1 = get_metadata_path(result1['blob_id'], blob_storage.storage_root)
    with open(meta_path1) as f:
        metadata1 = json.load(f)

    old_time = datetime.now(timezone.utc) - timedelta(days=2)
    metadata1['created_at'] = old_time.isoformat()

    with open(meta_path1, 'w') as f:
        json.dump(metadata1, f)

    # Test created_after filter (lines 255-258)
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    result = blob_storage.list_blobs(created_after=yesterday)
    assert result['total'] == 1  # Only result2 should match

    # Test created_before filter (lines 261-264)
    one_day_ago = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    result = blob_storage.list_blobs(created_before=one_day_ago)
    assert result['total'] == 1  # Only result1 should match


def test_list_blobs_malformed_metadata_exception(blob_storage):
    """Test list_blobs handles malformed metadata gracefully."""
    # Upload a blob
    result = blob_storage.upload_blob(data=b"test", filename="test.txt", mime_type="text/plain")

    # Corrupt the metadata
    from mcp_mapped_resource_lib.path import get_metadata_path

    meta_path = get_metadata_path(result['blob_id'], blob_storage.storage_root)
    with open(meta_path, 'w') as f:
        f.write("invalid json{{{")

    # Should handle exception and skip malformed metadata (lines 268-270)
    result = blob_storage.list_blobs()
    assert result['total'] == 0


def test_delete_blob_removes_empty_directories(blob_storage):
    """Test delete_blob removes empty shard directories."""
    # Upload a blob
    result = blob_storage.upload_blob(data=b"test", filename="test.txt", mime_type="text/plain")
    blob_id = result['blob_id']
    file_path = Path(result['file_path'])

    # Get parent directories
    second_level = file_path.parent
    first_level = second_level.parent

    # Verify directories exist
    assert second_level.exists()
    assert first_level.exists()

    # Delete blob
    blob_storage.delete_blob(blob_id)

    # Empty directories should be removed (lines 324-325)
    assert not second_level.exists()
    assert not first_level.exists()


def test_get_file_path_with_path_traversal(blob_storage):
    """Test get_file_path detects path traversal attempts."""
    # This tests line 355 (path safety validation)
    # Try to use a blob ID that would pass basic validation but fail path safety
    # This is a theoretical test as validate_blob_id should catch most cases
    with pytest.raises(InvalidBlobIdError):
        blob_storage.get_file_path("blob://../../../etc/passwd")


def test_find_blob_by_hash_exception_handling(blob_storage):
    """Test _find_blob_by_hash handles exceptions gracefully."""
    # Upload a blob
    result = blob_storage.upload_blob(data=b"test", filename="test.txt", mime_type="text/plain")

    # Corrupt metadata

    from mcp_mapped_resource_lib.path import get_metadata_path

    meta_path = get_metadata_path(result['blob_id'], blob_storage.storage_root)
    with open(meta_path, 'w') as f:
        f.write("invalid json{{{")

    # Should handle exception and return None (lines 381-382)
    found = blob_storage._find_blob_by_hash("somehash")
    assert found is None


def test_matches_tags_filter_with_no_blob_tags(blob_storage):
    """Test _matches_tags_filter when blob has no tags."""
    # This tests line 416 (return False when blob_tags is None/empty)
    result = blob_storage.upload_blob(data=b"test", filename="test.txt", mime_type="text/plain")

    # List with tag filter
    result = blob_storage.list_blobs(tags=["sometag"])
    assert result['total'] == 0  # Blob has no tags, so shouldn't match
