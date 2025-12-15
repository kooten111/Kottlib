"""
File discovery utilities for the scanner.

Provides functions for discovering comic files in a library directory.
"""

import logging
from pathlib import Path
from typing import List, Optional, Tuple

from .comic_loader import is_comic_file


logger = logging.getLogger(__name__)


def discover_files(library_path: Path) -> Tuple[List[Tuple[Path, Optional[Path]]], List[Path]]:
    """
    Recursively discover all comic files and folders.

    Args:
        library_path: Path to library root directory

    Returns:
        Tuple of (comic_files, folders)
        comic_files: List of (file_path, parent_folder_path) tuples
        folders: List of folder paths
    """
    comic_files = []
    folders = []

    def scan_dir(current_path: Path, parent_folder: Optional[Path] = None):
        """Recursively scan directory."""
        try:
            for item in current_path.iterdir():
                # Skip hidden files/folders
                if item.name.startswith('.'):
                    continue

                if item.is_dir():
                    folders.append(item)
                    # Recurse into subfolder
                    scan_dir(item, parent_folder=item)

                elif item.is_file() and is_comic_file(item):
                    comic_files.append((item, parent_folder))

        except PermissionError:
            logger.warning(f"Permission denied: {current_path}")
        except Exception as e:
            logger.error(f"Error scanning {current_path}: {e}")

    scan_dir(library_path)
    return comic_files, folders
