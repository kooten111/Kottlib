"""
Response Builder Utilities for API

Provides utilities for building API responses, particularly for comic metadata
where there are many optional fields that need conditional inclusion.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# Field mappings for comic metadata
# Format: (model_attribute, response_key, transform_function_or_None)
# If transform is None, the value is used as-is

COMIC_PEOPLE_FIELDS: List[Tuple[str, str, Any]] = [
    ('writer', 'writer', None),
    ('artist', 'artist', None),
    ('penciller', 'penciller', None),
    ('inker', 'inker', None),
    ('colorist', 'colorist', None),
    ('letterer', 'letterer', None),
    ('cover_artist', 'cover_artist', None),
    ('editor', 'editor', None),
    ('publisher', 'publisher', None),
]

COMIC_CLASSIFICATION_FIELDS: List[Tuple[str, str, Any]] = [
    ('genre', 'genre', None),
    ('year', 'year', None),
    ('language_iso', 'language_iso', None),
    ('age_rating', 'age_rating', None),
    ('format_type', 'format', None),
    ('is_color', 'is_color', None),
]

COMIC_LIST_FIELDS: List[Tuple[str, str, Any]] = [
    ('characters', 'characters', None),
    ('teams', 'teams', None),
    ('locations', 'locations', None),
]

COMIC_SERIES_FIELDS: List[Tuple[str, str, Any]] = [
    ('story_arc', 'story_arc', None),
    ('arc_number', 'arc_number', None),
    ('arc_count', 'arc_count', None),
    ('alternate_series', 'alternate_series', None),
    ('alternate_number', 'alternate_number', None),
    ('alternate_count', 'alternate_count', None),
    ('count', 'count', None),
]

COMIC_ADDITIONAL_FIELDS: List[Tuple[str, str, Any]] = [
    ('web', 'web', None),
    ('notes', 'notes', None),
    ('review', 'review', None),
]

COMIC_SCANNER_FIELDS: List[Tuple[str, str, Any]] = [
    ('scanner_source', 'scanner_source', None),
    ('scanner_source_id', 'scanner_source_id', None),
    ('scanner_source_url', 'scanner_source_url', None),
    ('scan_confidence', 'scan_confidence', None),
    ('scanned_at', 'scanned_at', None),
    ('tags', 'tags', None),
]


def add_optional_fields(
    response: Dict[str, Any],
    obj: Any,
    field_mappings: List[Tuple[str, str, Any]],
    include_none: bool = False
) -> None:
    """
    Add optional fields to a response dict from an object.

    This replaces the repetitive pattern of:
        if hasattr(obj, 'field') and obj.field:
            response['field'] = obj.field

    Args:
        response: The response dictionary to add fields to
        obj: The source object (e.g., Comic model)
        field_mappings: List of (attr_name, response_key, transform) tuples
        include_none: If True, include fields even if they are None/empty
    """
    for attr_name, response_key, transform in field_mappings:
        value = getattr(obj, attr_name, None)

        # Skip if value is None/empty and we don't want to include None
        if not include_none and not value:
            # Special case: 0 is valid for some numeric fields, None is not
            if value is None or value == '':
                continue
            # For is_color, 0/False should be included
            if attr_name == 'is_color' and value is not None:
                pass  # Include it
            elif not value:
                continue

        # Apply transform if provided
        if transform is not None and value is not None:
            try:
                value = transform(value)
            except Exception as e:
                logger.warning(f"Failed to transform {attr_name}: {e}")
                continue

        response[response_key] = value


def add_description_field(response: Dict[str, Any], comic: Any) -> None:
    """
    Add description/synopsis field with fallback logic.

    Checks 'description' first, then 'synopsis'.
    """
    description = getattr(comic, 'description', None)
    if description:
        response['synopsis'] = description
    else:
        synopsis = getattr(comic, 'synopsis', None)
        if synopsis:
            response['synopsis'] = synopsis


def add_metadata_json_field(response: Dict[str, Any], comic: Any) -> None:
    """
    Add parsed metadata_json field if present.
    """
    metadata_json = getattr(comic, 'metadata_json', None)
    if metadata_json:
        try:
            response['metadata'] = json.loads(metadata_json)
        except Exception as e:
            logger.warning(f"Failed to parse metadata_json for comic {comic.id}: {e}")


def build_comic_metadata_response(comic: Any) -> Dict[str, Any]:
    """
    Build the optional metadata portion of a comic response.

    This extracts all optional metadata fields from a comic model
    and returns them as a dictionary. Fields that are None/empty
    are excluded.

    Args:
        comic: Comic model instance

    Returns:
        Dictionary of optional metadata fields
    """
    metadata: Dict[str, Any] = {}

    # Description with fallback
    add_description_field(metadata, comic)

    # People fields
    add_optional_fields(metadata, comic, COMIC_PEOPLE_FIELDS)

    # Classification fields
    add_optional_fields(metadata, comic, COMIC_CLASSIFICATION_FIELDS)

    # List fields
    add_optional_fields(metadata, comic, COMIC_LIST_FIELDS)

    # Series/Arc fields
    add_optional_fields(metadata, comic, COMIC_SERIES_FIELDS)

    # Additional fields
    add_optional_fields(metadata, comic, COMIC_ADDITIONAL_FIELDS)

    # Metadata JSON
    add_metadata_json_field(metadata, comic)

    # Scanner fields
    add_optional_fields(metadata, comic, COMIC_SCANNER_FIELDS)

    return metadata


def build_full_comic_response(
    comic: Any,
    library: Any,
    api_path: str,
    current_page: int = 0,
    is_read: bool = False
) -> Dict[str, Any]:
    """
    Build a complete comic fullinfo response.

    This creates the full response for the /comic/{id}/fullinfo endpoint,
    combining required fields with optional metadata.

    Args:
        comic: Comic model instance
        library: Library model instance
        api_path: The API path for the comic
        current_page: Current reading page (from progress)
        is_read: Whether the comic has been completed

    Returns:
        Complete comic response dictionary
    """
    # Build base response with required fields
    response = {
        "type": "comic",
        "id": str(comic.id),
        "comic_info_id": str(comic.id),
        "parent_id": str(comic.folder_id) if comic.folder_id is not None else "0",
        "library_id": str(library.id),
        "library_uuid": library.uuid if library else "",
        "file_name": comic.filename,
        "file_size": str(comic.file_size),
        "hash": comic.hash,
        "path": api_path,
        "current_page": current_page,
        "num_pages": comic.num_pages,
        "read": is_read,
        "manga": comic.reading_direction == 'rtl' if hasattr(comic, 'reading_direction') else False,
        "file_type": 1,
        "cover_size_ratio": comic.cover_size_ratio if comic.cover_size_ratio > 0 else 0.67,
        "number": 0,
        "has_been_opened": current_page > 0,
    }

    # Add optional core fields
    if comic.title:
        response["title"] = comic.title
    if comic.series:
        response["series"] = comic.series
    if comic.volume:
        response["volume"] = str(comic.volume)
    if comic.issue_number:
        response["universal_number"] = str(comic.issue_number)

    # Add all optional metadata
    metadata = build_comic_metadata_response(comic)
    response.update(metadata)

    return response
