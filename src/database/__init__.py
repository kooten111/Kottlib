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
    # Folder operations
    create_folder,
    get_folder_by_id,
    get_folder_by_path,
    get_folders_in_library,
    get_subfolders,
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
    'create_folder',
    'get_folder_by_id',
    'get_folder_by_path',
    'get_folders_in_library',
    'get_subfolders',
    'get_user_by_username',
    'get_user_by_id',
    'create_session',
    'get_session_by_id',
    'update_session_activity',
    'cleanup_expired_sessions',
    'get_library_stats',
]
