"""
7-Zip-based comic archive loaders (CB7 format).

This module implements loaders for CB7 (Comic Book 7-Zip) format files,
including both py7zr library-based and CLI-based implementations.
"""

import py7zr
from pathlib import Path
from typing import List, Optional, Dict
from io import BytesIO
import logging
import subprocess
import shutil

from .base import ComicArchive
from .utils import IMAGE_EXTENSIONS
from ...utils.sorting import natural_filename_sort_key

logger = logging.getLogger(__name__)


class _MemoryWriter:
    """
    Simple in-memory writer for py7zr extraction.
    
    Used to extract individual files from 7z archives to memory
    without writing to disk.
    """
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
    """
    Factory for creating in-memory writers for py7zr.
    
    Args:
        target_file: The specific file to extract to memory
    """
    def __init__(self, target_file: str):
        self.target_file = target_file
        self.writer = None

    def create(self, filename: str):
        """
        Create writer for the target file.
        
        Args:
            filename: Name of the file being extracted
        
        Returns:
            _MemoryWriter instance
        """
        if filename == self.target_file:
            self.writer = _MemoryWriter()
            return self.writer
        # For other files, return a dummy writer that discards data
        return _MemoryWriter()


class CB7Archive(ComicArchive):
    """
    7-Zip-based comic archive (.cb7).
    
    Handles reading comic book archives stored in 7-Zip format using py7zr library.
    
    Args:
        file_path: Path to the .cb7 file
    """

    def __init__(self, file_path: Path):
        super().__init__(file_path)
        self.archive = py7zr.SevenZipFile(file_path, 'r')

    def _load_pages(self) -> List:
        """
        Load pages from 7z archive.
        
        Returns:
            List of ComicPage objects for image files in the archive
        """
        from ..comic_loader import ComicPage
        
        pages = []

        # Get all files - list() returns FileInfo objects directly
        for info in sorted(self.archive.list(), key=lambda x: natural_filename_sort_key(x.filename)):
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

        pages.sort(key=lambda page: natural_filename_sort_key(page.filename))
        for index, page in enumerate(pages):
            page.index = index

        return pages

    def get_file(self, filename: str) -> Optional[bytes]:
        """
        Get file contents from 7z archive.
        
        Args:
            filename: Name of the file to extract
        
        Returns:
            File contents as bytes or None if not found
        """
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
        """Close 7z archive."""
        if hasattr(self, 'archive'):
            self.archive.close()


class SevenZipCliArchive(ComicArchive):
    """
    Fallback archive handler using 7z CLI tool.
    
    Useful when unrar is missing for CBR files, or when py7zr fails.
    Requires '7z' command to be available in PATH.
    
    Args:
        file_path: Path to the archive file
    
    Raises:
        RuntimeError: If 7z command is not found
    """

    def __init__(self, file_path: Path):
        super().__init__(file_path)
        if not shutil.which('7z'):
            raise RuntimeError("7z command not found")

    def _load_pages(self) -> List:
        """
        Load pages by parsing '7z l -slt' output.
        
        Returns:
            List of ComicPage objects for image files in the archive
        """
        from ..comic_loader import ComicPage
        
        pages = []
        
        try:
            # List archive contents with technical details (-slt)
            cmd = ['7z', 'l', '-slt', str(self.file_path)]
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                encoding='utf-8', 
                errors='replace',
                check=True
            )
            
            # Parse output
            # Output format is blocks of lines separated by newlines
            current_file = {}
            
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    if current_file:
                        self._process_file_entry(current_file, pages)
                        current_file = {}
                    continue
                
                if '=' in line:
                    key, value = line.split('=', 1)
                    current_file[key.strip()] = value.strip()
            
            # Process last entry
            if current_file:
                self._process_file_entry(current_file, pages)

            pages.sort(key=lambda page: natural_filename_sort_key(page.filename))
            for index, page in enumerate(pages):
                page.index = index
                
        except subprocess.CalledProcessError as e:
            logger.error(f"7z list failed: {e.stderr}")
            raise
            
        return pages

    def _process_file_entry(self, entry: Dict[str, str], pages: List):
        """
        Process a single file entry from 7z output.
        
        Args:
            entry: Dictionary of file attributes from 7z output
            pages: List to append ComicPage objects to
        """
        from ..comic_loader import ComicPage
        
        path = entry.get('Path')
        if not path:
            return
            
        # Skip directories
        if entry.get('Attributes', '').startswith('D'):
            return
            
        # Skip hidden files
        if Path(path).name.startswith('.'):
            return
            
        # Skip ComicInfo.xml
        if path.lower() == 'comicinfo.xml':
            return
            
        try:
            size = int(entry.get('Size', '0'))
        except ValueError:
            size = 0
            
        page = ComicPage(
            filename=path,
            index=len(pages),
            size=size
        )
        
        if page.is_image:
            pages.append(page)

    def get_file(self, filename: str) -> Optional[bytes]:
        """
        Get file contents using '7z e -so'.
        
        Args:
            filename: Name of the file to extract
        
        Returns:
            File contents as bytes or None if not found
        """
        try:
            # Extract to stdout (-so)
            cmd = ['7z', 'e', '-so', str(self.file_path), filename]
            result = subprocess.run(
                cmd, 
                capture_output=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            # 7z returns non-zero if file not found or other errors
            # Only log if it's not just a missing file (which returns empty/error)
            # 7z output might contain "No files to process"
            error_msg = e.stderr.decode('utf-8', errors='replace')
            logger.debug(f"Failed to extract {filename} with 7z: {error_msg}")
            
            # Identify if it was just not found (not critical) vs other error
            return None
        except Exception as e:
            logger.error(f"Error executing 7z: {e}")
            return None

    def close(self):
        """Close archive (no-op for CLI-based extraction)."""
        pass
