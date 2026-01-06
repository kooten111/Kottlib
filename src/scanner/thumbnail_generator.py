"""
Thumbnail Generator

Generates dual-format thumbnails for comic covers:
- JPEG (300px) for mobile app compatibility
- WebP (400px) for web UI (better quality, smaller size)

Stores thumbnails in covers/ directory.
"""

import hashlib
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
from io import BytesIO
import logging

from src.utils.hashing import calculate_comic_hash

logger = logging.getLogger(__name__)


# Thumbnail settings
JPEG_SIZE = (300, 450)  # Width x Height for mobile
WEBP_SIZE = (400, 600)  # Width x Height for web
JPEG_QUALITY = 85
WEBP_QUALITY = 90


def resize_image_to_fit(
    image: Image.Image,
    max_size: Tuple[int, int],
    maintain_aspect: bool = True
) -> Image.Image:
    """
    Resize image to fit within max_size while maintaining aspect ratio

    Args:
        image: PIL Image to resize
        max_size: (width, height) maximum dimensions
        maintain_aspect: If True, maintain aspect ratio

    Returns:
        Resized PIL Image
    """
    if maintain_aspect:
        # Calculate scaling to fit within bounds
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        return image
    else:
        # Stretch to exact size (not recommended for covers)
        return image.resize(max_size, Image.Resampling.LANCZOS)


def get_thumbnail_path(
    covers_dir: Path,
    file_hash: str,
    format: str = 'JPEG',
    custom: bool = False
) -> Path:
    """
    Get path to thumbnail file using hierarchical storage.

    Uses first 2 characters of hash as subdirectory to avoid having
    thousands of files in a single directory.

    Example: hash "abc123..." -> covers/ab/abc123.jpg

    Args:
        covers_dir: Base covers directory
        file_hash: File hash (MD5 hex string)
        format: 'JPEG' or 'WEBP'
        custom: If True, look in custom_covers subdirectory

    Returns:
        Path to thumbnail
    """
    ext = '.jpg' if format == 'JPEG' else '.webp'

    if custom:
        # Custom covers are in a subdirectory
        subdir = file_hash[:2]
        custom_dir = covers_dir.parent / 'custom_covers' / subdir
        custom_dir.mkdir(parents=True, exist_ok=True)
        return custom_dir / f"{file_hash}{ext}"
    else:
        # Use first 2 characters of hash as subdirectory
        # This creates 256 possible subdirectories (00-ff)
        subdir = file_hash[:2]
        hash_dir = covers_dir / subdir
        hash_dir.mkdir(parents=True, exist_ok=True)
        return hash_dir / f"{file_hash}{ext}"


def generate_thumbnail_from_image(
    image: Image.Image,
    output_path: Path,
    format: str = 'JPEG',
    size: Tuple[int, int] = JPEG_SIZE,
    quality: int = JPEG_QUALITY
) -> bool:
    """
    Generate thumbnail from PIL Image

    Args:
        image: Source image
        output_path: Where to save the thumbnail
        format: 'JPEG' or 'WEBP'
        size: Target size (width, height)
        quality: Compression quality (1-100)

    Returns:
        True if successful
    """
    try:
        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert RGBA to RGB for JPEG
        if format == 'JPEG' and image.mode in ('RGBA', 'LA', 'P'):
            # Create white background
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
            image = background

        # Resize image
        thumb = image.copy()
        thumb = resize_image_to_fit(thumb, size)

        # Save thumbnail
        if format == 'JPEG':
            thumb.save(output_path, 'JPEG', quality=quality, optimize=True)
        elif format == 'WEBP':
            thumb.save(output_path, 'WEBP', quality=quality, method=6)
        else:
            logger.error(f"Unsupported format: {format}")
            return False

        logger.debug(f"Generated {format} thumbnail: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to generate thumbnail: {e}")
        return False


def generate_thumbnail_from_bytes(
    image_data: bytes,
    output_path: Path,
    format: str = 'JPEG',
    size: Tuple[int, int] = JPEG_SIZE,
    quality: int = JPEG_QUALITY
) -> bool:
    """
    Generate thumbnail from image bytes

    Args:
        image_data: Image data as bytes
        output_path: Where to save the thumbnail
        format: 'JPEG' or 'WEBP'
        size: Target size
        quality: Compression quality

    Returns:
        True if successful
    """
    try:
        image = Image.open(BytesIO(image_data))
        return generate_thumbnail_from_image(image, output_path, format, size, quality)
    except Exception as e:
        logger.error(f"Failed to open image data: {e}")
        return False


def generate_dual_thumbnails(
    cover_image: Image.Image,
    covers_dir: Path,
    file_hash: str
) -> Tuple[bool, bool]:
    """
    Generate both JPEG and WebP thumbnails using hierarchical storage

    Args:
        cover_image: PIL Image of the cover
        covers_dir: Directory where covers are stored
        file_hash: MD5 hash of the comic file (used as filename)

    Returns:
        (jpeg_success, webp_success) tuple of booleans
    """
    # Use get_thumbnail_path for hierarchical storage
    jpeg_path = get_thumbnail_path(covers_dir, file_hash, 'JPEG')
    webp_path = get_thumbnail_path(covers_dir, file_hash, 'WEBP')

    jpeg_ok = generate_thumbnail_from_image(
        cover_image,
        jpeg_path,
        format='JPEG',
        size=JPEG_SIZE,
        quality=JPEG_QUALITY
    )

    webp_ok = generate_thumbnail_from_image(
        cover_image,
        webp_path,
        format='WEBP',
        size=WEBP_SIZE,
        quality=WEBP_QUALITY
    )

    return jpeg_ok, webp_ok


def generate_custom_cover(
    page_image: Image.Image,
    custom_covers_dir: Path,
    file_hash: str,
    page_index: int
) -> Tuple[bool, bool]:
    """
    Generate custom cover from a specific page

    Args:
        page_image: PIL Image of the page to use as cover
        custom_covers_dir: Directory for custom covers
        file_hash: MD5 hash of the comic file
        page_index: Index of the page being used

    Returns:
        (jpeg_success, webp_success) tuple
    """
    # Custom covers use the same naming but in a different directory
    return generate_dual_thumbnails(page_image, custom_covers_dir, file_hash)


def thumbnail_exists(covers_dir: Path, file_hash: str, format: str = 'JPEG') -> bool:
    """
    Check if thumbnail already exists

    Args:
        covers_dir: Covers directory
        file_hash: File hash
        format: 'JPEG' or 'WEBP'

    Returns:
        True if thumbnail exists
    """
    # Use get_thumbnail_path to get the correct hierarchical path
    thumb_path = get_thumbnail_path(covers_dir, file_hash, format)
    return thumb_path.exists()


def get_thumbnail_size_info(thumb_path: Path) -> Optional[dict]:
    """
    Get information about a thumbnail

    Args:
        thumb_path: Path to thumbnail file

    Returns:
        Dict with size info or None
    """
    if not thumb_path.exists():
        return None

    try:
        with Image.open(thumb_path) as img:
            return {
                'width': img.width,
                'height': img.height,
                'format': img.format,
                'mode': img.mode,
                'file_size': thumb_path.stat().st_size,
            }
    except Exception as e:
        logger.error(f"Failed to get thumbnail info: {e}")
        return None


def clean_orphaned_thumbnails(
    covers_dir: Path,
    valid_hashes: set
) -> int:
    """
    Remove thumbnails for comics that no longer exist

    Args:
        covers_dir: Covers directory
        valid_hashes: Set of file hashes that should exist

    Returns:
        Number of thumbnails removed
    """
    removed = 0

    for thumb_file in covers_dir.glob('*'):
        if thumb_file.is_file():
            # Get hash from filename (remove extension)
            file_hash = thumb_file.stem

            if file_hash not in valid_hashes:
                try:
                    thumb_file.unlink()
                    removed += 1
                    logger.debug(f"Removed orphaned thumbnail: {thumb_file.name}")
                except Exception as e:
                    logger.error(f"Failed to remove {thumb_file}: {e}")

    return removed
