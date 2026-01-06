"""
Base archive class for comic loaders.

This module defines the abstract base class that all comic archive format
implementations must inherit from.
"""

from pathlib import Path
from typing import List, Optional
from io import BytesIO
from PIL import Image
import logging

logger = logging.getLogger(__name__)


class ComicArchive:
    """
    Base class for comic archives.
    
    All archive format implementations (CBZ, CBR, CB7) inherit from this class
    and must implement the abstract methods for loading pages and extracting files.
    
    Args:
        file_path: Path to the comic archive file
    """

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self._pages = None
        self._comic_info = None

    @property
    def pages(self):
        """
        Get list of pages in the comic.
        
        Returns:
            List of ComicPage objects representing pages in the archive
        """
        if self._pages is None:
            logger.debug(f"[COMIC_LOADER] Loading pages from archive: {self.file_path.name}")
            self._pages = self._load_pages()
            logger.debug(f"[COMIC_LOADER] Loaded {len(self._pages)} pages from {self.file_path.name}")
        return self._pages

    @property
    def page_count(self) -> int:
        """
        Get number of pages in the comic.
        
        Returns:
            Total number of pages
        """
        return len(self.pages)

    @property
    def comic_info(self):
        """
        Get comic metadata from ComicInfo.xml if available.
        
        Returns:
            ComicInfo object or None if not available
        """
        if self._comic_info is None:
            self._comic_info = self._load_comic_info()
        return self._comic_info

    def _load_pages(self) -> List:
        """
        Load list of pages from archive.
        
        Must be implemented by subclasses.
        
        Returns:
            List of ComicPage objects
        
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError

    def _load_comic_info(self):
        """
        Load ComicInfo.xml from archive if available.
        
        Returns:
            ComicInfo object or None if not found or parse failed
        """
        from ..comic_loader import ComicInfo
        
        try:
            xml_data = self.get_file('ComicInfo.xml')
            if xml_data:
                return ComicInfo.from_xml(xml_data)
        except Exception as e:
            logger.debug(f"No ComicInfo.xml found or failed to parse: {e}")
        return None

    def get_file(self, filename: str) -> Optional[bytes]:
        """
        Get file contents by filename.
        
        Must be implemented by subclasses.
        
        Args:
            filename: Name of the file to extract
        
        Returns:
            File contents as bytes or None if not found
        
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError

    def get_page(self, index: int) -> Optional[bytes]:
        """
        Get page data by index.
        
        Args:
            index: Page index (0-based)
        
        Returns:
            Page data as bytes or None if index out of range
        """
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
        """
        Get cover page (first page).
        
        Returns:
            Cover page data as bytes or None if no pages
        """
        return self.get_page(0) if self.page_count > 0 else None

    def extract_page_as_image(self, index: int) -> Optional[Image.Image]:
        """
        Extract page as PIL Image.
        
        Args:
            index: Page index (0-based)
        
        Returns:
            PIL Image object or None if extraction failed
        """
        page_data = self.get_page(index)
        if page_data:
            try:
                return Image.open(BytesIO(page_data))
            except Exception as e:
                logger.error(f"Failed to open image at index {index}: {e}")
        return None

    def close(self):
        """
        Close archive resources.
        
        Should be implemented by subclasses that need cleanup.
        """
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
