"""
Error handling utilities for API endpoints

Provides standardized error handling patterns for common operations like
file access, comic archive operations, and database operations.
"""

import inspect
import logging
from functools import wraps
from pathlib import Path
from typing import Callable, TypeVar, ParamSpec, Optional

from fastapi import HTTPException

logger = logging.getLogger(__name__)

P = ParamSpec('P')
T = TypeVar('T')


# ============================================================================
# Shared Error Handlers
# ============================================================================

def _handle_file_error(
    error: Exception,
    error_message: str,
    default_status_code: int
) -> HTTPException:
    """
    Convert a file operation exception to an HTTPException.

    This consolidates the error handling logic used by both async and sync
    file operation wrappers.

    Args:
        error: The caught exception
        error_message: Base error message to return
        default_status_code: Status code for unrecognized errors

    Returns:
        HTTPException to raise
    """
    if isinstance(error, FileNotFoundError):
        logger.warning(f"{error_message}: File not found - {error}")
        return HTTPException(status_code=404, detail=f"{error_message}: File not found")

    if isinstance(error, PermissionError):
        logger.error(f"{error_message}: Permission denied - {error}")
        return HTTPException(status_code=403, detail=f"{error_message}: Access denied")

    if isinstance(error, (OSError, IOError)):
        logger.error(f"{error_message}: I/O error - {error}", exc_info=True)
        return HTTPException(status_code=default_status_code, detail=f"{error_message}: I/O error")

    # Generic error
    logger.error(f"{error_message}: Unexpected error - {error}", exc_info=True)
    return HTTPException(status_code=default_status_code, detail=f"{error_message}")


def _handle_archive_error(
    error: Exception,
    error_message: str
) -> HTTPException:
    """
    Convert a comic archive exception to an HTTPException.

    This consolidates the error handling logic used by both async and sync
    archive operation wrappers.

    Args:
        error: The caught exception
        error_message: Base error message to return

    Returns:
        HTTPException to raise
    """
    if isinstance(error, FileNotFoundError):
        logger.warning(f"{error_message}: Comic file not found - {error}")
        return HTTPException(status_code=404, detail="Comic file not found")

    # Check for specific archive-related exceptions
    error_str = str(error).lower()
    exc_name = type(error).__name__

    if 'badzipfile' in exc_name.lower() or 'bad zip' in error_str:
        logger.error(f"{error_message}: Corrupt ZIP archive - {error}")
        return HTTPException(status_code=500, detail="Comic archive is corrupt (ZIP)")

    if 'rarcannotexec' in exc_name.lower() or 'unrar' in error_str:
        logger.error(f"{error_message}: unrar tool not available - {error}")
        return HTTPException(
            status_code=500,
            detail="Cannot extract RAR files: unrar tool not installed"
        )

    if '7z' in error_str or 'sevenzip' in error_str:
        logger.error(f"{error_message}: 7z archive error - {error}")
        return HTTPException(status_code=500, detail="Failed to read 7z archive")

    # Generic archive error
    logger.error(f"{error_message}: {error}", exc_info=True)
    return HTTPException(status_code=500, detail=f"{error_message}")


# ============================================================================
# Decorators
# ============================================================================

def handle_file_operation(error_message: str = "File operation failed", status_code: int = 500):
    """
    Decorator to handle file operation errors consistently

    Catches common file-related exceptions and returns appropriate HTTP errors:
    - FileNotFoundError -> 404
    - PermissionError -> 403
    - OSError, IOError -> 500

    Args:
        error_message: Base error message to return
        status_code: Default status code for non-specific errors

    Usage:
        @handle_file_operation("Failed to read cover image")
        async def get_cover(path: Path):
            return FileResponse(path)
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                raise
            except Exception as e:
                raise _handle_file_error(e, error_message, status_code)

        @wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except HTTPException:
                raise
            except Exception as e:
                raise _handle_file_error(e, error_message, status_code)

        # Return appropriate wrapper based on whether function is async
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def handle_comic_archive_errors(error_message: str = "Failed to open comic archive"):
    """
    Decorator to handle comic archive operation errors

    Catches comic loading exceptions and provides user-friendly error messages:
    - zipfile.BadZipFile -> 500 (corrupt archive)
    - rarfile.RarCannotExec -> 500 (unrar not installed)
    - py7zr exceptions -> 500 (corrupt or unsupported)

    Args:
        error_message: Base error message to return

    Usage:
        @handle_comic_archive_errors("Failed to extract comic page")
        async def get_page(comic_id: int, page_num: int):
            with open_comic(comic_path) as archive:
                return archive.get_page(page_num)
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                raise
            except Exception as e:
                raise _handle_archive_error(e, error_message)

        @wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except HTTPException:
                raise
            except Exception as e:
                raise _handle_archive_error(e, error_message)

        # Return appropriate wrapper based on whether function is async
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# ============================================================================
# Utility Functions
# ============================================================================

def safe_path_exists(path: Path, operation: str = "file access") -> bool:
    """
    Safely check if a path exists, catching permission and I/O errors

    Args:
        path: Path to check
        operation: Description of operation (for logging)

    Returns:
        True if path exists and is accessible, False otherwise
    """
    try:
        return path.exists()
    except PermissionError:
        logger.warning(f"Permission denied checking {operation}: {path}")
        return False
    except OSError as e:
        logger.warning(f"OS error checking {operation}: {path} - {e}")
        return False


def safe_file_stat(path: Path, operation: str = "file access"):
    """
    Safely get file stats, catching permission and I/O errors

    Args:
        path: Path to stat
        operation: Description of operation (for logging)

    Returns:
        os.stat_result or None if error occurred
    """
    try:
        return path.stat()
    except PermissionError:
        logger.warning(f"Permission denied accessing {operation}: {path}")
        return None
    except OSError as e:
        logger.warning(f"OS error accessing {operation}: {path} - {e}")
        return None


def not_found_exception(entity_type: str) -> HTTPException:
    """
    Create a standardized 404 exception for an entity type.

    Usage:
        raise not_found_exception("Library")
        raise not_found_exception("Comic")

    Args:
        entity_type: The type of entity (e.g., "Library", "Comic", "Folder")

    Returns:
        HTTPException with 404 status code
    """
    return HTTPException(status_code=404, detail=f"{entity_type} not found")
