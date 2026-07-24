"""
Database migrations module
"""

from . import add_search_indexes
from . import add_cover_source_columns
from . import add_folder_last_content_at
from . import inline_schema
from .runner import run_startup_migrations, STARTUP_MIGRATIONS

__all__ = [
    'add_search_indexes',
    'add_cover_source_columns',
    'add_folder_last_content_at',
    'inline_schema',
    'run_startup_migrations',
    'STARTUP_MIGRATIONS',
]
