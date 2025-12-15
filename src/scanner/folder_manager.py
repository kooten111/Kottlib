"""
Folder management for the scanner.

Provides functions for creating and managing folder records in the database.
"""

import logging
from pathlib import Path
from typing import List, Tuple

from src.database import (
    Database,
    create_folder,
    get_folder_by_path,
    get_or_create_root_folder,
)


logger = logging.getLogger(__name__)


def create_folders(
    db: Database,
    library_id: int,
    library_path: Path,
    folder_paths: List[Path]
) -> Tuple[dict, int]:
    """
    Create all folders in database and return mapping.

    YACReader compatibility: Creates a root folder (ID=1) for the library,
    and sets all top-level folders to have parent_id=1.

    Args:
        db: Database instance
        library_id: Library ID to create folders for
        library_path: Library root path
        folder_paths: List of folder paths to create

    Returns:
        Tuple of (folder_map, root_folder_id)
        - folder_map: Dict mapping folder path string to folder ID
        - root_folder_id: ID of the root folder for this library
    """
    folder_map = {}
    root_folder_id = None

    # Sort folders by depth to create parents first
    sorted_folders = sorted(folder_paths, key=lambda p: len(p.parts))

    with db.get_session() as session:
        # First, ensure root folder exists (YACReader convention)
        root_folder = get_or_create_root_folder(session, library_id, str(library_path))
        root_folder_id = root_folder.id
        logger.debug(f"Root folder ID={root_folder_id} for library {library_id}")

        for folder_path in sorted_folders:
            # Get or create folder
            folder = get_folder_by_path(session, library_id, str(folder_path))

            if not folder:
                # Find parent folder ID
                parent_path = folder_path.parent

                if parent_path == library_path:
                    # This is a top-level folder - parent is root
                    parent_id = root_folder_id
                elif str(parent_path) in folder_map:
                    # This is a subfolder - parent is another folder
                    parent_id = folder_map[str(parent_path)]
                else:
                    # Fallback: parent not found, make it top-level
                    parent_id = root_folder_id

                folder = create_folder(
                    session,
                    library_id=library_id,
                    path=str(folder_path),
                    name=folder_path.name,
                    parent_id=parent_id
                )

            folder_map[str(folder_path)] = folder.id

    return folder_map, root_folder_id
