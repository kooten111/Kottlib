"""
Migration: Add folders.last_content_at for fast "updated" browse sorting.

Backfills from MAX(comics.created_at) under each folder path, then indexes
(library_id, last_content_at DESC).
"""

import logging
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def upgrade(session: Session) -> None:
    logger.info("Starting folders.last_content_at migration...")

    result = session.execute(text("PRAGMA table_info(folders)"))
    columns = [row[1] for row in result.fetchall()]

    if "last_content_at" not in columns:
        logger.info("Adding last_content_at column to folders...")
        session.execute(
            text("ALTER TABLE folders ADD COLUMN last_content_at INTEGER")
        )
    else:
        logger.info("Column last_content_at already exists, skipping add...")

    # Backfill from descendant comics (path prefix), falling back to folder created_at.
    session.execute(
        text(
            """
            UPDATE folders
            SET last_content_at = COALESCE(
                (
                    SELECT MAX(comics.created_at)
                    FROM comics
                    WHERE comics.library_id = folders.library_id
                      AND (
                          comics.folder_id = folders.id
                          OR comics.path LIKE folders.path || '/%'
                      )
                ),
                folders.created_at
            )
            WHERE last_content_at IS NULL
            """
        )
    )

    session.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS idx_folders_library_last_content
            ON folders(library_id, last_content_at DESC)
            """
        )
    )

    logger.info("folders.last_content_at migration complete!")


def downgrade(session: Session) -> None:
    logger.warning(
        "SQLite cannot easily drop columns; last_content_at will remain unused."
    )
