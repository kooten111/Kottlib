#!/usr/bin/env python3
"""
MangaDex Scanner - Metadata Scanner for Manga

A complete, self-contained scanner for extracting metadata from MangaDex.org.
This scanner uses the MangaDex REST API to fetch manga metadata.

Features:
- MangaDex API client (no authentication required)
- Series-level metadata extraction
- Fuzzy matching with confidence scores
- Multi-language title support
- Author, artist, and tag extraction
- Rate limiting (5 requests/second)

Usage:
    python mangadex_scanner.py "One Piece"

    Or import as a module:
    from mangadex_scanner import MangaDexScanner
"""

import re
import json
import time
import logging
import argparse
from typing import List, Tuple, Optional, Dict, Any
from difflib import SequenceMatcher
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum

try:
    # Import from src.scanners package
    from src.scanners.base_scanner import (
        BaseScanner, ScanResult, ScanLevel, MatchConfidence,
        ScannerAPIError, ScannerRateLimitError
    )
    from src.scanners.config_schema import ConfigOption, ConfigType
except ImportError:
    # Fallback for standalone execution
    BaseScanner = ABC
    ScanResult = None
    ScanLevel = None
    MatchConfidence = None
    ScannerAPIError = Exception
    ScannerRateLimitError = Exception

import requests

logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

# MangaDex API configuration
BASE_URL = "https://api.mangadex.org"
RATE_LIMIT_DELAY = 0.2  # 5 requests per second = 200ms between requests

# Confidence scoring constants
EXACT_MATCH_CONFIDENCE = 1.0
SUBSTRING_MATCH_CONFIDENCE = 0.9
MAX_CONFIDENCE = 1.0

# User-Agent for API requests
USER_AGENT = 'YACLib-Enhanced (Compatible; MangaDexScanner)'


# ============================================================================
# MangaDex API Client
# ============================================================================

class MangaDexAPI:
    """
    Client for the MangaDex REST API

    Official API documentation: https://api.mangadex.org/docs/
    No authentication required for read operations.
    Rate limit: 5 requests per second
    """

    def __init__(
        self,
        timeout: int = 30,
        rate_limit_delay: float = RATE_LIMIT_DELAY
    ):
        """
        Initialize MangaDex API client

        Args:
            timeout: Request timeout in seconds
            rate_limit_delay: Delay between requests to respect rate limits
        """
        self.timeout = timeout
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = 0
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept': 'application/json',
        })

    def _wait_for_rate_limit(self):
        """Ensure we don't exceed rate limits (5 req/sec)"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()

    def _request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Execute an API request

        Args:
            endpoint: API endpoint (e.g., "manga")
            params: Query parameters

        Returns:
            Response data dictionary

        Raises:
            ScannerRateLimitError: If rate limited
            ScannerAPIError: On other API errors
        """
        self._wait_for_rate_limit()

        url = f"{BASE_URL}/{endpoint}"

        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout
            )

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = response.headers.get('Retry-After', '60')
                raise ScannerRateLimitError(
                    f"Rate limit exceeded. Retry after {retry_after} seconds"
                )

            response.raise_for_status()

            return response.json()

        except requests.exceptions.Timeout:
            raise ScannerAPIError(f"MangaDex API request timed out after {self.timeout}s")
        except requests.exceptions.ConnectionError as e:
            raise ScannerAPIError(f"Failed to connect to MangaDex API: {e}")
        except requests.exceptions.RequestException as e:
            raise ScannerAPIError(f"MangaDex API request failed: {e}")

    def search_manga(
        self,
        title: str,
        limit: int = 10,
        languages: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Search for manga by title

        Args:
            title: Manga title to search
            limit: Maximum results to return (max 100)
            languages: Optional list of ISO language codes to filter by

        Returns:
            List of manga dictionaries
        """
        params = {
            'title': title,
            'limit': min(limit, 100),
            'includes[]': ['author', 'artist', 'cover_art'],
            'order[relevance]': 'desc'
        }

        # Add language filter if specified
        if languages:
            # MangaDex uses translatedLanguage[] for filtering
            params['availableTranslatedLanguage[]'] = languages

        data = self._request('manga', params)
        return data.get('data', [])

    def get_manga(self, manga_id: str) -> Optional[Dict]:
        """
        Get detailed manga information by ID

        Args:
            manga_id: MangaDex manga UUID

        Returns:
            Manga dictionary with full details
        """
        params = {
            'includes[]': ['author', 'artist', 'cover_art']
        }

        data = self._request(f'manga/{manga_id}', params)
        return data.get('data')


# ============================================================================
# Title Matching and Confidence Scoring
# ============================================================================

def normalize_title(title: str) -> str:
    """Normalize a title for matching"""
    if not title:
        return ""
    title = title.lower()
    # Remove special characters but keep spaces and alphanumeric
    title = re.sub(r'[^\w\s]', '', title)
    title = ' '.join(title.split())
    return title


def calculate_title_similarity(query: str, candidate: str) -> float:
    """Calculate similarity between two titles"""
    query_norm = normalize_title(query)
    candidate_norm = normalize_title(candidate)

    if not query_norm or not candidate_norm:
        return 0.0

    # Exact match
    if query_norm == candidate_norm:
        return EXACT_MATCH_CONFIDENCE

    # Check if one contains the other
    if query_norm in candidate_norm or candidate_norm in query_norm:
        return SUBSTRING_MATCH_CONFIDENCE

    return SequenceMatcher(None, query_norm, candidate_norm).ratio()


def get_best_title_match(query: str, manga: Dict, preferred_languages: List[str]) -> Tuple[float, str]:
    """
    Find best matching title from manga's titles and alt titles

    Args:
        query: Search query
        manga: MangaDex manga object
        preferred_languages: List of preferred language codes

    Returns:
        Tuple of (best_confidence, matched_title)
    """
    attributes = manga.get('attributes', {})

    # Get main titles (multi-lang dict)
    titles = attributes.get('title', {})

    # Get alt titles (list of dicts)
    alt_titles = attributes.get('altTitles', [])

    best_score = 0.0
    matched_title = ""

    # Score main titles, prioritizing preferred languages
    for lang in preferred_languages:
        if lang in titles:
            score = calculate_title_similarity(query, titles[lang])
            if score > best_score:
                best_score = score
                matched_title = titles[lang]

    # Check all main titles
    for lang, title in titles.items():
        score = calculate_title_similarity(query, title)
        if score > best_score:
            best_score = score
            matched_title = title

    # Score alt titles, prioritizing preferred languages
    for alt_title_dict in alt_titles:
        for lang in preferred_languages:
            if lang in alt_title_dict:
                score = calculate_title_similarity(query, alt_title_dict[lang])
                if score > best_score:
                    best_score = score
                    matched_title = alt_title_dict[lang]

    # Check all alt titles
    for alt_title_dict in alt_titles:
        for lang, title in alt_title_dict.items():
            score = calculate_title_similarity(query, title)
            if score > best_score:
                best_score = score
                matched_title = title

    return best_score, matched_title


# ============================================================================
# Metadata Extraction
# ============================================================================

def extract_relationships(manga: Dict, rel_type: str) -> List[Dict]:
    """Extract relationships of a specific type from manga data"""
    relationships = manga.get('relationships', [])
    return [r for r in relationships if r.get('type') == rel_type]


def extract_authors(manga: Dict) -> List[str]:
    """Extract author names from manga relationships"""
    author_rels = extract_relationships(manga, 'author')
    authors = []
    for rel in author_rels:
        attrs = rel.get('attributes', {})
        name = attrs.get('name')
        if name:
            authors.append(name)
    return authors


def extract_artists(manga: Dict) -> List[str]:
    """Extract artist names from manga relationships"""
    artist_rels = extract_relationships(manga, 'artist')
    artists = []
    for rel in artist_rels:
        attrs = rel.get('attributes', {})
        name = attrs.get('name')
        if name:
            artists.append(name)
    return artists


def extract_cover_url(manga: Dict) -> Optional[str]:
    """Extract cover art URL from manga relationships"""
    cover_rels = extract_relationships(manga, 'cover_art')
    if cover_rels:
        attrs = cover_rels[0].get('attributes', {})
        filename = attrs.get('fileName')
        if filename:
            manga_id = manga.get('id')
            return f"https://uploads.mangadex.org/covers/{manga_id}/{filename}"
    return None


def extract_tags(manga: Dict) -> Tuple[List[str], List[str]]:
    """
    Extract tags and genres from manga

    Returns:
        Tuple of (genres, tags)
    """
    attributes = manga.get('attributes', {})
    tags = attributes.get('tags', [])

    genres = []
    other_tags = []

    for tag in tags:
        tag_attrs = tag.get('attributes', {})
        tag_group = tag_attrs.get('group', '')
        tag_name = tag_attrs.get('name', {}).get('en', '')

        if tag_name:
            if tag_group == 'genre':
                genres.append(tag_name)
            else:
                other_tags.append(tag_name)

    return genres, other_tags


def extract_external_links(manga: Dict) -> Dict[str, str]:
    """Extract external links (MAL, AniList, etc.)"""
    attributes = manga.get('attributes', {})
    links = attributes.get('links', {}) or {}

    # Map MangaDex link keys to readable names
    link_mapping = {
        'al': 'anilist',
        'ap': 'anime-planet',
        'bw': 'bookwalker',
        'mu': 'mangaupdates',
        'nu': 'novelupdates',
        'kt': 'kitsu',
        'amz': 'amazon',
        'ebj': 'ebookjapan',
        'mal': 'myanimelist',
        'raw': 'raw',
        'engtl': 'official_english'
    }

    external_links = {}
    for key, value in links.items():
        readable_key = link_mapping.get(key, key)
        if value:
            # Some links are just IDs, convert to full URLs
            if key == 'mal' and str(value).isdigit():
                value = f"https://myanimelist.net/manga/{value}"
            elif key == 'al' and str(value).isdigit():
                value = f"https://anilist.co/manga/{value}"
            external_links[readable_key] = value

    return external_links


def get_localized_description(manga: Dict, preferred_languages: List[str]) -> str:
    """Get description in preferred language"""
    attributes = manga.get('attributes', {})
    descriptions = attributes.get('description', {}) or {}

    # Try preferred languages first
    for lang in preferred_languages:
        if lang in descriptions and descriptions[lang]:
            return descriptions[lang]

    # Fall back to English
    if 'en' in descriptions and descriptions['en']:
        return descriptions['en']

    # Return any available description
    for desc in descriptions.values():
        if desc:
            return desc

    return ""


def get_primary_title(manga: Dict, preferred_languages: List[str]) -> str:
    """Get primary title in preferred language"""
    attributes = manga.get('attributes', {})
    titles = attributes.get('title', {})

    # Try preferred languages first
    for lang in preferred_languages:
        if lang in titles and titles[lang]:
            return titles[lang]

    # Fall back to English
    if 'en' in titles and titles['en']:
        return titles['en']

    # Return any available title
    for title in titles.values():
        if title:
            return title

    return ""


def get_alternative_titles(manga: Dict) -> List[str]:
    """Get all alternative titles"""
    attributes = manga.get('attributes', {})
    alt_titles = attributes.get('altTitles', [])

    titles = []
    for alt_dict in alt_titles:
        for title in alt_dict.values():
            if title and title not in titles:
                titles.append(title)

    return titles


# ============================================================================
# Scanner Framework Integration (for standalone execution)
# ============================================================================

if ScanLevel is None:
    class ScanLevel(Enum):
        FILE = "file"
        SERIES = "series"
        LIBRARY = "library"

if MatchConfidence is None:
    class MatchConfidence(Enum):
        NONE = 0
        LOW = 1
        MEDIUM = 2
        HIGH = 3
        EXACT = 4

if ScanResult is None:
    @dataclass
    class ScanResult:
        confidence: float
        source_id: Optional[str] = None
        source_url: Optional[str] = None
        metadata: Dict = None
        tags: List[str] = None
        raw_response: Optional[Dict] = None

        def __post_init__(self):
            if self.metadata is None:
                self.metadata = {}
            if self.tags is None:
                self.tags = []

        @property
        def confidence_level(self):
            if self.confidence == 0:
                return MatchConfidence.NONE
            elif self.confidence < 0.4:
                return MatchConfidence.LOW
            elif self.confidence < 0.7:
                return MatchConfidence.MEDIUM
            elif self.confidence < 0.9:
                return MatchConfidence.HIGH
            else:
                return MatchConfidence.EXACT

        def to_dict(self) -> Dict:
            """Convert to dictionary for storage"""
            return {
                'confidence': self.confidence,
                'confidence_level': self.confidence_level.name,
                'source_id': self.source_id,
                'source_url': self.source_url,
                'metadata': self.metadata,
                'tags': self.tags
            }


# Define BaseScanner for standalone execution if not imported
if 'BaseScanner' not in globals() or globals()['BaseScanner'] is ABC:
    class BaseScanner(ABC):
        def __init__(self, config: Optional[Dict] = None):
            self.config = config or {}
            self._validate_config()

        @property
        @abstractmethod
        def source_name(self) -> str:
            pass

        @property
        @abstractmethod
        def scan_level(self) -> ScanLevel:
            pass

        @abstractmethod
        def scan(self, query: str, **kwargs) -> Tuple[Optional[ScanResult], List[ScanResult]]:
            pass

        def _validate_config(self):
            pass

        def get_required_config_keys(self) -> List[str]:
            return []


# ============================================================================
# MangaDex Scanner Implementation
# ============================================================================

class MangaDexScanner(BaseScanner):
    """
    MangaDex metadata scanner for manga

    Operates at SERIES level - scans series metadata from MangaDex.org
    Uses MangaDex REST API (no authentication required)
    Rate limit: 5 requests per second
    """

    @property
    def source_name(self) -> str:
        return "MangaDex"

    @property
    def scan_level(self) -> ScanLevel:
        return ScanLevel.SERIES

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize MangaDex scanner

        Config options:
            - confidence_threshold: Minimum confidence to accept (default: 0.6)
            - max_results: Maximum search results (default: 10)
            - timeout: API timeout in seconds (default: 30)
            - rate_limit_delay: Delay between requests (default: 0.2 for 5 req/s)
            - languages: List of preferred language codes (default: ["en"])
        """
        super().__init__(config)
        self.confidence_threshold = self.config.get('confidence_threshold', 0.6)
        self.max_results = self.config.get('max_results', 10)
        self.timeout = self.config.get('timeout', 30)
        self.rate_limit_delay = self.config.get('rate_limit_delay', RATE_LIMIT_DELAY)
        self.languages = self.config.get('languages', ['en'])

        self.api = MangaDexAPI(
            timeout=self.timeout,
            rate_limit_delay=self.rate_limit_delay
        )

    def scan(self, query: str, **kwargs) -> Tuple[Optional[ScanResult], List[ScanResult]]:
        """
        Scan MangaDex for manga metadata

        Args:
            query: Manga title to search for
            **kwargs:
                - confidence_threshold: Override default threshold
                - max_results: Override max results
                - languages: Override language filter

        Returns:
            (best_match, all_candidates)
        """
        confidence_threshold = kwargs.get('confidence_threshold', self.confidence_threshold)
        max_results = kwargs.get('max_results', self.max_results)
        languages = kwargs.get('languages', self.languages)

        try:
            # Search for manga
            results = self.api.search_manga(
                title=query,
                limit=max_results,
                languages=languages if languages else None
            )

            if not results:
                return None, []

            scored_results = []
            for manga in results:
                # Calculate confidence based on title matching
                confidence, matched_title = get_best_title_match(query, manga, languages)

                if confidence >= confidence_threshold:
                    scan_result = self._build_result(manga, confidence, languages)
                    scored_results.append(scan_result)

            if not scored_results:
                return None, []

            scored_results.sort(key=lambda x: x.confidence, reverse=True)

            return scored_results[0], scored_results

        except (ScannerRateLimitError,):
            raise
        except Exception as e:
            logger.error(f"MangaDex scan failed: {e}")
            raise ScannerAPIError(f"MangaDex scan failed: {e}") from e

    def _build_result(self, manga: Dict, confidence: float, languages: List[str]) -> ScanResult:
        """Convert MangaDex manga to ScanResult"""

        manga_id = manga.get('id')
        attributes = manga.get('attributes', {})

        # Extract metadata
        authors = extract_authors(manga)
        artists = extract_artists(manga)
        genres, tags = extract_tags(manga)
        external_links = extract_external_links(manga)

        # Get localized content
        title = get_primary_title(manga, languages)
        description = get_localized_description(manga, languages)
        alt_titles = get_alternative_titles(manga)

        # Get cover URL
        cover_url = extract_cover_url(manga)

        # Map status to standardized format
        status_mapping = {
            'ongoing': 'Ongoing',
            'completed': 'Completed',
            'hiatus': 'Hiatus',
            'cancelled': 'Cancelled'
        }
        status = status_mapping.get(attributes.get('status', ''), attributes.get('status', ''))

        # Build metadata dict following the mapping requirements
        metadata = {
            # Core fields
            'title': title,
            'series': title,
            'alternative_titles': alt_titles,
            'description': description,
            'synopsis': description,  # Alias for compatibility

            # People
            'writer': ', '.join(authors) if authors else '',
            'artist': ', '.join(artists) if artists else '',

            # Classification
            'genre': ', '.join(genres) if genres else '',
            'tags': '\n'.join(tags) if tags else '',

            # Status and dates
            'status': status,
            'year': attributes.get('year'),

            # Content info
            'content_rating': attributes.get('contentRating', ''),
            'original_language': attributes.get('originalLanguage', ''),
            'latest_chapter': attributes.get('lastChapter', ''),

            # External links
            'external_links': external_links,

            # MangaDex specific - for cover provider
            'mangadex_id': manga_id,
            'cover_image': cover_url,

            # Source info
            'source': self.source_name,
        }

        # Clean up None values
        metadata = {k: v for k, v in metadata.items() if v is not None}

        # Build source URL
        source_url = f"https://mangadex.org/title/{manga_id}"

        # Combine genres and tags for the tags list
        all_tags = list(genres) + list(tags)

        return ScanResult(
            confidence=confidence,
            source_id=manga_id,
            source_url=source_url,
            metadata=metadata,
            tags=all_tags,
            raw_response=manga
        )

    def get_config_schema(self) -> List['ConfigOption']:
        """Get declarative configuration schema for MangaDex scanner"""
        try:
            from src.scanners.config_schema import ConfigOption, ConfigType
        except ImportError:
            return []

        return [
            ConfigOption(
                key="languages",
                type=ConfigType.MULTI_SELECT,
                label="Preferred Languages",
                description="ISO language codes to filter results (e.g., en, ja, ko)",
                default=["en"],
                options=["en", "ja", "ko", "zh", "zh-hk", "es", "es-la", "fr", "de", "it", "pt", "pt-br", "ru", "pl", "vi", "th", "id", "tr", "ar", "uk"],
                required=False
            ),
            ConfigOption(
                key="confidence_threshold",
                type=ConfigType.FLOAT,
                label="Confidence Threshold",
                description="Minimum confidence score (0.0-1.0) to accept a match",
                default=0.6,
                min_value=0.0,
                max_value=1.0,
                step=0.05,
                required=False
            ),
            ConfigOption(
                key="max_results",
                type=ConfigType.INTEGER,
                label="Max Search Results",
                description="Maximum number of search results to fetch",
                default=10,
                min_value=1,
                max_value=100,
                required=False,
                advanced=True
            ),
            ConfigOption(
                key="timeout",
                type=ConfigType.INTEGER,
                label="API Timeout",
                description="Request timeout in seconds",
                default=30,
                min_value=5,
                max_value=120,
                required=False,
                advanced=True
            ),
            ConfigOption(
                key="rate_limit_delay",
                type=ConfigType.FLOAT,
                label="Rate Limit Delay",
                description="Delay between API requests in seconds (0.2 = 5 req/sec)",
                default=0.2,
                min_value=0.1,
                max_value=5.0,
                step=0.1,
                required=False,
                advanced=True
            ),
        ]


# ============================================================================
# Standalone Functions (for direct usage)
# ============================================================================

def search_manga(title: str, max_results: int = 5, languages: Optional[List[str]] = None) -> List[Dict]:
    """
    Search for manga on MangaDex

    Args:
        title: Manga title to search
        max_results: Maximum results to return
        languages: Optional language filter

    Returns:
        List of manga dictionaries
    """
    api = MangaDexAPI()
    return api.search_manga(title, limit=max_results, languages=languages)


def get_manga_metadata(
    title: str,
    confidence_threshold: float = 0.6,
    languages: Optional[List[str]] = None
) -> Optional[Dict]:
    """
    Get metadata for a manga series

    Args:
        title: Manga title
        confidence_threshold: Minimum confidence for match
        languages: Preferred languages

    Returns:
        Metadata dictionary or None
    """
    config = {
        'confidence_threshold': confidence_threshold,
    }
    if languages:
        config['languages'] = languages

    scanner = MangaDexScanner(config)
    best_match, _ = scanner.scan(title)

    if best_match:
        return best_match.to_dict()
    return None


# ============================================================================
# Command Line Interface
# ============================================================================

def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(
        description='MangaDex Manga Metadata Scanner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Search for a manga:
    %(prog)s "One Piece"

  Filter by language:
    %(prog)s "進撃の巨人" --languages ja en

  Lower confidence threshold:
    %(prog)s "Naruto" --threshold 0.5
        """
    )

    parser.add_argument('title', help='Manga title to search for')
    parser.add_argument('--threshold', type=float, default=0.6,
                        help='Confidence threshold (0.0-1.0, default: 0.6)')
    parser.add_argument('--max-results', type=int, default=5,
                        help='Maximum search results (default: 5)')
    parser.add_argument('--languages', nargs='+', default=['en'],
                        help='Preferred languages (default: en)')
    parser.add_argument('--json', action='store_true',
                        help='Output as JSON')

    args = parser.parse_args()

    try:
        scanner = MangaDexScanner({
            'confidence_threshold': args.threshold,
            'max_results': args.max_results,
            'languages': args.languages
        })

        print(f"Searching MangaDex for: {args.title}")
        print(f"Languages: {', '.join(args.languages)}")
        print(f"Confidence threshold: {args.threshold}")
        print("-" * 60)

        best_match, all_matches = scanner.scan(args.title)

        if not best_match:
            print("No matches found.")
            return 1

        if args.json:
            output = {
                'best_match': best_match.to_dict(),
                'all_matches': [m.to_dict() for m in all_matches]
            }
            print(json.dumps(output, indent=2, ensure_ascii=False))
        else:
            print(f"\n✓ Best Match (Confidence: {best_match.confidence:.2%})")
            print("=" * 60)

            meta = best_match.metadata
            print(f"Title: {meta.get('title')}")
            print(f"MangaDex ID: {meta.get('mangadex_id')}")

            if meta.get('writer'):
                print(f"Author: {meta.get('writer')}")

            if meta.get('artist'):
                print(f"Artist: {meta.get('artist')}")

            if meta.get('year'):
                print(f"Year: {meta.get('year')}")

            if meta.get('status'):
                print(f"Status: {meta.get('status')}")

            if meta.get('genre'):
                print(f"Genres: {meta.get('genre')}")

            if meta.get('content_rating'):
                print(f"Rating: {meta.get('content_rating')}")

            if meta.get('original_language'):
                print(f"Original Language: {meta.get('original_language')}")

            print(f"\nMangaDex URL: {best_match.source_url}")

            if meta.get('external_links'):
                print("\nExternal Links:")
                for name, url in meta['external_links'].items():
                    print(f"  - {name}: {url}")

            # Show other matches
            if len(all_matches) > 1:
                print("\n" + "=" * 60)
                print(f"Other Matches ({len(all_matches) - 1}):")
                print("=" * 60)

                for i, match in enumerate(all_matches[1:], 1):
                    m = match.metadata
                    print(f"\n{i}. {m.get('title')} (Confidence: {match.confidence:.2%})")
                    if m.get('writer'):
                        print(f"   Author: {m.get('writer')}")
                    if m.get('year'):
                        print(f"   Year: {m.get('year')}")

        return 0

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 130
    except ScannerRateLimitError as e:
        print(f"\nRate Limit Error: {e}")
        return 1
    except ScannerAPIError as e:
        print(f"\nAPI Error: {e}")
        return 1
    except Exception as e:
        print(f"\nError: {e}")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
