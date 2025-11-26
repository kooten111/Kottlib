"""
Threaded Library Scanner

High-performance multi-threaded scanner for large comic libraries.
Significantly faster than single-threaded scanning.
"""

import time
import logging
import warnings
import json
from pathlib import Path
from typing import Tuple, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from dataclasses import dataclass

# Suppress PIL warnings about corrupt EXIF data
warnings.filterwarnings('ignore', message='Corrupt EXIF data')

try:
    # Try relative imports (when used as a package)
    from ..database import (
        Database,
        create_comic,
        get_comic_by_hash,
        get_comic_by_path_and_mtime,
        create_folder,
        get_folder_by_path,
        get_or_create_root_folder,
        get_library_by_id,
        get_covers_dir,
        update_library_series_tree_cache,
    )
    from ..database.models import Folder as FolderModel, Comic
    from .comic_loader import open_comic, is_comic_file
    from .thumbnail_generator import (
        calculate_yacreader_hash,
        generate_dual_thumbnails,
        thumbnail_exists,
    )
except ImportError:
    # Fallback for standalone scripts
    from database import (
        Database,
        create_comic,
        get_comic_by_hash,
        get_comic_by_path_and_mtime,
        create_folder,
        get_folder_by_path,
        get_or_create_root_folder,
        get_library_by_id,
        get_covers_dir,
        update_library_series_tree_cache,
    )
    from database.models import Folder as FolderModel, Comic
    from scanner.comic_loader import open_comic, is_comic_file
    from scanner.thumbnail_generator import (
        calculate_yacreader_hash,
        generate_dual_thumbnails,
        thumbnail_exists,
    )

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """Result from scanning operation"""
    comics_found: int = 0
    comics_added: int = 0
    comics_skipped: int = 0
    comics_skipped_unchanged: int = 0  # Fast path: unchanged files
    comics_updated: int = 0  # Moved/renamed files
    folders_found: int = 0
    thumbnails_generated: int = 0
    errors: int = 0
    duration: float = 0.0


class ThreadedScanner:
    """
    Multi-threaded comic library scanner

    Splits work into two phases:
    1. File discovery (fast, single-threaded)
    2. Comic processing (slow, multi-threaded)

    Uses thread pool for parallel processing of comics.
    """

    def __init__(
        self,
        db: Database,
        library_id: int,
        max_workers: int = 4,
        progress_callback=None
    ):
        """
        Initialize threaded scanner

        Args:
            db: Database instance
            library_id: Library ID to scan into
            max_workers: Number of worker threads (default: 4)
            progress_callback: Optional callback(current, total, message)
        """
        self.db = db
        self.library_id = library_id
        self.max_workers = max_workers
        self.progress_callback = progress_callback

        # Get library name for per-library data directories
        with self.db.get_session() as session:
            library = get_library_by_id(session, library_id)
            self.library_name = library.name if library else None

        # Thread-safe counters
        self._lock = Lock()
        self._comics_processed = 0
        self._comics_added = 0
        self._comics_skipped = 0
        self._comics_skipped_unchanged = 0  # Fast path skips
        self._comics_updated = 0  # Moved/renamed files
        self._thumbnails_generated = 0
        self._errors = 0

        # Track active workers for progress display
        self._active_workers = {}  # worker_id -> (series_name, filename)

    def scan_library(self, library_path: Path) -> ScanResult:
        """
        Scan entire library with multi-threading

        Args:
            library_path: Path to library root

        Returns:
            ScanResult with statistics
        """
        start_time = time.time()
        logger.info(f"Starting threaded scan of {library_path}")

        # Phase 1: Discover all files (fast, single-threaded)
        logger.info("Phase 1: Discovering files...")
        comic_files, folders = self._discover_files(library_path)

        total_comics = len(comic_files)
        logger.info(f"Found {total_comics} comics in {len(folders)} folders")

        if total_comics == 0:
            return ScanResult(
                folders_found=len(folders),
                duration=time.time() - start_time
            )

        # Create folders in database first (including root folder)
        folder_map, root_folder_id = self._create_folders(library_path, folders)

        # Phase 2: Process comics in parallel (slow, multi-threaded)
        logger.info(f"Phase 2: Processing comics with {self.max_workers} workers...")
        self._process_comics_parallel(comic_files, folder_map, root_folder_id, total_comics)

        duration = time.time() - start_time

        result = ScanResult(
            comics_found=total_comics,
            comics_added=self._comics_added,
            comics_skipped=self._comics_skipped,
            comics_skipped_unchanged=self._comics_skipped_unchanged,
            comics_updated=self._comics_updated,
            folders_found=len(folders),
            thumbnails_generated=self._thumbnails_generated,
            errors=self._errors,
            duration=duration
        )

        logger.info(
            f"Scan complete: {result.comics_added} added, "
            f"{result.comics_skipped} skipped ({result.comics_skipped_unchanged} unchanged, "
            f"{result.comics_updated} updated), "
            f"{result.errors} errors in {duration:.2f}s"
        )

        # Rebuild series table from comics (ensures series are up-to-date)
        try:
            self._rebuild_series_table()
        except Exception as e:
            logger.error(f"Failed to rebuild series table: {e}")
            # Don't fail the scan if series rebuild fails

        # Build and cache the series tree for fast loading
        try:
            self._build_series_tree_cache()
        except Exception as e:
            logger.error(f"Failed to build series tree cache: {e}")
            # Don't fail the scan if cache building fails

        return result

    def _discover_files(self, library_path: Path) -> Tuple[List[Tuple[Path, Optional[Path]]], List[Path]]:
        """
        Recursively discover all comic files and folders

        Returns:
            Tuple of (comic_files, folders)
            comic_files: List of (file_path, parent_folder_path) tuples
            folders: List of folder paths
        """
        comic_files = []
        folders = []

        def scan_dir(current_path: Path, parent_folder: Optional[Path] = None):
            """Recursively scan directory"""
            try:
                for item in current_path.iterdir():
                    # Skip hidden files/folders
                    if item.name.startswith('.'):
                        continue

                    if item.is_dir():
                        folders.append(item)
                        # Recurse into subfolder
                        scan_dir(item, parent_folder=item)

                    elif item.is_file() and is_comic_file(item):
                        comic_files.append((item, parent_folder))

            except PermissionError:
                logger.warning(f"Permission denied: {current_path}")
            except Exception as e:
                logger.error(f"Error scanning {current_path}: {e}")

        scan_dir(library_path)
        return comic_files, folders

    def _create_folders(self, library_path: Path, folder_paths: List[Path]) -> Tuple[dict, int]:
        """
        Create all folders in database and return mapping

        YACReader compatibility: Creates a root folder (ID=1) for the library,
        and sets all top-level folders to have parent_id=1.

        Args:
            library_path: Library root path
            folder_paths: List of folder paths to create

        Returns:
            Tuple of (folder_map, root_folder_id)
            - folder_map: Dict mapping folder path to folder ID
            - root_folder_id: ID of the root folder for this library
        """
        folder_map = {}
        root_folder_id = None

        # Sort folders by depth to create parents first
        sorted_folders = sorted(folder_paths, key=lambda p: len(p.parts))

        with self.db.get_session() as session:
            # First, ensure root folder exists (YACReader convention)
            root_folder = get_or_create_root_folder(session, self.library_id, str(library_path))
            root_folder_id = root_folder.id
            logger.debug(f"Root folder ID={root_folder_id} for library {self.library_id}")

            for folder_path in sorted_folders:
                # Get or create folder
                folder = get_folder_by_path(session, self.library_id, str(folder_path))

                if not folder:
                    # Find parent folder ID
                    parent_path = folder_path.parent

                    if parent_path == library_path:
                        # This is a top-level folder - parent is root
                        parent_id = root_folder_id
                    elif str(parent_path) in folder_map:
                        # This is a subfolder - parent is another folder
                        parent_id = folder_map[str(parent_path)]
                    else:
                        # Fallback: parent not found, make it top-level
                        parent_id = root_folder_id

                    folder = create_folder(
                        session,
                        library_id=self.library_id,
                        path=str(folder_path),
                        name=folder_path.name,
                        parent_id=parent_id
                    )

                folder_map[str(folder_path)] = folder.id

        return folder_map, root_folder_id

    def _process_comics_parallel(
        self,
        comic_files: List[Tuple[Path, Optional[Path]]],
        folder_map: dict,
        root_folder_id: int,
        total: int
    ):
        """
        Process comics in parallel using thread pool

        YACReader compatibility: Comics at library root get folder_id set to root_folder_id.

        IMPORTANT: Comics are processed and committed in file order. If the scan is interrupted,
        all processed comics will be fully available (metadata + thumbnails) in the database.

        Args:
            comic_files: List of (comic_path, parent_folder_path) tuples
            folder_map: Mapping of folder paths to folder IDs
            root_folder_id: ID of the root folder (for comics at library root)
            total: Total number of comics (for progress)
        """
        # Use thread pool to process comics in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks and keep them in order
            futures = []
            for comic_path, parent_folder in comic_files:
                if parent_folder:
                    # Comic is in a subfolder
                    folder_id = folder_map.get(str(parent_folder))
                else:
                    # Comic is at library root - use root folder ID (YACReader convention)
                    folder_id = root_folder_id

                future = executor.submit(self._process_single_comic_tracked, comic_path, folder_id)
                futures.append((future, comic_path))

            # Progress monitoring thread
            from threading import Thread, current_thread
            import threading

            def monitor_progress():
                """Update progress display with active workers"""
                while self._comics_processed < total:
                    with self._lock:
                        if self.progress_callback:
                            # Get list of active workers
                            running_comics = list(self._active_workers.values())
                            self.progress_callback(
                                self._comics_processed,
                                total,
                                "Processing...",
                                None,
                                None,
                                running_comics
                            )
                    import time
                    time.sleep(0.3)  # Update every 300ms

            # Start progress monitor thread
            monitor = Thread(target=monitor_progress, daemon=True)
            monitor.start()

            # IMPORTANT: Process completed tasks IN ORDER (not as_completed)
            # This ensures that if the scan is interrupted, all processed comics
            # are fully complete (metadata + thumbnails) in the database
            for i, (future, comic_path) in enumerate(futures, 1):
                try:
                    future.result()  # Wait for this specific comic to complete
                except Exception as e:
                    logger.error(f"Error processing comic {comic_path}: {e}")
                    with self._lock:
                        self._errors += 1

                # Update progress counter
                with self._lock:
                    self._comics_processed += 1

            # Final progress update to clear active workers
            if self.progress_callback:
                self.progress_callback(self._comics_processed, total, "Complete", None, None, [])

    def _process_single_comic_tracked(self, comic_path: Path, folder_id: Optional[int]):
        """
        Wrapper for _process_single_comic that tracks active workers

        Args:
            comic_path: Path to comic file
            folder_id: Parent folder ID (or None)
        """
        from threading import current_thread
        thread_id = current_thread().ident

        # Register this worker as active
        series_name = comic_path.parent.name if comic_path.parent else "Root"
        filename = comic_path.name
        with self._lock:
            self._active_workers[thread_id] = (series_name, filename)

        try:
            # Process the comic
            self._process_single_comic(comic_path, folder_id)
        finally:
            # Unregister this worker
            with self._lock:
                self._active_workers.pop(thread_id, None)

    def _process_single_comic(self, comic_path: Path, folder_id: Optional[int]):
        """
        Process a single comic file

        Args:
            comic_path: Path to comic file
            folder_id: Parent folder ID (or None)
        """
        try:
            # FAST PATH: Check by path + mtime first (avoids expensive hash calculation)
            # This makes re-scans MUCH faster by skipping unchanged files
            file_mtime = int(comic_path.stat().st_mtime)
            
            # DEBUG LOGGING
            if "67% Inertia" in str(comic_path):
                logger.info(f"DEBUG: Checking {comic_path.name}, folder_id arg={folder_id}")

            with self.db.get_session() as session:
                existing = get_comic_by_path_and_mtime(
                    session,
                    str(comic_path),
                    file_mtime,
                    library_id=self.library_id
                )
                if existing:
                    # DEBUG LOGGING
                    if "67% Inertia" in str(comic_path):
                        logger.info(f"DEBUG: Existing found. existing.folder_id={existing.folder_id}, new folder_id={folder_id}")

                    # File hasn't changed since last scan
                    # File hasn't changed since last scan
                    # BUT check if it moved to a different folder (folder_id changed)
                    if existing.folder_id != folder_id:
                        existing.folder_id = folder_id
                        session.commit()
                        with self._lock:
                            self._comics_updated += 1
                        logger.info(f"Updated folder for unchanged file: {comic_path.name}")
                    else:
                        # Truly unchanged
                        with self._lock:
                            self._comics_skipped += 1
                            self._comics_skipped_unchanged += 1
                        logger.debug(f"Skipping unchanged file: {comic_path.name}")
                    return

            # SLOW PATH: Calculate hash for new/modified files
            # This catches renamed files and ensures proper deduplication
            file_hash = calculate_yacreader_hash(comic_path)

            # Check if already in database by hash (catches moved/renamed files)
            with self.db.get_session() as session:
                existing = get_comic_by_hash(session, file_hash, library_id=self.library_id)
                if existing:
                    # Same content, different path/mtime - update the record
                    existing.path = str(comic_path)
                    existing.filename = comic_path.name
                    existing.file_modified_at = file_mtime
                    existing.folder_id = folder_id
                    session.commit()

                    with self._lock:
                        self._comics_skipped += 1
                        self._comics_updated += 1
                    logger.info(f"Updated moved/renamed comic: {comic_path.name}")
                    return

            # Open comic to extract metadata
            comic = open_comic(comic_path)
            if comic is None:
                logger.warning(f"Failed to open: {comic_path}")
                with self._lock:
                    self._errors += 1
                return

            with comic:
                # Extract metadata
                metadata = self._extract_metadata(comic)

                # Add to database (separate session)
                with self.db.get_session() as session:
                    db_comic = create_comic(
                        session,
                        library_id=self.library_id,
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

                with self._lock:
                    self._comics_added += 1

                # Generate thumbnails
                self._generate_thumbnails(comic, file_hash)

        except Exception as e:
            logger.error(f"Error processing {comic_path}: {e}", exc_info=True)
            with self._lock:
                self._errors += 1

    def _extract_metadata(self, comic) -> dict:
        """
        Extract metadata from comic

        Args:
            comic: Opened comic object

        Returns:
            Dict of metadata fields
        """
        metadata = {}
        
        # Set title to filename without extension as default
        # This will be overridden if ComicInfo.xml has a title
        if hasattr(comic, 'path'):
            from pathlib import Path
            filename_no_ext = Path(comic.path).stem
            metadata['title'] = filename_no_ext

        if comic.comic_info:
            info = comic.comic_info

            # Basic metadata
            if info.title:
                metadata['title'] = info.title
            if info.series:
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
                metadata['genre'] = info.genre
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

    def _generate_thumbnails(self, comic, file_hash: str):
        """
        Generate thumbnails for comic

        Args:
            comic: Opened comic object
            file_hash: File hash
        """
        try:
            # Get library-specific covers directory
            covers_dir = get_covers_dir(self.library_name)

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
                with self._lock:
                    self._thumbnails_generated += 1
            elif not jpeg_ok:
                logger.warning(f"Failed to generate JPEG thumbnail for {file_hash}")

        except Exception as e:
            logger.error(f"Error generating thumbnails for {file_hash}: {e}")

    def _rebuild_series_table(self):
        """
        Rebuild the series table from comics

        Groups comics by series and creates/updates series records.
        This ensures the series table is always in sync with the comics.
        """
        logger.info(f"Rebuilding series table for library {self.library_id}...")

        with self.db.get_session() as session:
            from sqlalchemy import func
            from src.database.models import Series as SeriesModel
            import time

            # Get all unique series names with comic counts
            series_data = session.query(
                Comic.series,
                func.count(Comic.id).label('comic_count')
            ).filter(
                Comic.library_id == self.library_id,
                Comic.series.isnot(None)
            ).group_by(
                Comic.series
            ).all()

            if not series_data:
                logger.info("No series found in comics")
                return

            created = 0
            updated = 0
            now = int(time.time())

            for series_name, comic_count in series_data:
                if not series_name:
                    continue

                # Check if series already exists
                existing = session.query(SeriesModel).filter(
                    SeriesModel.library_id == self.library_id,
                    SeriesModel.name == series_name
                ).first()

                if existing:
                    # Update comic count
                    existing.comic_count = comic_count
                    existing.total_issues = comic_count
                    existing.updated_at = now
                    updated += 1
                else:
                    # Create new series
                    new_series = SeriesModel(
                        library_id=self.library_id,
                        name=series_name,
                        display_name=series_name,
                        comic_count=comic_count,
                        total_issues=comic_count,
                        created_at=now,
                        updated_at=now
                    )
                    session.add(new_series)
                    created += 1

            session.commit()
            logger.info(f"Series table rebuilt: {created} created, {updated} updated")

    def _build_series_tree_cache(self):
        """
        Build and cache the series tree structure for this library

        This pre-computes the folder/comic hierarchy to avoid N+1 queries
        on every page load. The cache is stored as JSON in the library record.
        """
        logger.info(f"Building series tree cache for library {self.library_id}...")

        with self.db.get_session() as session:
            # Get all folders and comics in one query each (efficient)
            all_folders = session.query(FolderModel).filter_by(
                library_id=self.library_id
            ).all()

            all_comics = session.query(Comic).filter_by(
                library_id=self.library_id
            ).all()

            # Build lookup maps for efficient access
            folders_by_id = {f.id: f for f in all_folders}
            comics_by_folder = {}
            for comic in all_comics:
                if comic.folder_id not in comics_by_folder:
                    comics_by_folder[comic.folder_id] = []
                comics_by_folder[comic.folder_id].append(comic)

            def build_folder_node(folder, depth=0, max_depth=10):
                """Build tree node for a folder recursively"""
                if depth > max_depth or folder.name == "__ROOT__":
                    return None

                # Get comics in this folder
                comics_in_folder = comics_by_folder.get(folder.id, [])

                # Build comic nodes (no user-specific data like reading progress)
                comic_nodes = []
                for comic in sorted(comics_in_folder, key=lambda c: (c.volume or 0, c.issue_number or 0, c.title or c.filename)):
                    # For single comics, strip file extension from filename
                    display_name = comic.title
                    if not display_name:
                        # Strip common comic extensions (.cbz, .cbr, .cb7, .cbt)
                        import re
                        display_name = re.sub(r'\.(cbz|cbr|cb7|cbt)$', '', comic.filename, flags=re.IGNORECASE)
                    
                    comic_info = {
                        "id": comic.id,
                        "name": display_name,
                        "type": "comic",
                        "libraryId": self.library_id,
                        "folderId": folder.id,
                        "hash": comic.hash,
                        "totalPages": comic.num_pages,
                        "volume": comic.volume,
                        "issueNumber": comic.issue_number
                    }
                    comic_nodes.append(comic_info)

                # Get subfolders
                subfolders = [f for f in all_folders if f.parent_id == folder.id]

                # Build subfolder nodes recursively
                subfolder_nodes = []
                for subfolder in sorted(subfolders, key=lambda f: f.name):
                    subfolder_node = build_folder_node(subfolder, depth + 1)
                    if subfolder_node:
                        subfolder_nodes.append(subfolder_node)

                # Combine subfolders and comics as children
                children = subfolder_nodes + comic_nodes

                # Count total comics (including subfolders)
                total_comic_count = len(comics_in_folder)
                for subfolder_node in subfolder_nodes:
                    total_comic_count += subfolder_node.get("comicCount", 0)

                return {
                    "id": f"folder-{self.library_id}-{folder.id}",
                    "folderId": folder.id,
                    "name": folder.name,
                    "type": "folder",
                    "libraryId": self.library_id,
                    "comicCount": total_comic_count,
                    "children": children
                }

            # Find root folder
            root_folder = next((f for f in all_folders if f.name == "__ROOT__"), None)
            if not root_folder:
                logger.warning(f"No root folder found for library {self.library_id}")
                return

            # Get top-level folders
            top_level_folders = [
                f for f in all_folders
                if f.parent_id == root_folder.id or (f.parent_id is None and f.name != "__ROOT__")
            ]

            # Build tree structure
            tree_children = []
            for folder in sorted(top_level_folders, key=lambda f: f.name):
                folder_node = build_folder_node(folder)
                if folder_node:
                    tree_children.append(folder_node)

            # Add root folder comics
            root_comics = comics_by_folder.get(root_folder.id, [])
            for comic in sorted(root_comics, key=lambda c: (c.volume or 0, c.issue_number or 0, c.title or c.filename)):
                # For single comics, strip file extension from filename
                display_name = comic.title
                if not display_name:
                    # Strip common comic extensions (.cbz, .cbr, .cb7, .cbt)
                    import re
                    display_name = re.sub(r'\.(cbz|cbr|cb7|cbt)$', '', comic.filename, flags=re.IGNORECASE)
                
                comic_info = {
                    "id": comic.id,
                    "name": display_name,
                    "type": "comic",
                    "libraryId": self.library_id,
                    "hash": comic.hash,
                    "totalPages": comic.num_pages,
                    "volume": comic.volume,
                    "issueNumber": comic.issue_number
                }
                tree_children.append(comic_info)

            # Serialize to JSON and store in database
            tree_json = json.dumps(tree_children)
            update_library_series_tree_cache(session, self.library_id, tree_json)
            session.commit()

            logger.info(f"Series tree cache built and stored for library {self.library_id}")


def scan_library_threaded(
    db: Database,
    library_id: int,
    library_path: Path,
    max_workers: int = 4,
    progress_callback=None
) -> ScanResult:
    """
    Convenience function to scan library with threading

    Args:
        db: Database instance
        library_id: Library ID
        library_path: Path to library
        max_workers: Number of worker threads
        progress_callback: Optional progress callback

    Returns:
        ScanResult with statistics
    """
    scanner = ThreadedScanner(db, library_id, max_workers, progress_callback)
    return scanner.scan_library(library_path)
