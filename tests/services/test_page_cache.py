"""
Tests for open-archive LRU and page-bytes cache used by remote page serving.
"""

import threading
import time
import zipfile
from pathlib import Path

import pytest

from src.services.page_cache import (
    OpenArchiveCache,
    PageBytesCache,
    extract_page_bytes,
    get_archive_cache,
    get_page_bytes_cache,
    reset_caches_for_tests,
    schedule_warm_neighbors,
)
from src.api.middleware.session import is_static_asset_path


@pytest.fixture(autouse=True)
def _clear_global_caches():
    reset_caches_for_tests()
    yield
    reset_caches_for_tests()


@pytest.fixture
def cbz_path(tmp_path: Path) -> Path:
    path = tmp_path / "reader_cache.cbz"
    with zipfile.ZipFile(path, "w") as zf:
        for i in range(5):
            zf.writestr(f"page{i:03d}.jpg", f"page-bytes-{i}".encode())
    return path


class TestOpenArchiveCache:
    def test_reuses_open_handle(self, cbz_path: Path):
        cache = OpenArchiveCache(max_entries=4, idle_ttl_sec=600)

        first = cache.get_or_open(cbz_path)
        second = cache.get_or_open(cbz_path)

        assert first is not None
        assert second is first
        assert len(cache) == 1

        with first.lock:
            assert first.archive.get_page(0) == b"page-bytes-0"

        cache.clear()

    def test_evicts_lru_when_full(self, tmp_path: Path):
        cache = OpenArchiveCache(max_entries=2, idle_ttl_sec=600)
        paths = []
        for i in range(3):
            path = tmp_path / f"comic_{i}.cbz"
            with zipfile.ZipFile(path, "w") as zf:
                zf.writestr("000.jpg", f"data-{i}".encode())
            paths.append(path)

        cache.get_or_open(paths[0])
        cache.get_or_open(paths[1])
        cache.get_or_open(paths[2])

        assert len(cache) == 2
        # paths[0] should have been evicted
        assert cache.get_or_open(paths[1]) is not None
        assert cache.get_or_open(paths[2]) is not None

        cache.clear()

    def test_idle_ttl_evicts(self, cbz_path: Path):
        cache = OpenArchiveCache(max_entries=4, idle_ttl_sec=0.05)
        entry = cache.get_or_open(cbz_path)
        assert entry is not None
        assert len(cache) == 1

        time.sleep(0.06)
        # Next access triggers expired eviction before open
        again = cache.get_or_open(cbz_path)
        assert again is not None
        # Expired entry closed; replacement is a new handle
        assert again is not entry
        assert len(cache) == 1

        cache.clear()

    def test_mtime_invalidation(self, cbz_path: Path):
        cache = OpenArchiveCache(max_entries=4, idle_ttl_sec=600)
        first = cache.get_or_open(cbz_path)
        assert first is not None

        # Rewrite archive so mtime/size change
        time.sleep(0.01)
        with zipfile.ZipFile(cbz_path, "w") as zf:
            zf.writestr("000.jpg", b"rewritten")

        second = cache.get_or_open(cbz_path)
        assert second is not None
        assert second is not first
        with second.lock:
            assert second.archive.get_page(0) == b"rewritten"

        cache.clear()


class TestPageBytesCache:
    def test_put_get_and_lru(self, cbz_path: Path):
        cache = PageBytesCache(max_entries=2)
        cache.put(cbz_path, 0, b"a", "image/jpeg")
        cache.put(cbz_path, 1, b"b", "image/jpeg")
        cache.put(cbz_path, 2, b"c", "image/jpeg")

        assert cache.get(cbz_path, 0) is None
        assert cache.get(cbz_path, 1) == (b"b", "image/jpeg")
        assert cache.get(cbz_path, 2) == (b"c", "image/jpeg")
        assert len(cache) == 2

    def test_invalidate_by_path(self, cbz_path: Path):
        cache = PageBytesCache(max_entries=8)
        cache.put(cbz_path, 0, b"a", "image/jpeg")
        cache.put(cbz_path, 1, b"b", "image/jpeg")
        cache.invalidate(cbz_path)
        assert cache.get(cbz_path, 0) is None
        assert len(cache) == 0


class TestExtractPageBytes:
    def test_extract_and_reuse_bytes_cache(self, cbz_path: Path, monkeypatch):
        open_calls = {"count": 0}
        from src.scanner import comic_loader

        original_open = comic_loader.open_comic

        def counting_open(path):
            open_calls["count"] += 1
            return original_open(path)

        monkeypatch.setattr("src.scanner.comic_loader.open_comic", counting_open)
        monkeypatch.setattr("src.scanner.open_comic", counting_open)

        data1, ctype1 = extract_page_bytes(cbz_path, 1)
        data2, ctype2 = extract_page_bytes(cbz_path, 1)

        assert data1 == b"page-bytes-1"
        assert data2 == data1
        assert ctype1 == "image/jpeg"
        assert ctype2 == ctype1
        # First extract opens once; second hits page-bytes cache (no reopen)
        assert open_calls["count"] == 1
        assert len(get_archive_cache()) == 1
        assert len(get_page_bytes_cache()) >= 1

    def test_out_of_range_returns_none(self, cbz_path: Path):
        data, ctype = extract_page_bytes(cbz_path, 99)
        assert data is None
        assert ctype == ""

    def test_warm_neighbors_fills_cache(self, cbz_path: Path):
        extract_page_bytes(cbz_path, 2)
        schedule_warm_neighbors(cbz_path, 2, radius=1)

        # Wait for background warm executor
        deadline = time.time() + 2.0
        while time.time() < deadline:
            if (
                get_page_bytes_cache().has(cbz_path, 1)
                and get_page_bytes_cache().has(cbz_path, 3)
            ):
                break
            time.sleep(0.05)

        assert get_page_bytes_cache().has(cbz_path, 1)
        assert get_page_bytes_cache().has(cbz_path, 3)

    def test_concurrent_extract_is_safe(self, cbz_path: Path):
        results = []
        errors = []

        def worker(page_num: int):
            try:
                data, _ = extract_page_bytes(cbz_path, page_num)
                results.append((page_num, data))
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=worker, args=(i % 5,)) for i in range(20)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(results) == 20
        for page_num, data in results:
            assert data == f"page-bytes-{page_num}".encode()


class TestStaticAssetPath:
    def test_comic_pages_skip_session(self):
        assert is_static_asset_path(
            "/api/libraries/1/comics/2/pages/3/remote"
        )
        assert is_static_asset_path("/v2/library/1/comic/2/page/3/remote")
        assert is_static_asset_path("/v2/library/1/comic/2/remote/page/3")
        assert is_static_asset_path("/api/libraries/1/covers/abc.webp")
        assert not is_static_asset_path("/api/libraries/1/comics/2")
