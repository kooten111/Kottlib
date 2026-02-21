"""
Comic and Cover models.
"""

from typing import Optional, List
from sqlalchemy import (
    Integer, String, Text, Boolean, Float,
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


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

    @property
    def file_hash(self) -> str:
        """Backward-compatible alias for hash."""
        return self.hash

    @file_hash.setter
    def file_hash(self, value: str) -> None:
        self.hash = value

    @property
    def summary(self) -> Optional[str]:
        """Backward-compatible alias for description."""
        return self.description

    @summary.setter
    def summary(self, value: Optional[str]) -> None:
        self.description = value


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
