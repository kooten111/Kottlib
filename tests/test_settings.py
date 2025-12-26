"""
Tests for settings database operations
"""
import pytest
import time

from src.database.operations.setting import (
    get_setting,
    set_setting,
    get_all_settings,
    delete_setting,
    set_multiple_settings,
    initialize_default_settings,
)
from src.database import Setting


def test_set_and_get_string_setting(test_db):
    """Test setting and getting a string value"""
    with test_db.get_session() as session:
        # Set a string setting
        setting = set_setting(session, "test.string", "hello world")
        session.commit()
        
        # Get the setting
        value = get_setting(session, "test.string")
        assert value == "hello world"
        
        # Check the setting object
        assert setting.key == "test.string"
        assert setting.value == "hello world"
        assert setting.value_type == "string"


def test_set_and_get_int_setting(test_db):
    """Test setting and getting an integer value"""
    with test_db.get_session() as session:
        # Set an int setting
        set_setting(session, "test.int", 42)
        session.commit()
        
        # Get the setting
        value = get_setting(session, "test.int")
        assert value == 42
        assert isinstance(value, int)


def test_set_and_get_float_setting(test_db):
    """Test setting and getting a float value"""
    with test_db.get_session() as session:
        # Set a float setting
        set_setting(session, "test.float", 3.14)
        session.commit()
        
        # Get the setting
        value = get_setting(session, "test.float")
        assert value == 3.14
        assert isinstance(value, float)


def test_set_and_get_bool_setting(test_db):
    """Test setting and getting a boolean value"""
    with test_db.get_session() as session:
        # Set a bool setting (True)
        set_setting(session, "test.bool.true", True)
        session.commit()
        
        # Set a bool setting (False)
        set_setting(session, "test.bool.false", False)
        session.commit()
        
        # Get the settings
        value_true = get_setting(session, "test.bool.true")
        value_false = get_setting(session, "test.bool.false")
        
        assert value_true is True
        assert value_false is False
        assert isinstance(value_true, bool)
        assert isinstance(value_false, bool)


def test_set_and_get_json_setting(test_db):
    """Test setting and getting a JSON value"""
    with test_db.get_session() as session:
        # Set a dict
        data = {"key": "value", "number": 123, "nested": {"data": "here"}}
        set_setting(session, "test.json", data)
        session.commit()
        
        # Get the setting
        value = get_setting(session, "test.json")
        assert value == data
        assert isinstance(value, dict)


def test_set_and_get_null_setting(test_db):
    """Test setting and getting a null value"""
    with test_db.get_session() as session:
        # Set a null setting
        set_setting(session, "test.null", None)
        session.commit()
        
        # Get the setting
        value = get_setting(session, "test.null")
        assert value is None


def test_update_existing_setting(test_db):
    """Test updating an existing setting"""
    with test_db.get_session() as session:
        # Set initial value
        set_setting(session, "test.update", "initial")
        session.commit()
        
        # Update the value
        time.sleep(0.1)  # Ensure timestamp changes
        set_setting(session, "test.update", "updated")
        session.commit()
        
        # Get the updated value
        value = get_setting(session, "test.update")
        assert value == "updated"


def test_set_setting_with_description(test_db):
    """Test setting a value with description"""
    with test_db.get_session() as session:
        # Set with description
        setting = set_setting(
            session,
            "test.described",
            "value",
            description="This is a test setting"
        )
        session.commit()
        
        # Check description
        assert setting.description == "This is a test setting"


def test_get_nonexistent_setting(test_db):
    """Test getting a setting that doesn't exist"""
    with test_db.get_session() as session:
        value = get_setting(session, "nonexistent.key")
        assert value is None


def test_get_all_settings(test_db):
    """Test getting all settings"""
    with test_db.get_session() as session:
        # Set multiple settings
        set_setting(session, "test.one", "value1")
        set_setting(session, "test.two", 42)
        set_setting(session, "test.three", True)
        session.commit()
        
        # Get all settings
        all_settings = get_all_settings(session)
        
        assert "test.one" in all_settings
        assert all_settings["test.one"] == "value1"
        assert "test.two" in all_settings
        assert all_settings["test.two"] == 42
        assert "test.three" in all_settings
        assert all_settings["test.three"] is True


def test_delete_setting(test_db):
    """Test deleting a setting"""
    with test_db.get_session() as session:
        # Set a setting
        set_setting(session, "test.delete", "value")
        session.commit()
        
        # Verify it exists
        assert get_setting(session, "test.delete") == "value"
        
        # Delete it
        result = delete_setting(session, "test.delete")
        session.commit()
        
        assert result is True
        
        # Verify it's gone
        assert get_setting(session, "test.delete") is None


def test_delete_nonexistent_setting(test_db):
    """Test deleting a setting that doesn't exist"""
    with test_db.get_session() as session:
        result = delete_setting(session, "nonexistent.key")
        assert result is False


def test_set_multiple_settings(test_db):
    """Test setting multiple settings at once"""
    with test_db.get_session() as session:
        settings = {
            "multi.one": "value1",
            "multi.two": 42,
            "multi.three": True,
            "multi.four": {"nested": "data"}
        }
        
        set_multiple_settings(session, settings)
        session.commit()
        
        # Verify all settings were set
        assert get_setting(session, "multi.one") == "value1"
        assert get_setting(session, "multi.two") == 42
        assert get_setting(session, "multi.three") is True
        assert get_setting(session, "multi.four") == {"nested": "data"}


def test_initialize_default_settings(test_db):
    """Test initializing default settings"""
    with test_db.get_session() as session:
        # Initialize defaults
        initialize_default_settings(session)
        session.commit()
        
        # Check some default settings exist
        assert get_setting(session, "features.legacy_api") is True
        assert get_setting(session, "features.modern_api") is True
        assert get_setting(session, "features.reading_progress") is True
        assert get_setting(session, "database.echo") is False


def test_initialize_default_settings_does_not_overwrite(test_db):
    """Test that initializing defaults doesn't overwrite existing settings"""
    with test_db.get_session() as session:
        # Set a custom value
        set_setting(session, "features.legacy_api", False)
        session.commit()
        
        # Initialize defaults
        initialize_default_settings(session)
        session.commit()
        
        # Custom value should be preserved
        assert get_setting(session, "features.legacy_api") is False


def test_setting_updated_at_timestamp(test_db):
    """Test that updated_at timestamp is set correctly"""
    with test_db.get_session() as session:
        before = int(time.time())
        setting = set_setting(session, "test.timestamp", "value")
        session.commit()
        after = int(time.time())
        
        assert before <= setting.updated_at <= after
        
        # Update and check timestamp changes
        time.sleep(1.0)  # Wait 1 second to ensure timestamp changes
        updated_setting = set_setting(session, "test.timestamp", "new value")
        session.commit()
        
        assert updated_setting.updated_at >= setting.updated_at
