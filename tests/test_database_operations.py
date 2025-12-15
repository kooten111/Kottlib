"""
Test database operations for library and comic CRUD functionality.
"""
import pytest
from pathlib import Path

from src.database import (
    Database,
    create_library,
    get_library_by_id,
    get_library_by_path,
    get_all_libraries,
    update_library,
    delete_library,
    create_comic,
    get_comic_by_id,
    get_comic_by_hash,
    get_comics_in_library,
    search_comics,
)
from src.database.models import Library, Comic


class TestLibraryOperations:
    """Test library CRUD operations"""
    
    def test_create_library(self, test_db, test_data_dir):
        """Test creating a new library"""
        library_path = test_data_dir / "test_library"
        library_path.mkdir(exist_ok=True)
        
        with test_db.get_session() as session:
            library = create_library(
                session,
                name="Test Library",
                path=str(library_path)
            )
            
            assert library.id is not None
            assert library.name == "Test Library"
            assert library.path == str(library_path)
            assert library.created_at is not None
    
    def test_get_library_by_id(self, test_db, sample_library):
        """Test retrieving library by ID"""
        with test_db.get_session() as session:
            library = get_library_by_id(session, sample_library.id)
            
            assert library is not None
            assert library.id == sample_library.id
            assert library.name == sample_library.name
    
    def test_get_library_by_id_not_found(self, test_db):
        """Test retrieving non-existent library returns None"""
        with test_db.get_session() as session:
            library = get_library_by_id(session, 99999)
            
            assert library is None
    
    def test_get_library_by_path(self, test_db, sample_library):
        """Test retrieving library by path"""
        with test_db.get_session() as session:
            library = get_library_by_path(session, sample_library.path)
            
            assert library is not None
            assert library.path == sample_library.path
    
    def test_get_all_libraries(self, test_db, test_data_dir):
        """Test retrieving all libraries"""
        # Create multiple libraries
        with test_db.get_session() as session:
            for i in range(3):
                lib_path = test_data_dir / f"library_{i}"
                lib_path.mkdir(exist_ok=True)
                create_library(session, name=f"Library {i}", path=str(lib_path))
        
        with test_db.get_session() as session:
            libraries = get_all_libraries(session)
            
            assert len(libraries) >= 3
    
    def test_update_library(self, test_db, sample_library):
        """Test updating library attributes"""
        with test_db.get_session() as session:
            updated = update_library(
                session,
                sample_library.id,
                name="Updated Library Name"
            )
            
            assert updated is not None
            assert updated.name == "Updated Library Name"
    
    def test_delete_library(self, test_db, sample_library):
        """Test deleting a library"""
        with test_db.get_session() as session:
            result = delete_library(session, sample_library.id)
            
            assert result is True
            
            # Verify library is deleted
            library = get_library_by_id(session, sample_library.id)
            assert library is None


class TestComicOperations:
    """Test comic CRUD operations"""
    
    def test_create_comic(self, test_db, sample_library, sample_folder, test_data_dir):
        """Test creating a new comic record"""
        comic_path = test_data_dir / "library1" / "new_comic.cbz"
        comic_path.write_bytes(b"DUMMY_DATA")
        
        with test_db.get_session() as session:
            comic = create_comic(
                session,
                library_id=sample_library.id,
                folder_id=sample_folder.id,
                path=str(comic_path),
                filename="new_comic.cbz",
                hash="abc123def456",
                file_size=len(b"DUMMY_DATA"),
                format="cbz",
                num_pages=10
            )
            
            assert comic.id is not None
            assert comic.filename == "new_comic.cbz"
            assert comic.hash == "abc123def456"
            assert comic.num_pages == 10
    
    def test_get_comic_by_id(self, test_db, sample_comic):
        """Test retrieving comic by ID"""
        with test_db.get_session() as session:
            comic = get_comic_by_id(session, sample_comic.id)
            
            assert comic is not None
            assert comic.id == sample_comic.id
            assert comic.filename == sample_comic.filename
    
    def test_get_comic_by_id_not_found(self, test_db):
        """Test retrieving non-existent comic returns None"""
        with test_db.get_session() as session:
            comic = get_comic_by_id(session, 99999)
            
            assert comic is None
    
    def test_get_comic_by_hash(self, test_db, sample_comic):
        """Test retrieving comic by file hash"""
        with test_db.get_session() as session:
            comic = get_comic_by_hash(session, sample_comic.hash)
            
            assert comic is not None
            assert comic.hash == sample_comic.hash
    
    def test_get_comics_in_library(self, test_db, sample_library, multiple_comics):
        """Test retrieving all comics in a library"""
        with test_db.get_session() as session:
            comics = get_comics_in_library(session, sample_library.id)
            
            assert len(comics) == len(multiple_comics)
    
    def test_search_comics_by_title(self, test_db, sample_library, sample_comic):
        """Test comic search functionality"""
        with test_db.get_session() as session:
            results = search_comics(
                session,
                library_id=sample_library.id,
                query="Test Comic"
            )
            
            assert len(results) > 0
            assert any(comic.title == "Test Comic" for comic in results)
    
    def test_search_comics_by_series(self, test_db, sample_library, multiple_comics):
        """Test searching comics by series"""
        with test_db.get_session() as session:
            results = search_comics(
                session,
                library_id=sample_library.id,
                query="Test Series"
            )
            
            assert len(results) == len(multiple_comics)
    
    def test_search_comics_no_results(self, test_db, sample_library):
        """Test search with no matching results"""
        with test_db.get_session() as session:
            results = search_comics(
                session,
                library_id=sample_library.id,
                query="NonExistentComic"
            )
            
            assert len(results) == 0
    
    def test_comic_with_metadata(self, test_db, sample_library, sample_folder, test_data_dir):
        """Test creating comic with full metadata"""
        comic_path = test_data_dir / "library1" / "metadata_comic.cbz"
        comic_path.write_bytes(b"TEST")
        
        with test_db.get_session() as session:
            comic = create_comic(
                session,
                library_id=sample_library.id,
                folder_id=sample_folder.id,
                path=str(comic_path),
                filename="metadata_comic.cbz",
                hash="hash123",
                file_size=4,
                format="cbz",
                num_pages=20,
                title="Full Metadata Comic",
                series="Test Series",
                issue_number="5",
                year=2023,
                publisher="Test Publisher",
                writer="Test Writer",
                summary="A test comic with full metadata"
            )
            
            assert comic.title == "Full Metadata Comic"
            assert comic.series == "Test Series"
            assert comic.issue_number == "5"
            assert comic.year == 2023
            assert comic.publisher == "Test Publisher"
            assert comic.writer == "Test Writer"
            assert comic.summary == "A test comic with full metadata"


class TestComicUpdate:
    """Test updating comic records"""
    
    def test_update_comic_metadata(self, test_db, sample_comic):
        """Test updating comic metadata"""
        with test_db.get_session() as session:
            comic = get_comic_by_id(session, sample_comic.id)
            
            # Update metadata
            comic.title = "Updated Title"
            comic.year = 2025
            comic.summary = "Updated summary"
            session.commit()
            session.refresh(comic)
            
            assert comic.title == "Updated Title"
            assert comic.year == 2025
            assert comic.summary == "Updated summary"
    
    def test_update_comic_scanner_metadata(self, test_db, sample_comic):
        """Test updating scanner-related metadata"""
        with test_db.get_session() as session:
            comic = get_comic_by_id(session, sample_comic.id)
            
            # Update scanner metadata
            comic.scanner_source = "nhentai"
            comic.scanner_source_id = "12345"
            comic.scanner_source_url = "https://nhentai.net/g/12345"
            comic.scan_confidence = 0.95
            session.commit()
            session.refresh(comic)
            
            assert comic.scanner_source == "nhentai"
            assert comic.scanner_source_id == "12345"
            assert comic.scan_confidence == 0.95
