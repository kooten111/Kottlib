"""
API v2 Router - Tree Navigation

Endpoints for hierarchical tree navigation of libraries and folders.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ....constants import ROOT_FOLDER_MARKER
from ....database import get_library_by_id, get_all_libraries
from ....database.models import Comic, Folder as FolderModel
from ...dependencies import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/library/{library_id}/tree")
async def get_folder_tree(
    library_id: int,
    max_depth: int = 10,
    folder_id: Optional[int] = None,
    session: Session = Depends(get_db_session)
):
    """
    Get hierarchical folder tree for a library

    Returns nested folder structure with comic counts.
    Supports lazy loading via folder_id param.
    """
    # Get library
    library = get_library_by_id(session, library_id)
    if not library:
        raise HTTPException(status_code=404, detail="Library not found")

    # Helper to count comics in a folder (recursive or direct?)
    # For tree display, we usually want total count including subfolders
    def get_recursive_comic_count(f_id):
        return session.query(Comic).filter(
            Comic.library_id == library_id,
            Comic.folder_id == f_id
        ).count()

    # Helper to build a single node (shallow)
    def build_node(folder, include_children=False):
        # Count comics
        if folder.name == ROOT_FOLDER_MARKER:
            # Root count
            count = session.query(Comic).filter_by(library_id=library_id).count()
        else:
            count = get_recursive_comic_count(folder.id)

        node = {
            "id": folder.id,
            "name": folder.name,
            "type": "folder",
            "parent_id": folder.parent_id,
            "comic_count": count,
            "children": []  # Always initialize empty
        }

        if include_children:
            # Find direct children
            children = session.query(FolderModel).filter(
                FolderModel.library_id == library_id,
                FolderModel.parent_id == folder.id
            ).order_by(FolderModel.name).all()

            for child in children:
                node["children"].append(build_node(child, include_children=False))

        return node

    # If folder_id provided, return that folder with its children
    if folder_id is not None:
        if folder_id == 0:  # Convention for library root in some clients
            pass  # Fallthrough to library root logic
        else:
            target_folder = session.query(FolderModel).filter_by(
                id=folder_id,
                library_id=library_id
            ).first()
            if not target_folder:
                raise HTTPException(status_code=404, detail="Folder not found")

            # specific folder request -> return folder with children (depth 1)
            return JSONResponse(build_node(target_folder, include_children=True))

    # Library Root Logic (folder_id is None)
    # Get total comics
    total_comics = session.query(Comic).filter_by(library_id=library_id).count()

    tree = {
        "id": library.id,
        "name": library.name,
        "type": "library",
        "comic_count": total_comics,
        "children": []
    }

    # Find top-level folders
    # Top level means parent is None (or parent is ROOT_FOLDER_MARKER)
    root_folder_db = session.query(FolderModel).filter_by(
        library_id=library_id,
        name=ROOT_FOLDER_MARKER
    ).first()
    root_id = root_folder_db.id if root_folder_db else None

    query = session.query(FolderModel).filter(
        FolderModel.library_id == library_id
    )

    if root_id:
        query = query.filter(FolderModel.parent_id == root_id)
    else:
        query = query.filter(FolderModel.parent_id.is_(None))

    top_level = query.order_by(FolderModel.name).all()

    for folder in top_level:
        # Don't include ROOT_FOLDER_MARKER itself if it accidentally matches
        if folder.name == ROOT_FOLDER_MARKER:
            continue
        tree["children"].append(build_node(folder, include_children=False))

    return JSONResponse(tree)


@router.get("/libraries/series-tree")
async def get_libraries_series_tree(
    max_depth: int = 10,
    session: Session = Depends(get_db_session)
):
    """
    Get hierarchical tree of all libraries.

    OPTIMIZED: Returns only the list of libraries (shallow).
    Children are lazy-loaded via /library/{id}/tree.
    """
    # Get all libraries
    libraries = get_all_libraries(session)

    tree = []

    for library in libraries:
        # Count total comics in library
        total_comics = session.query(Comic).filter_by(library_id=library.id).count()

        tree.append({
            "id": library.id,
            "name": library.name,
            "type": "library",
            "comic_count": total_comics,
            "children": []  # Initialize empty for lazy loading
        })

    return JSONResponse(tree)
