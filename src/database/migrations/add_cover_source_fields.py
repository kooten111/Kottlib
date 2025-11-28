"""
Migration: Add source and source_url columns to covers table

This migration adds:
1. source column: Tracks where the cover came from ('archive', 'mangadex', 'upload')
2. source_url column: Original URL for external covers (nullable)
"""

import logging
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def upgrade(session: Session) -> None:
    """
    Apply migration: Add source and source_url columns to covers table
    """
    logger.info("Starting cover source fields migration...")

    # Check if columns already exist
    result = session.execute(text("PRAGMA table_info(covers)")).fetchall()
    column_names = [row[1] for row in result]

    # Add source column if it doesn't exist
    if 'source' not in column_names:
        logger.info("Adding 'source' column to covers table...")
        session.execute(text(
            "ALTER TABLE covers ADD COLUMN source TEXT NOT NULL DEFAULT 'archive'"
        ))
        session.commit()
        logger.info("Added 'source' column")
    else:
        logger.info("'source' column already exists")

    # Add source_url column if it doesn't exist
    if 'source_url' not in column_names:
        logger.info("Adding 'source_url' column to covers table...")
        session.execute(text(
            "ALTER TABLE covers ADD COLUMN source_url TEXT NULL"
        ))
        session.commit()
        logger.info("Added 'source_url' column")
    else:
        logger.info("'source_url' column already exists")

    logger.info("Cover source fields migration complete!")


def downgrade(session: Session) -> None:
    """
    Rollback migration: Remove source and source_url columns from covers table

    Note: SQLite doesn't support DROP COLUMN directly, so we'd need to recreate
    the table. For simplicity, we'll just log a warning.
    """
    logger.warning(
        "SQLite doesn't support DROP COLUMN directly. "
        "The columns will remain but won't affect functionality."
    )


if __name__ == "__main__":
    # Allow running migration directly
    from ..database import Database
    import sys

    db = Database()
    with db.get_session() as session:
        if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
            downgrade(session)
        else:
            upgrade(session)
