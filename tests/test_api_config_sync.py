"""
Integration test for config sync with API endpoints
"""
import pytest
import tempfile
from pathlib import Path

from src.config import Config, LibraryDefinition
from src.database import get_all_libraries


def test_create_library_syncs_to_config(test_client, test_db, monkeypatch):
    """Test that creating a library via API syncs to config"""
    # Create temporary config path
    temp_dir = Path(tempfile.mkdtemp(prefix="kottlib_api_test_"))
    config_path = temp_dir / "config.yml"
    
    # Mock get_config_path
    import src.services.config_sync as config_sync_module
    import src.config as config_module
    
    def mock_get_config_path():
        return config_path
    
    monkeypatch.setattr(config_sync_module, 'get_config_path', mock_get_config_path)
    monkeypatch.setattr(config_module, 'get_config_path', mock_get_config_path)
    
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
    
    # Verify config was updated
    from src.config import load_config
    config = load_config(config_path)
    assert len(config.libraries) == 1
    assert config.libraries[0].name == "Test Library"
    assert config.libraries[0].path == "/path/to/test"
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_update_library_syncs_to_config(test_client, test_db, sample_library, monkeypatch):
    """Test that updating a library via API syncs to config"""
    # Create temporary config path
    temp_dir = Path(tempfile.mkdtemp(prefix="kottlib_api_test_"))
    config_path = temp_dir / "config.yml"
    
    # Mock get_config_path
    import src.services.config_sync as config_sync_module
    import src.config as config_module
    
    def mock_get_config_path():
        return config_path
    
    monkeypatch.setattr(config_sync_module, 'get_config_path', mock_get_config_path)
    monkeypatch.setattr(config_module, 'get_config_path', mock_get_config_path)
    
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
    
    # Verify config was updated
    from src.config import load_config
    config = load_config(config_path)
    assert len(config.libraries) == 1
    assert config.libraries[0].name == "Updated Library"
    assert config.libraries[0].path == "/new/path"
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_delete_library_syncs_to_config(test_client, test_db, sample_library, monkeypatch):
    """Test that deleting a library via API syncs to config"""
    # Create temporary config path
    temp_dir = Path(tempfile.mkdtemp(prefix="kottlib_api_test_"))
    config_path = temp_dir / "config.yml"
    
    # Mock get_config_path
    import src.services.config_sync as config_sync_module
    import src.config as config_module
    
    def mock_get_config_path():
        return config_path
    
    monkeypatch.setattr(config_sync_module, 'get_config_path', mock_get_config_path)
    monkeypatch.setattr(config_module, 'get_config_path', mock_get_config_path)
    
    # First sync current state to config
    with test_db.get_session() as session:
        from src.services.config_sync import sync_db_to_config
        sync_db_to_config(session)
    
    # Verify library exists in config
    from src.config import load_config
    config = load_config(config_path)
    assert len(config.libraries) == 1
    
    # Delete library via API
    response = test_client.delete(f"/api/v1/libraries/{sample_library.id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    # Verify config was updated (library removed)
    config = load_config(config_path)
    assert len(config.libraries) == 0
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
