"""
Metadata management endpoint.

POST /clear-metadata - Clear metadata from comics
"""

from typing import Dict, Any
import logging

from fastapi import HTTPException, Request

from src.database.models import Comic

from ..models import ClearMetadataRequest


logger = logging.getLogger(__name__)


async def clear_metadata(
    clear_request: ClearMetadataRequest,
    request: Request
) -> Dict[str, Any]:
    """
    Clear metadata from comics.

    Can clear scanner info, tags, or all metadata from specific comics or entire library.
    """
    db = request.app.state.db

    with db.get_session() as session:
        # Build query for comics to clear
        query = session.query(Comic)

        if clear_request.comic_ids:
            query = query.filter(Comic.id.in_(clear_request.comic_ids))
        elif clear_request.library_id:
            query = query.filter(Comic.library_id == clear_request.library_id)
        else:
            raise HTTPException(
                status_code=400,
                detail="Either comic_ids or library_id must be provided"
            )

        comics = query.all()
        cleared_count = 0

        for comic in comics:
            if clear_request.clear_scanner_info:
                comic.scanner_source = None
                comic.scanner_source_id = None
                comic.scanner_source_url = None
                comic.scanned_at = None
                comic.scan_confidence = None
                comic.web = None

            if clear_request.clear_tags:
                comic.tags = None

            if clear_request.clear_metadata:
                # Clear all metadata fields but keep file info
                comic.title = None
                comic.series = None
                comic.normalized_series_name = None
                comic.volume = None
                comic.issue_number = None
                comic.year = None
                comic.publisher = None
                comic.writer = None
                comic.artist = None
                comic.description = None
                comic.penciller = None
                comic.inker = None
                comic.colorist = None
                comic.letterer = None
                comic.cover_artist = None
                comic.editor = None
                comic.story_arc = None
                comic.arc_number = None
                comic.arc_count = None
                comic.alternate_series = None
                comic.alternate_number = None
                comic.alternate_count = None
                comic.genre = None
                comic.language_iso = None
                comic.age_rating = None
                comic.imprint = None
                comic.format_type = None
                comic.is_color = None
                comic.characters = None
                comic.teams = None
                comic.locations = None
                comic.main_character_or_team = None
                comic.series_group = None
                comic.comic_vine_id = None
                comic.web = None

            cleared_count += 1

        session.commit()

        return {
            "success": True,
            "cleared_count": cleared_count,
            "message": f"Cleared metadata from {cleared_count} comic(s)"
        }
