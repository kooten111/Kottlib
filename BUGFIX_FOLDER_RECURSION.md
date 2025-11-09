# Bug Fix: Folder Navigation Issues
**Date:** 2025-11-09
**Issues:**
1. Clicking on folders causes infinite recursion/loop
2. Comics from wrong library appear in folders (cross-library contamination)

## Problem 1: Folder Recursion

### Description

When clicking on the "Spider-Gwen" folder (ID=1) in the Comics library, the mobile app would show the same folder again as a child of itself, creating an infinite recursion loop.

## Root Cause

The folder navigation logic in both V1 and V2 APIs was treating `folder_id <= 1` as the root folder:

```python
# BUGGY CODE (api_v2.py line 129)
if folder.parent_id == folder_id or (folder_id <= 1 and folder.parent_id is None):
```

### Why This Caused Recursion

1. Spider-Gwen folder has `id=1` and `parent_id=None` (it's a top-level folder)
2. When requesting `/library/1/folder/1` (Spider-Gwen's contents):
   - The condition `folder_id <= 1` evaluates to `True`
   - So it checks `folder.parent_id is None`
   - Spider-Gwen matches this condition!
   - Spider-Gwen is returned as a child of itself

This created the recursion: Spider-Gwen → Spider-Gwen → Spider-Gwen → ...

### The Confusion

The root folder should have `folder_id=0`, not `folder_id=1`. The condition `<= 1` was incorrectly trying to handle both:
- Folder ID 0 (actual root)
- Folder ID 1 (first real folder, NOT root)

## Solution

Changed the logic to explicitly check only for `folder_id == 0` as the root folder:

### api_v2.py (lines 128-137)

**Before:**
```python
for folder in folders:
    # Handle root folder (id=0 or id=1)
    if folder.parent_id == folder_id or (folder_id <= 1 and folder.parent_id is None):
```

**After:**
```python
for folder in folders:
    # Handle root folder (id=0 means show top-level folders with parent_id=None)
    # For other folders, show children where parent_id matches the requested folder_id
    if folder_id == 0:
        # Root level - show folders with no parent
        if folder.parent_id is not None:
            continue
    else:
        # Specific folder - show its children only
        if folder.parent_id != folder_id:
            continue
```

### api_v2.py comics section (lines 182-191)

**Before:**
```python
if folder_id > 1:
    # Normal folder
    comics = get_comics_in_folder(session, folder_id)
else:
    # Root folder (0 or 1) - get comics with no folder_id
```

**After:**
```python
if folder_id == 0:
    # Root folder (id=0) - get comics with no folder_id
    comics = session.query(Comic).filter_by(
        library_id=library_id,
        folder_id=None
    ).all()
else:
    # Specific folder - get its comics
    comics = get_comics_in_folder(session, folder_id)
```

### legacy_v1.py (lines 153-163)

Applied the same fix for consistency (V1 API was already mostly correct).

## Testing

Used the included [debug_folders.py](debug_folders.py) script to verify no circular references exist in the database:

```bash
$ /mnt/Black/Apps/KottLib/venv/bin/python debug_folders.py

Library: Comics (ID: 1)
  Folder   1: Spider-Gwen | Parent: None (ROOT)
✅ No folder relationship issues found

Library: Manga (ID: 2)
  Folder   2: Yuyushiki | Parent: None (ROOT)
  Folder   3: Yuusha ga Shinda | Parent: None (ROOT)
✅ No folder relationship issues found
```

## Expected Behavior After Fix

### Scenario 1: Browse root of library (folder_id=0)
- Shows: All top-level folders (parent_id=None)
- Shows: Comics with no folder assignment (folder_id=None)

### Scenario 2: Browse Spider-Gwen folder (folder_id=1)
- Shows: Child folders with parent_id=1 (none in this case)
- Shows: Comics with folder_id=1 (the Spider-Gwen comics)
- Does NOT show: Spider-Gwen folder itself

### Scenario 3: Browse any nested folder (folder_id=N where N>1)
- Shows: Child folders with parent_id=N
- Shows: Comics with folder_id=N
- Does NOT show: The folder itself

## Lessons Learned

1. **Always use exact equality checks for special IDs**
   - Use `folder_id == 0` for root
   - NOT `folder_id <= 1` or similar range checks

2. **Real folders start at ID=1**
   - ID 0 is reserved for "root" (virtual folder)
   - ID 1+ are actual folders in the filesystem

3. **Test with real data**
   - The bug only manifested because a real folder had ID=1
   - Unit tests with mock data might not have caught this

## Files Modified

- [src/api/routers/api_v2.py](src/api/routers/api_v2.py) - Lines 128-137, 182-191
- [src/api/routers/legacy_v1.py](src/api/routers/legacy_v1.py) - Lines 153-163
- [debug_folders.py](debug_folders.py) - New diagnostic script

---

## Problem 2: Cross-Library Comic Contamination

### Description

When browsing folders in different libraries, comics from the wrong library would appear:
- Opening folder ID=1 in the Manga library shows Spider-Gwen comics (from Comics library)
- Opening folder ID=2 in the Comics library would show Yuyushiki comics (from Manga library)
- Root folders show mixed content from different libraries

### Root Cause

The `get_comics_in_folder()` function in [database.py](src/database/database.py) only filtered by `folder_id`, not by `library_id`:

```python
# BUGGY CODE (database.py line 273)
def get_comics_in_folder(session: Session, folder_id: int) -> List[Comic]:
    """Get all comics in a folder"""
    return session.query(Comic).filter_by(folder_id=folder_id).all()
```

This caused folder IDs to collide across libraries:
- Comics library: Spider-Gwen folder has `folder_id=1, library_id=1`
- Manga library: (hypothetically) another folder could have `folder_id=1, library_id=2`
- Both would return ALL comics with `folder_id=1` regardless of library!

### Solution

Updated `get_comics_in_folder()` to accept an optional `library_id` parameter:

```python
# FIXED CODE (database.py lines 273-285)
def get_comics_in_folder(session: Session, folder_id: int, library_id: Optional[int] = None) -> List[Comic]:
    """
    Get all comics in a folder

    Args:
        session: Database session
        folder_id: ID of the folder
        library_id: Optional library ID to filter by (recommended to avoid cross-library issues)
    """
    query = session.query(Comic).filter_by(folder_id=folder_id)
    if library_id is not None:
        query = query.filter_by(library_id=library_id)
    return query.all()
```

### Files Modified

**database.py:**
- Line 273-285: Added `library_id` parameter to `get_comics_in_folder()`

**api_v2.py:**
- Line 191: Updated call to include `library_id=library_id`

**legacy_v1.py:**
- Line 169: Updated call to include `library_id=library_id`

### Expected Behavior After Fix

Each library now properly isolates its comics:
- Browsing Comics library folder ID=1 → Only shows Spider-Gwen comics from library_id=1
- Browsing Manga library folder ID=2 → Only shows Yuyushiki comics from library_id=2
- No cross-contamination between libraries

---

## Related Issues

These bugs were discovered during YACReader compatibility testing after implementing:
- File size reporting
- Library UUID inclusion
- Folder metadata (num_children)
- Session management

See [YACREADER_COMPATIBILITY_IMPROVEMENTS.md](YACREADER_COMPATIBILITY_IMPROVEMENTS.md) for the broader compatibility work.

## Summary

**Total bugs fixed:** 2
**Files modified:** 3
- [src/database/database.py](src/database/database.py)
- [src/api/routers/api_v2.py](src/api/routers/api_v2.py)
- [src/api/routers/legacy_v1.py](src/api/routers/legacy_v1.py)

Both issues stemmed from insufficient filtering:
1. **Folder recursion:** Not distinguishing folder_id=0 (root) from folder_id=1 (first real folder)
2. **Cross-library contamination:** Not filtering comics by library when querying folders

The fixes ensure proper isolation between libraries and correct folder hierarchy navigation.
