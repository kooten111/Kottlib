"""
Comic Scanner and Loader Module

Provides functionality for:
- Loading comic archives (CBZ, CBR, CB7)
- Generating thumbnails
- Extracting metadata
- Scanning library directories (single and multi-threaded)
"""

from .comic_loader import (
    ComicArchive,
    CBZArchive,
    CBRArchive,
    CB7Archive,
    ComicPage,
    ComicInfo,
    open_comic,
    is_comic_file,
    get_comic_format,
)

# Note: threaded_scanner is available but not auto-imported
# to avoid import issues in standalone scripts
# Import directly when needed: from scanner.threaded_scanner import scan_library_threaded

__all__ = [
    'ComicArchive',
    'CBZArchive',
    'CBRArchive',
    'CB7Archive',
    'ComicPage',
    'ComicInfo',
    'open_comic',
    'is_comic_file',
    'get_comic_format',
]
