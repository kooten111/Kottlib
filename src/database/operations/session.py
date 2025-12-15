"""
Session database operations.
"""

import time
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from ..models import Session as DBSession


def create_session(
    session: Session,
    user_id: int,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
    expires_in: int = 86400  # 24 hours
) -> DBSession:
    """Create a new session."""
    now = int(time.time())

    db_session = DBSession(
        id=str(uuid.uuid4()),
        user_id=user_id,
        user_agent=user_agent,
        ip_address=ip_address,
        created_at=now,
        last_activity_at=now,
        expires_at=now + expires_in
    )

    session.add(db_session)
    session.flush()  # Flush to get the ID without committing

    return db_session


def get_session_by_id(session: Session, session_id: str) -> Optional[DBSession]:
    """Get session by ID."""
    return session.query(DBSession).filter_by(id=session_id).first()


def update_session_activity(session: Session, session_id: str):
    """Update session last activity timestamp."""
    db_session = get_session_by_id(session, session_id)
    if db_session:
        db_session.last_activity_at = int(time.time())
        session.flush()  # Flush changes without committing


def cleanup_expired_sessions(session: Session):
    """Remove expired sessions."""
    now = int(time.time())
    session.query(DBSession).filter(DBSession.expires_at < now).delete()
    session.flush()  # Flush changes without committing
