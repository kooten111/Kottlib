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
    init_default_scanners
)

# Import available scanners
from .nhentai.nhentai_scanner import NhentaiScanner
from .AniList.anilist_scanner import AniListScanner

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

    # Scanners
    'NhentaiScanner',
    'AniListScanner',
]

__version__ = '1.0.0'
