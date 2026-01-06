"""
Database Models Package

SQLAlchemy ORM models for Kottlib database.
All models are re-exported from this package for backward compatibility.
"""

# Base
from .base import Base

# Library and Folder models
from .library import Library, Folder

# Comic models
from .comic import Comic, Cover

# User models
from .user import User, Session

# Reading models
from .reading import ReadingProgress

# Series models
from .series import Series

# Collection models
from .collection import Collection, Favorite, Label, ComicLabel

# Reading List models
from .reading_list import ReadingList, ReadingListItem

# Setting model
from .setting import Setting


__all__ = [
    # Base
    'Base',
    # Library
    'Library',
    'Folder',
    # Comics
    'Comic',
    'Cover',
    # Users
    'User',
    'Session',
    # Reading
    'ReadingProgress',
    # Series
    'Series',
    # Collections
    'Collection',
    'Favorite',
    'Label',
    'ComicLabel',
    # Reading Lists
    'ReadingList',
    'ReadingListItem',
    # Settings
    'Setting',
]
