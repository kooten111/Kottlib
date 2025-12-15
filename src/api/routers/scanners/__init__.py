"""
Scanner API Router Package.

This package provides the scanner API endpoints, split into focused modules:
- models.py: Pydantic models for request/response
- progress.py: Progress tracking for library scans
- manager.py: Scanner manager singleton
- router.py: Main router with endpoint registrations
- endpoints/: Individual endpoint handlers
- tasks/: Background task functions

Usage:
    from src.api.routers.scanners import router
"""

from .router import router
from .models import (
    ScanLevelEnum,
    ConfidenceLevelEnum,
    ScanResultModel,
    ScannerInfo,
    LibraryScannerConfig,
    UpdateLibraryScannerConfig,
    ScanRequest,
    BulkScanRequest,
    BulkScanResult,
    ScanComicRequest,
    ScanLibraryRequest,
    ClearMetadataRequest,
    ScanComicResponse,
    ScanLibraryResponse,
)
from .progress import (
    start_scan_progress,
    update_scan_progress,
    get_scan_progress,
    clear_scan_progress,
)
from .manager import get_scanner_manager

__all__ = [
    # Router
    "router",
    # Models
    "ScanLevelEnum",
    "ConfidenceLevelEnum",
    "ScanResultModel",
    "ScannerInfo",
    "LibraryScannerConfig",
    "UpdateLibraryScannerConfig",
    "ScanRequest",
    "BulkScanRequest",
    "BulkScanResult",
    "ScanComicRequest",
    "ScanLibraryRequest",
    "ClearMetadataRequest",
    "ScanComicResponse",
    "ScanLibraryResponse",
    # Progress
    "start_scan_progress",
    "update_scan_progress",
    "get_scan_progress",
    "clear_scan_progress",
    # Manager
    "get_scanner_manager",
]
