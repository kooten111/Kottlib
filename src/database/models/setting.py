"""
Setting model.
"""

from typing import Optional
from sqlalchemy import (
    Integer, String, Text,
    Index
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Setting(Base):
    """Application settings stored in database"""
    __tablename__ = 'settings'

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    value_type: Mapped[str] = mapped_column(String, default='string')  # string, int, float, bool, json
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        Index('idx_settings_key', 'key'),
    )
