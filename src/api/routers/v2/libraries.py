"""
API v2 Router - Libraries

Endpoints for library management and version information.
"""

import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse

from ....database import (
    get_all_libraries,
    get_library_by_id,
    create_library,
    get_library_stats,
    update_library,
    delete_library,
)

# Import scanner for background tasks
from ....scanner.threaded_scanner import ThreadedScanner

# Import scheduler
from ....services.scheduler import get_scheduler

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Helper Functions
# ============================================================================

def scan_library_background(library_id: int, request: Request):
    """Background task to scan a library"""
    try:
        db = request.app.state.db
        scanner = ThreadedScanner(db, library_id)
        
        # Get library path
        with db.get_session() as session:
            library = get_library_by_id(session, library_id)
            if not library:
                logger.error(f"Library {library_id} not found for background scan")
                return
            library_path = library.path
            
        from pathlib import Path
        scanner.scan_library(Path(library_path))
        logger.info(f"Background scan completed for library {library_id}")
        
    except Exception as e:
        logger.error(f"Background scan failed for library {library_id}: {e}", exc_info=True)


# ============================================================================
# Pydantic Models
# ============================================================================

class LibraryInfo(BaseModel):
    """Library information response"""
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


class CreateLibraryRequest(BaseModel):
    """Create library request"""
    name: str
    path: str
    settings: Optional[Dict[str, Any]] = None
    scan_interval: int = 0


class UpdateLibraryRequest(BaseModel):
    """Update library request"""
    name: Optional[str] = None
    path: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    scan_interval: Optional[int] = None


# ============================================================================
# Version Endpoint
# ============================================================================

@router.get("/version")
async def get_version():
    """
    Get server version information

    This is one of the first endpoints the mobile app calls
    Returns plain text version number like YACReader does
    """
    return PlainTextResponse("9.14.2")


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/libraries", response_model=List[LibraryInfo])
async def list_libraries(request: Request):
    """Get all libraries"""
    db = request.app.state.db

    with db.get_session() as session:
        libraries = get_all_libraries(session)

        result = []
        for lib in libraries:
            stats = get_library_stats(session, lib.id)

            result.append(LibraryInfo(
                id=lib.id,
                uuid=lib.uuid,
                name=lib.name,
                path=lib.path,
                created_at=lib.created_at,
                updated_at=lib.updated_at,
                last_scan_at=lib.last_scan_completed,
                scan_status=lib.scan_status,
                scan_interval=lib.scan_interval,
                comic_count=stats.get('comic_count', 0),
                folder_count=stats.get('folder_count', 0),
            ))

        return result


@router.get("/library/{library_id}/info", response_model=LibraryInfo)
async def get_library(library_id: int, request: Request):
    """Get library by ID"""
    db = request.app.state.db

    with db.get_session() as session:
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
            settings=data.settings
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
            folder_count=stats.get('folder_count', 0),
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
            scan_interval=data.scan_interval
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
        )


@router.delete("/libraries/{library_id}")
async def remove_library(library_id: int, request: Request):
    """Delete a library"""
    db = request.app.state.db

    # Remove schedule first
    try:
        scheduler = get_scheduler(db)
        scheduler.schedule_library_scan(library_id, 0) # 0 removes the job
    except Exception as e:
        logger.warning(f"Failed to remove schedule for deleted library: {e}")

    with db.get_session() as session:
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
