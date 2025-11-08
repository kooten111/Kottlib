"""
Database Models

SQLAlchemy ORM models for YACLib Enhanced database.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Integer, String, Text, Boolean, Float, JSON,
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship
)


class Base(DeclarativeBase):
    """Base class for all models"""
    pass


# ============================================================================
# LIBRARIES
# ============================================================================

class Library(Base):
    __tablename__ = 'libraries'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uuid: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    path: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[int] = mapped_column(Integer, nullable=False)
    last_scan_at: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    scan_status: Mapped[str] = mapped_column(String, default='pending')
    settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    folders: Mapped[List["Folder"]] = relationship(back_populates="library", cascade="all, delete-orphan")
    comics: Mapped[List["Comic"]] = relationship(back_populates="library", cascade="all, delete-orphan")
    series: Mapped[List["Series"]] = relationship(back_populates="library", cascade="all, delete-orphan")


# ============================================================================
# FOLDERS
# ============================================================================

class Folder(Base):
    __tablename__ = 'folders'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    library_id: Mapped[int] = mapped_column(ForeignKey('libraries.id', ondelete='CASCADE'), nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey('folders.id', ondelete='CASCADE'), nullable=True)
    path: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    library: Mapped["Library"] = relationship(back_populates="folders")
    parent: Mapped[Optional["Folder"]] = relationship(remote_side=[id], back_populates="children")
    children: Mapped[List["Folder"]] = relationship(back_populates="parent", cascade="all, delete-orphan")
    comics: Mapped[List["Comic"]] = relationship(back_populates="folder")

    __table_args__ = (
        UniqueConstraint('library_id', 'path'),
        Index('idx_folders_library', 'library_id'),
        Index('idx_folders_parent', 'parent_id'),
    )


# ============================================================================
# COMICS
# ============================================================================

class Comic(Base):
    __tablename__ = 'comics'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    library_id: Mapped[int] = mapped_column(ForeignKey('libraries.id', ondelete='CASCADE'), nullable=False)
    folder_id: Mapped[Optional[int]] = mapped_column(ForeignKey('folders.id', ondelete='SET NULL'), nullable=True)
    path: Mapped[str] = mapped_column(String, nullable=False)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    hash: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    # File metadata
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_modified_at: Mapped[int] = mapped_column(Integer, nullable=False)
    format: Mapped[str] = mapped_column(String, nullable=False)

    # Comic metadata
    title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    series: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    volume: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    issue_number: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    publisher: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    writer: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    artist: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Reading metadata
    num_pages: Mapped[int] = mapped_column(Integer, nullable=False)
    reading_direction: Mapped[str] = mapped_column(String, default='ltr')

    # Status
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    library: Mapped["Library"] = relationship(back_populates="comics")
    folder: Mapped[Optional["Folder"]] = relationship(back_populates="comics")
    covers: Mapped[List["Cover"]] = relationship(back_populates="comic", cascade="all, delete-orphan")
    reading_progress: Mapped[List["ReadingProgress"]] = relationship(back_populates="comic", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_comics_library', 'library_id'),
        Index('idx_comics_folder', 'folder_id'),
        Index('idx_comics_hash', 'hash'),
        Index('idx_comics_series', 'series'),
    )


# ============================================================================
# COVERS
# ============================================================================

class Cover(Base):
    __tablename__ = 'covers'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    comic_id: Mapped[int] = mapped_column(ForeignKey('comics.id', ondelete='CASCADE'), nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)  # auto, custom
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    jpeg_path: Mapped[str] = mapped_column(String, nullable=False)
    webp_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    generated_at: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    comic: Mapped["Comic"] = relationship(back_populates="covers")

    __table_args__ = (
        UniqueConstraint('comic_id', 'type'),
        Index('idx_covers_comic', 'comic_id'),
    )


# ============================================================================
# READING PROGRESS
# ============================================================================

class ReadingProgress(Base):
    __tablename__ = 'reading_progress'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    comic_id: Mapped[int] = mapped_column(ForeignKey('comics.id', ondelete='CASCADE'), nullable=False)

    # Progress
    current_page: Mapped[int] = mapped_column(Integer, default=0)
    total_pages: Mapped[int] = mapped_column(Integer, nullable=False)
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    started_at: Mapped[int] = mapped_column(Integer, nullable=False)
    last_read_at: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_at: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="reading_progress")
    comic: Mapped["Comic"] = relationship(back_populates="reading_progress")

    __table_args__ = (
        UniqueConstraint('user_id', 'comic_id'),
        Index('idx_reading_progress_user', 'user_id'),
        Index('idx_reading_progress_comic', 'comic_id'),
        Index('idx_reading_progress_last_read', 'last_read_at'),
    )


# ============================================================================
# SERIES
# ============================================================================

class Series(Base):
    __tablename__ = 'series'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    library_id: Mapped[int] = mapped_column(ForeignKey('libraries.id', ondelete='CASCADE'), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Metadata
    publisher: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    year_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    year_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Stats
    comic_count: Mapped[int] = mapped_column(Integer, default=0)
    total_issues: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    library: Mapped["Library"] = relationship(back_populates="series")

    __table_args__ = (
        UniqueConstraint('library_id', 'name'),
        Index('idx_series_library', 'library_id'),
        Index('idx_series_name', 'name'),
    )


# ============================================================================
# USERS
# ============================================================================

class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    last_login_at: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    reading_progress: Mapped[List["ReadingProgress"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    sessions: Mapped[List["Session"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    collections: Mapped[List["Collection"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_users_username', 'username'),
    )


# ============================================================================
# SESSIONS
# ============================================================================

class Session(Base):
    __tablename__ = 'sessions'

    id: Mapped[str] = mapped_column(String, primary_key=True)  # Session UUID
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    # Session state
    current_library_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    current_comic_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Metadata
    user_agent: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    last_activity_at: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="sessions")

    __table_args__ = (
        Index('idx_sessions_user', 'user_id'),
        Index('idx_sessions_expires', 'expires_at'),
    )


# ============================================================================
# COLLECTIONS
# ============================================================================

class Collection(Base):
    __tablename__ = 'collections'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="collections")

    __table_args__ = (
        Index('idx_collections_user', 'user_id'),
    )
