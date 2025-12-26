"""
Integration test for library API endpoints

NOTE: Libraries are now managed entirely in the database.
Config.yml is only for bootstrap settings (server + database path).
These tests verify that library operations work via the API.
"""
import pytest

from src.database import get_all_libraries


def test_create_library_via_api(test_client, test_db):
    """Test that creating a library via API works"""
    # Create library via API
    response = test_client.post(
        "/api/v1/libraries/",
        json={
            "name": "Test Library",
            "path": "/path/to/test",
            "settings": {"auto_scan": True}
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Library"
    
    # Verify library was created in database
    with test_db.get_session() as session:
        libraries = get_all_libraries(session)
        assert len(libraries) == 1
        assert libraries[0].name == "Test Library"
        assert libraries[0].path == "/path/to/test"


def test_update_library_via_api(test_client, test_db, sample_library):
    """Test that updating a library via API works"""
    # Update library via API
    response = test_client.put(
        f"/api/v1/libraries/{sample_library.id}",
        json={
            "name": "Updated Library",
            "path": "/new/path",
            "settings": {"auto_scan": False}
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Library"
    
    # Verify library was updated in database
    with test_db.get_session() as session:
        libraries = get_all_libraries(session)
        assert len(libraries) == 1
        assert libraries[0].name == "Updated Library"
        assert libraries[0].path == "/new/path"


def test_delete_library_via_api(test_client, test_db, sample_library):
    """Test that deleting a library via API works"""
    # Verify library exists in database
    with test_db.get_session() as session:
        libraries = get_all_libraries(session)
        assert len(libraries) == 1
    
    # Delete library via API
    response = test_client.delete(f"/api/v1/libraries/{sample_library.id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    # Verify library was deleted from database
    with test_db.get_session() as session:
        libraries = get_all_libraries(session)
        assert len(libraries) == 0
