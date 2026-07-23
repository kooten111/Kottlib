"""Tests for search_service."""

import pytest

from src.services.search_service import search_comics, search_comics_fts, advanced_search


def test_search_comics_by_filename(test_db, sample_library, sample_comic):
    with test_db.get_session() as session:
        results = search_comics(session, sample_library.id, sample_comic.filename[:5])

    assert len(results) >= 1
    assert any(comic.id == sample_comic.id for comic in results)


def test_search_comics_unknown_library_raises(test_db):
    with test_db.get_session() as session:
        with pytest.raises(ValueError, match="Library 9999 not found"):
            search_comics(session, 9999, "anything")


def test_search_comics_fts_empty_query_returns_empty(test_db, sample_library):
    with test_db.get_session() as session:
        assert search_comics_fts(session, sample_library.id, "") == []
        assert search_comics_fts(session, sample_library.id, "   ") == []


def test_advanced_search_returns_pagination_shape(test_db, sample_library, sample_comic):
    with test_db.get_session() as session:
        payload = advanced_search(
            session,
            sample_library.id,
            filters={"series": sample_comic.series},
            limit=10,
            offset=0,
        )

    assert "results" in payload
    assert "total" in payload
    assert payload["limit"] == 10
    assert payload["offset"] == 0
