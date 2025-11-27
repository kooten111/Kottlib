#!/usr/bin/env python3
"""
nhentai Scanner - Standalone Metadata Scanner for Doujinshi

A complete, self-contained scanner for extracting metadata from nhentai.net and nhentai.xxx.
This single script includes:
- nhentai API client (supports both .net and .xxx domains)
- Enhanced filename parsing with metadata extraction
- Fuzzy matching with confidence scores
- Fallback search strategies
- Scanner framework with standardized output

Usage:
    python nhentai_scanner.py "[Artist] Title [English].cbz"

    Or import as a module:
    from nhentai_scanner import NhentaiScanner, scan_file
"""

import re
import json
import argparse
from collections import namedtuple
from enum import Enum, unique
from typing import List, Tuple, Optional, Dict
from difflib import SequenceMatcher
from urllib.parse import urljoin, quote
from pathlib import Path
from dataclasses import dataclass
from abc import ABC, abstractmethod

try:
    # Import from src.scanners package
    from src.scanners.base_scanner import BaseScanner, ScanResult, ScanLevel, MatchConfidence, ScannerAPIError
except ImportError:
    # Fallback for standalone execution
    class BaseScanner(ABC):
        def __init__(self, config: Optional[Dict] = None):
            self.config = config or {}

        @property
        @abstractmethod
        def source_name(self) -> str:
            pass

        @property
        @abstractmethod
        def scan_level(self) -> 'ScanLevel':
            pass

        @abstractmethod
        def scan(self, query: str, **kwargs) -> Tuple[Optional['ScanResult'], List['ScanResult']]:
            pass

    ScanResult = None  # Will be defined below
    ScanLevel = None
    MatchConfidence = None
    ScannerAPIError = Exception

import requests
from bs4 import BeautifulSoup


# ============================================================================
# nhentai API Client
# ============================================================================

@unique
class Extension(Enum):
    JPG = 'j'
    PNG = 'p'
    GIF = 'g'
    WEBP = 'w'


class Doujin():
    """
    Class representing a doujin.

    :ivar int id:           Doujin id.
    :ivar dict titles:      Doujin titles (language:title).
    :ivar Doujin.Tag tags:  Doujin tag list.
    :ivar str cover:        Doujin cover image url.
    :ivar str thumbnail:    Doujin thumbnail image url.
    :ivar str base_url:     Base URL of the source site.
    """
    Tag = namedtuple("Tag", ["id", "type", "name", "url", "count"])
    Pages = namedtuple("Page", ["url", "width", "height"])

    def __init__(self, data, base_url: str = "https://nhentai.net"):
        self.id = data["id"]
        self.media_id = data["media_id"]
        self.titles = data["title"]
        self.favorites = data["num_favorites"]
        self.base_url = base_url
        self.url = f"{base_url}/g/{self.id}"
        images = data["images"]

        # Determine image server URL based on base URL
        if "nhentai.xxx" in base_url:
            img_server = base_url.replace("nhentai.xxx", "i.nhentai.xxx")
            thumb_server = base_url.replace("nhentai.xxx", "t.nhentai.xxx")
        else:
            img_server = "https://i.nhentai.net"
            thumb_server = "https://t.nhentai.net"

        self.pages = [Doujin.__makepage__(self.media_id, num, img_server, **_) for num, _ in enumerate(images["pages"], start=1)]
        self.tags = [Doujin.Tag(**_) for _ in data["tags"]]

        thumb_ext = Extension(images["thumbnail"]["t"]).name.lower()
        self.thumbnail = f"{thumb_server}/galleries/{self.media_id}/thumb.{thumb_ext}"

        cover_ext = Extension(images["cover"]["t"]).name.lower()
        self.cover = f"{thumb_server}/galleries/{self.media_id}/cover.{cover_ext}"

    def __getitem__(self, key: int):
        """
        Returns a page by index.

        :rtype: Doujin.Page
        """
        return self.pages[key]

    def __makepage__(media_id: int, num: int, img_server: str, t: str, w: int, h: int):
        return Doujin.Pages(f"{img_server}/galleries/{media_id}/{num}.{Extension(t).name.lower()}",
            w, h)


_SESSION = requests.Session()
_BASE_URL = "https://nhentai.net"  # Default base URL


def set_base_url(url: str):
    """
    Set the base URL for API requests.

    :param str url: Base URL (e.g., "https://nhentai.net" or "https://nhentai.xxx")
    """
    global _BASE_URL
    _BASE_URL = url.rstrip('/')


def get_base_url() -> str:
    """Get the current base URL."""
    return _BASE_URL


def _get(endpoint, params={}, base_url: str = None) -> dict:
    """
    Make a GET request to the API.

    :param str endpoint: API endpoint
    :param dict params: Query parameters
    :param str base_url: Override base URL for this request
    """
    url = base_url or _BASE_URL
    return _SESSION.get(urljoin(f"{url}/api/", endpoint), params=params).json()


def search(query: str, page: int = 1, sort_by: str = "date", base_url: str = None) -> List[Doujin]:
    """
    Search doujins by keyword.

    :param str query: Search term. (https://nhentai.net/info/)
    :param int page: Page number. Defaults to 1.
    :param str sort_by: Method to sort search results by (popular/date). Defaults to date.
    :param str base_url: Override base URL (e.g., "https://nhentai.xxx")

    :returns list[Doujin]: Search results parsed into a list of nHentaiDoujin objects
    """
    url = base_url or _BASE_URL
    galleries = _get('galleries/search', {"query": query, "page": page, "sort": sort_by}, base_url=url)["result"]
    return [Doujin(search_result, base_url=url) for search_result in galleries]


def search_multiple_sources(query: str, page: int = 1, sort_by: str = "date", sources: List[str] = None) -> Tuple[List[Doujin], str]:
    """
    Search across multiple nhentai sources, trying each until one succeeds.

    :param str query: Search term
    :param int page: Page number
    :param str sort_by: Sort method (popular/date)
    :param list sources: List of base URLs to try (defaults to [nhentai.net])

    :returns: Tuple of (results, successful_source)
    """
    if sources is None:
        sources = ["https://nhentai.net"]

    last_error = None
    for source in sources:
        try:
            results = search(query, page=page, sort_by=sort_by, base_url=source)
            return results, source
        except Exception as e:
            last_error = e
            continue

        # If all sources failed, raise the last error
    if last_error:
        raise last_error
    return [], ""


def get_doujin(id: int, base_url: str = None) -> Doujin:
    """
    Get a doujin by its id.

    :param int id: A doujin's id.
    :param str base_url: Override base URL

    :rtype: Doujin
    """
    url = base_url or _BASE_URL
    try:
        return Doujin(_get(f"gallery/{id}", base_url=url), base_url=url)
    except KeyError:
        raise ValueError("A doujin with the given id wasn't found")


# ============================================================================
# Web Scraping Support (for sites without API)
# ============================================================================

def scrape_search_results(query: str, base_url: str, page: int = 1) -> List[Dict]:
    """
    Scrape search results from nhentai HTML pages.
    Used for sites like nhentai.xxx that don't have an API.
    
    :param str query: Search term
    :param str base_url: Base URL (e.g., "https://nhentai.xxx")
    :param int page: Page number
    :returns: List of dicts with basic doujin info (id, title, thumbnail)
    """
    search_url = f"{base_url}/search/?q={quote(query)}&page={page}"
    
    try:
        response = _SESSION.get(search_url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
    except Exception as e:
        raise Exception(f"Failed to fetch search page: {e}")
    
    # Extract gallery IDs from links in the HTML
    # The page contains links like /g/123456/ even if JavaScript hasn't rendered
    gallery_matches = re.findall(r'/g/(\d+)/', response.text)
    # Remove duplicates while preserving order
    seen = set()
    unique_ids = []
    for gid in gallery_matches:
        if gid not in seen:
            seen.add(gid)
            unique_ids.append(int(gid))
    
    results = []
    for doujin_id in unique_ids:
        results.append({
            'id': doujin_id,
            'title': 'Unknown',  # Will be fetched from detail page
            'url': f"{base_url}/g/{doujin_id}/"
        })
    
    return results


def scrape_doujin_details(doujin_id: int, base_url: str) -> Dict:
    """
    Scrape full doujin details from the gallery page.
    
    :param int doujin_id: The doujin ID
    :param str base_url: Base URL
    :returns: Dict with full doujin data compatible with API format
    """
    url = f"{base_url}/g/{doujin_id}/"
    
    try:
        response = _SESSION.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
    except Exception as e:
        raise Exception(f"Failed to fetch doujin page: {e}")
    
    soup = BeautifulSoup(response.text, 'lxml')
    
    # Extract title
    title_elem = soup.find('h1', class_='title')
    pretty_title = title_elem.get_text(strip=True) if title_elem else 'Unknown'
    
    subtitle_elem = soup.find('h2', class_='subtitle')
    japanese_title = subtitle_elem.get_text(strip=True) if subtitle_elem else ''
    
    # Extract tags
    tags = []
    tag_container = soup.find('section', id='tags')
    if tag_container:
        tag_rows = tag_container.find_all('div', class_='tag-container')
        for row in tag_rows:
            # Get tag type from the label
            label = row.find('span', class_='tags')
            if not label:
                continue
            tag_type = label.get_text(strip=True).rstrip(':').lower()
            
            # Map display names to API tag types
            type_mapping = {
                'artists': 'artist',
                'groups': 'group',
                'parodies': 'parody',
                'characters': 'character',
                'tags': 'tag',
                'languages': 'language',
                'categories': 'category'
            }
            tag_type = type_mapping.get(tag_type, tag_type.rstrip('s'))
            
            # Get all tag links
            tag_links = row.find_all('a', class_='tag')
            for tag_link in tag_links:
                tag_name = tag_link.find('span', class_='name')
                if tag_name:
                    name = tag_name.get_text(strip=True)
                    # Extract count if available
                    count_elem = tag_link.find('span', class_='count')
                    count = 0
                    if count_elem:
                        count_text = count_elem.get_text(strip=True)
                        count_match = re.search(r'\d+', count_text.replace(',', ''))
                        if count_match:
                            count = int(count_match.group())
                    
                    tags.append({
                        'id': 0,  # Not available from HTML
                        'type': tag_type,
                        'name': name,
                        'url': tag_link.get('href', ''),
                        'count': count
                    })
    
    # Extract page count and other info
    info_elem = soup.find('div', id='info')
    num_pages = 0
    if info_elem:
        pages_div = info_elem.find('div', string=re.compile('Pages:'))
        if pages_div:
            pages_text = pages_div.get_text()
            match = re.search(r'(\d+)', pages_text)
            if match:
                num_pages = int(match.group(1))
    
    # Build data structure compatible with API format
    data = {
        'id': doujin_id,
        'media_id': str(doujin_id),  # Use ID as media_id for scraped content
        'title': {
            'english': pretty_title,
            'japanese': japanese_title,
            'pretty': pretty_title
        },
        'tags': tags,
        'num_favorites': 0,  # Not easily scrapable
        'images': {
            'pages': [{'t': 'j', 'w': 0, 'h': 0} for _ in range(num_pages)],
            'cover': {'t': 'j', 'w': 0, 'h': 0},
            'thumbnail': {'t': 'j', 'w': 0, 'h': 0}
        }
    }
    
    return data


def search_with_scraping(query: str, base_url: str, page: int = 1, sort_by: str = "date") -> List[Doujin]:
    """
    Search using web scraping, then fetch full details for each result.
    
    :param str query: Search term
    :param str base_url: Base URL
    :param int page: Page number
    :param str sort_by: Sort method (ignored for scraping)
    :returns: List of Doujin objects
    """
    # Get search results
    search_results = scrape_search_results(query, base_url, page)
    
    # Fetch full details for each result
    doujins = []
    for result in search_results[:25]:  # Limit to 25 to avoid too many requests
        try:
            data = scrape_doujin_details(result['id'], base_url)
            doujins.append(Doujin(data, base_url=base_url))
        except Exception:
            continue  # Skip failed fetches
    
    return doujins


def search_multiple_sources_with_scraping(query: str, page: int = 1, sort_by: str = "date", sources: List[str] = None) -> Tuple[List[Doujin], str]:
    """
    Search across multiple nhentai sources, using API when available and scraping when not.
    
    :param str query: Search term
    :param int page: Page number
    :param str sort_by: Sort method (popular/date)
    :param list sources: List of base URLs to try
    
    :returns: Tuple of (results, successful_source)
    """
    if sources is None:
        sources = ["https://nhentai.net", "https://nhentai.xxx"]
    
    last_error = None
    for source in sources:
        try:
            # Try API first
            results = search(query, page=page, sort_by=sort_by, base_url=source)
            return results, source
        except Exception as api_error:
            # If API fails and this is nhentai.xxx, try scraping
            if 'nhentai.xxx' in source:
                try:
                    results = search_with_scraping(query, base_url=source, page=page, sort_by=sort_by)
                    return results, source
                except Exception as scrape_error:
                    last_error = scrape_error
                    continue
            else:
                last_error = api_error
    # If all sources failed, raise the last error
    if last_error:
        raise last_error
    return [], ""


def get_doujin(id: int, base_url: str = None) -> Doujin:
    """
    Get a doujin by its id.

    :param int id: A doujin's id.
    :param str base_url: Override base URL

    :rtype: Doujin
    """
    url = base_url or _BASE_URL
    try:
        return Doujin(_get(f"gallery/{id}", base_url=url), base_url=url)
    except KeyError:
        raise ValueError("A doujin with the given id wasn't found")


# ============================================================================
# Enhanced Matching Engine
# ============================================================================

def extract_metadata_from_filename(filename: str) -> dict:
    """
    Extract metadata fields from filename before cleaning.

    Extracts:
    - Event codes: (C101), (C102), (Kemoket 13), etc.
    - Artist/Circle in first brackets: [Artist Name]
    - Parody/Series in parentheses: (Fate Grand Order), (Original)
    - Translator: [English] [Translator Name]

    Args:
        filename: Raw filename

    Returns:
        Dictionary with extracted metadata:
        {
            'event': 'C102',
            'artist': 'Yachan',
            'group': 'Yachan Coffee',
            'parody': 'Fate Grand Order',
            'language': 'English',
            'translator': 'YuushaNi'
        }

    Examples:
        >>> extract_metadata_from_filename("(C102) [Yachan Coffee (Yachan)] Title (Love Live!) [English] [YuushaNi].cbz")
        {'event': 'C102', 'artist': 'Yachan', 'group': 'Yachan Coffee', ...}
    """
    metadata = {
        'event': None,
        'artist': None,
        'group': None,
        'parody': None,
        'language': None,
        'translator': None
    }

    # Extract event code: (C101), (C102), (Kemoket 13), etc.
    # Usually at the very beginning
    event_match = re.match(r'^\(([CcKk]\w*[\s_\-]?\d+)\)', filename)
    if event_match:
        metadata['event'] = event_match.group(1).upper().replace('_', ' ')

    # Extract first bracketed content (usually artist/circle)
    # Pattern: [Circle Name (Artist Name)] or [Artist Name]
    first_bracket = re.search(r'\[([^\]]+)\]', filename)
    if first_bracket:
        content = first_bracket.group(1)
        # Check if it contains parentheses (Circle (Artist))
        artist_in_parens = re.search(r'\(([^\)]+)\)', content)
        if artist_in_parens:
            metadata['artist'] = artist_in_parens.group(1).strip()
            # Everything before the parentheses is the circle/group
            metadata['group'] = re.sub(r'\s*\([^\)]+\)', '', content).strip()
        else:
            # No parentheses, just artist name
            # Skip if it's a language tag
            if content.lower() not in ['english', 'translated', 'chinese', 'japanese', 'spanish', 'french', 'german', 'korean']:
                metadata['artist'] = content.strip()

    # Extract parody/series from parentheses (but not event codes or artists in brackets)
    # Usually after the title
    parens_matches = re.findall(r'\(([^\)]+)\)', filename)
    for match in parens_matches:
        # Skip event codes
        if re.match(r'^[CcKk]\w*[\s_\-]?\d+$', match):
            continue
        # Skip if this is the artist within the first bracket (already extracted)
        if metadata['artist'] and match.strip() == metadata['artist']:
            continue
        # This is likely a parody
        if not metadata['parody']:
            metadata['parody'] = match.strip()

    # Extract language and translator from trailing brackets
    # Pattern: [English] [Translator]
    trailing_brackets = re.findall(r'\[([^\]]+)\]', filename)
    for content in trailing_brackets:
        content_lower = content.lower()
        # Check for language
        if content_lower in ['english', 'translated', 'chinese', 'japanese', 'spanish', 'french', 'german', 'korean']:
            metadata['language'] = content
        # Last bracket that's not language/artist is probably translator
        elif content != first_bracket.group(1) if first_bracket else True:
            metadata['translator'] = content

    return metadata


def clean_filename(filename: str) -> str:
    """
    Clean a filename by removing common metadata markers.

    Removes:
    - Content in brackets: [English], [Aishi21], etc.
    - Content in parentheses: (C101), (Fate Grand Order), etc.
    - Content in curly braces: {tags}, etc.
    - File extensions

    Args:
        filename: Raw filename to clean

    Returns:
        Cleaned filename with only the core title

    Examples:
        >>> clean_filename("[Poni] Title | English Title [English] [Translator].cbz")
        'Title | English Title'

        >>> clean_filename("(C101) [Artist] Title (Original)")
        'Title'
    """
    # Remove file extension
    cleaned = re.sub(r'\.(cbz|cbr|zip|rar|7z|pdf)$', '', filename, flags=re.IGNORECASE)

    # Remove content in brackets, parentheses, and curly braces
    # Use a loop to handle nested brackets
    max_iterations = 10
    for _ in range(max_iterations):
        before = cleaned
        # Remove [...], (...), {...}
        cleaned = re.sub(r'\[[^\]]*\]', '', cleaned)
        cleaned = re.sub(r'\([^\)]*\)', '', cleaned)
        cleaned = re.sub(r'\{[^\}]*\}', '', cleaned)

        # If nothing changed, we're done
        if cleaned == before:
            break

    # Clean up extra whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = cleaned.strip()

    # Remove common separators at start/end
    cleaned = cleaned.strip(' -|_')

    return cleaned


def similarity_score(str1: str, str2: str) -> float:
    """
    Calculate similarity between two strings (0.0 to 1.0).

    Uses Python's SequenceMatcher for fuzzy matching.

    Args:
        str1: First string
        str2: Second string

    Returns:
        Similarity score from 0.0 (no match) to 1.0 (perfect match)
    """
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()


def find_best_match(
    query: str,
    results: List[Doujin],
    threshold: float = 0.4,
    filename_metadata: dict = None
) -> Tuple[Optional[Doujin], float, str, dict]:
    """
    Find the best matching doujin from search results using metadata scoring.

    Compares the cleaned query against titles AND validates metadata fields
    (artist, group, parody, event) to boost confidence.

    Scoring system:
    - Base score: Title similarity (0.0-1.0)
    - Artist match: +0.15 (only if unique in results)
    - Group match: +0.15 (only if unique in results)
    - Parody match: +0.10 (only if unique in results)
    - Event match: +0.10 (always - highly specific)

    Args:
        query: Original search query (will be cleaned internally)
        results: List of doujin search results
        threshold: Minimum similarity score (0.0 to 1.0)
        filename_metadata: Extracted metadata from original filename

    Returns:
        Tuple of (best_match, confidence_score, matched_field, bonus_breakdown)
        Returns (None, 0.0, '', {}) if no match above threshold
    """
    if not results:
        return None, 0.0, '', {}

    if filename_metadata is None:
        filename_metadata = {}

    # Clean the query
    cleaned_query = clean_filename(query)

    # Count how many results have each metadata field (for uniqueness check)
    metadata_counts = {
        'artist': {},
        'group': {},
        'parody': {}
    }

    for doujin in results:
        # Count artists
        for tag in doujin.tags:
            if tag.type == 'artist':
                artist_name = tag.name.lower()
                metadata_counts['artist'][artist_name] = metadata_counts['artist'].get(artist_name, 0) + 1
            elif tag.type == 'group':
                group_name = tag.name.lower()
                metadata_counts['group'][group_name] = metadata_counts['group'].get(group_name, 0) + 1
            elif tag.type == 'parody':
                parody_name = tag.name.lower()
                metadata_counts['parody'][parody_name] = metadata_counts['parody'].get(parody_name, 0) + 1

    best_match = None
    best_score = 0.0
    best_field = ''
    best_bonus_breakdown = {}

    for doujin in results:
        # Check all available titles
        titles_to_check = [
            ('english', doujin.titles.get('english', '')),
            ('japanese', doujin.titles.get('japanese', '')),
            ('pretty', doujin.titles.get('pretty', ''))
        ]

        for field_name, title in titles_to_check:
            if not title:
                continue

            # Clean the doujin title
            cleaned_title = clean_filename(title)

            # Calculate base similarity score
            score = similarity_score(cleaned_query, cleaned_title)

            # Also check if cleaned query is a substring (boost score)
            if cleaned_query.lower() in cleaned_title.lower():
                score = max(score, 0.8)  # Substring match gets at least 0.8

            # Metadata bonuses
            bonus_breakdown = {}
            total_bonus = 0.0

            # Check artist match (only bonus if unique in results)
            if filename_metadata.get('artist'):
                filename_artist = filename_metadata['artist'].lower()
                for tag in doujin.tags:
                    if tag.type == 'artist' and tag.name.lower() == filename_artist:
                        # Only give bonus if this artist is unique in results
                        if metadata_counts['artist'][tag.name.lower()] == 1:
                            bonus_breakdown['artist_unique'] = 0.15
                            total_bonus += 0.15
                        else:
                            bonus_breakdown['artist_common'] = 0.0

            # Check group match (only bonus if unique in results)
            if filename_metadata.get('group'):
                filename_group = filename_metadata['group'].lower()
                for tag in doujin.tags:
                    if tag.type == 'group' and tag.name.lower() == filename_group:
                        if metadata_counts['group'][tag.name.lower()] == 1:
                            bonus_breakdown['group_unique'] = 0.15
                            total_bonus += 0.15
                        else:
                            bonus_breakdown['group_common'] = 0.0

            # Check parody match (only bonus if unique in results)
            if filename_metadata.get('parody'):
                filename_parody = filename_metadata['parody'].lower()
                for tag in doujin.tags:
                    if tag.type == 'parody' and similarity_score(filename_parody, tag.name) > 0.7:
                        if metadata_counts['parody'][tag.name.lower()] == 1:
                            bonus_breakdown['parody_unique'] = 0.10
                            total_bonus += 0.10
                        else:
                            bonus_breakdown['parody_common'] = 0.0

            # Check event match (always bonus - highly specific)
            if filename_metadata.get('event'):
                filename_event = filename_metadata['event'].upper()
                # Event is usually in the title itself
                if filename_event in title.upper():
                    bonus_breakdown['event'] = 0.10
                    total_bonus += 0.10

            # Calculate final score
            final_score = min(score + total_bonus, 1.0)  # Cap at 1.0

            # Update best match if this is better
            if final_score > best_score:
                best_score = final_score
                best_match = doujin
                best_field = field_name
                best_bonus_breakdown = bonus_breakdown

    # IMPORTANT: Apply penalty if we have artist/group metadata but it doesn't match ANY results
    # This indicates the doujin might not be in the search results at all
    if filename_metadata.get('artist') or filename_metadata.get('group'):
        # Check if ANY result matches our artist/group
        any_artist_match = False
        any_group_match = False

        filename_artist = (filename_metadata.get('artist') or '').lower()
        filename_group = (filename_metadata.get('group') or '').lower()

        for doujin in results:
            for tag in doujin.tags:
                # Check artist with fuzzy matching (one might be short form of the other)
                if filename_artist and tag.type == 'artist':
                    if (tag.name.lower() == filename_artist or
                        tag.name.lower() in filename_artist or
                        filename_artist in tag.name.lower() or
                        similarity_score(tag.name, filename_metadata['artist']) > 0.7):
                        any_artist_match = True

                # Check group (exact match or fuzzy)
                if filename_group and tag.type == 'group':
                    if (tag.name.lower() == filename_group or
                        similarity_score(tag.name, filename_metadata['group']) > 0.7):
                        any_group_match = True

        # If we have artist metadata but NONE of the results match, apply penalty
        if filename_metadata.get('artist') and not any_artist_match:
            best_score *= 0.5  # 50% penalty - we expected an artist match but found none
            best_bonus_breakdown['artist_mismatch_penalty'] = -0.5

        # Same for group
        if filename_metadata.get('group') and not any_group_match:
            best_score *= 0.5
            best_bonus_breakdown['group_mismatch_penalty'] = -0.5

    # Only return if above threshold
    if best_score >= threshold:
        return best_match, best_score, best_field, best_bonus_breakdown
    else:
        return None, best_score, '', {}


def get_tags_from_filename_enhanced(
    filename: str,
    max_results: int = 10,
    confidence_threshold: float = 0.4,
    sort_by: str = "date",
    use_fallback_searches: bool = True,
    sources: List[str] = None
) -> Tuple[List[Doujin.Tag], float, dict]:
    """
    Get tags for a filename using enhanced matching with metadata validation.

    This function:
    1. Extracts metadata from filename (artist, event, parody, etc.)
    2. Cleans the filename (removes brackets, etc.)
    3. Searches nhentai (tries multiple sources) with cleaned query
    4. If too many results (>20), tries fallback searches with metadata
    5. Finds best match using fuzzy matching + metadata scoring
    6. Returns tags with confidence score

    Args:
        filename: Original filename (can include brackets, extensions, etc.)
        max_results: Max search results to fetch (default: 10)
        confidence_threshold: Minimum confidence to accept match (0.0-1.0)
        sort_by: Sort method for search ("date" or "popular")
        use_fallback_searches: Try alternative searches if initial query is too broad
        sources: List of base URLs to try (default: nhentai.net, nhentai.xxx)

    Returns:
        Tuple of (tags, confidence_score, metadata_dict)

        - tags: List of Tag objects from the best match
        - confidence_score: How confident we are (0.0 to 1.0)
        - metadata: Dict with extra info (includes 'source_used')
    """
    # Extract metadata from filename BEFORE cleaning
    extracted_metadata = extract_metadata_from_filename(filename)

    # Clean the filename
    cleaned = clean_filename(filename)

    # If cleaning removed everything, use original
    if not cleaned or len(cleaned) < 3:
        cleaned = filename

    # Try primary search across multiple sources (with scraping support)
    try:
        results, source_used = search_multiple_sources_with_scraping(cleaned, page=1, sort_by=sort_by, sources=sources)
        search_strategy = "primary"
    except Exception as e:
        # If search fails, return empty results
        return [], 0.0, {
            'error': str(e),
            'cleaned_query': cleaned,
            'num_results': 0,
            'extracted_metadata': extracted_metadata,
            'search_strategy': 'failed'
        }

    # FALLBACK STRATEGY: If too many results and we have metadata, try narrower searches
    if use_fallback_searches and len(results) > 20:
        fallback_queries = []

        # Try artist + title
        if extracted_metadata.get('artist'):
            fallback_queries.append((f"{extracted_metadata['artist']} {cleaned}", "artist+title"))

        # Try group + title
        if extracted_metadata.get('group'):
            fallback_queries.append((f"{extracted_metadata['group']} {cleaned}", "group+title"))

        # Try event + title
        if extracted_metadata.get('event'):
            fallback_queries.append((f"{extracted_metadata['event']} {cleaned}", "event+title"))

        # Try parody + title
        if extracted_metadata.get('parody'):
            fallback_queries.append((f"{extracted_metadata['parody']} {cleaned}", "parody+title"))

        # Try each fallback query
        for fallback_query, strategy_name in fallback_queries:
            try:
                fallback_results, fallback_source = search_multiple_sources_with_scraping(fallback_query, page=1, sort_by=sort_by, sources=sources)
                # Use fallback results if they narrow it down significantly
                if 0 < len(fallback_results) < len(results):
                    results = fallback_results
                    source_used = fallback_source
                    search_strategy = strategy_name
                    cleaned = fallback_query  # Update for metadata
                    break
            except:
                continue

    # Find best match using metadata-aware scoring
    best_match, confidence, matched_field, score_bonuses = find_best_match(
        filename,  # Use original filename for matching
        results,
        threshold=confidence_threshold,
        filename_metadata=extracted_metadata
    )

    # Build metadata
    metadata = {
        'cleaned_query': cleaned,
        'num_results': len(results),
        'matched_field': matched_field,
        'extracted_metadata': extracted_metadata,
        'score_bonuses': score_bonuses,
        'search_strategy': search_strategy,
        'source_used': source_used  # Which source (nhentai.net or nhentai.xxx) was used
    }

    if best_match:
        metadata['doujin_id'] = best_match.id
        metadata['doujin_title'] = best_match.titles.get(matched_field,
                                                         best_match.titles.get('pretty', 'Unknown'))
        metadata['doujin_url'] = best_match.url

        return best_match.tags, confidence, metadata
    else:
        return [], confidence, metadata


def format_tags_summary(tags: List[Doujin.Tag]) -> dict:
    """
    Format tags into categorized dictionary.

    Args:
        tags: List of Tag objects

    Returns:
        Dictionary with tags grouped by type
    """
    categorized = {
        'tag': [],
        'artist': [],
        'group': [],
        'character': [],
        'parody': [],
        'language': [],
        'category': []
    }

    for tag in tags:
        if tag.type in categorized:
            categorized[tag.type].append(tag.name)

    return categorized


# ============================================================================
# Scanner Framework
# ============================================================================

if ScanLevel is None:
    class ScanLevel(Enum):
        """What level the scanner operates at"""
        FILE = "file"  # Per-file metadata (e.g., nhentai for doujinshi)
        SERIES = "series"  # Per-series metadata (e.g., Comic Vine, AniList)
        LIBRARY = "library"  # Library-wide metadata


if MatchConfidence is None:
    class MatchConfidence(Enum):
        """Confidence level for metadata matches"""
        NONE = 0  # No match found
        LOW = 1  # 0-40% confidence
        MEDIUM = 2  # 40-70% confidence
        HIGH = 3  # 70-90% confidence
        EXACT = 4  # 90-100% confidence


if ScanResult is None:
    @dataclass
    class ScanResult:
        """
        Result from a metadata scan

        Attributes:
            confidence: How confident we are in this match (0.0 to 1.0)
            source_id: ID from the external source (e.g., nhentai ID, AniList ID)
            source_url: URL to the source entry
            metadata: Dictionary of extracted metadata
            tags: List of tags/genres
            raw_response: Optional raw API response for debugging
        """
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
    """
    Base class for all metadata scanners
    """
    # Only define if not imported
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


class ScannerError(Exception):
    """Base exception for scanner errors"""
    pass


if ScannerAPIError is Exception:
    class ScannerAPIError(ScannerError):
        """API communication error"""
        pass


# ============================================================================
# nhentai Scanner Implementation
# ============================================================================

class NhentaiScanner(BaseScanner):
    """
    nhentai metadata scanner for doujinshi

    Operates at FILE level - scans individual doujinshi files
    Uses enhanced matching with metadata extraction
    """

    @property
    def source_name(self) -> str:
        return "nhentai"

    @property
    def scan_level(self) -> ScanLevel:
        return ScanLevel.FILE

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize nhentai scanner

        Config options:
            - confidence_threshold: Minimum confidence to accept (default: 0.4)
            - use_fallback_searches: Try alternative searches (default: True)
            - sort_by: Sort search results by "date" or "popular" (default: "date")
            - sources: List of sources to try (default: ["https://nhentai.net", "https://nhentai.xxx"])
        """
        super().__init__(config)
        self.confidence_threshold = self.config.get('confidence_threshold', 0.4)
        self.use_fallback_searches = self.config.get('use_fallback_searches', True)
        self.sort_by = self.config.get('sort_by', 'date')
        self.sources = self.config.get('sources', ["https://nhentai.net", "https://nhentai.xxx"])

    def scan(self, query: str, **kwargs) -> Tuple[Optional[ScanResult], List[ScanResult]]:
        """
        Scan nhentai for metadata

        Args:
            query: Filename to search for (with or without path)
            **kwargs:
                - confidence_threshold: Override default threshold
                - use_fallback_searches: Override fallback setting

        Returns:
            (best_match, all_candidates)
        """
        # Override config with kwargs
        confidence_threshold = kwargs.get('confidence_threshold', self.confidence_threshold)
        use_fallback = kwargs.get('use_fallback_searches', self.use_fallback_searches)

        # Extract just the filename if a path was provided
        if '/' in query or '\\' in query:
            query = Path(query).name

        try:
            # Use enhanced tagger
            tags, confidence, metadata = get_tags_from_filename_enhanced(
                query,
                confidence_threshold=confidence_threshold,
                sort_by=self.sort_by,
                use_fallback_searches=use_fallback,
                sources=self.sources
            )

            # Check if we got a match
            if not tags or confidence < confidence_threshold:
                return None, []

            # Build ScanResult
            result = self._build_result(tags, confidence, metadata)

            # For now, we only return the best match
            return result, [result]

        except Exception as e:
            raise ScannerAPIError(f"nhentai scan failed: {e}") from e

    def _build_result(self, tags, confidence: float, metadata: Dict) -> ScanResult:
        """Convert nhentai response to ScanResult"""

        # Categorize tags
        categorized = format_tags_summary(tags)

        # Join list fields with commas to match Comic schema
        artists_str = ', '.join(categorized.get('artist', []))
        groups_str = ', '.join(categorized.get('group', []))
        characters_str = ', '.join(categorized.get('character', []))
        parodies_str = ', '.join(categorized.get('parody', []))
        language = categorized.get('language', [])
        language_str = language[0] if language else ''
        category = categorized.get('category', [])
        category_str = category[0] if category else ''

        # Build all tags as formatted strings (type:name)
        all_tags = []
        for tag in tags:
            all_tags.append(f"{tag.type}:{tag.name}")
        tags_str = '\n'.join(all_tags)  # Store tags as newline-separated

        # Build metadata dict in standardized format (matching FIELD_DEFINITIONS)
        scan_metadata = {
            'title': metadata.get('doujin_title', ''),
            'artist': artists_str,  # Use singular to match schema
            'writer': groups_str,   # Map groups to writer field
            'characters': characters_str,
            'genre': category_str,  # Map category to genre
            'language_iso': language_str.lower() if language_str else '',
            'tags': tags_str,  # All tags formatted as type:name

            # nhentai-specific (stored in metadata but not mapped to Comic fields)
            'parodies': parodies_str,
            'groups': groups_str,
            'source': self.source_name,
            'source_used': metadata.get('source_used', ''),
            'matched_field': metadata.get('matched_field', ''),
            'search_strategy': metadata.get('search_strategy', 'primary'),
            'extracted_metadata': metadata.get('extracted_metadata', {}),
            'score_bonuses': metadata.get('score_bonuses', {}),
        }

        # Add metadata_json field containing the full metadata
        # This is used by the single-DB architecture to store flexible metadata
        try:
            import json
            # Create a clean copy for JSON serialization
            json_metadata = scan_metadata.copy()
            # Add raw response data if available
            if metadata:
                json_metadata['_raw'] = {k: v for k, v in metadata.items() if k not in json_metadata}
            
            scan_metadata['metadata_json'] = json.dumps(json_metadata, ensure_ascii=False)
        except Exception as e:
            # Don't fail if JSON serialization fails
            pass

        # All tags (categorized by type) - kept for backward compatibility
        all_tags_list = []
        for tag_type, tag_list in categorized.items():
            for tag_name in tag_list:
                all_tags_list.append(f"{tag_type}:{tag_name}")

        return ScanResult(
            confidence=confidence,
            source_id=str(metadata.get('doujin_id', '')),
            source_url=metadata.get('doujin_url', ''),
            metadata=scan_metadata,
            tags=all_tags_list,  # Use the list version for ScanResult.tags
            raw_response=metadata
        )

    def get_required_config_keys(self) -> List[str]:
        """nhentai scanner doesn't require any API keys"""
        return []


# ============================================================================
# Convenience Functions
# ============================================================================

def scan_file(filename: str, confidence_threshold: float = 0.4, config_path: Optional[str] = None) -> Optional[ScanResult]:
    """
    Scan a single file with nhentai scanner

    Args:
        filename: Filename to scan
        confidence_threshold: Minimum confidence (default: 0.4)
        config_path: Optional path to JSON config file

    Returns:
        ScanResult if found, None otherwise

    Example:
        >>> result = scan_file("[Artist] Title [English].cbz")
        >>> if result:
        ...     print(f"Found: {result.metadata['title']}")
        ...     print(f"Confidence: {result.confidence:.0%}")
    """
    # Load config from file if provided
    config = {'confidence_threshold': confidence_threshold}
    if config_path and Path(config_path).exists():
        with open(config_path, 'r') as f:
            file_config = json.load(f)
            config.update(file_config)

    scanner = NhentaiScanner(config)
    best_match, _ = scanner.scan(filename)
    return best_match


# ============================================================================
# CLI Interface
# ============================================================================

def main():
    """Command-line interface for the scanner"""
    parser = argparse.ArgumentParser(
        description='nhentai Scanner - Extract metadata from doujinshi filenames',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python nhentai_scanner_merged.py "[Artist] Title [English].cbz"
  python nhentai_scanner_merged.py "doujin.cbz" --threshold 0.5
  python nhentai_scanner_merged.py "file.cbz" --config config.json
  python nhentai_scanner_merged.py "file.cbz" --json > output.json
        """
    )

    parser.add_argument('filename', help='Filename to scan (can be full path)')
    parser.add_argument('-t', '--threshold', type=float, default=0.4,
                        help='Confidence threshold (0.0-1.0, default: 0.4)')
    parser.add_argument('-c', '--config', help='Path to JSON config file')
    parser.add_argument('--json', action='store_true',
                        help='Output as JSON')
    parser.add_argument('--no-fallback', action='store_true',
                        help='Disable fallback search strategies')
    parser.add_argument('--sort', choices=['date', 'popular'], default='date',
                        help='Sort search results by (default: date)')
    parser.add_argument('--source', choices=['net', 'xxx', 'both'], default='both',
                        help='Which source(s) to use: net (nhentai.net only), xxx (nhentai.xxx only), both (try both, default)')

    args = parser.parse_args()

    # Determine sources based on --source argument
    if args.source == 'net':
        sources = ["https://nhentai.net"]
    elif args.source == 'xxx':
        sources = ["https://nhentai.xxx"]
    else:  # both
        sources = ["https://nhentai.net", "https://nhentai.xxx"]

    # Build config
    config = {
        'confidence_threshold': args.threshold,
        'use_fallback_searches': not args.no_fallback,
        'sort_by': args.sort,
        'sources': sources
    }

    # Load config file if provided
    if args.config and Path(args.config).exists():
        with open(args.config, 'r') as f:
            file_config = json.load(f)
            config.update(file_config)

    # Scan the file
    try:
        scanner = NhentaiScanner(config)
        result, _ = scanner.scan(args.filename)

        if result:
            if args.json:
                # JSON output
                print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
            else:
                # Human-readable output
                print(f"Match found!")
                print(f"Confidence: {result.confidence:.1%} ({result.confidence_level.name})")
                print(f"\nTitle: {result.metadata['title']}")
                print(f"URL: {result.source_url}")
                print(f"ID: {result.source_id}")

                print(f"\nMetadata:")
                if result.metadata.get('artists'):
                    print(f"  Artists: {', '.join(result.metadata['artists'])}")
                if result.metadata.get('groups'):
                    print(f"  Groups: {', '.join(result.metadata['groups'])}")
                if result.metadata.get('parodies'):
                    print(f"  Parodies: {', '.join(result.metadata['parodies'])}")
                if result.metadata.get('characters'):
                    print(f"  Characters: {', '.join(result.metadata['characters'][:5])}")
                if result.metadata.get('language'):
                    print(f"  Language: {', '.join(result.metadata['language'])}")

                print(f"\nSearch Info:")
                print(f"  Source: {result.metadata.get('source_used', 'unknown')}")
                print(f"  Strategy: {result.metadata.get('search_strategy', 'unknown')}")
                print(f"  Matched field: {result.metadata.get('matched_field', 'unknown')}")

                bonuses = result.metadata.get('score_bonuses', {})
                if bonuses:
                    print(f"  Score bonuses: {bonuses}")

                print(f"\nTags ({len(result.tags)} total):")
                # Show first 10 tags
                for tag in result.tags[:10]:
                    print(f"  - {tag}")
                if len(result.tags) > 10:
                    print(f"  ... and {len(result.tags) - 10} more")
        else:
            if args.json:
                print(json.dumps({'error': 'No match found'}, indent=2))
            else:
                print("No match found above confidence threshold.")
            return 1

    except Exception as e:
        if args.json:
            print(json.dumps({'error': str(e)}, indent=2))
        else:
            print(f"Error: {e}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
