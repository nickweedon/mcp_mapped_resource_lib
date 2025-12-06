"""Hash calculation utilities for blob storage."""

import hashlib


def calculate_sha256(data: bytes) -> str:
    """Calculate SHA256 hash of data.

    Args:
        data: Binary data to hash

    Returns:
        Hexadecimal SHA256 hash string

    Example:
        >>> calculate_sha256(b"test data")
        '916f0027a575074ce72a331777c3478d6513f786a591bd892da1a577bf2335f9'
    """
    return hashlib.sha256(data).hexdigest()
