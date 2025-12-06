"""Tests for path utilities."""

import tempfile
from pathlib import Path

import pytest

from mcp_mapped_resource_lib.exceptions import InvalidBlobIdError
from mcp_mapped_resource_lib.path import (
    blob_id_to_path,
    ensure_storage_directories,
    get_metadata_path,
    get_shard_directories,
    sanitize_filename,
    validate_path_safety,
)


def test_blob_id_to_path():
    """Test blob ID to path translation."""
    blob_id = "blob://1733437200-a3f9d8c2b1e4f6a7.png"
    storage_root = "/mnt/blob-storage"

    path = blob_id_to_path(blob_id, storage_root)

    # Expected: /mnt/blob-storage/17/33/1733437200-a3f9d8c2b1e4f6a7.png
    assert str(path) == "/mnt/blob-storage/17/33/1733437200-a3f9d8c2b1e4f6a7.png"
    assert path.parent.name == "33"
    assert path.parent.parent.name == "17"


def test_blob_id_to_path_without_extension():
    """Test blob ID to path without extension."""
    blob_id = "blob://1733437200-a3f9d8c2b1e4f6a7"
    storage_root = "/mnt/blob-storage"

    path = blob_id_to_path(blob_id, storage_root)

    assert str(path) == "/mnt/blob-storage/17/33/1733437200-a3f9d8c2b1e4f6a7"


def test_blob_id_to_path_strips_protocol():
    """Test blob ID to path handles protocol prefix."""
    blob_id_with = "blob://1733437200-a3f9d8c2b1e4f6a7.png"
    blob_id_without = "1733437200-a3f9d8c2b1e4f6a7.png"
    storage_root = "/mnt/blob-storage"

    # Both should work and produce the same result
    path_with = blob_id_to_path(blob_id_with, storage_root)
    path_without = blob_id_to_path(blob_id_without, storage_root)

    # They should produce the same path
    assert path_with == path_without
    assert str(path_with) == "/mnt/blob-storage/17/33/1733437200-a3f9d8c2b1e4f6a7.png"


def test_blob_id_to_path_invalid_id():
    """Test blob ID to path rejects invalid IDs."""
    with pytest.raises(InvalidBlobIdError):
        blob_id_to_path("invalid", "/mnt/blob-storage")

    with pytest.raises(InvalidBlobIdError):
        blob_id_to_path("blob://../../../etc/passwd", "/mnt/blob-storage")


def test_get_metadata_path():
    """Test getting metadata file path."""
    blob_id = "blob://1733437200-a3f9d8c2b1e4f6a7.png"
    storage_root = "/mnt/blob-storage"

    meta_path = get_metadata_path(blob_id, storage_root)

    # Expected: /mnt/blob-storage/17/33/1733437200-a3f9d8c2b1e4f6a7.png.meta.json
    assert str(meta_path) == "/mnt/blob-storage/17/33/1733437200-a3f9d8c2b1e4f6a7.png.meta.json"
    assert meta_path.name.endswith(".meta.json")


def test_sanitize_filename():
    """Test filename sanitization."""
    assert sanitize_filename("normal_file.txt") == "normal_file.txt"
    assert sanitize_filename("file with spaces.txt") == "file_with_spaces.txt"
    assert sanitize_filename("../../etc/passwd") == "etc_passwd"
    assert sanitize_filename("<script>alert(1)</script>.html") == "script_alert_1_script_.html"
    assert sanitize_filename("my file (1).txt") == "my_file_1_.txt"  # Collapses multiple underscores
    assert sanitize_filename("file___name.txt") == "file_name.txt"  # Collapse underscores


def test_sanitize_filename_empty():
    """Test sanitization handles empty/invalid filenames."""
    assert sanitize_filename("") == "unnamed"
    assert sanitize_filename("...") == "unnamed"
    assert sanitize_filename("/") == "unnamed"


def test_ensure_storage_directories():
    """Test storage directory initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_root = Path(tmpdir) / "blob-storage"

        # Directory shouldn't exist yet
        assert not storage_root.exists()

        # Ensure it
        ensure_storage_directories(str(storage_root))

        # Now it should exist
        assert storage_root.exists()
        assert storage_root.is_dir()


def test_ensure_storage_directories_already_exists():
    """Test ensure_storage_directories works if directory exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Already exists
        ensure_storage_directories(tmpdir)

        # Should not raise error
        ensure_storage_directories(tmpdir)


def test_validate_path_safety():
    """Test path safety validation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_root = tmpdir

        # Safe path within storage root
        safe_path = Path(tmpdir) / "17" / "33" / "file.png"
        assert validate_path_safety(safe_path, storage_root)

        # Unsafe path outside storage root
        unsafe_path = Path("/etc/passwd")
        assert not validate_path_safety(unsafe_path, storage_root)


def test_get_shard_directories_empty():
    """Test getting shard directories from empty storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        shard_dirs = get_shard_directories(tmpdir)
        assert shard_dirs == []


def test_get_shard_directories():
    """Test getting shard directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create some shard directories
        (Path(tmpdir) / "17" / "33").mkdir(parents=True)
        (Path(tmpdir) / "17" / "34").mkdir(parents=True)
        (Path(tmpdir) / "18" / "01").mkdir(parents=True)

        shard_dirs = get_shard_directories(tmpdir)

        assert len(shard_dirs) == 3

        # Convert to strings for easier comparison
        shard_names = {str(d.relative_to(tmpdir)) for d in shard_dirs}
        assert shard_names == {"17/33", "17/34", "18/01"}


def test_get_shard_directories_ignores_hidden():
    """Test get_shard_directories ignores hidden files/directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create normal shard
        (Path(tmpdir) / "17" / "33").mkdir(parents=True)

        # Create hidden directory
        (Path(tmpdir) / ".hidden").mkdir()

        # Create hidden file
        (Path(tmpdir) / ".last_cleanup").touch()

        shard_dirs = get_shard_directories(tmpdir)

        assert len(shard_dirs) == 1
        assert shard_dirs[0].name == "33"
