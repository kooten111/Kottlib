import time
import uuid
from pathlib import Path

from src.constants import ROOT_FOLDER_MARKER
from src.database.models import Comic, Folder, Library, Series
from src.scanner.cleanup import cleanup_missing_comics
from src.scanner.series_builder import rebuild_series_table


def test_cleanup_removes_missing_folders(test_db, test_data_dir):
    library_path = test_data_dir / "library1"
    current_folder_path = library_path / "Current Series"
    stale_folder_path = library_path / "Old Series (Digital) (Oak)"
    current_folder_path.mkdir(parents=True, exist_ok=True)

    current_comic_path = current_folder_path / "Current Series v01.cbz"
    current_comic_path.write_bytes(b"CURRENT")

    now = int(time.time())

    with test_db.get_session() as session:
        library = Library(
            uuid=str(uuid.uuid4()),
            name="Test Library",
            path=str(library_path),
            created_at=now,
            updated_at=now,
        )
        session.add(library)
        session.flush()

        root_folder = Folder(
            library_id=library.id,
            parent_id=None,
            path=str(library_path.resolve()),
            name=ROOT_FOLDER_MARKER,
            created_at=now,
            updated_at=now,
        )
        session.add(root_folder)
        session.flush()

        current_folder = Folder(
            library_id=library.id,
            parent_id=root_folder.id,
            path=str(current_folder_path.resolve()),
            name=current_folder_path.name,
            created_at=now,
            updated_at=now,
        )
        stale_folder = Folder(
            library_id=library.id,
            parent_id=root_folder.id,
            path=str(stale_folder_path.resolve()),
            name=stale_folder_path.name,
            created_at=now,
            updated_at=now,
        )
        session.add_all([current_folder, stale_folder])
        session.flush()

        current_comic = Comic(
            library_id=library.id,
            folder_id=current_folder.id,
            path=str(current_comic_path.resolve()),
            filename=current_comic_path.name,
            hash="current-hash",
            file_size=current_comic_path.stat().st_size,
            file_modified_at=now,
            format="cbz",
            num_pages=1,
            series=current_folder.name,
            created_at=now,
            updated_at=now,
        )
        stale_comic = Comic(
            library_id=library.id,
            folder_id=stale_folder.id,
            path=str((stale_folder_path / "Old Series v01.cbz").resolve()),
            filename="Old Series v01.cbz",
            hash="stale-hash",
            file_size=7,
            file_modified_at=now,
            format="cbz",
            num_pages=1,
            series=stale_folder.name,
            created_at=now,
            updated_at=now,
        )
        session.add_all([current_comic, stale_comic])
        session.commit()
        library_id = library.id
        stale_folder_id = stale_folder.id

    removed = cleanup_missing_comics(
        test_db,
        library_id,
        library_path.resolve(),
        {str(current_comic_path.resolve())},
        {str(current_folder_path.resolve())},
        "Test Library",
    )

    assert removed == 1

    with test_db.get_session() as session:
        assert session.get(Folder, stale_folder_id) is None
        remaining_folders = session.query(Folder).filter(Folder.library_id == library_id).all()
        assert {folder.name for folder in remaining_folders} == {ROOT_FOLDER_MARKER, current_folder_path.name}


def test_rebuild_series_table_removes_stale_series(test_db, test_data_dir):
    library_path = test_data_dir / "library1"
    library_path.mkdir(parents=True, exist_ok=True)
    comic_path = library_path / "Current Series v01.cbz"
    comic_path.write_bytes(b"CURRENT")

    now = int(time.time())

    with test_db.get_session() as session:
        library = Library(
            uuid=str(uuid.uuid4()),
            name="Test Library",
            path=str(library_path),
            created_at=now,
            updated_at=now,
        )
        session.add(library)
        session.flush()

        comic = Comic(
            library_id=library.id,
            folder_id=None,
            path=str(comic_path.resolve()),
            filename=comic_path.name,
            hash="current-series-hash",
            file_size=comic_path.stat().st_size,
            file_modified_at=now,
            format="cbz",
            num_pages=1,
            series="Current Series",
            created_at=now,
            updated_at=now,
        )
        stale_series = Series(
            library_id=library.id,
            name="Old Series (Digital) (Oak)",
            display_name="Old Series (Digital) (Oak)",
            comic_count=7,
            total_issues=7,
            created_at=now,
            updated_at=now,
        )
        session.add_all([comic, stale_series])
        session.commit()
        library_id = library.id

    rebuild_series_table(test_db, library_id)

    with test_db.get_session() as session:
        series_names = {
            series.name: (series.comic_count, series.total_issues)
            for series in session.query(Series).filter(Series.library_id == library_id).all()
        }

    assert series_names == {"Current Series": (1, 1)}


def test_cleanup_normalizes_paths_for_missing_detection(test_db, test_data_dir):
    library_root = test_data_dir / "library_norm"
    library_root.mkdir(parents=True, exist_ok=True)

    existing_file = library_root / "existing.cbz"
    existing_file.write_bytes(b"EXISTING")
    stale_file = library_root / "stale.cbz"

    now = int(time.time())

    with test_db.get_session() as session:
        library = Library(
            uuid=str(uuid.uuid4()),
            name="Test Library",
            path=str(library_root),
            created_at=now,
            updated_at=now,
        )
        session.add(library)
        session.flush()

        current = Comic(
            library_id=library.id,
            folder_id=None,
            path=str(existing_file.resolve()),
            filename=existing_file.name,
            hash="keep-hash",
            file_size=existing_file.stat().st_size,
            file_modified_at=now,
            format="cbz",
            num_pages=1,
            series="Series A",
            created_at=now,
            updated_at=now,
        )
        missing = Comic(
            library_id=library.id,
            folder_id=None,
            path=str(stale_file.resolve()),
            filename=stale_file.name,
            hash="drop-hash",
            file_size=10,
            file_modified_at=now,
            format="cbz",
            num_pages=1,
            series="Series B",
            created_at=now,
            updated_at=now,
        )
        session.add_all([current, missing])
        session.commit()
        library_id = library.id

    # Simulate scanner-discovered paths in a different path representation
    # (non-canonical input) to validate normalization behavior.
    discovered_paths = {str(library_root / "." / existing_file.name)}

    removed = cleanup_missing_comics(
        test_db,
        library_id,
        library_root,
        discovered_paths,
        discovered_folder_paths=set(),
        library_name="Test Library",
    )

    assert removed == 1

    with test_db.get_session() as session:
        remaining = session.query(Comic).filter(Comic.library_id == library_id).all()
        assert len(remaining) == 1
        assert remaining[0].filename == "existing.cbz"
