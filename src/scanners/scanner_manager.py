"""
Scanner Manager

Central registry and orchestrator for all metadata scanners.
Handles scanner selection, fallback logic, and result aggregation.
"""

from typing import Dict, List, Optional, Type, Tuple
from dataclasses import dataclass
from enum import Enum
import os
import sys
import importlib.util
from pathlib import Path

from .base_scanner import BaseScanner, ScanResult, ScanLevel, MatchConfidence


class FallbackStrategy(Enum):
    """How to handle fallback scanners"""
    NONE = "none"  # Don't use fallback
    ON_LOW_CONFIDENCE = "on_low_confidence"  # Use fallback if confidence < threshold
    ON_FAILURE = "on_failure"  # Use fallback only if primary fails completely
    ALWAYS = "always"  # Always try all scanners and merge results


@dataclass
class ScannerConfig:
    """
    Configuration for a scanner in a library

    Attributes:
        scanner_class: The scanner class to instantiate
        is_primary: Whether this is the primary scanner
        is_fallback: Whether this is a fallback scanner
        fallback_threshold: Confidence threshold to trigger fallback
        config: Scanner-specific configuration
    """
    scanner_class: Type[BaseScanner]
    is_primary: bool = True
    is_fallback: bool = False
    fallback_threshold: float = 0.7
    config: Dict = None

    def __post_init__(self):
        if self.config is None:
            self.config = {}


class ScannerManager:
    """
    Manages scanners for different library types

    Example usage:
        >>> manager = ScannerManager()
        >>> manager.register_scanner('doujinshi', NhentaiScanner)
        >>> manager.register_fallback('manga', AniListScanner, JikanScanner)
        >>> result = manager.scan('doujinshi', 'comic_file.cbz')
    """

    def __init__(self):
        # Library type -> list of ScannerConfig
        self._library_scanners: Dict[str, List[ScannerConfig]] = {}

        # Registered scanner classes (name -> class)
        self._available_scanners: Dict[str, Type[BaseScanner]] = {}

    def register_scanner_class(self, scanner_class: Type[BaseScanner]):
        """
        Register a scanner class as available

        Args:
            scanner_class: Scanner class to register
        """
        # Instantiate temporarily to get source name
        temp = scanner_class()
        self._available_scanners[temp.source_name] = scanner_class

    def configure_library(
        self,
        library_type: str,
        primary_scanner: str,
        fallback_scanners: Optional[List[str]] = None,
        fallback_strategy: FallbackStrategy = FallbackStrategy.ON_LOW_CONFIDENCE,
        fallback_threshold: float = 0.7,
        scanner_configs: Optional[Dict[str, Dict]] = None
    ):
        """
        Configure scanners for a library type

        Args:
            library_type: Type of library (e.g., "doujinshi", "manga", "comics")
            primary_scanner: Name of primary scanner (e.g., "nhentai")
            fallback_scanners: Optional list of fallback scanner names
            fallback_strategy: When to use fallback scanners
            fallback_threshold: Confidence threshold for fallback
            scanner_configs: Optional dict of scanner-specific configs

        Example:
            >>> manager.configure_library(
            ...     'manga',
            ...     primary_scanner='AniList',
            ...     fallback_scanners=['Jikan'],
            ...     fallback_threshold=0.7
            ... )
        """
        if scanner_configs is None:
            scanner_configs = {}

        # Get scanner classes
        if primary_scanner not in self._available_scanners:
            raise ValueError(f"Unknown scanner: {primary_scanner}")

        scanners = []

        # Add primary scanner
        scanners.append(ScannerConfig(
            scanner_class=self._available_scanners[primary_scanner],
            is_primary=True,
            is_fallback=False,
            config=scanner_configs.get(primary_scanner, {})
        ))

        # Add fallback scanners
        if fallback_scanners:
            for scanner_name in fallback_scanners:
                if scanner_name not in self._available_scanners:
                    raise ValueError(f"Unknown fallback scanner: {scanner_name}")

                scanners.append(ScannerConfig(
                    scanner_class=self._available_scanners[scanner_name],
                    is_primary=False,
                    is_fallback=True,
                    fallback_threshold=fallback_threshold,
                    config=scanner_configs.get(scanner_name, {})
                ))

        self._library_scanners[library_type] = scanners
        self._fallback_strategy = fallback_strategy

    def scan(
        self,
        library_type: str,
        query: str,
        **kwargs
    ) -> Tuple[Optional[ScanResult], List[ScanResult]]:
        """
        Scan for metadata using configured scanners

        Args:
            library_type: Type of library
            query: Search query (filename or series name)
            **kwargs: Additional scanner-specific parameters

        Returns:
            (best_result, all_candidates)

        Raises:
            ValueError: If library type not configured
        """
        if library_type not in self._library_scanners:
            raise ValueError(f"Library type '{library_type}' not configured")

        scanners = self._library_scanners[library_type]

        # Try primary scanner first
        primary_config = scanners[0]
        primary_scanner = primary_config.scanner_class(primary_config.config)

        best_result, candidates = primary_scanner.scan(query, **kwargs)

        # Check if we should use fallback
        should_fallback = False

        if self._fallback_strategy == FallbackStrategy.ALWAYS:
            should_fallback = True
        elif self._fallback_strategy == FallbackStrategy.ON_FAILURE:
            should_fallback = (best_result is None)
        elif self._fallback_strategy == FallbackStrategy.ON_LOW_CONFIDENCE:
            if best_result is None:
                should_fallback = True
            elif best_result.confidence < primary_config.fallback_threshold:
                should_fallback = True

        # Try fallback scanners if needed
        if should_fallback and len(scanners) > 1:
            for fallback_config in scanners[1:]:
                fallback_scanner = fallback_config.scanner_class(fallback_config.config)

                try:
                    fallback_result, fallback_candidates = fallback_scanner.scan(query, **kwargs)

                    if fallback_result:
                        # If better than current best, use it
                        if best_result is None or fallback_result.confidence > best_result.confidence:
                            best_result = fallback_result
                            candidates.extend(fallback_candidates)

                except Exception as e:
                    # Log error but continue
                    print(f"Fallback scanner {fallback_scanner.source_name} failed: {e}")
                    continue

        return best_result, candidates

    def get_configured_libraries(self) -> List[str]:
        """Get list of configured library types"""
        return list(self._library_scanners.keys())

    def get_available_scanners(self) -> List[str]:
        """Get list of available scanner names"""
        return list(self._available_scanners.keys())

    def get_library_config(self, library_type: str) -> Optional[List[ScannerConfig]]:
        """Get scanner configuration for a library type"""
        return self._library_scanners.get(library_type)


# Global singleton instance
_default_manager: Optional[ScannerManager] = None


def get_manager() -> ScannerManager:
    """Get the global scanner manager instance"""
    global _default_manager
    if _default_manager is None:
        _default_manager = ScannerManager()
    return _default_manager


def discover_scanners(scanners_dir: str = None) -> List[Type[BaseScanner]]:
    """
    Automatically discover scanner plugins in the scanners directory

    Args:
        scanners_dir: Path to scanners directory. If None, uses project root/scanners

    Returns:
        List of discovered scanner classes
    """
    if scanners_dir is None:
        # Get project root (2 levels up from src/scanners)
        project_root = Path(__file__).parent.parent.parent
        scanners_dir = project_root / "scanners"
    else:
        scanners_dir = Path(scanners_dir)

    if not scanners_dir.exists():
        print(f"Warning: Scanners directory not found: {scanners_dir}")
        return []

    discovered = []

    # Scan for scanner subdirectories
    for item in scanners_dir.iterdir():
        if not item.is_dir() or item.name.startswith('_') or item.name.startswith('.'):
            continue

        # Look for scanner files (*_scanner.py or scanner.py)
        scanner_files = list(item.glob('*_scanner.py')) + list(item.glob('scanner.py'))

        for scanner_file in scanner_files:
            try:
                # Load the module dynamically
                module_name = f"scanner_{item.name}_{scanner_file.stem}"
                spec = importlib.util.spec_from_file_location(module_name, scanner_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)

                    # Find BaseScanner subclasses in the module
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and
                            issubclass(attr, BaseScanner) and
                            attr is not BaseScanner):
                            discovered.append(attr)
                            print(f"Discovered scanner: {attr_name} from {item.name}")

            except Exception as e:
                print(f"Warning: Failed to load scanner from {scanner_file}: {e}")
                continue

    return discovered


def init_default_scanners():
    """
    Initialize default scanner configurations

    Automatically discovers and registers all scanners in the scanners/ directory.
    Sets up default library configurations based on scanner names.
    """
    manager = get_manager()

    # Auto-discover and register all scanners
    discovered_scanners = discover_scanners()

    for scanner_class in discovered_scanners:
        try:
            manager.register_scanner_class(scanner_class)
        except Exception as e:
            print(f"Warning: Failed to register scanner {scanner_class}: {e}")

    # Get available scanners to set up default configurations
    available = manager.get_available_scanners()

    # Configure libraries based on discovered scanners
    # Default mappings (can be overridden by config file)
    if 'nhentai' in available:
        manager.configure_library(
            'doujinshi',
            primary_scanner='nhentai',
            fallback_scanners=None
        )

    if 'AniList' in available:
        manager.configure_library(
            'manga',
            primary_scanner='AniList',
            fallback_scanners=None,
            fallback_threshold=0.7
        )

    if 'Comic Vine' in available:
        # Use Metron as fallback for comics if available
        fallback_scanners = ['Metron'] if 'Metron' in available else None
        manager.configure_library(
            'comics',
            primary_scanner='Comic Vine',
            fallback_scanners=fallback_scanners,
            fallback_threshold=0.7
        )
    elif 'Metron' in available:
        # If Comic Vine is not available but Metron is, use Metron as primary
        manager.configure_library(
            'comics',
            primary_scanner='Metron',
            fallback_scanners=None,
            fallback_threshold=0.7
        )

    return manager
