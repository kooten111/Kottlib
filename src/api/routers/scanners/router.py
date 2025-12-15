"""
Scanner API router.

Main router that registers all scanner endpoints.
"""

from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request

from .models import (
    ScannerInfo,
    LibraryScannerConfig,
    UpdateLibraryScannerConfig,
    ScanRequest,
    ScanResultModel,
    BulkScanRequest,
    BulkScanResult,
    ScanComicRequest,
    ScanComicResponse,
    ScanLibraryRequest,
    ClearMetadataRequest,
)
from .endpoints import (
    get_available_scanners,
    get_library_scanner_configs,
    configure_library_scanner,
    verify_scanner_credentials,
    scan_single,
    scan_bulk,
    scan_and_save_series,
    test_scanner,
    scan_comic,
    scan_library,
    get_library_scan_progress,
    clear_library_scan_progress,
    clear_metadata,
)


router = APIRouter(prefix="/scanners", tags=["scanners"])


# ============================================================================
# Available Scanners Endpoints
# ============================================================================

@router.get("/available", response_model=List[ScannerInfo])
async def available_scanners_endpoint():
    """
    Get list of available scanners.

    Returns information about all registered scanners including their capabilities.
    """
    return await get_available_scanners()


@router.get("/libraries", response_model=List[LibraryScannerConfig])
async def library_configs_endpoint(request: Request):
    """
    Get scanner configuration for all libraries.

    Returns all libraries from the database with their scanner configurations.
    Scanner settings are stored in the library's settings JSON field.
    """
    return await get_library_scanner_configs(request)


# ============================================================================
# Configuration Endpoints
# ============================================================================

@router.put("/libraries/{library_id}/configure", response_model=LibraryScannerConfig)
async def configure_library_endpoint(
    library_id: int,
    config: UpdateLibraryScannerConfig,
    request: Request
):
    """
    Configure scanner for a specific library.

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
    return await configure_library_scanner(library_id, config, request)


@router.post("/verify-credentials/{scanner_name}")
async def verify_credentials_endpoint(
    scanner_name: str,
    credentials: Dict[str, Any],
    request: Request
):
    """
    Verify scanner credentials by attempting to instantiate and test.
    
    Example:
        POST /scanners/verify-credentials/metron
        {
            "username": "test_user",
            "password": "test_pass"
        }
    """
    return await verify_scanner_credentials(scanner_name, credentials, request)


# ============================================================================
# Single Scan Endpoints
# ============================================================================

@router.post("/scan", response_model=ScanResultModel)
async def scan_single_endpoint(scan_request: ScanRequest, request: Request):
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
    return await scan_single(scan_request, request)


@router.post("/scan/bulk", response_model=BulkScanResult)
async def scan_bulk_endpoint(bulk_request: BulkScanRequest, request: Request):
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
    return await scan_bulk(bulk_request, request)


@router.post("/scan/series")
async def scan_series_endpoint(
    library_id: int,
    series_name: str,
    confidence_threshold: Optional[float] = None,
    overwrite: bool = False,
    request: Request = None
):
    """
    Scan and save metadata for a series.
    
    Scans the series using the library's configured scanner and saves
    the metadata to the database.
    """
    return await scan_and_save_series(library_id, series_name, confidence_threshold, overwrite, request)


@router.get("/test/{scanner_name}")
async def test_scanner_endpoint(scanner_name: str, query: str):
    """
    Test a specific scanner with a query.

    Useful for debugging and testing scanner behavior.

    Example:
        GET /scanners/test/nhentai?query=[Artist] Title [English].cbz
    """
    return await test_scanner(scanner_name, query)


# ============================================================================
# Comic Scanning Endpoints
# ============================================================================

@router.post("/scan/comic", response_model=ScanComicResponse)
async def scan_comic_endpoint(
    scan_request: ScanComicRequest,
    background_tasks: BackgroundTasks,
    request: Request
):
    """
    Scan a single comic for metadata.

    Uses the scanner configured for the comic's library.
    """
    return await scan_comic(scan_request, background_tasks, request)


# ============================================================================
# Library Scanning Endpoints
# ============================================================================

@router.post("/scan/library")
async def scan_library_endpoint(
    scan_request: ScanLibraryRequest,
    background_tasks: BackgroundTasks,
    request: Request
):
    """
    Scan all comics in a library for metadata.

    This starts a background task and returns immediately.
    Use the /scan/library/{library_id}/progress endpoint to check progress.
    """
    return await scan_library(scan_request, background_tasks, request)


@router.get("/scan/library/{library_id}/progress")
async def scan_progress_endpoint(library_id: int, request: Request):
    """
    Get the current progress of a library scan.

    Returns the number of comics processed, scanned, and total to scan.
    """
    return await get_library_scan_progress(library_id, request)


@router.delete("/scan/library/{library_id}/progress")
async def clear_progress_endpoint(library_id: int, request: Request):
    """
    Clear the scan progress for a library.

    Use this after reading the final progress state.
    """
    return await clear_library_scan_progress(library_id, request)


# ============================================================================
# Metadata Management Endpoints
# ============================================================================

@router.post("/clear-metadata")
async def clear_metadata_endpoint(
    clear_request: ClearMetadataRequest,
    request: Request
):
    """
    Clear metadata from comics.

    Can clear scanner info, tags, or all metadata from specific comics or entire library.
    """
    return await clear_metadata(clear_request, request)
