"""
Tests for config sync service
"""
import tempfile
import pytest
from pathlib import Path

from src.config import Config, LibraryDefinition, load_config, save_config
from src.services.config_sync import (
    ensure_config_file,
    sync_db_to_config,
    sync_config_to_db,
    get_sync_summary
)
from src.database import create_library, get_all_libraries, update_library, delete_library


def test_sync_db_to_config_empty_db(test_db, test_data_dir):
    """Test syncing empty database to config"""
    # Create a config with no libraries
    config = Config()
    
    with test_db.get_session() as session:
        # Sync empty DB to config
        sync_db_to_config(session, config)
    
    # Should have no libraries
    assert len(config.libraries) == 0


def test_sync_db_to_config_with_libraries(test_db, test_data_dir):
    """Test syncing database with libraries to config"""
    config = Config()
    
    with test_db.get_session() as session:
        # Create some libraries in DB
        lib1 = create_library(
            session,
            name="Comics",
            path="/path/to/comics",
            settings={
                "auto_scan": True,
                "scan_on_startup": False,
                "sort_mode": "folders_first",
                "default_reading_direction": "ltr"
            }
        )
        
        lib2 = create_library(
            session,
            name="Manga",
            path="/path/to/manga",
            settings={
                "auto_scan": False,
                "scan_on_startup": True,
                "default_reading_direction": "rtl"
            }
        )
        
        session.commit()
        
        # Sync to config
        sync_db_to_config(session, config)
    
    # Check config has the libraries
    assert len(config.libraries) == 2
    
    # Check first library
    comics_lib = next((lib for lib in config.libraries if lib.name == "Comics"), None)
    assert comics_lib is not None
    assert comics_lib.path == "/path/to/comics"
    assert comics_lib.auto_scan == True
    assert comics_lib.scan_on_startup == False
    assert comics_lib.settings.get("sort_mode") == "folders_first"
    
    # Check second library
    manga_lib = next((lib for lib in config.libraries if lib.name == "Manga"), None)
    assert manga_lib is not None
    assert manga_lib.path == "/path/to/manga"
    assert manga_lib.auto_scan == False
    assert manga_lib.scan_on_startup == True


def test_sync_config_to_db_new_libraries(test_db, test_data_dir):
    """Test syncing config with new libraries to empty database"""
    # Create config with libraries
    config = Config()
    config.libraries = [
        LibraryDefinition(
            name="Comics",
            path="/path/to/comics",
            auto_scan=True,
            scan_on_startup=False,
            settings={"sort_mode": "folders_first"}
        ),
        LibraryDefinition(
            name="Manga",
            path="/path/to/manga",
            auto_scan=False,
            scan_on_startup=True,
            settings={"default_reading_direction": "rtl"}
        )
    ]
    
    with test_db.get_session() as session:
        # Sync to DB
        stats = sync_config_to_db(session, config)
        
        # Check stats
        assert stats['created'] == 2
        assert stats['updated'] == 0
        assert stats['warnings'] == 0
        
        # Check libraries were created in DB
        db_libs = get_all_libraries(session)
        assert len(db_libs) == 2
        
        # Check first library
        comics_lib = next((lib for lib in db_libs if lib.name == "Comics"), None)
        assert comics_lib is not None
        assert comics_lib.path == "/path/to/comics"
        assert comics_lib.settings.get("auto_scan") == True
        assert comics_lib.settings.get("scan_on_startup") == False
        
        # Check second library
        manga_lib = next((lib for lib in db_libs if lib.name == "Manga"), None)
        assert manga_lib is not None
        assert manga_lib.path == "/path/to/manga"
        assert manga_lib.settings.get("auto_scan") == False
        assert manga_lib.settings.get("scan_on_startup") == True


def test_sync_config_to_db_update_path(test_db, test_data_dir):
    """Test updating library path from config"""
    with test_db.get_session() as session:
        # Create library in DB
        lib = create_library(
            session,
            name="Comics",
            path="/old/path/to/comics",
            settings={"auto_scan": True}
        )
        session.commit()
        
        # Create config with updated path
        config = Config()
        config.libraries = [
            LibraryDefinition(
                name="Comics",
                path="/new/path/to/comics",
                auto_scan=True,
                scan_on_startup=False,
                settings={}
            )
        ]
        
        # Sync to DB
        stats = sync_config_to_db(session, config)
        
        # Check stats
        assert stats['created'] == 0
        assert stats['updated'] == 1
        assert stats['warnings'] == 0
        assert any("path" in change.lower() for change in stats['changes'])
        
        # Check library was updated
        db_libs = get_all_libraries(session)
        assert len(db_libs) == 1
        assert db_libs[0].path == "/new/path/to/comics"


def test_sync_config_to_db_update_settings(test_db, test_data_dir):
    """Test updating library settings from config"""
    with test_db.get_session() as session:
        # Create library in DB
        lib = create_library(
            session,
            name="Comics",
            path="/path/to/comics",
            settings={"auto_scan": True, "old_setting": "value"}
        )
        session.commit()
        
        # Create config with updated settings
        config = Config()
        config.libraries = [
            LibraryDefinition(
                name="Comics",
                path="/path/to/comics",
                auto_scan=False,
                scan_on_startup=True,
                settings={"new_setting": "new_value"}
            )
        ]
        
        # Sync to DB
        stats = sync_config_to_db(session, config)
        
        # Check stats
        assert stats['created'] == 0
        assert stats['updated'] == 1
        assert stats['warnings'] == 0
        
        # Check library settings were updated
        db_libs = get_all_libraries(session)
        assert len(db_libs) == 1
        assert db_libs[0].settings.get("auto_scan") == False
        assert db_libs[0].settings.get("scan_on_startup") == True
        assert db_libs[0].settings.get("new_setting") == "new_value"


def test_sync_config_to_db_library_in_db_not_in_config(test_db, test_data_dir):
    """Test warning when library exists in DB but not in config"""
    with test_db.get_session() as session:
        # Create library in DB
        lib = create_library(
            session,
            name="Comics",
            path="/path/to/comics",
            settings={"auto_scan": True}
        )
        session.commit()
        
        # Create empty config
        config = Config()
        config.libraries = []
        
        # Sync to DB
        stats = sync_config_to_db(session, config)
        
        # Check stats - should have warning
        assert stats['created'] == 0
        assert stats['updated'] == 0
        assert stats['warnings'] == 1
        assert any("Comics" in change for change in stats['changes'])
        
        # Library should still exist in DB (not deleted)
        db_libs = get_all_libraries(session)
        assert len(db_libs) == 1


def test_sync_config_to_db_no_changes(test_db, test_data_dir):
    """Test sync when config and DB are already in sync"""
    with test_db.get_session() as session:
        # Create library in DB
        lib = create_library(
            session,
            name="Comics",
            path="/path/to/comics",
            settings={"auto_scan": True, "scan_on_startup": False}
        )
        session.commit()
        
        # Create matching config
        config = Config()
        config.libraries = [
            LibraryDefinition(
                name="Comics",
                path="/path/to/comics",
                auto_scan=True,
                scan_on_startup=False,
                settings={}
            )
        ]
        
        # Sync to DB
        stats = sync_config_to_db(session, config)
        
        # Check stats - no changes
        assert stats['created'] == 0
        assert stats['updated'] == 0
        assert stats['warnings'] == 0
        assert len(stats['changes']) == 0


def test_ensure_config_file_creates_from_db(test_db, test_data_dir, monkeypatch):
    """Test that ensure_config_file creates config.yml from database state"""
    # Use a temporary config path
    temp_config_path = test_data_dir / "test_config.yml"
    
    # Mock get_config_path to return our temp path
    import src.services.config_sync as config_sync_module
    original_get_config_path = config_sync_module.get_config_path
    
    def mock_get_config_path():
        return temp_config_path
    
    monkeypatch.setattr(config_sync_module, 'get_config_path', mock_get_config_path)
    
    # Also patch it in the config module
    import src.config as config_module
    monkeypatch.setattr(config_module, 'get_config_path', mock_get_config_path)
    
    with test_db.get_session() as session:
        # Create library in DB
        lib = create_library(
            session,
            name="Comics",
            path="/path/to/comics",
            settings={"auto_scan": True}
        )
        session.commit()
        
        # Ensure config doesn't exist yet
        assert not temp_config_path.exists()
        
        # Call ensure_config_file
        ensure_config_file(session)
        
        # Config should now exist
        assert temp_config_path.exists()
        
        # Load and verify config
        from src.config import load_config
        config = load_config(temp_config_path)
        assert len(config.libraries) == 1
        assert config.libraries[0].name == "Comics"


def test_get_sync_summary_no_changes():
    """Test sync summary with no changes"""
    stats = {
        'created': 0,
        'updated': 0,
        'warnings': 0,
        'changes': []
    }
    
    summary = get_sync_summary(stats)
    assert "No changes" in summary


def test_get_sync_summary_with_changes():
    """Test sync summary with changes"""
    stats = {
        'created': 2,
        'updated': 1,
        'warnings': 1,
        'changes': [
            "Created library from config: Comics",
            "Created library from config: Manga",
            "Updated library from config: Books",
            "Warning: Library 'Old' exists in database but not in config.yml"
        ]
    }
    
    summary = get_sync_summary(stats)
    assert "2 libraries created" in summary
    assert "1 libraries updated" in summary
    assert "1 warnings" in summary


def test_roundtrip_db_to_config_to_db(test_db, test_data_dir, monkeypatch):
    """Test that syncing DB -> config -> DB preserves library data"""
    # Use a temporary config path
    temp_config_path = test_data_dir / "roundtrip_config.yml"
    
    # Mock get_config_path
    import src.services.config_sync as config_sync_module
    import src.config as config_module
    
    def mock_get_config_path():
        return temp_config_path
    
    monkeypatch.setattr(config_sync_module, 'get_config_path', mock_get_config_path)
    monkeypatch.setattr(config_module, 'get_config_path', mock_get_config_path)
    
    with test_db.get_session() as session:
        # Create library in DB with complex settings
        lib = create_library(
            session,
            name="Comics",
            path="/path/to/comics",
            settings={
                "auto_scan": True,
                "scan_on_startup": False,
                "sort_mode": "folders_first",
                "default_reading_direction": "ltr",
                "custom_setting": "value"
            }
        )
        session.commit()
        original_id = lib.id
        
        # Sync DB -> config
        sync_db_to_config(session)
        
        # Delete library from DB
        delete_library(session, original_id)
        session.commit()
        
        # Verify DB is empty
        assert len(get_all_libraries(session)) == 0
        
        # Sync config -> DB
        stats = sync_config_to_db(session)
        
        # Verify library was recreated
        assert stats['created'] == 1
        db_libs = get_all_libraries(session)
        assert len(db_libs) == 1
        
        restored_lib = db_libs[0]
        assert restored_lib.name == "Comics"
        assert restored_lib.path == "/path/to/comics"
        assert restored_lib.settings.get("auto_scan") == True
        assert restored_lib.settings.get("scan_on_startup") == False
        assert restored_lib.settings.get("sort_mode") == "folders_first"
        assert restored_lib.settings.get("custom_setting") == "value"
