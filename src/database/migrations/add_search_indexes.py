"""
Migration: Add comprehensive search indexes and FTS5 table

This migration adds:
1. Additional indexes on Comic and Series tables for searchable text fields
2. FTS5 virtual table for full-text search
3. Triggers to keep FTS table in sync with Comic table
"""

import logging
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def upgrade(session: Session) -> None:
    """
    Apply migration: Add search indexes and FTS5 table
    """
    logger.info("Starting search indexing migration...")

    # Step 1: Create new indexes on Comic table (if they don't exist)
    logger.info("Creating Comic table indexes...")
    comic_indexes = [
        "CREATE INDEX IF NOT EXISTS idx_comics_writer ON comics(writer)",
        "CREATE INDEX IF NOT EXISTS idx_comics_artist ON comics(artist)",
        "CREATE INDEX IF NOT EXISTS idx_comics_penciller ON comics(penciller)",
        "CREATE INDEX IF NOT EXISTS idx_comics_inker ON comics(inker)",
        "CREATE INDEX IF NOT EXISTS idx_comics_colorist ON comics(colorist)",
        "CREATE INDEX IF NOT EXISTS idx_comics_letterer ON comics(letterer)",
        "CREATE INDEX IF NOT EXISTS idx_comics_cover_artist ON comics(cover_artist)",
        "CREATE INDEX IF NOT EXISTS idx_comics_editor ON comics(editor)",
        "CREATE INDEX IF NOT EXISTS idx_comics_genre ON comics(genre)",
        "CREATE INDEX IF NOT EXISTS idx_comics_scanner_source ON comics(scanner_source)",
        "CREATE INDEX IF NOT EXISTS idx_comics_story_arc ON comics(story_arc)",
        "CREATE INDEX IF NOT EXISTS idx_comics_language ON comics(language_iso)",
        "CREATE INDEX IF NOT EXISTS idx_comics_age_rating ON comics(age_rating)",
        # Composite indexes
        "CREATE INDEX IF NOT EXISTS idx_comics_library_writer ON comics(library_id, writer)",
        "CREATE INDEX IF NOT EXISTS idx_comics_library_artist ON comics(library_id, artist)",
        "CREATE INDEX IF NOT EXISTS idx_comics_library_genre ON comics(library_id, genre)",
        "CREATE INDEX IF NOT EXISTS idx_comics_library_publisher ON comics(library_id, publisher)",
        "CREATE INDEX IF NOT EXISTS idx_comics_library_year ON comics(library_id, year)",
    ]

    for index_sql in comic_indexes:
        session.execute(text(index_sql))
    session.commit()

    # Step 2: Create new indexes on Series table
    logger.info("Creating Series table indexes...")
    series_indexes = [
        "CREATE INDEX IF NOT EXISTS idx_series_writer ON series(writer)",
        "CREATE INDEX IF NOT EXISTS idx_series_artist ON series(artist)",
        "CREATE INDEX IF NOT EXISTS idx_series_genre ON series(genre)",
        "CREATE INDEX IF NOT EXISTS idx_series_publisher ON series(publisher)",
        "CREATE INDEX IF NOT EXISTS idx_series_status ON series(status)",
        "CREATE INDEX IF NOT EXISTS idx_series_scanner_source ON series(scanner_source)",
        # Composite indexes
        "CREATE INDEX IF NOT EXISTS idx_series_library_writer ON series(library_id, writer)",
        "CREATE INDEX IF NOT EXISTS idx_series_library_artist ON series(library_id, artist)",
        "CREATE INDEX IF NOT EXISTS idx_series_library_genre ON series(library_id, genre)",
        "CREATE INDEX IF NOT EXISTS idx_series_library_publisher ON series(library_id, publisher)",
    ]

    for index_sql in series_indexes:
        session.execute(text(index_sql))
    session.commit()

    # Step 3: Create FTS5 virtual table
    logger.info("Creating FTS5 virtual table...")
    from ..search_index import SearchIndexManager

    # Check if FTS table already exists
    if SearchIndexManager.check_fts_exists(session):
        logger.info("FTS table already exists, dropping and recreating...")
        session.execute(text("DROP TABLE IF EXISTS comics_fts"))
        session.commit()

    SearchIndexManager.create_fts_table(session)

    # Step 4: Create triggers to keep FTS in sync
    logger.info("Creating FTS sync triggers...")

    # Trigger: INSERT
    session.execute(text("""
        CREATE TRIGGER IF NOT EXISTS comics_fts_insert
        AFTER INSERT ON comics
        BEGIN
            INSERT INTO comics_fts (
                comic_id, library_id,
                title, series, filename,
                writer, artist, penciller, inker, colorist, letterer, cover_artist, editor, publisher,
                description, genre, tags, characters, teams, locations, story_arc,
                language_iso, age_rating, imprint, format_type,
                dynamic_metadata, scanner_source
            ) VALUES (
                NEW.id, NEW.library_id,
                NEW.title, NEW.series, NEW.filename,
                NEW.writer, NEW.artist, NEW.penciller, NEW.inker, NEW.colorist, NEW.letterer,
                NEW.cover_artist, NEW.editor, NEW.publisher,
                NEW.description, NEW.genre, NEW.tags, NEW.characters, NEW.teams, NEW.locations, NEW.story_arc,
                NEW.language_iso, NEW.age_rating, NEW.imprint, NEW.format_type,
                COALESCE(NEW.metadata_json, ''), NEW.scanner_source
            );
        END;
    """))

    # Trigger: UPDATE
    session.execute(text("""
        CREATE TRIGGER IF NOT EXISTS comics_fts_update
        AFTER UPDATE ON comics
        BEGIN
            UPDATE comics_fts SET
                library_id = NEW.library_id,
                title = NEW.title,
                series = NEW.series,
                filename = NEW.filename,
                writer = NEW.writer,
                artist = NEW.artist,
                penciller = NEW.penciller,
                inker = NEW.inker,
                colorist = NEW.colorist,
                letterer = NEW.letterer,
                cover_artist = NEW.cover_artist,
                editor = NEW.editor,
                publisher = NEW.publisher,
                description = NEW.description,
                genre = NEW.genre,
                tags = NEW.tags,
                characters = NEW.characters,
                teams = NEW.teams,
                locations = NEW.locations,
                story_arc = NEW.story_arc,
                language_iso = NEW.language_iso,
                age_rating = NEW.age_rating,
                imprint = NEW.imprint,
                format_type = NEW.format_type,
                dynamic_metadata = COALESCE(NEW.metadata_json, ''),
                scanner_source = NEW.scanner_source
            WHERE comic_id = NEW.id;
        END;
    """))

    # Trigger: DELETE
    session.execute(text("""
        CREATE TRIGGER IF NOT EXISTS comics_fts_delete
        AFTER DELETE ON comics
        BEGIN
            DELETE FROM comics_fts WHERE comic_id = OLD.id;
        END;
    """))

    session.commit()

    # Step 5: Populate FTS table with existing data
    logger.info("Populating FTS table with existing comics...")
    indexed_count = SearchIndexManager.reindex_all_comics(session)
    logger.info(f"Migration complete! Indexed {indexed_count} comics.")


def downgrade(session: Session) -> None:
    """
    Rollback migration: Remove search indexes and FTS5 table
    """
    logger.info("Rolling back search indexing migration...")

    # Drop FTS triggers
    session.execute(text("DROP TRIGGER IF EXISTS comics_fts_insert"))
    session.execute(text("DROP TRIGGER IF EXISTS comics_fts_update"))
    session.execute(text("DROP TRIGGER IF EXISTS comics_fts_delete"))

    # Drop FTS table
    session.execute(text("DROP TABLE IF EXISTS comics_fts"))

    # Note: We don't drop the regular indexes as they're beneficial for performance
    # and don't have significant downsides

    session.commit()
    logger.info("Migration rollback complete!")


if __name__ == "__main__":
    # Allow running migration directly
    from ..database import DatabaseManager
    import sys

    db = DatabaseManager()
    with db.get_session() as session:
        if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
            downgrade(session)
        else:
            upgrade(session)
