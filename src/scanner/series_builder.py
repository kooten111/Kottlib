"""
Series builder for the scanner.

Provides functions to rebuild the series table and cache
the series tree structure after scanning.
"""

import json
import logging
import re
import time

from src.database import (
    Database,
    update_library_series_tree_cache,
)
from src.database.models import Folder as FolderModel, Comic, Series as SeriesModel

from sqlalchemy import func


logger = logging.getLogger(__name__)


def rebuild_series_table(db: Database, library_id: int) -> None:
    """
    Rebuild the series table from comics.

    Groups comics by series and creates/updates series records.
    This ensures the series table is always in sync with the comics.

    Args:
        db: Database instance
        library_id: Library ID to rebuild series for
    """
    logger.info(f"Rebuilding series table for library {library_id}...")

    with db.get_session() as session:
        # Get all unique series names with comic counts
        series_data = session.query(
            Comic.series,
            func.count(Comic.id).label('comic_count')
        ).filter(
            Comic.library_id == library_id,
            Comic.series.isnot(None)
        ).group_by(
            Comic.series
        ).all()

        if not series_data:
            logger.info("No series found in comics")
            return

        created = 0
        updated = 0
        now = int(time.time())

        for series_name, comic_count in series_data:
            if not series_name:
                continue

            # Check if series already exists
            existing = session.query(SeriesModel).filter(
                SeriesModel.library_id == library_id,
                SeriesModel.name == series_name
            ).first()

            if existing:
                # Update comic count
                existing.comic_count = comic_count
                existing.total_issues = comic_count
                existing.updated_at = now
                updated += 1
            else:
                # Create new series
                new_series = SeriesModel(
                    library_id=library_id,
                    name=series_name,
                    display_name=series_name,
                    comic_count=comic_count,
                    total_issues=comic_count,
                    created_at=now,
                    updated_at=now
                )
                session.add(new_series)
                created += 1

        session.commit()
        logger.info(f"Series table rebuilt: {created} created, {updated} updated")


def build_series_tree_cache(db: Database, library_id: int) -> None:
    """
    Build and cache the series tree structure for this library.

    This pre-computes the folder/comic hierarchy to avoid N+1 queries
    on every page load. The cache is stored as JSON in the library record.

    Args:
        db: Database instance
        library_id: Library ID to build tree cache for
    """
    logger.info(f"Building series tree cache for library {library_id}...")

    with db.get_session() as session:
        # Get all folders and comics in one query each (efficient)
        all_folders = session.query(FolderModel).filter_by(
            library_id=library_id
        ).all()

        all_comics = session.query(Comic).filter_by(
            library_id=library_id
        ).all()

        # Build lookup maps for efficient access
        folders_by_id = {f.id: f for f in all_folders}
        comics_by_folder = {}
        for comic in all_comics:
            if comic.folder_id not in comics_by_folder:
                comics_by_folder[comic.folder_id] = []
            comics_by_folder[comic.folder_id].append(comic)

        def build_folder_node(folder, depth=0, max_depth=10):
            """Build tree node for a folder recursively."""
            if depth > max_depth or folder.name == "__ROOT__":
                return None

            # Recursively build children
            children = []
            cover_hash = None
            
            # Add comics directly in this folder
            comics_in_folder = comics_by_folder.get(folder.id, [])
            # Sort comics to pick the first one (e.g. Vol 1 or Issue 1) as cover
            sorted_comics = sorted(
                comics_in_folder,
                key=lambda c: (c.volume or 0, c.issue_number or 0, c.title or c.filename)
            )
            
            if sorted_comics:
                cover_hash = sorted_comics[0].hash

            # Get subfolders
            subfolders = [f for f in all_folders if f.parent_id == folder.id]

            # Build subfolder nodes recursively
            subfolder_nodes = []
            for subfolder in sorted(subfolders, key=lambda f: f.name):
                subfolder_node = build_folder_node(subfolder, depth + 1)
                if subfolder_node:
                    subfolder_nodes.append(subfolder_node)
                    # If we don't have a cover yet, use the first subfolder's cover
                    if not cover_hash and subfolder_node.get("hash"):
                        cover_hash = subfolder_node.get("hash")

            # Add subfolders to children
            children.extend(subfolder_nodes)
            
            # Add comics to children
            for comic in sorted_comics:
                # For single comics, strip file extension from filename
                display_name = comic.title
                if not display_name:
                    display_name = re.sub(r'\.(cbz|cbr|cb7|cbt)$', '', comic.filename, flags=re.IGNORECASE)
                
                comic_node = {
                    "id": comic.id,
                    "name": display_name,
                    "type": "comic",
                    "libraryId": library_id,
                    "folderId": folder.id,
                    "hash": comic.hash,
                    "totalPages": comic.num_pages,
                    "volume": comic.volume,
                    "issueNumber": comic.issue_number
                }
                children.append(comic_node)

            # Count total comics (including subfolders)
            total_comic_count = len(comics_in_folder)
            for subfolder_node in subfolder_nodes:
                total_comic_count += subfolder_node.get("comicCount", 0)

            return {
                "id": f"folder-{library_id}-{folder.id}",
                "folderId": folder.id,
                "name": folder.name,
                "type": "folder",
                "libraryId": library_id,
                "comicCount": total_comic_count,
                "children": children
            }

        # Find root folder
        root_folder = next((f for f in all_folders if f.name == "__ROOT__"), None)
        if not root_folder:
            logger.warning(f"No root folder found for library {library_id}")
            return

        # Get top-level folders
        top_level_folders = [
            f for f in all_folders
            if f.parent_id == root_folder.id or (f.parent_id is None and f.name != "__ROOT__")
        ]

        # Build tree structure
        tree_children = []
        for folder in sorted(top_level_folders, key=lambda f: f.name):
            folder_node = build_folder_node(folder)
            if folder_node:
                tree_children.append(folder_node)

        # Add root folder comics
        root_comics = comics_by_folder.get(root_folder.id, [])
        for comic in sorted(root_comics, key=lambda c: (c.volume or 0, c.issue_number or 0, c.title or c.filename)):
            # For single comics, strip file extension from filename
            display_name = comic.title
            if not display_name:
                # Strip common comic extensions (.cbz, .cbr, .cb7, .cbt)
                display_name = re.sub(r'\.(cbz|cbr|cb7|cbt)$', '', comic.filename, flags=re.IGNORECASE)
            
            comic_info = {
                "id": comic.id,
                "name": display_name,
                "type": "comic",
                "libraryId": library_id,
                "hash": comic.hash,
                "totalPages": comic.num_pages,
                "volume": comic.volume,
                "issueNumber": comic.issue_number
            }
            tree_children.append(comic_info)

        # Serialize to JSON and store in database
        tree_json = json.dumps(tree_children)
        update_library_series_tree_cache(session, library_id, tree_json)
        session.commit()

        logger.info(f"Series tree cache built and stored for library {library_id}")
