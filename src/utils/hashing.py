"""Centralized hashing utilities for Kottlib"""

import hashlib
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def calculate_comic_hash(file_path: Path) -> str:
    """
    Calculate hash for comic file identification.
    
    Protocol: SHA1(first 512KB) + file_size_as_string
    
    This hash is used for thumbnail naming and comic identification.
    The algorithm is compatible with YACReader protocol.
    
    Args:
        file_path: Path to the comic file
        
    Returns:
        Hash string for the comic file
    """
    try:
        # Read first 512KB (or entire file if smaller)
        with open(file_path, 'rb') as f:
            first_chunk = f.read(512 * 1024)  # 512KB

        # Calculate SHA1 of chunk
        sha1_hash = hashlib.sha1(first_chunk).hexdigest()

        # Get file size
        file_size = file_path.stat().st_size

        # Concatenate: hash + size
        return f"{sha1_hash}{file_size}"
    except Exception as e:
        logger.error(f"Failed to calculate hash for {file_path}: {e}")
        raise


def calculate_cache_key(data: str) -> str:
    """
    Calculate MD5 hash for cache keys.
    
    Args:
        data: String data to hash
        
    Returns:
        MD5 hash string
    """
    return hashlib.md5(data.encode()).hexdigest()
