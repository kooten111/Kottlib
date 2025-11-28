"""
Full-Text Search Index Management

Provides FTS5-based full-text search capabilities for flexible metadata search.
Automatically indexes both standard fields and dynamic metadata_json content.
"""

from typing import Optional, Dict, Any, List
from sqlalchemy import text, select
from sqlalchemy.orm import Session
import json
import logging

logger = logging.getLogger(__name__)


class SearchIndexManager:
    """Manages FTS5 full-text search index for comics metadata"""

    @staticmethod
    def create_fts_table(session: Session) -> None:
        """
        Create FTS5 virtual table for full-text search

        This creates a virtual table that indexes:
        - All standard metadata fields (title, series, writer, artist, etc.)
        - Dynamic metadata from metadata_json (extracted and flattened)
        """
        # Drop existing FTS table if it exists
        session.execute(text("DROP TABLE IF EXISTS comics_fts"))

        # Create FTS5 virtual table with all searchable fields
        create_fts_sql = text("""
            CREATE VIRTUAL TABLE comics_fts USING fts5(
                comic_id UNINDEXED,
                library_id UNINDEXED,

                -- Core metadata (indexed for full-text search)
                title,
                series,
                filename,

                -- People
                writer,
                artist,
                penciller,
                inker,
                colorist,
                letterer,
                cover_artist,
                editor,
                publisher,

                -- Content
                description,
                genre,
                tags,
                characters,
                teams,
                locations,
                story_arc,

                -- Additional fields
                language_iso,
                age_rating,
                imprint,
                format_type,

                -- Dynamic metadata (extracted from metadata_json)
                -- This will contain flattened key-value pairs from JSON
                dynamic_metadata,

                -- Scanner info
                scanner_source,

                -- Tokenizer configuration
                tokenize = 'porter unicode61 remove_diacritics 2'
            )
        """)

        session.execute(create_fts_sql)
        session.commit()
        logger.info("Created FTS5 search index table")

    @staticmethod
    def extract_dynamic_metadata(metadata_json: Optional[str]) -> str:
        """
        Extract and flatten metadata_json into searchable text

        Converts JSON like:
        {"parodies": ["touhou"], "artists": ["zun"], "tags": ["fantasy"]}

        Into searchable text:
        "parodies:touhou artists:zun tags:fantasy"

        This allows searching for "parodies:touhou" or just "touhou"
        """
        if not metadata_json:
            return ""

        try:
            data = json.loads(metadata_json)
            if not isinstance(data, dict):
                return ""

            # Flatten the JSON into searchable key:value pairs
            searchable_parts = []

            for key, value in data.items():
                key_lower = key.lower()

                # Handle different value types
                if isinstance(value, list):
                    # For lists, create "key:item" for each item
                    for item in value:
                        if isinstance(item, (str, int, float)):
                            searchable_parts.append(f"{key_lower}:{item}")
                            # Also add just the value for general search
                            searchable_parts.append(str(item))
                elif isinstance(value, (str, int, float, bool)):
                    # For scalar values
                    searchable_parts.append(f"{key_lower}:{value}")
                    searchable_parts.append(str(value))
                elif isinstance(value, dict):
                    # For nested objects, flatten one level
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, (str, int, float)):
                            searchable_parts.append(f"{key_lower}.{sub_key.lower()}:{sub_value}")
                            searchable_parts.append(str(sub_value))

            return " ".join(searchable_parts)

        except (json.JSONDecodeError, AttributeError, TypeError) as e:
            logger.warning(f"Failed to parse metadata_json: {e}")
            return ""

    @staticmethod
    def index_comic(session: Session, comic_id: int, comic_data: Dict[str, Any]) -> None:
        """
        Index a single comic in the FTS table

        Args:
            session: Database session
            comic_id: Comic ID
            comic_data: Dictionary containing comic metadata
        """
        # Extract dynamic metadata
        dynamic_metadata = SearchIndexManager.extract_dynamic_metadata(
            comic_data.get('metadata_json')
        )

        # Build insert query
        insert_sql = text("""
            INSERT INTO comics_fts (
                comic_id, library_id,
                title, series, filename,
                writer, artist, penciller, inker, colorist, letterer, cover_artist, editor, publisher,
                description, genre, tags, characters, teams, locations, story_arc,
                language_iso, age_rating, imprint, format_type,
                dynamic_metadata, scanner_source
            ) VALUES (
                :comic_id, :library_id,
                :title, :series, :filename,
                :writer, :artist, :penciller, :inker, :colorist, :letterer, :cover_artist, :editor, :publisher,
                :description, :genre, :tags, :characters, :teams, :locations, :story_arc,
                :language_iso, :age_rating, :imprint, :format_type,
                :dynamic_metadata, :scanner_source
            )
        """)

        session.execute(insert_sql, {
            'comic_id': comic_id,
            'library_id': comic_data.get('library_id'),
            'title': comic_data.get('title'),
            'series': comic_data.get('series'),
            'filename': comic_data.get('filename'),
            'writer': comic_data.get('writer'),
            'artist': comic_data.get('artist'),
            'penciller': comic_data.get('penciller'),
            'inker': comic_data.get('inker'),
            'colorist': comic_data.get('colorist'),
            'letterer': comic_data.get('letterer'),
            'cover_artist': comic_data.get('cover_artist'),
            'editor': comic_data.get('editor'),
            'publisher': comic_data.get('publisher'),
            'description': comic_data.get('description'),
            'genre': comic_data.get('genre'),
            'tags': comic_data.get('tags'),
            'characters': comic_data.get('characters'),
            'teams': comic_data.get('teams'),
            'locations': comic_data.get('locations'),
            'story_arc': comic_data.get('story_arc'),
            'language_iso': comic_data.get('language_iso'),
            'age_rating': comic_data.get('age_rating'),
            'imprint': comic_data.get('imprint'),
            'format_type': comic_data.get('format_type'),
            'dynamic_metadata': dynamic_metadata,
            'scanner_source': comic_data.get('scanner_source')
        })
        session.commit()

    @staticmethod
    def reindex_all_comics(session: Session) -> int:
        """
        Rebuild the entire FTS index from scratch

        Returns:
            Number of comics indexed
        """
        from .models import Comic

        logger.info("Starting full FTS reindex...")

        # Clear existing FTS data
        session.execute(text("DELETE FROM comics_fts"))
        session.commit()

        # Get all comics
        comics = session.query(Comic).all()

        indexed_count = 0
        for comic in comics:
            comic_data = {
                'library_id': comic.library_id,
                'title': comic.title,
                'series': comic.series,
                'filename': comic.filename,
                'writer': comic.writer,
                'artist': comic.artist,
                'penciller': comic.penciller,
                'inker': comic.inker,
                'colorist': comic.colorist,
                'letterer': comic.letterer,
                'cover_artist': comic.cover_artist,
                'editor': comic.editor,
                'publisher': comic.publisher,
                'description': comic.description,
                'genre': comic.genre,
                'tags': comic.tags,
                'characters': comic.characters,
                'teams': comic.teams,
                'locations': comic.locations,
                'story_arc': comic.story_arc,
                'language_iso': comic.language_iso,
                'age_rating': comic.age_rating,
                'imprint': comic.imprint,
                'format_type': comic.format_type,
                'metadata_json': comic.metadata_json,
                'scanner_source': comic.scanner_source
            }

            SearchIndexManager.index_comic(session, comic.id, comic_data)
            indexed_count += 1

            if indexed_count % 100 == 0:
                logger.info(f"Indexed {indexed_count} comics...")

        logger.info(f"FTS reindex complete. Indexed {indexed_count} comics.")
        return indexed_count

    @staticmethod
    def update_comic_index(session: Session, comic_id: int, comic_data: Dict[str, Any]) -> None:
        """Update FTS index for a single comic"""
        # Delete existing entry
        session.execute(
            text("DELETE FROM comics_fts WHERE comic_id = :comic_id"),
            {'comic_id': comic_id}
        )
        # Reindex
        SearchIndexManager.index_comic(session, comic_id, comic_data)

    @staticmethod
    def delete_comic_index(session: Session, comic_id: int) -> None:
        """Remove comic from FTS index"""
        session.execute(
            text("DELETE FROM comics_fts WHERE comic_id = :comic_id"),
            {'comic_id': comic_id}
        )
        session.commit()

    @staticmethod
    def check_fts_exists(session: Session) -> bool:
        """Check if FTS table exists"""
        result = session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='comics_fts'")
        ).fetchone()
        return result is not None
