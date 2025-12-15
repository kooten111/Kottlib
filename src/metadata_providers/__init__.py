"""
YACLib Metadata Providers (formerly Scanners)

Pluggable metadata provider system for extracting metadata from different sources.

This module has been renamed from 'scanners' to 'metadata_providers' for clarity.
Backward compatibility imports are maintained.
"""

from .base import (
    BaseScanner,
    ScanResult,
    ScanLevel,
    MatchConfidence,
    ScannerError,
    ScannerConfigError,
    ScannerAPIError,
    ScannerRateLimitError
)

from .manager import (
    ScannerManager,
    ScannerConfig,
    FallbackStrategy,
    get_manager,
    init_default_scanners,
    discover_scanners
)

from .config import (
    ConfigOption,
    ConfigType
)

from .schema import (
    get_scanner_capabilities,
    MetadataField
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
    
    # Config
    'ConfigOption',
    'ConfigType',
    
    # Schema
    'get_scanner_capabilities',
    'MetadataField',
]

__version__ = '2.0.0'
