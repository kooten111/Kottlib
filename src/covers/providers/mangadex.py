"""
MangaDex Cover Provider

Fetches cover images from MangaDex API.

MangaDex API documentation: https://api.mangadex.org/docs/
Rate limit: 5 requests per second
"""

import logging
import time
from typing import List, Optional, Dict, Any

import requests

from ..base_provider import (
    BaseCoverProvider,
    CoverOption,
    CoverProviderAPIError,
    CoverProviderRateLimitError,
)

logger = logging.getLogger(__name__)

# MangaDex API Constants
MANGADEX_API_BASE = "https://api.mangadex.org"
MANGADEX_UPLOADS_BASE = "https://uploads.mangadex.org"
USER_AGENT = "Kottlib-Enhanced (Compatible; MangaDexCoverProvider)"

# Rate limiting: 5 requests per second
RATE_LIMIT_DELAY = 0.2


class MangaDexCoverProvider(BaseCoverProvider):
    """
    MangaDex cover provider.

    Fetches covers from the MangaDex API. Supports searching for manga
    and retrieving their cover images.

    API Endpoints used:
    - GET /manga?title={query} - Search for manga by title
    - GET /cover?manga[]={manga_id} - Get covers for a manga

    Image URL format:
    https://uploads.mangadex.org/covers/{manga_id}/{filename}

    Rate limit: 5 requests per second (200ms between requests)
    """

    @property
    def source_name(self) -> str:
        return "mangadex"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self._last_request_time = 0
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            }
        )
        # Max results per search
        self._max_results = self.config.get("max_results", 10)
        # Timeout for API requests
        self._timeout = self.config.get("timeout", 30)

    def _wait_for_rate_limit(self):
        """Ensure we don't exceed rate limits (5 req/sec)."""
        elapsed = time.time() - self._last_request_time
        if elapsed < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - elapsed)
        self._last_request_time = time.time()

    def _request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute an API request.

        Args:
            endpoint: API endpoint (e.g., 'manga')
            params: Query parameters

        Returns:
            Response data dictionary

        Raises:
            CoverProviderRateLimitError: If rate limited
            CoverProviderAPIError: On other API errors
        """
        self._wait_for_rate_limit()

        url = f"{MANGADEX_API_BASE}/{endpoint}"

        try:
            response = self._session.get(url, params=params, timeout=self._timeout)

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After", "60")
                raise CoverProviderRateLimitError(
                    f"Rate limit exceeded. Retry after {retry_after} seconds"
                )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            raise CoverProviderAPIError(
                f"MangaDex API request timed out after {self._timeout}s"
            )
        except requests.exceptions.ConnectionError as e:
            raise CoverProviderAPIError(f"Failed to connect to MangaDex API: {e}")
        except requests.exceptions.HTTPError as e:
            raise CoverProviderAPIError(f"MangaDex API HTTP error: {e}")
        except requests.exceptions.RequestException as e:
            raise CoverProviderAPIError(f"MangaDex API request failed: {e}")

    def _search_manga(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for manga by title.

        Args:
            query: Search query

        Returns:
            List of manga data dictionaries
        """
        params = {
            "title": query,
            "limit": self._max_results,
            "includes[]": ["cover_art"],
            "order[relevance]": "desc",
        }

        data = self._request("manga", params)
        return data.get("data", [])

    def _get_covers_for_manga(self, manga_id: str) -> List[Dict[str, Any]]:
        """
        Get all covers for a manga.

        Args:
            manga_id: MangaDex manga UUID

        Returns:
            List of cover data dictionaries
        """
        params = {
            "manga[]": manga_id,
            "limit": 100,  # Get all covers
            "order[volume]": "asc",
        }

        data = self._request("cover", params)
        return data.get("data", [])

    def _build_cover_url(
        self, manga_id: str, filename: str, size: str = "original"
    ) -> str:
        """
        Build the cover image URL.

        Args:
            manga_id: MangaDex manga UUID
            filename: Cover filename
            size: Size variant ('original', '512', '256')

        Returns:
            Full cover image URL
        """
        if size == "original":
            return f"{MANGADEX_UPLOADS_BASE}/covers/{manga_id}/{filename}"
        return f"{MANGADEX_UPLOADS_BASE}/covers/{manga_id}/{filename}.{size}.jpg"

    def _extract_cover_from_manga(self, manga: Dict[str, Any]) -> Optional[CoverOption]:
        """
        Extract the main cover from manga data (when includes[] contains cover_art).

        Args:
            manga: Manga data dictionary from API

        Returns:
            CoverOption or None
        """
        manga_id = manga.get("id")
        if not manga_id:
            return None

        # Get manga title
        title_dict = manga.get("attributes", {}).get("title", {})
        title = title_dict.get("en") or next(iter(title_dict.values()), "Unknown")

        # Find cover_art relationship
        relationships = manga.get("relationships", [])
        for rel in relationships:
            if rel.get("type") == "cover_art":
                cover_id = rel.get("id")
                filename = rel.get("attributes", {}).get("fileName")
                if cover_id and filename:
                    full_url = self._build_cover_url(manga_id, filename, "original")
                    thumbnail_url = self._build_cover_url(manga_id, filename, "256")

                    return CoverOption(
                        id=f"{manga_id}:{cover_id}",
                        source=self.source_name,
                        thumbnail_url=thumbnail_url,
                        full_url=full_url,
                        description=f"{title} (Main Cover)",
                    )

        return None

    def _cover_data_to_option(
        self, cover: Dict[str, Any], manga_id: str, manga_title: str
    ) -> CoverOption:
        """
        Convert cover API data to CoverOption.

        Args:
            cover: Cover data from API
            manga_id: Manga UUID
            manga_title: Manga title for description

        Returns:
            CoverOption object
        """
        cover_id = cover.get("id", "unknown")
        attrs = cover.get("attributes", {})
        filename = attrs.get("fileName", "")
        volume = attrs.get("volume")
        locale = attrs.get("locale", "en")

        # Build description
        if volume:
            description = f"{manga_title} - Volume {volume}"
        else:
            description = f"{manga_title} - Cover"

        if locale and locale != "en":
            description += f" ({locale})"

        full_url = self._build_cover_url(manga_id, filename, "original")
        thumbnail_url = self._build_cover_url(manga_id, filename, "256")

        return CoverOption(
            id=f"{manga_id}:{cover_id}",
            source=self.source_name,
            thumbnail_url=thumbnail_url,
            full_url=full_url,
            description=description,
        )

    def search_covers(self, query: str, **kwargs) -> List[CoverOption]:
        """
        Search for covers by manga title.

        Args:
            query: Search query (manga title)
            **kwargs:
                - include_all_covers: If True, fetch all covers for each manga
                                     (default: False, only returns main cover)

        Returns:
            List of CoverOption objects
        """
        include_all = kwargs.get("include_all_covers", False)

        try:
            # Search for manga
            manga_list = self._search_manga(query)

            if not manga_list:
                logger.debug(f"No manga found for query: {query}")
                return []

            covers: List[CoverOption] = []

            for manga in manga_list:
                manga_id = manga.get("id")
                if not manga_id:
                    continue

                # Get manga title
                title_dict = manga.get("attributes", {}).get("title", {})
                title = title_dict.get("en") or next(iter(title_dict.values()), "Unknown")

                if include_all:
                    # Fetch all covers for this manga
                    cover_data_list = self._get_covers_for_manga(manga_id)
                    for cover_data in cover_data_list:
                        cover_option = self._cover_data_to_option(
                            cover_data, manga_id, title
                        )
                        covers.append(cover_option)
                else:
                    # Just extract the main cover from the manga data
                    cover_option = self._extract_cover_from_manga(manga)
                    if cover_option:
                        covers.append(cover_option)

            logger.debug(f"Found {len(covers)} covers for query: {query}")
            return covers

        except (CoverProviderRateLimitError, CoverProviderAPIError):
            raise
        except Exception as e:
            logger.error(f"Error searching MangaDex covers: {e}")
            raise CoverProviderAPIError(f"MangaDex search failed: {e}")

    def download_cover(self, cover_id: str) -> bytes:
        """
        Download cover image data.

        Args:
            cover_id: Cover ID in format 'manga_id:cover_id'

        Returns:
            Raw image data as bytes

        Raises:
            CoverProviderAPIError: If download fails
        """
        try:
            # Parse the cover_id to get manga_id and cover_id
            parts = cover_id.split(":", 1)
            if len(parts) != 2:
                raise CoverProviderAPIError(f"Invalid cover ID format: {cover_id}")

            manga_id, actual_cover_id = parts

            # Fetch cover details to get the filename
            params = {"ids[]": actual_cover_id}
            data = self._request("cover", params)

            covers = data.get("data", [])
            if not covers:
                raise CoverProviderAPIError(f"Cover not found: {cover_id}")

            cover_data = covers[0]
            filename = cover_data.get("attributes", {}).get("fileName")

            if not filename:
                raise CoverProviderAPIError(f"Cover filename not found: {cover_id}")

            # Download the image
            image_url = self._build_cover_url(manga_id, filename, "original")

            self._wait_for_rate_limit()

            response = self._session.get(image_url, timeout=self._timeout)
            response.raise_for_status()

            logger.debug(f"Downloaded cover: {cover_id} ({len(response.content)} bytes)")
            return response.content

        except CoverProviderAPIError:
            raise
        except requests.exceptions.RequestException as e:
            raise CoverProviderAPIError(f"Failed to download cover: {e}")
        except Exception as e:
            logger.error(f"Error downloading cover {cover_id}: {e}")
            raise CoverProviderAPIError(f"Cover download failed: {e}")
