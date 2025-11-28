"""
Admin API Router

Admin-only endpoints for database maintenance and system operations.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel

from ....database.database import get_db_session
from ....database.search_index import SearchIndexManager
from ....database.migrations import add_search_indexes
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# ============================================================================
# Pydantic Models
# ============================================================================

class ReindexResponse(BaseModel):
    """Response for reindex operations"""
    success: bool
    message: str
    comics_indexed: Optional[int] = None


class MigrationResponse(BaseModel):
    """Response for migration operations"""
    success: bool
    message: str
    details: Optional[str] = None


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/reindex-search", response_model=ReindexResponse)
async def reindex_search(
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db_session)
):
    """
    Rebuild the full-text search index

    This operation:
    1. Clears the existing FTS5 index
    2. Reindexes all comics with their metadata
    3. Extracts and indexes dynamic metadata from metadata_json

    This can take several minutes for large libraries.
    The operation runs in the background.
    """
    try:
        # Check if FTS table exists
        if not SearchIndexManager.check_fts_exists(session):
            logger.warning("FTS table does not exist, creating it first...")
            SearchIndexManager.create_fts_table(session)

        logger.info("Starting search reindex operation...")

        # Run reindex in background
        def reindex_task():
            try:
                indexed_count = SearchIndexManager.reindex_all_comics(session)
                logger.info(f"Reindex complete! Indexed {indexed_count} comics.")
            except Exception as e:
                logger.error(f"Reindex failed: {e}", exc_info=True)

        background_tasks.add_task(reindex_task)

        return ReindexResponse(
            success=True,
            message="Search reindex started in background. Check logs for progress.",
            comics_indexed=None
        )

    except Exception as e:
        logger.error(f"Failed to start reindex: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start reindex: {str(e)}"
        )


@router.post("/reindex-search/sync", response_model=ReindexResponse)
async def reindex_search_sync(session: Session = Depends(get_db_session)):
    """
    Rebuild the full-text search index (synchronous)

    Same as /reindex-search but runs synchronously and returns
    the number of comics indexed.

    WARNING: This can take several minutes for large libraries and will
    block the API response until complete.
    """
    try:
        # Check if FTS table exists
        if not SearchIndexManager.check_fts_exists(session):
            logger.warning("FTS table does not exist, creating it first...")
            SearchIndexManager.create_fts_table(session)

        logger.info("Starting synchronous search reindex...")
        indexed_count = SearchIndexManager.reindex_all_comics(session)
        logger.info(f"Reindex complete! Indexed {indexed_count} comics.")

        return ReindexResponse(
            success=True,
            message=f"Successfully reindexed {indexed_count} comics.",
            comics_indexed=indexed_count
        )

    except Exception as e:
        logger.error(f"Reindex failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Reindex failed: {str(e)}"
        )


@router.post("/migrate/search-indexes", response_model=MigrationResponse)
async def run_search_indexes_migration(
    session: Session = Depends(get_db_session)
):
    """
    Run the search indexes migration

    This creates:
    - Indexes on Comic and Series tables for searchable fields
    - FTS5 virtual table for full-text search
    - Triggers to keep FTS table in sync
    - Populates FTS table with existing data

    This is idempotent and safe to run multiple times.
    """
    try:
        logger.info("Running search indexes migration...")
        add_search_indexes.upgrade(session)

        return MigrationResponse(
            success=True,
            message="Search indexes migration completed successfully",
            details="Created indexes, FTS5 table, triggers, and populated search index"
        )

    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Migration failed: {str(e)}"
        )


@router.get("/search-index/status")
async def get_search_index_status(session: Session = Depends(get_db_session)):
    """
    Get the status of the search index

    Returns information about whether the FTS table exists and
    how many comics are indexed.
    """
    try:
        fts_exists = SearchIndexManager.check_fts_exists(session)

        if not fts_exists:
            return {
                "fts_enabled": False,
                "message": "Full-text search index not initialized. Run migration first."
            }

        # Count comics in FTS table
        from sqlalchemy import text
        result = session.execute(text("SELECT COUNT(*) FROM comics_fts")).fetchone()
        fts_count = result[0] if result else 0

        # Count total comics
        from ....database.models import Comic
        total_comics = session.query(Comic).count()

        return {
            "fts_enabled": True,
            "comics_indexed": fts_count,
            "total_comics": total_comics,
            "index_complete": fts_count == total_comics,
            "message": "Search index active" if fts_count == total_comics else "Search index incomplete, reindex recommended"
        }

    except Exception as e:
        logger.error(f"Failed to get search index status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get status: {str(e)}"
        )
