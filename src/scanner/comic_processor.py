"""
Comic processing for the scanner.

Provides functions for processing individual comics and extracting metadata.
"""

import logging
from pathlib import Path
from threading import Lock
from typing import Optional, Dict, Any

from src.database import (
    Database,
    create_comic,
    get_comic_by_hash,
    get_comic_by_path_and_mtime,
    get_covers_dir,
)

from .comic_loader import open_comic
from .thumbnail_generator import (
    calculate_yacreader_hash,
    generate_dual_thumbnails,
    thumbnail_exists,
)


logger = logging.getLogger(__name__)


def process_single_comic(
    db: Database,
    library_id: int,
    library_name: Optional[str],
    library_path: Path,
    comic_path: Path,
    folder_id: Optional[int],
    structure_cache: Dict[str, str],
    lock: Lock,
    counters: dict
) -> None:
    """
    Process a single comic file.

    Args:
        db: Database instance
        library_id: Library ID
        library_name: Library name for covers directory
        library_path: Library root path
        comic_path: Path to comic file
        folder_id: Parent folder ID (or None)
        structure_cache: Pre-computed structure mode cache
        lock: Thread lock for counters
        counters: Dict with counter keys: 'added', 'skipped', 'unchanged', 'updated', 'thumbnails', 'errors'
    """
    try:
        # Import config lazily to avoid circular imports
        try:
            from src.config import get_config
        except ImportError:
            from config import get_config

        # FAST PATH: Check by path + mtime first (avoids expensive hash calculation)
        # This makes re-scans MUCH faster by skipping unchanged files
        file_mtime = int(comic_path.stat().st_mtime)

        with db.get_session() as session:
            existing = get_comic_by_path_and_mtime(
                session,
                str(comic_path),
                file_mtime,
                library_id=library_id
            )
            if existing:
                # File hasn't changed since last scan
                # BUT check if it moved to a different folder (folder_id changed)
                if existing.folder_id != folder_id:
                    existing.folder_id = folder_id
                    session.commit()
                    with lock:
                        counters['updated'] += 1
                    logger.info(f"Updated folder for unchanged file: {comic_path.name}")
                else:
                    # Truly unchanged
                    with lock:
                        counters['skipped'] += 1
                        counters['unchanged'] += 1
                    logger.debug(f"Skipping unchanged file: {comic_path.name}")
                return

        # SLOW PATH: Calculate hash for new/modified files
        # This catches renamed files and ensures proper deduplication
        file_hash = calculate_yacreader_hash(comic_path)

        # Check if already in database by hash (catches moved/renamed files)
        with db.get_session() as session:
            existing = get_comic_by_hash(session, file_hash, library_id=library_id)
            if existing:
                # Same content, different path/mtime - update the record
                existing.path = str(comic_path)
                existing.filename = comic_path.name
                existing.file_modified_at = file_mtime
                existing.folder_id = folder_id
                session.commit()

                with lock:
                    counters['skipped'] += 1
                    counters['updated'] += 1
                logger.info(f"Updated moved/renamed comic: {comic_path.name}")
                return

        # Open comic to extract metadata
        comic = open_comic(comic_path)
        if comic is None:
            logger.warning(f"Failed to open: {comic_path}")
            with lock:
                counters['errors'] += 1
            return

        with comic:
            # Extract metadata
            metadata = extract_metadata(comic, library_path, structure_cache)

            # Add to database (separate session)
            with db.get_session() as session:
                db_comic = create_comic(
                    session,
                    library_id=library_id,
                    folder_id=folder_id,
                    path=str(comic_path),
                    filename=comic_path.name,
                    file_hash=file_hash,
                    file_size=comic_path.stat().st_size,
                    file_modified_at=int(comic_path.stat().st_mtime),
                    format=comic_path.suffix[1:].lower(),
                    num_pages=comic.page_count,
                    **metadata
                )

            with lock:
                counters['added'] += 1

            # Generate thumbnails
            _generate_thumbnails(comic, file_hash, library_name, lock, counters)

    except Exception as e:
        logger.error(f"Error processing {comic_path}: {e}", exc_info=True)
        with lock:
            counters['errors'] += 1


def extract_metadata(comic, library_path: Optional[Path], structure_cache: Dict[str, str]) -> dict:
    """
    Extract metadata from comic.

    Args:
        comic: Opened comic object
        library_path: Library root path for relative path calculation
        structure_cache: Pre-computed structure mode cache

    Returns:
        Dict of metadata fields
    """
    metadata = {}
    
    # Set title to filename without extension as default
    # This will be overridden if ComicInfo.xml has a title
    if hasattr(comic, 'path'):
        comic_path = Path(comic.path)
        filename_no_ext = comic_path.stem
        metadata['title'] = filename_no_ext

        # --- Hybrid Hierarchy Logic ---
        try:
            if library_path:
                # Get path relative to library root
                rel_path = comic_path.relative_to(library_path)
                
                if len(rel_path.parts) > 0:
                    top_folder = rel_path.parts[0]
                    mode = structure_cache.get(top_folder, "unknown")
                    
                    # Apply logic based on mode
                    if mode == "simple":
                        # Mode 1: Root/Series/Vol.cbz
                        metadata['series'] = top_folder
                        metadata['series_group'] = None
                        
                    elif mode == "nested":
                        # Mode 2: Root/Franchise/Arc/Vol.cbz
                        # OR Root/Franchise/Oneshot.cbz
                        
                        if len(rel_path.parts) == 2:
                            # Directly in franchise folder (Oneshot/Special)
                            # e.g. Batman/Killing Joke.cbz
                            metadata['series'] = top_folder
                            metadata['series_group'] = top_folder  # Group with the franchise
                        elif len(rel_path.parts) > 2:
                            # In subfolder (Arc/Series)
                            # e.g. Batman/Night of Owls/Vol1.cbz
                            # Series is the immediate parent folder
                            metadata['series'] = rel_path.parts[1]
                            metadata['series_group'] = top_folder
                            
                    elif mode == "unpacked":
                        # Mode 3: Root/Series/Vol/Chap/Img.jpg
                        # Series is the top folder
                        metadata['series'] = top_folder
                        metadata['series_group'] = None
                        
                    else:
                        # Fallback for unknown structure
                        # Use parent folder name as series
                        if comic_path.parent != library_path:
                            metadata['series'] = comic_path.parent.name
                        
        except Exception as e:
            logger.warning(f"Error determining series from structure: {e}")

    if comic.comic_info:
        info = comic.comic_info

        # Basic metadata
        if info.title:
            metadata['title'] = info.title
        
        # Check if we should ignore series metadata
        ignore_series_metadata = True
        try:
            from src.config import get_config
            ignore_series_metadata = get_config().features.ignore_series_metadata
        except Exception:
            pass

        if info.series and not ignore_series_metadata:
            metadata['series'] = info.series
        if info.number:
            try:
                metadata['issue_number'] = float(info.number)
            except ValueError:
                pass
        if info.count:
            metadata['count'] = info.count
        if info.volume:
            metadata['volume'] = info.volume
        if info.year:
            metadata['year'] = info.year
        if info.summary:
            metadata['description'] = info.summary
        if info.notes:
            metadata['notes'] = info.notes

        # Build date field from year/month/day
        if info.year:
            if info.month and info.day:
                metadata['date'] = f"{info.year:04d}-{info.month:02d}-{info.day:02d}"
            elif info.month:
                metadata['date'] = f"{info.year:04d}-{info.month:02d}"

        # Creator metadata
        if info.writer:
            metadata['writer'] = info.writer
        if info.penciller:
            metadata['penciller'] = info.penciller
        if info.inker:
            metadata['inker'] = info.inker
        if info.colorist:
            metadata['colorist'] = info.colorist
        if info.letterer:
            metadata['letterer'] = info.letterer
        if info.cover_artist:
            metadata['cover_artist'] = info.cover_artist
        if info.editor:
            metadata['editor'] = info.editor

        # Publishing information
        if info.publisher:
            metadata['publisher'] = info.publisher
        if info.genre:
            # Validate genre before setting - filter out nonsensical values
            genre_lower = info.genre.lower()
            # Blacklist of invalid genre terms (building names, library types, random text)
            invalid_genres = [
                'mitsuwa building',  # Building names
                'building',
                'comic',  # Too generic
                'manga',  # Library type
            ]
            
            # Only set genre if it's not in the blacklist
            is_valid = not any(invalid in genre_lower for invalid in invalid_genres)
            if is_valid and len(info.genre.strip()) > 0:
                metadata['genre'] = info.genre
            elif not is_valid:
                logger.debug(f"Filtered out invalid genre: {info.genre}")
        if info.language_iso:
            metadata['language_iso'] = info.language_iso
        if info.age_rating:
            metadata['age_rating'] = info.age_rating
        if info.imprint:
            metadata['imprint'] = info.imprint
        if info.format:
            metadata['format_type'] = info.format

        # Story arc information
        if info.story_arc:
            metadata['story_arc'] = info.story_arc
        if info.story_arc_number:
            metadata['arc_number'] = info.story_arc_number
        if info.series_group:
            metadata['series_group'] = info.series_group

        # Alternate series (for cross-overs)
        if info.alternate_series:
            metadata['alternate_series'] = info.alternate_series
        if info.alternate_number:
            metadata['alternate_number'] = info.alternate_number
        if info.alternate_count:
            metadata['alternate_count'] = info.alternate_count

        # Ratings
        if info.community_rating is not None:
            metadata['rating'] = info.community_rating

        # Characters, teams, locations
        if info.characters:
            metadata['characters'] = info.characters
        if info.teams:
            metadata['teams'] = info.teams
        if info.locations:
            metadata['locations'] = info.locations

        # Reading direction and color
        if info.manga is not None:
            metadata['reading_direction'] = 'rtl' if info.manga else 'ltr'
        if info.black_and_white is not None:
            metadata['is_color'] = not info.black_and_white

        # Page count from ComicInfo.xml (if available)
        if info.page_count:
            # Note: We still calculate num_pages from actual files,
            # but this could be used for validation
            pass

    # Serialize flexible metadata to JSON
    # We store everything in metadata_json to preserve it, even if mapped to columns
    # This allows for future schema changes without losing data
    try:
        import json
        # Filter out large fields or binary data if any
        json_safe_metadata = {k: v for k, v in metadata.items() if isinstance(v, (str, int, float, bool, list, dict, type(None)))}
        metadata['metadata_json'] = json.dumps(json_safe_metadata)
    except Exception as e:
        logger.warning(f"Failed to serialize metadata to JSON: {e}")

    return metadata


def _generate_thumbnails(comic, file_hash: str, library_name: Optional[str], lock: Lock, counters: dict) -> None:
    """
    Generate thumbnails for comic.

    Args:
        comic: Opened comic object
        file_hash: File hash
        library_name: Library name for covers directory
        lock: Thread lock for counters
        counters: Dict with counter keys including 'thumbnails'
    """
    try:
        # Get library-specific covers directory
        covers_dir = get_covers_dir(library_name)

        # Check if thumbnails already exist
        if thumbnail_exists(covers_dir, file_hash, 'JPEG'):
            return

        # Extract cover image
        cover_image = comic.extract_page_as_image(0)
        if not cover_image:
            logger.warning(f"Failed to extract cover for hash {file_hash}")
            return

        # Generate thumbnails
        jpeg_ok, webp_ok = generate_dual_thumbnails(
            cover_image,
            covers_dir,
            file_hash
        )

        if jpeg_ok and webp_ok:
            with lock:
                counters['thumbnails'] += 1
        elif not jpeg_ok:
            logger.warning(f"Failed to generate JPEG thumbnail for {file_hash}")

    except Exception as e:
        logger.error(f"Error generating thumbnails for {file_hash}: {e}")
