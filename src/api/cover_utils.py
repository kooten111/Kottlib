"""
Cover image utilities for API endpoints

Provides helper functions for resolving cover file paths with hierarchical
storage and format fallbacks (WebP -> JPEG).
"""

import logging
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

from ..database import get_covers_dir
from .error_handling import safe_path_exists

logger = logging.getLogger(__name__)

# library_id -> (name, cached_at). Avoids a DB round-trip per cover request.
_LIBRARY_NAME_CACHE: Dict[int, Tuple[str, float]] = {}
_LIBRARY_NAME_TTL_SECONDS = 300.0


def get_cached_library_name(library_id: int, db) -> Optional[str]:
    """Return library name from a short-lived in-memory cache."""
    cached = _LIBRARY_NAME_CACHE.get(library_id)
    now = time.monotonic()
    if cached and (now - cached[1]) < _LIBRARY_NAME_TTL_SECONDS:
        return cached[0]

    from ..database import get_library_by_id

    with db.get_session() as session:
        library = get_library_by_id(session, library_id)
        if not library:
            return None
        _LIBRARY_NAME_CACHE[library_id] = (library.name, now)
        return library.name


def invalidate_library_name_cache(library_id: Optional[int] = None) -> None:
    """Drop cached library names (all, or one id)."""
    if library_id is None:
        _LIBRARY_NAME_CACHE.clear()
    else:
        _LIBRARY_NAME_CACHE.pop(library_id, None)


def find_cover_file(
    hash_value: str,
    library_name: str,
    try_webp: bool = True,
    prefer_format: Optional[str] = None,
) -> Optional[Tuple[Path, str]]:
    """
    Find cover file for a given hash, trying multiple locations and formats

    Searches in this order (unless prefer_format forces jpeg/webp first):
    1. Hierarchical WebP (covers/ab/abc123.webp) - if try_webp=True
    2. Hierarchical JPEG (covers/ab/abc123.jpg)
    3. Flat WebP (covers/abc123.webp) - if try_webp=True
    4. Flat JPEG (covers/abc123.jpg)

    Args:
        hash_value: Comic hash (e.g., "abc123")
        library_name: Library name for covers directory
        try_webp: Whether to try WebP format (default: True)
        prefer_format: Optional 'webp' or 'jpg' to try that format first

    Returns:
        Tuple of (Path, media_type) if found, None otherwise
        media_type will be either "image/webp" or "image/jpeg"
    """
    # Do not mkdir on the hot path — covers should already exist after scan.
    covers_dir = get_covers_dir(library_name, create=False)
    if not covers_dir.exists():
        return None

    want_webp_first = try_webp
    if prefer_format == "jpg":
        want_webp_first = False
    elif prefer_format == "webp":
        want_webp_first = True

    def _try_hierarchical(ext: str, media_type: str) -> Optional[Tuple[Path, str]]:
        if len(hash_value) < 2:
            return None
        path = covers_dir / hash_value[:2] / f"{hash_value}.{ext}"
        if path.is_file():
            return (path, media_type)
        return None

    def _try_flat(ext: str, media_type: str) -> Optional[Tuple[Path, str]]:
        path = covers_dir / f"{hash_value}.{ext}"
        if path.is_file():
            return (path, media_type)
        return None

    if want_webp_first:
        found = _try_hierarchical("webp", "image/webp")
        if found:
            return found
        found = _try_hierarchical("jpg", "image/jpeg")
        if found:
            return found
        found = _try_flat("webp", "image/webp")
        if found:
            return found
        found = _try_flat("jpg", "image/jpeg")
        if found:
            return found
    else:
        found = _try_hierarchical("jpg", "image/jpeg")
        if found:
            return found
        if try_webp:
            found = _try_hierarchical("webp", "image/webp")
            if found:
                return found
        found = _try_flat("jpg", "image/jpeg")
        if found:
            return found
        if try_webp:
            found = _try_flat("webp", "image/webp")
            if found:
                return found

    logger.debug(f"No cover found for hash: {hash_value}")
    return None


def find_cover_for_comic(
    comic_hash: str,
    library_name: str,
    custom_cover_path: Optional[str] = None
) -> Optional[Tuple[Path, str]]:
    """
    Find cover file for a comic, checking custom cover first

    Args:
        comic_hash: Comic hash for default cover lookup
        library_name: Library name for covers directory
        custom_cover_path: Optional custom cover path to try first

    Returns:
        Tuple of (Path, media_type) if found, None otherwise
    """
    # Try custom cover first if provided
    if custom_cover_path:
        custom_path = Path(custom_cover_path)
        if not custom_path.is_absolute():
            logger.warning(f"Ignoring non-absolute custom cover path: {custom_cover_path}")
        elif safe_path_exists(custom_path, "custom cover"):
            logger.debug(f"Using custom cover: {custom_path}")
            # Determine media type from extension
            ext = custom_path.suffix.lower()
            media_type = "image/webp" if ext == ".webp" else "image/jpeg"
            return (custom_path, media_type)

    # Fall back to hash-based lookup
    return find_cover_file(comic_hash, library_name)
