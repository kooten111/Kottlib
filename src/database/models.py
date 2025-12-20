"""
Database Models

SQLAlchemy ORM models for Kottlib database.
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

    scan_status: Mapped[str] = mapped_column(String, default='pending')
    last_scan_started: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_scan_completed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    scanner_type: Mapped[str] = mapped_column(String, default='comic')
    settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    scan_interval: Mapped[int] = mapped_column(Integer, default=0)  # Scan interval in minutes (0 = disabled)

    # Performance cache - stores pre-built series tree as JSON
    cached_series_tree: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tree_cache_updated_at: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    folders: Mapped[List["Folder"]] = relationship(back_populates="library", cascade="all, delete-orphan")
    comics: Mapped[List["Comic"]] = relationship(back_populates="library", cascade="all, delete-orphan")
    series: Mapped[List["Series"]] = relationship(back_populates="library", cascade="all, delete-orphan")
    
    @property
    def last_scan_at(self) -> Optional[int]:
        """Alias for last_scan_completed for backward compatibility"""
        return self.last_scan_completed


# ============================================================================
# FOLDERS
# ============================================================================

class Folder(Base):
    __tablename__ = 'folders'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # library_id is nullable to support both main DB (has library_id) and library-specific DBs (no library_id)
    library_id: Mapped[Optional[int]] = mapped_column(ForeignKey('libraries.id', ondelete='CASCADE'), nullable=True)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey('folders.id', ondelete='CASCADE'), nullable=True)
    path: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    first_child_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
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
        # Performance indexes
        Index('idx_folders_library_path', 'library_id', 'path'),
        Index('idx_folders_name', 'name'),
    )


# ============================================================================
# COMICS
# ============================================================================

class Comic(Base):
    __tablename__ = 'comics'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # library_id is nullable to support both main DB (has library_id) and library-specific DBs (no library_id)
    library_id: Mapped[Optional[int]] = mapped_column(ForeignKey('libraries.id', ondelete='CASCADE'), nullable=True)
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
    # normalized_series_name removed as per user request
    volume: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    issue_number: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    publisher: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    writer: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    artist: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Extended ComicInfo.xml metadata (YACReader compatibility)
    penciller: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    inker: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    colorist: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    letterer: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    cover_artist: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    editor: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Series/Arc metadata
    story_arc: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    arc_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    arc_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Alternate series
    alternate_series: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    alternate_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    alternate_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Additional metadata
    genre: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    language_iso: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    age_rating: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    imprint: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    format_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # Comic format (not file format)
    is_color: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Characters, teams, locations
    characters: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    teams: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    locations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    main_character_or_team: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Series organization
    series_group: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # User content
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # External IDs
    comic_vine_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    web: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # Web URL / source URL

    # Flexible Metadata (JSON)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Scanner metadata
    scanner_source: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # Scanner name (e.g., 'nhentai')
    scanner_source_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # External source ID
    scanner_source_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # External source URL
    scanned_at: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Timestamp of last scan
    scan_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Confidence score (0.0-1.0)

    # Issue metadata
    is_bis: Mapped[bool] = mapped_column(Boolean, default=False)  # Special issue flag
    count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Total issue count in series
    date: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # Publication date (YYYY-MM or YYYY-MM-DD)

    # Reading metadata
    num_pages: Mapped[int] = mapped_column(Integer, nullable=False)
    reading_direction: Mapped[str] = mapped_column(String, default='ltr')

    # Display settings (per-comic)
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    brightness: Mapped[int] = mapped_column(Integer, default=0)
    contrast: Mapped[int] = mapped_column(Integer, default=0)
    gamma: Mapped[float] = mapped_column(Float, default=1.0)

    # Bookmarks (page numbers)
    bookmark1: Mapped[int] = mapped_column(Integer, default=0)
    bookmark2: Mapped[int] = mapped_column(Integer, default=0)
    bookmark3: Mapped[int] = mapped_column(Integer, default=0)

    # Cover info
    cover_page: Mapped[int] = mapped_column(Integer, default=1)
    cover_size_ratio: Mapped[float] = mapped_column(Float, default=0.0)  # Width/Height ratio
    original_cover_size: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # e.g., "800x1200"

    # Access tracking
    last_time_opened: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    has_been_opened: Mapped[bool] = mapped_column(Boolean, default=False)
    edited: Mapped[bool] = mapped_column(Boolean, default=False)  # Metadata manually edited flag

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
        # Performance indexes
        Index('idx_comics_title', 'title'),
        Index('idx_comics_publisher', 'publisher'),
        Index('idx_comics_year', 'year'),
        Index('idx_comics_filename', 'filename'),
        Index('idx_comics_library_series', 'library_id', 'series'),
        Index('idx_comics_library_folder', 'library_id', 'folder_id'),
        Index('idx_comics_file_modified', 'file_modified_at'),
        Index('idx_comics_library_count', 'library_id'),
        # Search optimization indexes (for metadata search)
        Index('idx_comics_writer', 'writer'),
        Index('idx_comics_artist', 'artist'),
        Index('idx_comics_penciller', 'penciller'),
        Index('idx_comics_inker', 'inker'),
        Index('idx_comics_colorist', 'colorist'),
        Index('idx_comics_letterer', 'letterer'),
        Index('idx_comics_cover_artist', 'cover_artist'),
        Index('idx_comics_editor', 'editor'),
        Index('idx_comics_genre', 'genre'),
        Index('idx_comics_scanner_source', 'scanner_source'),
        Index('idx_comics_story_arc', 'story_arc'),
        Index('idx_comics_language', 'language_iso'),
        Index('idx_comics_age_rating', 'age_rating'),
        # Composite indexes for common search patterns
        Index('idx_comics_library_writer', 'library_id', 'writer'),
        Index('idx_comics_library_artist', 'library_id', 'artist'),
        Index('idx_comics_library_genre', 'library_id', 'genre'),
        Index('idx_comics_library_publisher', 'library_id', 'publisher'),
        Index('idx_comics_library_year', 'library_id', 'year'),
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

    # External source tracking
    source: Mapped[str] = mapped_column(String, nullable=False, default='archive')  # archive, mangadex, upload
    source_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # Original URL for external covers

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
        # Performance indexes
        Index('idx_reading_progress_continue', 'user_id', 'is_completed', 'last_read_at'),
        Index('idx_reading_progress_completed', 'user_id', 'is_completed', 'completed_at'),
        Index('idx_reading_progress_percent', 'progress_percent'),
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

    # Scanner metadata
    scanner_source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    scanner_source_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    scanner_source_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    scanned_at: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    scan_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Additional metadata fields
    writer: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    artist: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    genre: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    format: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    chapters: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    volumes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    library: Mapped["Library"] = relationship(back_populates="series")

    __table_args__ = (
        UniqueConstraint('library_id', 'name'),
        Index('idx_series_library', 'library_id'),
        Index('idx_series_name', 'name'),
        # Performance indexes
        Index('idx_series_library_name', 'library_id', 'name'),
        Index('idx_series_year_start', 'year_start'),
        # Search optimization indexes
        Index('idx_series_writer', 'writer'),
        Index('idx_series_artist', 'artist'),
        Index('idx_series_genre', 'genre'),
        Index('idx_series_publisher', 'publisher'),
        Index('idx_series_status', 'status'),
        Index('idx_series_scanner_source', 'scanner_source'),
        # Composite indexes for common search patterns
        Index('idx_series_library_writer', 'library_id', 'writer'),
        Index('idx_series_library_artist', 'library_id', 'artist'),
        Index('idx_series_library_genre', 'library_id', 'genre'),
        Index('idx_series_library_publisher', 'library_id', 'publisher'),
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

    # Device info (YACReader compatibility)
    device_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # e.g., 'ipad', 'android', 'tablet'
    display_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # e.g., '@1x', '@2x', '@3x'
    downloaded_comics: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Tab-separated list of hashes

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
        # Performance indexes
        Index('idx_collections_user_position', 'user_id', 'position'),
    )


# ============================================================================
# FAVORITES (YACReader Compatibility)
# ============================================================================

class Favorite(Base):
    __tablename__ = 'favorites'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    library_id: Mapped[int] = mapped_column(ForeignKey('libraries.id', ondelete='CASCADE'), nullable=False)
    comic_id: Mapped[int] = mapped_column(ForeignKey('comics.id', ondelete='CASCADE'), nullable=False)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint('user_id', 'comic_id'),
        Index('idx_favorites_user', 'user_id'),
        Index('idx_favorites_library', 'library_id'),
        Index('idx_favorites_comic', 'comic_id'),
        # Performance indexes
        Index('idx_favorites_user_created', 'user_id', 'created_at'),
    )


# ============================================================================
# LABELS/TAGS (YACReader Compatibility)
# ============================================================================

class Label(Base):
    __tablename__ = 'labels'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    library_id: Mapped[int] = mapped_column(ForeignKey('libraries.id', ondelete='CASCADE'), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    color_id: Mapped[int] = mapped_column(Integer, default=0)  # Color identifier for UI
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint('library_id', 'name'),
        Index('idx_labels_library', 'library_id'),
    )


class ComicLabel(Base):
    """Junction table for many-to-many relationship between comics and labels"""
    __tablename__ = 'comic_labels'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    comic_id: Mapped[int] = mapped_column(ForeignKey('comics.id', ondelete='CASCADE'), nullable=False)
    label_id: Mapped[int] = mapped_column(ForeignKey('labels.id', ondelete='CASCADE'), nullable=False)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint('comic_id', 'label_id'),
        Index('idx_comic_labels_comic', 'comic_id'),
        Index('idx_comic_labels_label', 'label_id'),
    )


# ============================================================================
# READING LISTS (YACReader Compatibility)
# ============================================================================

class ReadingList(Base):
    __tablename__ = 'reading_lists'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    library_id: Mapped[int] = mapped_column(ForeignKey('libraries.id', ondelete='CASCADE'), nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        Index('idx_reading_lists_library', 'library_id'),
        Index('idx_reading_lists_user', 'user_id'),
    )


class ReadingListItem(Base):
    """Junction table for many-to-many relationship between reading lists and comics"""
    __tablename__ = 'reading_list_items'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reading_list_id: Mapped[int] = mapped_column(ForeignKey('reading_lists.id', ondelete='CASCADE'), nullable=False)
    comic_id: Mapped[int] = mapped_column(ForeignKey('comics.id', ondelete='CASCADE'), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0)  # Order in the reading list
    added_at: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint('reading_list_id', 'comic_id'),
        Index('idx_reading_list_items_list', 'reading_list_id'),
        Index('idx_reading_list_items_comic', 'comic_id'),
        Index('idx_reading_list_items_position', 'reading_list_id', 'position'),
    )
