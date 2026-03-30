"""
Config Sync Service

Manages minimal config.yml bootstrap settings.
Libraries and other settings are managed in the database only.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from ..config import (
    Config,
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


# ============================================================================
# Legacy Migration Support
# ============================================================================

@dataclass
class LibraryDefinition:
    """
    Legacy library definition for migrating from config.yml to database.
    Only used during migration - new libraries should be created via database operations.
    """
    name: str
    path: str
    auto_scan: bool = True
    scan_on_startup: bool = False
    settings: Dict[str, Any] = field(default_factory=dict)


def ensure_config_file(session: Session, config: Optional[Config] = None) -> None:
    """
    Ensure minimal config.yml exists. If it doesn't, create it with bootstrap defaults.
    
    Args:
        session: Database session (unused, kept for compatibility)
        config: Optional existing config (will be created if not provided)
    """
    config_path = get_config_path()
    
    if config_path.exists():
        logger.debug(f"Config file already exists at {config_path}")
        return
    
    logger.info(f"Config file not found at {config_path}, creating minimal bootstrap config")
    
    # Load default config or use provided one
    if config is None:
        from ..config import create_default_config
        config = create_default_config()
    
    # Save minimal config (server + database only)
    save_config(config)
    logger.info(f"Created minimal config file at {config_path}")


def migrate_legacy_config_to_db(session: Session, config: Optional[Config] = None) -> dict:
    """
    ONE-TIME migration: Import libraries from old config.yml to database.
    This supports migration from the old config system.
    
    After migration, libraries should be managed via WebUI/API and stored in database only.
    
    Args:
        session: Database session
        config: Optional config object (will be loaded if not provided)
        
    Returns:
        Dict with migration statistics: {
            'created': int,
            'updated': int,
            'warnings': int,
            'changes': list[str]
        }
    """
    # Load config if not provided
    if config is None:
        config_path = get_config_path()
        if not config_path.exists():
            return {
                'created': 0,
                'updated': 0,
                'warnings': 0,
                'changes': []
            }
        
        # Load legacy config (might have libraries section)
        import yaml
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f) or {}
        
        # Only process if there are libraries in the config
        if 'libraries' not in data:
            return {
                'created': 0,
                'updated': 0,
                'warnings': 0,
                'changes': []
            }
        
        # Parse libraries from legacy config
        config_libraries = [LibraryDefinition(**lib) for lib in data['libraries']]
    else:
        # This shouldn't happen in the new system but keep for compatibility
        config_libraries = getattr(config, 'libraries', [])
    
    if not config_libraries:
        return {
            'created': 0,
            'updated': 0,
            'warnings': 0,
            'changes': []
        }
    
    # Get existing libraries from database
    db_libs_list = get_all_libraries(session)
    db_libs = {lib.name: lib for lib in db_libs_list}
    
    stats = {
        'created': 0,
        'updated': 0,
        'warnings': 0,
        'changes': []
    }
    
    # Process libraries from config
    for lib_def in config_libraries:
        name = lib_def.name
        
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
            stats['changes'].append(f"Migrated library from config: {name}")
            logger.info(f"Migrated library from config to database: {name}")
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
    
    return stats


def get_sync_summary(stats: dict) -> str:
    """
    Generate a human-readable summary of migration/sync changes.
    
    Args:
        stats: Stats dictionary from migrate_legacy_config_to_db
        
    Returns:
        Summary string
    """
    if not stats['changes']:
        return "No changes detected"
    
    summary_parts = []
    
    if stats['created'] > 0:
        plural = "libraries" if stats['created'] > 1 else "library"
        summary_parts.append(f"{stats['created']} {plural} migrated")
    
    if stats['updated'] > 0:
        plural = "libraries" if stats['updated'] > 1 else "library"
        summary_parts.append(f"{stats['updated']} {plural} updated")
    
    if stats['warnings'] > 0:
        plural = "warnings" if stats['warnings'] > 1 else "warning"
        summary_parts.append(f"{stats['warnings']} {plural}")
    
    summary = f"Config migration: {', '.join(summary_parts)}"
    
    # Add change details
    if logger.isEnabledFor(logging.INFO):
        for change in stats['changes']:
            summary += f"\n  - {change}"
    
    return summary
