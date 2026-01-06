"""
User and Session models.
"""

from typing import Optional, List
from sqlalchemy import (
    Integer, String, Text, Boolean,
    ForeignKey, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


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
