"""
Browse response helpers for library folder/series views.

Extracted from v2/series.py to keep the router focused on HTTP wiring.
"""

import json
import logging
from copy import deepcopy
from time import perf_counter
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import unquote

from fastapi.responses import JSONResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..constants import ROOT_FOLDER_MARKER
from ..database.models import Comic, Folder, ReadingProgress, Series

logger = logging.getLogger(__name__)

SORT_ALIASES = {
    "date_added": "recent",
    "recently_added": "recent",
    "last_updated": "updated",
    "recently_updated": "updated",
    "date_updated": "updated",
}

COMIC_EXTENSIONS = (".cbz", ".cbr", ".cb7", ".cbt", ".CBZ", ".CBR", ".CB7", ".CBT")


class BrowsePathNotFoundError(Exception):
    """Raised when a browse path segment cannot be resolved."""


def normalize_sort(sort: Optional[str]) -> str:
    """Normalize sort aliases used by different clients into canonical values."""
    normalized = (sort or "name").lower()
    return SORT_ALIASES.get(normalized, normalized)


def cache_safe_copy(data: dict) -> dict:
    """Return a deep-copied response with reading-progress fields stripped."""
    cache_data = deepcopy(data)
    items = cache_data.get("items", [])
    for item in items:
        if item.get("type") == "comic":
            item["progress_percent"] = 0
            item["is_completed"] = False
            item["current_page"] = 0

    comic = cache_data.get("comic")
    if isinstance(comic, dict):
        comic["progress_percent"] = 0
        comic["is_completed"] = False
        comic["current_page"] = 0

    first_comic_metadata = cache_data.get("first_comic_metadata")
    if isinstance(first_comic_metadata, dict):
        first_comic_metadata["progress_percent"] = 0
        first_comic_metadata["is_completed"] = False
        first_comic_metadata["current_page"] = 0

    return cache_data


def apply_progress_overlay(data: dict, session: Session, user) -> dict:
    """Overlay per-user reading progress onto a browse response payload."""
    if not user:
        return data

    response = deepcopy(data)
    comic_ids = [item["id"] for item in response.get("items", []) if item.get("type") == "comic"]

    comic_obj = response.get("comic")
    if isinstance(comic_obj, dict) and comic_obj.get("id"):
        comic_ids.append(comic_obj["id"])

    if not comic_ids:
        return response

    progress_records = session.query(ReadingProgress).filter(
        ReadingProgress.user_id == user.id,
        ReadingProgress.comic_id.in_(comic_ids),
    ).all()
    progress_map = {p.comic_id: p for p in progress_records}

    for item in response.get("items", []):
        if item.get("type") != "comic":
            continue
        progress = progress_map.get(item.get("id"))
        item["progress_percent"] = progress.progress_percent if progress else 0
        item["is_completed"] = progress.is_completed if progress else False
        item["current_page"] = progress.current_page if progress else 0

    if isinstance(comic_obj, dict):
        progress = progress_map.get(comic_obj.get("id"))
        comic_obj["progress_percent"] = progress.progress_percent if progress else 0
        comic_obj["is_completed"] = progress.is_completed if progress else False
        comic_obj["current_page"] = progress.current_page if progress else 0

    first_comic_metadata = response.get("first_comic_metadata")
    if isinstance(first_comic_metadata, dict):
        progress = progress_map.get(first_comic_metadata.get("id"))
        first_comic_metadata["progress_percent"] = progress.progress_percent if progress else 0
        first_comic_metadata["is_completed"] = progress.is_completed if progress else False
        first_comic_metadata["current_page"] = progress.current_page if progress else 0

    return response


def timed_browse_response(
    payload: dict, endpoint: str, cache_status: str, started_at: float
) -> JSONResponse:
    """Build a JSON response with browse timing and cache status headers."""
    elapsed_ms = int((perf_counter() - started_at) * 1000)
    logger.info("[BROWSE] endpoint=%s cache=%s duration_ms=%s", endpoint, cache_status, elapsed_ms)
    return JSONResponse(
        payload,
        headers={
            "X-Browse-Cache": cache_status,
            "X-Browse-Endpoint": endpoint,
            "X-Browse-Time-Ms": str(elapsed_ms),
        },
    )


def parse_library_settings(settings_raw: Any) -> Dict[str, Any]:
    """Normalize library.settings from dict, JSON string, or None."""
    if settings_raw is None:
        return {}
    if isinstance(settings_raw, str):
        try:
            parsed = json.loads(settings_raw)
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError, ValueError):
            return {}
    if isinstance(settings_raw, dict):
        return settings_raw
    return {}


def get_primary_scanner(settings: Dict[str, Any]) -> Optional[str]:
    scanner_config = settings.get("scanner", {})
    if isinstance(scanner_config, dict):
        return scanner_config.get("primary_scanner")
    return None


def detect_per_volume_metadata(primary_scanner: Optional[str]) -> bool:
    """Return True when the library's primary scanner operates at file level."""
    if not primary_scanner:
        return False
    try:
        from ..api.routers.scanners.manager import get_scanner_manager

        manager = get_scanner_manager()
        scanner_class = manager._available_scanners.get(primary_scanner)
        if scanner_class:
            return scanner_class().scan_level.value == "file"
    except Exception as exc:
        logger.warning("Per-volume metadata check failed: %s", exc)
    return False


def find_comic_by_path_segment(
    session: Session,
    library_id: int,
    folder_id: int,
    segment: str,
) -> Optional[Comic]:
    """Find a comic in a folder by id, title, or filename (with extension variants)."""
    if segment.isdigit():
        comic = session.query(Comic).filter(
            Comic.id == int(segment),
            Comic.library_id == library_id,
            Comic.folder_id == folder_id,
        ).first()
        if comic:
            return comic

    comic = session.query(Comic).filter(
        Comic.library_id == library_id,
        Comic.folder_id == folder_id,
        Comic.title == segment,
    ).first()
    if comic:
        return comic

    filename_filters = [Comic.filename == segment]
    filename_filters.extend(Comic.filename == segment + ext for ext in COMIC_EXTENSIONS)
    return session.query(Comic).filter(
        Comic.library_id == library_id,
        Comic.folder_id == folder_id,
        or_(*filename_filters),
    ).first()


def resolve_browse_path(
    session: Session,
    library_id: int,
    root_folder: Folder,
    path: Optional[str],
) -> Tuple[Folder, List[Dict[str, str]], Optional[Comic]]:
    """
    Walk a slash-separated browse path from the library root.

    Returns (current_folder, breadcrumbs, optional_comic) where comic is set when
    the final segment names a comic file (single-volume series view).
    """
    current_folder = root_folder
    breadcrumbs: List[Dict[str, str]] = []

    if not path:
        return current_folder, breadcrumbs, None

    decoded_path = unquote(path).strip("/")
    path_parts = decoded_path.split("/") if decoded_path else []

    for index, part in enumerate(path_parts):
        if not part:
            continue

        child = session.query(Folder).filter(
            Folder.parent_id == current_folder.id,
            Folder.name == part,
        ).first()
        if not child and part.isdigit():
            child = session.query(Folder).filter(
                Folder.parent_id == current_folder.id,
                Folder.id == int(part),
            ).first()

        if not child:
            if index == len(path_parts) - 1:
                comic = find_comic_by_path_segment(
                    session, library_id, current_folder.id, part
                )
                if comic:
                    return current_folder, breadcrumbs, comic
            raise BrowsePathNotFoundError(part)

        current_folder = child
        breadcrumbs.append(
            {
                "name": child.name,
                "path": "/".join(crumb["name"] for crumb in breadcrumbs)
                + ("/" if breadcrumbs else "")
                + child.name,
            }
        )

    return current_folder, breadcrumbs, None


def build_folder_metadata(
    session: Session,
    library_id: int,
    current_folder: Folder,
    root_folder: Folder,
    total_items: int,
) -> Optional[Dict[str, Any]]:
    """Build folder header metadata for non-root browse views."""
    if current_folder.id == root_folder.id:
        return None

    folder_metadata: Dict[str, Any] = {
        "id": current_folder.id,
        "name": current_folder.name,
        "total_issues": total_items,
        "cover_hash": current_folder.first_child_hash,
    }

    if not folder_metadata["cover_hash"]:
        first_comic = (
            session.query(Comic)
            .filter(
                Comic.library_id == library_id,
                Comic.path.startswith(current_folder.path),
            )
            .order_by(Comic.path)
            .first()
        )
        if first_comic:
            folder_metadata["cover_hash"] = first_comic.hash

    series_record = (
        session.query(Series)
        .filter(
            Series.library_id == library_id,
            Series.name == current_folder.name,
        )
        .first()
    )
    if not series_record:
        return folder_metadata

    field_map = {
        "display_name": "display_name",
        "description": "synopsis",
        "writer": "writer",
        "artist": "artist",
        "genre": "genre",
        "tags": "tags",
        "publisher": "publisher",
        "year_start": "year",
        "status": "status",
        "format": "format",
        "chapters": "chapters",
        "scanner_source": "scanner_source",
        "scanner_source_id": "scanner_source_id",
        "scanner_source_url": "scanner_source_url",
        "scan_confidence": "scan_confidence",
        "scanned_at": "scanned_at",
    }
    for source_attr, dest_key in field_map.items():
        value = getattr(series_record, source_attr, None)
        if value is not None and value != "":
            folder_metadata[dest_key] = value

    if series_record.volumes:
        folder_metadata["volumes_count"] = series_record.volumes

    return folder_metadata


def build_single_comic_folder_metadata(comic: Comic, display_name: str) -> Dict[str, Any]:
    """Build folder-like metadata when a path resolves to a single comic volume."""
    return {
        "id": comic.id,
        "name": display_name,
        "total_issues": 1,
        "cover_hash": comic.hash,
        "synopsis": comic.description,
        "writer": comic.writer,
        "artist": comic.penciller,
        "publisher": comic.publisher,
        "year": comic.year,
        "genre": comic.genre,
    }


def get_library_root_folder(session: Session, library_id: int) -> Optional[Folder]:
    return (
        session.query(Folder)
        .filter(
            Folder.library_id == library_id,
            Folder.name == ROOT_FOLDER_MARKER,
        )
        .first()
    )
