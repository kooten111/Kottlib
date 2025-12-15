"""
Available scanners endpoints.

GET /available - List all available scanners
GET /libraries - Get scanner configuration for all libraries
"""

from typing import List
import logging

from fastapi import Request

from src.metadata_providers.schema import get_scanner_capabilities
from src.database.models import Library

from ..models import ScannerInfo, LibraryScannerConfig, ScanLevelEnum
from ..manager import get_scanner_manager


logger = logging.getLogger(__name__)


async def get_available_scanners() -> List[ScannerInfo]:
    """
    Get list of available scanners.

    Returns information about all registered scanners including their capabilities.
    """
    manager = get_scanner_manager()
    available = manager.get_available_scanners()

    scanners_info = []
    
    # Build info for each available scanner
    for scanner_name in available:
        # Get capabilities from metadata schema (try exact match first, then lowercase)
        caps = get_scanner_capabilities(scanner_name)
        if not caps:
            caps = get_scanner_capabilities(scanner_name.lower())
        
        # Get scanner class to check scan_level and config
        scanner_class = manager._available_scanners.get(scanner_name)
        scan_level = ScanLevelEnum.SERIES  # Default
        requires_config = False
        config_keys = []
        
        # Get declarative config schema
        config_schema = []

        if scanner_class:
            try:
                # Instantiate to get properties
                temp_scanner = scanner_class()

                # Map from ScanLevel enum to ScanLevelEnum
                if temp_scanner.scan_level.value == 'file':
                    scan_level = ScanLevelEnum.FILE
                elif temp_scanner.scan_level.value == 'series':
                    scan_level = ScanLevelEnum.SERIES

                # Get declarative config schema (new method)
                schema_options = temp_scanner.get_config_schema()
                if schema_options:
                    config_schema = [opt.to_dict() for opt in schema_options]
                    # Mark as requiring config if any options are required
                    requires_config = any(opt.required for opt in schema_options)

                # Get config requirements (deprecated method, for backward compatibility)
                config_keys = temp_scanner.get_required_config_keys()
                if config_keys and not requires_config:
                    requires_config = True

                # Check for optional config keys if exposed as property (convention)
                if hasattr(temp_scanner, 'config_keys'):
                    extra_keys = getattr(temp_scanner, 'config_keys')
                    if isinstance(extra_keys, list):
                        for key in extra_keys:
                            if key not in config_keys:
                                config_keys.append(key)

            except Exception as e:
                logger.warning(f"Failed to inspect scanner {scanner_name}: {e}")
        
        scanners_info.append(ScannerInfo(
            name=scanner_name,
            scan_level=scan_level,
            description=caps.description if caps else f"Metadata scanner: {scanner_name}",
            requires_config=requires_config,
            config_keys=config_keys,
            config_schema=config_schema,
            provided_fields=[f.value for f in caps.provided_fields] if caps else [],
            primary_fields=[f.value for f in caps.primary_fields] if caps else []
        ))

    return scanners_info


async def get_library_scanner_configs(request: Request) -> List[LibraryScannerConfig]:
    """
    Get scanner configuration for all libraries.

    Returns all libraries from the database with their scanner configurations.
    Scanner settings are stored in the library's settings JSON field.
    """
    db = request.app.state.db

    with db.get_session() as session:
        libraries = session.query(Library).all()
        manager = get_scanner_manager()

        configs = []
        for lib in libraries:
            # Get scanner settings from library settings JSON
            settings = lib.settings or {}
            scanner_config = settings.get('scanner', {})
            primary_scanner = scanner_config.get('primary_scanner')
            
            # Determine scan level from the primary scanner
            scan_level = None
            if primary_scanner and primary_scanner in manager.get_available_scanners():
                try:
                    # Get the scanner class and instantiate to check scan_level
                    scanner_class = manager._available_scanners.get(primary_scanner)
                    if scanner_class:
                        temp_scanner = scanner_class()
                        # Map from ScanLevel enum to ScanLevelEnum
                        if temp_scanner.scan_level.value == 'file':
                            scan_level = ScanLevelEnum.FILE
                        elif temp_scanner.scan_level.value == 'series':
                            scan_level = ScanLevelEnum.SERIES
                except Exception:
                    pass  # Fallback to None if scanner can't be instantiated

            configs.append(LibraryScannerConfig(
                library_id=lib.id,
                library_name=lib.name,
                library_path=lib.path,
                primary_scanner=primary_scanner,
                scan_level=scan_level,
                fallback_scanners=scanner_config.get('fallback_scanners', []),
                fallback_threshold=scanner_config.get('fallback_threshold', 0.7),
                confidence_threshold=scanner_config.get('confidence_threshold', 0.4),
                scanner_configs=scanner_config.get('scanner_configs', {})
            ))

        return configs
