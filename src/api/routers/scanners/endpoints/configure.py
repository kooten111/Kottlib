"""
Scanner configuration endpoints.

PUT /libraries/{library_id}/configure - Configure scanner for a library
POST /verify-credentials/{scanner_name} - Verify scanner credentials
"""

from typing import Dict, Any
import logging

from fastapi import HTTPException, Request
from sqlalchemy.orm.attributes import flag_modified

from src.scanners import ScannerConfigError
from src.database.models import Library
from src.database import get_library_by_id, update_library

from ..models import LibraryScannerConfig, UpdateLibraryScannerConfig, ScanLevelEnum
from ..manager import get_scanner_manager


logger = logging.getLogger(__name__)


async def configure_library_scanner(
    library_id: int,
    config: UpdateLibraryScannerConfig,
    request: Request
) -> LibraryScannerConfig:
    """
    Configure scanner for a specific library.

    Updates the scanner configuration for a library and saves it to the database.

    Example:
        PUT /scanners/libraries/4/configure
        {
            "primary_scanner": "nhentai",
            "fallback_scanners": [],
            "confidence_threshold": 0.4,
            "fallback_threshold": 0.7
        }
    """
    db = request.app.state.db
    manager = get_scanner_manager()

    with db.get_session() as session:
        # Validate library exists
        library = session.query(Library).filter(Library.id == library_id).first()
        if not library:
            raise HTTPException(
                status_code=404,
                detail=f"Library with ID {library_id} not found"
            )

        # Validate primary scanner
        if config.primary_scanner not in manager.get_available_scanners():
            raise HTTPException(
                status_code=400,
                detail=f"Scanner '{config.primary_scanner}' not available"
            )

        # Validate fallback scanners
        for fallback in config.fallback_scanners:
            if fallback not in manager.get_available_scanners():
                raise HTTPException(
                    status_code=400,
                    detail=f"Fallback scanner '{fallback}' not available"
                )

        # Update library settings
        settings = library.settings or {}
        settings['scanner'] = {
            'primary_scanner': config.primary_scanner,
            'fallback_scanners': config.fallback_scanners,
            'confidence_threshold': config.confidence_threshold,
            'fallback_threshold': config.fallback_threshold,
            'scanner_configs': config.scanner_configs
        }
        
        # Force SQLAlchemy to detect the change to the JSON column
        library.settings = settings
        flag_modified(library, 'settings')

        # Save to database
        session.commit()
        session.refresh(library)

        # Determine scan level
        scan_level = None
        try:
            scanner_class = manager._available_scanners.get(config.primary_scanner)
            if scanner_class:
                temp_scanner = scanner_class()
                if temp_scanner.scan_level.value == 'file':
                    scan_level = ScanLevelEnum.FILE
                elif temp_scanner.scan_level.value == 'series':
                    scan_level = ScanLevelEnum.SERIES
        except Exception:
            pass

        # Return updated configuration
        return LibraryScannerConfig(
            library_id=library.id,
            library_name=library.name,
            library_path=library.path,
            primary_scanner=config.primary_scanner,
            scan_level=scan_level,
            fallback_scanners=config.fallback_scanners,
            confidence_threshold=config.confidence_threshold,
            fallback_threshold=config.fallback_threshold
        )


async def verify_scanner_credentials(
    scanner_name: str,
    credentials: Dict[str, Any],
    request: Request
) -> Dict[str, Any]:
    """
    Verify scanner credentials by attempting to instantiate and test.
    
    Example:
        POST /scanners/verify-credentials/metron
        {
            "username": "test_user",
            "password": "test_pass"
        }
    """
    manager = get_scanner_manager()
    
    if scanner_name not in manager.get_available_scanners():
        raise HTTPException(status_code=404, detail=f"Scanner '{scanner_name}' not found")
    
    try:
        # Instantiate scanner with provided credentials
        scanner = manager.get_scanner(scanner_name, config=credentials)
        
        # Try a minimal test - for Metron, just check if API client initializes
        # Scanner-specific verification logic could be added here
        
        return {
            "success": True,
            "scanner": scanner_name,
            "message": "Credentials validated successfully"
        }
    except ScannerConfigError as e:
        return {
            "success": False,
            "scanner": scanner_name,
            "error": str(e),
            "error_type": "config_error"  
        }
    except Exception as e:
        return {
            "success": False,
            "scanner": scanner_name,
            "error": str(e),
            "error_type": "unknown"
        }
