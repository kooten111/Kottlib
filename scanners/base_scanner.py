"""
Base Scanner Framework for YACLib

Defines the interface that all metadata scanners must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ScanLevel(Enum):
    """What level the scanner operates at"""
    FILE = "file"  # Per-file metadata (e.g., nhentai for doujinshi)
    SERIES = "series"  # Per-series metadata (e.g., Comic Vine, AniList)
    LIBRARY = "library"  # Library-wide metadata


class MatchConfidence(Enum):
    """Confidence level for metadata matches"""
    NONE = 0  # No match found
    LOW = 1  # 0-40% confidence
    MEDIUM = 2  # 40-70% confidence
    HIGH = 3  # 70-90% confidence
    EXACT = 4  # 90-100% confidence


@dataclass
class ScanResult:
    """
    Result from a metadata scan

    Attributes:
        confidence: How confident we are in this match (0.0 to 1.0)
        source_id: ID from the external source (e.g., nhentai ID, AniList ID)
        source_url: URL to the source entry
        metadata: Dictionary of extracted metadata
        tags: List of tags/genres
        raw_response: Optional raw API response for debugging
    """
    confidence: float
    source_id: Optional[str] = None
    source_url: Optional[str] = None
    metadata: Dict = None
    tags: List[str] = None
    raw_response: Optional[Dict] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.tags is None:
            self.tags = []

    @property
    def confidence_level(self) -> MatchConfidence:
        """Get confidence as an enum"""
        if self.confidence == 0:
            return MatchConfidence.NONE
        elif self.confidence < 0.4:
            return MatchConfidence.LOW
        elif self.confidence < 0.7:
            return MatchConfidence.MEDIUM
        elif self.confidence < 0.9:
            return MatchConfidence.HIGH
        else:
            return MatchConfidence.EXACT

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            'confidence': self.confidence,
            'confidence_level': self.confidence_level.name,
            'source_id': self.source_id,
            'source_url': self.source_url,
            'metadata': self.metadata,
            'tags': self.tags
        }


class BaseScanner(ABC):
    """
    Base class for all metadata scanners

    Each scanner should:
    1. Implement the scan() method
    2. Define its scan_level (FILE or SERIES)
    3. Define its source_name (e.g., "nhentai", "Comic Vine")
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize scanner with optional configuration

        Args:
            config: Scanner-specific configuration (API keys, rate limits, etc.)
        """
        self.config = config or {}
        self._validate_config()

    @property
    @abstractmethod
    def source_name(self) -> str:
        """
        Name of the metadata source

        Examples: "nhentai", "Comic Vine", "AniList", "Jikan"
        """
        pass

    @property
    @abstractmethod
    def scan_level(self) -> ScanLevel:
        """
        What level this scanner operates at

        Returns:
            ScanLevel.FILE for per-file scanning (doujinshi)
            ScanLevel.SERIES for series-based scanning (comics, manga)
        """
        pass

    @abstractmethod
    def scan(self, query: str, **kwargs) -> Tuple[Optional[ScanResult], List[ScanResult]]:
        """
        Scan for metadata based on a query

        Args:
            query: Search query (filename for FILE level, series name for SERIES level)
            **kwargs: Additional scanner-specific parameters

        Returns:
            Tuple of (best_match, all_matches)
            - best_match: The best matching result (or None if no good match)
            - all_matches: List of all potential matches for manual selection

        Raises:
            ScannerError: If scanning fails
        """
        pass

    def _validate_config(self):
        """
        Validate scanner configuration

        Override this to check for required API keys, etc.
        """
        pass

    def get_required_config_keys(self) -> List[str]:
        """
        Get list of required configuration keys

        Returns:
            List of required config keys (e.g., ["api_key"])
        """
        return []

    def __str__(self):
        return f"{self.source_name} Scanner ({self.scan_level.value})"

    def __repr__(self):
        return f"<{self.__class__.__name__} source={self.source_name} level={self.scan_level.value}>"


class ScannerError(Exception):
    """Base exception for scanner errors"""
    pass


class ScannerConfigError(ScannerError):
    """Configuration error"""
    pass


class ScannerAPIError(ScannerError):
    """API communication error"""
    pass


class ScannerRateLimitError(ScannerError):
    """Rate limit exceeded"""
    pass
