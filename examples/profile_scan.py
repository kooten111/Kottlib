#!/usr/bin/env python3
"""
Profile Scanner Performance

Identifies bottlenecks in the scanning process.
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from scanner import open_comic, is_comic_file
from scanner.thumbnail_generator import calculate_file_hash, generate_dual_thumbnails
from database import get_covers_dir


def profile_single_comic(comic_path: Path):
    """Profile processing a single comic"""
    print(f"\nProfiling: {comic_path.name}")
    print(f"File size: {comic_path.stat().st_size / 1024 / 1024:.2f} MB")
    print("="*60)

    timings = {}

    # 1. Calculate hash
    start = time.time()
    file_hash = calculate_file_hash(comic_path)
    timings['hash'] = time.time() - start
    print(f"✅ Hash calculation:  {timings['hash']*1000:.1f}ms")

    # 2. Open archive
    start = time.time()
    comic = open_comic(comic_path)
    timings['open'] = time.time() - start
    print(f"✅ Open archive:      {timings['open']*1000:.1f}ms")

    if not comic:
        print("❌ Failed to open comic")
        return

    # 3. Get page count (triggers _load_pages)
    start = time.time()
    page_count = comic.page_count
    timings['page_count'] = time.time() - start
    print(f"✅ Get page count:    {timings['page_count']*1000:.1f}ms ({page_count} pages)")

    # 4. Load ComicInfo.xml
    start = time.time()
    comic_info = comic.comic_info
    timings['metadata'] = time.time() - start
    print(f"✅ Load metadata:     {timings['metadata']*1000:.1f}ms")

    # 5. Extract cover image
    start = time.time()
    cover_image = comic.extract_page_as_image(0)
    timings['extract_cover'] = time.time() - start
    print(f"✅ Extract cover:     {timings['extract_cover']*1000:.1f}ms")

    # 6. Generate thumbnails
    if cover_image:
        covers_dir = get_covers_dir()
        start = time.time()
        jpeg_ok, webp_ok = generate_dual_thumbnails(cover_image, covers_dir, file_hash)
        timings['thumbnails'] = time.time() - start
        print(f"✅ Generate thumbs:   {timings['thumbnails']*1000:.1f}ms")
    else:
        print("❌ No cover image")
        timings['thumbnails'] = 0

    comic.close()

    # Summary
    total = sum(timings.values())
    print(f"\n{'='*60}")
    print(f"TOTAL TIME:          {total*1000:.1f}ms ({total:.3f}s)")
    print(f"\nBreakdown:")
    for step, duration in sorted(timings.items(), key=lambda x: x[1], reverse=True):
        pct = (duration / total * 100) if total > 0 else 0
        print(f"  {step:20s} {duration*1000:6.1f}ms ({pct:5.1f}%)")

    return timings, total


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python profile_scan.py <comic_file.cbz>")
        print("\nExample:")
        print("  python profile_scan.py /path/to/comic.cbz")
        return

    comic_path = Path(sys.argv[1])

    if not comic_path.exists():
        print(f"❌ File not found: {comic_path}")
        return

    if not is_comic_file(comic_path):
        print(f"❌ Not a comic file: {comic_path}")
        return

    profile_single_comic(comic_path)


if __name__ == "__main__":
    main()
