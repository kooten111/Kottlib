"""
Session database operations.
"""

import time
import uuid
from typing import Optional, Union

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


def update_session_activity(
    session: Session,
    session_or_id: Union[DBSession, str],
    throttle_seconds: int = 0,
) -> None:
    """
    Update session last activity timestamp.

    Prefer passing the already-loaded DBSession to avoid a second SELECT.
    When throttle_seconds > 0, skip the write if last_activity_at is recent.
    """
    if isinstance(session_or_id, DBSession):
        db_session = session_or_id
    else:
        db_session = get_session_by_id(session, session_or_id)

    if not db_session:
        return

    now = int(time.time())
    if throttle_seconds > 0 and db_session.last_activity_at:
        if now - db_session.last_activity_at < throttle_seconds:
            return

    db_session.last_activity_at = now
    session.flush()


def cleanup_expired_sessions(session: Session):
    """Remove expired sessions."""
    now = int(time.time())
    session.query(DBSession).filter(DBSession.expires_at < now).delete()
    session.flush()  # Flush changes without committing
