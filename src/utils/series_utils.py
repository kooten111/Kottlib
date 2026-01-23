"""
Series Utilities

Helper functions for series name determination.
"""

from ..constants import ROOT_FOLDER_MARKER


def get_series_name(series_metadata: str = None, folder_name: str = None, title: str = None, filename: str = None) -> str:
    """
    Get the series name for a comic.

    Simple priority system:
    1. ComicInfo.xml series field (if provided)
    2. Folder name (THE FOLDER IS THE SERIES - users organize by folder!)
    3. Title from metadata
    4. Filename as last resort

    Args:
        series_metadata: Series from ComicInfo.xml
        folder_name: Name of the folder containing the comic
        title: Title from metadata
        filename: Comic filename

    Returns:
        Series name to use
    """
    # Priority 1: Use metadata series if available
    if series_metadata and series_metadata.strip():
        return series_metadata.strip()

    # Priority 2: Folder name IS the series (most common case)
    if folder_name and folder_name != ROOT_FOLDER_MARKER:
        return folder_name

    # Priority 3: Use title from metadata
    if title and title.strip():
        return title.strip()

    # Priority 4: Fallback to filename (strip extension)
    if filename:
        name = filename
        for ext in ['.cbr', '.cbz', '.cb7', '.cbt', '.pdf']:
            if name.lower().endswith(ext):
                name = name[:-len(ext)]
                break
        return name

    return "Unknown"


def get_series_name_from_comic(comic, folder_name: str = None) -> str:
    """
    Determine the series name for a comic model.

    Args:
        comic: Comic database model
        folder_name: Name of the folder containing the comic (optional)

    Returns:
        Series name for this comic
    """
    return get_series_name(
        series_metadata=comic.series if hasattr(comic, 'series') else None,
        folder_name=folder_name,
        title=comic.title if hasattr(comic, 'title') else None,
        filename=comic.filename if hasattr(comic, 'filename') else None
    )
