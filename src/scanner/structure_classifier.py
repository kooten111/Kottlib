"""
Structure classification for the scanner.

Provides logic to classify library folder structure types
(simple, nested, unpacked) for proper series detection.
"""

import logging
from pathlib import Path
from typing import Dict


logger = logging.getLogger(__name__)


# Archive file extensions
ARCHIVE_EXTS = {'.cbz', '.cbr', '.zip', '.rar', '.7z', '.epub', '.cb7'}
# Image file extensions
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff', '.tif'}


def classify_series_structure(series_path: Path) -> str:
    """
    Determines if a Series folder is Simple, Nested, or Unpacked
    based on the Hybrid Hierarchy rules.

    Args:
        series_path: Path to the series folder to classify

    Returns:
        One of: "simple", "nested", "unpacked", "unknown",
                "Empty Folder", or "Error: ..." strings
    """
    try:
        # Get all items in the series folder
        contents = list(series_path.iterdir())
    except OSError:
        return "Error: Access Denied"

    if not contents:
        return "Empty Folder"

    # Get list of sub-directories to check for Modes 2 and 3
    subdirs = [d for d in contents if d.is_dir()]
    
    if subdirs:
        # We verify the structure by checking the content of the first sub-directory found.
        # (Assumes consistent structure within a single series folder)
        first_subdir = subdirs[0]
        try:
            subdir_contents = list(first_subdir.iterdir())
            
            # 2. Check for MODE 2: Franchise Collection
            # Logic: Do the sub-directories contain archives?
            if any(f.is_file() and f.suffix.lower() in ARCHIVE_EXTS for f in subdir_contents):
                return "nested"
            
            # 3. Check for MODE 3: Unpacked/Raw
            # Logic: Do the sub-directories contain images?
            if any(f.is_file() and f.suffix.lower() in IMAGE_EXTS for f in subdir_contents):
                return "unpacked"

            # 4. Check for MODE 3: Unpacked/Raw (Nested in Chapter folder)
            # If we found directories but no archives/images, look one level deeper
            grandchild_subdirs = [d for d in subdir_contents if d.is_dir()]
            if grandchild_subdirs:
                first_grandchild = grandchild_subdirs[0]
                try:
                    grandchild_contents = list(first_grandchild.iterdir())
                    if any(f.is_file() and f.suffix.lower() in IMAGE_EXTS for f in grandchild_contents):
                        return "unpacked"
                except OSError:
                    pass
                
        except OSError:
            return "Error: Subdir Access Denied"

    # 1. Check for MODE 1: Simple Series
    # Logic: Does it contain archive files directly?
    # We check this LAST so that mixed folders (files + subfolders) are treated as nested/franchise
    has_archives = any(f.is_file() and f.suffix.lower() in ARCHIVE_EXTS for f in contents)
    if has_archives:
        return "simple"

    return "unknown"


def scan_library_structure(library_path: Path) -> Dict[str, str]:
    """
    Scan the library structure to determine the mode of each top-level folder.

    Args:
        library_path: Path to the library root

    Returns:
        Dictionary mapping folder name to structure mode
    """
    structure_cache = {}
    
    logger.info("Scanning library structure...")
    try:
        for item in library_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                mode = classify_series_structure(item)
                structure_cache[item.name] = mode
                logger.debug(f"Structure detected for {item.name}: {mode}")
    except Exception as e:
        logger.error(f"Error scanning structure: {e}")
    
    return structure_cache
