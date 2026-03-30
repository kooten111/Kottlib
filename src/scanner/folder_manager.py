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
                # Calculate parent recursively (creates it if missing)
                parent_id = _get_or_create_parent_recursive(
                    session, library_id, folder_path, folder_map, root_folder_id, library_path
                )

                folder = create_folder(
                    session,
                    library_id=library_id,
                    path=str(folder_path),
                    name=folder_path.name,
                    parent_id=parent_id
                )
            else:
                 # Check/Fix existing parent
                 expected_parent_id = _get_or_create_parent_recursive(
                    session, library_id, folder_path, folder_map, root_folder_id, library_path
                 )
                 
                 if folder.parent_id != expected_parent_id:
                     logger.info(f"Fixing parent for {folder.name}: {folder.parent_id} -> {expected_parent_id}")
                     folder.parent_id = expected_parent_id
            
            folder_map[str(folder_path)] = folder.id

    # Second pass: Ensure hierarchy using get_or_create_parent logic for everything
    # This is cleaner than mixing it with the creation loop
    return folder_map, root_folder_id

_MAX_FOLDER_DEPTH = 100

def _get_or_create_parent_recursive(session, library_id: int, folder_path: Path, folder_map: dict, root_folder_id: int, library_path: Path, _depth: int = 0) -> int:
    """
    Recursively find or create the parent ID for a given folder path.
    """
    if _depth > _MAX_FOLDER_DEPTH:
        raise RuntimeError(f"Folder hierarchy exceeds max depth ({_MAX_FOLDER_DEPTH}) at: {folder_path}")

    parent_path = folder_path.parent
    
    # Base case: Parent is library root
    if parent_path == library_path:
        return root_folder_id
        
    # Check map (fastest)
    if str(parent_path) in folder_map:
        return folder_map[str(parent_path)]
        
    # Check DB
    parent_db = get_folder_by_path(session, library_id, str(parent_path))
    if parent_db:
        folder_map[str(parent_path)] = parent_db.id
        return parent_db.id
        
    # Parent missing: Recursively create grandparent, then create parent
    grandparent_id = _get_or_create_parent_recursive(session, library_id, parent_path, folder_map, root_folder_id, library_path, _depth + 1)
    
    # Create the missing parent
    logger.info(f"Creating missing parent folder: {parent_path.name}")
    new_parent = create_folder(
        session,
        library_id=library_id,
        path=str(parent_path),
        name=parent_path.name,
        parent_id=grandparent_id
    )
    folder_map[str(parent_path)] = new_parent.id
    return new_parent.id
