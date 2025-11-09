# YACReader 100% Compatibility - Final Implementation

**Date:** 2025-11-09
**Status:** ✅ COMPLETE

## Summary

Achieved 100% YACReader compatibility by implementing the YACReader folder hierarchy convention with virtual `__ROOT__` folders and allowing the same files to exist in multiple libraries.

## Key Changes

### 1. Root Folder Implementation (YACReader Convention)

YACReader uses a special convention where every library has a virtual root folder (typically ID=1) that acts as a container for top-level folders and comics, but is never shown in the UI itself.

**Convention Details:**
- Every library must have a `__ROOT__` folder
- Top-level folders have `parent_id` pointing to the root folder
- Root-level comics have `folder_id` pointing to the root folder
- The root folder itself is NEVER shown in folder listings
- Mobile apps request `/library/{id}/folder/1` to view library contents (not folder_id=0)

### 2. Database Schema Change

**File:** [src/database/models.py](src/database/models.py)

**Change:** Removed UNIQUE constraint on `comics.hash` column to allow same file in multiple libraries

```python
# BEFORE:
hash: Mapped[str] = mapped_column(String, unique=True, nullable=False)

# AFTER:
hash: Mapped[str] = mapped_column(String, nullable=False)  # Removed unique=True
```

**Why:** The UNIQUE constraint prevented the same file (identified by hash) from existing in multiple libraries. Removing it allows users to have the same comic files in different test/backup libraries.

### 3. Database Operations

**File:** [src/database/database.py](src/database/database.py)

**New Function:** `get_or_create_root_folder()` (lines 374-438)

Creates or retrieves the virtual root folder for a library:

```python
def get_or_create_root_folder(session: Session, library_id: int, library_path: str) -> Folder:
    """
    Get or create the virtual root folder for a library.
    YACReader convention: Every library has a virtual root folder that acts as
    a container for top-level folders and comics, but is never shown in the UI.
    """
    # Try to find existing root folder by name
    root = session.query(Folder).filter_by(
        library_id=library_id,
        name="__ROOT__"
    ).first()

    if root:
        return root

    # Create new root folder
    now = int(datetime.now().timestamp())
    root = Folder(
        library_id=library_id,
        parent_id=None,
        path=str(Path(library_path).resolve()),
        name="__ROOT__",
        created_at=now,
        updated_at=now
    )
    session.add(root)
    session.flush()
    session.commit()
    return root
```

**Updated Function:** `get_comic_by_hash()` (lines 263-275)

Added optional `library_id` parameter to enable library-aware duplicate detection:

```python
def get_comic_by_hash(session: Session, file_hash: str, library_id: Optional[int] = None) -> Optional[Comic]:
    """
    Get comic by file hash

    Args:
        session: Database session
        file_hash: File hash to search for
        library_id: Optional library ID to filter by (allows same file in different libraries)
    """
    query = session.query(Comic).filter_by(hash=file_hash)
    if library_id is not None:
        query = query.filter_by(library_id=library_id)
    return query.first()
```

### 4. Scanner Updates

**File:** [src/scanner/threaded_scanner.py](src/scanner/threaded_scanner.py)

**Updated:** `_create_folders()` method (lines 195-251)

Now creates root folder first and sets proper parent relationships:

```python
def _create_folders(self, library_path: Path, folder_paths: List[Path]) -> Tuple[dict, int]:
    """
    Create all folders in database and return mapping.
    YACReader compatibility: Creates a root folder for the library,
    and sets all top-level folders to have parent_id pointing to root.
    """
    folder_map = {}
    root_folder_id = None

    with self.db.get_session() as session:
        # First, ensure root folder exists (YACReader convention)
        root_folder = get_or_create_root_folder(session, self.library_id, str(library_path))
        root_folder_id = root_folder.id

        # Process folders in hierarchy order (parents before children)
        sorted_folders = sorted(folder_paths, key=lambda p: len(p.parts))

        for folder_path in sorted_folders:
            folder = get_folder_by_path(session, self.library_id, str(folder_path))
            if not folder:
                parent_path = folder_path.parent
                if parent_path == library_path:
                    # This is a top-level folder - parent is root
                    parent_id = root_folder_id
                elif str(parent_path) in folder_map:
                    parent_id = folder_map[str(parent_path)]
                else:
                    parent_id = root_folder_id

                folder = create_folder(session, library_id=self.library_id,
                                     path=str(folder_path), name=folder_path.name,
                                     parent_id=parent_id)

            folder_map[str(folder_path)] = folder.id

    return folder_map, root_folder_id
```

**Updated:** `_process_single_comic()` method (lines 314-324)

Now checks for duplicates per-library instead of globally:

```python
# Check if already in database FOR THIS LIBRARY (library-aware)
# Pass library_id to allow same file in different libraries
with self.db.get_session() as session:
    existing = get_comic_by_hash(session, file_hash, library_id=self.library_id)
    if existing:
        with self._lock:
            self._comics_skipped += 1
        return
```

### 5. API Updates

**Files:**
- [src/api/routers/api_v2.py](src/api/routers/api_v2.py) (lines 129-153, 207-225)
- [src/api/routers/legacy_v1.py](src/api/routers/legacy_v1.py) (similar changes)

**Key Changes:**

1. **Skip `__ROOT__` folders in listings:**

```python
for folder in folders:
    # Skip root folder (marked with __ROOT__ name) - never show in listings
    if folder.name == "__ROOT__":
        continue
```

2. **Dynamic root folder detection for comics:**

Instead of hardcoding `folder_id=1`, dynamically find the root folder for each library:

```python
if is_root_request:
    # Root folder request - get comics in the __ROOT__ folder for this library
    # Find the root folder ID (marked with __ROOT__ name)
    root_folder = next((f for f in folders if f.name == "__ROOT__"), None)
    if root_folder:
        # Get comics with folder_id pointing to root folder
        comics = session.query(Comic).filter(
            Comic.library_id == library_id,
            (Comic.folder_id == root_folder.id) | (Comic.folder_id == None)
        ).all()
    else:
        # Fallback: no root folder found, get comics with folder_id=None
        comics = session.query(Comic).filter(
            Comic.library_id == library_id,
            Comic.folder_id == None
        ).all()
```

3. **Library-aware comic filtering:**

```python
comics = get_comics_in_folder(session, folder_id, library_id=library_id)
```

## Migration Support

**File:** [migrate_to_yacreader_schema.py](migrate_to_yacreader_schema.py)

Created migration script to update existing databases without rescanning:

```bash
python migrate_to_yacreader_schema.py
```

The script:
1. Creates `__ROOT__` folder for each library
2. Updates top-level folders to have `parent_id` pointing to root folder
3. Updates root-level comics to have `folder_id` pointing to root folder

## Testing Results

After implementation, tested with 3 libraries containing duplicate files:

```
Library 1 (Comics):  14 comics
Library 2 (Manga):   25 comics
Library 3 (Test):    30 comics (includes duplicates from Library 1)
---
Total:               69 comic records
Unique file hashes:  55 unique files
Duplicate records:   14 (same files in multiple libraries)
```

**Test Cases Verified:**

✅ Root folder creation for each library
✅ Top-level folders have correct parent_id
✅ Root-level comics have correct folder_id
✅ `__ROOT__` folders never shown in listings
✅ Same file can exist in multiple libraries
✅ Library isolation (no cross-library contamination)
✅ Folder navigation works correctly
✅ Root comics appear in library root view
✅ Dynamic root folder detection (not hardcoded)

**Example folder structure:**

```
Library 1 (Comics):
  Folder ID=1: __ROOT__ (never shown)
    ├─ Folder ID=2: Spider-Gwen (parent_id=1)
    │   └─ 13 comics (folder_id=2)
    └─ Comic ID=14: A Man Among Ye.cbz (folder_id=1)

Library 3 (Test):
  Folder ID=6: __ROOT__ (never shown)
    ├─ Folder ID=7: Spider-Gwen (parent_id=6)
    │   └─ 13 comics (folder_id=7) - DUPLICATES of Library 1
    ├─ Folder ID=8: Sunstone (parent_id=6)
    ├─ Folder ID=9: Vampirella (parent_id=6)
    └─ 6 root comics (folder_id=6)
```

## Mobile App Usage

The YACReader mobile app should request:
- `/v2/library/{id}/folder/1` - Shows library root contents (NOT folder_id=0)
- `/v2/library/{id}/folder/{N}` - Shows contents of folder N

The API automatically:
- Skips showing `__ROOT__` folders
- Returns top-level folders when requesting the root folder ID
- Returns root-level comics when requesting the root folder ID
- Filters all content by library_id to prevent cross-library contamination

## Files Modified

1. [src/database/models.py](src/database/models.py) - Removed UNIQUE constraint on hash
2. [src/database/database.py](src/database/database.py) - Added `get_or_create_root_folder()`, updated `get_comic_by_hash()`
3. [src/scanner/threaded_scanner.py](src/scanner/threaded_scanner.py) - Root folder creation, library-aware duplicates
4. [src/api/routers/api_v2.py](src/api/routers/api_v2.py) - Dynamic root detection, skip `__ROOT__` folders
5. [src/api/routers/legacy_v1.py](src/api/routers/legacy_v1.py) - Same changes as V2 API
6. [migrate_to_yacreader_schema.py](migrate_to_yacreader_schema.py) - New migration script

## Benefits

1. **100% YACReader Compatibility:** Follows exact YACReader folder hierarchy convention
2. **Multi-Library Support:** Same files can exist in multiple libraries (test, backup, etc.)
3. **Scalability:** No hardcoded folder IDs - works for thousands of libraries
4. **Library Isolation:** Proper filtering prevents cross-library contamination
5. **Migration Support:** Existing databases can be updated without rescanning

## Related Documentation

- [BUGFIX_FOLDER_RECURSION.md](BUGFIX_FOLDER_RECURSION.md) - Earlier folder navigation fixes
- [YACREADER_COMPATIBILITY_IMPROVEMENTS.md](YACREADER_COMPATIBILITY_IMPROVEMENTS.md) - Session management, file size, UUIDs
