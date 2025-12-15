"""
Comic scanning endpoint.

POST /scan/comic - Scan a single comic for metadata
"""

import logging

from fastapi import HTTPException, BackgroundTasks, Request

from src.services.metadata_service import MetadataService
from src.database.models import Comic

from ..models import ScanComicRequest, ScanComicResponse
from ..manager import get_scanner_manager


logger = logging.getLogger(__name__)


async def scan_comic(
    scan_request: ScanComicRequest,
    background_tasks: BackgroundTasks,
    request: Request
) -> ScanComicResponse:
    """
    Scan a single comic for metadata.

    Uses the scanner configured for the comic's library.
    """
    db = request.app.state.db

    with db.get_session() as session:
        # Get comic
        comic = session.query(Comic).filter(Comic.id == scan_request.comic_id).first()
        if not comic:
            raise HTTPException(status_code=404, detail=f"Comic {scan_request.comic_id} not found")

        # Get library scanner configuration
        library = comic.library
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

        # Determine confidence threshold
        threshold = scan_request.confidence_threshold
        if threshold is None:
            threshold = scanner_config.get('confidence_threshold', 0.4)

        try:
            # Get scanner specific config
            scanner_specific_config = scanner_config.get('scanner_configs', {}).get(primary_scanner, {})
            
            # Scan using filename with direct scanner invocation
            scanner = manager.get_scanner(primary_scanner, config=scanner_specific_config)
            result, _ = scanner.scan(
                comic.filename,
                confidence_threshold=threshold
            )

            if not result:
                return ScanComicResponse(
                    comic_id=comic.id,
                    success=False,
                    error="No match found with sufficient confidence"
                )

            # Apply metadata
            application_result = MetadataService.apply_scan_result_to_comic(
                session,
                comic,
                result,
                primary_scanner,
                overwrite=scan_request.overwrite
            )

            return ScanComicResponse(
                comic_id=comic.id,
                success=application_result.success,
                confidence=result.confidence,
                fields_updated=application_result.fields_updated,
                error=application_result.error
            )

        except Exception as e:
            return ScanComicResponse(
                comic_id=comic.id,
                success=False,
                error=str(e)
            )
