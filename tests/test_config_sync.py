"""
Tests for config sync service
"""
import pytest
from pathlib import Path
import yaml

from src.config import load_config
from src.services.config_sync import (
    ensure_config_file,
    migrate_legacy_config_to_db,
    get_sync_summary
)
from src.database import get_all_libraries


def test_ensure_config_file_creates_minimal_config(test_db, test_data_dir, monkeypatch):
    """Test that ensure_config_file creates minimal config.yml"""
    temp_config_path = test_data_dir / "test_config.yml"
    
    # Mock get_config_path
    import src.services.config_sync as config_sync_module
    import src.config as config_module
    
    monkeypatch.setattr(config_sync_module, 'get_config_path', lambda: temp_config_path)
    monkeypatch.setattr(config_module, 'get_config_path', lambda: temp_config_path)
    
    with test_db.get_session() as session:
        assert not temp_config_path.exists()
        
        ensure_config_file(session)
        
        assert temp_config_path.exists()
        
        # Verify minimal bootstrap config
        config = load_config(temp_config_path)
        assert config.server.host == "0.0.0.0"
        assert config.server.port == 8081
        assert config.database.path is None


def test_migrate_legacy_config_no_libraries(test_db, test_data_dir, monkeypatch):
    """Test migrating config with no libraries section"""
    temp_config_path = test_data_dir / "minimal_config.yml"
    minimal_config = {
        'server': {'host': '0.0.0.0', 'port': 8081, 'reload': False, 'log_level': 'info', 'cors_origins': ['*']},
        'database': {'path': None}
    }
    
    with open(temp_config_path, 'w') as f:
        yaml.dump(minimal_config, f)
    
    import src.services.config_sync as config_sync_module
    monkeypatch.setattr(config_sync_module, 'get_config_path', lambda: temp_config_path)
    
    with test_db.get_session() as session:
        stats = migrate_legacy_config_to_db(session)
        
        assert stats['created'] == 0
        assert stats['updated'] == 0
        assert stats['warnings'] == 0


def test_migrate_legacy_config_with_libraries(test_db, test_data_dir, monkeypatch):
    """Test migrating legacy config with libraries"""
    temp_config_path = test_data_dir / "legacy_config.yml"
    legacy_config = {
        'server': {'host': '0.0.0.0', 'port': 8081, 'reload': False, 'log_level': 'info', 'cors_origins': ['*']},
        'database': {'path': None},
        'libraries': [
            {
                'name': 'Comics',
                'path': '/path/to/comics',
                'auto_scan': True,
                'scan_on_startup': False,
                'settings': {'sort_mode': 'folders_first'}
            }
        ]
    }
    
    with open(temp_config_path, 'w') as f:
        yaml.dump(legacy_config, f)
    
    import src.services.config_sync as config_sync_module
    monkeypatch.setattr(config_sync_module, 'get_config_path', lambda: temp_config_path)
    
    with test_db.get_session() as session:
        stats = migrate_legacy_config_to_db(session)
        
        assert stats['created'] == 1
        assert stats['updated'] == 0
        
        db_libs = get_all_libraries(session)
        assert len(db_libs) == 1
        assert db_libs[0].name == "Comics"
        assert db_libs[0].path == "/path/to/comics"


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
        'warnings': 0,
        'changes': [
            "Migrated library from config: Comics",
            "Migrated library from config: Manga",
            "Updated library from config: Books"
        ]
    }
    
    summary = get_sync_summary(stats)
    assert "2 libraries migrated" in summary
    assert "1 library updated" in summary
