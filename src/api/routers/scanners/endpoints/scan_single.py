"""
Single scan endpoints.

POST /scan - Scan a single file or series
POST /scan/bulk - Scan multiple files
POST /scan/series - Scan and save series metadata
GET /test/{scanner_name} - Test a scanner
"""

from typing import Optional, Dict, Any
import logging
import time

from fastapi import HTTPException, Request

from src.database.models import Library, Series

from ..models import (
    ScanRequest,
    ScanResultModel,
    ConfidenceLevelEnum,
    BulkScanRequest,
    BulkScanResult,
)
from ..manager import get_scanner_manager


logger = logging.getLogger(__name__)


async def scan_single(scan_request: ScanRequest, request: Request) -> ScanResultModel:
    """
    Scan a single file or series for metadata.

    Performs a metadata scan using the configured scanner for the library.
    Returns the best match with confidence score.

    Example:
        POST /scanners/scan
        {
            "query": "[Artist] Comic Title [English].cbz",
            "library_id": 1
        }
    """
    db = request.app.state.db

    # Get library scanner configuration
    scanner_config = None
    library_name = None
    primary_scanner = None

    if scan_request.library_id:
        with db.get_session() as session:
            library = session.query(Library).filter(Library.id == scan_request.library_id).first()
            if not library:
                raise HTTPException(status_code=404, detail=f"Library {scan_request.library_id} not found")

            settings = library.settings or {}
            scanner_config = settings.get('scanner', {})
            library_name = library.name
            primary_scanner = scanner_config.get('primary_scanner') if scanner_config else None
    
    # Allow scanner_name override from request
    if scan_request.scanner_name:
        primary_scanner = scan_request.scanner_name
    
    if not primary_scanner:
        raise HTTPException(
            status_code=400,
            detail=f"No scanner configured for library '{library_name}'. Please configure a scanner in the admin panel."
        )

    # Get the scanner manager and instantiate the scanner directly
    manager = get_scanner_manager()
    
    if primary_scanner not in manager.get_available_scanners():
        raise HTTPException(
            status_code=500,
            detail=f"Scanner '{primary_scanner}' is not available"
        )

    # Instantiate the scanner class directly
    scanner_class = manager._available_scanners[primary_scanner]
    scanner_instance = scanner_class()

    # Set confidence threshold
    confidence_threshold = scan_request.confidence_threshold
    if confidence_threshold is None and scanner_config:
        confidence_threshold = scanner_config.get('confidence_threshold', 0.4)
    if confidence_threshold is None:
        confidence_threshold = 0.4

    # Perform scan
    try:
        result, candidates = scanner_instance.scan(scan_request.query, confidence_threshold=confidence_threshold)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")

    if not result:
        raise HTTPException(
            status_code=404,
            detail="No match found with sufficient confidence"
        )

    # Convert to response model
    try:
        return ScanResultModel(
            confidence=result.confidence,
            confidence_level=ConfidenceLevelEnum[result.confidence_level.name],
            source_id=result.source_id,
            source_url=result.source_url,
            metadata=result.metadata,
            tags=result.tags
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


async def scan_bulk(bulk_request: BulkScanRequest, request: Request) -> BulkScanResult:
    """
    Scan multiple files or series for metadata.

    Performs bulk scanning and returns results for all queries.
    Useful for batch processing entire libraries.

    Example:
        POST /scanners/scan/bulk
        {
            "queries": ["file1.cbz", "file2.cbz", "file3.cbz"],
            "library_id": 1,
            "confidence_threshold": 0.4
        }
    """
    db = request.app.state.db
    manager = get_scanner_manager()

    # Get library configuration and scanner
    scanner_config = None
    primary_scanner = None

    if bulk_request.library_id:
        with db.get_session() as session:
            library = session.query(Library).filter(Library.id == bulk_request.library_id).first()
            if not library:
                raise HTTPException(status_code=404, detail=f"Library {bulk_request.library_id} not found")

            settings = library.settings or {}
            scanner_config = settings.get('scanner', {})
            primary_scanner = scanner_config.get('primary_scanner')

            if not primary_scanner:
                raise HTTPException(
                    status_code=400,
                    detail=f"No scanner configured for library '{library.name}'. Please configure a scanner in the admin panel."
                )
    else:
        raise HTTPException(status_code=400, detail="library_id is required")

    # Verify scanner is available
    if primary_scanner not in manager.get_available_scanners():
        raise HTTPException(
            status_code=500,
            detail=f"Scanner '{primary_scanner}' is not available"
        )

    # Instantiate scanner
    scanner_class = manager._available_scanners[primary_scanner]
    scanner_instance = scanner_class()

    # Set confidence threshold
    confidence_threshold = bulk_request.confidence_threshold
    if confidence_threshold is None and scanner_config:
        confidence_threshold = scanner_config.get('confidence_threshold', 0.4)
    if confidence_threshold is None:
        confidence_threshold = 0.4

    results = []
    matched = 0
    rejected = 0

    for query in bulk_request.queries:
        try:
            result, _ = scanner_instance.scan(query, confidence_threshold=confidence_threshold)

            if result:
                matched += 1
                results.append({
                    "query": query,
                    "status": "matched",
                    "confidence": result.confidence,
                    "confidence_level": result.confidence_level.name,
                    "source_id": result.source_id,
                    "source_url": result.source_url,
                    "metadata": result.metadata
                })
            else:
                rejected += 1
                results.append({
                    "query": query,
                    "status": "rejected",
                    "confidence": 0.0,
                    "reason": "Low confidence"
                })

        except Exception as e:
            rejected += 1
            results.append({
                "query": query,
                "status": "error",
                "error": str(e)
            })

    return BulkScanResult(
        total=len(bulk_request.queries),
        matched=matched,
        rejected=rejected,
        results=results
    )


async def scan_and_save_series(
    library_id: int,
    series_name: str,
    confidence_threshold: Optional[float] = None,
    overwrite: bool = False,
    request: Request = None
) -> Dict[str, Any]:
    """
    Scan and save metadata for a series.
    
    Scans the series using the library's configured scanner and saves
    the metadata to the database.
    """
    db = request.app.state.db
    
    with db.get_session() as session:
        # Get library and scanner config
        library = session.query(Library).filter(Library.id == library_id).first()
        if not library:
            raise HTTPException(status_code=404, detail=f"Library {library_id} not found")
        
        settings = library.settings or {}
        scanner_config = settings.get('scanner', {})
        primary_scanner = scanner_config.get('primary_scanner')
        
        if not primary_scanner:
            raise HTTPException(
                status_code=400,
                detail=f"No scanner configured for library '{library.name}'"
            )
        
        # Get or create series
        series = session.query(Series).filter(
            Series.library_id == library_id,
            Series.name == series_name
        ).first()
        
        if not series:
            series = Series(
                library_id=library_id,
                name=series_name,
                display_name=series_name,
                created_at=int(time.time()),
                updated_at=int(time.time())
            )
            session.add(series)
            session.flush()
        
        # Scan for metadata
        manager = get_scanner_manager()
        
        if primary_scanner not in manager.get_available_scanners():
            raise HTTPException(
                status_code=500,
                detail=f"Scanner '{primary_scanner}' is not available"
            )
        
        # Get scanner specific config
        scanner_specific_config = scanner_config.get('scanner_configs', {}).get(primary_scanner, {})
        
        # Get scanner instance directly with config
        scanner = manager.get_scanner(primary_scanner, config=scanner_specific_config)
        
        # Determine auto-match threshold (high confidence required for automatic application)
        if confidence_threshold is not None:
            auto_match_threshold = confidence_threshold
        elif scanner_config:
            auto_match_threshold = scanner_config.get('confidence_threshold', 0.7)
        else:
            auto_match_threshold = 0.7
        
        # Use a very low threshold to get ALL candidates from the scanner
        scan_kwargs = {'confidence_threshold': 0.1}
        
        # Debug logging
        logger.info(f"[SERIES SCAN] series_name='{series_name}', scanner='{primary_scanner}', auto_threshold={auto_match_threshold}")
        
        try:
            result, all_candidates = scanner.scan(series_name, **scan_kwargs)
            
            logger.info(f"[SERIES SCAN] result={result is not None}, candidates={len(all_candidates) if all_candidates else 0}")
            if result:
                logger.info(f"[SERIES SCAN] confidence={result.confidence}, title={result.metadata.get('title')}")
            
            # No results at all from AniList
            if not result:
                return {
                    "success": False,
                    "error": "No matches found on AniList",
                    "series_id": series.id,
                    "candidates": []
                }
            
            # Check if best result meets auto-match threshold
            if result.confidence < auto_match_threshold:
                # Return candidates for manual selection
                candidate_list = []
                for candidate in all_candidates[:10]:  # Limit to top 10
                    candidate_list.append({
                        "confidence": candidate.confidence,
                        "source_id": candidate.source_id,
                        "source_url": candidate.source_url,
                        "title": candidate.metadata.get('title', ''),
                        "metadata": candidate.metadata
                    })
                
                logger.info(f"[SERIES SCAN] Below threshold ({result.confidence:.2f} < {auto_match_threshold}), returning {len(candidate_list)} candidates for manual selection")
                
                return {
                    "success": False,
                    "error": f"Best match ({result.confidence*100:.0f}%) below auto-match threshold ({auto_match_threshold*100:.0f}%)",
                    "series_id": series.id,
                    "candidates": candidate_list,
                    "auto_match_threshold": auto_match_threshold
                }
            
            # Result passed threshold - auto-apply
            
            # Apply metadata to series
            fields_updated = []
            metadata = result.metadata
            
            # Update fields if overwrite=True or field is empty
            def should_update(field_value):
                return overwrite or not field_value
            
            if metadata.get('title') and should_update(series.display_name):
                series.display_name = metadata['title']
                fields_updated.append('display_name')
            
            if metadata.get('description') and should_update(series.description):
                series.description = metadata['description']
                fields_updated.append('description')
            
            if metadata.get('writer') and should_update(series.writer):
                series.writer = metadata['writer']
                fields_updated.append('writer')
            
            if metadata.get('artist') and should_update(series.artist):
                series.artist = metadata['artist']
                fields_updated.append('artist')
            
            if metadata.get('genre') and should_update(series.genre):
                series.genre = metadata['genre']
                fields_updated.append('genre')
            
            if metadata.get('year') and should_update(series.year_start):
                series.year_start = metadata['year']
                fields_updated.append('year_start')
            
            if metadata.get('publisher') and should_update(series.publisher):
                series.publisher = metadata['publisher']
                fields_updated.append('publisher')
            
            if metadata.get('status') and should_update(series.status):
                series.status = metadata['status']
                fields_updated.append('status')
            
            if metadata.get('format') and should_update(series.format):
                series.format = metadata['format']
                fields_updated.append('format')
            
            if metadata.get('volume') and should_update(series.volumes):
                series.volumes = metadata['volume']
                fields_updated.append('volumes')
            
            if metadata.get('count') and should_update(series.chapters):
                series.chapters = metadata['count']
                fields_updated.append('chapters')
            
            # Join tags if they're a list
            if result.tags and should_update(series.tags):
                series.tags = ', '.join(result.tags) if isinstance(result.tags, list) else str(result.tags)
                fields_updated.append('tags')
            
            # Store scanner metadata
            series.scanner_source = primary_scanner
            series.scanner_source_id = result.source_id
            series.scanner_source_url = result.source_url
            series.scanned_at = int(time.time())
            series.scan_confidence = result.confidence
            series.updated_at = int(time.time())
            fields_updated.append('scanner_metadata')
            
            session.commit()
            session.refresh(series)
            
            # Invalidate browse cache so UI gets fresh data with new metadata
            try:
                from src.services.library_cache import get_library_cache
                get_library_cache(library_id).invalidate_all()
                logger.info(f"Invalidated browse cache for library {library_id} after series scan")
            except Exception as cache_err:
                logger.warning(f"Failed to invalidate browse cache: {cache_err}")
            
            return {
                "success": True,
                "series_id": series.id,
                "confidence": result.confidence,
                "fields_updated": fields_updated,
                "metadata": metadata,
                "source_url": result.source_url
            }
            
        except Exception as e:
            session.rollback()
            return {
                "success": False,
                "error": str(e),
                "series_id": series.id if series else None
            }


async def apply_series_metadata(
    library_id: int,
    series_name: str,
    source_id: str,
    metadata: Dict[str, Any],
    source_url: Optional[str] = None,
    confidence: float = 0.0,
    overwrite: bool = False,
    request: Request = None
) -> Dict[str, Any]:
    """
    Apply metadata from a manually selected candidate to a series.
    
    This endpoint is used when the user manually selects a candidate
    from the low-confidence results returned by scan_and_save_series.
    """
    db = request.app.state.db
    
    with db.get_session() as session:
        # Get library and scanner config
        library = session.query(Library).filter(Library.id == library_id).first()
        if not library:
            raise HTTPException(status_code=404, detail=f"Library {library_id} not found")
        
        settings = library.settings or {}
        scanner_config = settings.get('scanner', {})
        primary_scanner = scanner_config.get('primary_scanner', 'manual')
        
        # Get or create series
        series = session.query(Series).filter(
            Series.library_id == library_id,
            Series.name == series_name
        ).first()
        
        if not series:
            series = Series(
                library_id=library_id,
                name=series_name,
                display_name=series_name,
                created_at=int(time.time()),
                updated_at=int(time.time())
            )
            session.add(series)
            session.flush()
        
        # Apply metadata to series
        fields_updated = []
        
        def should_update(field_value):
            return overwrite or not field_value
        
        if metadata.get('title') and should_update(series.display_name):
            series.display_name = metadata['title']
            fields_updated.append('display_name')
        
        if metadata.get('description') and should_update(series.description):
            series.description = metadata['description']
            fields_updated.append('description')
        
        if metadata.get('writer') and should_update(series.writer):
            series.writer = metadata['writer']
            fields_updated.append('writer')
        
        if metadata.get('artist') and should_update(series.artist):
            series.artist = metadata['artist']
            fields_updated.append('artist')
        
        if metadata.get('genre') and should_update(series.genre):
            series.genre = metadata['genre']
            fields_updated.append('genre')
        
        if metadata.get('year') and should_update(series.year_start):
            series.year_start = metadata['year']
            fields_updated.append('year_start')
        
        if metadata.get('publisher') and should_update(series.publisher):
            series.publisher = metadata['publisher']
            fields_updated.append('publisher')
        
        if metadata.get('status') and should_update(series.status):
            series.status = metadata['status']
            fields_updated.append('status')
        
        if metadata.get('format') and should_update(series.format):
            series.format = metadata['format']
            fields_updated.append('format')
        
        if metadata.get('volume') and should_update(series.volumes):
            series.volumes = metadata['volume']
            fields_updated.append('volumes')
        
        if metadata.get('count') and should_update(series.chapters):
            series.chapters = metadata['count']
            fields_updated.append('chapters')
        
        # Handle tags
        if metadata.get('tags') and should_update(series.tags):
            tags = metadata['tags']
            series.tags = ', '.join(tags) if isinstance(tags, list) else str(tags)
            fields_updated.append('tags')
        
        # Store scanner metadata
        series.scanner_source = primary_scanner
        series.scanner_source_id = source_id
        series.scanner_source_url = source_url
        series.scanned_at = int(time.time())
        series.scan_confidence = confidence
        series.updated_at = int(time.time())
        fields_updated.append('scanner_metadata')
        
        session.commit()
        session.refresh(series)
        
        # Invalidate browse cache
        try:
            from src.services.library_cache import get_library_cache
            get_library_cache(library_id).invalidate_all()
            logger.info(f"Invalidated browse cache for library {library_id} after manual metadata apply")
        except Exception as cache_err:
            logger.warning(f"Failed to invalidate browse cache: {cache_err}")
        
        return {
            "success": True,
            "series_id": series.id,
            "confidence": confidence,
            "fields_updated": fields_updated,
            "metadata": metadata,
            "source_url": source_url
        }


async def test_scanner(scanner_name: str, query: str) -> Dict[str, Any]:
    """
    Test a specific scanner with a query.

    Useful for debugging and testing scanner behavior.

    Example:
        GET /scanners/test/nhentai?query=[Artist] Title [English].cbz
    """
    manager = get_scanner_manager()

    if scanner_name not in manager.get_available_scanners():
        raise HTTPException(status_code=404, detail=f"Scanner '{scanner_name}' not found")

    # Instantiate the scanner class directly
    scanner_class = manager._available_scanners[scanner_name]
    scanner_instance = scanner_class()

    try:
        # Use default confidence threshold for testing
        result, candidates = scanner_instance.scan(query, confidence_threshold=0.4)

        return {
            "scanner": scanner_name,
            "query": query,
            "result": result.to_dict() if result else None,
            "candidates_count": len(candidates)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
