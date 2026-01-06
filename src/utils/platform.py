"""
Platform-specific path and configuration utilities.

Provides functions for getting platform-appropriate configuration and data
directories, as well as detecting the project root directory.
"""

import os
import platform
import logging
from pathlib import Path
from typing import Optional


logger = logging.getLogger(__name__)


def get_config_dir() -> Path:
    """
    Get platform-appropriate config directory.
    
    Returns:
        Path to the configuration directory based on platform:
        - Linux: ~/.config/kottlib
        - macOS: ~/Library/Application Support/Kottlib
        - Windows: %APPDATA%/Kottlib
        - Other: ~/.kottlib
    """
    system = platform.system()
    
    if system == 'Linux':
        config_dir = Path.home() / '.config' / 'kottlib'
    elif system == 'Darwin':  # macOS
        config_dir = Path.home() / 'Library' / 'Application Support' / 'Kottlib'
    elif system == 'Windows':
        config_dir = Path(os.environ.get('APPDATA', Path.home())) / 'Kottlib'
    else:
        config_dir = Path.home() / '.kottlib'
    
    return config_dir


def get_data_dir() -> Path:
    """
    Get platform-appropriate data directory.
    
    Returns ./data relative to project root, or directory specified by
    KOTTLIB_DATA_DIR environment variable.
    
    Returns:
        Path to the data directory
    """
    # Check for environment variable override
    env_data_dir = os.environ.get('KOTTLIB_DATA_DIR')
    if env_data_dir:
        data_dir = Path(env_data_dir).resolve()
        logger.info(f"Using data directory from KOTTLIB_DATA_DIR: {data_dir}")
    else:
        project_root = get_project_root()
        data_dir = project_root / 'data'
    
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_project_root() -> Path:
    """
    Find project root by walking up looking for markers.
    
    This finds the project root by looking for key files (config.yml, src/ directory)
    starting from this file's location and walking up the directory tree.
    
    Returns:
        Path to the project root directory
    """
    # Start from this file's directory
    current = Path(__file__).parent.parent.parent.resolve()
    logger.debug(f"Looking for project root, starting from: {current}")
    
    # Walk up to find project root (directory containing config.yml or src/)
    max_depth = 10
    for _ in range(max_depth):
        # Check for project markers
        has_config = (current / 'config.yml').exists()
        has_src = (current / 'src').exists()
        logger.debug(f"Checking {current}: config.yml={has_config}, src/={has_src}")
        
        if has_config or has_src:
            logger.info(f"Found project root: {current}")
            return current
        
        # Move up one level
        parent = current.parent
        if parent == current:  # Reached filesystem root
            break
        current = parent
    
    # Fallback to current working directory if not found
    fallback = Path.cwd()
    logger.warning(f"Could not find project root, falling back to cwd: {fallback}")
    return fallback
