"""
User database operations.
"""

import hashlib
import secrets
from typing import Optional

from sqlalchemy.orm import Session

from ..models import User

# PBKDF2 parameters
_HASH_ALGORITHM = "sha256"
_ITERATIONS = 600_000  # OWASP recommendation for PBKDF2-SHA256


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-SHA256 with a random salt.

    Returns a string in the format ``pbkdf2:sha256:iterations$salt$hash``.
    """
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        _HASH_ALGORITHM,
        password.encode("utf-8"),
        salt.encode("utf-8"),
        _ITERATIONS,
    )
    return f"pbkdf2:{_HASH_ALGORITHM}:{_ITERATIONS}${salt}${dk.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a PBKDF2-SHA256 hash.

    Also accepts legacy plaintext hashes for backwards compatibility
    (e.g. ``'changeme'``), returning True on exact match so that
    existing databases still work after the upgrade.
    """
    if "$" not in password_hash:
        # Legacy plaintext fallback — matches old 'changeme' values
        return secrets.compare_digest(password, password_hash)

    try:
        method_info, salt, stored_hash = password_hash.split("$")
        _, algo, iterations_str = method_info.split(":")
        dk = hashlib.pbkdf2_hmac(
            algo,
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations_str),
        )
        return secrets.compare_digest(dk.hex(), stored_hash)
    except (ValueError, KeyError):
        return False


def get_user_by_username(session: Session, username: str) -> Optional[User]:
    """Get user by username."""
    return session.query(User).filter_by(username=username).first()


def get_user_by_id(session: Session, user_id: int) -> Optional[User]:
    """Get user by ID."""
    return session.query(User).filter_by(id=user_id).first()
