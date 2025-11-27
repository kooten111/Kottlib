"""
Shared utilities and models for API v2 routers
"""

import re
import logging
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# In-memory cache for parsed series trees (cache key: library_id + cache_timestamp)
series_tree_cache = {}


def get_comic_display_name(comic) -> str:
    """
    Get the display name for a comic.

    Returns the comic title if available, otherwise the filename without extension.
    This ensures folders show their actual names and comics show clean filenames.

    Args:
        comic: Comic model instance

    Returns:
        Display name for the comic
    """
    if comic.title:
        return comic.title
    # Strip common comic extensions (.cbz, .cbr, .cb7, .cbt)
    return re.sub(r'\.(cbz|cbr|cb7|cbt)$', '', comic.filename, flags=re.IGNORECASE)


# ============================================================================
# Pydantic Models for v2 API
# ============================================================================

class LibraryInfo(BaseModel):
    """Library information"""
    id: int
    name: str
    path: str


class VersionInfo(BaseModel):
    """Server version information"""
    version: str
    name: str
    api_version: str
