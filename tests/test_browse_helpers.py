"""Tests for v2 browse helper functions."""

from src.api.routers.v2._browse_helpers import (
    apply_random_sort,
    count_folder_children,
    fetch_sorted_browse_items,
    find_first_comic_metadata,
)


def test_apply_random_sort_is_reproducible_with_seed(test_db, sample_library, sample_folder, sample_comic):
    with test_db.get_session() as session:
        first_page, total = apply_random_sort(
            session, sample_folder.id, sample_library.id, offset=0, limit=10, seed=42
        )
        second_page, total_again = apply_random_sort(
            session, sample_folder.id, sample_library.id, offset=0, limit=10, seed=42
        )

    assert total == total_again
    assert first_page == second_page
    assert total >= 1


def test_count_folder_children(test_db, sample_library, sample_folder, sample_comic):
    with test_db.get_session() as session:
        num_folders, num_comics = count_folder_children(
            session, sample_folder.id, sample_library.id
        )

    assert num_folders == 0
    assert num_comics == 1


def test_fetch_sorted_browse_items_name_sort(test_db, sample_library, sample_folder, sample_comic):
    with test_db.get_session() as session:
        items, total = fetch_sorted_browse_items(
            session,
            sample_library.id,
            sample_folder,
            breadcrumbs=[],
            user=None,
            normalized_sort="name",
            offset=0,
            limit=50,
            per_volume_metadata=False,
        )

    assert total == 1
    assert len(items) == 1
    assert items[0]["type"] == "comic"
    assert items[0]["id"] == sample_comic.id


def test_find_first_comic_metadata():
    items = [{"type": "series", "id": 1}, {"type": "comic", "id": 2, "title": "Issue 1"}]
    assert find_first_comic_metadata(items)["id"] == 2
    assert find_first_comic_metadata([{"type": "series"}]) is None
