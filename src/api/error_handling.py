"""
Error handling utilities for API endpoints

Provides standardized error handling patterns for common operations like
file access, comic archive operations, and database operations.
"""

import logging
from functools import wraps
from pathlib import Path
from typing import Callable, TypeVar, ParamSpec

from fastapi import HTTPException

logger = logging.getLogger(__name__)

P = ParamSpec('P')
T = TypeVar('T')


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
            except FileNotFoundError as e:
                logger.warning(f"{error_message}: File not found - {e}")
                raise HTTPException(status_code=404, detail=f"{error_message}: File not found")
            except PermissionError as e:
                logger.error(f"{error_message}: Permission denied - {e}")
                raise HTTPException(status_code=403, detail=f"{error_message}: Access denied")
            except (OSError, IOError) as e:
                logger.error(f"{error_message}: I/O error - {e}", exc_info=True)
                raise HTTPException(status_code=status_code, detail=f"{error_message}: I/O error")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"{error_message}: Unexpected error - {e}", exc_info=True)
                raise HTTPException(status_code=status_code, detail=f"{error_message}")

        @wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except FileNotFoundError as e:
                logger.warning(f"{error_message}: File not found - {e}")
                raise HTTPException(status_code=404, detail=f"{error_message}: File not found")
            except PermissionError as e:
                logger.error(f"{error_message}: Permission denied - {e}")
                raise HTTPException(status_code=403, detail=f"{error_message}: Access denied")
            except (OSError, IOError) as e:
                logger.error(f"{error_message}: I/O error - {e}", exc_info=True)
                raise HTTPException(status_code=status_code, detail=f"{error_message}: I/O error")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"{error_message}: Unexpected error - {e}", exc_info=True)
                raise HTTPException(status_code=status_code, detail=f"{error_message}")

        # Return appropriate wrapper based on whether function is async
        import inspect
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
            except FileNotFoundError as e:
                logger.warning(f"{error_message}: Comic file not found - {e}")
                raise HTTPException(status_code=404, detail="Comic file not found")
            except HTTPException:
                raise
            except Exception as e:
                # Check for specific archive-related exceptions
                error_str = str(e).lower()
                exc_name = type(e).__name__

                if 'badzipfile' in exc_name.lower() or 'bad zip' in error_str:
                    logger.error(f"{error_message}: Corrupt ZIP archive - {e}")
                    raise HTTPException(status_code=500, detail="Comic archive is corrupt (ZIP)")
                elif 'rarcannotexec' in exc_name.lower() or 'unrar' in error_str:
                    logger.error(f"{error_message}: unrar tool not available - {e}")
                    raise HTTPException(
                        status_code=500,
                        detail="Cannot extract RAR files: unrar tool not installed"
                    )
                elif '7z' in error_str or 'sevenzip' in error_str:
                    logger.error(f"{error_message}: 7z archive error - {e}")
                    raise HTTPException(status_code=500, detail="Failed to read 7z archive")
                else:
                    logger.error(f"{error_message}: {e}", exc_info=True)
                    raise HTTPException(status_code=500, detail=f"{error_message}")

        @wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except FileNotFoundError as e:
                logger.warning(f"{error_message}: Comic file not found - {e}")
                raise HTTPException(status_code=404, detail="Comic file not found")
            except HTTPException:
                raise
            except Exception as e:
                # Check for specific archive-related exceptions
                error_str = str(e).lower()
                exc_name = type(e).__name__

                if 'badzipfile' in exc_name.lower() or 'bad zip' in error_str:
                    logger.error(f"{error_message}: Corrupt ZIP archive - {e}")
                    raise HTTPException(status_code=500, detail="Comic archive is corrupt (ZIP)")
                elif 'rarcannotexec' in exc_name.lower() or 'unrar' in error_str:
                    logger.error(f"{error_message}: unrar tool not available - {e}")
                    raise HTTPException(
                        status_code=500,
                        detail="Cannot extract RAR files: unrar tool not installed"
                    )
                elif '7z' in error_str or 'sevenzip' in error_str:
                    logger.error(f"{error_message}: 7z archive error - {e}")
                    raise HTTPException(status_code=500, detail="Failed to read 7z archive")
                else:
                    logger.error(f"{error_message}: {e}", exc_info=True)
                    raise HTTPException(status_code=500, detail=f"{error_message}")

        # Return appropriate wrapper based on whether function is async
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


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
