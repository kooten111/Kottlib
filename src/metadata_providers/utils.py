"""
Shared utility functions for scanners.
"""

import re

def clean_query(query: str) -> str:
    """
    Clean a search query by removing common metadata markers.

    Removes:
    - Content in brackets: [English], [Aishi21], etc.
    - Content in parentheses: (C101), (Fate Grand Order), etc.
    - Content in curly braces: {tags}, etc.
    - File extensions

    Args:
        query: Raw query string to clean

    Returns:
        Cleaned query with only the core title

    Examples:
        >>> clean_query("[Poni] Title | English Title [English] [Translator].cbz")
        'Title | English Title'

        >>> clean_query("(C101) [Artist] Title (Original)")
        'Title'
    """
    # Remove file extension
    cleaned = re.sub(r'\.(cbz|cbr|zip|rar|7z|pdf|epub)$', '', query, flags=re.IGNORECASE)

    # Remove content in brackets, parentheses, and curly braces
    # Use a loop to handle nested brackets
    max_iterations = 10
    for _ in range(max_iterations):
        before = cleaned
        # Remove [...], (...), {...}
        cleaned = re.sub(r'\[[^\]]*\]', '', cleaned)
        cleaned = re.sub(r'\([^\)]*\)', '', cleaned)
        cleaned = re.sub(r'\{[^\}]*\}', '', cleaned)

        # If nothing changed, we're done
        if cleaned == before:
            break

    # Clean up extra whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = cleaned.strip()

    # Remove common separators at start/end
    cleaned = cleaned.strip(' -|_')

    return cleaned
