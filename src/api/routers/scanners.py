"""
Scanner API endpoints

Provides REST API for metadata scanner management and execution.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
import sys
from pathlib import Path

# Add scanners to path
SCANNERS_PATH = Path(__file__).parent.parent.parent.parent / "scanners"
sys.path.insert(0, str(SCANNERS_PATH))

from scanners import (
    init_default_scanners,
    get_manager,
    ScannerManager,
    ScanResult,
    MatchConfidence,
    FallbackStrategy
)

# Import database dependencies
from ...database.models import Library

router = APIRouter(prefix="/scanners", tags=["scanners"])


# ============================================================================
# Pydantic Models
# ============================================================================

class ScanLevelEnum(str, Enum):
    FILE = "file"
    SERIES = "series"


class ConfidenceLevelEnum(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EXACT = "EXACT"


class ScanResultModel(BaseModel):
    """Scan result response model"""
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    confidence_level: ConfidenceLevelEnum
    source_id: Optional[str] = Field(None, description="ID from external source")
    source_url: Optional[str] = Field(None, description="URL to source")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)

    class Config:
        schema_extra = {
            "example": {
                "confidence": 1.0,
                "confidence_level": "EXACT",
                "source_id": "573470",
                "source_url": "https://nhentai.net/g/573470",
                "metadata": {
                    "title": "(C102) [Yachan Coffee] ...",
                    "artists": ["yachan"],
                    "groups": ["yachan coffee"]
                },
                "tags": ["tag:swimsuit", "artist:yachan"]
            }
        }


class ScannerInfo(BaseModel):
    """Information about an available scanner"""
    name: str
    scan_level: ScanLevelEnum
    description: Optional[str] = None
    requires_config: bool = False
    config_keys: List[str] = Field(default_factory=list)
    provided_fields: List[str] = Field(default_factory=list)
    primary_fields: List[str] = Field(default_factory=list)


class LibraryScannerConfig(BaseModel):
    """Scanner configuration for a library"""
    library_id: int
    library_name: str
    library_path: Optional[str] = None
    primary_scanner: Optional[str] = None
    scan_level: Optional[ScanLevelEnum] = None  # FILE or SERIES - determines UI scanning options
    fallback_scanners: List[str] = Field(default_factory=list)
    fallback_threshold: float = Field(0.7, ge=0.0, le=1.0)
    confidence_threshold: float = Field(0.4, ge=0.0, le=1.0)


class UpdateLibraryScannerConfig(BaseModel):
    """Request model for updating library scanner configuration"""
    primary_scanner: str = Field(..., description="Primary scanner to use")
    fallback_scanners: List[str] = Field(default_factory=list, description="Fallback scanners (optional)")
    confidence_threshold: float = Field(0.4, ge=0.0, le=1.0, description="Minimum confidence threshold")
    fallback_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Threshold to trigger fallback")

    class Config:
        schema_extra = {
            "example": {
                "primary_scanner": "nhentai",
                "fallback_scanners": [],
                "confidence_threshold": 0.4,
                "fallback_threshold": 0.7
            }
        }


class ScanRequest(BaseModel):
    """Request to scan a file or series"""
    query: str = Field(..., description="Filename or series name to scan")
    library_id: Optional[int] = Field(None, description="Library ID (recommended)")
    scanner_name: Optional[str] = Field(None, description="Specific scanner to use (overrides library config)")
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    # Deprecated fields for backward compatibility
    library_type: Optional[str] = Field(None, description="[DEPRECATED] Use library_id instead")

    class Config:
        schema_extra = {
            "example": {
                "query": "[Artist] Comic Title [English].cbz",
                "library_id": 1,
                "confidence_threshold": 0.4
            }
        }


class BulkScanRequest(BaseModel):
    """Request to scan multiple files"""
    queries: List[str] = Field(..., description="List of filenames or series names")
    library_id: int = Field(..., description="Library ID")
    confidence_threshold: Optional[float] = Field(0.4, ge=0.0, le=1.0)
    # Deprecated field
    library_type: Optional[str] = Field(None, description="[DEPRECATED] Use library_id instead")


class BulkScanResult(BaseModel):
    """Result of bulk scan operation"""
    total: int
    matched: int
    rejected: int
    results: List[Dict[str, Any]]


# ============================================================================
# Scanner Manager Singleton
# ============================================================================

_scanner_manager: Optional[ScannerManager] = None


def get_scanner_manager() -> ScannerManager:
    """Get or initialize the scanner manager"""
    global _scanner_manager
    if _scanner_manager is None:
        _scanner_manager = init_default_scanners()
    return _scanner_manager


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/available", response_model=List[ScannerInfo])
async def get_available_scanners():
    """
    Get list of available scanners

    Returns information about all registered scanners including their capabilities.
    """
    from scanners.metadata_schema import get_scanner_capabilities
    from scanners import NhentaiScanner, AniListScanner
    
    manager = get_scanner_manager()
    available = manager.get_available_scanners()

    scanners_info = []
    
    # Scanner metadata mapping
    scanner_metadata = {
        "nhentai": {
            "class": NhentaiScanner,
            "scan_level": ScanLevelEnum.FILE,
            "requires_config": False,
            "config_keys": ["confidence_threshold", "use_fallback_searches", "sort_by"]
        },
        "AniList": {
            "class": AniListScanner,
            "scan_level": ScanLevelEnum.SERIES,
            "requires_config": False,
            "config_keys": ["confidence_threshold", "use_romaji_titles", "use_english_titles", "use_native_titles", "max_results"]
        }
    }
    
    # Build info for each available scanner
    for scanner_name in available:
        # Get capabilities from metadata schema (try exact match first, then lowercase)
        caps = get_scanner_capabilities(scanner_name)
        if not caps:
            caps = get_scanner_capabilities(scanner_name.lower())
        
        # Get scanner metadata
        meta = scanner_metadata.get(scanner_name, {})
        
        scanners_info.append(ScannerInfo(
            name=scanner_name,
            scan_level=meta.get("scan_level", ScanLevelEnum.SERIES),
            description=caps.description if caps else f"Metadata scanner: {scanner_name}",
            requires_config=meta.get("requires_config", False),
            config_keys=meta.get("config_keys", []),
            provided_fields=[f.value for f in caps.provided_fields] if caps else [],
            primary_fields=[f.value for f in caps.primary_fields] if caps else []
        ))

    return scanners_info


@router.get("/libraries", response_model=List[LibraryScannerConfig])
async def get_library_scanner_configs(request: Request):
    """
    Get scanner configuration for all libraries

    Returns all libraries from the database with their scanner configurations.
    Scanner settings are stored in the library's settings JSON field.
    """
    db = request.app.state.db

    with db.get_session() as session:
        libraries = session.query(Library).all()
        manager = get_scanner_manager()

        configs = []
        for lib in libraries:
            # Get scanner settings from library settings JSON
            settings = lib.settings or {}
            scanner_config = settings.get('scanner', {})
            primary_scanner = scanner_config.get('primary_scanner')
            
            # Determine scan level from the primary scanner
            scan_level = None
            if primary_scanner and primary_scanner in manager.get_available_scanners():
                try:
                    # Get the scanner class and instantiate to check scan_level
                    scanner_class = manager._available_scanners.get(primary_scanner)
                    if scanner_class:
                        temp_scanner = scanner_class()
                        # Map from ScanLevel enum to ScanLevelEnum
                        if temp_scanner.scan_level.value == 'file':
                            scan_level = ScanLevelEnum.FILE
                        elif temp_scanner.scan_level.value == 'series':
                            scan_level = ScanLevelEnum.SERIES
                except Exception:
                    pass  # Fallback to None if scanner can't be instantiated

            configs.append(LibraryScannerConfig(
                library_id=lib.id,
                library_name=lib.name,
                library_path=lib.path,
                primary_scanner=primary_scanner,
                scan_level=scan_level,
                fallback_scanners=scanner_config.get('fallback_scanners', []),
                fallback_threshold=scanner_config.get('fallback_threshold', 0.7),
                confidence_threshold=scanner_config.get('confidence_threshold', 0.4)
            ))

        return configs


@router.post("/scan", response_model=ScanResultModel)
async def scan_single(scan_request: ScanRequest, request: Request):
    """
    Scan a single file or series for metadata

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


@router.post("/scan/bulk", response_model=BulkScanResult)
async def scan_bulk(bulk_request: BulkScanRequest, request: Request):
    """
    Scan multiple files or series for metadata

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


@router.post("/scan/series")
async def scan_and_save_series(
    library_id: int,
    series_name: str,
    confidence_threshold: Optional[float] = None,
    overwrite: bool = False,
    request: Request = None
):
    """
    Scan and save metadata for a series
    
    Scans the series using the library's configured scanner and saves
    the metadata to the database.
    """
    from ...database.models import Series, Library
    import time
    
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
        
        # Determine library type for scanner
        library_type = 'manga' if primary_scanner == 'AniList' else 'doujinshi'
        
        kwargs = {}
        if confidence_threshold is not None:
            kwargs['confidence_threshold'] = confidence_threshold
        elif scanner_config:
            kwargs['confidence_threshold'] = scanner_config.get('confidence_threshold', 0.6)
        
        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[SERIES SCAN] series_name='{series_name}', library_type='{library_type}', scanner='{primary_scanner}', kwargs={kwargs}")
        
        try:
            result, candidates = manager.scan(library_type, series_name, **kwargs)
            
            logger.info(f"[SERIES SCAN] result={result is not None}, candidates={len(candidates) if candidates else 0}")
            if result:
                logger.info(f"[SERIES SCAN] confidence={result.confidence}, title={result.metadata.get('title')}")
            
            if not result:
                return {
                    "success": False,
                    "error": "No match found with sufficient confidence",
                    "series_id": series.id
                }
            
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


@router.get("/test/{scanner_name}")
async def test_scanner(scanner_name: str, query: str):
    """
    Test a specific scanner with a query

    Useful for debugging and testing scanner behavior.

    Example:
        GET /scanners/test/nhentai?query=[Artist] Title [English].cbz
    """
    manager = get_scanner_manager()

    if scanner_name not in manager.get_available_scanners():
        raise HTTPException(status_code=404, detail=f"Scanner '{scanner_name}' not found")

    # For now, we'll use the configured library for this scanner
    # TODO: Allow direct scanner invocation
    configured = manager.get_configured_libraries()
    library_type = None

    for lib in configured:
        lib_config = manager.get_library_config(lib)
        if lib_config and lib_config[0].scanner_class({}).source_name == scanner_name:
            library_type = lib
            break

    if not library_type:
        raise HTTPException(
            status_code=400,
            detail=f"Scanner '{scanner_name}' not configured for any library"
        )

    try:
        result, candidates = manager.scan(library_type, query)

        return {
            "scanner": scanner_name,
            "query": query,
            "result": result.to_dict() if result else None,
            "candidates_count": len(candidates)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Configuration Endpoints (for admin UI)
# ============================================================================

@router.put("/libraries/{library_id}/configure", response_model=LibraryScannerConfig)
async def configure_library_scanner(
    library_id: int,
    config: UpdateLibraryScannerConfig,
    request: Request
):
    """
    Configure scanner for a specific library

    Updates the scanner configuration for a library and saves it to the database.

    Example:
        PUT /scanners/libraries/4/configure
        {
            "primary_scanner": "nhentai",
            "fallback_scanners": [],
            "confidence_threshold": 0.4,
            "fallback_threshold": 0.7
        }
    """
    db = request.app.state.db
    manager = get_scanner_manager()

    with db.get_session() as session:
        # Validate library exists
        library = session.query(Library).filter(Library.id == library_id).first()
        if not library:
            raise HTTPException(
                status_code=404,
                detail=f"Library with ID {library_id} not found"
            )

        # Validate primary scanner
        if config.primary_scanner not in manager.get_available_scanners():
            raise HTTPException(
                status_code=400,
                detail=f"Scanner '{config.primary_scanner}' not available"
            )

        # Validate fallback scanners
        for fallback in config.fallback_scanners:
            if fallback not in manager.get_available_scanners():
                raise HTTPException(
                    status_code=400,
                    detail=f"Fallback scanner '{fallback}' not available"
                )

        # Update library settings
        settings = library.settings or {}
        settings['scanner'] = {
            'primary_scanner': config.primary_scanner,
            'fallback_scanners': config.fallback_scanners,
            'confidence_threshold': config.confidence_threshold,
            'fallback_threshold': config.fallback_threshold
        }
        
        # Force SQLAlchemy to detect the change to the JSON column
        from sqlalchemy.orm.attributes import flag_modified
        library.settings = settings
        flag_modified(library, 'settings')

        # Save to database
        session.commit()
        session.refresh(library)

        # Return updated configuration
        return LibraryScannerConfig(
            library_id=library.id,
            library_name=library.name,
            library_path=library.path,
            primary_scanner=config.primary_scanner,
            fallback_scanners=config.fallback_scanners,
            confidence_threshold=config.confidence_threshold,
            fallback_threshold=config.fallback_threshold
        )


# ============================================================================
# Comic Scanning Endpoints
# ============================================================================

class ScanComicRequest(BaseModel):
    """Request model for scanning a comic"""
    comic_id: int
    overwrite: bool = Field(False, description="Overwrite existing metadata")
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)


class ScanLibraryRequest(BaseModel):
    """Request model for scanning a library"""
    library_id: int
    overwrite: bool = Field(False, description="Overwrite existing metadata")
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    rescan_existing: bool = Field(False, description="Rescan comics already scanned")


class ClearMetadataRequest(BaseModel):
    """Request model for clearing metadata"""
    comic_ids: Optional[List[int]] = Field(None, description="Specific comic IDs to clear")
    library_id: Optional[int] = Field(None, description="Clear all comics in library")
    clear_scanner_info: bool = Field(True, description="Clear scanner metadata")
    clear_tags: bool = Field(True, description="Clear tags")
    clear_metadata: bool = Field(False, description="Clear all metadata fields")


class ScanComicResponse(BaseModel):
    """Response for comic scan"""
    comic_id: int
    success: bool
    confidence: Optional[float] = None
    fields_updated: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class ScanLibraryResponse(BaseModel):
    """Response for library scan"""
    total_comics: int
    scanned: int
    failed: int
    skipped: int
    results: List[ScanComicResponse]


@router.post("/scan/comic", response_model=ScanComicResponse)
async def scan_comic(
    scan_request: ScanComicRequest,
    background_tasks: BackgroundTasks,
    request: Request
):
    """
    Scan a single comic for metadata

    Uses the scanner configured for the comic's library.
    """
    from ...services.metadata_service import MetadataService
    from ...database.models import Comic

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
            # Scan using filename
            # TODO: Use direct scanner invocation instead of library_type
            library_type = 'doujinshi'  # Default for nhentai
            result, _ = manager.scan(
                library_type,
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


@router.post("/scan/library", response_model=ScanLibraryResponse)
async def scan_library(
    scan_request: ScanLibraryRequest,
    background_tasks: BackgroundTasks,
    request: Request
):
    """
    Scan all comics in a library for metadata

    This can take a while for large libraries.
    """
    from ...services.metadata_service import MetadataService
    from ...database.models import Comic, Library

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

        # Get all comics in library
        query = session.query(Comic).filter(Comic.library_id == scan_request.library_id)
        
        # Filter out already scanned if not rescanning
        if not scan_request.rescan_existing:
            query = query.filter(Comic.scanned_at.is_(None))
        
        comics = query.all()

        # Determine confidence threshold
        threshold = scan_request.confidence_threshold
        if threshold is None:
            threshold = scanner_config.get('confidence_threshold', 0.4)

        results = []
        scanned = 0
        failed = 0
        skipped = 0

        # TODO: Use direct scanner invocation
        library_type = 'doujinshi'  # Default for nhentai

        for comic in comics:
            try:
                # Scan using filename
                result, _ = manager.scan(
                    library_type,
                    comic.filename,
                    confidence_threshold=threshold
                )

                if not result:
                    skipped += 1
                    results.append(ScanComicResponse(
                        comic_id=comic.id,
                        success=False,
                        error="No match found with sufficient confidence"
                    ))
                    continue

                # Apply metadata
                application_result = MetadataService.apply_scan_result_to_comic(
                    session,
                    comic,
                    result,
                    primary_scanner,
                    overwrite=scan_request.overwrite
                )

                if application_result.success:
                    scanned += 1
                else:
                    failed += 1

                results.append(ScanComicResponse(
                    comic_id=comic.id,
                    success=application_result.success,
                    confidence=result.confidence,
                    fields_updated=application_result.fields_updated,
                    error=application_result.error
                ))

            except Exception as e:
                failed += 1
                results.append(ScanComicResponse(
                    comic_id=comic.id,
                    success=False,
                    error=str(e)
                ))

        return ScanLibraryResponse(
            total_comics=len(comics),
            scanned=scanned,
            failed=failed,
            skipped=skipped,
            results=results
        )


@router.post("/clear-metadata")
async def clear_metadata(
    clear_request: ClearMetadataRequest,
    request: Request
):
    """
    Clear metadata from comics

    Can clear scanner info, tags, or all metadata from specific comics or entire library.
    """
    from ...database.models import Comic

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
