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
    title: Optional[str] = None
    series: Optional[str] = None
    number: Optional[str] = None
    volume: Optional[int] = None
    summary: Optional[str] = None
    notes: Optional[str] = None
    year: Optional[int] = None
    month: Optional[int] = None
    writer: Optional[str] = None
    penciller: Optional[str] = None
    inker: Optional[str] = None
    colorist: Optional[str] = None
    letterer: Optional[str] = None
    cover_artist: Optional[str] = None
    editor: Optional[str] = None
    publisher: Optional[str] = None
    imprint: Optional[str] = None
    genre: Optional[str] = None
    web: Optional[str] = None
    page_count: Optional[int] = None
    language_iso: Optional[str] = None
    format: Optional[str] = None
    age_rating: Optional[str] = None
    manga: Optional[bool] = None

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

            def get_bool(tag: str) -> Optional[bool]:
                text = get_text(tag)
                if text is None:
                    return None
                return text.lower() in ('yes', 'true', '1')

            return cls(
                title=get_text('Title'),
                series=get_text('Series'),
                number=get_text('Number'),
                volume=get_int('Volume'),
                summary=get_text('Summary'),
                notes=get_text('Notes'),
                year=get_int('Year'),
                month=get_int('Month'),
                writer=get_text('Writer'),
                penciller=get_text('Penciller'),
                inker=get_text('Inker'),
                colorist=get_text('Colorist'),
                letterer=get_text('Letterer'),
                cover_artist=get_text('CoverArtist'),
                editor=get_text('Editor'),
                publisher=get_text('Publisher'),
                imprint=get_text('Imprint'),
                genre=get_text('Genre'),
                web=get_text('Web'),
                page_count=get_int('PageCount'),
                language_iso=get_text('LanguageISO'),
                format=get_text('Format'),
                age_rating=get_text('AgeRating'),
                manga=get_bool('Manga'),
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
            self._pages = self._load_pages()
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
        if 0 <= index < len(self.pages):
            return self.get_file(self.pages[index].filename)
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
        self.archive = rarfile.RarFile(file_path, 'r')

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
        except KeyError:
            # Try case-insensitive search
            for name in self.archive.namelist():
                if name.lower() == filename.lower():
                    return self.archive.read(name)
        except Exception as e:
            logger.error(f"Failed to read {filename} from RAR: {e}")
        return None

    def close(self):
        """Close RAR archive"""
        if hasattr(self, 'archive'):
            self.archive.close()


class CB7Archive(ComicArchive):
    """7-Zip-based comic archive (.cb7)"""

    def __init__(self, file_path: Path):
        super().__init__(file_path)
        self.archive = py7zr.SevenZipFile(file_path, 'r')

    def _load_pages(self) -> List[ComicPage]:
        """Load pages from 7z archive"""
        pages = []

        # Get all files
        for filename, info in sorted(self.archive.list(), key=lambda x: x[0]):
            # Skip directories
            if info.is_directory:
                continue

            # Skip hidden files
            if Path(filename).name.startswith('.'):
                continue

            # Skip ComicInfo.xml
            if filename.lower() == 'comicinfo.xml':
                continue

            page = ComicPage(
                filename=filename,
                index=len(pages),
                size=info.uncompressed
            )

            if page.is_image:
                pages.append(page)

        return pages

    def get_file(self, filename: str) -> Optional[bytes]:
        """Get file contents from 7z archive"""
        try:
            # 7z requires extracting to dict
            data = self.archive.read([filename])
            if filename in data:
                # Read the BytesIO object
                return data[filename].read()

            # Try case-insensitive search
            for name in self.archive.getnames():
                if name.lower() == filename.lower():
                    data = self.archive.read([name])
                    return data[name].read()
        except Exception as e:
            logger.error(f"Failed to read {filename} from 7z: {e}")
        return None

    def close(self):
        """Close 7z archive"""
        if hasattr(self, 'archive'):
            self.archive.close()


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
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return None

    ext = file_path.suffix.lower()

    try:
        if ext == '.cbz':
            return CBZArchive(file_path)
        elif ext == '.cbr':
            return CBRArchive(file_path)
        elif ext == '.cb7':
            return CB7Archive(file_path)
        else:
            logger.error(f"Unsupported format: {ext}")
            return None
    except Exception as e:
        logger.error(f"Failed to open comic {file_path}: {e}")
        return None


def is_comic_file(file_path: Path) -> bool:
    """Check if file is a supported comic format"""
    return file_path.suffix.lower() in {'.cbz', '.cbr', '.cb7'}


def get_comic_format(file_path: Path) -> Optional[str]:
    """Get comic format type"""
    ext = file_path.suffix.lower()
    formats = {
        '.cbz': 'CBZ',
        '.cbr': 'CBR',
        '.cb7': 'CB7',
    }
    return formats.get(ext)
