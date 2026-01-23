"""
Application-wide constants for Kottlib

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

# ============================================================================
# Path Markers
# ============================================================================

# Prefix for comic paths in browse API (distinguishes comics from folders)
COMIC_PATH_PREFIX = "_comic/"

# ============================================================================
# Pagination
# ============================================================================

# Default page size for browse endpoints
DEFAULT_PAGE_SIZE = 50

# Maximum page size allowed
MAX_PAGE_SIZE = 200

# ============================================================================
# HTTP Status Codes (for readability)
# ============================================================================

HTTP_OK = 200
HTTP_CREATED = 201
HTTP_NO_CONTENT = 204
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_CONFLICT = 409
HTTP_INTERNAL_ERROR = 500

# ============================================================================
# Error Messages
# ============================================================================

ERROR_LIBRARY_NOT_FOUND = "Library not found"
ERROR_COMIC_NOT_FOUND = "Comic not found"
ERROR_FOLDER_NOT_FOUND = "Folder not found"
ERROR_USER_NOT_FOUND = "User not found"
ERROR_SESSION_REQUIRED = "Session required"
ERROR_AUTH_REQUIRED = "Authentication required"
