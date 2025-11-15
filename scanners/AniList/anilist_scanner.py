#!/usr/bin/env python3
"""
AniList Scanner - Metadata Scanner for Manga and Light Novels

A complete, self-contained scanner for extracting metadata from AniList.co.
This scanner uses the AniList GraphQL API to fetch manga and light novel metadata.

Features:
- AniList GraphQL API client
- Series-level metadata extraction
- Fuzzy matching with confidence scores
- Staff and character information
- Genre and tag extraction
- Multiple title format support (Romaji, English, Native)

Usage:
    python anilist_scanner.py "Berserk"

    Or import as a module:
    from anilist_scanner import AniListScanner, search_manga
"""

import re
import json
import time
import argparse
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from difflib import SequenceMatcher
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum

import requests


# ============================================================================
# AniList API Client
# ============================================================================

class AniListAPI:
    """
    Client for the AniList GraphQL API
    
    Official API documentation: https://anilist.gitbook.io/anilist-apiv2-docs/
    """
    
    BASE_URL = "https://graphql.anilist.co"
    
    def __init__(self, timeout: int = 10, rate_limit_delay: float = 0.7):
        """
        Initialize AniList API client
        
        Args:
            timeout: Request timeout in seconds
            rate_limit_delay: Delay between requests to respect rate limits (90 req/min)
        """
        self.timeout = timeout
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = 0
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })
    
    def _wait_for_rate_limit(self):
        """Ensure we don't exceed rate limits"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()
    
    def _query(self, query: str, variables: Dict = None) -> Dict:
        """
        Execute a GraphQL query
        
        Args:
            query: GraphQL query string
            variables: Query variables
            
        Returns:
            Response data dictionary
            
        Raises:
            Exception: On API errors
        """
        self._wait_for_rate_limit()
        
        payload = {
            'query': query,
            'variables': variables or {}
        }
        
        try:
            response = self.session.post(
                self.BASE_URL,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            if 'errors' in data:
                errors = data['errors']
                error_msgs = [e.get('message', str(e)) for e in errors]
                raise Exception(f"GraphQL errors: {', '.join(error_msgs)}")
            
            return data.get('data', {})
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"AniList API request failed: {e}")
    
    def search_manga(self, title: str, page: int = 1, per_page: int = 10) -> List[Dict]:
        """
        Search for manga by title
        
        Args:
            title: Search query
            page: Page number
            per_page: Results per page (max 50)
            
        Returns:
            List of manga dictionaries
        """
        query = '''
        query ($search: String, $page: Int, $perPage: Int, $type: MediaType) {
          Page(page: $page, perPage: $perPage) {
            pageInfo {
              total
              currentPage
              lastPage
              hasNextPage
              perPage
            }
            media(search: $search, type: $type, format_in: [MANGA, ONE_SHOT, NOVEL]) {
              id
              idMal
              title {
                romaji
                english
                native
              }
              format
              status
              description
              startDate {
                year
                month
                day
              }
              endDate {
                year
                month
                day
              }
              chapters
              volumes
              coverImage {
                large
                medium
              }
              bannerImage
              genres
              tags {
                name
                rank
                isMediaSpoiler
              }
              averageScore
              popularity
              staff {
                edges {
                  role
                  node {
                    id
                    name {
                      full
                      native
                    }
                  }
                }
              }
              characters(sort: ROLE, perPage: 10) {
                edges {
                  role
                  node {
                    id
                    name {
                      full
                      native
                    }
                  }
                }
              }
              relations {
                edges {
                  relationType
                  node {
                    id
                    title {
                      romaji
                      english
                    }
                    type
                    format
                  }
                }
              }
              siteUrl
            }
          }
        }
        '''
        
        variables = {
            'search': title,
            'page': page,
            'perPage': per_page,
            'type': 'MANGA'
        }
        
        data = self._query(query, variables)
        return data.get('Page', {}).get('media', [])
    
    def get_manga_by_id(self, media_id: int) -> Optional[Dict]:
        """
        Get manga details by ID
        
        Args:
            media_id: AniList media ID
            
        Returns:
            Manga dictionary or None
        """
        query = '''
        query ($id: Int) {
          Media(id: $id, type: MANGA) {
            id
            idMal
            title {
              romaji
              english
              native
            }
            format
            status
            description
            startDate {
              year
              month
              day
            }
            endDate {
              year
              month
              day
            }
            chapters
            volumes
            coverImage {
              large
              medium
            }
            bannerImage
            genres
            tags {
              name
              rank
              isMediaSpoiler
            }
            averageScore
            popularity
            staff {
              edges {
                role
                node {
                  id
                  name {
                    full
                    native
                  }
                }
              }
            }
            characters(sort: ROLE, perPage: 10) {
              edges {
                role
                node {
                  id
                  name {
                    full
                    native
                  }
                }
              }
            }
            relations {
              edges {
                relationType
                node {
                  id
                  title {
                    romaji
                    english
                  }
                  type
                  format
                }
              }
            }
            siteUrl
          }
        }
        '''
        
        variables = {'id': media_id}
        data = self._query(query, variables)
        return data.get('Media')


# ============================================================================
# Title Matching and Confidence Scoring
# ============================================================================

def normalize_title(title: str) -> str:
    """
    Normalize a title for matching
    
    Args:
        title: Original title
        
    Returns:
        Normalized title
    """
    if not title:
        return ""
    
    # Convert to lowercase
    title = title.lower()
    
    # Remove special characters but keep spaces and alphanumeric
    title = re.sub(r'[^\w\s]', '', title)
    
    # Normalize whitespace
    title = ' '.join(title.split())
    
    return title


def calculate_title_similarity(query: str, candidate: str) -> float:
    """
    Calculate similarity between two titles
    
    Args:
        query: Query title
        candidate: Candidate title
        
    Returns:
        Similarity score (0.0 to 1.0)
    """
    query_norm = normalize_title(query)
    candidate_norm = normalize_title(candidate)
    
    if not query_norm or not candidate_norm:
        return 0.0
    
    # Exact match
    if query_norm == candidate_norm:
        return 1.0
    
    # Check if one contains the other
    if query_norm in candidate_norm or candidate_norm in query_norm:
        return 0.9
    
    # Use sequence matcher for fuzzy matching
    return SequenceMatcher(None, query_norm, candidate_norm).ratio()


def match_manga_title(query: str, manga: Dict, use_romaji: bool = True, 
                     use_english: bool = True, use_native: bool = False) -> float:
    """
    Match a query against a manga's titles
    
    Args:
        query: Query string
        manga: Manga dictionary from API
        use_romaji: Consider romaji title
        use_english: Consider English title
        use_native: Consider native title
        
    Returns:
        Best match score (0.0 to 1.0)
    """
    titles = manga.get('title', {})
    scores = []
    
    if use_romaji and titles.get('romaji'):
        scores.append(calculate_title_similarity(query, titles['romaji']))
    
    if use_english and titles.get('english'):
        scores.append(calculate_title_similarity(query, titles['english']))
    
    if use_native and titles.get('native'):
        scores.append(calculate_title_similarity(query, titles['native']))
    
    return max(scores) if scores else 0.0


# ============================================================================
# Metadata Extraction
# ============================================================================

def extract_staff(manga: Dict) -> Dict[str, List[str]]:
    """
    Extract staff information from manga data
    
    Args:
        manga: Manga dictionary
        
    Returns:
        Dictionary mapping roles to staff names
    """
    staff_dict = {}
    staff_edges = manga.get('staff', {}).get('edges', [])
    
    for edge in staff_edges:
        role = edge.get('role', 'Unknown')
        name = edge.get('node', {}).get('name', {}).get('full', '')
        
        if name:
            # Normalize role name
            role = role.lower()
            
            # Map common roles
            if 'story' in role or 'author' in role or 'original creator' in role:
                key = 'writer'
            elif 'art' in role or 'illustrator' in role or 'character design' in role:
                key = 'artist'
            else:
                key = 'other'
            
            if key not in staff_dict:
                staff_dict[key] = []
            staff_dict[key].append(name)
    
    return staff_dict


def extract_characters(manga: Dict, max_count: int = 10) -> List[str]:
    """
    Extract main character names
    
    Args:
        manga: Manga dictionary
        max_count: Maximum number of characters to extract
        
    Returns:
        List of character names
    """
    characters = []
    char_edges = manga.get('characters', {}).get('edges', [])
    
    for edge in char_edges[:max_count]:
        role = edge.get('role', '')
        name = edge.get('node', {}).get('name', {}).get('full', '')
        
        if name and role in ['MAIN', 'SUPPORTING']:
            characters.append(name)
    
    return characters


def extract_genres_and_tags(manga: Dict, include_spoiler_tags: bool = False) -> Tuple[List[str], List[str]]:
    """
    Extract genres and tags
    
    Args:
        manga: Manga dictionary
        include_spoiler_tags: Include tags marked as spoilers
        
    Returns:
        Tuple of (genres, tags)
    """
    genres = manga.get('genres', [])
    
    tags = []
    tag_list = manga.get('tags', [])
    for tag in tag_list:
        if tag.get('isMediaSpoiler', False) and not include_spoiler_tags:
            continue
        name = tag.get('name', '')
        if name:
            tags.append(name)
    
    return genres, tags


def format_date(date_dict: Optional[Dict]) -> Optional[str]:
    """
    Format a date dictionary to string
    
    Args:
        date_dict: Dictionary with year, month, day keys
        
    Returns:
        Formatted date string or None
    """
    if not date_dict:
        return None
    
    year = date_dict.get('year')
    month = date_dict.get('month')
    day = date_dict.get('day')
    
    if year:
        if month and day:
            return f"{year}-{month:02d}-{day:02d}"
        elif month:
            return f"{year}-{month:02d}"
        else:
            return str(year)
    
    return None


def clean_html_description(html: Optional[str]) -> str:
    """
    Clean HTML tags from description
    
    Args:
        html: HTML string
        
    Returns:
        Plain text
    """
    if not html:
        return ""
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', html)
    
    # Decode common HTML entities
    text = text.replace('&quot;', '"')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&nbsp;', ' ')
    text = text.replace('<br>', '\n')
    
    # Clean up whitespace
    text = '\n'.join(line.strip() for line in text.split('\n'))
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


# ============================================================================
# Scanner Framework Integration
# ============================================================================

class ScanLevel(Enum):
    """What level the scanner operates at"""
    FILE = "file"
    SERIES = "series"
    LIBRARY = "library"


class MatchConfidence(Enum):
    """Confidence level for metadata matches"""
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    EXACT = 4


@dataclass
class ScanResult:
    """Result from a metadata scan"""
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
    def confidence_level(self) -> MatchConfidence:
        """Get confidence as an enum"""
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


class BaseScanner(ABC):
    """Base class for all metadata scanners"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self._validate_config()
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Name of the metadata source"""
        pass
    
    @property
    @abstractmethod
    def scan_level(self) -> ScanLevel:
        """What level this scanner operates at"""
        pass
    
    @abstractmethod
    def scan(self, query: str, **kwargs) -> Tuple[Optional[ScanResult], List[ScanResult]]:
        """Scan for metadata based on a query"""
        pass
    
    def _validate_config(self):
        """Validate scanner configuration"""
        pass
    
    def get_required_config_keys(self) -> List[str]:
        """Get list of required configuration keys"""
        return []


class ScannerError(Exception):
    """Base exception for scanner errors"""
    pass


class ScannerAPIError(ScannerError):
    """API communication error"""
    pass


# ============================================================================
# AniList Scanner Implementation
# ============================================================================

class AniListScanner(BaseScanner):
    """
    AniList metadata scanner for manga and light novels
    
    Operates at SERIES level - scans series metadata
    Uses AniList GraphQL API for metadata extraction
    """
    
    @property
    def source_name(self) -> str:
        return "AniList"
    
    @property
    def scan_level(self) -> ScanLevel:
        return ScanLevel.SERIES
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize AniList scanner
        
        Config options:
            - confidence_threshold: Minimum confidence to accept (default: 0.6)
            - use_romaji_titles: Match romaji titles (default: True)
            - use_english_titles: Match English titles (default: True)
            - use_native_titles: Match native titles (default: False)
            - timeout: API request timeout (default: 10)
            - rate_limit_delay: Delay between requests (default: 0.7)
            - max_results: Maximum search results (default: 10)
            - max_characters: Maximum characters to extract (default: 10)
            - include_spoiler_tags: Include spoiler tags (default: False)
        """
        super().__init__(config)
        self.confidence_threshold = self.config.get('confidence_threshold', 0.6)
        self.use_romaji = self.config.get('use_romaji_titles', True)
        self.use_english = self.config.get('use_english_titles', True)
        self.use_native = self.config.get('use_native_titles', False)
        self.max_results = self.config.get('max_results', 10)
        self.max_characters = self.config.get('max_characters', 10)
        self.include_spoiler_tags = self.config.get('include_spoiler_tags', False)
        
        # Initialize API client
        timeout = self.config.get('timeout', 10)
        rate_limit_delay = self.config.get('rate_limit_delay', 0.7)
        self.api = AniListAPI(timeout=timeout, rate_limit_delay=rate_limit_delay)
    
    def scan(self, query: str, **kwargs) -> Tuple[Optional[ScanResult], List[ScanResult]]:
        """
        Scan AniList for manga metadata
        
        Args:
            query: Series name to search for
            **kwargs:
                - confidence_threshold: Override default threshold
                - max_results: Override max results
                
        Returns:
            (best_match, all_candidates)
        """
        # Override config with kwargs
        confidence_threshold = kwargs.get('confidence_threshold', self.confidence_threshold)
        max_results = kwargs.get('max_results', self.max_results)
        
        try:
            # Search for manga
            results = self.api.search_manga(query, per_page=max_results)
            
            if not results:
                return None, []
            
            # Score all results
            scored_results = []
            for manga in results:
                confidence = match_manga_title(
                    query, manga,
                    use_romaji=self.use_romaji,
                    use_english=self.use_english,
                    use_native=self.use_native
                )
                
                if confidence >= confidence_threshold:
                    scan_result = self._build_result(manga, confidence)
                    scored_results.append(scan_result)
            
            if not scored_results:
                return None, []
            
            # Sort by confidence
            scored_results.sort(key=lambda x: x.confidence, reverse=True)
            
            return scored_results[0], scored_results
            
        except Exception as e:
            raise ScannerAPIError(f"AniList scan failed: {e}") from e
    
    def _build_result(self, manga: Dict, confidence: float) -> ScanResult:
        """Convert AniList response to ScanResult"""
        
        # Extract staff
        staff = extract_staff(manga)
        writers = ', '.join(staff.get('writer', []))
        artists = ', '.join(staff.get('artist', []))
        
        # Extract characters
        characters = extract_characters(manga, self.max_characters)
        characters_str = ', '.join(characters)
        
        # Extract genres and tags
        genres, tags = extract_genres_and_tags(manga, self.include_spoiler_tags)
        genre_str = ', '.join(genres)
        
        # Get titles
        titles = manga.get('title', {})
        title_romaji = titles.get('romaji', '')
        title_english = titles.get('english', '')
        title_native = titles.get('native', '')
        
        # Prefer English title, fallback to Romaji
        primary_title = title_english or title_romaji or title_native
        
        # Get description
        description = clean_html_description(manga.get('description'))
        
        # Format dates
        start_date = format_date(manga.get('startDate'))
        end_date = format_date(manga.get('endDate'))
        
        # Extract year from start date
        year = None
        if start_date:
            year_match = re.match(r'^(\d{4})', start_date)
            if year_match:
                year = int(year_match.group(1))
        
        # Get format and map to ComicInfo format
        anilist_format = manga.get('format', '')
        format_mapping = {
            'MANGA': 'Manga',
            'ONE_SHOT': 'One-Shot',
            'NOVEL': 'Light Novel',
            'MANHWA': 'Manhwa',
            'MANHUA': 'Manhua'
        }
        comic_format = format_mapping.get(anilist_format, anilist_format)
        
        # Build metadata dict
        scan_metadata = {
            # Core fields
            'title': primary_title,
            'series': primary_title,
            'description': description,
            'year': year,
            
            # People
            'writer': writers,
            'artist': artists,
            
            # Classification
            'genre': genre_str,
            'format': comic_format,
            'language_iso': 'en',  # AniList doesn't specify, default to English
            
            # Lists
            'characters': characters_str,
            
            # Counts
            'volume': manga.get('volumes'),
            'count': manga.get('chapters'),
            
            # Additional AniList-specific data
            'title_romaji': title_romaji,
            'title_english': title_english,
            'title_native': title_native,
            'status': manga.get('status'),
            'start_date': start_date,
            'end_date': end_date,
            'average_score': manga.get('averageScore'),
            'popularity': manga.get('popularity'),
            'cover_image': manga.get('coverImage', {}).get('large'),
            'banner_image': manga.get('bannerImage'),
            'mal_id': manga.get('idMal'),
            
            # Source info
            'source': self.source_name,
        }
        
        # Build tag list
        all_tags = []
        all_tags.extend(genres)
        all_tags.extend(tags)
        
        return ScanResult(
            confidence=confidence,
            source_id=str(manga.get('id')),
            source_url=manga.get('siteUrl'),
            metadata=scan_metadata,
            tags=all_tags,
            raw_response=manga
        )


# ============================================================================
# Standalone Functions (for direct usage)
# ============================================================================

def search_manga(title: str, max_results: int = 5) -> List[Dict]:
    """
    Search for manga on AniList
    
    Args:
        title: Series title to search
        max_results: Maximum results to return
        
    Returns:
        List of manga dictionaries
    """
    api = AniListAPI()
    return api.search_manga(title, per_page=max_results)


def get_manga_metadata(title: str, confidence_threshold: float = 0.6) -> Optional[Dict]:
    """
    Get metadata for a manga series
    
    Args:
        title: Series title
        confidence_threshold: Minimum confidence for match
        
    Returns:
        Metadata dictionary or None
    """
    scanner = AniListScanner()
    best_match, _ = scanner.scan(title, confidence_threshold=confidence_threshold)
    
    if best_match:
        return best_match.to_dict()
    return None


# ============================================================================
# Command Line Interface
# ============================================================================

def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(
        description='AniList Manga Metadata Scanner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Search for a manga:
    %(prog)s "Berserk"
    
  Get detailed metadata:
    %(prog)s "One Piece" --detailed
    
  Lower confidence threshold:
    %(prog)s "Vagabond" --threshold 0.5
        """
    )
    
    parser.add_argument('title', help='Manga title to search for')
    parser.add_argument('--threshold', type=float, default=0.6,
                       help='Confidence threshold (0.0-1.0, default: 0.6)')
    parser.add_argument('--max-results', type=int, default=5,
                       help='Maximum search results (default: 5)')
    parser.add_argument('--detailed', action='store_true',
                       help='Show detailed metadata')
    parser.add_argument('--json', action='store_true',
                       help='Output as JSON')
    
    args = parser.parse_args()
    
    try:
        scanner = AniListScanner({
            'confidence_threshold': args.threshold,
            'max_results': args.max_results
        })
        
        print(f"Searching AniList for: {args.title}")
        print(f"Confidence threshold: {args.threshold}")
        print("-" * 60)
        
        best_match, all_matches = scanner.scan(args.title)
        
        if not best_match:
            print("No matches found.")
            return 1
        
        if args.json:
            # JSON output
            output = {
                'best_match': best_match.to_dict(),
                'all_matches': [m.to_dict() for m in all_matches]
            }
            print(json.dumps(output, indent=2, ensure_ascii=False))
        else:
            # Human-readable output
            print(f"\n✓ Best Match (Confidence: {best_match.confidence:.2%})")
            print("=" * 60)
            
            meta = best_match.metadata
            print(f"Title: {meta.get('title')}")
            print(f"Series: {meta.get('series')}")
            
            if meta.get('writer'):
                print(f"Writer: {meta.get('writer')}")
            if meta.get('artist'):
                print(f"Artist: {meta.get('artist')}")
            
            if meta.get('year'):
                print(f"Year: {meta.get('year')}")
            
            if meta.get('genre'):
                print(f"Genres: {meta.get('genre')}")
            
            if meta.get('format'):
                print(f"Format: {meta.get('format')}")
            
            if meta.get('status'):
                print(f"Status: {meta.get('status')}")
            
            if meta.get('volume'):
                print(f"Volumes: {meta.get('volume')}")
            
            if meta.get('count'):
                print(f"Chapters: {meta.get('count')}")
            
            print(f"\nAniList URL: {best_match.source_url}")
            
            if args.detailed:
                print("\n" + "=" * 60)
                print("DETAILED METADATA")
                print("=" * 60)
                
                if meta.get('description'):
                    print(f"\nDescription:\n{meta.get('description')[:500]}...")
                
                if meta.get('characters'):
                    print(f"\nMain Characters: {meta.get('characters')}")
                
                if best_match.tags:
                    print(f"\nTags: {', '.join(best_match.tags[:10])}")
                
                if meta.get('average_score'):
                    print(f"\nAverage Score: {meta.get('average_score')}/100")
                
                if meta.get('popularity'):
                    print(f"Popularity: {meta.get('popularity')}")
            
            # Show other matches
            if len(all_matches) > 1:
                print("\n" + "=" * 60)
                print(f"Other Matches ({len(all_matches) - 1}):")
                print("=" * 60)
                
                for i, match in enumerate(all_matches[1:], 1):
                    meta = match.metadata
                    print(f"\n{i}. {meta.get('title')} (Confidence: {match.confidence:.2%})")
                    if meta.get('writer'):
                        print(f"   Writer: {meta.get('writer')}")
                    if meta.get('year'):
                        print(f"   Year: {meta.get('year')}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 130
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        if '--debug' in sys.argv:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
