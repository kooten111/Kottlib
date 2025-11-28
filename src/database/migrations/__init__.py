"""
Database migrations module
"""

from . import add_search_indexes
from . import add_cover_source_columns

__all__ = ['add_search_indexes', 'add_cover_source_columns']
