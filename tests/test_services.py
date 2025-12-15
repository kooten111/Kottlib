"""
Tests for service layer

Basic tests to ensure service functions work correctly.
"""
import pytest
from src.services import (
    create_library_with_stats,
    get_library_with_stats,
    list_libraries_with_stats,
)


def test_create_library_with_stats(test_db):
    """Test creating a library with statistics"""
    with test_db.get_session() as session:
        result = create_library_with_stats(
            session,
            name="Test Library",
            path="/test/path"
        )
        
        assert result is not None
        assert result["name"] == "Test Library"
        assert result["path"] == "/test/path"
        assert result["comic_count"] == 0
        assert result["folder_count"] == 0


def test_list_libraries_with_stats(test_db):
    """Test listing all libraries with statistics"""
    with test_db.get_session() as session:
        # Create a library first
        create_library_with_stats(
            session,
            name="Test Library",
            path="/test/path"
        )
        
        # List all libraries
        results = list_libraries_with_stats(session)
        
        assert len(results) >= 1
        assert any(lib["name"] == "Test Library" for lib in results)

