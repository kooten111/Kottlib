"""
Base Cover Provider

Defines the interface that all cover providers must implement.
Similar to the scanner architecture pattern used in src/scanners/base_scanner.py.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class CoverOption:
    """
    Represents a cover option returned from a provider search.

    Attributes:
        id: Unique identifier for this cover from the provider
        source: Name of the provider (e.g., 'mangadex', 'anilist')
        thumbnail_url: URL to a small preview of the cover
        full_url: URL to the full-size cover image
        description: Optional description (e.g., 'Volume 1', 'Volume 5')
        width: Optional width of the full image in pixels
        height: Optional height of the full image in pixels
    """

    id: str
    source: str
    thumbnail_url: str
    full_url: str
    description: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "source": self.source,
            "thumbnail_url": self.thumbnail_url,
            "full_url": self.full_url,
            "description": self.description,
            "width": self.width,
            "height": self.height,
        }


class BaseCoverProvider(ABC):
    """
    Base class for all cover providers.

    Each provider should:
    1. Implement the source_name property
    2. Implement the search_covers() method
    3. Implement the download_cover() method

    Example usage:
        >>> provider = MangaDexCoverProvider()
        >>> covers = provider.search_covers("One Piece")
        >>> image_data = provider.download_cover(covers[0].id)
    """

    def __init__(self, config: Optional[dict] = None):
        """
        Initialize provider with optional configuration.

        Args:
            config: Provider-specific configuration (API keys, rate limits, etc.)
        """
        self.config = config or {}
        self._validate_config()

    @property
    @abstractmethod
    def source_name(self) -> str:
        """
        Name of the cover source.

        Examples: 'mangadex', 'anilist', 'metron', 'comicvine'
        """
        pass

    @abstractmethod
    def search_covers(self, query: str, **kwargs) -> List[CoverOption]:
        """
        Search for available covers.

        Args:
            query: Search query (typically series name)
            **kwargs: Additional provider-specific parameters

        Returns:
            List of CoverOption objects representing available covers

        Raises:
            CoverProviderError: If search fails
        """
        pass

    @abstractmethod
    def download_cover(self, cover_id: str) -> bytes:
        """
        Download cover image data.

        Args:
            cover_id: The cover ID (from CoverOption.id)

        Returns:
            Raw image data as bytes

        Raises:
            CoverProviderError: If download fails
        """
        pass

    def _validate_config(self):
        """
        Validate provider configuration.

        Override this to check for required API keys, etc.
        """
        pass

    def get_required_config_keys(self) -> List[str]:
        """
        Get list of required configuration keys.

        Returns:
            List of required config keys (e.g., ['api_key'])
        """
        return []

    def __str__(self):
        return f"{self.source_name} Cover Provider"

    def __repr__(self):
        return f"<{self.__class__.__name__} source={self.source_name}>"


class CoverProviderError(Exception):
    """Base exception for cover provider errors"""

    pass


class CoverProviderConfigError(CoverProviderError):
    """Configuration error"""

    pass


class CoverProviderAPIError(CoverProviderError):
    """API communication error"""

    pass


class CoverProviderRateLimitError(CoverProviderError):
    """Rate limit exceeded"""

    pass
