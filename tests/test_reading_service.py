"""Tests for reading_service."""

import time

from src.database import get_user_by_username
from src.database.models import ReadingProgress
from src.services.reading_service import (
    update_reading_progress,
    get_continue_reading,
    add_to_favorites,
    remove_from_favorites,
)


def test_update_reading_progress_creates_record(test_db, sample_comic):
    with test_db.get_session() as session:
        admin = get_user_by_username(session, "admin")

        result = update_reading_progress(
            session,
            user_id=admin.id,
            comic_id=sample_comic.id,
            current_page=3,
            total_pages=sample_comic.num_pages,
        )

        assert result["current_page"] == 3
        assert result["total_pages"] == sample_comic.num_pages

        stored = session.query(ReadingProgress).filter_by(
            user_id=admin.id, comic_id=sample_comic.id
        ).one()
        assert stored.current_page == 3
        assert stored.last_read_at > 0


def test_get_continue_reading_filters_by_library(test_db, sample_library, sample_comic, sample_reading_progress):
    with test_db.get_session() as session:
        admin = get_user_by_username(session, "admin")

        results = get_continue_reading(session, admin.id, library_id=sample_library.id, limit=10)

        assert len(results) == 1
        assert results[0]["comic_id"] == sample_comic.id
        assert results[0]["current_page"] == sample_reading_progress.current_page


def test_favorites_add_and_remove(test_db, sample_comic):
    with test_db.get_session() as session:
        admin = get_user_by_username(session, "admin")

        added = add_to_favorites(session, admin.id, sample_comic.id)
        assert added["success"] is True

        again = add_to_favorites(session, admin.id, sample_comic.id)
        assert again["success"] is True

        removed = remove_from_favorites(session, admin.id, sample_comic.id)
        assert removed["success"] is True

        missing = remove_from_favorites(session, admin.id, sample_comic.id)
        assert missing["success"] is False
