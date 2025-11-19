"""
Tool availability checker for external dependencies.

Checks if required external tools (unrar, 7z, etc.) are available on the system
before attempting to scan comic archives.
"""

import shutil
import subprocess
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


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

        print("External Tool Status:")
        print("-" * 60)

        for key, tool in self.TOOLS.items():
            status = "✓ Available" if results[key] else "✗ Missing"
            required = "(Required)" if tool.required else "(Optional)"
            print(f"  {tool.name:12} {status:15} {required:12} - {tool.purpose}")

        print("-" * 60)
        print(f"Supported formats: {', '.join(self.get_available_formats())}")
        print()

        # Show installation hints for missing optional tools if verbose
        missing = self.get_missing_tools(required_only=False)
        if missing and verbose:
            print("\nTo install missing tools:")
            print("-" * 60)
            for tool in missing:
                print(f"\n{tool.name}:")
                for line in tool.install_hint.split('\n'):
                    print(f"  {line}")
            print()

    def print_warnings(self):
        """Print warnings for missing tools"""
        missing_required = self.get_missing_tools(required_only=True)
        missing_optional = [t for t in self.get_missing_tools(required_only=False)
                           if t not in missing_required]

        if missing_required:
            print("\n⚠️  WARNING: Required tools missing!")
            print("-" * 60)
            for tool in missing_required:
                print(f"  • {tool.name}: {tool.purpose}")
                print(f"    Install: {tool.install_hint.split(chr(10))[0]}")
            print("-" * 60)
            print()

        if missing_optional:
            print("\n⚠️  NOTE: Some archive formats will not be supported")
            print("-" * 60)
            for tool in missing_optional:
                print(f"  • {tool.name} is missing - {tool.purpose}")
            print(f"\nSupported formats: {', '.join(self.get_available_formats())}")
            print("Unsupported archives will be skipped during scan.")
            print("\nTo enable all formats, install the missing tools:")
            for tool in missing_optional:
                print(f"  {tool.install_hint.split(chr(10))[0]}")
            print("-" * 60)
            print()


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
