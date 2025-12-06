"""Tests for MIME type utilities."""

from mcp_mapped_resource_lib.mime import detect_mime_type, validate_mime_type


def test_detect_mime_type_from_extension():
    """Test MIME type detection from file extension."""
    mime = detect_mime_type(b"", "test.txt")
    assert mime == "text/plain"

    mime = detect_mime_type(b"", "image.png")
    assert mime == "image/png"

    mime = detect_mime_type(b"", "document.pdf")
    assert mime == "application/pdf"


def test_detect_mime_type_unknown():
    """Test MIME type detection for unknown extensions."""
    mime = detect_mime_type(b"", "file.unknown_ext_xyz")
    assert mime == "application/octet-stream"


def test_validate_mime_type_exact_match():
    """Test MIME type validation with exact match."""
    assert validate_mime_type("image/png", ["image/png", "image/jpeg"])
    assert validate_mime_type("image/jpeg", ["image/png", "image/jpeg"])
    assert not validate_mime_type("text/plain", ["image/png", "image/jpeg"])


def test_validate_mime_type_wildcard():
    """Test MIME type validation with wildcards."""
    assert validate_mime_type("image/png", ["image/*"])
    assert validate_mime_type("image/jpeg", ["image/*"])
    assert not validate_mime_type("text/plain", ["image/*"])

    assert validate_mime_type("application/pdf", ["application/*"])
    assert not validate_mime_type("image/png", ["application/*"])


def test_validate_mime_type_mixed():
    """Test MIME type validation with mixed exact and wildcard."""
    allowed = ["image/*", "application/pdf", "text/plain"]

    assert validate_mime_type("image/png", allowed)
    assert validate_mime_type("image/jpeg", allowed)
    assert validate_mime_type("application/pdf", allowed)
    assert validate_mime_type("text/plain", allowed)
    assert not validate_mime_type("application/json", allowed)


def test_validate_mime_type_allow_all():
    """Test MIME type validation with None (allow all)."""
    assert validate_mime_type("image/png", None)
    assert validate_mime_type("text/plain", None)
    assert validate_mime_type("application/octet-stream", None)


def test_validate_mime_type_empty_list():
    """Test MIME type validation with empty list (allow all)."""
    assert validate_mime_type("image/png", [])
    assert validate_mime_type("text/plain", [])
