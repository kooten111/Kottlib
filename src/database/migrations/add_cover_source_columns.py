"""
Migration: Add external cover source columns to covers table

This migration adds:
1. source column - identifies where the cover came from ('archive', 'mangadex', etc.)
2. source_url column - original URL for external covers
3. source_id column - provider's ID for the cover
"""

import logging
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def upgrade(session: Session) -> None:
    """
    Apply migration: Add source columns to covers table
    """
    logger.info("Starting cover source columns migration...")

    # SQLite doesn't support IF NOT EXISTS for columns, so we need to check first
    try:
        # Check if source column exists
        result = session.execute(text("PRAGMA table_info(covers)"))
        columns = [row[1] for row in result.fetchall()]

        if 'source' not in columns:
            logger.info("Adding 'source' column to covers table...")
            session.execute(
                text("ALTER TABLE covers ADD COLUMN source VARCHAR DEFAULT 'archive'")
            )
        else:
            logger.info("Column 'source' already exists, skipping...")

        if 'source_url' not in columns:
            logger.info("Adding 'source_url' column to covers table...")
            session.execute(
                text("ALTER TABLE covers ADD COLUMN source_url VARCHAR")
            )
        else:
            logger.info("Column 'source_url' already exists, skipping...")

        if 'source_id' not in columns:
            logger.info("Adding 'source_id' column to covers table...")
            session.execute(
                text("ALTER TABLE covers ADD COLUMN source_id VARCHAR")
            )
        else:
            logger.info("Column 'source_id' already exists, skipping...")

        session.commit()
        logger.info("Cover source columns migration complete!")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        session.rollback()
        raise


def downgrade(session: Session) -> None:
    """
    Rollback migration: Remove source columns from covers table

    Note: SQLite doesn't support DROP COLUMN in older versions.
    This would require recreating the table.
    """
    logger.warning(
        "SQLite doesn't support dropping columns easily. "
        "The source columns will remain in the table but won't be used."
    )
    # No action needed - columns will just be unused
    pass


def check_migration_needed(session: Session) -> bool:
    """
    Check if migration is needed
    """
    try:
        result = session.execute(text("PRAGMA table_info(covers)"))
        columns = [row[1] for row in result.fetchall()]
        return 'source' not in columns
    except Exception:
        return False


if __name__ == "__main__":
    # Allow running migration directly
    from ..database import Database
    import sys

    db = Database()
    with db.get_session() as session:
        if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
            downgrade(session)
        elif len(sys.argv) > 1 and sys.argv[1] == "check":
            needed = check_migration_needed(session)
            print(f"Migration needed: {needed}")
        else:
            upgrade(session)
