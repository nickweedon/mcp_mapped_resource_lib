"""Blob identifier generation, parsing, and validation."""

import re
import secrets
import time

from .exceptions import InvalidBlobIdError
from .types import BlobIdComponents

# Regex pattern for blob ID validation
# Format: blob://TIMESTAMP-HASH.EXT
# Example: blob://1733437200-a3f9d8c2b1e4f6a7.png
BLOB_ID_PATTERN = re.compile(r'^blob://(\d{10})-([a-f0-9]{16})(\.[a-z0-9]+)?$')


def create_blob_id(extension: str | None = None) -> str:
    """Generate a unique blob identifier.

    The blob ID format is: blob://TIMESTAMP-HASH.EXT
    - TIMESTAMP: 10-digit Unix timestamp
    - HASH: 16-character hexadecimal random string
    - EXT: Optional file extension (e.g., ".png", ".pdf")

    Args:
        extension: Optional file extension (with or without leading dot)

    Returns:
        Unique blob identifier string

    Example:
        >>> blob_id = create_blob_id("png")
        >>> blob_id.startswith("blob://")
        True
        >>> blob_id.endswith(".png")
        True
    """
    timestamp = int(time.time())
    random_hash = secrets.token_hex(8)  # 8 bytes = 16 hex characters

    # Normalize extension (ensure leading dot, lowercase)
    if extension:
        if not extension.startswith("."):
            extension = f".{extension}"
        extension = extension.lower()
        # Remove any invalid characters from extension
        extension = re.sub(r'[^a-z0-9.]', '', extension)
    else:
        extension = ""

    return f"blob://{timestamp}-{random_hash}{extension}"


def parse_blob_id(blob_id: str) -> BlobIdComponents:
    """Parse a blob ID into its components.

    Args:
        blob_id: Blob identifier to parse

    Returns:
        Dictionary with timestamp, hash, and extension components

    Raises:
        InvalidBlobIdError: If blob_id format is invalid

    Example:
        >>> components = parse_blob_id("blob://1733437200-a3f9d8c2b1e4f6a7.png")
        >>> components['timestamp']
        1733437200
        >>> components['hash']
        'a3f9d8c2b1e4f6a7'
        >>> components['extension']
        'png'
    """
    match = BLOB_ID_PATTERN.match(blob_id)
    if not match:
        raise InvalidBlobIdError(f"Invalid blob ID format: {blob_id}")

    timestamp_str, hash_str, ext_str = match.groups()

    return BlobIdComponents(
        timestamp=int(timestamp_str),
        hash=hash_str,
        extension=ext_str[1:] if ext_str else None  # Remove leading dot
    )


def validate_blob_id(blob_id: str) -> bool:
    """Validate blob ID format and security.

    Checks:
    - Format matches blob://TIMESTAMP-HASH.EXT pattern
    - No path traversal attempts (../, //, \\)
    - Timestamp is 10 digits
    - Hash is 16 hexadecimal characters
    - Extension (if present) is alphanumeric

    Args:
        blob_id: Blob identifier to validate

    Returns:
        True if valid, False otherwise

    Example:
        >>> validate_blob_id("blob://1733437200-a3f9d8c2b1e4f6a7.png")
        True
        >>> validate_blob_id("blob://../../../etc/passwd")
        False
        >>> validate_blob_id("invalid")
        False
    """
    # Check basic format
    if not BLOB_ID_PATTERN.match(blob_id):
        return False

    # Check for path traversal attempts
    if ".." in blob_id or "\\" in blob_id:
        return False

    # Additional security check: ensure no path separators after protocol
    blob_id_without_protocol = blob_id[7:]  # Remove "blob://"
    if "/" in blob_id_without_protocol or "\\" in blob_id_without_protocol:
        return False

    return True


def strip_blob_protocol(blob_id: str) -> str:
    """Remove the 'blob://' protocol prefix from a blob ID.

    Args:
        blob_id: Blob identifier with or without protocol

    Returns:
        Blob ID without protocol prefix

    Example:
        >>> strip_blob_protocol("blob://1733437200-a3f9d8c2b1e4f6a7.png")
        '1733437200-a3f9d8c2b1e4f6a7.png'
        >>> strip_blob_protocol("1733437200-a3f9d8c2b1e4f6a7.png")
        '1733437200-a3f9d8c2b1e4f6a7.png'
    """
    if blob_id.startswith("blob://"):
        return blob_id[7:]
    return blob_id
