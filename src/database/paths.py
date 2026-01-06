"""
Database path utilities.

Provides functions for resolving project paths and data directories.
"""

import os
import logging
from pathlib import Path
from typing import Optional

from ..utils.platform import get_project_root, get_data_dir


logger = logging.getLogger(__name__)


def get_default_db_path() -> Path:
    """
    Get the default main database path in ./data directory.

    This is the main database containing global settings, users, and sessions.
    Each library will have its own database.

    Returns ./data/main.db relative to the project root.
    """
    project_root = get_project_root()
    base_dir = project_root / 'data'

    # Create directory if it doesn't exist
    try:
        base_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError as e:
        logger.error(f"Permission denied creating data directory: {base_dir}")
        raise
    except Exception as e:
        logger.error(f"Error creating data directory {base_dir}: {e}")
        raise

    db_path = base_dir / 'main.db'
    logger.debug(f"Database path: {db_path}")

    return db_path


def get_library_data_dir(library_name: str) -> Path:
    """
    Get the data directory for a specific library.

    Args:
        library_name: Name of the library (e.g., 'Manga', 'Comics')

    Returns:
        Path to library-specific data directory (./data/<LibraryName>/)
    """
    data_dir = get_data_dir()
    library_dir = data_dir / library_name
    library_dir.mkdir(parents=True, exist_ok=True)
    return library_dir


def get_covers_dir(library_name: Optional[str] = None) -> Path:
    """
    Get the covers directory for a library.

    Args:
        library_name: Name of the library (optional, for library-specific covers)

    Returns:
        Path to covers directory:
        - With library_name: ./data/<LibraryName>/covers/
        - Without library_name: ./data/covers/ (shared/legacy)
    """
    logger.debug(f"[DB] get_covers_dir: library_name={library_name}")
    if library_name:
        library_dir = get_library_data_dir(library_name)
        covers_dir = library_dir / 'covers'
    else:
        # Shared covers directory (legacy/fallback)
        data_dir = get_data_dir()
        covers_dir = data_dir / 'covers'

    logger.debug(f"[DB] Covers directory: {covers_dir}, exists={covers_dir.exists()}")
    covers_dir.mkdir(parents=True, exist_ok=True)
    return covers_dir
