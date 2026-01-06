"""
ZIP-based comic archive loader (CBZ format).

This module implements the loader for CBZ (Comic Book ZIP) format files.
"""

import zipfile
from pathlib import Path
from typing import List, Optional
import logging

from .base import ComicArchive
from .utils import IMAGE_EXTENSIONS

logger = logging.getLogger(__name__)


class CBZArchive(ComicArchive):
    """
    ZIP-based comic archive (.cbz).
    
    Handles reading comic book archives stored in ZIP format.
    
    Args:
        file_path: Path to the .cbz file
    """

    def __init__(self, file_path: Path):
        super().__init__(file_path)
        self.archive = zipfile.ZipFile(file_path, 'r')

    def _load_pages(self) -> List:
        """
        Load pages from ZIP archive.
        
        Returns:
            List of ComicPage objects for image files in the archive
        """
        from ..comic_loader import ComicPage
        
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
        """
        Get file contents from ZIP.
        
        Args:
            filename: Name of the file to extract
        
        Returns:
            File contents as bytes or None if not found
        """
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
        """Close ZIP archive."""
        if hasattr(self, 'archive'):
            self.archive.close()
