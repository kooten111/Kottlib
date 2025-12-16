"""
Pytest configuration and shared fixtures for API tests
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.models import Base, Library, Comic, User, Folder, ReadingProgress
from src.database import Database


@pytest.fixture(scope="session")
def test_data_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test data"""
    temp_dir = Path(tempfile.mkdtemp(prefix="yaclib_test_"))
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="session")
def test_db_path(test_data_dir: Path) -> Path:
    """Path to test database"""
    return test_data_dir / "test.db"


@pytest.fixture(scope="function")
def test_db(test_db_path: Path) -> Generator[Database, None, None]:
    """Create a fresh test database for each test"""
    # Remove existing DB
    if test_db_path.exists():
        test_db_path.unlink()

    # Create new database
    db = Database(str(test_db_path))

    # Create tables
    engine = create_engine(f"sqlite:///{test_db_path}")
    Base.metadata.create_all(engine)

    yield db

    # Cleanup
    db.close()
    if test_db_path.exists():
        test_db_path.unlink()


@pytest.fixture(scope="function")
def sample_user(test_db: Database) -> User:
    """Create a sample user for testing"""
    import time
    with test_db.get_session() as session:
        user = User(
            username="testuser",
            password_hash="test_hash",
            is_admin=True,
            created_at=int(time.time())
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


@pytest.fixture(scope="function")
def sample_library(test_db: Database, test_data_dir: Path) -> Library:
    """Create a sample library for testing"""
    import uuid
    import time
    
    library_path = test_data_dir / "library1"
    library_path.mkdir(exist_ok=True)

    with test_db.get_session() as session:
        library = Library(
            uuid=str(uuid.uuid4()),
            name="Test Library",
            path=str(library_path),
            created_at=int(time.time()),
            updated_at=int(time.time())
        )
        session.add(library)
        session.commit()
        session.refresh(library)
        return library


@pytest.fixture(scope="function")
def sample_folder(test_db: Database, sample_library: Library) -> Folder:
    """Create a sample folder for testing"""
    import time
    
    with test_db.get_session() as session:
        folder = Folder(
            name="Test Folder",
            path=str(Path(sample_library.path) / "Test Folder"),
            parent_id=None,
            library_id=sample_library.id,
            created_at=int(time.time()),
            updated_at=int(time.time())
        )
        session.add(folder)
        session.commit()
        session.refresh(folder)
        return folder


@pytest.fixture(scope="function")
def sample_comic(test_db: Database, sample_library: Library, sample_folder: Folder, test_data_dir: Path) -> Comic:
    """Create a sample comic for testing"""
    import time
    
    # Create a dummy comic file
    comic_path = test_data_dir / "library1" / "test_comic.cbz"
    comic_path.write_bytes(b"DUMMY_CBZ_DATA")

    with test_db.get_session() as session:
        comic = Comic(
            library_id=sample_library.id,
            folder_id=sample_folder.id,
            path=str(comic_path),
            filename="test_comic.cbz",
            hash="abc123",
            file_size=14,
            file_modified_at=int(time.time()),
            format="cbz",
            num_pages=24,
            title="Test Comic",
            series="Test Series",
            issue_number="1",
            year=2024,
            reading_direction="ltr",
            created_at=int(time.time()),
            updated_at=int(time.time())
        )
        session.add(comic)
        session.commit()
        session.refresh(comic)
        return comic


@pytest.fixture(scope="function")
def multiple_comics(test_db: Database, sample_library: Library, sample_folder: Folder, test_data_dir: Path) -> list[Comic]:
    """Create multiple sample comics for testing"""
    import time
    
    comics = []
    with test_db.get_session() as session:
        for i in range(5):
            comic_path = test_data_dir / "library1" / f"test_comic_{i}.cbz"
            comic_path.write_bytes(b"DUMMY_CBZ_DATA")

            comic = Comic(
                library_id=sample_library.id,
                folder_id=sample_folder.id,
                path=str(comic_path),
                filename=f"test_comic_{i}.cbz",
                hash=f"hash_{i}",
                file_size=14,
                file_modified_at=int(time.time()),
                format="cbz",
                num_pages=24 + i,
                title=f"Test Comic {i}",
                series="Test Series",
                issue_number=str(i + 1),
                year=2024,
                reading_direction="ltr",
                created_at=int(time.time()),
                updated_at=int(time.time())
            )
            session.add(comic)
            comics.append(comic)
        session.commit()
        for comic in comics:
            session.refresh(comic)
        return comics


@pytest.fixture(scope="function")
def sample_reading_progress(test_db: Database, sample_user: User, sample_comic: Comic) -> ReadingProgress:
    """Create sample reading progress for testing"""
    import time
    now = int(time.time())
    with test_db.get_session() as session:
        progress = ReadingProgress(
            user_id=sample_user.id,
            comic_id=sample_comic.id,
            current_page=5,
            total_pages=sample_comic.num_pages,
            progress_percent=(5 / sample_comic.num_pages * 100),
            is_completed=False,
            started_at=now,
            last_read_at=now
        )
        session.add(progress)
        session.commit()
        session.refresh(progress)
        return progress


@pytest.fixture(scope="function")
def test_client(test_db: Database) -> TestClient:
    """Create a FastAPI test client with test database"""
    from src.api.main import app

    # Override database dependency
    app.state.db = test_db

    client = TestClient(app)
    return client


@pytest.fixture(scope="function")
def authenticated_client(test_client: TestClient, sample_user: User) -> TestClient:
    """Create an authenticated test client"""
    # For simplicity, we'll add the user_id to the client's state
    # In real implementation, this would involve session/cookie handling
    test_client.cookies.set("user_id", str(sample_user.id))
    return test_client
