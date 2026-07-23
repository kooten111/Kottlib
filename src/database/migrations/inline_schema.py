"""
Inline schema migrations previously embedded in connection.py.

Idempotent ALTER TABLE / CREATE TABLE steps run on every database init.
"""

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def upgrade(session: Session) -> None:
    """Apply core schema patches for databases created with older code."""
    _migrate_sessions_table(session)
    _migrate_favorites_table(session)
    _migrate_browse_indexes(session)


def _migrate_sessions_table(session: Session) -> None:
    result = session.execute(text("PRAGMA table_info(sessions)")).fetchall()
    column_names = [row[1] for row in result]

    if "device_type" not in column_names:
        logger.info("Adding device_type to sessions table")
        session.execute(text("ALTER TABLE sessions ADD COLUMN device_type TEXT NULL"))

    if "display_type" not in column_names:
        logger.info("Adding display_type to sessions table")
        session.execute(text("ALTER TABLE sessions ADD COLUMN display_type TEXT NULL"))

    if "downloaded_comics" not in column_names:
        logger.info("Adding downloaded_comics to sessions table")
        session.execute(text("ALTER TABLE sessions ADD COLUMN downloaded_comics TEXT NULL"))


def _migrate_favorites_table(session: Session) -> None:
    result = session.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name='favorites'")
    ).fetchone()
    if result:
        return

    logger.info("Creating favorites table")
    session.execute(
        text(
            """
            CREATE TABLE favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                library_id INTEGER NOT NULL,
                comic_id INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (comic_id) REFERENCES comics(id) ON DELETE CASCADE,
                UNIQUE(user_id, comic_id)
            )
            """
        )
    )
    session.execute(text("CREATE INDEX idx_favorites_user ON favorites(user_id)"))
    session.execute(text("CREATE INDEX idx_favorites_comic ON favorites(comic_id)"))


def _migrate_browse_indexes(session: Session) -> None:
    logger.info("Ensuring browse performance indexes")
    session.execute(
        text("CREATE INDEX IF NOT EXISTS idx_comics_folder_created ON comics(folder_id, created_at DESC)")
    )
    session.execute(
        text("CREATE INDEX IF NOT EXISTS idx_comics_library_created ON comics(library_id, created_at DESC)")
    )
    session.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_comics_library_path_created "
            "ON comics(library_id, path, created_at DESC)"
        )
    )
