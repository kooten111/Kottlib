"""
Cover image utilities for API endpoints

Provides helper functions for resolving cover file paths with hierarchical
storage and format fallbacks (WebP -> JPEG).
"""

import logging
from pathlib import Path
from typing import Optional, Tuple

from ..database import get_covers_dir
from .error_handling import safe_path_exists

logger = logging.getLogger(__name__)


def find_cover_file(
    hash_value: str,
    library_name: str,
    try_webp: bool = True
) -> Optional[Tuple[Path, str]]:
    """
    Find cover file for a given hash, trying multiple locations and formats

    Searches in this order:
    1. Hierarchical WebP (covers/ab/abc123.webp) - if try_webp=True
    2. Hierarchical JPEG (covers/ab/abc123.jpg)
    3. Flat WebP (covers/abc123.webp) - if try_webp=True
    4. Flat JPEG (covers/abc123.jpg)

    Args:
        hash_value: Comic hash (e.g., "abc123")
        library_name: Library name for covers directory
        try_webp: Whether to try WebP format (default: True)

    Returns:
        Tuple of (Path, media_type) if found, None otherwise
        media_type will be either "image/webp" or "image/jpeg"

    Example:
        >>> cover_path, media_type = find_cover_file("abc123", "My Library")
        >>> if cover_path:
        ...     return FileResponse(cover_path, media_type=media_type)
    """
    covers_dir = get_covers_dir(library_name)

    # Try hierarchical path first (covers/ab/abc123.*)
    if len(hash_value) >= 2:
        subdir = hash_value[:2]

        # Try hierarchical WebP
        if try_webp:
            webp_path = covers_dir / subdir / f"{hash_value}.webp"
            if safe_path_exists(webp_path, "hierarchical WebP cover"):
                logger.debug(f"Found hierarchical WebP cover: {webp_path}")
                return (webp_path, "image/webp")

        # Try hierarchical JPEG
        jpeg_path = covers_dir / subdir / f"{hash_value}.jpg"
        if safe_path_exists(jpeg_path, "hierarchical JPEG cover"):
            logger.debug(f"Found hierarchical JPEG cover: {jpeg_path}")
            return (jpeg_path, "image/jpeg")

    # Try flat path as fallback (covers/abc123.*)
    if try_webp:
        webp_path = covers_dir / f"{hash_value}.webp"
        if safe_path_exists(webp_path, "flat WebP cover"):
            logger.debug(f"Found flat WebP cover: {webp_path}")
            return (webp_path, "image/webp")

    # Try flat JPEG
    jpeg_path = covers_dir / f"{hash_value}.jpg"
    if safe_path_exists(jpeg_path, "flat JPEG cover"):
        logger.debug(f"Found flat JPEG cover: {jpeg_path}")
        return (jpeg_path, "image/jpeg")

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

    Example:
        >>> cover = get_best_cover(session, comic_id)
        >>> result = find_cover_for_comic(
        ...     comic.hash,
        ...     library.name,
        ...     cover.jpeg_path if cover else None
        ... )
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
