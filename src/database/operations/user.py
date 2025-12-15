"""
User database operations.
"""

from typing import Optional

from sqlalchemy.orm import Session

from ..models import User


def get_user_by_username(session: Session, username: str) -> Optional[User]:
    """Get user by username."""
    return session.query(User).filter_by(username=username).first()


def get_user_by_id(session: Session, user_id: int) -> Optional[User]:
    """Get user by ID."""
    return session.query(User).filter_by(id=user_id).first()
