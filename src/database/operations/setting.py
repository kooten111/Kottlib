"""
Settings database operations

Functions for managing application settings stored in the database.
"""

import json
import time
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from ..models import Setting


def get_setting(session: Session, key: str) -> Optional[Any]:
    """
    Get a setting value from the database
    
    Args:
        session: Database session
        key: Setting key
        
    Returns:
        Setting value (converted to appropriate type) or None if not found
    """
    setting = session.query(Setting).filter(Setting.key == key).first()
    if not setting:
        return None
    
    # Convert based on type
    if setting.value is None:
        return None
    
    if setting.value_type == 'string':
        return setting.value
    elif setting.value_type == 'int':
        return int(setting.value)
    elif setting.value_type == 'float':
        return float(setting.value)
    elif setting.value_type == 'bool':
        return setting.value.lower() in ('true', '1', 'yes')
    elif setting.value_type == 'json':
        return json.loads(setting.value)
    else:
        return setting.value


def set_setting(
    session: Session,
    key: str,
    value: Any,
    description: Optional[str] = None
) -> Setting:
    """
    Set a setting value in the database
    
    Args:
        session: Database session
        key: Setting key
        value: Setting value
        description: Optional description of the setting
        
    Returns:
        Setting object
    """
    # Determine value type and convert to string
    if value is None:
        value_str = None
        value_type = 'string'
    elif isinstance(value, bool):
        value_str = str(value).lower()
        value_type = 'bool'
    elif isinstance(value, int):
        value_str = str(value)
        value_type = 'int'
    elif isinstance(value, float):
        value_str = str(value)
        value_type = 'float'
    elif isinstance(value, (dict, list)):
        value_str = json.dumps(value)
        value_type = 'json'
    else:
        value_str = str(value)
        value_type = 'string'
    
    # Get or create setting
    setting = session.query(Setting).filter(Setting.key == key).first()
    
    if setting:
        # Update existing
        setting.value = value_str
        setting.value_type = value_type
        if description is not None:
            setting.description = description
        setting.updated_at = int(time.time())
    else:
        # Create new
        setting = Setting(
            key=key,
            value=value_str,
            value_type=value_type,
            description=description,
            updated_at=int(time.time())
        )
        session.add(setting)
    
    return setting


def get_all_settings(session: Session) -> Dict[str, Any]:
    """
    Get all settings as a dictionary
    
    Args:
        session: Database session
        
    Returns:
        Dictionary of all settings
    """
    settings = session.query(Setting).all()
    result = {}
    
    for setting in settings:
        value = get_setting(session, setting.key)
        result[setting.key] = value
    
    return result


def delete_setting(session: Session, key: str) -> bool:
    """
    Delete a setting from the database
    
    Args:
        session: Database session
        key: Setting key
        
    Returns:
        True if deleted, False if not found
    """
    setting = session.query(Setting).filter(Setting.key == key).first()
    if setting:
        session.delete(setting)
        return True
    return False


def set_multiple_settings(
    session: Session,
    settings: Dict[str, Any]
) -> None:
    """
    Set multiple settings at once
    
    Args:
        session: Database session
        settings: Dictionary of key-value pairs
    """
    for key, value in settings.items():
        set_setting(session, key, value)


# Default settings initialization
DEFAULT_SETTINGS = {
    # Storage settings
    'storage.covers_dir': None,
    'storage.cache_dir': None,
    
    # Feature flags
    'features.legacy_api': True,
    'features.modern_api': True,
    'features.reading_progress': True,
    'features.series_detection': True,
    'features.collections': True,
    'features.auto_thumbnails': True,
    'features.ignore_series_metadata': True,
    
    # Database settings
    'database.echo': False,
}


def initialize_default_settings(session: Session) -> None:
    """
    Initialize default settings in the database if they don't exist
    
    Args:
        session: Database session
    """
    for key, value in DEFAULT_SETTINGS.items():
        existing = session.query(Setting).filter(Setting.key == key).first()
        if not existing:
            set_setting(session, key, value)
