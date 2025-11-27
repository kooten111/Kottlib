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


def get_comic_sort_key(v: dict) -> tuple:
    """
    Get sort key for a comic volume/chapter.
    Sorts by:
    1. Volume number (volumes before chapters)
    2. Issue/Chapter number
    3. Filename (fallback)

    Args:
        v: Dictionary containing 'volume', 'issue_number', 'title' keys

    Returns:
        Tuple for sorting
    """
    vol = v.get("volume") or 0
    issue = v.get("issue_number") or 0
    title = v.get("title", "").lower()

    # If metadata exists, use it
    if vol > 0:
        # Has volume metadata - it's a volume
        return (0, vol, issue, title)
    elif issue > 0:
        # Has issue metadata but no volume - likely a chapter
        # But check title for volume patterns first (in case metadata is incomplete)
        if re.search(r'\bv(?:ol)?\.?\s*\d+', title) or re.search(r'\bvolume\s+\d+', title):
            # Title suggests it's a volume, extract number
            match = re.search(r'\bv(?:ol)?\.?\s*(\d+)', title) or re.search(r'\bvolume\s+(\d+)', title)
            if match:
                vol_num = int(match.group(1))
                return (0, vol_num, 0, title)
        # It's a chapter
        return (1, issue, 0, title)
    else:
        # No metadata - rely on filename patterns
        # Check for volume patterns: v01, vol01, volume 1, etc.
        if re.search(r'\bv(?:ol)?\.?\s*\d+', title) or re.search(r'\bvolume\s+\d+', title):
            match = re.search(r'\bv(?:ol)?\.?\s*(\d+)', title) or re.search(r'\bvolume\s+(\d+)', title)
            if match:
                vol_num = int(match.group(1))
                return (0, vol_num, 0, title)
        # Check for chapter patterns: c001, ch01, chapter 1, #001 etc.
        elif re.search(r'\bc(?:h|hapter)?\.?\s*\d+', title) or re.search(r'\bchapter\s+\d+', title) or re.search(r'#\s*\d+', title):
            match = re.search(r'\bc(?:h|hapter)?\.?\s*(\d+)', title) or re.search(r'\bchapter\s+(\d+)', title) or re.search(r'#\s*(\d+)', title)
            if match:
                ch_num = int(match.group(1))
                return (1, ch_num, 0, title)
        # Fallback: sort by title
        return (2, 0, 0, title)
