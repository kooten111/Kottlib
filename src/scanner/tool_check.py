"""
Tool availability checker for external dependencies.

Checks if required external tools (unrar, 7z, etc.) are available on the system
before attempting to scan comic archives.
"""

import logging
import shutil
import subprocess
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ToolInfo:
    """Information about an external tool"""
    name: str
    command: str
    purpose: str
    required: bool
    install_hint: str


class ToolChecker:
    """Checks for availability of external tools"""

    # Define all tools we might need
    TOOLS = {
        'unrar': ToolInfo(
            name='unrar',
            command='unrar',
            purpose='Extract CBR (RAR) comic archives',
            required=False,
            install_hint='sudo pacman -S unrar  # Arch/CachyOS\nsudo apt install unrar  # Debian/Ubuntu'
        ),
        '7z': ToolInfo(
            name='7-Zip',
            command='7z',
            purpose='Extract CB7 (7-Zip) comic archives',
            required=False,
            install_hint='sudo pacman -S p7zip  # Arch/CachyOS\nsudo apt install p7zip-full  # Debian/Ubuntu'
        ),
    }

    def __init__(self):
        self._cache: Dict[str, bool] = {}

    def check_tool(self, tool_key: str) -> bool:
        """Check if a specific tool is available"""
        if tool_key not in self.TOOLS:
            return False

        if tool_key in self._cache:
            return self._cache[tool_key]

        tool = self.TOOLS[tool_key]
        available = shutil.which(tool.command) is not None
        self._cache[tool_key] = available

        return available

    def check_all(self) -> Dict[str, bool]:
        """Check all tools and return availability status"""
        return {
            key: self.check_tool(key)
            for key in self.TOOLS.keys()
        }

    def get_missing_tools(self, required_only: bool = False) -> List[ToolInfo]:
        """Get list of missing tools"""
        missing = []
        for key, tool in self.TOOLS.items():
            if required_only and not tool.required:
                continue
            if not self.check_tool(key):
                missing.append(tool)
        return missing

    def get_available_formats(self) -> List[str]:
        """Get list of comic formats that can be processed"""
        formats = ['CBZ', 'ZIP']  # Always available (uses Python's zipfile)

        if self.check_tool('unrar'):
            formats.append('CBR')

        if self.check_tool('7z'):
            formats.append('CB7')

        return formats

    def print_status(self, verbose: bool = False):
        """Print status of all tools"""
        results = self.check_all()

        logger.info("External Tool Status:")
        logger.info("-" * 60)

        for key, tool in self.TOOLS.items():
            status = "✓ Available" if results[key] else "✗ Missing"
            required = "(Required)" if tool.required else "(Optional)"
            logger.info(f"  {tool.name:12} {status:15} {required:12} - {tool.purpose}")

        logger.info("-" * 60)
        logger.info(f"Supported formats: {', '.join(self.get_available_formats())}")

        # Show installation hints for missing optional tools if verbose
        missing = self.get_missing_tools(required_only=False)
        if missing and verbose:
            logger.info("\nTo install missing tools:")
            logger.info("-" * 60)
            for tool in missing:
                logger.info(f"\n{tool.name}:")
                for line in tool.install_hint.split('\n'):
                    logger.info(f"  {line}")

    def print_warnings(self):
        """Print warnings for missing tools"""
        missing_required = self.get_missing_tools(required_only=True)
        missing_optional = [t for t in self.get_missing_tools(required_only=False)
                           if t not in missing_required]

        if missing_required:
            logger.warning("⚠️  WARNING: Required tools missing!")
            logger.warning("-" * 60)
            for tool in missing_required:
                logger.warning(f"  • {tool.name}: {tool.purpose}")
                logger.warning(f"    Install: {tool.install_hint.split(chr(10))[0]}")
            logger.warning("-" * 60)

        if missing_optional:
            logger.warning("⚠️  NOTE: Some archive formats will not be supported")
            logger.warning("-" * 60)
            for tool in missing_optional:
                logger.warning(f"  • {tool.name} is missing - {tool.purpose}")
            logger.warning(f"\nSupported formats: {', '.join(self.get_available_formats())}")
            logger.warning("Unsupported archives will be skipped during scan.")
            logger.warning("\nTo enable all formats, install the missing tools:")
            for tool in missing_optional:
                logger.warning(f"  {tool.install_hint.split(chr(10))[0]}")
            logger.warning("-" * 60)


def check_tools_and_warn(verbose: bool = False) -> ToolChecker:
    """
    Check for external tools and print warnings if any are missing.

    Args:
        verbose: If True, print detailed installation instructions

    Returns:
        ToolChecker instance with cached results
    """
    checker = ToolChecker()

    if verbose:
        checker.print_status(verbose=True)
    else:
        checker.print_warnings()

    return checker
