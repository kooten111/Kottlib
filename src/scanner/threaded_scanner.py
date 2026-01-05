"""
Threaded Library Scanner

High-performance multi-threaded scanner for large comic libraries.
Significantly faster than single-threaded scanning.

This module has been refactored to use focused submodules:
- base.py: ScanResult dataclass
- file_discovery.py: discover_files function
- structure_classifier.py: classify_series_structure, scan_library_structure
- folder_manager.py: create_folders function
- comic_processor.py: process_single_comic, extract_metadata
- series_builder.py: rebuild_series_table, build_series_tree_cache
- cleanup.py: cleanup_missing_comics function
"""

import time
import logging
import warnings
from pathlib import Path
from typing import Tuple, List, Optional, Dict, Any, Callable
from concurrent.futures import ThreadPoolExecutor
from threading import Lock, Thread, current_thread

# Suppress PIL warnings about corrupt EXIF data
warnings.filterwarnings('ignore', message='Corrupt EXIF data')

from src.database import Database, get_library_by_id, get_folder_by_path

# Import from refactored modules
from .base import ScanResult
from .file_discovery import discover_files
from .structure_classifier import scan_library_structure
from .folder_manager import create_folders
from .comic_processor import process_single_comic
from .series_builder import rebuild_series_table, build_series_tree_cache
from .cleanup import cleanup_missing_comics


logger = logging.getLogger(__name__)


class ThreadedScanner:
    """
    Multi-threaded comic library scanner.

    Splits work into three phases:
    1. File discovery (fast, single-threaded)
    2. Comic processing (slow, multi-threaded)
    3. Cleanup of missing comics (removes stale database entries)

    Uses thread pool for parallel processing of comics.
    """

    def __init__(
        self,
        db: Database,
        library_id: int,
        max_workers: int = 4,
        progress_callback: Optional[Callable[..., None]] = None
    ) -> None:
        """
        Initialize threaded scanner.

        Args:
            db: Database instance
            library_id: Library ID to scan into
            max_workers: Number of worker threads (default: 4)
            progress_callback: Optional callback(current, total, message)
        """
        self.db: Database = db
        self.library_id: int = library_id
        self.max_workers: int = max_workers
        self.progress_callback: Optional[Callable[..., None]] = progress_callback

        # Get library name for per-library data directories
        with self.db.get_session() as session:
            library = get_library_by_id(session, library_id)
            self.library_name: Optional[str] = library.name if library else None

        # Thread-safe counters
        self._lock: Lock = Lock()
        self._comics_processed: int = 0
        self._counters: Dict[str, int] = {
            'added': 0,
            'skipped': 0,
            'unchanged': 0,
            'updated': 0,
            'thumbnails': 0,
            'errors': 0
        }

        # Track active workers for progress display
        self._active_workers: Dict[int, Tuple[str, str]] = {}  # worker_id -> (series_name, filename)

        # Structure cache: folder_path -> mode
        self._structure_cache: Dict[str, str] = {}

    def scan_library(self, library_path: Path) -> ScanResult:
        """
        Scan entire library with multi-threading.

        Args:
            library_path: Path to library root

        Returns:
            ScanResult with statistics
        """
        self.library_path = library_path  # Store for metadata extraction
        start_time = time.time()
        logger.info(f"Starting threaded scan of {library_path}")

        # Phase 1: Discover all files (fast, single-threaded)
        logger.info("Phase 1: Discovering files...")
        
        # Pre-scan structure using extracted module
        self._structure_cache = scan_library_structure(library_path)
        
        # Use extracted discover_files function
        comic_files, folders = discover_files(library_path)

        total_comics = len(comic_files)
        logger.info(f"Found {total_comics} comics in {len(folders)} folders")

        if total_comics == 0:
            logger.info("No comics found in scan - proceeding to cleanup phase to remove any deleted files")

        # Create folders in database first (including root folder)
        # Use extracted create_folders function
        folder_map, root_folder_id = create_folders(
            self.db,
            self.library_id,
            library_path,
            folders
        )

        # Ensure all parent folders are in the map
        # This prevents comics from being flattened to root if their parent wasn't in discovered folders
        missing_parents = set()
        for _, parent_folder in comic_files:
            if parent_folder and str(parent_folder) not in folder_map:
                missing_parents.add(str(parent_folder))
        
        if missing_parents:
            logger.info(f"Resolving {len(missing_parents)} missing parent folders from DB...")
            with self.db.get_session() as session:
                for parent_path_str in missing_parents:
                    folder = get_folder_by_path(session, self.library_id, parent_path_str)
                    if folder:
                        folder_map[parent_path_str] = folder.id
                        logger.debug(f"Resolved missing folder: {parent_path_str}")

        # Phase 2: Process comics in parallel (slow, multi-threaded)
        logger.info(f"Phase 2: Processing comics with {self.max_workers} workers...")
        self._process_comics_parallel(comic_files, folder_map, root_folder_id, total_comics)

        # Phase 3: Cleanup - remove comics that no longer exist on disk
        logger.info("Phase 3: Cleaning up missing comics...")
        if self.progress_callback:
            self.progress_callback(0, 0, "Cleaning up...", None, None, [])
        
        # Build set of discovered paths for comparison
        discovered_paths = {str(comic_path) for comic_path, _ in comic_files}
        
        try:
            comics_removed = cleanup_missing_comics(
                self.db,
                self.library_id,
                library_path,
                discovered_paths,
                self.library_name  # Pass library name for cover cleanup
            )
        except Exception as e:
            logger.error(f"Failed to cleanup missing comics: {e}", exc_info=True)
            comics_removed = 0

        duration = time.time() - start_time

        result = ScanResult(
            comics_found=total_comics,
            comics_added=self._counters['added'],
            comics_skipped=self._counters['skipped'],
            comics_skipped_unchanged=self._counters['unchanged'],
            comics_updated=self._counters['updated'],
            comics_removed=comics_removed,
            folders_found=len(folders),
            thumbnails_generated=self._counters['thumbnails'],
            errors=self._counters['errors'],
            duration=duration
        )

        logger.info(
            f"Scan complete: {result.comics_added} added, "
            f"{result.comics_skipped} skipped ({result.comics_skipped_unchanged} unchanged, "
            f"{result.comics_updated} updated), "
            f"{result.comics_removed} removed, "
            f"{result.errors} errors in {duration:.2f}s"
        )

        # Rebuild series table from comics (ensures series are up-to-date)
        # Use extracted rebuild_series_table function
        try:
            rebuild_series_table(self.db, self.library_id)
        except Exception as e:
            logger.error(f"Failed to rebuild series table: {e}", exc_info=True)
            logger.warning(
                "Series table rebuild failed - series grouping may be incomplete. "
                "This is not critical and the scan will continue."
            )
            # Don't fail the scan if series rebuild fails

        # Build and cache the series tree for fast loading
        # Use extracted build_series_tree_cache function
        try:
            build_series_tree_cache(self.db, self.library_id)
        except Exception as e:
            logger.error(f"Failed to build series tree cache: {e}", exc_info=True)
            logger.warning(
                "Series tree cache build failed - tree navigation may be slower. "
                "This is not critical and the scan will continue."
            )
            # Don't fail the scan if cache building fails

        # Invalidate browse cache so UI gets fresh data
        try:
            from ..services.library_cache import get_library_cache
            get_library_cache(self.library_id).invalidate_all()
        except Exception as e:
            logger.error(f"Failed to invalidate browse cache: {e}")

        return result

    def _process_comics_parallel(
        self,
        comic_files: List[Tuple[Path, Optional[Path]]],
        folder_map: Dict[str, int],
        root_folder_id: int,
        total: int
    ) -> None:
        """
        Process comics in parallel using thread pool.

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

                future = executor.submit(
                    self._process_single_comic_tracked,
                    comic_path,
                    folder_id
                )
                futures.append((future, comic_path))

            # Progress monitoring thread
            def monitor_progress() -> None:
                """Update progress display with active workers."""
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
                        self._counters['errors'] += 1

                # Update progress counter
                with self._lock:
                    self._comics_processed += 1

            # Final progress update to clear active workers
            if self.progress_callback:
                self.progress_callback(self._comics_processed, total, "Complete", None, None, [])

    def _process_single_comic_tracked(self, comic_path: Path, folder_id: Optional[int]) -> None:
        """
        Wrapper for process_single_comic that tracks active workers.

        Args:
            comic_path: Path to comic file
            folder_id: Parent folder ID (or None)
        """
        thread_id = current_thread().ident

        # Register this worker as active
        series_name = comic_path.parent.name if comic_path.parent else "Root"
        filename = comic_path.name
        with self._lock:
            self._active_workers[thread_id] = (series_name, filename)

        try:
            # Process the comic using extracted function
            process_single_comic(
                db=self.db,
                library_id=self.library_id,
                library_name=self.library_name,
                library_path=self.library_path,
                comic_path=comic_path,
                folder_id=folder_id,
                structure_cache=self._structure_cache,
                lock=self._lock,
                counters=self._counters
            )
        finally:
            # Unregister this worker
            with self._lock:
                self._active_workers.pop(thread_id, None)


def scan_library_threaded(
    db: Database,
    library_id: int,
    library_path: Path,
    max_workers: int = 4,
    progress_callback: Optional[Callable[..., None]] = None
) -> ScanResult:
    """
    Convenience function to scan library with threading.

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
