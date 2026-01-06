"""
Shared utilities for comic loaders.

This module contains utility functions and constants used by multiple loader
implementations.
"""

from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Supported image extensions for comic pages
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif'}


def detect_archive_format(file_path: Path) -> Optional[str]:
    """
    Detect actual archive format by reading file magic numbers.

    This handles cases where files have incorrect extensions (e.g., .cbr file
    that's actually a ZIP archive).

    Args:
        file_path: Path to the archive file

    Returns:
        'zip', 'rar', '7z', or None if format cannot be determined
    """
    try:
        with open(file_path, 'rb') as f:
            header = f.read(16)

        if not header:
            return None

        # ZIP magic number: 50 4B (PK)
        if header[:2] == b'PK':
            return 'zip'

        # RAR magic numbers
        # RAR 4.x: 52 61 72 21 1A 07 00 (Rar!\x1a\x07\x00)
        # RAR 5.x: 52 61 72 21 1A 07 01 00 (Rar!\x1a\x07\x01\x00)
        if header[:4] == b'Rar!':
            return 'rar'

        # 7z magic number: 37 7A BC AF 27 1C
        if header[:6] == b'7z\xbc\xaf\x27\x1c':
            return '7z'

        return None
    except Exception as e:
        logger.debug(f"Failed to detect format for {file_path}: {e}")
        return None


def is_comic_file(file_path: Path) -> bool:
    """
    Check if file is a supported comic format.
    
    Args:
        file_path: Path to check
    
    Returns:
        True if file extension indicates a comic format
    """
    return file_path.suffix.lower() in {'.cbz', '.cbr', '.cb7', '.zip'}


def get_comic_format(file_path: Path) -> Optional[str]:
    """
    Get comic format type from file extension.
    
    Args:
        file_path: Path to the comic file
    
    Returns:
        Format string ('CBZ', 'CBR', 'CB7') or None if not supported
    """
    ext = file_path.suffix.lower()
    formats = {
        '.cbz': 'CBZ',
        '.cbr': 'CBR',
        '.cb7': 'CB7',
        '.zip': 'CBZ',  # .zip files are treated as CBZ
    }
    return formats.get(ext)
