"""
Scanner API endpoints.

This package contains endpoint handlers for the scanner router,
organized by functionality.
"""

from .available import get_available_scanners, get_library_scanner_configs
from .configure import configure_library_scanner, verify_scanner_credentials
from .scan_single import scan_single, scan_bulk, scan_and_save_series, apply_series_metadata, test_scanner
from .scan_comic import scan_comic
from .scan_library import scan_library, get_library_scan_progress, clear_library_scan_progress
from .metadata import clear_metadata

__all__ = [
    # Available scanners
    "get_available_scanners",
    "get_library_scanner_configs",
    # Configuration
    "configure_library_scanner",
    "verify_scanner_credentials",
    # Single scans
    "scan_single",
    "scan_bulk",
    "scan_and_save_series",
    "apply_series_metadata",
    "test_scanner",
    # Comic scanning
    "scan_comic",
    # Library scanning
    "scan_library",
    "get_library_scan_progress",
    "clear_library_scan_progress",
    # Metadata
    "clear_metadata",
]
