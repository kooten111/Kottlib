"""
API v2 Router - Libraries

Endpoints for library management and version information.
"""

import logging
import time
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from ....database import (
    get_all_libraries,
    get_library_by_id,
    create_library,
    get_library_stats,
    update_library,
    update_library_scan_status,
    delete_library,
)
from ...dependencies import get_db_session

# Import scanner for background tasks
from ....scanner.threaded_scanner import ThreadedScanner

# Import scheduler
from ....services.scheduler import get_scheduler

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Helper Functions
# ============================================================================

# In-memory progress tracking for file system scans
_file_scan_progress: Dict[int, Dict[str, Any]] = {}
_progress_lock = {}  # Lock per library_id

def update_file_scan_progress(library_id: int, processed: int, total: int, message: str = "", db=None):
    """Update file scan progress in memory and database (thread-safe)"""
    import threading

    # Ensure we have a lock for this library
    if library_id not in _progress_lock:
        _progress_lock[library_id] = threading.Lock()

    did_update = False
    current_progress = None

    with _progress_lock[library_id]:
        # Get existing progress to avoid overwriting with stale data
        existing = _file_scan_progress.get(library_id, {})
        existing_current = existing.get('current', 0)

        # Only update if we have new progress (processed >= existing)
        # This prevents race conditions from background DB writes
        if processed >= existing_current:
            progress_data = {
                "current": processed,  # Number of comics processed (completed)
                "total": total,
                "message": message or "Processing...",
                "in_progress": True,
                "timestamp": time.time()
            }

            # ALWAYS update memory first
            _file_scan_progress[library_id] = progress_data
            did_update = True
            current_progress = dict(progress_data)  # Capture for DB write

            # Log every 10% or at start/end
            if total > 0 and (processed == 0 or processed == total or processed % max(1, total // 10) == 0):
                logger.info(f"Progress: {processed}/{total} comics processed")
        else:
            logger.debug(f"Ignoring stale progress update: {processed} < {existing_current}")

    # Write to DB outside the lock to avoid blocking reads
    # Only if we actually updated the progress
    if did_update and current_progress:
        should_write = (processed % 10 == 0 or processed == 0 or processed >= total)

        if db and should_write:
            try:
                # Use a separate thread to avoid blocking
                import threading
                progress_to_write = current_progress  # Capture in closure

                def write_to_db():
                    try:
                        with db.get_session() as session:
                            library = get_library_by_id(session, library_id)
                            if library:
                                settings = dict(library.settings or {})
                                settings['file_scan_progress'] = progress_to_write
                                library.settings = settings
                                session.add(library)
                                session.commit()
                    except Exception as e:
                        logger.error(f"Failed to persist progress to database: {e}")

                # Don't wait for DB write - fire and forget
                threading.Thread(target=write_to_db, daemon=True).start()
            except Exception as e:
                logger.error(f"Failed to start DB write thread: {e}")

def scan_library_background(library_id: int, request: Request):
    """Background task to scan a library"""
    try:
        db = request.app.state.db

        # Get library path
        with db.get_session() as session:
            library = get_library_by_id(session, library_id)
            if not library:
                logger.error(f"Library {library_id} not found for background scan")
                return
            library_path = library.path

            # Update library status
            import time as time_module
            update_library_scan_status(session, library_id, status="scanning", timestamp=int(time_module.time()))

        # Initialize progress
        _file_scan_progress[library_id] = {
            "current": 0,
            "total": 0,
            "message": "Starting scan...",
            "in_progress": True,
            "timestamp": time.time()
        }

        # Create scanner with progress callback
        def progress_callback(current: int, total: int, message: str = "", *args, **kwargs):
            update_file_scan_progress(library_id, current, total, message, db=db)

        scanner = ThreadedScanner(db, library_id, progress_callback=progress_callback)

        from pathlib import Path
        result = scanner.scan_library(Path(library_path))

        # Mark scan as complete
        with db.get_session() as session:
            import time as time_module
            update_library_scan_status(session, library_id, status="idle", timestamp=int(time_module.time()))

            # Clear progress from database
            library = get_library_by_id(session, library_id)
            if library and library.settings:
                settings = dict(library.settings)
                settings.pop('file_scan_progress', None)
                library.settings = settings
                session.add(library)
                session.commit()

        # Update final progress in memory with completion status
        _file_scan_progress[library_id] = {
            "current": result.comics_found,
            "total": result.comics_found,
            "message": f"Scan complete: {result.comics_added} added, {result.comics_skipped} skipped",
            "in_progress": False,
            "timestamp": time.time()
        }

        logger.info(f"Background scan completed for library {library_id}: {result}")

    except Exception as e:
        logger.error(f"Background scan failed for library {library_id}: {e}", exc_info=True)

        # Mark scan as failed
        with db.get_session() as session:
            update_library_scan_status(session, library_id, status="error")

        _file_scan_progress[library_id] = {
            "current": 0,
            "total": 0,
            "message": f"Scan failed: {str(e)}",
            "in_progress": False,
            "error": str(e),
            "timestamp": time.time()
        }


# ============================================================================
# Pydantic Models
# ============================================================================

class LibrarySimple(BaseModel):
    """Library simple response for YACReader compatibility"""
    id: int
    name: str
    uuid: str


class LibraryInfo(BaseModel):
    """Library information response (extended)"""
    id: int
    uuid: str
    name: str
    path: str
    created_at: int
    updated_at: int
    last_scan_at: int | None
    scan_status: str
    scan_interval: int = 0
    comic_count: int = 0
    folder_count: int = 0
    exclude_from_webui: bool = False
    settings: Optional[Dict[str, Any]] = None


class CreateLibraryRequest(BaseModel):
    """Create library request"""
    name: str
    path: str
    settings: Optional[Dict[str, Any]] = None
    scan_interval: int = 0
    exclude_from_webui: bool = False


class UpdateLibraryRequest(BaseModel):
    """Update library request"""
    name: Optional[str] = None
    path: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    scan_interval: Optional[int] = None
    exclude_from_webui: Optional[bool] = None


# ============================================================================
# Version Endpoint
# ============================================================================

@router.get("/version")
async def get_version():
    """
    Get server version information

    This is one of the first endpoints the mobile app calls
    Returns plain text version number like YACReader does

    IMPORTANT: YACReader 2.1 returns "2.1" for compatibility with mobile apps
    """
    return PlainTextResponse("2.1")


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/libraries", response_model=List[LibraryInfo])
async def list_libraries(session: Session = Depends(get_db_session)):
    """
    Get all libraries with extended information

    Returns full library info including path, comic count, and folder count.
    For YACReader minimal format, the mobile app can filter the needed fields.
    """
    libraries = get_all_libraries(session)

    result = []
    for lib in libraries:
        # Format UUID with curly braces for YACReader compatibility
        uuid_formatted = f"{{{lib.uuid}}}" if not lib.uuid.startswith('{') else lib.uuid

        # Get library stats
        stats = get_library_stats(session, lib.id)

        result.append(LibraryInfo(
            id=lib.id,
            name=lib.name,
            uuid=uuid_formatted,
            path=lib.path,
            created_at=lib.created_at,
            updated_at=lib.updated_at,
            last_scan_at=lib.last_scan_completed,
            scan_status=lib.scan_status,
            scan_interval=lib.scan_interval,
            comic_count=stats.get('comic_count', 0),
            folder_count=stats.get('folder_count', 0),
            exclude_from_webui=bool(lib.exclude_from_webui or False),
            settings=lib.settings,
        ))

    return result


@router.get("/library/{library_id}/info", response_model=LibraryInfo)
async def get_library(library_id: int, session: Session = Depends(get_db_session)):
    """Get library by ID"""
    library = get_library_by_id(session, library_id)
    if not library:
        raise HTTPException(status_code=404, detail="Library not found")

    stats = get_library_stats(session, library.id)

    return LibraryInfo(
        id=library.id,
        uuid=library.uuid,
        name=library.name,
        path=library.path,
        created_at=library.created_at,
        updated_at=library.updated_at,
        last_scan_at=library.last_scan_completed,
        scan_status=library.scan_status,
        scan_interval=library.scan_interval,
        comic_count=stats.get('comic_count', 0),
        folder_count=stats.get('folder_count', 0),
        exclude_from_webui=bool(library.exclude_from_webui or False),
        settings=library.settings,
    )


@router.post("/libraries", response_model=LibraryInfo)
async def add_library(
    request: Request, 
    data: CreateLibraryRequest, 
    background_tasks: BackgroundTasks
):
    """Create a new library and start scanning"""
    db = request.app.state.db

    with db.get_session() as session:
        library = create_library(
            session,
            name=data.name,
            path=data.path,
            settings=data.settings,
            exclude_from_webui=data.exclude_from_webui
        )
        
        # Update scan interval if provided
        if data.scan_interval > 0:
            update_library(session, library.id, scan_interval=data.scan_interval)
            # Schedule periodic scan
            try:
                scheduler = get_scheduler(db)
                scheduler.schedule_library_scan(library.id, data.scan_interval)
            except Exception as e:
                logger.error(f"Failed to schedule scan for new library: {e}")

        stats = get_library_stats(session, library.id)
        
        # Trigger background scan
        background_tasks.add_task(scan_library_background, library.id, request)

        return LibraryInfo(
            id=library.id,
            uuid=library.uuid,
            name=library.name,
            path=library.path,
            created_at=library.created_at,
            updated_at=library.updated_at,
            last_scan_at=library.last_scan_completed,
            scan_status="scanning",  # Optimistically set status
            scan_interval=data.scan_interval,
            comic_count=stats.get('comic_count', 0),
            folder_count=stats.get('folder_count', 0),
            exclude_from_webui=data.exclude_from_webui,
            settings=library.settings,
        )


@router.put("/libraries/{library_id}", response_model=LibraryInfo)
async def update_library_details(library_id: int, request: Request, data: UpdateLibraryRequest):
    """Update library details"""
    db = request.app.state.db

    with db.get_session() as session:
        library = update_library(
            session,
            library_id,
            name=data.name,
            path=data.path,
            settings=data.settings,
            scan_interval=data.scan_interval,
            exclude_from_webui=data.exclude_from_webui
        )
        
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")
            
        # Update schedule if interval changed
        if data.scan_interval is not None:
            try:
                scheduler = get_scheduler(db)
                scheduler.schedule_library_scan(library.id, data.scan_interval)
            except Exception as e:
                logger.error(f"Failed to update scan schedule: {e}")

        stats = get_library_stats(session, library.id)

        return LibraryInfo(
            id=library.id,
            uuid=library.uuid,
            name=library.name,
            path=library.path,
            created_at=library.created_at,
            updated_at=library.updated_at,
            last_scan_at=library.last_scan_completed,
            scan_status=library.scan_status,
            scan_interval=library.scan_interval,
            comic_count=stats.get('comic_count', 0),
            folder_count=stats.get('folder_count', 0),
            exclude_from_webui=bool(library.exclude_from_webui or False),
            settings=library.settings,
        )


@router.delete("/libraries/{library_id}")
async def remove_library(library_id: int, request: Request, session: Session = Depends(get_db_session)):
    """Delete a library"""
    db = request.app.state.db

    # Remove schedule first
    try:
        scheduler = get_scheduler(db)
        scheduler.schedule_library_scan(library_id, 0)  # 0 removes the job
    except Exception as e:
        logger.warning(f"Failed to remove schedule for deleted library: {e}")

    success = delete_library(session, library_id)

    if not success:
        raise HTTPException(status_code=404, detail="Library not found")

    return {"success": True, "message": "Library deleted"}


@router.post("/libraries/{library_id}/scan")
async def scan_library_manual(library_id: int, request: Request, background_tasks: BackgroundTasks):
    """Trigger a manual scan for a library"""
    db = request.app.state.db

    with db.get_session() as session:
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

    # Trigger background scan
    background_tasks.add_task(scan_library_background, library_id, request)

    return {"success": True, "message": "Scan started"}


@router.get("/libraries/{library_id}/scan/progress")
async def get_file_scan_progress(library_id: int, session: Session = Depends(get_db_session)):
    """Get file scan progress for a library (checks both memory and database)"""
    # Check memory first (fastest and most up-to-date)
    memory_progress = _file_scan_progress.get(library_id)

    # If we have memory progress, return it immediately
    if memory_progress:
        logger.debug(f"Progress for library {library_id}: {memory_progress['current']}/{memory_progress['total']} - {memory_progress['message']}")
        return memory_progress

    # Otherwise check database for multi-worker setups
    library = get_library_by_id(session, library_id)
    if not library:
        raise HTTPException(status_code=404, detail="Library not found")

    if library.settings:
        db_progress = library.settings.get('file_scan_progress')
        if db_progress:
            # Cache it in memory for next time
            _file_scan_progress[library_id] = db_progress
            logger.debug(f"Progress from DB for library {library_id}: {db_progress['current']}/{db_progress['total']}")
            return db_progress

    # No progress found
    logger.debug(f"No progress found for library {library_id}")
    return {
        "in_progress": False,
        "current": 0,
        "total": 0,
        "message": "No scan in progress"
    }


@router.delete("/libraries/{library_id}/scan/progress")
async def clear_file_scan_progress(library_id: int, session: Session = Depends(get_db_session)):
    """Clear file scan progress for a library (both memory and database)"""
    # Clear from memory
    if library_id in _file_scan_progress:
        del _file_scan_progress[library_id]

    # Clean up lock
    if library_id in _progress_lock:
        del _progress_lock[library_id]

    # Clear from database
    library = get_library_by_id(session, library_id)
    if library and library.settings:
        settings = dict(library.settings)
        if settings.pop('file_scan_progress', None) is not None:
            library.settings = settings
            session.add(library)

    return {"success": True, "message": "Progress cleared"}
