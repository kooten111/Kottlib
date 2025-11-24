"""
Comic Archive Loader

Handles loading comic files from various archive formats:
- CBZ (ZIP)
- CBR (RAR)
- CB7 (7-Zip)
- PDF (experimental)

Provides unified interface for extracting pages, metadata, and generating thumbnails.
"""

import zipfile
import rarfile
import py7zr
from pathlib import Path
from typing import List, Optional, BinaryIO, Dict, Any
from dataclasses import dataclass
from io import BytesIO
import xml.etree.ElementTree as ET
from PIL import Image
import logging

logger = logging.getLogger(__name__)

# Configure rarfile to use system unrar tool
rarfile.UNRAR_TOOL = "unrar"
rarfile.NEED_COMMENTS = 0
rarfile.USE_DATETIME = 0


# Supported image extensions for comic pages
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif'}


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
        """Parse ComicInfo.xml data"""
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


class ComicArchive:
    """Base class for comic archives"""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self._pages: Optional[List[ComicPage]] = None
        self._comic_info: Optional[ComicInfo] = None

    @property
    def pages(self) -> List[ComicPage]:
        """Get list of pages in the comic"""
        if self._pages is None:
            logger.debug(f"[COMIC_LOADER] Loading pages from archive: {self.file_path.name}")
            self._pages = self._load_pages()
            logger.debug(f"[COMIC_LOADER] Loaded {len(self._pages)} pages from {self.file_path.name}")
        return self._pages

    @property
    def page_count(self) -> int:
        """Get number of pages in the comic"""
        return len(self.pages)

    @property
    def comic_info(self) -> Optional[ComicInfo]:
        """Get comic metadata from ComicInfo.xml if available"""
        if self._comic_info is None:
            self._comic_info = self._load_comic_info()
        return self._comic_info

    def _load_pages(self) -> List[ComicPage]:
        """Load list of pages from archive (to be implemented by subclasses)"""
        raise NotImplementedError

    def _load_comic_info(self) -> Optional[ComicInfo]:
        """Load ComicInfo.xml from archive if available"""
        try:
            xml_data = self.get_file('ComicInfo.xml')
            if xml_data:
                return ComicInfo.from_xml(xml_data)
        except Exception as e:
            logger.debug(f"No ComicInfo.xml found or failed to parse: {e}")
        return None

    def get_file(self, filename: str) -> Optional[bytes]:
        """Get file contents by filename (to be implemented by subclasses)"""
        raise NotImplementedError

    def get_page(self, index: int) -> Optional[bytes]:
        """Get page data by index"""
        logger.debug(f"[COMIC_LOADER] get_page called: index={index}, total_pages={len(self.pages)}")
        if 0 <= index < len(self.pages):
            page_filename = self.pages[index].filename
            logger.debug(f"[COMIC_LOADER] Extracting page: {page_filename}")
            page_data = self.get_file(page_filename)
            if page_data:
                logger.debug(f"[COMIC_LOADER] Page extracted successfully: size={len(page_data)} bytes")
            else:
                logger.error(f"[COMIC_LOADER] Failed to extract page: {page_filename}")
            return page_data
        logger.error(f"[COMIC_LOADER] Page index out of range: index={index}, total_pages={len(self.pages)}")
        return None

    def get_cover(self) -> Optional[bytes]:
        """Get cover page (first page)"""
        return self.get_page(0) if self.page_count > 0 else None

    def extract_page_as_image(self, index: int) -> Optional[Image.Image]:
        """Extract page as PIL Image"""
        page_data = self.get_page(index)
        if page_data:
            try:
                return Image.open(BytesIO(page_data))
            except Exception as e:
                logger.error(f"Failed to open image at index {index}: {e}")
        return None

    def close(self):
        """Close archive (to be implemented by subclasses)"""
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class CBZArchive(ComicArchive):
    """ZIP-based comic archive (.cbz)"""

    def __init__(self, file_path: Path):
        super().__init__(file_path)
        self.archive = zipfile.ZipFile(file_path, 'r')

    def _load_pages(self) -> List[ComicPage]:
        """Load pages from ZIP archive"""
        pages = []

        # Get all files from the archive
        for idx, info in enumerate(sorted(self.archive.infolist(), key=lambda x: x.filename)):
            # Skip directories and non-image files
            if info.is_dir():
                continue

            # Skip hidden files and metadata
            if Path(info.filename).name.startswith('.'):
                continue

            # Skip ComicInfo.xml
            if info.filename.lower() == 'comicinfo.xml':
                continue

            page = ComicPage(
                filename=info.filename,
                index=len(pages),
                size=info.file_size
            )

            # Only include image files
            if page.is_image:
                pages.append(page)

        return pages

    def get_file(self, filename: str) -> Optional[bytes]:
        """Get file contents from ZIP"""
        try:
            return self.archive.read(filename)
        except KeyError:
            # Try case-insensitive search
            for name in self.archive.namelist():
                if name.lower() == filename.lower():
                    return self.archive.read(name)
        except Exception as e:
            logger.error(f"Failed to read {filename} from ZIP: {e}")
        return None

    def close(self):
        """Close ZIP archive"""
        if hasattr(self, 'archive'):
            self.archive.close()


class CBRArchive(ComicArchive):
    """RAR-based comic archive (.cbr)"""

    def __init__(self, file_path: Path):
        super().__init__(file_path)
        try:
            self.archive = rarfile.RarFile(file_path, 'r')
        except rarfile.RarCannotExec as e:
            raise RuntimeError(
                f"Cannot extract RAR files: unrar tool not found. "
                f"Please install unrar to read CBR archives. "
                f"(Arch: sudo pacman -S unrar, Debian/Ubuntu: sudo apt install unrar)"
            ) from e

    def _load_pages(self) -> List[ComicPage]:
        """Load pages from RAR archive"""
        pages = []

        for idx, info in enumerate(sorted(self.archive.infolist(), key=lambda x: x.filename)):
            # Skip directories
            if info.is_dir():
                continue

            # Skip hidden files
            if Path(info.filename).name.startswith('.'):
                continue

            # Skip ComicInfo.xml
            if info.filename.lower() == 'comicinfo.xml':
                continue

            page = ComicPage(
                filename=info.filename,
                index=len(pages),
                size=info.file_size
            )

            if page.is_image:
                pages.append(page)

        return pages

    def get_file(self, filename: str) -> Optional[bytes]:
        """Get file contents from RAR"""
        try:
            return self.archive.read(filename)
        except (KeyError, rarfile.NoRarEntry):
            # Try case-insensitive search
            for name in self.archive.namelist():
                if name.lower() == filename.lower():
                    return self.archive.read(name)
            # Not found - return None silently (expected for optional files)
            return None
        except Exception as e:
            logger.error(f"Failed to read {filename} from RAR: {e}")
        return None

    def close(self):
        """Close RAR archive"""
        if hasattr(self, 'archive'):
            self.archive.close()


class _MemoryWriter:
    """Simple in-memory writer for py7zr extraction"""
    def __init__(self):
        self._buffer = BytesIO()

    def write(self, data: bytes) -> int:
        return self._buffer.write(data)

    def seek(self, offset: int, whence: int = 0) -> int:
        return self._buffer.seek(offset, whence)

    def tell(self) -> int:
        return self._buffer.tell()

    def flush(self):
        pass

    def close(self):
        pass

    def get_bytes(self) -> bytes:
        return self._buffer.getvalue()


class _MemoryWriterFactory:
    """Factory for creating in-memory writers for py7zr"""
    def __init__(self, target_file: str):
        self.target_file = target_file
        self.writer = None

    def create(self, filename: str):
        """Create writer for the target file"""
        if filename == self.target_file:
            self.writer = _MemoryWriter()
            return self.writer
        # For other files, return a dummy writer that discards data
        return _MemoryWriter()


class CB7Archive(ComicArchive):
    """7-Zip-based comic archive (.cb7)"""

    def __init__(self, file_path: Path):
        super().__init__(file_path)
        self.archive = py7zr.SevenZipFile(file_path, 'r')

    def _load_pages(self) -> List[ComicPage]:
        """Load pages from 7z archive"""
        pages = []

        # Get all files - list() returns FileInfo objects directly
        for info in sorted(self.archive.list(), key=lambda x: x.filename):
            # Skip directories
            if info.is_directory:
                continue

            # Skip hidden files
            if Path(info.filename).name.startswith('.'):
                continue

            # Skip ComicInfo.xml
            if info.filename.lower() == 'comicinfo.xml':
                continue

            page = ComicPage(
                filename=info.filename,
                index=len(pages),
                size=info.uncompressed
            )

            if page.is_image:
                pages.append(page)

        return pages

    def get_file(self, filename: str) -> Optional[bytes]:
        """Get file contents from 7z archive"""
        try:
            # Find the actual filename (might be case-insensitive)
            target_name = filename
            found = False

            for name in self.archive.getnames():
                if name == filename:
                    found = True
                    break
                elif name.lower() == filename.lower():
                    target_name = name
                    found = True
                    break

            if not found:
                return None

            # Extract to memory using factory pattern
            factory = _MemoryWriterFactory(target_name)
            self.archive.reset()  # Reset archive position for extraction
            self.archive.extract(targets=[target_name], factory=factory)

            if factory.writer:
                return factory.writer.get_bytes()

        except Exception as e:
            logger.error(f"Failed to read {filename} from 7z: {e}")
        return None

    def close(self):
        """Close 7z archive"""
        if hasattr(self, 'archive'):
            self.archive.close()


def detect_archive_format(file_path: Path) -> Optional[str]:
    """
    Detect actual archive format by reading file magic numbers.

    This handles cases where files have incorrect extensions (e.g., .cbr file
    that's actually a ZIP archive).

    Returns:
        'zip', 'rar', '7z', or None if format cannot be determined
    """
    try:
        with open(file_path, 'rb') as f:
            header = f.read(16)

        if not header:
            return None

        # ZIP magic number: 50 4B (PK)
        if header[:2] == b'PK':
            return 'zip'

        # RAR magic numbers
        # RAR 4.x: 52 61 72 21 1A 07 00 (Rar!\x1a\x07\x00)
        # RAR 5.x: 52 61 72 21 1A 07 01 00 (Rar!\x1a\x07\x01\x00)
        if header[:4] == b'Rar!':
            return 'rar'

        # 7z magic number: 37 7A BC AF 27 1C
        if header[:6] == b'7z\xbc\xaf\x27\x1c':
            return '7z'

        return None
    except Exception as e:
        logger.debug(f"Failed to detect format for {file_path}: {e}")
        return None


def open_comic(file_path: Path) -> Optional[ComicArchive]:
    """
    Open a comic archive file

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
            logger.warning(f"[COMIC_LOADER] Failed to open as {fmt} (tool missing): {e}")
            continue
        except Exception as e:
            last_error = e
            logger.warning(f"[COMIC_LOADER] Failed to open as {fmt}: {type(e).__name__}: {e}")
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


def is_comic_file(file_path: Path) -> bool:
    """Check if file is a supported comic format"""
    return file_path.suffix.lower() in {'.cbz', '.cbr', '.cb7', '.zip'}


def get_comic_format(file_path: Path) -> Optional[str]:
    """Get comic format type"""
    ext = file_path.suffix.lower()
    formats = {
        '.cbz': 'CBZ',
        '.cbr': 'CBR',
        '.cb7': 'CB7',
        '.zip': 'CBZ',  # .zip files are treated as CBZ
    }
    return formats.get(ext)
