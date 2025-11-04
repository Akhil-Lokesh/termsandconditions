"""Input validation utilities."""

import os
from typing import List
import logging

from app.utils.exceptions import InvalidFileTypeError, FileSizeExceededError

logger = logging.getLogger(__name__)


def validate_file_type(filename: str, allowed_types: List[str]) -> bool:
    """
    Validate file type by extension.

    Args:
        filename: File name
        allowed_types: List of allowed file extensions (e.g., [".pdf"])

    Returns:
        bool: True if file type is allowed

    Raises:
        InvalidFileTypeError: If file type is not allowed
    """
    _, ext = os.path.splitext(filename)
    ext = ext.lower()

    if ext not in allowed_types:
        raise InvalidFileTypeError(
            f"File type '{ext}' is not allowed. Allowed types: {allowed_types}"
        )

    return True


def validate_file_size(file_size: int, max_size_bytes: int) -> bool:
    """
    Validate file size.

    Args:
        file_size: File size in bytes
        max_size_bytes: Maximum allowed file size in bytes

    Returns:
        bool: True if file size is within limit

    Raises:
        FileSizeExceededError: If file size exceeds limit
    """
    if file_size > max_size_bytes:
        max_size_mb = max_size_bytes / (1024 * 1024)
        actual_size_mb = file_size / (1024 * 1024)
        raise FileSizeExceededError(
            f"File size ({actual_size_mb:.2f}MB) exceeds maximum allowed size ({max_size_mb:.2f}MB)"
        )

    return True


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing potentially dangerous characters.

    Args:
        filename: Original filename

    Returns:
        str: Sanitized filename
    """
    # Remove path separators and other dangerous characters
    filename = os.path.basename(filename)
    filename = "".join(c for c in filename if c.isalnum() or c in "._- ")
    filename = filename.strip()

    return filename or "document.pdf"
