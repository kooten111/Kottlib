"""
Enhanced Search with FTS5 and Field-Specific Queries

Provides advanced search capabilities including:
- Full-text search using FTS5 index
- Field-specific queries (e.g., "writer:Stan Lee")
- Dynamic metadata_json search
- Boolean operators (AND, OR, NOT)
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import text, select
from sqlalchemy.orm import Session

from .models import Comic, Series
from .search_index import SearchIndexManager
from .operations.comic import search_comics

logger = logging.getLogger(__name__)


class SearchQuery:
    """Represents a parsed search query"""

    def __init__(self):
        self.field_queries: Dict[str, List[str]] = {}  # field -> [values]
        self.general_terms: List[str] = []  # General search terms (no field specified)
        self.exclude_terms: List[str] = []  # Terms to exclude (NOT)

    def add_field_query(self, field: str, value: str):
        """Add a field-specific query"""
        if field not in self.field_queries:
            self.field_queries[field] = []
        self.field_queries[field].append(value)

    def add_general_term(self, term: str):
        """Add a general search term"""
        if term and term not in self.general_terms:
            self.general_terms.append(term)

    def add_exclude_term(self, term: str):
        """Add a term to exclude"""
        if term and term not in self.exclude_terms:
            self.exclude_terms.append(term)

    def is_empty(self) -> bool:
        """Check if query has any search criteria"""
        return not self.field_queries and not self.general_terms


def parse_search_query(query_str: str) -> SearchQuery:
    """
    Parse search query into structured format

    Supports syntax:
    - Simple terms: "batman"
    - Field-specific: "writer:Stan Lee" or "writer:'Stan Lee'"
    - Multiple fields: "writer:Stan genre:superhero"
    - Exclusions: "-tag:nsfw" or "NOT tag:nsfw"
    - Quoted phrases: "writer:'Frank Miller'"

    Returns:
        SearchQuery object with parsed components
    """
    query = SearchQuery()

    if not query_str or not query_str.strip():
        return query

    # Pattern to match field:value or field:"quoted value"
    field_pattern = r'(-?)(\w+):(?:"([^"]+)"|\'([^\']+)\'|(\S+))'

    # Find all field-specific queries
    matches = list(re.finditer(field_pattern, query_str))

    # Track matched positions to extract general terms
    matched_positions = set()
    for match in matches:
        matched_positions.update(range(match.start(), match.end()))

        exclude = match.group(1) == '-'
        field = match.group(2).lower()
        # Value could be in group 3 (double quotes), 4 (single quotes), or 5 (no quotes)
        value = match.group(3) or match.group(4) or match.group(5)

        if exclude:
            query.add_exclude_term(f"{field}:{value}")
        else:
            query.add_field_query(field, value)

    # Extract general terms (not part of field-specific queries)
    # Remove field queries from original string
    remaining = query_str
    for match in reversed(matches):
        remaining = remaining[:match.start()] + ' ' + remaining[match.end():]

    # Clean up and split general terms
    general_terms = remaining.strip().split()
    for term in general_terms:
        term = term.strip().lower()
        # Skip NOT keyword
        if term == 'not':
            continue
        # Handle -term exclusions
        if term.startswith('-') and len(term) > 1:
            query.add_exclude_term(term[1:])
        elif term:
            query.add_general_term(term)

    return query


def build_fts_query(parsed_query: SearchQuery) -> str:
    """
    Build FTS5 query string from parsed query

    FTS5 query syntax:
    - Simple term: "batman"
    - AND: "batman AND robin"
    - OR: "batman OR superman"
    - NOT: "batman NOT joker"
    - Field-specific: "title:batman"
    - Phrase: '"dark knight"'
    """
    query_parts = []

    # Add field-specific queries
    for field, values in parsed_query.field_queries.items():
        for value in values:
            # Escape special FTS5 characters
            escaped_value = value.replace('"', '""')
            # For multi-word values, use phrase search
            if ' ' in value:
                query_parts.append(f'{field}:"{escaped_value}"')
            else:
                query_parts.append(f'{field}:{escaped_value}')

    # Add general terms
    for term in parsed_query.general_terms:
        escaped_term = term.replace('"', '""')
        query_parts.append(escaped_term)

    # Add exclusions
    for term in parsed_query.exclude_terms:
        escaped_term = term.replace('"', '""')
        query_parts.append(f'NOT {escaped_term}')

    # Join with AND (all terms must match)
    return ' AND '.join(query_parts) if query_parts else ''


def search_with_fts(
    session: Session,
    library_id: int,
    query_str: str,
    limit: int = 100
) -> List[Comic]:
    """
    Search comics using FTS5 index

    Args:
        session: Database session
        library_id: Library to search in
        query_str: Search query string
        limit: Maximum number of results

    Returns:
        List of matching Comics, ordered by relevance
    """
    # Check if FTS index exists
    if not SearchIndexManager.check_fts_exists(session):
        logger.warning("FTS index does not exist, falling back to basic search")
        return search_comics(session, library_id, query_str)

    # Parse query
    parsed_query = parse_search_query(query_str)

    if parsed_query.is_empty():
        return []

    # Build FTS query
    fts_query = build_fts_query(parsed_query)

    logger.debug(f"FTS query: {fts_query}")

    try:
        # Query FTS table
        sql = text("""
            SELECT
                c.id,
                cf.rank
            FROM comics_fts cf
            JOIN comics c ON c.id = cf.comic_id
            WHERE
                cf.library_id = :library_id
                AND comics_fts MATCH :query
            ORDER BY cf.rank
            LIMIT :limit
        """)

        result = session.execute(sql, {
            'library_id': library_id,
            'query': fts_query,
            'limit': limit
        })

        # Get comic IDs
        comic_ids = [row[0] for row in result]

        if not comic_ids:
            return []

        # Fetch full comic objects in the same order
        comics = session.query(Comic).filter(Comic.id.in_(comic_ids)).all()

        # Sort by original FTS rank order
        comics_map = {comic.id: comic for comic in comics}
        sorted_comics = [comics_map[cid] for cid in comic_ids if cid in comics_map]

        return sorted_comics

    except Exception as e:
        logger.error(f"FTS search failed: {e}", exc_info=True)
        # Fall back to basic search
        return search_comics(session, library_id, query_str)


def search_series(
    session: Session,
    library_id: int,
    query_str: str,
    limit: int = 5
) -> List[Series]:
    """
    Search for series in a library

    Args:
        session: Database session
        library_id: Library to search in
        query_str: Search query
        limit: Max results

    Returns:
        List of matching Series
    """
    if not query_str or not query_str.strip():
        return []

    search_pattern = f"%{query_str.strip()}%"
    
    query = session.query(Series).filter(
        Series.library_id == library_id,
        Series.name.ilike(search_pattern)
    ).limit(limit)
    
    return query.all()


def get_searchable_fields(session: Session, library_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Get list of searchable fields for a library

    Returns a dictionary with:
    - Standard fields (title, writer, artist, etc.)
    - Dynamic fields from metadata_json (parodies, circles, etc.)
    - Field value examples

    Args:
        session: Database session
        library_id: Optional library ID to get library-specific fields

    Returns:
        Dictionary of field information
    """
    standard_fields = {
        'title': {'type': 'text', 'description': 'Comic title', 'example': 'Batman'},
        'series': {'type': 'text', 'description': 'Series name', 'example': 'The Dark Knight'},
        'writer': {'type': 'text', 'description': 'Writer name', 'example': 'Stan Lee'},
        'artist': {'type': 'text', 'description': 'Artist name', 'example': 'Jack Kirby'},
        'penciller': {'type': 'text', 'description': 'Penciller name', 'example': 'John Romita'},
        'inker': {'type': 'text', 'description': 'Inker name', 'example': 'Klaus Janson'},
        'colorist': {'type': 'text', 'description': 'Colorist name', 'example': 'Laura Martin'},
        'letterer': {'type': 'text', 'description': 'Letterer name', 'example': 'Chris Eliopoulos'},
        'cover_artist': {'type': 'text', 'description': 'Cover artist name', 'example': 'Alex Ross'},
        'editor': {'type': 'text', 'description': 'Editor name', 'example': 'Tom Brevoort'},
        'publisher': {'type': 'text', 'description': 'Publisher name', 'example': 'Marvel'},
        'genre': {'type': 'text', 'description': 'Genre/categories', 'example': 'superhero'},
        'tags': {'type': 'text', 'description': 'Tags/keywords', 'example': 'action'},
        'characters': {'type': 'text', 'description': 'Character names', 'example': 'Spider-Man'},
        'teams': {'type': 'text', 'description': 'Team names', 'example': 'Avengers'},
        'locations': {'type': 'text', 'description': 'Location names', 'example': 'Gotham'},
        'story_arc': {'type': 'text', 'description': 'Story arc', 'example': 'Civil War'},
        'language_iso': {'type': 'text', 'description': 'Language code', 'example': 'en'},
        'age_rating': {'type': 'text', 'description': 'Age rating', 'example': 'Teen'},
        'imprint': {'type': 'text', 'description': 'Publisher imprint', 'example': 'Vertigo'},
        'format_type': {'type': 'text', 'description': 'Format type', 'example': 'Single Issue'},
        'scanner_source': {'type': 'text', 'description': 'Scanner source', 'example': 'nhentai'},
    }

    # TODO: Extract dynamic fields from metadata_json
    # This would require analyzing actual metadata_json content
    # For now, return standard fields

    return {
        'standard_fields': standard_fields,
        'supports_dynamic_fields': True,
        'dynamic_field_note': 'Scanner-specific fields from metadata_json can be searched using dynamic_metadata field'
    }


def search_comics_advanced(
    session: Session,
    library_id: Optional[int] = None,
    filters: Optional[Dict[str, Any]] = None,
    query_str: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> Tuple[List[Comic], int]:
    """
    Advanced search with filters and pagination

    Args:
        session: Database session
        library_id: Optional library ID filter
        filters: Dictionary of filters (e.g., {'year': 2020, 'genre': 'superhero'})
        query_str: Text search query
        limit: Maximum results to return
        offset: Number of results to skip

    Returns:
        Tuple of (results, total_count)
    """
    # Start with base query
    query = session.query(Comic)

    # Apply library filter
    if library_id is not None:
        query = query.filter(Comic.library_id == library_id)

    # Apply text search if provided
    if query_str and query_str.strip():
        # Use FTS if available
        if SearchIndexManager.check_fts_exists(session):
            fts_comics = search_with_fts(session, library_id, query_str, limit=limit)
            return fts_comics, len(fts_comics)
        else:
            # Fall back to LIKE search
            search_pattern = f"%{query_str.strip()}%"
            query = query.filter(
                (Comic.title.ilike(search_pattern)) |
                (Comic.series.ilike(search_pattern)) |
                (Comic.writer.ilike(search_pattern)) |
                (Comic.artist.ilike(search_pattern))
            )

    # Apply field filters
    if filters:
        for field, value in filters.items():
            if hasattr(Comic, field):
                column = getattr(Comic, field)
                if isinstance(value, list):
                    # OR filter for multiple values
                    query = query.filter(column.in_(value))
                else:
                    query = query.filter(column == value)

    # Get total count
    total_count = query.count()

    # Apply pagination
    results = query.offset(offset).limit(limit).all()

    return results, total_count
