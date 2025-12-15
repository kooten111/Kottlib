"""
Scanner manager singleton.

Provides access to the scanner manager instance for API endpoints.
"""

from typing import Optional
import logging

from src.metadata_providers import (
    init_default_scanners,
    ScannerManager,
)


logger = logging.getLogger(__name__)

# Scanner manager singleton
_scanner_manager: Optional[ScannerManager] = None


def get_scanner_manager() -> ScannerManager:
    """Get or initialize the scanner manager."""
    global _scanner_manager
    if _scanner_manager is None:
        _scanner_manager = init_default_scanners()
    return _scanner_manager
