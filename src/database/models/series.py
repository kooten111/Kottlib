"""
Series model.
"""

from typing import Optional
from sqlalchemy import (
    Integer, String, Text, Float,
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


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
