#!/usr/bin/env python3
"""
Metron Scanner - Metadata Scanner for Comics

A complete, self-contained scanner for extracting metadata from Metron.cloud.
This scanner uses the Metron REST API to fetch comic metadata.

Features:
- Metron API client with authentication
- Series/Volume level metadata extraction
- Fuzzy matching with confidence scores
- Staff (Writer, Artist, Cover Artist) extraction
- Character, story arc extraction
- Publisher information

Usage:
    python metron_scanner.py "Batman" --username YOUR_USERNAME --password YOUR_PASSWORD

    Or import as a module:
    from metron_scanner import MetronScanner
"""

import re
import json
import time
import logging
from typing import List, Tuple, Optional, Dict, Any
from difflib import SequenceMatcher
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum

try:
    # Import from src.scanners package
    from src.scanners.base_scanner import (
        BaseScanner, ScanResult, ScanLevel, MatchConfidence,
        ScannerAPIError, ScannerConfigError, ScannerRateLimitError
    )
    from src.scanners.config_schema import ConfigOption, ConfigType
except ImportError:
    # Fallback for standalone execution
    BaseScanner = ABC
    ScanResult = None
    ScanLevel = None
    MatchConfidence = None
    ScannerAPIError = Exception
    ScannerConfigError = Exception
    ScannerRateLimitError = Exception

import requests

logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

# Confidence scoring constants
YEAR_MATCH_CONFIDENCE_BOOST = 0.1
SUBSTRING_MATCH_CONFIDENCE = 0.9
EXACT_MATCH_CONFIDENCE = 1.0
MAX_CONFIDENCE = 1.0

# User-Agent for API requests
USER_AGENT = 'YACLib-Enhanced (Compatible; MetronScanner)'


# ============================================================================
# Metron API Client
# ============================================================================

class MetronAPI:
    """
    Client for the Metron REST API

    Official API documentation: https://metron.cloud/docs/
    """

    BASE_URL = "https://metron.cloud/api"

    def __init__(
        self,
        username: str,
        password: str,
        timeout: int = 30,
        rate_limit_delay: float = 1.0
    ):
        """
        Initialize Metron API client

        Args:
            username: Metron username
            password: Metron password
            timeout: Request timeout in seconds
            rate_limit_delay: Delay between requests to respect rate limits
        """
        self.username = username
        self.password = password
        self.timeout = timeout
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = 0
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept': 'application/json',
        })
        # Set basic auth
        self.session.auth = (username, password)

    def _wait_for_rate_limit(self):
        """Ensure we don't exceed rate limits"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()

    def _request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Execute an API request

        Args:
            endpoint: API endpoint (e.g., "series")
            params: Query parameters

        Returns:
            Response data dictionary

        Raises:
            ScannerConfigError: If credentials are missing
            ScannerRateLimitError: If rate limited
            ScannerAPIError: On other API errors
        """
        if not self.username or not self.password:
            raise ScannerConfigError("Metron username and password are required")

        self._wait_for_rate_limit()

        url = f"{self.BASE_URL}/{endpoint}/"

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

            # Handle authentication errors
            if response.status_code == 401:
                raise ScannerConfigError("Invalid Metron credentials")

            response.raise_for_status()

            return response.json()

        except requests.exceptions.Timeout:
            raise ScannerAPIError(f"Metron API request timed out after {self.timeout}s")
        except requests.exceptions.ConnectionError as e:
            raise ScannerAPIError(f"Failed to connect to Metron API: {e}")
        except requests.exceptions.RequestException as e:
            raise ScannerAPIError(f"Metron API request failed: {e}")

    def search_series(self, name: str) -> List[Dict]:
        """
        Search for comic series by name

        Args:
            name: Series name to search

        Returns:
            List of series dictionaries
        """
        params = {'name': name}
        data = self._request('series', params)
        return data.get('results', [])

    def get_series(self, series_id: int) -> Optional[Dict]:
        """
        Get details for a specific series

        Args:
            series_id: Series ID

        Returns:
            Series details dictionary
        """
        data = self._request(f'series/{series_id}')
        return data

    def search_issues(self, series_id: Optional[int] = None, name: Optional[str] = None) -> List[Dict]:
        """
        Search for issues

        Args:
            series_id: Filter by series ID
            name: Filter by issue name/title

        Returns:
            List of issue dictionaries
        """
        params = {}
        if series_id:
            params['series_id'] = series_id
        if name:
            params['name'] = name
        data = self._request('issue', params)
        return data.get('results', [])

    def get_issue(self, issue_id: int) -> Optional[Dict]:
        """
        Get details for a specific issue

        Args:
            issue_id: Issue ID

        Returns:
            Issue details dictionary
        """
        data = self._request(f'issue/{issue_id}')
        return data

    def search_publishers(self, name: str) -> List[Dict]:
        """
        Search for publishers

        Args:
            name: Publisher name to search

        Returns:
            List of publisher dictionaries
        """
        params = {'name': name}
        data = self._request('publisher', params)
        return data.get('results', [])


# ============================================================================
# Title Matching and Confidence Scoring
# ============================================================================

def normalize_title(title: str) -> str:
    """Normalize a title for matching"""
    if not title:
        return ""
    title = title.lower()
    # Remove common suffixes like volume numbers, years in parentheses
    title = re.sub(r'\s*\(\d{4}\)\s*$', '', title)
    title = re.sub(r'\s*vol\.?\s*\d+\s*$', '', title, flags=re.IGNORECASE)
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
# Metron Scanner Implementation
# ============================================================================

class MetronScanner(BaseScanner):
    """
    Metron metadata scanner for comics

    Operates at SERIES level - scans series metadata from Metron.cloud
    Uses Metron REST API for metadata extraction
    """

    @property
    def source_name(self) -> str:
        return "Metron"

    @property
    def scan_level(self) -> ScanLevel:
        return ScanLevel.SERIES

    def get_required_config_keys(self) -> List[str]:
        return ["username", "password"]

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize Metron scanner

        Config options:
            - username: Metron username (required)
            - password: Metron password (required)
            - confidence_threshold: Minimum confidence to accept (default: 0.6)
            - max_results: Maximum search results (default: 10)
            - timeout: API timeout in seconds (default: 30)
            - rate_limit_delay: Delay between requests (default: 1.0)
        """
        super().__init__(config)
        self.username = self.config.get('username')
        self.password = self.config.get('password')
        self.confidence_threshold = self.config.get('confidence_threshold', 0.6)
        self.max_results = self.config.get('max_results', 10)
        self.timeout = self.config.get('timeout', 30)
        self.rate_limit_delay = self.config.get('rate_limit_delay', 1.0)

        if self.username and self.password:
            self.api = MetronAPI(
                username=self.username,
                password=self.password,
                timeout=self.timeout,
                rate_limit_delay=self.rate_limit_delay
            )
        else:
            self.api = None

    def _validate_config(self):
        # Don't raise error here to allow instantiation for discovery
        # Check is done in scan()
        pass

    def scan(self, query: str, **kwargs) -> Tuple[Optional[ScanResult], List[ScanResult]]:
        """
        Scan Metron for series metadata

        Args:
            query: Series name to search for
            **kwargs:
                - confidence_threshold: Override default threshold
                - max_results: Override max results
                - username: Override username (if not configured)
                - password: Override password (if not configured)

        Returns:
            (best_match, all_candidates)
        """
        # Check for credentials
        username = kwargs.get('username', self.username)
        password = kwargs.get('password', self.password)

        if not self.api:
            if username and password:
                self.api = MetronAPI(
                    username=username,
                    password=password,
                    timeout=self.timeout,
                    rate_limit_delay=self.rate_limit_delay
                )
            else:
                raise ScannerConfigError(
                    "Metron credentials are not configured. "
                    "Please add username and password in settings."
                )

        confidence_threshold = kwargs.get('confidence_threshold', self.confidence_threshold)
        max_results = kwargs.get('max_results', self.max_results)

        try:
            # Search for series
            results = self.api.search_series(query)

            if not results:
                return None, []

            # Limit results
            results = results[:max_results]

            scored_results = []
            for series in results:
                confidence = calculate_title_similarity(query, series.get('name', ''))

                # Boost confidence if year matches (if provided in query)
                year_match = re.search(r'\b(19|20)\d{2}\b', query)
                if year_match and series.get('year_began'):
                    if year_match.group(0) == str(series.get('year_began')):
                        confidence += YEAR_MATCH_CONFIDENCE_BOOST
                        confidence = min(MAX_CONFIDENCE, confidence)

                if confidence >= confidence_threshold:
                    scan_result = self._build_result(series, confidence)
                    scored_results.append(scan_result)

            if not scored_results:
                return None, []

            scored_results.sort(key=lambda x: x.confidence, reverse=True)

            return scored_results[0], scored_results

        except (ScannerConfigError, ScannerRateLimitError):
            raise
        except Exception as e:
            logger.error(f"Metron scan failed: {e}")
            raise ScannerAPIError(f"Metron scan failed: {e}") from e

    def _build_result(self, series: Dict, confidence: float) -> ScanResult:
        """Convert Metron series to ScanResult"""

        # Extract publisher info
        publisher = series.get('publisher', {})
        publisher_name = publisher.get('name') if isinstance(publisher, dict) else None

        # Extract series type
        series_type = series.get('series_type', {})
        series_type_name = series_type.get('name') if isinstance(series_type, dict) else None

        # Build metadata
        metadata = {
            'title': series.get('name'),
            'series': series.get('name'),
            'year': series.get('year_began'),
            'year_ended': series.get('year_ended'),
            'publisher': publisher_name,
            'volume': series.get('volume'),
            'count': series.get('issue_count'),
            'description': series.get('desc'),
            'series_type': series_type_name,
            'source': self.source_name,
        }

        # Clean up None values
        metadata = {k: v for k, v in metadata.items() if v is not None}

        # Build source URL
        source_url = f"https://metron.cloud/series/{series.get('id')}/"

        # Extract genres/tags from series type
        tags = []
        if series_type_name:
            tags.append(f"type:{series_type_name}")

        # Build extra metadata for flexible display
        extra_metadata = {
            "items": []
        }

        # Helper to add items
        def add_extra(label, value, display="row", color=None, placement="details"):
            if value:
                item = {
                    "label": label, 
                    "value": value, 
                    "display": display,
                    "placement": placement
                }
                if color:
                    item["color"] = color
                extra_metadata["items"].append(item)

        # Publisher
        if publisher_name:
            add_extra("Publisher", publisher_name, "tag", "blue")

        # Series Type
        if series_type_name:
            add_extra("Series Type", series_type_name, "tag", "gray")

        # Volume
        volume_num = series.get('volume')
        if volume_num:
            add_extra("Volume", volume_num)

        # Issue Count
        count = series.get('issue_count')
        if count:
            add_extra("Issue Count", count)

        # Years
        year_began = series.get('year_began')
        year_ended = series.get('year_ended')
        if year_began:
            year_str = str(year_began)
            if year_ended:
                year_str += f" - {year_ended}"
            add_extra("Years", year_str)

        return ScanResult(
            confidence=confidence,
            source_id=str(series.get('id')),
            source_url=source_url,
            metadata=metadata,
            tags=tags,
            raw_response=series,
            extra_metadata=extra_metadata
        )

    def get_config_schema(self) -> List['ConfigOption']:
        """Get declarative configuration schema for Metron scanner"""
        try:
            from src.scanners.config_schema import ConfigOption, ConfigType
        except ImportError:
            return []

        return [
            ConfigOption(
                key="username",
                type=ConfigType.STRING,
                label="Username",
                description="Your Metron username from https://metron.cloud/",
                required=True,
                placeholder="Enter your Metron username"
            ),
            ConfigOption(
                key="password",
                type=ConfigType.SECRET,
                label="Password",
                description="Your Metron password",
                required=True,
                placeholder="Enter your Metron password"
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
                max_value=50,
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
                description="Delay between API requests in seconds",
                default=1.0,
                min_value=0.5,
                max_value=10.0,
                step=0.5,
                required=False,
                advanced=True
            ),
        ]


# ============================================================================
# Standalone Functions (for direct usage)
# ============================================================================

def search_series(title: str, username: str, password: str, max_results: int = 5) -> List[Dict]:
    """
    Search for series on Metron

    Args:
        title: Series title to search
        username: Metron username
        password: Metron password
        max_results: Maximum results to return

    Returns:
        List of series dictionaries
    """
    api = MetronAPI(username=username, password=password)
    results = api.search_series(title)
    return results[:max_results]


def get_series_metadata(
    title: str,
    username: str,
    password: str,
    confidence_threshold: float = 0.6
) -> Optional[Dict]:
    """
    Get metadata for a comic series

    Args:
        title: Series title
        username: Metron username
        password: Metron password
        confidence_threshold: Minimum confidence for match

    Returns:
        Metadata dictionary or None
    """
    scanner = MetronScanner({
        'username': username,
        'password': password,
        'confidence_threshold': confidence_threshold
    })
    best_match, _ = scanner.scan(title)

    if best_match:
        return best_match.to_dict()
    return None


# ============================================================================
# Command Line Interface
# ============================================================================

def main():
    """Command line interface"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Metron Comic Metadata Scanner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Search for a series:
    %(prog)s "Batman" --username USER --password PASS

  Lower confidence threshold:
    %(prog)s "Spider-Man" --username USER --password PASS --threshold 0.5
        """
    )

    parser.add_argument('title', help='Series title to search for')
    parser.add_argument('--username', '-u', required=True, help='Metron username')
    parser.add_argument('--password', '-p', required=True, help='Metron password')
    parser.add_argument('--threshold', type=float, default=0.6,
                        help='Confidence threshold (0.0-1.0, default: 0.6)')
    parser.add_argument('--max-results', type=int, default=5,
                        help='Maximum search results (default: 5)')
    parser.add_argument('--json', action='store_true',
                        help='Output as JSON')

    args = parser.parse_args()

    try:
        scanner = MetronScanner({
            'username': args.username,
            'password': args.password,
            'confidence_threshold': args.threshold,
            'max_results': args.max_results
        })

        print(f"Searching Metron for: {args.title}")
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

            if meta.get('publisher'):
                print(f"Publisher: {meta.get('publisher')}")

            if meta.get('year'):
                year_str = str(meta.get('year'))
                if meta.get('year_ended'):
                    year_str += f" - {meta.get('year_ended')}"
                print(f"Year: {year_str}")

            if meta.get('volume'):
                print(f"Volume: {meta.get('volume')}")

            if meta.get('count'):
                print(f"Issues: {meta.get('count')}")

            if meta.get('series_type'):
                print(f"Type: {meta.get('series_type')}")

            print(f"\nMetron URL: {best_match.source_url}")

            # Show other matches
            if len(all_matches) > 1:
                print("\n" + "=" * 60)
                print(f"Other Matches ({len(all_matches) - 1}):")
                print("=" * 60)

                for i, match in enumerate(all_matches[1:], 1):
                    meta = match.metadata
                    print(f"\n{i}. {meta.get('title')} (Confidence: {match.confidence:.2%})")
                    if meta.get('publisher'):
                        print(f"   Publisher: {meta.get('publisher')}")
                    if meta.get('year'):
                        print(f"   Year: {meta.get('year')}")

        return 0

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 130
    except ScannerConfigError as e:
        print(f"\nConfiguration Error: {e}")
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
