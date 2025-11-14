"""
Metadata Schema Definition

Defines what metadata fields each scanner can provide and how they map to
the Comic database model.
"""

from enum import Enum
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field


class MetadataField(str, Enum):
    """Standard metadata fields that scanners can provide"""

    # Core fields
    TITLE = "title"
    SERIES = "series"
    VOLUME = "volume"
    ISSUE_NUMBER = "issue_number"
    YEAR = "year"
    DESCRIPTION = "description"

    # People
    WRITER = "writer"
    ARTIST = "artist"
    PENCILLER = "penciller"
    INKER = "inker"
    COLORIST = "colorist"
    LETTERER = "letterer"
    COVER_ARTIST = "cover_artist"
    EDITOR = "editor"
    PUBLISHER = "publisher"

    # Series/Arc
    STORY_ARC = "story_arc"
    ARC_NUMBER = "arc_number"
    ARC_COUNT = "arc_count"
    ALTERNATE_SERIES = "alternate_series"
    ALTERNATE_NUMBER = "alternate_number"
    ALTERNATE_COUNT = "alternate_count"

    # Classification
    GENRE = "genre"
    LANGUAGE_ISO = "language_iso"
    AGE_RATING = "age_rating"
    IMPRINT = "imprint"
    FORMAT_TYPE = "format_type"
    IS_COLOR = "is_color"

    # Lists
    CHARACTERS = "characters"
    TEAMS = "teams"
    LOCATIONS = "locations"
    TAGS = "tags"

    # Links
    WEB_LINK = "web"
    MANGA_PLUS_URL = "manga_plus_url"

    # Counts
    PAGE_COUNT = "page_count"
    COUNT = "count"  # Total issues in series

    # Additional
    NOTES = "notes"
    REVIEW = "review"


class FieldCategory(str, Enum):
    """Categories for grouping metadata fields"""
    CORE = "core"
    PEOPLE = "people"
    SERIES = "series"
    CLASSIFICATION = "classification"
    LISTS = "lists"
    LINKS = "links"
    ADDITIONAL = "additional"


@dataclass
class FieldDefinition:
    """Definition of a metadata field"""
    field: MetadataField
    category: FieldCategory
    display_name: str
    description: str
    data_type: str  # 'string', 'integer', 'float', 'boolean', 'list'
    db_column: Optional[str] = None  # Maps to Comic model column
    is_list: bool = False  # If true, expects array of values
    separator: Optional[str] = None  # For joining list items (e.g., ', ')


# Field definitions with database mappings
FIELD_DEFINITIONS: Dict[MetadataField, FieldDefinition] = {
    # Core fields
    MetadataField.TITLE: FieldDefinition(
        MetadataField.TITLE, FieldCategory.CORE,
        "Title", "Comic title",
        "string", "title"
    ),
    MetadataField.SERIES: FieldDefinition(
        MetadataField.SERIES, FieldCategory.CORE,
        "Series", "Series name",
        "string", "series"
    ),
    MetadataField.VOLUME: FieldDefinition(
        MetadataField.VOLUME, FieldCategory.CORE,
        "Volume", "Volume number",
        "integer", "volume"
    ),
    MetadataField.ISSUE_NUMBER: FieldDefinition(
        MetadataField.ISSUE_NUMBER, FieldCategory.CORE,
        "Issue #", "Issue number",
        "float", "issue_number"
    ),
    MetadataField.YEAR: FieldDefinition(
        MetadataField.YEAR, FieldCategory.CORE,
        "Year", "Publication year",
        "integer", "year"
    ),
    MetadataField.DESCRIPTION: FieldDefinition(
        MetadataField.DESCRIPTION, FieldCategory.CORE,
        "Description", "Comic description/summary",
        "string", "description"
    ),

    # People
    MetadataField.WRITER: FieldDefinition(
        MetadataField.WRITER, FieldCategory.PEOPLE,
        "Writer", "Writer(s)",
        "string", "writer"
    ),
    MetadataField.ARTIST: FieldDefinition(
        MetadataField.ARTIST, FieldCategory.PEOPLE,
        "Artist", "Artist(s)",
        "string", "artist"
    ),
    MetadataField.PENCILLER: FieldDefinition(
        MetadataField.PENCILLER, FieldCategory.PEOPLE,
        "Penciller", "Penciller(s)",
        "string", "penciller"
    ),
    MetadataField.INKER: FieldDefinition(
        MetadataField.INKER, FieldCategory.PEOPLE,
        "Inker", "Inker(s)",
        "string", "inker"
    ),
    MetadataField.COLORIST: FieldDefinition(
        MetadataField.COLORIST, FieldCategory.PEOPLE,
        "Colorist", "Colorist(s)",
        "string", "colorist"
    ),
    MetadataField.LETTERER: FieldDefinition(
        MetadataField.LETTERER, FieldCategory.PEOPLE,
        "Letterer", "Letterer(s)",
        "string", "letterer"
    ),
    MetadataField.COVER_ARTIST: FieldDefinition(
        MetadataField.COVER_ARTIST, FieldCategory.PEOPLE,
        "Cover Artist", "Cover artist(s)",
        "string", "cover_artist"
    ),
    MetadataField.EDITOR: FieldDefinition(
        MetadataField.EDITOR, FieldCategory.PEOPLE,
        "Editor", "Editor(s)",
        "string", "editor"
    ),
    MetadataField.PUBLISHER: FieldDefinition(
        MetadataField.PUBLISHER, FieldCategory.PEOPLE,
        "Publisher", "Publisher",
        "string", "publisher"
    ),

    # Series/Arc
    MetadataField.STORY_ARC: FieldDefinition(
        MetadataField.STORY_ARC, FieldCategory.SERIES,
        "Story Arc", "Story arc name",
        "string", "story_arc"
    ),
    MetadataField.ARC_NUMBER: FieldDefinition(
        MetadataField.ARC_NUMBER, FieldCategory.SERIES,
        "Arc Number", "Position in arc",
        "string", "arc_number"
    ),
    MetadataField.ARC_COUNT: FieldDefinition(
        MetadataField.ARC_COUNT, FieldCategory.SERIES,
        "Arc Count", "Total issues in arc",
        "integer", "arc_count"
    ),

    # Classification
    MetadataField.GENRE: FieldDefinition(
        MetadataField.GENRE, FieldCategory.CLASSIFICATION,
        "Genre", "Genre(s)",
        "string", "genre"
    ),
    MetadataField.LANGUAGE_ISO: FieldDefinition(
        MetadataField.LANGUAGE_ISO, FieldCategory.CLASSIFICATION,
        "Language", "Language code (ISO 639-1)",
        "string", "language_iso"
    ),
    MetadataField.AGE_RATING: FieldDefinition(
        MetadataField.AGE_RATING, FieldCategory.CLASSIFICATION,
        "Age Rating", "Age rating",
        "string", "age_rating"
    ),

    # Lists
    MetadataField.CHARACTERS: FieldDefinition(
        MetadataField.CHARACTERS, FieldCategory.LISTS,
        "Characters", "Character names",
        "list", "characters", True, ", "
    ),
    MetadataField.TEAMS: FieldDefinition(
        MetadataField.TEAMS, FieldCategory.LISTS,
        "Teams", "Team names",
        "list", "teams", True, ", "
    ),
    MetadataField.LOCATIONS: FieldDefinition(
        MetadataField.LOCATIONS, FieldCategory.LISTS,
        "Locations", "Location names",
        "list", "locations", True, ", "
    ),
    MetadataField.TAGS: FieldDefinition(
        MetadataField.TAGS, FieldCategory.LISTS,
        "Tags", "Content tags",
        "list", "tags", True, ", "
    ),

    # Links
    MetadataField.WEB_LINK: FieldDefinition(
        MetadataField.WEB_LINK, FieldCategory.LINKS,
        "Web Link", "Source URL",
        "string", "web"
    ),

    # Additional
    MetadataField.PAGE_COUNT: FieldDefinition(
        MetadataField.PAGE_COUNT, FieldCategory.ADDITIONAL,
        "Page Count", "Number of pages",
        "integer", "page_count"
    ),
    MetadataField.COUNT: FieldDefinition(
        MetadataField.COUNT, FieldCategory.ADDITIONAL,
        "Issue Count", "Total issues in series",
        "integer", "count"
    ),
    MetadataField.NOTES: FieldDefinition(
        MetadataField.NOTES, FieldCategory.ADDITIONAL,
        "Notes", "Additional notes",
        "string", "notes"
    ),
}


@dataclass
class ScannerCapabilities:
    """Defines what fields a scanner can provide"""
    scanner_name: str
    provided_fields: Set[MetadataField] = field(default_factory=set)
    primary_fields: Set[MetadataField] = field(default_factory=set)  # High confidence fields
    description: str = ""

    def can_provide(self, field: MetadataField) -> bool:
        """Check if scanner can provide this field"""
        return field in self.provided_fields

    def is_primary_field(self, field: MetadataField) -> bool:
        """Check if this is a primary/high-confidence field for this scanner"""
        return field in self.primary_fields

    def get_fields_by_category(self, category: FieldCategory) -> List[MetadataField]:
        """Get all provided fields in a category"""
        return [
            field for field in self.provided_fields
            if FIELD_DEFINITIONS.get(field) and FIELD_DEFINITIONS[field].category == category
        ]


# Scanner capability definitions
SCANNER_CAPABILITIES: Dict[str, ScannerCapabilities] = {
    "nhentai": ScannerCapabilities(
        scanner_name="nhentai",
        provided_fields={
            MetadataField.TITLE,
            MetadataField.ARTIST,
            MetadataField.GENRE,
            MetadataField.LANGUAGE_ISO,
            MetadataField.TAGS,
            MetadataField.CHARACTERS,
            MetadataField.PAGE_COUNT,
            MetadataField.WEB_LINK,
        },
        primary_fields={
            MetadataField.TITLE,
            MetadataField.ARTIST,
            MetadataField.TAGS,
        },
        description="Provides title, artist, tags, and parody information from nhentai.net"
    ),

    # Future scanners
    "anilist": ScannerCapabilities(
        scanner_name="anilist",
        provided_fields={
            MetadataField.TITLE,
            MetadataField.SERIES,
            MetadataField.VOLUME,
            MetadataField.ISSUE_NUMBER,
            MetadataField.YEAR,
            MetadataField.DESCRIPTION,
            MetadataField.GENRE,
            MetadataField.TAGS,
            MetadataField.WEB_LINK,
        },
        primary_fields={
            MetadataField.TITLE,
            MetadataField.SERIES,
            MetadataField.DESCRIPTION,
        },
        description="Manga metadata from AniList"
    ),

    "comicvine": ScannerCapabilities(
        scanner_name="comicvine",
        provided_fields={
            MetadataField.TITLE,
            MetadataField.SERIES,
            MetadataField.VOLUME,
            MetadataField.ISSUE_NUMBER,
            MetadataField.YEAR,
            MetadataField.DESCRIPTION,
            MetadataField.WRITER,
            MetadataField.ARTIST,
            MetadataField.PENCILLER,
            MetadataField.INKER,
            MetadataField.COLORIST,
            MetadataField.LETTERER,
            MetadataField.COVER_ARTIST,
            MetadataField.PUBLISHER,
            MetadataField.CHARACTERS,
            MetadataField.TEAMS,
            MetadataField.LOCATIONS,
            MetadataField.STORY_ARC,
            MetadataField.WEB_LINK,
        },
        primary_fields={
            MetadataField.TITLE,
            MetadataField.SERIES,
            MetadataField.ISSUE_NUMBER,
            MetadataField.WRITER,
            MetadataField.ARTIST,
        },
        description="Comprehensive comic book metadata from Comic Vine"
    ),
}


def get_scanner_capabilities(scanner_name: str) -> Optional[ScannerCapabilities]:
    """Get capabilities for a scanner"""
    return SCANNER_CAPABILITIES.get(scanner_name)


def get_all_scanner_capabilities() -> Dict[str, ScannerCapabilities]:
    """Get all scanner capabilities"""
    return SCANNER_CAPABILITIES


def map_scanner_metadata_to_comic(scanner_metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map scanner metadata to Comic model fields

    Takes raw scanner metadata and maps it to database column names.
    """
    comic_data = {}

    for field_enum, definition in FIELD_DEFINITIONS.items():
        field_name = field_enum.value

        if field_name in scanner_metadata and definition.db_column:
            value = scanner_metadata[field_name]

            # Handle list fields
            if definition.is_list and isinstance(value, list):
                if definition.separator:
                    value = definition.separator.join(str(v) for v in value)
                else:
                    value = str(value)

            comic_data[definition.db_column] = value

    return comic_data
