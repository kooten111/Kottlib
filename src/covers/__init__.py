"""
Cover Provider Module

Provides a pluggable cover provider system for fetching covers from external sources.
"""

from .base_provider import (
    BaseCoverProvider,
    CoverOption,
    CoverProviderError,
    CoverProviderConfigError,
    CoverProviderAPIError,
    CoverProviderRateLimitError,
)
from .provider_manager import CoverProviderManager, get_cover_provider_manager

__all__ = [
    "BaseCoverProvider",
    "CoverOption",
    "CoverProviderError",
    "CoverProviderConfigError",
    "CoverProviderAPIError",
    "CoverProviderRateLimitError",
    "CoverProviderManager",
    "get_cover_provider_manager",
]
