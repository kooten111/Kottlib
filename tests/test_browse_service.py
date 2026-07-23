"""Tests for browse_service helpers."""

from src.constants import ROOT_FOLDER_MARKER
from src.database.models import Folder, Series
from src.services.browse_service import (
    normalize_sort,
    cache_safe_copy,
    apply_progress_overlay,
    parse_library_settings,
    get_primary_scanner,
    resolve_browse_path,
    build_folder_metadata,
    BrowsePathNotFoundError,
)


def test_normalize_sort_aliases():
    assert normalize_sort("date_added") == "recent"
    assert normalize_sort("last_updated") == "updated"
    assert normalize_sort("name") == "name"
    assert normalize_sort(None) == "name"


def test_cache_safe_copy_strips_progress():
    payload = {
        "items": [
            {"type": "comic", "id": 1, "progress_percent": 50, "is_completed": True, "current_page": 3},
            {"type": "folder", "id": 2},
        ],
        "comic": {"id": 3, "progress_percent": 10, "is_completed": False, "current_page": 1},
    }

    cached = cache_safe_copy(payload)

    assert cached["items"][0]["progress_percent"] == 0
    assert cached["items"][0]["is_completed"] is False
    assert cached["items"][0]["current_page"] == 0
    assert cached["items"][1]["type"] == "folder"
    assert cached["comic"]["current_page"] == 0


def test_apply_progress_overlay(test_db, sample_comic, sample_reading_progress):
    from src.database import get_user_by_username

    payload = {
        "items": [{"type": "comic", "id": sample_comic.id, "progress_percent": 0, "is_completed": False, "current_page": 0}]
    }

    with test_db.get_session() as session:
        admin = get_user_by_username(session, "admin")
        result = apply_progress_overlay(payload, session, admin)

    comic_item = result["items"][0]
    assert comic_item["current_page"] == sample_reading_progress.current_page
    assert comic_item["is_completed"] is False


def test_parse_library_settings_handles_json_string():
    assert parse_library_settings('{"scanner": {"primary_scanner": "local"}}') == {
        "scanner": {"primary_scanner": "local"}
    }
    assert parse_library_settings(None) == {}
    assert parse_library_settings("not-json") == {}


def test_get_primary_scanner():
    settings = {"scanner": {"primary_scanner": "mangadex"}}
    assert get_primary_scanner(settings) == "mangadex"
    assert get_primary_scanner({}) is None


def test_resolve_browse_path_walks_folders(test_db, sample_library, sample_folder):
    import time

    with test_db.get_session() as session:
        root = session.query(Folder).filter_by(
            library_id=sample_library.id, name=ROOT_FOLDER_MARKER
        ).one()

        child = Folder(
            name="Nested",
            path=f"{sample_folder.path}/Nested",
            parent_id=sample_folder.id,
            library_id=sample_library.id,
            created_at=int(time.time()),
            updated_at=int(time.time()),
        )
        session.add(child)
        session.commit()

        folder, breadcrumbs, comic = resolve_browse_path(
            session,
            sample_library.id,
            root,
            f"{sample_folder.name}/Nested",
        )

    assert comic is None
    assert folder.name == "Nested"
    assert [crumb["name"] for crumb in breadcrumbs] == [sample_folder.name, "Nested"]


def test_resolve_browse_path_missing_segment_raises(test_db, sample_library):
    with test_db.get_session() as session:
        root = session.query(Folder).filter_by(
            library_id=sample_library.id, name=ROOT_FOLDER_MARKER
        ).one()

        try:
            resolve_browse_path(session, sample_library.id, root, "missing-folder")
            assert False, "expected BrowsePathNotFoundError"
        except BrowsePathNotFoundError as exc:
            assert str(exc) == "missing-folder"


def test_build_folder_metadata_merges_series(test_db, sample_library, sample_folder):
    import time

    with test_db.get_session() as session:
        series = Series(
            library_id=sample_library.id,
            name=sample_folder.name,
            display_name="Display Name",
            description="A synopsis",
            writer="Writer",
            created_at=int(time.time()),
            updated_at=int(time.time()),
        )
        session.add(series)
        session.commit()

        root = session.query(Folder).filter_by(
            library_id=sample_library.id, name=ROOT_FOLDER_MARKER
        ).one()
        metadata = build_folder_metadata(
            session, sample_library.id, sample_folder, root, total_items=3
        )

    assert metadata["name"] == sample_folder.name
    assert metadata["total_issues"] == 3
    assert metadata["display_name"] == "Display Name"
    assert metadata["synopsis"] == "A synopsis"
    assert metadata["writer"] == "Writer"
