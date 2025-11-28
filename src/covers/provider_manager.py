"""
Cover Provider Manager

Central registry and manager for all cover providers.
Similar to the scanner_manager.py pattern used in src/scanners/scanner_manager.py.
"""

import logging
from typing import Dict, List, Optional, Type

from .base_provider import BaseCoverProvider, CoverOption, CoverProviderError

logger = logging.getLogger(__name__)


class CoverProviderManager:
    """
    Manages cover providers for fetching covers from external sources.

    Example usage:
        >>> manager = CoverProviderManager()
        >>> manager.register_provider(MangaDexCoverProvider())
        >>> providers = manager.get_available_providers()
        >>> covers = manager.search_all("One Piece")
    """

    def __init__(self):
        # Registered provider instances (name -> instance)
        self._providers: Dict[str, BaseCoverProvider] = {}

    def register_provider(self, provider: BaseCoverProvider):
        """
        Register a cover provider.

        Args:
            provider: Provider instance to register
        """
        name = provider.source_name
        self._providers[name] = provider
        logger.debug(f"Registered cover provider: {name}")

    def unregister_provider(self, name: str):
        """
        Unregister a cover provider.

        Args:
            name: Provider name to unregister
        """
        if name in self._providers:
            del self._providers[name]
            logger.debug(f"Unregistered cover provider: {name}")

    def get_provider(self, name: str) -> Optional[BaseCoverProvider]:
        """
        Get a provider by name.

        Args:
            name: Provider name

        Returns:
            Provider instance or None if not found
        """
        return self._providers.get(name)

    def get_available_providers(self) -> List[str]:
        """
        Get list of available provider names.

        Returns:
            List of registered provider names
        """
        return list(self._providers.keys())

    def search(
        self, provider_name: str, query: str, **kwargs
    ) -> List[CoverOption]:
        """
        Search for covers using a specific provider.

        Args:
            provider_name: Name of the provider to use
            query: Search query
            **kwargs: Additional provider-specific parameters

        Returns:
            List of CoverOption objects

        Raises:
            ValueError: If provider not found
            CoverProviderError: If search fails
        """
        provider = self.get_provider(provider_name)
        if not provider:
            raise ValueError(f"Unknown cover provider: {provider_name}")

        return provider.search_covers(query, **kwargs)

    def search_all(self, query: str, **kwargs) -> Dict[str, List[CoverOption]]:
        """
        Search all registered providers for covers.

        Args:
            query: Search query
            **kwargs: Additional parameters passed to all providers

        Returns:
            Dict mapping provider name to list of CoverOption objects
        """
        results: Dict[str, List[CoverOption]] = {}

        for name, provider in self._providers.items():
            try:
                covers = provider.search_covers(query, **kwargs)
                results[name] = covers
                logger.debug(f"Provider {name} returned {len(covers)} covers")
            except CoverProviderError as e:
                logger.warning(f"Provider {name} search failed: {e}")
                results[name] = []
            except Exception as e:
                logger.error(f"Unexpected error from provider {name}: {e}")
                results[name] = []

        return results

    def download_cover(self, provider_name: str, cover_id: str) -> bytes:
        """
        Download a cover from a specific provider.

        Args:
            provider_name: Name of the provider
            cover_id: Cover ID (from CoverOption.id)

        Returns:
            Raw image data as bytes

        Raises:
            ValueError: If provider not found
            CoverProviderError: If download fails
        """
        provider = self.get_provider(provider_name)
        if not provider:
            raise ValueError(f"Unknown cover provider: {provider_name}")

        return provider.download_cover(cover_id)


# Global singleton instance
_default_manager: Optional[CoverProviderManager] = None


def get_cover_provider_manager() -> CoverProviderManager:
    """Get the global cover provider manager instance."""
    global _default_manager
    if _default_manager is None:
        _default_manager = CoverProviderManager()
        _init_default_providers()
    return _default_manager


def _init_default_providers():
    """Initialize default cover providers."""
    global _default_manager
    if _default_manager is None:
        return

    # Auto-discover and register providers
    try:
        from .providers.mangadex import MangaDexCoverProvider

        _default_manager.register_provider(MangaDexCoverProvider())
        logger.info("Registered MangaDex cover provider")
    except ImportError as e:
        logger.debug(f"MangaDex provider not available: {e}")
    except Exception as e:
        logger.warning(f"Failed to register MangaDex provider: {e}")
