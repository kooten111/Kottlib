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


class LibraryScannerConfig(BaseModel):
    """Scanner configuration for a library"""
    library_id: int
    library_name: str
    library_path: Optional[str] = None
    primary_scanner: Optional[str] = None
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
    library_id: Optional[int] = Field(None, description="Library ID (optional)")
    library_type: Optional[str] = Field(None, description="Library type (e.g., 'doujinshi')")
    scanner_name: Optional[str] = Field(None, description="Specific scanner to use")
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)

    class Config:
        schema_extra = {
            "example": {
                "query": "[Artist] Comic Title [English].cbz",
                "library_type": "doujinshi",
                "confidence_threshold": 0.4
            }
        }


class BulkScanRequest(BaseModel):
    """Request to scan multiple files"""
    queries: List[str] = Field(..., description="List of filenames or series names")
    library_id: Optional[int] = None
    library_type: Optional[str] = None
    confidence_threshold: Optional[float] = Field(0.4, ge=0.0, le=1.0)


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
    Get list of all available scanners

    Returns information about scanners that can be configured.
    """
    manager = get_scanner_manager()
    available = manager.get_available_scanners()

    # For now, return basic info for nhentai
    # TODO: Extend this when more scanners are added
    scanners_info = [
        ScannerInfo(
            name="nhentai",
            scan_level=ScanLevelEnum.FILE,
            description="File-level scanner for doujinshi metadata from nhentai.net",
            requires_config=False,
            config_keys=["confidence_threshold", "use_fallback_searches", "sort_by"]
        )
    ]

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

        configs = []
        for lib in libraries:
            # Get scanner settings from library settings JSON
            settings = lib.settings or {}
            scanner_config = settings.get('scanner', {})

            configs.append(LibraryScannerConfig(
                library_id=lib.id,
                library_name=lib.name,
                library_path=lib.path,
                primary_scanner=scanner_config.get('primary_scanner'),
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

    if scan_request.library_id:
        with db.get_session() as session:
            library = session.query(Library).filter(Library.id == scan_request.library_id).first()
            if not library:
                raise HTTPException(status_code=404, detail=f"Library {scan_request.library_id} not found")

            settings = library.settings or {}
            scanner_config = settings.get('scanner', {})
            library_name = library.name
    elif scan_request.library_type:
        # Legacy support: use library_type as a fallback
        library_name = scan_request.library_type
    else:
        raise HTTPException(status_code=400, detail="library_id or library_type required")

    # Check if scanner is configured
    primary_scanner = scanner_config.get('primary_scanner') if scanner_config else None

    if not primary_scanner:
        # Fallback to default scanners for backward compatibility
        manager = get_scanner_manager()
        if scan_request.library_type and scan_request.library_type in manager.get_configured_libraries():
            # Use manager's default configuration
            kwargs = {}
            if scan_request.confidence_threshold is not None:
                kwargs['confidence_threshold'] = scan_request.confidence_threshold
            result, candidates = manager.scan(scan_request.library_type, scan_request.query, **kwargs)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"No scanner configured for library '{library_name}'"
            )
    else:
        # Use configured scanner
        manager = get_scanner_manager()

        if primary_scanner not in manager.get_available_scanners():
            raise HTTPException(
                status_code=500,
                detail=f"Configured scanner '{primary_scanner}' is not available"
            )

        # For now, use the library_type approach with manager
        # TODO: Direct scanner invocation
        # Use library_type if provided, otherwise default to 'doujinshi' for nhentai
        library_type_for_scan = scan_request.library_type if scan_request.library_type else 'doujinshi'

        kwargs = {}
        if scan_request.confidence_threshold is not None:
            kwargs['confidence_threshold'] = scan_request.confidence_threshold
        elif scanner_config:
            kwargs['confidence_threshold'] = scanner_config.get('confidence_threshold', 0.4)

        result, candidates = manager.scan(library_type_for_scan, scan_request.query, **kwargs)

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
            "library_type": "doujinshi",
            "confidence_threshold": 0.4
        }
    """
    db = request.app.state.db
    manager = get_scanner_manager()

    # Get library configuration
    library_name = None
    scanner_config = None

    if bulk_request.library_id:
        with db.get_session() as session:
            library = session.query(Library).filter(Library.id == bulk_request.library_id).first()
            if not library:
                raise HTTPException(status_code=404, detail=f"Library {bulk_request.library_id} not found")

            settings = library.settings or {}
            scanner_config = settings.get('scanner', {})
            library_name = library.name

            # Check if scanner is configured
            if not scanner_config.get('primary_scanner'):
                raise HTTPException(
                    status_code=400,
                    detail=f"No scanner configured for library '{library_name}'"
                )
    elif bulk_request.library_type:
        # Legacy support
        library_name = bulk_request.library_type
        if library_name not in manager.get_configured_libraries():
            raise HTTPException(
                status_code=404,
                detail=f"Library type '{library_name}' not configured"
            )
    else:
        raise HTTPException(status_code=400, detail="library_id or library_type required")

    results = []
    matched = 0
    rejected = 0

    kwargs = {}
    if bulk_request.confidence_threshold is not None:
        kwargs['confidence_threshold'] = bulk_request.confidence_threshold
    elif scanner_config:
        kwargs['confidence_threshold'] = scanner_config.get('confidence_threshold', 0.4)

    # Use library_type for backward compatibility with manager
    scan_library_type = bulk_request.library_type if bulk_request.library_type else 'doujinshi'  # Fallback default

    for query in bulk_request.queries:
        try:
            result, _ = manager.scan(scan_library_type, query, **kwargs)

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
        total=len(request.queries),
        matched=matched,
        rejected=rejected,
        results=results
    )


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
        library.settings = settings

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
