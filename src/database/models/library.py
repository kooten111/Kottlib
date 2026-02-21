"""
Library and Folder models.
"""

import time
import uuid
from typing import Optional, List
from sqlalchemy import (
    Integer, String, Text, JSON,
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Library(Base):
    __tablename__ = 'libraries'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uuid: Mapped[str] = mapped_column(String, unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)
    path: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False, default=lambda: int(time.time()))
    updated_at: Mapped[int] = mapped_column(Integer, nullable=False, default=lambda: int(time.time()))

    scan_status: Mapped[str] = mapped_column(String, default='pending')
    last_scan_started: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_scan_completed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    scanner_type: Mapped[str] = mapped_column(String, default='comic')
    settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    exclude_from_webui: Mapped[bool] = mapped_column(Integer, default=0) # Using Integer for boolean compatibility (0=False, 1=True)
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
