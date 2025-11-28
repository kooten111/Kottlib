"""
MangaDex API Client

Provides functionality to search and fetch cover art from MangaDex API.
Used for fetching cover images independent of which metadata scanner was used.

MangaDex API Documentation: https://api.mangadex.org/docs/

Rate Limits:
- 5 requests per second
- Implemented via simple sleep delay between requests
"""

import logging
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from io import BytesIO

import requests
from PIL import Image

logger = logging.getLogger(__name__)

# MangaDex API configuration
MANGADEX_API_BASE = "https://api.mangadex.org"
MANGADEX_COVER_BASE = "https://uploads.mangadex.org/covers"
RATE_LIMIT_DELAY = 0.2  # 5 requests/second


@dataclass
class MangaDexCover:
    """Represents a cover from MangaDex"""
    cover_id: str
    manga_id: str
    filename: str
    volume: Optional[str]
    description: Optional[str]
    locale: Optional[str]
    thumbnail_url: str
    full_url: str
    created_at: Optional[str] = None


@dataclass
class MangaDexManga:
    """Represents a manga from MangaDex search"""
    manga_id: str
    title: str
    alt_titles: List[str]
    description: Optional[str]
    year: Optional[int]
    status: Optional[str]
    cover_id: Optional[str] = None
    cover_filename: Optional[str] = None


class MangaDexClient:
    """
    Client for interacting with MangaDex API

    Provides search and cover fetching functionality with rate limiting.
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'YACLib-Enhanced/1.0'
        })
        self._last_request_time = 0

    def _rate_limit(self):
        """Enforce rate limiting between requests"""
        elapsed = time.time() - self._last_request_time
        if elapsed < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - elapsed)
        self._last_request_time = time.time()

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make a rate-limited request to MangaDex API

        Args:
            endpoint: API endpoint (without base URL)
            params: Query parameters

        Returns:
            JSON response dict or None on error
        """
        self._rate_limit()

        url = f"{MANGADEX_API_BASE}{endpoint}"
        logger.debug(f"MangaDex API request: {url} params={params}")

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error(f"MangaDex API timeout: {url}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"MangaDex API HTTP error: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"MangaDex API request error: {e}")
            return None
        except ValueError as e:
            logger.error(f"MangaDex API JSON decode error: {e}")
            return None

    def search_manga(self, title: str, limit: int = 10) -> List[MangaDexManga]:
        """
        Search for manga by title

        Args:
            title: Manga title to search for
            limit: Maximum number of results (default: 10, max: 100)

        Returns:
            List of MangaDexManga objects
        """
        params = {
            'title': title,
            'limit': min(limit, 100),
            'includes[]': ['cover_art'],
            'order[relevance]': 'desc'
        }

        data = self._make_request('/manga', params)
        if not data or 'data' not in data:
            return []

        results = []
        for manga_data in data['data']:
            manga = self._parse_manga(manga_data)
            if manga:
                results.append(manga)

        logger.info(f"MangaDex search for '{title}' returned {len(results)} results")
        return results

    def _parse_manga(self, manga_data: Dict) -> Optional[MangaDexManga]:
        """Parse manga data from API response"""
        try:
            manga_id = manga_data['id']
            attributes = manga_data.get('attributes', {})

            # Get title (prefer English, fallback to first available)
            title = None
            titles = attributes.get('title', {})
            if 'en' in titles:
                title = titles['en']
            elif titles:
                title = next(iter(titles.values()))

            if not title:
                return None

            # Get alternative titles
            alt_titles = []
            for alt in attributes.get('altTitles', []):
                for lang_title in alt.values():
                    alt_titles.append(lang_title)

            # Get description (prefer English)
            description = None
            descriptions = attributes.get('description', {})
            if 'en' in descriptions:
                description = descriptions['en']
            elif descriptions:
                description = next(iter(descriptions.values()))

            # Get cover from relationships
            cover_id = None
            cover_filename = None
            for rel in manga_data.get('relationships', []):
                if rel.get('type') == 'cover_art':
                    cover_id = rel.get('id')
                    cover_attrs = rel.get('attributes', {})
                    cover_filename = cover_attrs.get('fileName')
                    break

            return MangaDexManga(
                manga_id=manga_id,
                title=title,
                alt_titles=alt_titles,
                description=description,
                year=attributes.get('year'),
                status=attributes.get('status'),
                cover_id=cover_id,
                cover_filename=cover_filename
            )
        except Exception as e:
            logger.error(f"Error parsing manga data: {e}")
            return None

    def get_manga_covers(self, manga_id: str, limit: int = 100) -> List[MangaDexCover]:
        """
        Get all covers for a manga

        Args:
            manga_id: MangaDex manga ID
            limit: Maximum number of covers to return

        Returns:
            List of MangaDexCover objects
        """
        params = {
            'manga[]': manga_id,
            'limit': min(limit, 100),
            'order[volume]': 'asc'
        }

        data = self._make_request('/cover', params)
        if not data or 'data' not in data:
            return []

        covers = []
        for cover_data in data['data']:
            cover = self._parse_cover(cover_data, manga_id)
            if cover:
                covers.append(cover)

        logger.info(f"Found {len(covers)} covers for manga {manga_id}")
        return covers

    def _parse_cover(self, cover_data: Dict, manga_id: str) -> Optional[MangaDexCover]:
        """Parse cover data from API response"""
        try:
            cover_id = cover_data['id']
            attributes = cover_data.get('attributes', {})
            filename = attributes.get('fileName')

            if not filename:
                return None

            # Build cover URLs
            thumbnail_url = f"{MANGADEX_COVER_BASE}/{manga_id}/{filename}.256.jpg"
            full_url = f"{MANGADEX_COVER_BASE}/{manga_id}/{filename}"

            return MangaDexCover(
                cover_id=cover_id,
                manga_id=manga_id,
                filename=filename,
                volume=attributes.get('volume'),
                description=attributes.get('description'),
                locale=attributes.get('locale'),
                thumbnail_url=thumbnail_url,
                full_url=full_url,
                created_at=attributes.get('createdAt')
            )
        except Exception as e:
            logger.error(f"Error parsing cover data: {e}")
            return None

    def download_cover(self, cover: MangaDexCover, use_thumbnail: bool = False) -> Optional[bytes]:
        """
        Download a cover image

        Args:
            cover: MangaDexCover object
            use_thumbnail: If True, download thumbnail (256px), otherwise full image

        Returns:
            Image bytes or None on error
        """
        url = cover.thumbnail_url if use_thumbnail else cover.full_url
        self._rate_limit()

        logger.info(f"Downloading cover from {url}")

        try:
            response = self.session.get(url, timeout=60)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download cover: {e}")
            return None

    def download_cover_as_image(self, cover: MangaDexCover, use_thumbnail: bool = False) -> Optional[Image.Image]:
        """
        Download a cover and return as PIL Image

        Args:
            cover: MangaDexCover object
            use_thumbnail: If True, download thumbnail (256px), otherwise full image

        Returns:
            PIL Image or None on error
        """
        image_data = self.download_cover(cover, use_thumbnail)
        if not image_data:
            return None

        try:
            return Image.open(BytesIO(image_data))
        except Exception as e:
            logger.error(f"Failed to open cover image: {e}")
            return None

    def search_and_get_covers(self, title: str, limit_manga: int = 5, limit_covers: int = 20) -> List[Dict[str, Any]]:
        """
        Search for manga and return covers for all matches

        This is a convenience method that combines search and cover fetching.

        Args:
            title: Manga title to search for
            limit_manga: Max manga results to process
            limit_covers: Max covers per manga

        Returns:
            List of dicts with manga info and covers
        """
        results = []
        manga_list = self.search_manga(title, limit=limit_manga)

        for manga in manga_list:
            covers = self.get_manga_covers(manga.manga_id, limit=limit_covers)

            manga_result = {
                'manga_id': manga.manga_id,
                'title': manga.title,
                'alt_titles': manga.alt_titles,
                'description': manga.description,
                'year': manga.year,
                'status': manga.status,
                'covers': [
                    {
                        'cover_id': c.cover_id,
                        'volume': c.volume,
                        'description': c.description,
                        'thumbnail_url': c.thumbnail_url,
                        'full_url': c.full_url
                    }
                    for c in covers
                ]
            }
            results.append(manga_result)

        return results


# Singleton instance for reuse
_client_instance: Optional[MangaDexClient] = None


def get_mangadex_client() -> MangaDexClient:
    """Get the singleton MangaDex client instance"""
    global _client_instance
    if _client_instance is None:
        _client_instance = MangaDexClient()
    return _client_instance
