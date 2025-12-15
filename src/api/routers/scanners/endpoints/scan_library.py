"""
Library scanning endpoints.

POST /scan/library - Start library scan
GET /scan/library/{library_id}/progress - Get scan progress
DELETE /scan/library/{library_id}/progress - Clear scan progress
"""

from typing import Dict, Any
import logging

from fastapi import HTTPException, BackgroundTasks, Request

from src.database.models import Library

from ..models import ScanLibraryRequest
from ..progress import (
    start_scan_progress,
    get_scan_progress,
    clear_scan_progress,
    get_merged_progress,
    _sanitize_progress,
)
from ..manager import get_scanner_manager
from ..tasks import run_library_scan_task


logger = logging.getLogger(__name__)


async def scan_library(
    scan_request: ScanLibraryRequest,
    background_tasks: BackgroundTasks,
    request: Request
) -> Dict[str, str]:
    """
    Scan all comics in a library for metadata.

    This starts a background task and returns immediately.
    Use the /scan/library/{library_id}/progress endpoint to check progress.
    """
    db = request.app.state.db

    with db.get_session() as session:
        # Get library
        library = session.query(Library).filter(Library.id == scan_request.library_id).first()
        if not library:
            raise HTTPException(status_code=404, detail=f"Library {scan_request.library_id} not found")

        # Get scanner configuration
        settings = library.settings or {}
        scanner_config = settings.get('scanner', {})
        primary_scanner = scanner_config.get('primary_scanner')

        if not primary_scanner:
            raise HTTPException(
                status_code=400,
                detail=f"No scanner configured for library '{library.name}'"
            )

        # Get scanner manager (use local initialized instance)
        manager = get_scanner_manager()

        if primary_scanner not in manager.get_available_scanners():
            raise HTTPException(
                status_code=500,
                detail=f"Scanner '{primary_scanner}' is not available"
            )

        # Check if a scan is already in progress
        current_progress = get_scan_progress(scan_request.library_id)
        if current_progress and current_progress.get("in_progress", False):
            raise HTTPException(
                status_code=409,
                detail=f"A scan is already in progress for library '{library.name}'"
            )

        # Initialize progress immediately so the frontend sees in-progress status
        progress = start_scan_progress(scan_request.library_id)
        settings = dict(library.settings or {})
        settings['scanner_progress'] = _sanitize_progress(progress)
        library.settings = settings
        session.add(library)

        # Determine confidence threshold
        threshold = scan_request.confidence_threshold
        if threshold is None:
            threshold = scanner_config.get('confidence_threshold', 0.4)

        # Start background task
        background_tasks.add_task(
            run_library_scan_task,
            db,
            scan_request.library_id,
            primary_scanner,
            scan_request.overwrite,
            scan_request.rescan_existing,
            threshold
        )

        return {
            "status": "started",
            "message": "Library scan started in background. Use /scan/library/{library_id}/progress to check progress."
        }


async def get_library_scan_progress(library_id: int, request: Request) -> Dict[str, Any]:
    """
    Get the current progress of a library scan.

    Returns the number of comics processed, scanned, and total to scan.
    """
    db_progress = None

    db = request.app.state.db
    with db.get_session() as session:
        library = session.query(Library).filter(Library.id == library_id).first()
        if library:
            settings = library.settings or {}
            stored_progress = settings.get('scanner_progress')
            if stored_progress:
                db_progress = stored_progress

    progress = get_merged_progress(library_id, db_progress)

    if not progress:
        logger.info("Progress requested but no entry found for library %s", library_id)
        return {
            "in_progress": False,
            "completed": False,
            "processed": 0,
            "scanned": 0,
            "total": 0,
            "failed": 0,
            "skipped": 0,
            "error": None
        }

    progress = _sanitize_progress(progress)
    logger.info(
        "Progress requested for library %s: processed=%s/%s scanned=%s failed=%s skipped=%s in_progress=%s",
        library_id,
        progress.get("processed"),
        progress.get("total"),
        progress.get("scanned"),
        progress.get("failed"),
        progress.get("skipped"),
        progress.get("in_progress")
    )
    return progress


async def clear_library_scan_progress(library_id: int, request: Request) -> Dict[str, str]:
    """
    Clear the scan progress for a library.

    Use this after reading the final progress state.
    """
    clear_scan_progress(library_id)
    db = request.app.state.db
    with db.get_session() as session:
        library = session.query(Library).filter(Library.id == library_id).first()
        if library:
            settings = dict(library.settings or {})
            if settings.pop('scanner_progress', None) is not None:
                library.settings = settings
                session.add(library)
    return {"status": "cleared"}
