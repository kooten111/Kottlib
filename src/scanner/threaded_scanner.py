"""
Threaded Library Scanner

High-performance multi-threaded scanner for large comic libraries.
Significantly faster than single-threaded scanning.
"""

import time
import logging
from pathlib import Path
from typing import Tuple, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from dataclasses import dataclass

try:
    # Try relative imports (when used as a package)
    from ..database import (
        Database,
        create_comic,
        get_comic_by_hash,
        create_folder,
        get_folder_by_path,
        get_covers_dir,
    )
    from .comic_loader import open_comic, is_comic_file
    from .thumbnail_generator import (
        calculate_file_hash,
        generate_dual_thumbnails,
        thumbnail_exists,
    )
except ImportError:
    # Fallback for standalone scripts
    from database import (
        Database,
        create_comic,
        get_comic_by_hash,
        create_folder,
        get_folder_by_path,
        get_covers_dir,
    )
    from scanner.comic_loader import open_comic, is_comic_file
    from scanner.thumbnail_generator import (
        calculate_file_hash,
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

        # Thread-safe counters
        self._lock = Lock()
        self._comics_processed = 0
        self._comics_added = 0
        self._comics_skipped = 0
        self._thumbnails_generated = 0
        self._errors = 0

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

        # Create folders in database first
        folder_map = self._create_folders(library_path, folders)

        # Phase 2: Process comics in parallel (slow, multi-threaded)
        logger.info(f"Phase 2: Processing comics with {self.max_workers} workers...")
        self._process_comics_parallel(comic_files, folder_map, total_comics)

        duration = time.time() - start_time

        result = ScanResult(
            comics_found=total_comics,
            comics_added=self._comics_added,
            comics_skipped=self._comics_skipped,
            folders_found=len(folders),
            thumbnails_generated=self._thumbnails_generated,
            errors=self._errors,
            duration=duration
        )

        logger.info(
            f"Scan complete: {result.comics_added} added, "
            f"{result.comics_skipped} skipped, "
            f"{result.errors} errors in {duration:.2f}s"
        )

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

    def _create_folders(self, library_path: Path, folder_paths: List[Path]) -> dict:
        """
        Create all folders in database and return mapping

        Args:
            library_path: Library root path
            folder_paths: List of folder paths to create

        Returns:
            Dict mapping folder path to folder ID
        """
        folder_map = {}

        # Sort folders by depth to create parents first
        sorted_folders = sorted(folder_paths, key=lambda p: len(p.parts))

        with self.db.get_session() as session:
            for folder_path in sorted_folders:
                # Get or create folder
                folder = get_folder_by_path(session, self.library_id, str(folder_path))

                if not folder:
                    # Find parent folder ID
                    parent_id = None
                    parent_path = folder_path.parent
                    if parent_path != library_path and str(parent_path) in folder_map:
                        parent_id = folder_map[str(parent_path)]

                    folder = create_folder(
                        session,
                        library_id=self.library_id,
                        path=str(folder_path),
                        name=folder_path.name,
                        parent_id=parent_id
                    )

                folder_map[str(folder_path)] = folder.id

        return folder_map

    def _process_comics_parallel(
        self,
        comic_files: List[Tuple[Path, Optional[Path]]],
        folder_map: dict,
        total: int
    ):
        """
        Process comics in parallel using thread pool

        Args:
            comic_files: List of (comic_path, parent_folder_path) tuples
            folder_map: Mapping of folder paths to folder IDs
            total: Total number of comics (for progress)
        """
        # Use thread pool to process comics in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            futures = []
            for comic_path, parent_folder in comic_files:
                folder_id = folder_map.get(str(parent_folder)) if parent_folder else None
                future = executor.submit(self._process_single_comic, comic_path, folder_id)
                futures.append(future)

            # Process completed tasks
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Error processing comic: {e}")
                    with self._lock:
                        self._errors += 1

                # Update progress
                with self._lock:
                    self._comics_processed += 1
                    if self.progress_callback:
                        self.progress_callback(
                            self._comics_processed,
                            total,
                            f"Processed {self._comics_processed}/{total} comics"
                        )

    def _process_single_comic(self, comic_path: Path, folder_id: Optional[int]):
        """
        Process a single comic file

        Args:
            comic_path: Path to comic file
            folder_id: Parent folder ID (or None)
        """
        try:
            # Calculate hash
            file_hash = calculate_file_hash(comic_path)

            # Check if already in database (use separate session per thread)
            with self.db.get_session() as session:
                existing = get_comic_by_hash(session, file_hash)
                if existing:
                    with self._lock:
                        self._comics_skipped += 1
                    return

            # Open comic to extract metadata
            with open_comic(comic_path) as comic:
                if comic is None:
                    logger.warning(f"Failed to open: {comic_path}")
                    with self._lock:
                        self._errors += 1
                    return

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

        if comic.comic_info:
            info = comic.comic_info
            if info.title:
                metadata['title'] = info.title
            if info.series:
                metadata['series'] = info.series
            if info.number:
                try:
                    metadata['issue_number'] = float(info.number)
                except ValueError:
                    pass
            if info.year:
                metadata['year'] = info.year
            if info.publisher:
                metadata['publisher'] = info.publisher
            if info.writer:
                metadata['writer'] = info.writer
            if info.manga:
                metadata['reading_direction'] = 'rtl' if info.manga else 'ltr'

        return metadata

    def _generate_thumbnails(self, comic, file_hash: str):
        """
        Generate thumbnails for comic

        Args:
            comic: Opened comic object
            file_hash: File hash
        """
        try:
            covers_dir = get_covers_dir()

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
