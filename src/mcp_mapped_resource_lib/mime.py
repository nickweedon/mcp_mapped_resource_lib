"""MIME type detection and validation utilities."""

import mimetypes

try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False


def detect_mime_type(data: bytes, filename: str) -> str:
    """Detect MIME type from data and filename.

    Uses python-magic (if available) to detect from magic bytes,
    falls back to mimetypes module based on filename extension.

    Args:
        data: Binary data to analyze
        filename: Filename to use for extension-based detection

    Returns:
        Detected MIME type (e.g., "image/png", "application/pdf")
        Returns "application/octet-stream" if detection fails

    Example:
        >>> detect_mime_type(b"\\x89PNG\\r\\n...", "image.png")
        'image/png'
        >>> detect_mime_type(b"test", "file.txt")
        'text/plain'
    """
    # Try python-magic first (most accurate)
    if HAS_MAGIC and data:
        try:
            mime = magic.from_buffer(data, mime=True)
            if mime:
                return mime
        except Exception:
            # Fall through to extension-based detection
            pass

    # Fall back to filename extension
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or "application/octet-stream"


def validate_mime_type(mime_type: str, allowed: list[str] | None) -> bool:
    """Validate MIME type against allowed list.

    Supports wildcard matching (e.g., "image/*" matches "image/png").

    Args:
        mime_type: MIME type to validate (e.g., "image/png")
        allowed: List of allowed MIME types, or None to allow all

    Returns:
        True if mime_type is allowed, False otherwise

    Example:
        >>> validate_mime_type("image/png", ["image/*", "application/pdf"])
        True
        >>> validate_mime_type("text/plain", ["image/*"])
        False
        >>> validate_mime_type("anything", None)
        True
    """
    # None or empty list = allow all
    if not allowed:
        return True

    # Check for exact match or wildcard match
    for allowed_type in allowed:
        if allowed_type.endswith("/*"):
            # Wildcard match (e.g., "image/*")
            prefix = allowed_type[:-2]
            if mime_type.startswith(prefix + "/"):
                return True
        elif mime_type == allowed_type:
            # Exact match
            return True

    return False
