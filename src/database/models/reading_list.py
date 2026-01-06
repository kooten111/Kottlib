"""
ReadingList and ReadingListItem models.
"""

from typing import Optional
from sqlalchemy import (
    Integer, String, Text, Boolean,
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


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
