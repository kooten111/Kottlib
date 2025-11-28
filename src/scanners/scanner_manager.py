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
    Manages metadata scanners

    Discovers and registers scanner plugins. Libraries use scanners directly
    via their settings configuration.

    Example usage:
        >>> manager = ScannerManager()
        >>> manager.register_scanner_class(NhentaiScanner)
        >>> scanner = manager.get_scanner('nhentai', config={'api_key': 'xxx'})
        >>> result, candidates = scanner.scan('filename.cbz')
    """

    def __init__(self):
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

    def get_scanner(self, scanner_name: str, config: Optional[Dict] = None) -> BaseScanner:
        """
        Get a scanner instance by name

        Args:
            scanner_name: Name of the scanner (e.g., "nhentai", "AniList")
            config: Optional scanner-specific configuration

        Returns:
            Scanner instance

        Raises:
            ValueError: If scanner not found
        """
        if scanner_name not in self._available_scanners:
            raise ValueError(f"Unknown scanner: {scanner_name}")

        scanner_class = self._available_scanners[scanner_name]
        return scanner_class(config or {})



    def get_available_scanners(self) -> List[str]:
        """Get list of available scanner names"""
        return list(self._available_scanners.keys())




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
    """
    manager = get_manager()

    # Auto-discover and register all scanners
    discovered_scanners = discover_scanners()

    for scanner_class in discovered_scanners:
        try:
            manager.register_scanner_class(scanner_class)
        except Exception as e:
            print(f"Warning: Failed to register scanner {scanner_class}: {e}")

    return manager
