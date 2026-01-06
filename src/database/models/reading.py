"""
ReadingProgress model.
"""

from typing import Optional
from sqlalchemy import (
    Integer, Float, Boolean,
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


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
