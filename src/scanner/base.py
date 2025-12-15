"""
Scanner base types.

Contains core dataclasses and interfaces for the scanner module.
"""

from dataclasses import dataclass


@dataclass
class ScanResult:
    """Result from scanning operation."""
    comics_found: int = 0
    comics_added: int = 0
    comics_skipped: int = 0
    comics_skipped_unchanged: int = 0  # Fast path: unchanged files
    comics_updated: int = 0  # Moved/renamed files
    folders_found: int = 0
    thumbnails_generated: int = 0
    errors: int = 0
    duration: float = 0.0
