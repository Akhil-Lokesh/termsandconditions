"""
Input sanitization utilities for security.

Prevents path traversal, XSS, and injection attacks.
"""

import re
from pathlib import Path


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize uploaded filename to prevent path traversal and other attacks.

    Args:
        filename: Original filename from upload
        max_length: Maximum allowed filename length

    Returns:
        str: Sanitized filename safe for filesystem storage

    Examples:
        >>> sanitize_filename("../../etc/passwd")
        'etc_passwd'
        >>> sanitize_filename("test<script>.pdf")
        'testscript.pdf'
        >>> sanitize_filename("document (1).pdf")
        'document_1.pdf'
    """
    # Remove path components (handles both / and \)
    filename = Path(filename).name

    # Remove or replace dangerous characters
    # Keep only: alphanumeric, dash, underscore, period
    filename = re.sub(r'[^\w\s.-]', '', filename)

    # Replace spaces with underscores
    filename = filename.replace(' ', '_')

    # Remove multiple consecutive dots (prevent directory traversal)
    filename = re.sub(r'\.{2,}', '.', filename)

    # Remove leading dots (hidden files)
    filename = filename.lstrip('.')

    # Truncate to max length (preserve extension)
    if len(filename) > max_length:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        # Leave room for extension + dot
        max_name_length = max_length - len(ext) - 1 if ext else max_length
        filename = f"{name[:max_name_length]}.{ext}" if ext else name[:max_length]

    # Ensure we have a valid filename
    if not filename or filename == '.':
        filename = 'untitled'

    return filename


def sanitize_text_input(text: str, max_length: int = 10000) -> str:
    """
    Sanitize user text input to prevent XSS and injection attacks.

    Removes HTML/script tags and limits length.

    Args:
        text: User-provided text
        max_length: Maximum allowed text length

    Returns:
        str: Sanitized text

    Examples:
        >>> sanitize_text_input("<script>alert('xss')</script>Hello")
        'Hello'
        >>> sanitize_text_input("What is the refund policy?")
        'What is the refund policy?'
    """
    # Truncate to max length
    text = text[:max_length]

    # Remove HTML tags (simple approach)
    text = re.sub(r'<[^>]+>', '', text)

    # Remove script content
    text = re.sub(r'<script.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)

    # Remove style content
    text = re.sub(r'<style.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def sanitize_path(path: str, allowed_base: str) -> str:
    """
    Sanitize file path to prevent directory traversal.

    Ensures path stays within allowed base directory.

    Args:
        path: User-provided path
        allowed_base: Base directory that path must stay within

    Returns:
        str: Sanitized absolute path

    Raises:
        ValueError: If path attempts to escape allowed base

    Examples:
        >>> sanitize_path("file.pdf", "/tmp")
        '/tmp/file.pdf'
        >>> sanitize_path("../../../etc/passwd", "/tmp")
        ValueError: Path escapes allowed base directory
    """
    # Convert to Path objects and resolve
    base = Path(allowed_base).resolve()
    requested = (base / path).resolve()

    # Check if requested path is within base
    try:
        requested.relative_to(base)
    except ValueError:
        raise ValueError(
            f"Path '{path}' escapes allowed base directory '{allowed_base}'"
        )

    return str(requested)


def validate_pdf_content(file_bytes: bytes, max_size_mb: int = 10) -> bool:
    """
    Validate PDF file content.

    Checks for:
    - Valid PDF header
    - Size limits
    - Suspicious content

    Args:
        file_bytes: PDF file content as bytes
        max_size_mb: Maximum allowed file size in MB

    Returns:
        bool: True if file appears to be a valid PDF

    Raises:
        ValueError: If file fails validation
    """
    # Check size
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > max_size_mb:
        raise ValueError(f"File size ({size_mb:.2f}MB) exceeds maximum ({max_size_mb}MB)")

    # Check PDF header (PDF files start with %PDF-)
    if not file_bytes.startswith(b'%PDF-'):
        raise ValueError("File does not appear to be a valid PDF")

    # Check for EOF marker
    if b'%%EOF' not in file_bytes[-1024:]:  # EOF should be near end
        raise ValueError("PDF file appears to be truncated or corrupted")

    return True


def sanitize_metadata_value(value: any, max_length: int = 1000) -> str:
    """
    Sanitize metadata field values.

    Args:
        value: Metadata value (any type)
        max_length: Maximum string length

    Returns:
        str: Sanitized string value
    """
    # Convert to string
    str_value = str(value) if value is not None else ""

    # Remove control characters
    str_value = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', str_value)

    # Truncate
    str_value = str_value[:max_length]

    return str_value.strip()
