"""
Kottlib Utilities

Shared utility functions and classes used across the codebase.
"""

# Re-export series utilities
from .series_utils import get_series_name_from_comic

__all__ = [
    'get_series_name_from_comic',
]
