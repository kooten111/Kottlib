"""Sorting helpers used across the application."""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Tuple


_NATURAL_SPLIT_RE = re.compile(r"(\d+)")


def _tokenize_natural(value: str) -> Tuple[tuple, ...]:
    """Tokenize a string into comparable natural-sort tokens."""
    tokens = []
    for part in _NATURAL_SPLIT_RE.split(value.casefold()):
        if not part:
            continue

        if part.isdigit():
            tokens.append((0, int(part), len(part)))
        else:
            tokens.append((1, part))

    return tuple(tokens)


def natural_filename_sort_key(filename: str) -> Tuple[tuple, ...]:
    """
    Build a natural sort key for filenames/paths.

    Splits each path segment into numeric and text chunks so values like
    ``1, 2, 10`` sort numerically instead of lexicographically.
    """
    normalized = filename.replace("\\", "/")
    path = PurePosixPath(normalized)

    tokens = []
    for part in path.parts:
        tokens.extend(_tokenize_natural(part))
        tokens.append((2, ""))

    return tuple(tokens)
