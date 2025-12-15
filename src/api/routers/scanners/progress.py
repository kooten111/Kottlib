"""
Progress tracking for scanner operations.

Provides in-memory and database-persistent progress tracking for library scans.

Note: This is a performance optimization cache. The source of truth is stored
in the database (library.settings['scanner_progress']) to support multi-worker
deployments. The API endpoint merges both memory and database state, keeping
the most advanced progress values.
"""

from typing import Dict, Any, Optional
import logging

from sqlalchemy.orm import Session

from src.database.models import Library


logger = logging.getLogger(__name__)

# In-memory progress tracking cache for library scans
_scan_progress: Dict[int, Dict[str, Any]] = {}


def _normalize_progress(progress: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize progress payload to expected shape and types."""
    if not progress:
        return {}

    normalized = {
        "processed": int(progress.get("processed", 0) or 0),
        "scanned": int(progress.get("scanned", 0) or 0),
        "total": int(progress.get("total", 0) or 0),
        "failed": int(progress.get("failed", 0) or 0),
        "skipped": int(progress.get("skipped", 0) or 0),
        "in_progress": bool(progress.get("in_progress", False)),
        "completed": bool(progress.get("completed", False)),
        "error": progress.get("error")
    }

    if normalized["processed"] > normalized["total"]:
        normalized["processed"] = normalized["total"]

    return normalized


def _sanitize_progress(progress: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of progress without internal bookkeeping keys."""
    if not progress:
        return progress
    cleaned = {
        key: value
        for key, value in progress.items()
        if not str(key).startswith("_")
    }
    return _normalize_progress(cleaned)


def _merge_progress(primary: Dict[str, Any], secondary: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two progress dictionaries, keeping the most advanced values."""
    if not primary:
        return dict(secondary or {})
    if not secondary:
        return dict(primary or {})

    primary = _normalize_progress(primary)
    secondary = _normalize_progress(secondary)

    merged = dict(primary)

    for key in ("processed", "scanned", "failed", "skipped", "total"):
        merged[key] = max(primary.get(key, 0), secondary.get(key, 0))

    merged["in_progress"] = primary.get("in_progress", False) or secondary.get("in_progress", False)
    merged["completed"] = primary.get("completed", False) or secondary.get("completed", False)
    merged["error"] = primary.get("error") or secondary.get("error")

    return merged


def persist_progress_to_db(session: Session, library: Library, progress: Dict[str, Any]) -> None:
    """Persist scan progress to the database for cross-worker visibility."""
    if not library:
        return

    serialized = _sanitize_progress(progress or {})

    settings = dict(library.settings or {})
    settings['scanner_progress'] = serialized
    library.settings = settings
    session.add(library)
    session.commit()


def start_scan_progress(library_id: int) -> Dict[str, Any]:
    """Initialize scan progress for a library."""
    progress = {
        "processed": 0,
        "scanned": 0,
        "total": 0,
        "failed": 0,
        "skipped": 0,
        "in_progress": True,
        "completed": False,
        "error": None
    }
    _scan_progress[library_id] = progress
    return progress


def update_scan_progress(
    library_id: int,
    processed: int,
    total: int,
    scanned: int = 0,
    failed: int = 0,
    skipped: int = 0
) -> None:
    """Update scan progress for a library."""
    progress = _scan_progress.get(library_id)
    if not progress:
        progress = start_scan_progress(library_id)

    progress.update({
        "processed": processed,
        "scanned": scanned,
        "total": total,
        "failed": failed,
        "skipped": skipped,
        "in_progress": processed < total,
        "completed": False,
        "error": None
    })

    # Log occasional progress snapshots for troubleshooting large scans
    log_interval = max(1, total // 10) if total else 1
    if processed in (0, total) or (processed and processed % log_interval == 0):
        logger.info(
            "Library %s scan progress: processed=%s/%s scanned=%s failed=%s skipped=%s",
            library_id,
            processed,
            total,
            scanned,
            failed,
            skipped
        )


def get_scan_progress(library_id: int) -> Optional[Dict[str, Any]]:
    """Get scan progress for a library."""
    return _scan_progress.get(library_id)


def clear_scan_progress(library_id: int) -> None:
    """Clear scan progress for a library."""
    if library_id in _scan_progress:
        del _scan_progress[library_id]


def get_merged_progress(library_id: int, db_progress: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Get merged progress from memory and database.
    
    Args:
        library_id: The library ID
        db_progress: Progress loaded from database (optional)
    
    Returns:
        Merged and sanitized progress dictionary
    """
    memory_progress = get_scan_progress(library_id)
    progress = _merge_progress(memory_progress, db_progress)
    progress = _sanitize_progress(progress)
    
    if progress:
        # Update in-memory cache so future reads on this worker stay current
        _scan_progress[library_id] = progress
    
    return progress


def get_internal_progress(library_id: int) -> Optional[Dict[str, Any]]:
    """Get raw internal progress for a library (used by tasks)."""
    return _scan_progress.get(library_id)
