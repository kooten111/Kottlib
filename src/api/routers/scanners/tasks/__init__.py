"""
Background tasks for scanner operations.

Contains the library scan background task function.
"""

from typing import Optional
import logging
import time

from sqlalchemy import or_

from src.database.models import Comic, Library, Series
from src.services.metadata_service import MetadataService

from ..progress import (
    start_scan_progress,
    update_scan_progress,
    persist_progress_to_db,
    get_internal_progress,
)
from ..manager import get_scanner_manager


logger = logging.getLogger(__name__)


def run_library_scan_task(
    db,
    library_id: int,
    scanner_name: str,
    overwrite: bool,
    rescan_existing: bool,
    confidence_threshold: Optional[float]
) -> None:
    """Background task to scan all comics in a library."""
    manager = get_scanner_manager()
    scanned = 0
    failed = 0
    skipped = 0
    processed = 0
    total_items = 0

    try:
        with db.get_session() as session:
            library = session.query(Library).filter(Library.id == library_id).first()
            if not library:
                logger.warning("Library %s no longer exists; aborting scan", library_id)
                return

            # Get scanner and determine scan level
            if scanner_name not in manager.get_available_scanners():
                logger.error("Scanner %s not available", scanner_name)
                return

            scanner_class = manager._available_scanners[scanner_name]
            scanner_instance = scanner_class()
            scan_level = scanner_instance.scan_level

            logger.info(
                "Starting library scan for library %s with scanner %s (scan_level=%s, rescan_existing=%s)",
                library_id,
                scanner_name,
                scan_level.value,
                rescan_existing
            )

            # Get scanner specific config
            settings = library.settings or {}
            scanner_config = settings.get('scanner', {})
            scanner_specific_config = scanner_config.get('scanner_configs', {}).get(scanner_name, {})
            
            # Get scanner instance directly (removed library_type abstraction)
            scanner = manager.get_scanner(scanner_name, config=scanner_specific_config)

            # Branch based on scan level (use string comparison to avoid enum import issues)
            if scan_level.value == 'file':
                # FILE-level scanning: scan each comic individually
                logger.info("Using FILE-level scanning (each comic individually)")

                # Get all comics in library
                query = session.query(Comic).filter(Comic.library_id == library_id)

                # Filter out already scanned if not rescanning
                if not rescan_existing:
                    query = query.filter(or_(Comic.scanned_at.is_(None), Comic.scanned_at == 0))

                comics = query.all()
                total_items = len(comics)

                # Initialize progress with known totals
                update_scan_progress(library_id, 0, total_items, 0, 0, 0)
                persist_progress_to_db(session, library, get_internal_progress(library_id) or {})

                for index, comic in enumerate(comics):
                    processed = index + 1

                    try:
                        # Scan using filename with direct scanner invocation
                        result, _ = scanner.scan(
                            comic.filename,
                            confidence_threshold=confidence_threshold
                        )

                        if not result:
                            skipped += 1
                        else:
                            # Apply metadata
                            application_result = MetadataService.apply_scan_result_to_comic(
                                session,
                                comic,
                                result,
                                scanner_name,
                                overwrite=overwrite
                            )

                            if application_result.success:
                                scanned += 1
                            else:
                                failed += 1

                    except Exception:
                        failed += 1
                        logger.exception("Failed to scan comic %s in library %s", comic.id, library_id)

                    # Update progress after each comic
                    update_scan_progress(library_id, processed, total_items, scanned, failed, skipped)
                    persist_progress_to_db(session, library, get_internal_progress(library_id) or {})

            elif scan_level.value == 'series':
                # SERIES-level scanning: scan each unique series
                logger.info("Using SERIES-level scanning (by series name)")

                # Get all unique series names from comics
                series_query = session.query(
                    Comic.series
                ).filter(
                    Comic.library_id == library_id,
                    Comic.series.isnot(None),
                    Comic.series != ''
                ).distinct()
                unique_series = [s[0] for s in series_query.all()]

                total_items = len(unique_series)
                logger.info("Found %s unique series to scan", total_items)

                # Initialize progress with known totals
                update_scan_progress(library_id, 0, total_items, 0, 0, 0)
                persist_progress_to_db(session, library, get_internal_progress(library_id) or {})

                for index, series_name in enumerate(unique_series):
                    processed = index + 1

                    try:
                        logger.info("Scanning series: %s", series_name)

                        # Scan for series metadata with retry logic for rate limiting
                        max_retries = 3
                        result = None

                        for attempt in range(max_retries):
                            try:
                                result, _ = scanner.scan(
                                    series_name,
                                    confidence_threshold=confidence_threshold
                                )
                                break  # Success, exit retry loop
                            except Exception as scan_error:
                                error_str = str(scan_error)
                                # Check if it's a rate limit error
                                if '429' in error_str or 'Too Many Requests' in error_str or 'Rate limit exceeded' in error_str:
                                    if attempt < max_retries - 1:
                                        # Try to extract Retry-After value from error message
                                        wait_time = 60  # Default to 60 seconds
                                        if '||RETRY_AFTER:' in error_str:
                                            try:
                                                retry_after_str = error_str.split('||RETRY_AFTER:')[1].strip()
                                                wait_time = int(retry_after_str)
                                            except (IndexError, ValueError):
                                                pass

                                        logger.warning(
                                            "Rate limit hit for series '%s', waiting %s seconds before retry %s/%s",
                                            series_name, wait_time, attempt + 1, max_retries
                                        )
                                        time.sleep(wait_time)
                                    else:
                                        logger.error("Max retries reached for series '%s' due to rate limiting", series_name)
                                        raise
                                else:
                                    # Not a rate limit error, raise immediately
                                    raise

                        if not result:
                            skipped += 1
                            logger.info("No match found for series: %s", series_name)
                        else:
                            # Get or create series record
                            series = session.query(Series).filter(
                                Series.library_id == library_id,
                                Series.name == series_name
                            ).first()

                            if not series:
                                series = Series(
                                    library_id=library_id,
                                    name=series_name,
                                    display_name=series_name,
                                    created_at=int(time.time()),
                                    updated_at=int(time.time())
                                )
                                session.add(series)
                                session.flush()

                            # Apply metadata to series
                            metadata = result.metadata

                            def should_update(field_value):
                                return overwrite or not field_value

                            if metadata.get('title') and should_update(series.display_name):
                                series.display_name = metadata['title']

                            if metadata.get('description') and should_update(series.description):
                                series.description = metadata['description']

                            if metadata.get('writer') and should_update(series.writer):
                                series.writer = metadata['writer']

                            if metadata.get('artist') and should_update(series.artist):
                                series.artist = metadata['artist']

                            if metadata.get('genre') and should_update(series.genre):
                                series.genre = metadata['genre']

                            if metadata.get('year') and should_update(series.year_start):
                                series.year_start = metadata['year']

                            if metadata.get('publisher') and should_update(series.publisher):
                                series.publisher = metadata['publisher']

                            if metadata.get('status') and should_update(series.status):
                                series.status = metadata['status']

                            if metadata.get('format') and should_update(series.format):
                                series.format = metadata['format']

                            if metadata.get('volume') and should_update(series.volumes):
                                series.volumes = metadata['volume']

                            if metadata.get('count') and should_update(series.chapters):
                                series.chapters = metadata['count']

                            if result.tags and should_update(series.tags):
                                series.tags = ', '.join(result.tags) if isinstance(result.tags, list) else str(result.tags)

                            # Store scanner metadata
                            series.scanner_source = scanner_name
                            series.scanner_source_id = result.source_id
                            series.scanner_source_url = result.source_url
                            series.scanned_at = int(time.time())
                            series.scan_confidence = result.confidence
                            series.updated_at = int(time.time())

                            session.commit()
                            scanned += 1
                            logger.info("Successfully scanned series: %s (confidence: %.2f)", series_name, result.confidence)

                    except Exception:
                        failed += 1
                        logger.exception("Failed to scan series %s in library %s", series_name, library_id)
                        session.rollback()

                    # Update progress after each series
                    update_scan_progress(library_id, processed, total_items, scanned, failed, skipped)
                    persist_progress_to_db(session, library, get_internal_progress(library_id) or {})

            else:
                logger.error("Unsupported scan level: %s", scan_level)
                return

    except Exception as exc:
        logger.exception("Library scan failed for library %s", library_id)
        progress = get_internal_progress(library_id) or start_scan_progress(library_id)
        progress.update({
            "processed": processed,
            "scanned": scanned,
            "total": total_items,
            "failed": failed,
            "skipped": skipped,
            "error": str(exc)
        })
        try:
            with db.get_session() as session:
                library = session.query(Library).filter(Library.id == library_id).first()
                if library:
                    persist_progress_to_db(session, library, progress)
        except Exception:
            logger.exception("Failed to persist error progress for library %s", library_id)

    finally:
        progress = get_internal_progress(library_id) or start_scan_progress(library_id)
        progress.update({
            "processed": processed,
            "scanned": scanned,
            "total": total_items,
            "failed": failed,
            "skipped": skipped,
            "in_progress": False,
            "completed": True
        })
        try:
            with db.get_session() as session:
                library = session.query(Library).filter(Library.id == library_id).first()
                if library:
                    persist_progress_to_db(session, library, progress)
        except Exception:
            logger.exception("Failed to persist final progress for library %s", library_id)

        logger.info(
            "Library scan completed for library %s: processed=%s scanned=%s failed=%s skipped=%s",
            library_id,
            processed,
            scanned,
            failed,
            skipped
        )
