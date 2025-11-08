"""
YACLibrary Server Python Client

A Python client library for interacting with YACReaderLibrary Server.
Handles session management, async loading delays, and provides a clean API.
"""

import time
from typing import Optional, Dict, List, BinaryIO
from dataclasses import dataclass
import requests
from io import BytesIO


@dataclass
class ComicMetadata:
    """Comic metadata from YACServer"""
    library: str
    library_id: int
    comic_id: int
    hash: str
    path: str
    num_pages: int
    rating: int
    current_page: int
    contrast: int
    read: bool
    cover_page: int
    manga: bool
    added: int
    type: int
    next_comic: Optional[int] = None
    previous_comic: Optional[int] = None

    @classmethod
    def from_text(cls, text: str) -> 'ComicMetadata':
        """Parse metadata from YACServer text format"""
        data = {}
        for line in text.strip().split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                data[key] = value

        return cls(
            library=data.get('library', ''),
            library_id=int(data.get('libraryId', 0)),
            comic_id=int(data.get('comicid', 0)),
            hash=data.get('hash', ''),
            path=data.get('path', ''),
            num_pages=int(data.get('numpages', 0)),
            rating=int(data.get('rating', 0)),
            current_page=int(data.get('currentPage', 1)),
            contrast=int(data.get('contrast', -1)),
            read=bool(int(data.get('read', 0))),
            cover_page=int(data.get('coverPage', 1)),
            manga=bool(int(data.get('manga', 0))),
            added=int(data.get('added', 0)),
            type=int(data.get('type', 0)),
            next_comic=int(data['nextComic']) if 'nextComic' in data else None,
            previous_comic=int(data['previousComic']) if 'previousComic' in data else None,
        )


class YACLibClient:
    """Client for YACReaderLibrary Server"""

    def __init__(
        self,
        base_url: str = "http://192.168.1.5:25565",
        load_wait_time: float = 3.0,
        max_retries: int = 5,
        retry_delay: float = 0.5
    ):
        """
        Initialize YACLib client

        Args:
            base_url: Base URL of YACServer (e.g., http://192.168.1.5:25565)
            load_wait_time: Time to wait after opening comic for it to load
            max_retries: Maximum number of retries for page requests
            retry_delay: Delay between retries in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.load_wait_time = load_wait_time
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Current state
        self.current_comic: Optional[ComicMetadata] = None
        self.comic_loaded_time: Optional[float] = None

    def get_libraries(self) -> str:
        """
        Get list of libraries (HTML format)

        Returns:
            HTML page with library list
        """
        response = self.session.get(f"{self.base_url}/")
        response.raise_for_status()
        return response.text

    def get_folder(
        self,
        library_id: int,
        folder_id: int = 1,
        page: int = 0
    ) -> str:
        """
        Get folder contents

        Args:
            library_id: Library ID
            folder_id: Folder ID (default: 1 = root)
            page: Page number for pagination

        Returns:
            HTML page with folder contents
        """
        url = f"{self.base_url}/library/{library_id}/folder/{folder_id}"
        params = {'page': page} if page > 0 else {}
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.text

    def get_cover(self, library_id: int, hash: str) -> bytes:
        """
        Get comic cover image

        Args:
            library_id: Library ID
            hash: Comic hash

        Returns:
            JPEG image bytes
        """
        url = f"{self.base_url}/library/{library_id}/cover/{hash}.jpg"
        response = self.session.get(url)
        response.raise_for_status()
        return response.content

    def open_comic(
        self,
        library_id: int,
        comic_id: int,
        wait_for_load: bool = True
    ) -> ComicMetadata:
        """
        Open a comic for reading

        This loads the comic file into memory on the server. Pages won't be
        available immediately - you must wait for loading to complete.

        Args:
            library_id: Library ID
            comic_id: Comic ID
            wait_for_load: If True, wait for comic to load before returning

        Returns:
            Comic metadata
        """
        url = f"{self.base_url}/library/{library_id}/comic/{comic_id}/remote"
        response = self.session.get(url)
        response.raise_for_status()

        metadata = ComicMetadata.from_text(response.text)
        self.current_comic = metadata
        self.comic_loaded_time = time.time()

        if wait_for_load:
            time.sleep(self.load_wait_time)

        return metadata

    def get_page(
        self,
        library_id: int,
        comic_id: int,
        page_num: int,
        auto_retry: bool = True
    ) -> bytes:
        """
        Get a page image

        The comic must be opened first with open_comic().
        If the page isn't loaded yet, this will retry automatically.

        Args:
            library_id: Library ID
            comic_id: Comic ID
            page_num: Page number (0-indexed)
            auto_retry: Automatically retry if page not loaded yet

        Returns:
            JPEG image bytes

        Raises:
            ValueError: If page doesn't exist or comic not opened
        """
        url = f"{self.base_url}/library/{library_id}/comic/{comic_id}/page/{page_num}/remote"

        retries = self.max_retries if auto_retry else 1

        for attempt in range(retries):
            response = self.session.get(url)

            if response.status_code == 200 and len(response.content) > 0:
                return response.content

            if response.status_code == 404:
                if attempt < retries - 1:
                    # Comic might still be loading, wait and retry
                    time.sleep(self.retry_delay)
                    continue
                else:
                    raise ValueError(
                        f"Page {page_num} not found. "
                        "Comic may not be loaded yet or page doesn't exist."
                    )

            response.raise_for_status()

        raise ValueError(f"Failed to load page {page_num} after {retries} attempts")

    def get_all_pages(
        self,
        library_id: int,
        comic_id: int,
        start_page: int = 0,
        end_page: Optional[int] = None
    ) -> List[bytes]:
        """
        Get multiple pages

        Args:
            library_id: Library ID
            comic_id: Comic ID
            start_page: Starting page number (0-indexed)
            end_page: Ending page number (exclusive), None = all pages

        Returns:
            List of JPEG image bytes
        """
        if not self.current_comic or self.current_comic.comic_id != comic_id:
            # Need to open comic first
            self.open_comic(library_id, comic_id)

        if end_page is None:
            end_page = self.current_comic.num_pages

        pages = []
        for page_num in range(start_page, end_page):
            page_data = self.get_page(library_id, comic_id, page_num)
            pages.append(page_data)

        return pages

    def update_reading_progress(
        self,
        library_id: int,
        comic_id: int,
        current_page: int
    ) -> None:
        """
        Update reading progress

        Args:
            library_id: Library ID
            comic_id: Comic ID
            current_page: Current page number
        """
        url = f"{self.base_url}/library/{library_id}/comic/{comic_id}/update"
        data = f"currentPage:{current_page}"
        response = self.session.post(url, data=data.encode())
        response.raise_for_status()

    def close(self):
        """Close the session"""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class YACLibAsyncClient(YACLibClient):
    """
    Enhanced client with async page loading

    Monitors comic loading status and only requests pages when ready.
    Provides better performance and reliability.
    """

    def is_comic_loaded(self) -> bool:
        """Check if current comic is likely loaded"""
        if not self.comic_loaded_time:
            return False

        elapsed = time.time() - self.comic_loaded_time
        return elapsed >= self.load_wait_time

    def wait_for_comic_load(self, timeout: float = 10.0) -> bool:
        """
        Wait for comic to finish loading

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if loaded, False if timeout
        """
        if not self.comic_loaded_time:
            return False

        start_time = time.time()
        while not self.is_comic_loaded():
            if time.time() - start_time > timeout:
                return False
            time.sleep(0.1)

        return True

    def get_page(
        self,
        library_id: int,
        comic_id: int,
        page_num: int,
        auto_retry: bool = True,
        wait_if_not_loaded: bool = True
    ) -> bytes:
        """
        Get a page with enhanced loading detection

        Args:
            library_id: Library ID
            comic_id: Comic ID
            page_num: Page number (0-indexed)
            auto_retry: Automatically retry if page not loaded yet
            wait_if_not_loaded: Wait for comic to load before requesting

        Returns:
            JPEG image bytes
        """
        if wait_if_not_loaded and not self.is_comic_loaded():
            self.wait_for_comic_load()

        return super().get_page(library_id, comic_id, page_num, auto_retry)


# Convenience function
def connect(base_url: str = "http://192.168.1.5:25565") -> YACLibClient:
    """
    Create a YACLib client

    Args:
        base_url: Base URL of YACServer

    Returns:
        YACLibClient instance
    """
    return YACLibClient(base_url)
