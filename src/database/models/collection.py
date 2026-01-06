"""
Collection, Favorite, Label, and ComicLabel models.
"""

from typing import Optional
from sqlalchemy import (
    Integer, String, Text, Boolean,
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


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
