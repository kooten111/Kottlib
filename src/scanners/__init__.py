"""
YACLib Metadata Scanners

Pluggable scanner system for extracting metadata from different sources.
"""

from .base_scanner import (
    BaseScanner,
    ScanResult,
    ScanLevel,
    MatchConfidence,
    ScannerError,
    ScannerConfigError,
    ScannerAPIError,
    ScannerRateLimitError
)

from .scanner_manager import (
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
