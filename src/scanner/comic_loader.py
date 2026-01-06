"""
Comic Archive Loader

Provides ComicInfo and ComicPage dataclasses, and factory functions for opening
comic archives. The actual archive format implementations are in the loaders/
package.

Supported formats:
- CBZ (ZIP)
- CBR (RAR)
- CB7 (7-Zip)
"""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import xml.etree.ElementTree as ET
import logging

# Import archive implementations from loaders package
from .loaders import (
    ComicArchive,
    CBZArchive,
    CBRArchive,
    CB7Archive,
    SevenZipCliArchive,
    detect_archive_format,
    is_comic_file,
    get_comic_format,
    IMAGE_EXTENSIONS,
)

logger = logging.getLogger(__name__)




@dataclass
class ComicPage:
    """Represents a single page in a comic"""
    filename: str
    index: int
    size: Optional[int] = None  # File size in bytes

    @property
    def is_image(self) -> bool:
        """Check if this page is an image file"""
        ext = Path(self.filename).suffix.lower()
        return ext in IMAGE_EXTENSIONS


@dataclass
class ComicInfo:
    """Comic metadata from ComicInfo.xml"""
    # Basic information
    title: Optional[str] = None
    series: Optional[str] = None
    number: Optional[str] = None
    count: Optional[int] = None  # Total issue count in series
    volume: Optional[int] = None
    summary: Optional[str] = None
    notes: Optional[str] = None

    # Date fields
    year: Optional[int] = None
    month: Optional[int] = None
    day: Optional[int] = None

    # Creator fields
    writer: Optional[str] = None
    penciller: Optional[str] = None
    inker: Optional[str] = None
    colorist: Optional[str] = None
    letterer: Optional[str] = None
    cover_artist: Optional[str] = None
    editor: Optional[str] = None

    # Publishing information
    publisher: Optional[str] = None
    imprint: Optional[str] = None
    genre: Optional[str] = None
    web: Optional[str] = None

    # Story arc information
    story_arc: Optional[str] = None
    story_arc_number: Optional[str] = None
    series_group: Optional[str] = None

    # Alternate series (for cross-overs)
    alternate_series: Optional[str] = None
    alternate_number: Optional[str] = None
    alternate_count: Optional[int] = None

    # Ratings and reviews
    age_rating: Optional[str] = None
    community_rating: Optional[float] = None  # 0.0 to 5.0

    # Characters and locations
    characters: Optional[str] = None
    teams: Optional[str] = None
    locations: Optional[str] = None

    # Other metadata
    page_count: Optional[int] = None
    language_iso: Optional[str] = None
    format: Optional[str] = None
    black_and_white: Optional[bool] = None
    manga: Optional[bool] = None
    gtin: Optional[str] = None

    @classmethod
    def from_xml(cls, xml_data: bytes) -> 'ComicInfo':
        """
        Parse ComicInfo.xml data.
        
        Args:
            xml_data: Raw XML data as bytes
        
        Returns:
            ComicInfo object with parsed metadata, or empty ComicInfo on parse error
        """
        try:
            root = ET.fromstring(xml_data)

            # Helper to get text from element
            def get_text(tag: str) -> Optional[str]:
                elem = root.find(tag)
                return elem.text if elem is not None and elem.text else None

            def get_int(tag: str) -> Optional[int]:
                text = get_text(tag)
                try:
                    return int(text) if text else None
                except ValueError:
                    return None

            def get_float(tag: str) -> Optional[float]:
                text = get_text(tag)
                try:
                    return float(text) if text else None
                except ValueError:
                    return None

            def get_bool(tag: str) -> Optional[bool]:
                text = get_text(tag)
                if text is None:
                    return None
                return text.lower() in ('yes', 'true', '1')

            return cls(
                # Basic information
                title=get_text('Title'),
                series=get_text('Series'),
                number=get_text('Number'),
                count=get_int('Count'),
                volume=get_int('Volume'),
                summary=get_text('Summary'),
                notes=get_text('Notes'),

                # Date fields
                year=get_int('Year'),
                month=get_int('Month'),
                day=get_int('Day'),

                # Creator fields
                writer=get_text('Writer'),
                penciller=get_text('Penciller'),
                inker=get_text('Inker'),
                colorist=get_text('Colorist'),
                letterer=get_text('Letterer'),
                cover_artist=get_text('CoverArtist'),
                editor=get_text('Editor'),

                # Publishing information
                publisher=get_text('Publisher'),
                imprint=get_text('Imprint'),
                genre=get_text('Genre'),
                web=get_text('Web'),

                # Story arc information
                story_arc=get_text('StoryArc'),
                story_arc_number=get_text('StoryArcNumber'),
                series_group=get_text('SeriesGroup'),

                # Alternate series
                alternate_series=get_text('AlternateSeries'),
                alternate_number=get_text('AlternateNumber'),
                alternate_count=get_int('AlternateCount'),

                # Ratings and reviews
                age_rating=get_text('AgeRating'),
                community_rating=get_float('CommunityRating'),

                # Characters and locations
                characters=get_text('Characters'),
                teams=get_text('Teams'),
                locations=get_text('Locations'),

                # Other metadata
                page_count=get_int('PageCount'),
                language_iso=get_text('LanguageISO'),
                format=get_text('Format'),
                black_and_white=get_bool('BlackAndWhite'),
                manga=get_bool('Manga'),
                gtin=get_text('GTIN'),
            )
        except ET.ParseError as e:
            logger.warning(f"Failed to parse ComicInfo.xml: {e}")
            return cls()


def open_comic(file_path: Path) -> Optional[ComicArchive]:
    """
    Open a comic archive file.

    Args:
        file_path: Path to comic file (.cbz, .cbr, .cb7)

    Returns:
        ComicArchive instance or None if format not supported

    Example:
        >>> with open_comic(Path("comic.cbz")) as comic:
        ...     print(f"Pages: {comic.page_count}")
        ...     cover = comic.get_cover()
    """
    logger.info(f"[COMIC_LOADER] Opening comic: {file_path}")
    logger.debug(f"[COMIC_LOADER] File exists: {file_path.exists()}, is_file: {file_path.is_file() if file_path.exists() else 'N/A'}")

    if not file_path.exists():
        logger.error(f"[COMIC_LOADER] File not found: {file_path}")
        return None

    # First, try to detect the actual format by magic numbers
    logger.debug(f"[COMIC_LOADER] Detecting archive format by magic numbers")
    detected_format = detect_archive_format(file_path)
    logger.debug(f"[COMIC_LOADER] Detected format: {detected_format}")

    # Try detected format first, then fall back to extension-based detection
    formats_to_try = []

    if detected_format:
        formats_to_try.append(detected_format)

    # Also try extension-based format if different from detected
    ext = file_path.suffix.lower()
    logger.debug(f"[COMIC_LOADER] File extension: {ext}")
    ext_format = None
    if ext in {'.cbz', '.zip'}:
        ext_format = 'zip'
    elif ext == '.cbr':
        ext_format = 'rar'
    elif ext == '.cb7':
        ext_format = '7z'

    logger.debug(f"[COMIC_LOADER] Extension-based format: {ext_format}")

    if ext_format and ext_format != detected_format:
        formats_to_try.append(ext_format)

    logger.debug(f"[COMIC_LOADER] Formats to try: {formats_to_try}")

    # If we have no format to try, give up
    if not formats_to_try:
        logger.error(f"[COMIC_LOADER] Unsupported or unrecognized format: {file_path.name}")
        return None

    # Try each format
    last_error = None
    tool_missing = False

    for fmt in formats_to_try:
        logger.debug(f"[COMIC_LOADER] Attempting to open as {fmt}")
        try:
            if fmt == 'zip':
                archive = CBZArchive(file_path)
                logger.info(f"[COMIC_LOADER] Successfully opened as CBZ: {file_path.name}")
                return archive
            elif fmt == 'rar':
                archive = CBRArchive(file_path)
                logger.info(f"[COMIC_LOADER] Successfully opened as CBR: {file_path.name}")
                return archive
            elif fmt == '7z':
                archive = CB7Archive(file_path)
                logger.info(f"[COMIC_LOADER] Successfully opened as CB7: {file_path.name}")
                return archive
        except RuntimeError as e:
            # RuntimeError indicates missing external tool
            last_error = e
            tool_missing = True
            
            # If unrar is missing for a RAR file, try 7z fallback
            if fmt == 'rar' and 'unrar' in str(e):
                logger.info("unrar missing, attempting 7z fallback for CBR")
                try:
                    archive = SevenZipCliArchive(file_path)
                    logger.info(f"[COMIC_LOADER] Successfully opened as CBR (via 7z): {file_path.name}")
                    return archive
                except Exception as e7z:
                    logger.warning(f"[COMIC_LOADER] 7z fallback failed: {e7z}")
            
            logger.warning(f"[COMIC_LOADER] Failed to open as {fmt} (tool missing): {e}")
            continue
        except Exception as e:
            last_error = e
            logger.warning(f"[COMIC_LOADER] Failed to open as {fmt}: {type(e).__name__}: {e}")
            
            # If standard py7zr failed for 7z/cb7, try 7z CLI fallback
            if fmt == '7z':
                logger.info("py7zr failed, attempting 7z fallback for CB7")
                try:
                    archive = SevenZipCliArchive(file_path)
                    logger.info(f"[COMIC_LOADER] Successfully opened as CB7 (via 7z): {file_path.name}")
                    return archive
                except Exception as e7z:
                    logger.warning(f"[COMIC_LOADER] 7z fallback failed: {e7z}")
                    
            continue

    # All formats failed
    if tool_missing:
        # Specific error for missing external tools
        logger.error(f"Failed to read {file_path.name} from RAR: {last_error}")
    elif detected_format and ext_format and detected_format != ext_format:
        logger.error(
            f"Failed to open {file_path.name}: "
            f"File appears to be {detected_format} but has .{ext_format} extension. "
            f"Could not open as either format."
        )
    else:
        logger.error(f"Failed to open {file_path.name}: Tried all supported formats")

    return None

