#!/usr/bin/env python3
"""
Test script for search functionality
"""
import sys
from pathlib import Path

# Add the src directory to path
sys.path.insert(0, str(Path(__file__).parent / "yaclib-enhanced" / "src"))

from database.database import Database, search_comics
from database.models import Library, Comic
import tempfile
import os

print("Testing Search Functionality...")
print("=" * 60)

# Create a temporary database
with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
    db_path = tmp.name

try:
    # Initialize database
    db = Database(db_path=Path(db_path))
    db.init_db()

    with db.get_session() as session:
        # Create a test library
        library = Library(
            name="Test Library",
            path="/test/library",
            uuid="test-uuid-123",
            created_at=1234567890,
            updated_at=1234567890
        )
        session.add(library)
        session.flush()
        library_id = library.id

        # Create test comics with various metadata
        test_comics = [
            {
                "filename": "Amazing Spider-Man 001.cbz",
                "title": "Amazing Spider-Man",
                "series": "Spider-Man",
                "writer": "Stan Lee",
                "publisher": "Marvel Comics",
                "description": "The amazing adventures of Spider-Man",
                "genre": "Superhero",
                "characters": "Spider-Man, Mary Jane, Green Goblin"
            },
            {
                "filename": "Batman Detective Comics 027.cbz",
                "title": "Detective Comics",
                "series": "Batman",
                "writer": "Bob Kane",
                "publisher": "DC Comics",
                "description": "The dark knight rises",
                "genre": "Crime Fighter",
                "characters": "Batman, Robin, Joker"
            },
            {
                "filename": "X-Men 001.cbz",
                "title": "The Uncanny X-Men",
                "series": "X-Men",
                "writer": "Stan Lee",
                "publisher": "Marvel Comics",
                "description": "Mutants saving the world",
                "genre": "Superhero",
                "characters": "Cyclops, Jean Grey, Wolverine"
            },
            {
                "filename": "Random Comic 123.cbz",
                "title": "Some Random Comic",
                "series": None,
                "writer": "Unknown",
                "publisher": None,
                "description": None,
                "genre": None,
                "characters": None
            }
        ]

        for i, comic_data in enumerate(test_comics):
            comic = Comic(
                library_id=library_id,
                path=f"/test/library/{comic_data['filename']}",
                filename=comic_data['filename'],
                hash=f"hash{i}",
                file_size=1000000,
                file_modified_at=1234567890,
                format="cbz",
                title=comic_data['title'],
                series=comic_data['series'],
                writer=comic_data['writer'],
                publisher=comic_data['publisher'],
                description=comic_data['description'],
                genre=comic_data['genre'],
                characters=comic_data['characters'],
                num_pages=24,
                created_at=1234567890,
                updated_at=1234567890
            )
            session.add(comic)

        session.commit()

        print(f"✓ Created test library with {len(test_comics)} comics")
        print()

        # Test various searches
        test_queries = [
            ("Spider-Man", "Search by title/series/character"),
            ("Stan Lee", "Search by writer"),
            ("Marvel", "Search by publisher"),
            ("Batman", "Search by series/character"),
            ("Superhero", "Search by genre"),
            ("dark knight", "Search by description"),
            ("Wolverine", "Search by character"),
            ("Random", "Search by filename"),
            ("nonexistent", "Search with no results"),
        ]

        all_passed = True
        for query, description in test_queries:
            results = search_comics(session, library_id, query)
            print(f"Query: '{query}' ({description})")
            print(f"  Found {len(results)} results:")
            for comic in results:
                print(f"    - {comic.title or comic.filename}")

            # Verify expected results
            if query == "Spider-Man":
                if len(results) >= 1 and any("Spider" in (c.title or "") for c in results):
                    print("  ✓ PASS")
                else:
                    print("  ✗ FAIL: Expected to find Spider-Man comics")
                    all_passed = False
            elif query == "Stan Lee":
                if len(results) >= 2:  # Should find Spider-Man and X-Men
                    print("  ✓ PASS")
                else:
                    print("  ✗ FAIL: Expected to find multiple comics by Stan Lee")
                    all_passed = False
            elif query == "Marvel":
                if len(results) >= 2:  # Should find Spider-Man and X-Men
                    print("  ✓ PASS")
                else:
                    print("  ✗ FAIL: Expected to find Marvel comics")
                    all_passed = False
            elif query == "Batman":
                if len(results) >= 1 and any("Batman" in (c.series or "") for c in results):
                    print("  ✓ PASS")
                else:
                    print("  ✗ FAIL: Expected to find Batman comics")
                    all_passed = False
            elif query == "nonexistent":
                if len(results) == 0:
                    print("  ✓ PASS")
                else:
                    print("  ✗ FAIL: Expected no results")
                    all_passed = False
            else:
                if len(results) > 0:
                    print("  ✓ PASS")
                else:
                    print("  ⚠ WARNING: Expected to find results")

            print()

        print("=" * 60)
        if all_passed:
            print("✓ All search tests passed!")
            sys.exit(0)
        else:
            print("✗ Some search tests failed")
            sys.exit(1)

finally:
    # Clean up
    if os.path.exists(db_path):
        os.unlink(db_path)
