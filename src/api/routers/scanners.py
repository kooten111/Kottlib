"""
Scanner API endpoints

Provides REST API for metadata scanner management and execution.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
import logging
import sys
from pathlib import Path

from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.scanners import (
    init_default_scanners,
    get_manager,
    ScannerManager,
    ScanResult,
    MatchConfidence,
    FallbackStrategy
)

# Import database dependencies
from ...database.models import Library
from ...database import update_library, get_library_by_id

router = APIRouter(prefix="/scanners", tags=["scanners"])
logger = logging.getLogger(__name__)


# ============================================================================
# Progress Tracking
# ============================================================================

# In-memory progress tracking cache for library scans
# Note: This is a performance optimization cache. The source of truth is stored
# in the database (library.settings['scanner_progress']) to support multi-worker
# deployments. The API endpoint merges both memory and database state, keeping
# the most advanced progress values. See _persist_progress_to_db() and
# get_library_scan_progress() for the multi-worker architecture.
_scan_progress: Dict[int, Dict[str, Any]] = {}


def _normalize_progress(progress: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize progress payload to expected shape and types"""
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
    """Return a copy of progress without internal bookkeeping keys"""
    if not progress:
        return progress
    cleaned = {
        key: value
        for key, value in progress.items()
        if not str(key).startswith("_")
    }
    return _normalize_progress(cleaned)


def _merge_progress(primary: Dict[str, Any], secondary: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two progress dictionaries, keeping the most advanced values"""
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


def _persist_progress_to_db(session: Session, library: Library, progress: Dict[str, Any]):
    """Persist scan progress to the database for cross-worker visibility"""
    if not library:
        return

    serialized = _sanitize_progress(progress or {})

    settings = dict(library.settings or {})
    settings['scanner_progress'] = serialized
    library.settings = settings
    session.add(library)
    session.commit()


def start_scan_progress(library_id: int) -> Dict[str, Any]:
    """Initialize scan progress for a library"""
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


def update_scan_progress(library_id: int, processed: int, total: int, scanned: int = 0, failed: int = 0, skipped: int = 0):
    """Update scan progress for a library"""
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
    """Get scan progress for a library"""
    return _scan_progress.get(library_id)


def clear_scan_progress(library_id: int):
    """Clear scan progress for a library"""
    if library_id in _scan_progress:
        del _scan_progress[library_id]


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
        json_schema_extra = {
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
    config_keys: List[str] = Field(default_factory=list)  # DEPRECATED: use config_schema instead
    config_schema: List[Dict[str, Any]] = Field(default_factory=list)  # Declarative config schema
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
    scanner_configs: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class UpdateLibraryScannerConfig(BaseModel):
    """Request model for updating library scanner configuration"""
    primary_scanner: str = Field(..., description="Primary scanner to use")
    fallback_scanners: List[str] = Field(default_factory=list, description="Fallback scanners (optional)")
    confidence_threshold: float = Field(0.4, ge=0.0, le=1.0, description="Minimum confidence threshold")
    fallback_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Threshold to trigger fallback")
    scanner_configs: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Configuration for specific scanners (e.g. API keys)")

    class Config:
        json_schema_extra = {
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
        json_schema_extra = {
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
    from src.scanners.metadata_schema import get_scanner_capabilities
    
    manager = get_scanner_manager()
    available = manager.get_available_scanners()

    scanners_info = []
    
    # Build info for each available scanner
    for scanner_name in available:
        # Get capabilities from metadata schema (try exact match first, then lowercase)
        caps = get_scanner_capabilities(scanner_name)
        if not caps:
            caps = get_scanner_capabilities(scanner_name.lower())
        
        # Get scanner class to check scan_level and config
        scanner_class = manager._available_scanners.get(scanner_name)
        scan_level = ScanLevelEnum.SERIES  # Default
        requires_config = False
        config_keys = []
        
        # Get declarative config schema
        config_schema = []

        if scanner_class:
            try:
                # Instantiate to get properties
                temp_scanner = scanner_class()

                # Map from ScanLevel enum to ScanLevelEnum
                if temp_scanner.scan_level.value == 'file':
                    scan_level = ScanLevelEnum.FILE
                elif temp_scanner.scan_level.value == 'series':
                    scan_level = ScanLevelEnum.SERIES

                # Get declarative config schema (new method)
                schema_options = temp_scanner.get_config_schema()
                if schema_options:
                    config_schema = [opt.to_dict() for opt in schema_options]
                    # Mark as requiring config if any options are required
                    requires_config = any(opt.required for opt in schema_options)

                # Get config requirements (deprecated method, for backward compatibility)
                config_keys = temp_scanner.get_required_config_keys()
                if config_keys and not requires_config:
                    requires_config = True

                # Check for optional config keys if exposed as property (convention)
                if hasattr(temp_scanner, 'config_keys'):
                    extra_keys = getattr(temp_scanner, 'config_keys')
                    if isinstance(extra_keys, list):
                        for key in extra_keys:
                            if key not in config_keys:
                                config_keys.append(key)

            except Exception as e:
                logger.warning(f"Failed to inspect scanner {scanner_name}: {e}")
        
        scanners_info.append(ScannerInfo(
            name=scanner_name,
            scan_level=scan_level,
            description=caps.description if caps else f"Metadata scanner: {scanner_name}",
            requires_config=requires_config,
            config_keys=config_keys,
            config_schema=config_schema,
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
                confidence_threshold=scanner_config.get('confidence_threshold', 0.4),
                scanner_configs=scanner_config.get('scanner_configs', {})
            ))

        return configs


@router.put("/libraries/{library_id}/configure", response_model=LibraryScannerConfig)
async def configure_library_scanner(
    library_id: int,
    config: UpdateLibraryScannerConfig,
    request: Request
):
    """
    Update scanner configuration for a library
    """
    db = request.app.state.db
    manager = get_scanner_manager()

    # Validate scanner existence
    if config.primary_scanner not in manager.get_available_scanners():
        raise HTTPException(
            status_code=400,
            detail=f"Scanner '{config.primary_scanner}' is not available"
        )

    for scanner in config.fallback_scanners:
        if scanner not in manager.get_available_scanners():
            raise HTTPException(
                status_code=400,
                detail=f"Fallback scanner '{scanner}' is not available"
            )

    with db.get_session() as session:
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Get existing settings
        settings = dict(library.settings or {})
        scanner_settings = settings.get('scanner', {})

        # Update scanner settings
        scanner_settings.update({
            'primary_scanner': config.primary_scanner,
            'fallback_scanners': config.fallback_scanners,
            'confidence_threshold': config.confidence_threshold,
            'fallback_threshold': config.fallback_threshold,
            'scanner_configs': config.scanner_configs
        })
        
        settings['scanner'] = scanner_settings

        # Save to DB
        update_library(session, library_id, settings=settings)

        # Determine scan level
        scan_level = None
        try:
            scanner_class = manager._available_scanners.get(config.primary_scanner)
            if scanner_class:
                temp_scanner = scanner_class()
                if temp_scanner.scan_level.value == 'file':
                    scan_level = ScanLevelEnum.FILE
                elif temp_scanner.scan_level.value == 'series':
                    scan_level = ScanLevelEnum.SERIES
        except Exception:
            pass

        return LibraryScannerConfig(
            library_id=library.id,
            library_name=library.name,
            library_path=library.path,
            primary_scanner=config.primary_scanner,
            scan_level=scan_level,
            fallback_scanners=config.fallback_scanners,
            fallback_threshold=config.fallback_threshold,
            confidence_threshold=config.confidence_threshold
        )


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
        if primary_scanner == 'AniList':
            library_type = 'manga'
        elif primary_scanner == 'Comic Vine':
            library_type = 'comics'
        else:
            library_type = 'doujinshi'
        
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


def _run_library_scan_task(
    db,
    library_id: int,
    scanner_name: str,
    overwrite: bool,
    rescan_existing: bool,
    confidence_threshold: Optional[float]
):
    """Background task to scan all comics in a library"""
    from ...services.metadata_service import MetadataService
    from ...database.models import Comic, Library, Series
    import time

    manager = get_scanner_manager()
    scanned = 0
    failed = 0
    skipped = 0
    processed = 0
    total_items = 0

    try:
        with db.get_session() as session:
            library = session.query(Library).filter(Library.id == library_id).first()
            if not library:
                logger.warning("Library %s no longer exists; aborting scan", library_id)
                return

            # Get scanner and determine scan level
            if scanner_name not in manager.get_available_scanners():
                logger.error("Scanner %s not available", scanner_name)
                return

            scanner_class = manager._available_scanners[scanner_name]
            scanner_instance = scanner_class()
            scan_level = scanner_instance.scan_level

            logger.info(
                "Starting library scan for library %s with scanner %s (scan_level=%s, rescan_existing=%s)",
                library_id,
                scanner_name,
                scan_level.value,
                rescan_existing
            )

            # Determine library type for scanner
            library_type = 'manga' if scanner_name == 'AniList' else 'doujinshi'

            # Branch based on scan level (use string comparison to avoid enum import issues)
            if scan_level.value == 'file':
                # FILE-level scanning: scan each comic individually
                logger.info("Using FILE-level scanning (each comic individually)")

                # Get all comics in library
                query = session.query(Comic).filter(Comic.library_id == library_id)

                # Filter out already scanned if not rescanning
                if not rescan_existing:
                    query = query.filter(or_(Comic.scanned_at.is_(None), Comic.scanned_at == 0))

                comics = query.all()
                total_items = len(comics)

                # Initialize progress with known totals
                update_scan_progress(library_id, 0, total_items, 0, 0, 0)
                _persist_progress_to_db(session, library, _scan_progress.get(library_id, {}))

                for index, comic in enumerate(comics):
                    processed = index + 1

                    try:
                        # Scan using filename
                        result, _ = manager.scan(
                            library_type,
                            comic.filename,
                            confidence_threshold=confidence_threshold
                        )

                        if not result:
                            skipped += 1
                        else:
                            # Apply metadata
                            application_result = MetadataService.apply_scan_result_to_comic(
                                session,
                                comic,
                                result,
                                scanner_name,
                                overwrite=overwrite
                            )

                            if application_result.success:
                                scanned += 1
                            else:
                                failed += 1

                    except Exception:
                        failed += 1
                        logger.exception("Failed to scan comic %s in library %s", comic.id, library_id)

                    # Update progress after each comic
                    update_scan_progress(library_id, processed, total_items, scanned, failed, skipped)
                    _persist_progress_to_db(session, library, _scan_progress.get(library_id, {}))

            elif scan_level.value == 'series':
                # SERIES-level scanning: scan each unique series
                logger.info("Using SERIES-level scanning (by series name)")

                # Get all unique series names from comics
                series_query = session.query(
                    Comic.series
                ).filter(
                    Comic.library_id == library_id,
                    Comic.series.isnot(None),
                    Comic.series != ''
                ).distinct()
                unique_series = [s[0] for s in series_query.all()]

                total_items = len(unique_series)
                logger.info("Found %s unique series to scan", total_items)

                # Initialize progress with known totals
                update_scan_progress(library_id, 0, total_items, 0, 0, 0)
                _persist_progress_to_db(session, library, _scan_progress.get(library_id, {}))

                for index, series_name in enumerate(unique_series):
                    processed = index + 1

                    try:
                        logger.info("Scanning series: %s", series_name)

                        # Scan for series metadata with retry logic for rate limiting
                        max_retries = 3
                        result = None

                        for attempt in range(max_retries):
                            try:
                                result, _ = manager.scan(
                                    library_type,
                                    series_name,
                                    confidence_threshold=confidence_threshold
                                )
                                break  # Success, exit retry loop
                            except Exception as scan_error:
                                error_str = str(scan_error)
                                # Check if it's a rate limit error
                                if '429' in error_str or 'Too Many Requests' in error_str or 'Rate limit exceeded' in error_str:
                                    if attempt < max_retries - 1:
                                        # Try to extract Retry-After value from error message
                                        wait_time = 60  # Default to 60 seconds
                                        if '||RETRY_AFTER:' in error_str:
                                            try:
                                                retry_after_str = error_str.split('||RETRY_AFTER:')[1].strip()
                                                wait_time = int(retry_after_str)
                                            except (IndexError, ValueError):
                                                pass

                                        logger.warning(
                                            "Rate limit hit for series '%s', waiting %s seconds before retry %s/%s",
                                            series_name, wait_time, attempt + 1, max_retries
                                        )
                                        time.sleep(wait_time)
                                    else:
                                        logger.error("Max retries reached for series '%s' due to rate limiting", series_name)
                                        raise
                                else:
                                    # Not a rate limit error, raise immediately
                                    raise

                        if not result:
                            skipped += 1
                            logger.info("No match found for series: %s", series_name)
                        else:
                            # Get or create series record
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
                            metadata = result.metadata

                            def should_update(field_value):
                                return overwrite or not field_value

                            if metadata.get('title') and should_update(series.display_name):
                                series.display_name = metadata['title']

                            if metadata.get('description') and should_update(series.description):
                                series.description = metadata['description']

                            if metadata.get('writer') and should_update(series.writer):
                                series.writer = metadata['writer']

                            if metadata.get('artist') and should_update(series.artist):
                                series.artist = metadata['artist']

                            if metadata.get('genre') and should_update(series.genre):
                                series.genre = metadata['genre']

                            if metadata.get('year') and should_update(series.year_start):
                                series.year_start = metadata['year']

                            if metadata.get('publisher') and should_update(series.publisher):
                                series.publisher = metadata['publisher']

                            if metadata.get('status') and should_update(series.status):
                                series.status = metadata['status']

                            if metadata.get('format') and should_update(series.format):
                                series.format = metadata['format']

                            if metadata.get('volume') and should_update(series.volumes):
                                series.volumes = metadata['volume']

                            if metadata.get('count') and should_update(series.chapters):
                                series.chapters = metadata['count']

                            if result.tags and should_update(series.tags):
                                series.tags = ', '.join(result.tags) if isinstance(result.tags, list) else str(result.tags)

                            # Store scanner metadata
                            series.scanner_source = scanner_name
                            series.scanner_source_id = result.source_id
                            series.scanner_source_url = result.source_url
                            series.scanned_at = int(time.time())
                            series.scan_confidence = result.confidence
                            series.updated_at = int(time.time())

                            session.commit()
                            scanned += 1
                            logger.info("Successfully scanned series: %s (confidence: %.2f)", series_name, result.confidence)

                    except Exception:
                        failed += 1
                        logger.exception("Failed to scan series %s in library %s", series_name, library_id)
                        session.rollback()

                    # Update progress after each series
                    update_scan_progress(library_id, processed, total_items, scanned, failed, skipped)
                    _persist_progress_to_db(session, library, _scan_progress.get(library_id, {}))

            else:
                logger.error("Unsupported scan level: %s", scan_level)
                return

    except Exception as exc:
        logger.exception("Library scan failed for library %s", library_id)
        progress = _scan_progress.get(library_id) or start_scan_progress(library_id)
        progress.update({
            "processed": processed,
            "scanned": scanned,
            "total": total_items,
            "failed": failed,
            "skipped": skipped,
            "error": str(exc)
        })
        try:
            with db.get_session() as session:
                library = session.query(Library).filter(Library.id == library_id).first()
                if library:
                    _persist_progress_to_db(session, library, progress)
        except Exception:
            logger.exception("Failed to persist error progress for library %s", library_id)

    finally:
        progress = _scan_progress.get(library_id) or start_scan_progress(library_id)
        progress.update({
            "processed": processed,
            "scanned": scanned,
            "total": total_items,
            "failed": failed,
            "skipped": skipped,
            "in_progress": False,
            "completed": True
        })
        try:
            with db.get_session() as session:
                library = session.query(Library).filter(Library.id == library_id).first()
                if library:
                    _persist_progress_to_db(session, library, progress)
        except Exception:
            logger.exception("Failed to persist final progress for library %s", library_id)

        logger.info(
            "Library scan completed for library %s: processed=%s scanned=%s failed=%s skipped=%s",
            library_id,
            processed,
            scanned,
            failed,
            skipped
        )


@router.post("/scan/library")
async def scan_library(
    scan_request: ScanLibraryRequest,
    background_tasks: BackgroundTasks,
    request: Request
):
    """
    Scan all comics in a library for metadata

    This starts a background task and returns immediately.
    Use the /scan/library/{library_id}/progress endpoint to check progress.
    """
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
            _run_library_scan_task,
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


@router.get("/scan/library/{library_id}/progress")
async def get_library_scan_progress(library_id: int, request: Request):
    """
    Get the current progress of a library scan

    Returns the number of comics processed, scanned, and total to scan.
    """
    memory_progress = get_scan_progress(library_id)
    db_progress = None

    db = request.app.state.db
    with db.get_session() as session:
        library = session.query(Library).filter(Library.id == library_id).first()
        if library:
            settings = library.settings or {}
            stored_progress = settings.get('scanner_progress')
            if stored_progress:
                db_progress = stored_progress

    progress = _merge_progress(memory_progress, db_progress)
    progress = _sanitize_progress(progress)

    if progress:
        # Update in-memory cache so future reads on this worker stay current
        _scan_progress[library_id] = progress

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


@router.delete("/scan/library/{library_id}/progress")
async def clear_library_scan_progress(library_id: int, request: Request):
    """
    Clear the scan progress for a library

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
