"""
Kottlib Metadata Scanners (DEPRECATED)

This module has been moved to src.metadata_providers for clarity.
This file provides backward compatibility by re-exporting from the new location.

DEPRECATED: Import from src.metadata_providers instead of src.scanners
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "src.scanners is deprecated. Use src.metadata_providers instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from the new location for backward compatibility
from src.metadata_providers import (
    BaseScanner,
    ScanResult,
    ScanLevel,
    MatchConfidence,
    ScannerError,
    ScannerConfigError,
    ScannerAPIError,
    ScannerRateLimitError,
    ScannerManager,
    ScannerConfig,
    FallbackStrategy,
    get_manager,
    init_default_scanners,
    discover_scanners
)

__all__ = [
    # Base classes
    'BaseScanner',
    'ScanResult',
    'ScanLevel',
    'MatchConfidence',

    # Exceptions
    'ScannerError',
    'ScannerConfigError',
    'ScannerAPIError',
    'ScannerRateLimitError',

    # Manager
    'ScannerManager',
    'ScannerConfig',
    'FallbackStrategy',
    'get_manager',
    'init_default_scanners',
    'discover_scanners',
]

__version__ = '1.0.0'
