"""
Comic archive loaders package.

This package provides loader implementations for various comic archive formats:
- CBZ (ZIP format)
- CBR (RAR format)
- CB7 (7-Zip format)

All loaders inherit from the ComicArchive base class and provide a unified
interface for reading comic files.
"""

from .base import ComicArchive
from .zip import CBZArchive
from .rar import CBRArchive
from .sevenzip import CB7Archive, SevenZipCliArchive
from .utils import detect_archive_format, is_comic_file, get_comic_format, IMAGE_EXTENSIONS

__all__ = [
    'ComicArchive',
    'CBZArchive',
    'CBRArchive',
    'CB7Archive',
    'SevenZipCliArchive',
    'detect_archive_format',
    'is_comic_file',
    'get_comic_format',
    'IMAGE_EXTENSIONS',
]
