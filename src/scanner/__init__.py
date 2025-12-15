"""
Comic Scanner and Loader Module

Provides functionality for:
- Loading comic archives (CBZ, CBR, CB7)
- Generating thumbnails
- Extracting metadata
- Scanning library directories (single and multi-threaded)

This module has been refactored into focused submodules:
- base.py: ScanResult dataclass
- file_discovery.py: discover_files function
- structure_classifier.py: classify_series_structure, scan_library_structure
- folder_manager.py: create_folders function
- comic_processor.py: process_single_comic, extract_metadata
- series_builder.py: rebuild_series_table, build_series_tree_cache
- threaded_scanner.py: ThreadedScanner class (orchestrator)
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

from .base import ScanResult

# Note: threaded_scanner is available but not auto-imported
# to avoid import issues in standalone scripts
# Import directly when needed: from src.scanner.threaded_scanner import scan_library_threaded

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
    'ScanResult',
]
