"""
Apply metadata endpoint for comics.

POST /apply/comic - Apply manually selected metadata to a comic
"""

import logging

from fastapi import HTTPException, Request

from src.services.metadata_service import MetadataService
from src.database.models import Comic

from ..models import ApplyComicMetadataRequest, ScanComicResponse


logger = logging.getLogger(__name__)


async def apply_comic_metadata(
    apply_request: ApplyComicMetadataRequest,
    request: Request
) -> ScanComicResponse:
    """
    Apply metadata from a manually selected candidate to a comic.
    
    This endpoint is used when the user manually selects a candidate
    from the low-confidence results returned by the scan endpoint.
    """
    db = request.app.state.db
    
    with db.get_session() as session:
        # Get comic
        comic = session.query(Comic).filter(Comic.id == apply_request.comic_id).first()
        if not comic:
            raise HTTPException(status_code=404, detail=f"Comic {apply_request.comic_id} not found")
        
        # Get library scanner configuration
        library = comic.library
        settings = library.settings or {}
        scanner_config = settings.get('scanner', {})
        primary_scanner = scanner_config.get('primary_scanner', 'manual')
        
        # Create a ScanResult-like object from the candidate
        from src.metadata_providers.base import ScanResult
        
        scan_result = ScanResult(
            confidence=apply_request.confidence,
            source_id=apply_request.source_id,
            source_url=apply_request.source_url,
            metadata=apply_request.metadata,
            tags=apply_request.metadata.get('tags', [])
        )
        
        # Apply metadata
        application_result = MetadataService.apply_scan_result_to_comic(
            session,
            comic,
            scan_result,
            primary_scanner,
            overwrite=apply_request.overwrite
        )
        
        return ScanComicResponse(
            comic_id=comic.id,
            success=application_result.success,
            confidence=apply_request.confidence,
            fields_updated=application_result.fields_updated,
            error=application_result.error
        )
