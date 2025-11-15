# Series Scanner Metadata Migration

## What This Does

This migration adds scanner metadata fields to the `series` table, enabling the system to save metadata from series-level scanners (like AniList) directly to series records.

## Do I Need This Migration?

- **New Libraries/Fresh Install**: ✅ **NO** - The schema is already updated, you're good to go!
- **Existing Database**: ⚠️ **YES** - You need to run this migration to add the new fields

If you created your database before November 15, 2025, you need this migration. If you're creating a new library now, the fields are already included in the schema.

## New Fields Added

### Scanner Tracking
- `scanner_source` - Name of scanner used (e.g., "AniList")
- `scanner_source_id` - ID from external source
- `scanner_source_url` - URL to source page
- `scanned_at` - Timestamp of scan
- `scan_confidence` - Match confidence (0.0-1.0)

### Metadata Fields
- `writer` - Writer/author name(s)
- `artist` - Artist name(s)
- `genre` - Comma-separated genres
- `tags` - Comma-separated tags
- `status` - Publication status (e.g., "FINISHED", "RELEASING")
- `format` - Format type (e.g., "Manga", "Light Novel")
- `chapters` - Total chapter count
- `volumes` - Total volume count

## How to Apply

### Option 1: Using the Python Script

```bash
cd tools/migrations
python apply_series_scanner_migration.py ../../yaclib.db
```

### Option 2: Manual SQL Execution

```bash
sqlite3 yaclib.db < tools/migrations/005_add_series_scanner_metadata.sql
```

## Verification

After applying the migration, verify it worked:

```bash
sqlite3 yaclib.db "PRAGMA table_info(series);"
```

You should see all the new columns listed.

## What This Enables

Once this migration is applied, you can:

1. **Scan Series Metadata**: Visit a series page (e.g., `/series/1/Berserk`)
2. **Click "Scan Metadata"**: For libraries with series-level scanners
3. **View Results**: See matched metadata with confidence score
4. **Automatic Save**: Metadata is automatically saved to the database
5. **Persistent Data**: Scanned metadata persists across sessions

## Example Usage

1. Configure a library with AniList scanner in admin
2. Navigate to a series page
3. Click "Scan Metadata" button
4. Metadata from AniList is fetched and saved
5. Series page displays updated information
6. Metadata is preserved in the database

## Compatibility

- **SQLite**: Fully compatible
- **Existing Data**: No data loss - only adds new columns
- **Rollback**: Can be rolled back by dropping the added columns

## Safety

This migration is **safe** and **non-destructive**:
- Only adds new columns
- Doesn't modify existing data
- Can be run multiple times (idempotent)
- Includes verification step
