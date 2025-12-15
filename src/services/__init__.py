"""
Services Module

Business logic layer for Kottlib.
Services orchestrate database operations and other lower-level functionality.
"""

# Import and export all services
from .library_service import (
    create_library_with_stats,
    get_library_with_stats,
    list_libraries_with_stats,
    update_library_with_stats,
    delete_library_with_cleanup,
    get_library_statistics,
)

from .scan_service import (
    scan_library,
    scan_single_comic,
    scan_series,
    get_scan_progress,
    start_library_scan_task,
)

from .search_service import (
    search_comics,
    search_comics_fts,
    advanced_search,
)

from .cover_service import (
    get_cover_for_comic,
    fetch_external_covers,
    fetch_and_set_cover,
)

from .reading_service import (
    update_reading_progress,
    get_continue_reading,
    get_user_favorites,
    add_to_favorites,
    remove_from_favorites,
    get_user_labels,
    create_label,
    add_label_to_comic,
    remove_label_from_comic,
    get_user_reading_lists,
    create_reading_list,
    add_comic_to_reading_list,
    remove_comic_from_reading_list,
)

# Existing services
from .metadata_service import MetadataService
from .scheduler import BackgroundScheduler

__all__ = [
    # Library service
    "create_library_with_stats",
    "get_library_with_stats",
    "list_libraries_with_stats",
    "update_library_with_stats",
    "delete_library_with_cleanup",
    "get_library_statistics",
    
    # Scan service
    "scan_library",
    "scan_single_comic",
    "scan_series",
    "get_scan_progress",
    "start_library_scan_task",
    
    # Search service
    "search_comics",
    "search_comics_fts",
    "advanced_search",
    
    # Cover service
    "get_cover_for_comic",
    "fetch_external_covers",
    "fetch_and_set_cover",
    
    # Reading service
    "update_reading_progress",
    "get_continue_reading",
    "get_user_favorites",
    "add_to_favorites",
    "remove_from_favorites",
    "get_user_labels",
    "create_label",
    "add_label_to_comic",
    "remove_label_from_comic",
    "get_user_reading_lists",
    "create_reading_list",
    "add_comic_to_reading_list",
    "remove_comic_from_reading_list",
    
    # Existing services
    "MetadataService",
    "BackgroundScheduler",
]
