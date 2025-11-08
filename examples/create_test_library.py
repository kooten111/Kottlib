#!/usr/bin/env python3
"""
Create Test Comic Library

Generates a test library with sample CBZ files for testing.
"""

import zipfile
import sys
from pathlib import Path
from io import BytesIO
from PIL import Image

def create_comic_cbz(path: Path, title: str, series: str, issue: int, pages: int = 5):
    """Create a test CBZ file"""
    with zipfile.ZipFile(path, 'w') as zf:
        # Create cover and pages
        for i in range(pages):
            # Create a simple colored image
            colors = ['red', 'blue', 'green', 'yellow', 'orange', 'purple', 'pink']
            color = colors[i % len(colors)]
            img = Image.new('RGB', (200, 300), color=color)

            # Add some text to identify the page
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)

            img_bytes = BytesIO()
            img.save(img_bytes, format='JPEG')
            zf.writestr(f'{i+1:03d}.jpg', img_bytes.getvalue())

        # Add ComicInfo.xml
        comic_info_xml = f'''<?xml version="1.0"?>
<ComicInfo>
    <Title>{title}</Title>
    <Series>{series}</Series>
    <Number>{issue}</Number>
    <Year>2024</Year>
    <Publisher>Test Publisher</Publisher>
    <Writer>Test Writer</Writer>
    <PageCount>{pages}</PageCount>
</ComicInfo>'''
        zf.writestr('ComicInfo.xml', comic_info_xml)


def main():
    """Generate test library"""
    if len(sys.argv) < 2:
        print("Usage: python create_test_library.py <output_dir> [num_comics]")
        print("\nExample:")
        print("  python create_test_library.py /tmp/test_comics 50")
        return

    output_dir = Path(sys.argv[1])
    num_comics = int(sys.argv[2]) if len(sys.argv) > 2 else 20

    print(f"\nCreating test library at: {output_dir}")
    print(f"Number of comics: {num_comics}\n")

    # Create directory structure
    output_dir.mkdir(parents=True, exist_ok=True)

    marvel_dir = output_dir / "Marvel"
    dc_dir = output_dir / "DC"
    manga_dir = output_dir / "Manga"

    marvel_dir.mkdir(exist_ok=True)
    dc_dir.mkdir(exist_ok=True)
    manga_dir.mkdir(exist_ok=True)

    # Create Marvel comics
    marvel_count = num_comics // 3
    print(f"Creating {marvel_count} Marvel comics...")
    for i in range(1, marvel_count + 1):
        create_comic_cbz(
            marvel_dir / f"Spider-Man_{i:03d}.cbz",
            f"Spider-Man #{i}",
            "The Amazing Spider-Man",
            i,
            pages=10
        )
        print(f"  Created Spider-Man_{i:03d}.cbz")

    # Create DC comics
    dc_count = num_comics // 3
    print(f"\nCreating {dc_count} DC comics...")
    for i in range(1, dc_count + 1):
        create_comic_cbz(
            dc_dir / f"Batman_{i:03d}.cbz",
            f"Batman #{i}",
            "Batman",
            i,
            pages=12
        )
        print(f"  Created Batman_{i:03d}.cbz")

    # Create Manga
    manga_count = num_comics - marvel_count - dc_count
    print(f"\nCreating {manga_count} Manga comics...")
    for i in range(1, manga_count + 1):
        create_comic_cbz(
            manga_dir / f"One_Piece_{i:03d}.cbz",
            f"One Piece Vol. {i}",
            "One Piece",
            i,
            pages=15
        )
        print(f"  Created One_Piece_{i:03d}.cbz")

    print(f"\n{'='*60}")
    print(f"✅ Test library created successfully!")
    print(f"{'='*60}")
    print(f"Location: {output_dir}")
    print(f"Total comics: {marvel_count + dc_count + manga_count}")
    print(f"  Marvel: {marvel_count}")
    print(f"  DC: {dc_count}")
    print(f"  Manga: {manga_count}")
    print(f"\nTo scan this library:")
    print(f"  python examples/scan_library_fast.py {output_dir} 'Test Library' 4")
    print()


if __name__ == "__main__":
    main()
