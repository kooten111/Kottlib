#!/usr/bin/env python3
"""
Test Comic Loader

Demonstrates loading and extracting information from comic files.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from scanner import open_comic, is_comic_file


def test_comic_file(file_path: Path):
    """Test loading a single comic file"""
    print(f"\n{'='*60}")
    print(f"Testing: {file_path.name}")
    print(f"{'='*60}\n")

    # Check if it's a comic file
    if not is_comic_file(file_path):
        print(f"❌ Not a supported comic file format")
        return

    # Open the comic
    with open_comic(file_path) as comic:
        if comic is None:
            print(f"❌ Failed to open comic")
            return

        print(f"✅ Successfully opened comic")
        print(f"\nFormat: {file_path.suffix.upper()}")
        print(f"Pages: {comic.page_count}")

        # Show first few pages
        print(f"\nFirst 5 pages:")
        for i, page in enumerate(comic.pages[:5]):
            size_kb = page.size / 1024 if page.size else 0
            print(f"  {i+1}. {page.filename} ({size_kb:.1f} KB)")

        # Check for ComicInfo.xml
        if comic.comic_info:
            info = comic.comic_info
            print(f"\n📖 Comic Metadata (from ComicInfo.xml):")
            if info.title:
                print(f"  Title: {info.title}")
            if info.series:
                print(f"  Series: {info.series}")
            if info.number:
                print(f"  Issue: #{info.number}")
            if info.writer:
                print(f"  Writer: {info.writer}")
            if info.publisher:
                print(f"  Publisher: {info.publisher}")
            if info.year:
                print(f"  Year: {info.year}")
        else:
            print(f"\nℹ️  No ComicInfo.xml found")

        # Try to extract cover
        print(f"\n📷 Extracting cover...")
        cover_data = comic.get_cover()
        if cover_data:
            print(f"  ✅ Cover extracted ({len(cover_data)} bytes)")
        else:
            print(f"  ❌ Failed to extract cover")


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python test_comic_loader.py <comic_file.cbz>")
        print("\nExample:")
        print("  python test_comic_loader.py /path/to/comic.cbz")
        return

    file_path = Path(sys.argv[1])

    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return

    test_comic_file(file_path)


if __name__ == "__main__":
    main()
