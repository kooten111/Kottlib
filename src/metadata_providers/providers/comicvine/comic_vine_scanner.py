#!/usr/bin/env python3
"""
Comic Vine Scanner - Metadata Scanner for Western Comics

A complete, self-contained scanner for extracting metadata from Comic Vine.
This scanner uses the Comic Vine API to fetch comic metadata.

Features:
- Comic Vine API client
- Series/Volume level metadata extraction
- Fuzzy matching with confidence scores
- Staff (Writer, Artist) extraction
- Character extraction
- Cover image retrieval

Usage:
    python comic_vine_scanner.py "Batman" --api-key YOUR_API_KEY

    Or import as a module:
    from comic_vine_scanner import ComicVineScanner
"""

import re
import json
import time
import urllib.parse
from typing import List, Tuple, Optional, Dict, Any
from difflib import SequenceMatcher
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum

try:
    # Import from src.metadata_providers package
    from src.metadata_providers.base import BaseScanner, ScanResult, ScanLevel, MatchConfidence, ScannerAPIError, ScannerConfigError
    from src.metadata_providers.config import ConfigOption, ConfigType
    from src.metadata_providers.utils import clean_query
except ImportError:
    # Fallback for standalone execution
    BaseScanner = ABC
    ScanResult = None  # Will be defined below
    ScanLevel = None
    MatchConfidence = None
    ScannerAPIError = Exception
    ScannerConfigError = Exception

import requests


# ============================================================================
# Comic Vine API Client
# ============================================================================

class ComicVineAPI:
    """
    Client for the Comic Vine API
    
    Official API documentation: https://comicvine.gamespot.com/api/documentation
    """
    
    BASE_URL = "https://comicvine.gamespot.com/api"
    
    def __init__(self, api_key: str, timeout: int = 30, rate_limit_delay: float = 1.0):
        """
        Initialize Comic Vine API client

        Args:
            api_key: Comic Vine API Key
            timeout: Request timeout in seconds
            rate_limit_delay: Delay between requests to respect rate limits
        """
        self.api_key = api_key
        self.timeout = timeout
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = 0
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'YACLib-Enhanced/1.0 (Compatible; ComicVineScanner)',
            'Accept': 'application/json',
        })
    
    def _wait_for_rate_limit(self):
        """Ensure we don't exceed rate limits"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()
    
    def _request(self, endpoint: str, params: Dict = None) -> Dict:
        """
        Execute an API request
        
        Args:
            endpoint: API endpoint (e.g., "volumes")
            params: Query parameters
            
        Returns:
            Response data dictionary
            
        Raises:
            Exception: On API errors
        """
        if not self.api_key:
            raise ScannerConfigError("Comic Vine API key is required")

        self._wait_for_rate_limit()
        
        url = f"{self.BASE_URL}/{endpoint}/"
        
        default_params = {
            'api_key': self.api_key,
            'format': 'json',
        }
        
        if params:
            default_params.update(params)
        
        try:
            response = self.session.get(
                url,
                params=default_params,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('error') and data.get('error') != 'OK':
                raise Exception(f"Comic Vine API error: {data.get('error')}")
                
            return data
            
        except requests.exceptions.RequestException as e:
            raise ScannerAPIError(f"Comic Vine API request failed: {e}")
    
    def search_volumes(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search for comic volumes (series)
        
        Args:
            query: Search query (series name)
            limit: Maximum results
            
        Returns:
            List of volume dictionaries
        """
        # Comic Vine search is a bit tricky. We can use the general 'search' resource
        # or filter the 'volumes' resource. Filtering 'volumes' is usually better for specific series.
        
        # Method 1: Filter volumes (often more precise for series names)
        params = {
            'filter': f'name:{query}',
            'sort': 'count_of_issues:desc', # Prefer series with more issues
            'field_list': 'id,name,start_year,count_of_issues,publisher,image,description,site_detail_url',
            'limit': limit
        }
        
        data = self._request('volumes', params)
        return data.get('results', [])

    def get_volume_details(self, volume_id: int) -> Optional[Dict]:
        """
        Get details for a specific volume
        
        Args:
            volume_id: Volume ID
            
        Returns:
            Volume details dictionary
        """
        params = {
            'field_list': 'id,name,start_year,count_of_issues,publisher,image,description,site_detail_url,characters,people,concepts'
        }
        
        data = self._request(f'volume/4050-{volume_id}', params)
        return data.get('results')


# ============================================================================
# Title Matching and Confidence Scoring
# ============================================================================

def normalize_title(title: str) -> str:
    """Normalize a title for matching"""
    if not title:
        return ""
    title = title.lower()
    title = re.sub(r'[^\w\s]', '', title)
    title = ' '.join(title.split())
    return title

def calculate_title_similarity(query: str, candidate: str) -> float:
    """Calculate similarity between two titles"""
    query_norm = normalize_title(query)
    candidate_norm = normalize_title(candidate)
    
    if not query_norm or not candidate_norm:
        return 0.0
    
    if query_norm == candidate_norm:
        return 1.0
    
    if query_norm in candidate_norm or candidate_norm in query_norm:
        return 0.9
    
    return SequenceMatcher(None, query_norm, candidate_norm).ratio()


# ============================================================================
# Scanner Framework Integration
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
            if self.metadata is None: self.metadata = {}
            if self.tags is None: self.tags = []
        
        @property
        def confidence_level(self):
            if self.confidence == 0: return MatchConfidence.NONE
            elif self.confidence < 0.4: return MatchConfidence.LOW
            elif self.confidence < 0.7: return MatchConfidence.MEDIUM
            elif self.confidence < 0.9: return MatchConfidence.HIGH
            else: return MatchConfidence.EXACT

if 'BaseScanner' not in globals() or globals()['BaseScanner'] is ABC:
    class BaseScanner(ABC):
        def __init__(self, config: Optional[Dict] = None):
            self.config = config or {}
            self._validate_config()
        
        @property
        @abstractmethod
        def source_name(self) -> str: pass
        
        @property
        @abstractmethod
        def scan_level(self) -> ScanLevel: pass
        
        @abstractmethod
        def scan(self, query: str, **kwargs) -> Tuple[Optional[ScanResult], List[ScanResult]]: pass
        
        def _validate_config(self): pass
        
        def get_required_config_keys(self) -> List[str]: return []


# ============================================================================
# Comic Vine Scanner Implementation
# ============================================================================

class ComicVineScanner(BaseScanner):
    """
    Comic Vine metadata scanner for Western comics
    
    Operates at SERIES level.
    """
    
    @property
    def source_name(self) -> str:
        return "Comic Vine"
    
    @property
    def scan_level(self) -> ScanLevel:
        return ScanLevel.SERIES
    
    def get_required_config_keys(self) -> List[str]:
        return ["api_key"]

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.api_key = self.config.get('api_key')
        self.confidence_threshold = self.config.get('confidence_threshold', 0.6)
        self.max_results = self.config.get('max_results', 10)
        self.use_normalized_search = self.config.get('use_normalized_search', True)
        
        if self.api_key:
            self.api = ComicVineAPI(self.api_key)
        else:
            self.api = None

    def _validate_config(self):
        # We don't raise error here to allow instantiation for discovery
        # Check is done in scan()
        pass

    def scan(self, query: str, **kwargs) -> Tuple[Optional[ScanResult], List[ScanResult]]:
        """
        Scan Comic Vine for series metadata
        """
        if not self.api:
             # Try to get API key from kwargs or raise error
            api_key = kwargs.get('api_key')
            if api_key:
                self.api = ComicVineAPI(api_key)
            else:
                raise ScannerConfigError("Comic Vine API key is not configured. Please add it in settings.")

        confidence_threshold = kwargs.get('confidence_threshold', self.confidence_threshold)
        max_results = kwargs.get('max_results', self.max_results)
        use_normalized_search = kwargs.get('use_normalized_search', self.use_normalized_search)

        # Extract year from raw query for boosting logic later
        year_match = re.search(r'\b(19|20)\d{2}\b', query)
        
        # Clean query if enabled
        search_query = query
        if use_normalized_search:
            search_query = clean_query(query)
            if not search_query:
                search_query = query
        
        try:
            # Search for volumes
            results = self.api.search_volumes(search_query, limit=max_results)
            
            if not results:
                return None, []
            
            scored_results = []
            for volume in results:
                confidence = calculate_title_similarity(query, volume.get('name', ''))
                
                # Boost confidence if start year matches (if provided in query, e.g. "Batman 2016")
                # Simple heuristic: check if a year (19xx or 20xx) in query matches start_year
                if year_match and volume.get('start_year'):
                    if year_match.group(0) == str(volume.get('start_year')):
                        confidence += 0.1
                        confidence = min(1.0, confidence)
                
                if confidence >= confidence_threshold:
                    scan_result = self._build_result(volume, confidence)
                    scored_results.append(scan_result)
            
            if not scored_results:
                return None, []
            
            scored_results.sort(key=lambda x: x.confidence, reverse=True)
            
            # Optionally fetch full details for the best match if needed
            # For now, the search result has enough basic info
            
            return scored_results[0], scored_results
            
        except Exception as e:
            raise ScannerAPIError(f"Comic Vine scan failed: {e}") from e

    def _build_result(self, volume: Dict, confidence: float) -> ScanResult:
        """Convert Comic Vine volume to ScanResult"""
        
        metadata = {
            'title': volume.get('name'),
            'year': volume.get('start_year'),
            'publisher': volume.get('publisher', {}).get('name') if volume.get('publisher') else None,
            'count': volume.get('count_of_issues'),
            'description': self._clean_description(volume.get('description')),
            'status': None, # Comic Vine doesn't easily give status in search results
            'cover_image': volume.get('image', {}).get('original_url')
        }
        
        # Clean up None values
        metadata = {k: v for k, v in metadata.items() if v is not None}
        
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
        publisher = volume.get('publisher', {}).get('name') if volume.get('publisher') else None
        if publisher:
            add_extra("Publisher", publisher, "tag", "blue")

        # Issue Count
        count = volume.get('count_of_issues')
        if count:
            add_extra("Issue Count", count)

        # Start Year
        start_year = volume.get('start_year')
        if start_year:
            add_extra("Start Year", start_year)
            
        return ScanResult(
            confidence=confidence,
            source_id=str(volume.get('id')),
            source_url=volume.get('site_detail_url'),
            metadata=metadata,
            tags=[], # Tags/Genres not always available in search list
            raw_response=volume,
            extra_metadata=extra_metadata
        )

    def _clean_description(self, description: Optional[str]) -> Optional[str]:
        if not description:
            return None
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', description)
        return text.strip()

    def get_config_schema(self) -> List[ConfigOption]:
        """Get declarative configuration schema for Comic Vine scanner"""
        return [
            ConfigOption(
                key="api_key",
                type=ConfigType.SECRET,
                label="API Key",
                description="Your Comic Vine API key from https://comicvine.gamespot.com/api/",
                required=True,
                placeholder="Enter your Comic Vine API key"
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
                key="use_normalized_search",
                type=ConfigType.BOOLEAN,
                label="Use Normalized Search",
                description="Clean search query by removing brackets, tags, etc.",
                default=True,
                required=False
            ),
        ]

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Comic Vine Scanner')
    parser.add_argument('query', help='Series name to search')
    parser.add_argument('--api-key', help='Comic Vine API Key', required=True)
    args = parser.parse_args()
    
    scanner = ComicVineScanner({'api_key': args.api_key})
    try:
        result, candidates = scanner.scan(args.query)
        if result:
            print(f"Found: {result.metadata['title']} ({result.metadata.get('year')})")
            print(f"Confidence: {result.confidence}")
            print(f"Publisher: {result.metadata.get('publisher')}")
            print(f"Issues: {result.metadata.get('count')}")
            print(f"URL: {result.source_url}")
        else:
            print("No match found")
    except Exception as e:
        print(f"Error: {e}")
