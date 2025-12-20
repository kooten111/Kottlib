"""
Config Sync Service

Manages synchronization between config.yml and the database.
The database is the source of truth for runtime operations.
"""

import logging
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from ..config import (
    Config,
    LibraryDefinition,
    get_config_path,
    save_config,
    load_config,
)
from ..database import (
    get_all_libraries,
    create_library,
    update_library,
    delete_library,
    get_library_by_id,
)
from ..database.models import Library

logger = logging.getLogger(__name__)


def ensure_config_file(session: Session, config: Optional[Config] = None) -> None:
    """
    Ensure config.yml exists. If it doesn't, create it from database state.
    
    Args:
        session: Database session
        config: Optional existing config (will be loaded if not provided)
    """
    config_path = get_config_path()
    
    if config_path.exists():
        logger.debug(f"Config file already exists at {config_path}")
        return
    
    logger.info(f"Config file not found at {config_path}, creating from database state")
    
    # Load default config or use provided one
    if config is None:
        from ..config import create_default_config
        config = create_default_config()
    
    # Export current database state to config
    sync_db_to_config(session, config)
    logger.info(f"Created config file at {config_path} from database state")


def sync_db_to_config(session: Session, config: Optional[Config] = None) -> None:
    """
    Export database library state to config.yml.
    This is called after any database changes (create/update/delete library).
    
    Args:
        session: Database session
        config: Optional config object (will be loaded if not provided)
    """
    # Load config if not provided
    if config is None:
        config = load_config()
    
    # Get all libraries from database
    db_libraries = get_all_libraries(session)
    
    # Convert to LibraryDefinition objects
    config.libraries = []
    for lib in db_libraries:
        settings = lib.settings or {}
        
        lib_def = LibraryDefinition(
            name=lib.name,
            path=lib.path,
            auto_scan=settings.get('auto_scan', True),
            scan_on_startup=settings.get('scan_on_startup', False),
            settings={
                k: v for k, v in settings.items()
                if k not in ['auto_scan', 'scan_on_startup']
            }
        )
        config.libraries.append(lib_def)
    
    # Save to file
    save_config(config)
    logger.info(f"Synced {len(config.libraries)} libraries from database to config.yml")


def sync_config_to_db(session: Session, config: Optional[Config] = None) -> dict:
    """
    Import libraries from config.yml to database and detect/apply diffs.
    This is called on application startup.
    
    Behavior:
    - New libraries in config.yml: Create them in database
    - Changed paths/settings: Update library in database
    - Libraries in DB but not in config: Log warning (don't auto-delete)
    
    Args:
        session: Database session
        config: Optional config object (will be loaded if not provided)
        
    Returns:
        Dict with sync statistics: {
            'created': int,
            'updated': int,
            'warnings': int,
            'changes': list[str]
        }
    """
    # Load config if not provided
    if config is None:
        config = load_config()
    
    # Get libraries from config and database
    config_libs = {lib.name: lib for lib in config.libraries}
    db_libs_list = get_all_libraries(session)
    db_libs = {lib.name: lib for lib in db_libs_list}
    
    stats = {
        'created': 0,
        'updated': 0,
        'warnings': 0,
        'changes': []
    }
    
    # Process libraries from config
    for name, lib_def in config_libs.items():
        if name not in db_libs:
            # New library in config - create in database
            settings = dict(lib_def.settings) if lib_def.settings else {}
            settings['auto_scan'] = lib_def.auto_scan
            settings['scan_on_startup'] = lib_def.scan_on_startup
            
            create_library(
                session,
                name=lib_def.name,
                path=lib_def.path,
                settings=settings
            )
            session.commit()
            
            stats['created'] += 1
            stats['changes'].append(f"Created library from config: {name}")
            logger.info(f"Created library from config: {name}")
        else:
            # Library exists - check for updates
            db_lib = db_libs[name]
            needs_update = False
            update_fields = {}
            
            # Check path
            if lib_def.path != db_lib.path:
                needs_update = True
                update_fields['path'] = lib_def.path
                stats['changes'].append(f"Updated library '{name}' path: {db_lib.path} -> {lib_def.path}")
            
            # Check settings
            config_settings = dict(lib_def.settings) if lib_def.settings else {}
            config_settings['auto_scan'] = lib_def.auto_scan
            config_settings['scan_on_startup'] = lib_def.scan_on_startup
            
            db_settings = db_lib.settings or {}
            
            if config_settings != db_settings:
                needs_update = True
                update_fields['settings'] = config_settings
                stats['changes'].append(f"Updated library '{name}' settings")
            
            # Apply updates if needed
            if needs_update:
                update_library(
                    session,
                    db_lib.id,
                    **update_fields
                )
                session.commit()
                
                stats['updated'] += 1
                logger.info(f"Updated library from config: {name}")
    
    # Check for libraries in DB but not in config (warn only, don't delete)
    for name in db_libs:
        if name not in config_libs:
            stats['warnings'] += 1
            stats['changes'].append(f"Warning: Library '{name}' exists in database but not in config.yml")
            logger.warning(f"Library '{name}' exists in database but not in config.yml")
    
    return stats


def get_sync_summary(stats: dict) -> str:
    """
    Generate a human-readable summary of sync changes.
    
    Args:
        stats: Stats dictionary from sync_config_to_db
        
    Returns:
        Summary string
    """
    if not stats['changes']:
        return "No changes detected between config.yml and database"
    
    summary_parts = []
    
    if stats['created'] > 0:
        summary_parts.append(f"{stats['created']} libraries created")
    
    if stats['updated'] > 0:
        summary_parts.append(f"{stats['updated']} libraries updated")
    
    if stats['warnings'] > 0:
        summary_parts.append(f"{stats['warnings']} warnings")
    
    summary = f"Config sync: {', '.join(summary_parts)}"
    
    # Add change details
    if logger.isEnabledFor(logging.INFO):
        for change in stats['changes']:
            summary += f"\n  - {change}"
    
    return summary
