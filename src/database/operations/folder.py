"""
Folder database operations.
"""

import time
import logging
from pathlib import Path
from typing import Optional, List

from sqlalchemy.orm import Session

from ...constants import ROOT_FOLDER_MARKER
from ..models import Folder, Comic


logger = logging.getLogger(__name__)


def create_folder(
    session: Session,
    library_id: int,
    path: str,
    name: str,
    parent_id: Optional[int] = None
) -> Folder:
    """Create a new folder."""
    now = int(time.time())

    folder = Folder(
        library_id=library_id,
        parent_id=parent_id,
        path=str(Path(path).resolve()),
        name=name,
        created_at=now,
        updated_at=now
    )

    session.add(folder)
    session.flush()  # Flush to get the ID without committing

    logger.debug(f"Created folder: {name}")
    return folder


def get_folder_by_id(session: Session, folder_id: int) -> Optional[Folder]:
    """Get folder by ID."""
    return session.query(Folder).filter_by(id=folder_id).first()


def get_folder_by_path(session: Session, library_id: int, path: str) -> Optional[Folder]:
    """Get folder by path."""
    return session.query(Folder).filter_by(
        library_id=library_id,
        path=str(Path(path).resolve())
    ).first()


def get_folders_in_library(session: Session, library_id: int) -> List[Folder]:
    """
    Get all folders in a library from the main database.
    """
    return session.query(Folder).filter_by(library_id=library_id).all()


def get_or_create_root_folder(session: Session, library_id: int, library_path: str) -> Folder:
    """
    Get or create the virtual root folder (ID=1) for a library.

    YACReader convention: Every library has a virtual root folder with ID=1
    that acts as a container for top-level folders and comics, but is never
    shown in the UI.

    Args:
        session: Database session
        library_id: Library ID
        library_path: Path to the library root

    Returns:
        Root folder (ID=1 for the library)
    """
    # Check if root folder already exists (ID=1)
    root = session.query(Folder).filter_by(id=1, library_id=library_id).first()

    if root:
        return root

    # Check if ANY folder with ID=1 exists (might be from another library)
    existing_id_1 = session.query(Folder).filter_by(id=1).first()

    if existing_id_1:
        # ID=1 is taken by another library's root folder
        # This is OK - each library can have its own root folder
        # But we need to find this library's root folder (parent_id=None with special marker)
        root = session.query(Folder).filter_by(
            library_id=library_id,
            parent_id=None,
            name=ROOT_FOLDER_MARKER
        ).first()

        if root:
            return root

    # Check if a root folder exists by path but finding by name failed
    # This prevents unique constraint violations if the root folder exists but has a different name
    root_by_path = session.query(Folder).filter_by(
        library_id=library_id,
        path=str(Path(library_path).resolve())
    ).first()

    if root_by_path:
        # We found the folder by path!
        # Update its name to __ROOT__ if it's not already
        if root_by_path.name != ROOT_FOLDER_MARKER:
            logger.warning(f"Found root folder by path but with name '{root_by_path.name}'. Renaming to '__ROOT__'.")
            root_by_path.name = "__ROOT__"
            session.add(root_by_path)
            session.flush()
        return root_by_path

    # Create new root folder
    now = int(time.time())

    # Try to create with ID=1
    root = Folder(
        library_id=library_id,
        parent_id=None,  # Root has no parent
        path=str(Path(library_path).resolve()),
        name=ROOT_FOLDER_MARKER,  # Special marker name
        created_at=now,
        updated_at=now
    )

    session.add(root)
    session.flush()  # Flush to get the auto-generated ID

    # Check if we got ID=1
    if root.id == 1:
        logger.debug(f"Created root folder with ID=1 for library {library_id}")
        return root
    else:
        # We didn't get ID=1, this means another library already has it
        # Keep this root folder but mark it specially
        logger.debug(f"Created root folder with ID={root.id} for library {library_id} (ID=1 taken)")
        return root


def get_subfolders(session: Session, parent_id: int) -> List[Folder]:
    """Get immediate subfolders of a folder."""
    return session.query(Folder).filter_by(parent_id=parent_id).all()


def get_first_comic_recursive(session: Session, folder_id: int, library_id: int):
    """
    Recursively find the first comic in a folder hierarchy.

    If the folder contains comics, return the first one (ordered by filename).
    If the folder contains only subfolders, recursively search the first subfolder.

    Args:
        session: Database session
        folder_id: ID of the folder to search in
        library_id: ID of the library (for scoping)

    Returns:
        Comic object or None if no comics found
    """
    # First, try to find a comic directly in this folder
    first_comic = session.query(Comic).filter_by(
        library_id=library_id,
        folder_id=folder_id
    ).order_by(Comic.filename).first()

    if first_comic:
        return first_comic

    # If no comics in this folder, recursively search subfolders
    subfolders = session.query(Folder).filter_by(
        parent_id=folder_id
    ).order_by(Folder.name).all()

    for subfolder in subfolders:
        comic = get_first_comic_recursive(session, subfolder.id, library_id)
        if comic:
            return comic

    return None
