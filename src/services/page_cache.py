"""
In-process caches for comic page serving.

Keeps recently opened archives warm and caches extracted page bytes so remote
readers (WebUI + YACReader) avoid reopening CBZ/CBR on every page turn.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

CONTENT_TYPE_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
}

DEFAULT_ARCHIVE_MAX_ENTRIES = 12
DEFAULT_ARCHIVE_IDLE_TTL_SEC = 600
DEFAULT_PAGE_BYTES_MAX_ENTRIES = 64
DEFAULT_WARM_RADIUS = 5
DEFAULT_WARM_MAX_WORKERS = 2


def _file_identity(comic_path: Path) -> Tuple[str, float, int]:
    """Return (resolved_path, mtime, size) for cache keys / invalidation."""
    resolved = str(comic_path.resolve())
    try:
        stat = comic_path.stat()
        return resolved, stat.st_mtime, stat.st_size
    except OSError:
        return resolved, 0.0, 0


def _content_type_for_filename(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return CONTENT_TYPE_MAP.get(ext, "image/jpeg")


@dataclass
class _ArchiveEntry:
    path_key: str
    mtime: float
    size: int
    archive: object
    last_used: float
    lock: threading.Lock = field(default_factory=threading.Lock)


class OpenArchiveCache:
    """Thread-safe LRU of open ComicArchive handles with idle TTL."""

    def __init__(
        self,
        max_entries: int = DEFAULT_ARCHIVE_MAX_ENTRIES,
        idle_ttl_sec: float = DEFAULT_ARCHIVE_IDLE_TTL_SEC,
    ):
        self.max_entries = max_entries
        self.idle_ttl_sec = idle_ttl_sec
        self._lock = threading.RLock()
        self._entries: OrderedDict[str, _ArchiveEntry] = OrderedDict()

    def _close_entry(self, entry: _ArchiveEntry) -> None:
        try:
            entry.archive.close()
        except Exception as exc:
            logger.debug("Failed closing cached archive %s: %s", entry.path_key, exc)

    def _evict_expired_unlocked(self, now: float) -> None:
        expired_keys = [
            key
            for key, entry in self._entries.items()
            if now - entry.last_used > self.idle_ttl_sec
        ]
        for key in expired_keys:
            entry = self._entries.pop(key)
            self._close_entry(entry)

    def _evict_lru_unlocked(self) -> None:
        while len(self._entries) >= self.max_entries:
            _, entry = self._entries.popitem(last=False)
            self._close_entry(entry)

    def get_or_open(self, comic_path: Path) -> Optional[_ArchiveEntry]:
        """Return a warm archive entry, opening the comic if needed."""
        from ..scanner import open_comic

        path_key, mtime, size = _file_identity(comic_path)
        now = time.monotonic()

        with self._lock:
            self._evict_expired_unlocked(now)
            entry = self._entries.get(path_key)
            if entry is not None:
                if entry.mtime == mtime and entry.size == size:
                    entry.last_used = now
                    self._entries.move_to_end(path_key)
                    return entry
                # File changed on disk — drop stale handle
                del self._entries[path_key]
                self._close_entry(entry)

            self._evict_lru_unlocked()

        archive = open_comic(comic_path)
        if archive is None:
            return None

        entry = _ArchiveEntry(
            path_key=path_key,
            mtime=mtime,
            size=size,
            archive=archive,
            last_used=time.monotonic(),
        )

        with self._lock:
            # Another thread may have opened the same path meanwhile
            existing = self._entries.get(path_key)
            if existing is not None and existing.mtime == mtime and existing.size == size:
                self._close_entry(entry)
                existing.last_used = time.monotonic()
                self._entries.move_to_end(path_key)
                return existing

            self._evict_lru_unlocked()
            self._entries[path_key] = entry
            return entry

    def touch(self, entry: _ArchiveEntry) -> None:
        with self._lock:
            if entry.path_key not in self._entries:
                return
            entry.last_used = time.monotonic()
            self._entries.move_to_end(entry.path_key)

    def invalidate(self, comic_path: Path) -> None:
        path_key, _, _ = _file_identity(comic_path)
        with self._lock:
            entry = self._entries.pop(path_key, None)
        if entry is not None:
            self._close_entry(entry)

    def clear(self) -> None:
        with self._lock:
            entries = list(self._entries.values())
            self._entries.clear()
        for entry in entries:
            self._close_entry(entry)

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)


class PageBytesCache:
    """Thread-safe LRU of extracted page image bytes."""

    def __init__(self, max_entries: int = DEFAULT_PAGE_BYTES_MAX_ENTRIES):
        self.max_entries = max_entries
        self._lock = threading.Lock()
        self._entries: OrderedDict[Tuple[str, float, int, int], Tuple[bytes, str]] = (
            OrderedDict()
        )

    def get(
        self, comic_path: Path, page_num: int
    ) -> Optional[Tuple[bytes, str]]:
        path_key, mtime, size = _file_identity(comic_path)
        key = (path_key, mtime, size, page_num)
        with self._lock:
            value = self._entries.get(key)
            if value is None:
                return None
            self._entries.move_to_end(key)
            return value

    def put(
        self, comic_path: Path, page_num: int, page_data: bytes, content_type: str
    ) -> None:
        path_key, mtime, size = _file_identity(comic_path)
        key = (path_key, mtime, size, page_num)
        with self._lock:
            if key in self._entries:
                self._entries.move_to_end(key)
            self._entries[key] = (page_data, content_type)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)

    def has(self, comic_path: Path, page_num: int) -> bool:
        path_key, mtime, size = _file_identity(comic_path)
        key = (path_key, mtime, size, page_num)
        with self._lock:
            return key in self._entries

    def invalidate(self, comic_path: Path) -> None:
        path_key, _, _ = _file_identity(comic_path)
        with self._lock:
            stale = [key for key in self._entries if key[0] == path_key]
            for key in stale:
                del self._entries[key]

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)


_archive_cache = OpenArchiveCache()
_page_bytes_cache = PageBytesCache()
_warm_executor = ThreadPoolExecutor(
    max_workers=DEFAULT_WARM_MAX_WORKERS, thread_name_prefix="page-warm"
)
_warm_inflight: Dict[Tuple[str, int], bool] = {}
_warm_inflight_lock = threading.Lock()


def get_archive_cache() -> OpenArchiveCache:
    return _archive_cache


def get_page_bytes_cache() -> PageBytesCache:
    return _page_bytes_cache


def extract_page_bytes(
    comic_path: Path, page_num: int, *, store_in_cache: bool = True
) -> Tuple[Optional[bytes], str]:
    """
    Extract a page using warm archive + page-bytes caches.

    Returns:
        (page_bytes, content_type) or (None, "") on failure / out of range.
    """
    if page_num < 0:
        return None, ""

    cached = _page_bytes_cache.get(comic_path, page_num)
    if cached is not None:
        return cached

    if not comic_path.exists():
        raise FileNotFoundError(comic_path)

    entry = _archive_cache.get_or_open(comic_path)
    if entry is None:
        # Preserve prior API behavior: unreadable archives are 500, not 404
        raise RuntimeError(f"Failed to open comic archive: {comic_path}")

    with entry.lock:
        # Re-check bytes cache under archive lock to avoid duplicate extract
        cached = _page_bytes_cache.get(comic_path, page_num)
        if cached is not None:
            return cached

        archive = entry.archive
        if page_num >= archive.page_count:
            return None, ""

        page_data = archive.get_page(page_num)
        if page_data is None:
            return None, ""

        page = archive.pages[page_num]
        content_type = _content_type_for_filename(page.filename)

    if store_in_cache:
        _page_bytes_cache.put(comic_path, page_num, page_data, content_type)

    _archive_cache.touch(entry)
    return page_data, content_type


def _warm_page(comic_path: Path, page_num: int) -> None:
    path_key, _, _ = _file_identity(comic_path)
    inflight_key = (path_key, page_num)
    try:
        if _page_bytes_cache.has(comic_path, page_num):
            return
        extract_page_bytes(comic_path, page_num, store_in_cache=True)
    except Exception as exc:
        logger.debug(
            "Background page warm failed path=%s page=%s: %s",
            comic_path,
            page_num,
            exc,
        )
    finally:
        with _warm_inflight_lock:
            _warm_inflight.pop(inflight_key, None)


def schedule_warm_neighbors(
    comic_path: Path,
    page_num: int,
    radius: int = DEFAULT_WARM_RADIUS,
) -> None:
    """Extract nearby pages into the bytes cache while the client views page_num."""
    if radius < 1:
        return

    path_key, _, _ = _file_identity(comic_path)
    for offset in range(-radius, radius + 1):
        if offset == 0:
            continue
        neighbor = page_num + offset
        if neighbor < 0:
            continue
        if _page_bytes_cache.has(comic_path, neighbor):
            continue

        inflight_key = (path_key, neighbor)
        with _warm_inflight_lock:
            if inflight_key in _warm_inflight:
                continue
            _warm_inflight[inflight_key] = True

        _warm_executor.submit(_warm_page, comic_path, neighbor)


def reset_caches_for_tests() -> None:
    """Clear caches between unit tests."""
    _archive_cache.clear()
    _page_bytes_cache.clear()
    with _warm_inflight_lock:
        _warm_inflight.clear()
