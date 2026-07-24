"""Tests for v2 browse helper functions."""

import time
from pathlib import Path

from src.constants import ROOT_FOLDER_MARKER
from src.database.models import Comic, Folder, ReadingProgress, User
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


def _add_comic(session, library, folder, filename: str, title: str) -> Comic:
    now = int(time.time())
    comic_path = Path(library.path) / folder.name / filename
    comic_path.parent.mkdir(parents=True, exist_ok=True)
    comic_path.write_bytes(b"DUMMY")
    comic = Comic(
        library_id=library.id,
        folder_id=folder.id,
        path=str(comic_path),
        filename=filename,
        hash=f"hash-{folder.name}-{filename}",
        file_size=5,
        file_modified_at=now,
        format="cbz",
        num_pages=100,
        title=title,
        series=folder.name,
        reading_direction="ltr",
        created_at=now,
        updated_at=now,
    )
    session.add(comic)
    session.flush()
    return comic


def _add_progress(
    session,
    user_id: int,
    comic_id: int,
    *,
    progress_percent: float,
    is_completed: bool = False,
) -> None:
    now = int(time.time())
    session.add(
        ReadingProgress(
            user_id=user_id,
            comic_id=comic_id,
            current_page=int(progress_percent) if not is_completed else 99,
            total_pages=100,
            progress_percent=progress_percent,
            is_completed=is_completed,
            started_at=now,
            last_read_at=now,
        )
    )


def test_progress_sort_orders_folders_by_avg_volume_progress(test_db, sample_library, sample_user):
    """Folders with higher average volume progress come first."""
    with test_db.get_session() as session:
        root = session.query(Folder).filter_by(
            library_id=sample_library.id,
            name=ROOT_FOLDER_MARKER,
        ).first()
        user = session.get(User, sample_user.id)
        now = int(time.time())

        high = Folder(
            name="Almost Done",
            path=str(Path(sample_library.path) / "Almost Done"),
            parent_id=root.id,
            library_id=sample_library.id,
            created_at=now,
            updated_at=now,
        )
        mid = Folder(
            name="Halfway",
            path=str(Path(sample_library.path) / "Halfway"),
            parent_id=root.id,
            library_id=sample_library.id,
            created_at=now,
            updated_at=now,
        )
        unread = Folder(
            name="Unread Series",
            path=str(Path(sample_library.path) / "Unread Series"),
            parent_id=root.id,
            library_id=sample_library.id,
            created_at=now,
            updated_at=now,
        )
        session.add_all([high, mid, unread])
        session.flush()

        # high: completed + 50% → avg 75
        high_a = _add_comic(session, sample_library, high, "a.cbz", "A")
        high_b = _add_comic(session, sample_library, high, "b.cbz", "B")
        _add_progress(session, user.id, high_a.id, progress_percent=100.0, is_completed=True)
        _add_progress(session, user.id, high_b.id, progress_percent=50.0)

        # mid: 40% + unread → avg 20
        mid_a = _add_comic(session, sample_library, mid, "a.cbz", "A")
        _add_comic(session, sample_library, mid, "b.cbz", "B")
        _add_progress(session, user.id, mid_a.id, progress_percent=40.0)

        # unread: no progress rows → avg 0
        _add_comic(session, sample_library, unread, "a.cbz", "A")
        session.commit()

        items, total = fetch_sorted_browse_items(
            session,
            sample_library.id,
            root,
            breadcrumbs=[],
            user=user,
            normalized_sort="progress",
            offset=0,
            limit=50,
            per_volume_metadata=False,
        )

    folder_names = [item["name"] for item in items if item["type"] != "comic"]
    assert total == 3
    assert folder_names == ["Almost Done", "Halfway", "Unread Series"]


def test_progress_sort_orders_comics_by_volume_percent(
    test_db, sample_library, sample_folder, sample_user
):
    """Comics inside a folder sort by completed/percent, not last_read_at."""
    with test_db.get_session() as session:
        folder = session.get(Folder, sample_folder.id)
        user = session.get(User, sample_user.id)

        low = _add_comic(session, sample_library, folder, "low.cbz", "Low")
        high = _add_comic(session, sample_library, folder, "high.cbz", "High")
        done = _add_comic(session, sample_library, folder, "done.cbz", "Done")
        _add_comic(session, sample_library, folder, "none.cbz", "None")

        # Older last_read on the low-progress comic so last_read_at order would invert.
        now = int(time.time())
        session.add(
            ReadingProgress(
                user_id=user.id,
                comic_id=low.id,
                current_page=10,
                total_pages=100,
                progress_percent=10.0,
                is_completed=False,
                started_at=now - 100,
                last_read_at=now,  # most recent
            )
        )
        session.add(
            ReadingProgress(
                user_id=user.id,
                comic_id=high.id,
                current_page=80,
                total_pages=100,
                progress_percent=80.0,
                is_completed=False,
                started_at=now - 200,
                last_read_at=now - 50,
            )
        )
        session.add(
            ReadingProgress(
                user_id=user.id,
                comic_id=done.id,
                current_page=99,
                total_pages=100,
                progress_percent=99.0,
                is_completed=True,
                started_at=now - 300,
                last_read_at=now - 100,
            )
        )
        session.commit()

        items, total = fetch_sorted_browse_items(
            session,
            sample_library.id,
            folder,
            breadcrumbs=[],
            user=user,
            normalized_sort="progress",
            offset=0,
            limit=50,
            per_volume_metadata=False,
        )

    comic_titles = [item["title"] for item in items if item["type"] == "comic"]
    # sample_comic from fixture is also in this folder
    assert "Done" in comic_titles
    done_idx = comic_titles.index("Done")
    high_idx = comic_titles.index("High")
    low_idx = comic_titles.index("Low")
    none_idx = comic_titles.index("None")
    assert done_idx < high_idx < low_idx < none_idx
    assert total >= 4
