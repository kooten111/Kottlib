"""
Session Management Middleware

Handles YACReader session management for mobile app compatibility.
Sessions are tracked via the 'yacread_session' cookie.
"""

import logging
from typing import Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from ...database import (
    get_session_by_id,
    update_session_activity,
    cleanup_expired_sessions,
    create_session,
    get_user_by_username,
)

logger = logging.getLogger(__name__)


class SessionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle YACReader sessions

    - Reads 'yacread_session' cookie from requests
    - Validates sessions and extends their expiry on activity
    - Cleans up expired sessions periodically
    - Creates sessions for new connections
    """

    def __init__(self, app, auto_create_session: bool = True):
        super().__init__(app)
        self.auto_create_session = auto_create_session
        self._cleanup_counter = 0
        self._cleanup_interval = 100  # Clean up every 100 requests

    async def dispatch(self, request: Request, call_next) -> StarletteResponse:
        """Process request and manage session"""

        # Get session ID from cookie
        session_id = request.cookies.get('yacread_session')

        # Attach session to request state
        request.state.session_id = session_id
        request.state.user_id = None
        request.state.db_session = None

        # Validate and refresh session if it exists
        if session_id:
            db = request.app.state.db
            with db.get_session() as db_session:
                session = get_session_by_id(db_session, session_id)

                if session:
                    # Valid session found
                    request.state.user_id = session.user_id
                    request.state.db_session = session

                    # Update last activity timestamp
                    try:
                        update_session_activity(db_session, session_id)
                    except Exception as e:
                        logger.warning(f"Failed to update session activity: {e}")

                    logger.debug(f"Session {session_id[:8]}... validated for user {session.user_id}")
                else:
                    # Invalid/expired session
                    logger.debug(f"Session {session_id[:8]}... not found or expired")
                    request.state.session_id = None

        # Create new session if auto-create is enabled and no valid session exists
        if self.auto_create_session and not request.state.session_id:
            # Only create sessions for certain endpoints (e.g., library access)
            if should_create_session(request):
                new_session_id = await self._create_default_session(request)
                if new_session_id:
                    request.state.session_id = new_session_id
                    logger.info(f"Created new session {new_session_id[:8]}... for {request.client.host}")

        # Periodic cleanup of expired sessions
        self._cleanup_counter += 1
        if self._cleanup_counter >= self._cleanup_interval:
            self._cleanup_counter = 0
            try:
                db = request.app.state.db
                with db.get_session() as db_session:
                    cleanup_expired_sessions(db_session)
            except Exception as e:
                logger.error(f"Failed to cleanup expired sessions: {e}")

        # Process request
        response = await call_next(request)

        # Set session cookie if new session was created
        if request.state.session_id and session_id != request.state.session_id:
            # New session was created, set cookie
            response.set_cookie(
                key='yacread_session',
                value=request.state.session_id,
                max_age=86400,  # 24 hours
                httponly=True,
                samesite='lax'
            )
            logger.debug(f"Set session cookie: {request.state.session_id[:8]}...")

        return response

    async def _create_default_session(self, request: Request) -> Optional[str]:
        """Create a session for the default admin user"""
        try:
            db = request.app.state.db
            with db.get_session() as db_session:
                # Get default user (admin)
                user = get_user_by_username(db_session, 'admin')
                if not user:
                    logger.warning("Cannot create session: admin user not found")
                    return None

                # Create session
                user_agent = request.headers.get('user-agent')
                ip_address = request.client.host if request.client else None

                session = create_session(
                    db_session,
                    user.id,
                    user_agent=user_agent,
                    ip_address=ip_address,
                    expires_in=86400  # 24 hours
                )

                return session.id
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return None


def should_create_session(request: Request) -> bool:
    """
    Determine if a session should be auto-created for this request

    Only create sessions for:
    - Library browsing endpoints
    - Comic reading endpoints
    - Not for static assets, version checks, etc.
    """
    path = request.url.path

    # Create sessions for library/comic access
    if '/library/' in path or '/libraries' in path:
        return True

    # Create sessions for v2 API endpoints (except version)
    if path.startswith('/v2/') and path != '/v2/version':
        return True

    # Don't create for version checks, covers, static assets
    if path in ['/v2/version', '/version', '/']:
        return False

    return False


def get_current_user_id(request: Request) -> Optional[int]:
    """
    Helper function to get current user ID from request

    Usage in route handlers:
        user_id = get_current_user_id(request)
        if not user_id:
            raise HTTPException(status_code=401, detail="Not authenticated")
    """
    return getattr(request.state, 'user_id', None)


def get_current_session_id(request: Request) -> Optional[str]:
    """Helper function to get current session ID from request"""
    return getattr(request.state, 'session_id', None)


def require_session(request: Request) -> str:
    """
    Require a valid session, raise exception if not found

    Usage in route handlers:
        session_id = require_session(request)
    """
    from fastapi import HTTPException

    session_id = get_current_session_id(request)
    if not session_id:
        raise HTTPException(status_code=401, detail="Session required")
    return session_id


def require_user(request: Request) -> int:
    """
    Require a valid user, raise exception if not found

    Usage in route handlers:
        user_id = require_user(request)
    """
    from fastapi import HTTPException

    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user_id
