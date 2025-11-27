"""
Application-wide constants for YACLib Enhanced

This module contains constants used throughout the application to avoid
magic strings and numbers scattered across the codebase.
"""

# ============================================================================
# User and Authentication
# ============================================================================

# Default admin user username
DEFAULT_USER = "admin"

# ============================================================================
# Folder and Navigation
# ============================================================================

# Special marker for virtual root folder
ROOT_FOLDER_MARKER = "__ROOT__"

# ============================================================================
# Scanner and Metadata
# ============================================================================

# Default confidence threshold for metadata matching
DEFAULT_CONFIDENCE_THRESHOLD = 0.4

# Fallback confidence threshold when using lower quality matches
FALLBACK_CONFIDENCE_THRESHOLD = 0.7

# Default number of worker threads for scanning
DEFAULT_WORKER_COUNT = 4

# ============================================================================
# Caching
# ============================================================================

# Cache duration in seconds (24 hours)
CACHE_DURATION_SECONDS = 86400

# ============================================================================
# API Protocol
# ============================================================================

# Protocol markers for API responses
PROTOCOL_CURRENT_PAGE = "currentPage:"
PROTOCOL_LIBRARY = "library:"
PROTOCOL_LIBRARY_ID = "libraryId:"
PROTOCOL_PREVIOUS_COMIC = "previousComic:"
PROTOCOL_NEXT_COMIC = "nextComic:"
