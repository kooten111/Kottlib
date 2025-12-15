"""
Database operations module.

This package provides focused database operation functions organized by entity:
- library: Library CRUD operations
- comic: Comic CRUD and search operations
- folder: Folder operations
- user: User operations
- session: Session operations
- progress: Reading progress operations
- cover: Cover operations
- favorite: Favorites operations
- label: Labels/tags operations
- reading_list: Reading lists operations
"""

from .library import (
    create_library,
    get_library_by_id,
    get_library_by_path,
    update_library,
    delete_library,
    get_all_libraries,
    update_library_scan_status,
    update_library_series_tree_cache,
)
from .comic import (
    create_comic,
    get_comic_by_id,
    get_comic_by_hash,
    get_comic_by_path_and_mtime,
    get_comics_in_library,
    get_all_comics_in_db,
    get_comics_in_folder,
    get_comics_in_folder_simple,
    search_comics,
    get_sibling_comics,
)
from .folder import (
    create_folder,
    get_folder_by_id,
    get_folder_by_path,
    get_folders_in_library,
    get_or_create_root_folder,
    get_subfolders,
    get_first_comic_recursive,
)
from .user import (
    get_user_by_username,
    get_user_by_id,
)
from .session import (
    create_session,
    get_session_by_id,
    update_session_activity,
    cleanup_expired_sessions,
)
from .stats import (
    get_library_stats,
)
from .progress import (
    update_reading_progress,
    get_reading_progress,
    get_continue_reading,
    get_recently_completed,
)
from .cover import (
    create_cover,
    get_cover,
    get_best_cover,
    delete_cover,
)
from .favorite import (
    add_favorite,
    remove_favorite,
    get_user_favorites,
    is_favorite,
)
from .label import (
    create_label,
    get_label_by_id,
    get_labels_in_library,
    delete_label,
    add_label_to_comic,
    remove_label_from_comic,
    get_comics_with_label,
    get_comic_labels,
)
from .reading_list import (
    create_reading_list,
    get_reading_list_by_id,
    get_reading_lists_in_library,
    delete_reading_list,
    add_comic_to_reading_list,
    remove_comic_from_reading_list,
    get_reading_list_comics,
)


__all__ = [
    # Library
    "create_library",
    "get_library_by_id",
    "get_library_by_path",
    "update_library",
    "delete_library",
    "get_all_libraries",
    "update_library_scan_status",
    "update_library_series_tree_cache",
    # Comic
    "create_comic",
    "get_comic_by_id",
    "get_comic_by_hash",
    "get_comic_by_path_and_mtime",
    "get_comics_in_library",
    "get_all_comics_in_db",
    "get_comics_in_folder",
    "get_comics_in_folder_simple",
    "search_comics",
    "get_sibling_comics",
    # Folder
    "create_folder",
    "get_folder_by_id",
    "get_folder_by_path",
    "get_folders_in_library",
    "get_or_create_root_folder",
    "get_subfolders",
    "get_first_comic_recursive",
    # User
    "get_user_by_username",
    "get_user_by_id",
    # Session
    "create_session",
    "get_session_by_id",
    "update_session_activity",
    "cleanup_expired_sessions",
    # Stats
    "get_library_stats",
    # Progress
    "update_reading_progress",
    "get_reading_progress",
    "get_continue_reading",
    "get_recently_completed",
    # Cover
    "create_cover",
    "get_cover",
    "get_best_cover",
    "delete_cover",
    # Favorite
    "add_favorite",
    "remove_favorite",
    "get_user_favorites",
    "is_favorite",
    # Label
    "create_label",
    "get_label_by_id",
    "get_labels_in_library",
    "delete_label",
    "add_label_to_comic",
    "remove_label_from_comic",
    "get_comics_with_label",
    "get_comic_labels",
    # Reading List
    "create_reading_list",
    "get_reading_list_by_id",
    "get_reading_lists_in_library",
    "delete_reading_list",
    "add_comic_to_reading_list",
    "remove_comic_from_reading_list",
    "get_reading_list_comics",
]
