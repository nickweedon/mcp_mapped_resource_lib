"""Tests for blob ID utilities."""

import time

import pytest

from mcp_mapped_resource_lib.blob_id import (
    create_blob_id,
    parse_blob_id,
    strip_blob_protocol,
    validate_blob_id,
)
from mcp_mapped_resource_lib.exceptions import InvalidBlobIdError


def test_create_blob_id_without_extension():
    """Test blob ID creation without extension."""
    blob_id = create_blob_id()

    assert blob_id.startswith("blob://")
    assert validate_blob_id(blob_id)

    # Should have format: blob://TIMESTAMP-HASH
    parts = blob_id[7:].split("-")
    assert len(parts) == 2
    assert len(parts[0]) == 10  # Timestamp
    assert len(parts[1]) == 16  # Hash


def test_create_blob_id_with_extension():
    """Test blob ID creation with extension."""
    blob_id = create_blob_id("png")

    assert blob_id.startswith("blob://")
    assert blob_id.endswith(".png")
    assert validate_blob_id(blob_id)


def test_create_blob_id_extension_normalization():
    """Test extension is normalized (lowercase, leading dot)."""
    blob_id1 = create_blob_id(".PNG")
    blob_id2 = create_blob_id("PNG")

    assert blob_id1.endswith(".png")
    assert blob_id2.endswith(".png")


def test_create_blob_id_uniqueness():
    """Test blob IDs are unique."""
    blob_ids = set()

    for _ in range(100):
        blob_id = create_blob_id()
        assert blob_id not in blob_ids
        blob_ids.add(blob_id)


def test_create_blob_id_timestamp():
    """Test blob ID contains current timestamp."""
    before = int(time.time())
    blob_id = create_blob_id()
    after = int(time.time())

    components = parse_blob_id(blob_id)
    timestamp = components['timestamp']

    assert before <= timestamp <= after


def test_parse_blob_id_without_extension():
    """Test parsing blob ID without extension."""
    blob_id = "blob://1733437200-a3f9d8c2b1e4f6a7"
    components = parse_blob_id(blob_id)

    assert components['timestamp'] == 1733437200
    assert components['hash'] == 'a3f9d8c2b1e4f6a7'
    assert components['extension'] is None


def test_parse_blob_id_with_extension():
    """Test parsing blob ID with extension."""
    blob_id = "blob://1733437200-a3f9d8c2b1e4f6a7.png"
    components = parse_blob_id(blob_id)

    assert components['timestamp'] == 1733437200
    assert components['hash'] == 'a3f9d8c2b1e4f6a7'
    assert components['extension'] == 'png'


def test_parse_blob_id_invalid():
    """Test parsing invalid blob ID raises error."""
    with pytest.raises(InvalidBlobIdError):
        parse_blob_id("invalid")

    with pytest.raises(InvalidBlobIdError):
        parse_blob_id("blob://invalid")

    with pytest.raises(InvalidBlobIdError):
        parse_blob_id("blob://../../../etc/passwd")


def test_validate_blob_id_valid():
    """Test validation of valid blob IDs."""
    assert validate_blob_id("blob://1733437200-a3f9d8c2b1e4f6a7")
    assert validate_blob_id("blob://1733437200-a3f9d8c2b1e4f6a7.png")
    assert validate_blob_id("blob://9999999999-0123456789abcdef.txt")


def test_validate_blob_id_invalid_format():
    """Test validation rejects invalid formats."""
    assert not validate_blob_id("invalid")
    assert not validate_blob_id("blob://")
    assert not validate_blob_id("blob://123")
    assert not validate_blob_id("blob://1733437200")  # Missing hash
    assert not validate_blob_id("blob://1733437200-abc")  # Hash too short
    assert not validate_blob_id("blob://1733437200-a3f9d8c2b1e4f6a7g")  # Invalid hex


def test_validate_blob_id_path_traversal():
    """Test validation rejects path traversal attempts."""
    assert not validate_blob_id("blob://../../../etc/passwd")
    assert not validate_blob_id("blob://1733437200-a3f9d8c2b1e4f6a7/../../../etc/passwd")
    assert not validate_blob_id("blob://1733437200-a3f9d8c2b1e4f6a7/../../file")
    assert not validate_blob_id("blob://1733437200-a3f9d8c2b1e4f6a7\\..\\file")
    # Test backslash detection (line 117)
    assert not validate_blob_id("blob://1733437200\\a3f9d8c2b1e4f6a7")
    # Test path separator after protocol (line 122)
    assert not validate_blob_id("blob://1733437200-a3f9d8c2b1e4f6a7/subdir")


def test_validate_blob_id_protocol_variations():
    """Test validation handles protocol variations."""
    # Without blob:// prefix should fail
    assert not validate_blob_id("1733437200-a3f9d8c2b1e4f6a7.png")

    # Double slashes should fail
    assert not validate_blob_id("blob:///1733437200-a3f9d8c2b1e4f6a7.png")


def test_strip_blob_protocol():
    """Test stripping blob:// protocol."""
    assert strip_blob_protocol("blob://1733437200-a3f9d8c2b1e4f6a7.png") == "1733437200-a3f9d8c2b1e4f6a7.png"
    assert strip_blob_protocol("1733437200-a3f9d8c2b1e4f6a7.png") == "1733437200-a3f9d8c2b1e4f6a7.png"


def test_blob_id_roundtrip():
    """Test creating, parsing, and validating blob ID."""
    blob_id = create_blob_id("txt")

    # Validate
    assert validate_blob_id(blob_id)

    # Parse
    components = parse_blob_id(blob_id)
    assert components['extension'] == 'txt'
    assert isinstance(components['timestamp'], int)
    assert isinstance(components['hash'], str)
    assert len(components['hash']) == 16
