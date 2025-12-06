"""Tests for hash utilities."""

from mcp_mapped_resource_lib.hash import calculate_sha256


def test_calculate_sha256():
    """Test SHA256 hash calculation."""
    data = b"test data"
    expected = "916f0027a575074ce72a331777c3478d6513f786a591bd892da1a577bf2335f9"
    assert calculate_sha256(data) == expected


def test_calculate_sha256_empty():
    """Test SHA256 with empty data."""
    data = b""
    expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert calculate_sha256(data) == expected


def test_calculate_sha256_deterministic():
    """Test SHA256 is deterministic."""
    data = b"test data"
    hash1 = calculate_sha256(data)
    hash2 = calculate_sha256(data)
    assert hash1 == hash2


def test_calculate_sha256_different_data():
    """Test SHA256 produces different hashes for different data."""
    data1 = b"test data 1"
    data2 = b"test data 2"
    hash1 = calculate_sha256(data1)
    hash2 = calculate_sha256(data2)
    assert hash1 != hash2
