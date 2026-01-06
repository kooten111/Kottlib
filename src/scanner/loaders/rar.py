"""
RAR-based comic archive loader (CBR format).

This module implements the loader for CBR (Comic Book RAR) format files.
"""

import rarfile
from pathlib import Path
from typing import List, Optional
import logging

from .base import ComicArchive
from .utils import IMAGE_EXTENSIONS

logger = logging.getLogger(__name__)

# Configure rarfile to use system unrar tool
rarfile.UNRAR_TOOL = "unrar"
rarfile.NEED_COMMENTS = 0
rarfile.USE_DATETIME = 0


class CBRArchive(ComicArchive):
    """
    RAR-based comic archive (.cbr).
    
    Handles reading comic book archives stored in RAR format.
    Requires the 'unrar' command-line tool to be installed.
    
    Args:
        file_path: Path to the .cbr file
    
    Raises:
        RuntimeError: If unrar tool is not found
    """

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

    def _load_pages(self) -> List:
        """
        Load pages from RAR archive.
        
        Returns:
            List of ComicPage objects for image files in the archive
        """
        from ..comic_loader import ComicPage
        
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
        """
        Get file contents from RAR.
        
        Args:
            filename: Name of the file to extract
        
        Returns:
            File contents as bytes or None if not found
        """
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
        """Close RAR archive."""
        if hasattr(self, 'archive'):
            self.archive.close()
