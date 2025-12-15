"""
Tests for MangaDex Cover API

Tests the MangaDex cover fetching and selection endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


# Mock MangaDex client responses
MOCK_MANGA_SEARCH_RESULT = [
    {
        'manga_id': 'manga-123',
        'title': 'Test Manga',
        'alt_titles': ['TM', 'テストマンガ'],
        'description': 'A test manga',
        'year': 2020,
        'status': 'completed',
        'covers': [
            {
                'cover_id': 'cover-1',
                'volume': '1',
                'description': 'Volume 1 cover',
                'thumbnail_url': 'https://uploads.mangadex.org/covers/manga-123/cover1.jpg.256.jpg',
                'full_url': 'https://uploads.mangadex.org/covers/manga-123/cover1.jpg'
            },
            {
                'cover_id': 'cover-2',
                'volume': '2',
                'description': 'Volume 2 cover',
                'thumbnail_url': 'https://uploads.mangadex.org/covers/manga-123/cover2.jpg.256.jpg',
                'full_url': 'https://uploads.mangadex.org/covers/manga-123/cover2.jpg'
            }
        ]
    }
]


class TestMangaDexClient:
    """Tests for the MangaDex client"""

    def test_client_creation(self):
        """Test that client can be instantiated"""
        from src.services.mangadex_client import MangaDexClient
        client = MangaDexClient()
        assert client is not None
        assert client.session is not None

    def test_singleton_pattern(self):
        """Test that get_mangadex_client returns same instance"""
        from src.services.mangadex_client import get_mangadex_client

        client1 = get_mangadex_client()
        client2 = get_mangadex_client()
        assert client1 is client2

    def test_rate_limiting(self):
        """Test that rate limiting is applied"""
        import time
        from src.services.mangadex_client import MangaDexClient, RATE_LIMIT_DELAY

        client = MangaDexClient()

        # Make a request (it will fail due to network, but rate limit will be recorded)
        start = time.time()
        client._make_request('/test')
        client._make_request('/test')
        elapsed = time.time() - start

        # Second request should have waited at least RATE_LIMIT_DELAY
        assert elapsed >= RATE_LIMIT_DELAY

    @patch('src.services.mangadex_client.MangaDexClient._make_request')
    def test_search_manga(self, mock_request):
        """Test manga search with mocked API"""
        from src.services.mangadex_client import MangaDexClient

        mock_request.return_value = {
            'data': [
                {
                    'id': 'manga-123',
                    'attributes': {
                        'title': {'en': 'Test Manga'},
                        'altTitles': [{'ja': 'テスト'}],
                        'description': {'en': 'Description'},
                        'year': 2020,
                        'status': 'completed'
                    },
                    'relationships': [
                        {
                            'type': 'cover_art',
                            'id': 'cover-abc',
                            'attributes': {'fileName': 'cover.jpg'}
                        }
                    ]
                }
            ]
        }

        client = MangaDexClient()
        results = client.search_manga('Test Manga')

        assert len(results) == 1
        assert results[0].manga_id == 'manga-123'
        assert results[0].title == 'Test Manga'
        assert results[0].cover_id == 'cover-abc'

    @patch('src.services.mangadex_client.MangaDexClient._make_request')
    def test_get_manga_covers(self, mock_request):
        """Test getting covers for a manga"""
        from src.services.mangadex_client import MangaDexClient

        mock_request.return_value = {
            'data': [
                {
                    'id': 'cover-1',
                    'attributes': {
                        'fileName': 'vol1.jpg',
                        'volume': '1',
                        'description': 'Volume 1',
                        'locale': 'en'
                    }
                },
                {
                    'id': 'cover-2',
                    'attributes': {
                        'fileName': 'vol2.jpg',
                        'volume': '2',
                        'description': None,
                        'locale': 'en'
                    }
                }
            ]
        }

        client = MangaDexClient()
        covers = client.get_manga_covers('manga-123')

        assert len(covers) == 2
        assert covers[0].cover_id == 'cover-1'
        assert covers[0].volume == '1'
        assert 'manga-123' in covers[0].full_url

    def test_empty_search_result(self):
        """Test handling of empty search results"""
        from src.services.mangadex_client import MangaDexClient

        client = MangaDexClient()
        # Network request will fail in test environment
        results = client.search_manga('NonexistentManga')
        assert results == []


class TestMangaDexCoverDataclasses:
    """Tests for MangaDex cover dataclasses"""

    def test_mangadex_cover_creation(self):
        """Test MangaDexCover dataclass"""
        from src.services.mangadex_client import MangaDexCover

        cover = MangaDexCover(
            cover_id='cover-123',
            manga_id='manga-456',
            filename='cover.jpg',
            volume='1',
            description='Test cover',
            locale='en',
            thumbnail_url='https://example.com/thumb.jpg',
            full_url='https://example.com/full.jpg'
        )

        assert cover.cover_id == 'cover-123'
        assert cover.manga_id == 'manga-456'
        assert cover.volume == '1'

    def test_mangadex_manga_creation(self):
        """Test MangaDexManga dataclass"""
        from src.services.mangadex_client import MangaDexManga

        manga = MangaDexManga(
            manga_id='manga-123',
            title='Test Manga',
            alt_titles=['TM'],
            description='A test',
            year=2020,
            status='completed'
        )

        assert manga.manga_id == 'manga-123'
        assert manga.title == 'Test Manga'
        assert len(manga.alt_titles) == 1


class TestCoverModel:
    """Tests for the Cover model changes"""

    def test_cover_model_has_source_fields(self):
        """Test that Cover model has source and source_url fields"""
        from src.database.models import Cover

        # Check that the class has the expected attributes
        mapper = Cover.__mapper__
        columns = {c.name for c in mapper.columns}

        assert 'source' in columns
        assert 'source_url' in columns

    def test_cover_source_default_value(self):
        """Test that Cover.source defaults to 'archive'"""
        from src.database.models import Cover

        # Get the default value from the column definition
        source_column = Cover.__table__.c.source
        assert source_column.default.arg == 'archive'


class TestDatabaseMigration:
    """Tests for database migration functionality"""

    def test_migration_module_exists(self):
        """Test that the migration module exists and can be imported"""
        from src.database.migrations import add_cover_source_fields
        assert hasattr(add_cover_source_fields, 'upgrade')
        assert hasattr(add_cover_source_fields, 'downgrade')


class TestCreateCoverFunction:
    """Tests for the create_cover function with new parameters"""

    def test_create_cover_signature(self):
        """Test that create_cover has the new source parameters"""
        import inspect
        from src.database import create_cover

        sig = inspect.signature(create_cover)
        params = list(sig.parameters.keys())

        assert 'source' in params
        assert 'source_url' in params

    def test_create_cover_default_source(self):
        """Test that source defaults to 'archive'"""
        import inspect
        from src.database import create_cover

        sig = inspect.signature(create_cover)
        source_param = sig.parameters['source']

        assert source_param.default == 'archive'
