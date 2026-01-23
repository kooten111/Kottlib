"""
Tests for MangaDex Scanner

Tests cover:
- Scanner initialization and configuration
- Metadata extraction functions
- Title matching and confidence scoring
- API client mocking
- Scanner discovery integration
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

# Import from scanners directory at project root (pythonpath set in pytest.ini)
from scanners.mangadex.mangadex_scanner import (
    MangaDexScanner,
    MangaDexAPI,
    normalize_title,
    calculate_title_similarity,
    get_best_title_match,
    extract_authors,
    extract_artists,
    extract_tags,
    extract_external_links,
    extract_cover_url,
    get_primary_title,
    get_alternative_titles,
    get_localized_description,
)
from src.metadata_providers.base import ScanLevel, ScanResult


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_manga_response():
    """Sample MangaDex manga API response"""
    return {
        "id": "a96676e5-8ae2-425e-b549-7f15dd34a6d8",
        "type": "manga",
        "attributes": {
            "title": {
                "en": "One Piece",
                "ja-ro": "One Piece",
                "ja": "ワンピース"
            },
            "altTitles": [
                {"en": "OP"},
                {"ko": "원피스"},
                {"zh": "海贼王"}
            ],
            "description": {
                "en": "A story about pirates.",
                "ja": "海賊の物語。"
            },
            "status": "ongoing",
            "year": 1997,
            "contentRating": "safe",
            "originalLanguage": "ja",
            "lastChapter": "1100",
            "tags": [
                {
                    "id": "tag1",
                    "type": "tag",
                    "attributes": {
                        "name": {"en": "Action"},
                        "group": "genre"
                    }
                },
                {
                    "id": "tag2",
                    "type": "tag",
                    "attributes": {
                        "name": {"en": "Adventure"},
                        "group": "genre"
                    }
                },
                {
                    "id": "tag3",
                    "type": "tag",
                    "attributes": {
                        "name": {"en": "Shounen"},
                        "group": "demographic"
                    }
                }
            ],
            "links": {
                "al": "21",
                "mal": "13"
            }
        },
        "relationships": [
            {
                "id": "author1",
                "type": "author",
                "attributes": {
                    "name": "Eiichiro Oda"
                }
            },
            {
                "id": "artist1",
                "type": "artist",
                "attributes": {
                    "name": "Eiichiro Oda"
                }
            },
            {
                "id": "cover1",
                "type": "cover_art",
                "attributes": {
                    "fileName": "cover.jpg"
                }
            }
        ]
    }


@pytest.fixture
def sample_search_response(sample_manga_response):
    """Sample MangaDex search API response"""
    return {
        "result": "ok",
        "data": [sample_manga_response]
    }


# ============================================================================
# Scanner Initialization Tests
# ============================================================================

class TestMangaDexScannerInit:
    """Tests for MangaDex scanner initialization"""

    def test_default_initialization(self):
        """Test scanner initializes with default config"""
        scanner = MangaDexScanner()
        
        assert scanner.source_name == "MangaDex"
        assert scanner.scan_level == ScanLevel.SERIES
        assert scanner.confidence_threshold == 0.6
        assert scanner.max_results == 10
        assert scanner.languages == ['en']

    def test_custom_config(self):
        """Test scanner with custom configuration"""
        config = {
            'confidence_threshold': 0.8,
            'max_results': 20,
            'languages': ['ja', 'en'],
            'timeout': 60
        }
        scanner = MangaDexScanner(config)
        
        assert scanner.confidence_threshold == 0.8
        assert scanner.max_results == 20
        assert scanner.languages == ['ja', 'en']
        assert scanner.timeout == 60

    def test_config_schema(self):
        """Test configuration schema is properly defined"""
        scanner = MangaDexScanner()
        schema = scanner.get_config_schema()
        
        # Check expected options exist
        keys = [opt.key for opt in schema]
        assert 'languages' in keys
        assert 'confidence_threshold' in keys
        assert 'max_results' in keys
        assert 'timeout' in keys
        assert 'rate_limit_delay' in keys

        # Check languages option specifically
        languages_opt = next(opt for opt in schema if opt.key == 'languages')
        assert languages_opt.default == ['en']
        assert 'en' in languages_opt.options
        assert 'ja' in languages_opt.options


# ============================================================================
# Title Matching Tests
# ============================================================================

class TestTitleMatching:
    """Tests for title matching and confidence scoring"""

    def test_normalize_title(self):
        """Test title normalization"""
        assert normalize_title("One Piece") == "one piece"
        assert normalize_title("  One   Piece  ") == "one piece"
        assert normalize_title("One-Piece!") == "onepiece"
        assert normalize_title("") == ""
        assert normalize_title(None) == ""

    def test_exact_match(self):
        """Test exact title match gives 1.0 confidence"""
        score = calculate_title_similarity("One Piece", "One Piece")
        assert score == 1.0

    def test_case_insensitive_match(self):
        """Test case insensitive matching"""
        score = calculate_title_similarity("one piece", "ONE PIECE")
        assert score == 1.0

    def test_substring_match(self):
        """Test substring match gives high confidence"""
        score = calculate_title_similarity("One Piece", "One Piece: Romance Dawn")
        assert score >= 0.9

    def test_fuzzy_match(self):
        """Test fuzzy matching gives appropriate confidence"""
        score = calculate_title_similarity("One Piece", "One Peace")
        assert 0.5 < score < 1.0

    def test_no_match(self):
        """Test completely different titles give low confidence"""
        score = calculate_title_similarity("One Piece", "Naruto")
        assert score < 0.5

    def test_best_title_match(self, sample_manga_response):
        """Test finding best matching title from manga"""
        score, title = get_best_title_match("One Piece", sample_manga_response, ['en'])
        assert score == 1.0
        assert title == "One Piece"

    def test_best_title_match_alt_title(self, sample_manga_response):
        """Test matching with alternative title"""
        score, title = get_best_title_match("OP", sample_manga_response, ['en'])
        assert score == 1.0
        assert title == "OP"

    def test_best_title_match_japanese(self, sample_manga_response):
        """Test matching with Japanese title"""
        score, title = get_best_title_match("ワンピース", sample_manga_response, ['ja', 'en'])
        assert score == 1.0
        assert title == "ワンピース"


# ============================================================================
# Metadata Extraction Tests
# ============================================================================

class TestMetadataExtraction:
    """Tests for metadata extraction from MangaDex responses"""

    def test_extract_authors(self, sample_manga_response):
        """Test author extraction"""
        authors = extract_authors(sample_manga_response)
        assert "Eiichiro Oda" in authors

    def test_extract_artists(self, sample_manga_response):
        """Test artist extraction"""
        artists = extract_artists(sample_manga_response)
        assert "Eiichiro Oda" in artists

    def test_extract_tags(self, sample_manga_response):
        """Test tag/genre extraction"""
        genres, tags = extract_tags(sample_manga_response)
        assert "Action" in genres
        assert "Adventure" in genres
        assert "Shounen" in tags  # demographic, not genre

    def test_extract_external_links(self, sample_manga_response):
        """Test external links extraction"""
        links = extract_external_links(sample_manga_response)
        assert 'anilist' in links
        assert 'myanimelist' in links
        # Verify the MAL link is properly formatted as a URL
        mal_url = links['myanimelist']
        assert mal_url.startswith('https://myanimelist.net/manga/')

    def test_extract_cover_url(self, sample_manga_response):
        """Test cover URL extraction"""
        cover_url = extract_cover_url(sample_manga_response)
        assert cover_url is not None
        assert sample_manga_response['id'] in cover_url
        assert 'cover.jpg' in cover_url

    def test_get_primary_title(self, sample_manga_response):
        """Test primary title extraction with language preference"""
        title = get_primary_title(sample_manga_response, ['en'])
        assert title == "One Piece"
        
        title_ja = get_primary_title(sample_manga_response, ['ja', 'en'])
        assert title_ja == "ワンピース"

    def test_get_alternative_titles(self, sample_manga_response):
        """Test alternative titles extraction"""
        alt_titles = get_alternative_titles(sample_manga_response)
        assert "OP" in alt_titles
        assert "원피스" in alt_titles

    def test_get_localized_description(self, sample_manga_response):
        """Test localized description extraction"""
        desc = get_localized_description(sample_manga_response, ['en'])
        assert desc == "A story about pirates."
        
        desc_ja = get_localized_description(sample_manga_response, ['ja', 'en'])
        assert desc_ja == "海賊の物語。"


# ============================================================================
# Scanner Scan Method Tests
# ============================================================================

class TestMangaDexScannerScan:
    """Tests for the scan method with mocked API"""

    @patch.object(MangaDexAPI, 'search_manga')
    def test_scan_success(self, mock_search, sample_manga_response):
        """Test successful scan"""
        mock_search.return_value = [sample_manga_response]
        
        scanner = MangaDexScanner()
        best_match, all_matches = scanner.scan("One Piece")
        
        assert best_match is not None
        assert best_match.confidence == 1.0
        assert best_match.metadata['title'] == "One Piece"
        assert best_match.metadata['mangadex_id'] == sample_manga_response['id']
        assert len(all_matches) == 1

    @patch.object(MangaDexAPI, 'search_manga')
    def test_scan_no_results(self, mock_search):
        """Test scan with no results"""
        mock_search.return_value = []
        
        scanner = MangaDexScanner()
        best_match, all_matches = scanner.scan("Nonexistent Manga")
        
        assert best_match is None
        assert len(all_matches) == 0

    @patch.object(MangaDexAPI, 'search_manga')
    def test_scan_below_threshold(self, mock_search, sample_manga_response):
        """Test scan filters results below confidence threshold"""
        mock_search.return_value = [sample_manga_response]
        
        scanner = MangaDexScanner({'confidence_threshold': 0.99})
        best_match, all_matches = scanner.scan("Completely Different Title")
        
        # Low match should be filtered out
        assert best_match is None or best_match.confidence >= 0.99

    @patch.object(MangaDexAPI, 'search_manga')
    def test_scan_with_language_filter(self, mock_search, sample_manga_response):
        """Test scan passes language filter to API"""
        mock_search.return_value = [sample_manga_response]
        
        scanner = MangaDexScanner({'languages': ['ja', 'en']})
        scanner.scan("One Piece")
        
        mock_search.assert_called_once()
        call_args = mock_search.call_args
        assert call_args[1]['languages'] == ['ja', 'en']

    @patch.object(MangaDexAPI, 'search_manga')
    def test_scan_metadata_mapping(self, mock_search, sample_manga_response):
        """Test metadata is correctly mapped"""
        mock_search.return_value = [sample_manga_response]
        
        scanner = MangaDexScanner()
        best_match, _ = scanner.scan("One Piece")
        
        meta = best_match.metadata
        
        # Check required mappings from requirements
        assert meta.get('title') == "One Piece"
        assert meta.get('writer') == "Eiichiro Oda"
        assert meta.get('artist') == "Eiichiro Oda"
        assert meta.get('status') == "Ongoing"
        assert meta.get('year') == 1997
        assert meta.get('content_rating') == "safe"
        assert meta.get('original_language') == "ja"
        assert meta.get('latest_chapter') == "1100"
        assert meta.get('mangadex_id') == sample_manga_response['id']
        assert 'Action' in meta.get('genre', '')
        assert meta.get('external_links') is not None


# ============================================================================
# Scanner Discovery Tests
# ============================================================================

class TestScannerDiscovery:
    """Tests for scanner auto-discovery"""

    def test_scanner_discovered(self):
        """Test MangaDex scanner is discovered by scanner manager"""
        from src.metadata_providers.manager import discover_scanners
        
        scanners = discover_scanners()
        scanner_names = []
        
        for scanner_class in scanners:
            try:
                instance = scanner_class()
                scanner_names.append(instance.source_name)
            except Exception:
                pass
        
        assert "MangaDex" in scanner_names


# ============================================================================
# API Client Tests
# ============================================================================

class TestMangaDexAPI:
    """Tests for MangaDex API client"""

    def test_rate_limit_delay(self):
        """Test rate limit delay is configured correctly"""
        api = MangaDexAPI(rate_limit_delay=0.5)
        assert api.rate_limit_delay == 0.5

    @patch('requests.Session.get')
    def test_api_timeout(self, mock_get):
        """Test API timeout is applied"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response
        
        api = MangaDexAPI(timeout=60)
        api.search_manga("test")
        
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs['timeout'] == 60

    @patch('requests.Session.get')
    def test_api_includes_relationships(self, mock_get):
        """Test API includes author, artist, cover relationships"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response
        
        api = MangaDexAPI()
        api.search_manga("test")
        
        call_kwargs = mock_get.call_args[1]
        params = call_kwargs['params']
        assert 'includes[]' in params
        includes = params['includes[]']
        assert 'author' in includes
        assert 'artist' in includes
        assert 'cover_art' in includes
