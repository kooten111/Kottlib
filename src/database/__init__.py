"""
Database Module

Provides database models and access layer for YACLib Enhanced.
"""

from .models import (
    Base,
    Library,
    Folder,
    Comic,
    Cover,
    User,
    Session,
    ReadingProgress,
    Series,
    Collection,
)

from .database import (
    Database,
    get_default_db_path,
    get_covers_dir,
    # Library operations
    create_library,
    get_library_by_id,
    get_library_by_path,
    get_all_libraries,
    update_library_scan_status,
    # Comic operations
    create_comic,
    get_comic_by_id,
    get_comic_by_hash,
    get_comics_in_library,
    get_comics_in_folder,
    get_sibling_comics,
    # Folder operations
    create_folder,
    get_folder_by_id,
    get_folder_by_path,
    get_folders_in_library,
    get_subfolders,
    get_or_create_root_folder,
    # User operations
    get_user_by_username,
    get_user_by_id,
    # Session operations
    create_session,
    get_session_by_id,
    update_session_activity,
    cleanup_expired_sessions,
    # Statistics
    get_library_stats,
    # Reading Progress operations
    update_reading_progress,
    get_reading_progress,
    get_continue_reading,
    get_recently_completed,
    # Cover operations
    create_cover,
    get_cover,
    get_best_cover,
    delete_cover,
)

__all__ = [
    # Models
    'Base',
    'Library',
    'Folder',
    'Comic',
    'Cover',
    'User',
    'Session',
    'ReadingProgress',
    'Series',
    'Collection',
    # Database
    'Database',
    'get_default_db_path',
    'get_covers_dir',
    # Operations
    'create_library',
    'get_library_by_id',
    'get_library_by_path',
    'get_all_libraries',
    'update_library_scan_status',
    'create_comic',
    'get_comic_by_id',
    'get_comic_by_hash',
    'get_comics_in_library',
    'get_comics_in_folder',
    'get_sibling_comics',
    'create_folder',
    'get_folder_by_id',
    'get_folder_by_path',
    'get_folders_in_library',
    'get_subfolders',
    'get_or_create_root_folder',
    'get_user_by_username',
    'get_user_by_id',
    'create_session',
    'get_session_by_id',
    'update_session_activity',
    'cleanup_expired_sessions',
    'get_library_stats',
    'update_reading_progress',
    'get_reading_progress',
    'get_continue_reading',
    'get_recently_completed',
    'create_cover',
    'get_cover',
    'get_best_cover',
    'delete_cover',
]
