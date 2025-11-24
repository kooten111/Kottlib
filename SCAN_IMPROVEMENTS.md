# Scan Improvements

## Changes Made

### 1. Sequential Comic Processing (In-Order Commit)

**Problem:** Previously, comics were processed in parallel and completed in random order. If you interrupted the scan, you'd have incomplete comics in the database.

**Solution:** Modified `_process_comics_parallel()` to:
- Still process comics in parallel for speed (using ThreadPoolExecutor)
- BUT wait for each comic to fully complete IN ORDER before moving to the next
- This ensures comics are committed to the database sequentially

**Result:** If you interrupt a scan halfway:
- ✅ All processed comics are FULLY complete (metadata + thumbnails)
- ✅ You can immediately read the comics that were processed
- ✅ No partial/incomplete comics in the database

### 2. Automatic Series Table Rebuild

**Problem:** The series table could become out of sync with comics, causing the UI to show no content.

**Solution:** Added `_rebuild_series_table()` method that:
- Runs automatically after every scan
- Groups comics by series name
- Creates/updates series records
- Ensures series counts are accurate

**Result:**
- ✅ Series table is always in sync with comics
- ✅ UI will show all series immediately after scan
- ✅ No manual rebuild needed

## How It Works

### Scan Process Flow

```
1. File Discovery (fast, single-threaded)
   └─> Find all comic files and folders

2. Create Folders (database)
   └─> Create folder hierarchy

3. Process Comics (parallel, ordered commit)
   ├─> Submit all comics to thread pool
   ├─> Process in parallel (extract metadata, hash, etc.)
   └─> Wait for each comic IN ORDER before moving to next
       ├─> Commit comic to database
       └─> Generate thumbnails

4. Rebuild Series Table (automatic)
   └─> Group comics by series name
   └─> Create/update series records

5. Build Series Tree Cache (automatic)
   └─> Pre-compute folder/comic hierarchy
```

### Example: Interrupting a Scan

**Before changes:**
```
Scan 100 comics with 4 workers
- Comics complete in random order: 1, 5, 2, 8, 3...
- Interrupt at 50 comics
- Database has mix of complete and incomplete comics
- Can't reliably read any of them
```

**After changes:**
```
Scan 100 comics with 4 workers
- Comics complete in parallel but commit in order: 1, 2, 3, 4...
- Interrupt at 50 comics
- Database has comics 1-50 FULLY complete
- Can immediately read comics 1-50
- Comics 51-100 not in database yet (clean state)
```

## Usage

No changes needed to your workflow! Just run the scan as normal:

```bash
# Scan a library
source venv/bin/activate
python scripts/scan_library.py /path/to/library --workers 8

# Interrupt anytime with Ctrl+C
# All processed comics will be fully available
```

## Performance Notes

- Multi-threading still provides speed benefits (extracting metadata in parallel)
- Ordered commit adds minimal overhead
- Larger worker counts (6-8) recommended for large libraries
- Each comic is fully ingested before the next, making interrupts safe

## Technical Details

### Files Modified

1. `src/scanner/threaded_scanner.py`
   - Modified `_process_comics_parallel()` to use ordered commits
   - Added `_rebuild_series_table()` method
   - Integrated series rebuild into scan flow

### Database Transactions

Each comic is processed in its own transaction:

```python
with self.db.get_session() as session:
    create_comic(session, ...)  # Commit on exit

# Then generate thumbnails (after DB commit)
```

This ensures:
- Comic is in database before thumbnails are generated
- If thumbnail generation fails, comic is still usable
- Thumbnails are tied to comic hash, not database record
