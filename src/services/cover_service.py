"""
Cover Service

Cover generation and retrieval operations including:
- Getting covers for comics
- Fetching external covers from providers
- Setting custom covers
"""

import logging
from typing import Optional, List, Dict, Any
from io import BytesIO
from sqlalchemy.orm import Session
from PIL import Image

from ..database import (
    get_comic_by_id,
    get_covers_dir,
    create_cover,
)
from ..covers import (
    get_cover_provider_manager,
    CoverOption,
    CoverProviderError,
    CoverProviderRateLimitError,
)
from ..scanner.thumbnail_generator import (
    generate_dual_thumbnails,
    get_thumbnail_path,
    thumbnail_exists,
)
from ..scanner.comic_loader import open_comic
from ..database.models import Cover
from pathlib import Path

logger = logging.getLogger(__name__)


def get_cover_for_comic(
    session: Session,
    comic_id: int
) -> Optional[str]:
    """
    Get the best cover path for a comic.
    
    Returns the path to the comic's cover image, preferring:
    1. Custom cover
    2. External cover
    3. Generated thumbnail
    
    Args:
        session: Database session
        comic_id: Comic ID
        
    Returns:
        Path to cover image, or None if no cover available
    """
    comic = get_comic_by_id(session, comic_id)
    if not comic:
        return None
        
    # Check for custom or external cover first
    if comic.cover_path:
        return comic.cover_path
        
    # Fall back to generated thumbnail
    thumbnail_path = get_thumbnail_path(comic.path)
    return thumbnail_path if thumbnail_path else None


def fetch_external_covers(
    session: Session,
    comic_id: int,
    provider_name: Optional[str] = None,
    query: Optional[str] = None
) -> Dict[str, List[CoverOption]]:
    """
    Fetch covers from external providers for a comic.
    
    Args:
        session: Database session
        comic_id: Comic ID
        provider_name: Optional specific provider to use (e.g., 'mangadex')
        query: Optional search query (defaults to comic series name)
        
    Returns:
        Dictionary mapping provider names to lists of cover options
        
    Raises:
        ValueError: If comic not found
        CoverProviderError: If provider API fails
        CoverProviderRateLimitError: If rate limited
    """
    comic = get_comic_by_id(session, comic_id)
    if not comic:
        raise ValueError(f"Comic {comic_id} not found")
        
    # Determine search query
    search_query = query or comic.series or comic.filename
    
    logger.info(f"Fetching covers for comic {comic_id} using query '{search_query}'")
    
    # Get cover provider manager
    manager = get_cover_provider_manager()
    
    # Fetch from specific provider or all providers
    if provider_name:
        provider = manager.get_provider(provider_name)
        if not provider:
            raise ValueError(f"Provider {provider_name} not available")
            
        covers = provider.search_covers(search_query)
        return {provider_name: covers}
    else:
        # Fetch from all providers
        all_covers = {}
        for name in manager.get_available_providers():
            try:
                provider = manager.get_provider(name)
                covers = provider.search_covers(search_query)
                all_covers[name] = covers
            except Exception as e:
                logger.warning(f"Failed to fetch covers from {name}: {e}")
                all_covers[name] = []
                
        return all_covers


def fetch_and_set_cover(
    session: Session,
    comic_id: int,
    provider_name: str,
    cover_id: str
) -> Dict[str, Any]:
    """
    Fetch a cover from a provider and set it for a comic.
    
    Args:
        session: Database session
        comic_id: Comic ID
        provider_name: Provider name (e.g., 'mangadex')
        cover_id: Provider-specific cover ID
        
    Returns:
        Dictionary with:
        - success: Boolean
        - message: Status message
        - cover_type: Type of cover set
        
    Raises:
        ValueError: If comic not found or provider not available
        CoverProviderError: If provider API fails
    """
    comic = get_comic_by_id(session, comic_id)
    if not comic:
        raise ValueError(f"Comic {comic_id} not found")
        
    # Get cover provider
    manager = get_cover_provider_manager()
    provider = manager.get_provider(provider_name)
    if not provider:
        raise ValueError(f"Provider {provider_name} not available")
        
    logger.info(f"Fetching cover {cover_id} from {provider_name} for comic {comic_id}")
    
    # Download cover
    try:
        cover_data = provider.download_cover(cover_id)
    except Exception as e:
        logger.error(f"Failed to download cover: {e}")
        raise CoverProviderError(f"Failed to download cover: {e}")
        
    # Validate it's an image
    try:
        img = Image.open(BytesIO(cover_data))
        img.verify()
    except Exception as e:
        logger.error(f"Invalid image data: {e}")
        raise ValueError(f"Invalid image data: {e}")
        
    # Get library name for cover directory
    if not comic.library:
        raise ValueError(f"Comic {comic_id} has no associated library")
    library_name = comic.library.name
    
    # Save cover to database and generate thumbnails
    covers_dir = get_covers_dir(library_name)
    
    # Create cover record
    cover = create_cover(
        session,
        comic_id=comic_id,
        cover_type='external',
        source=provider_name,
        source_id=cover_id
    )
    
    # Generate thumbnails from cover data
    img = Image.open(BytesIO(cover_data))
    generate_dual_thumbnails(covers_dir, comic.path, image=img)
    
    # Update comic cover path
    comic.cover_path = str(covers_dir / f"{comic.hash}.jpg")
    session.commit()
    
    logger.info(f"Successfully set cover for comic {comic_id} from {provider_name}")
    
    return {
        "success": True,
        "message": "Cover set successfully",
        "cover_type": "external",
    }


def regenerate_cover_for_comic(
    session: Session,
    comic,
    library_name: str,
    force: bool = False
) -> Dict[str, Any]:
    """
    Regenerate cover for a single comic.
    
    This is the centralized function for cover regeneration used by
    the regenerate_covers.py CLI script.
    
    Args:
        session: Database session
        comic: Comic model instance (must have id, path, hash attributes)
        library_name: Name of the library for cover directory
        force: If True, regenerate even if cover already exists
        
    Returns:
        Dict with:
        - status: 'success', 'skipped', 'failed', or 'error'
        - comic_id: ID of the comic
        - filename: Filename of the comic
        - error: Error message if status is 'failed' or 'error'
    """
    try:
        # Get covers directory
        covers_dir = get_covers_dir(library_name)
        
        # Check if cover already exists (unless force)
        if not force and thumbnail_exists(covers_dir, comic.hash, 'JPEG'):
            return {
                'status': 'skipped',
                'comic_id': comic.id,
                'filename': comic.filename
            }

        # Open the comic file and extract cover image
        comic_obj = open_comic(Path(comic.path))
        if comic_obj is None:
            return {
                'status': 'failed',
                'comic_id': comic.id,
                'filename': comic.filename,
                'error': 'Failed to open comic file'
            }
        
        with comic_obj:
            # Extract cover image (first page)
            cover_image = comic_obj.extract_page_as_image(0)
            if not cover_image:
                return {
                    'status': 'failed',
                    'comic_id': comic.id,
                    'filename': comic.filename,
                    'error': 'Failed to extract cover image'
                }
            
            # Generate thumbnails
            jpeg_ok, webp_ok = generate_dual_thumbnails(
                cover_image,
                covers_dir,
                comic.hash
            )
            
            if jpeg_ok:
                return {
                    'status': 'success',
                    'comic_id': comic.id,
                    'filename': comic.filename
                }
            else:
                return {
                    'status': 'failed',
                    'comic_id': comic.id,
                    'filename': comic.filename,
                    'error': 'Thumbnail generation failed'
                }

    except Exception as e:
        return {
            'status': 'error',
            'comic_id': comic.id,
            'filename': comic.filename,
            'error': str(e)
        }
