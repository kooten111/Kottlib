# Scanner Library Integration Fix

## Issue

The scanner test interface was using hardcoded library types ("doujinshi", "manga", "comics") instead of showing the actual libraries from the database (Manga, Comics, Webtoon, X).

## Root Cause

The UI was using a hardcoded dropdown:
```svelte
<select bind:value={testLibraryType}>
  <option value="doujinshi">Doujinshi</option>
  <option value="manga">Manga</option>
  <option value="comics">Comics</option>
</select>
```

But the actual libraries in the database have:
- Manga (ID: 1)
- Comics (ID: 2)
- Webtoon (ID: 3)
- X (ID: 4)

## Solution

### 1. Updated UI to Use Actual Libraries

**Changed from:** Hardcoded library types
**Changed to:** Dynamic library dropdown from database

```svelte
<select bind:value={testLibraryId}>
  {#each libraryConfigs as config}
    <option value={config.library_id}>
      {config.library_name}
      {#if config.primary_scanner}
        (Scanner: {config.primary_scanner})
      {:else}
        (No scanner configured)
      {/if}
    </option>
  {/each}
</select>
```

**Features:**
- Shows actual library names
- Displays which scanner is configured for each library
- Shows "No scanner configured" for libraries without scanners
- Automatically selects first library with a configured scanner

### 2. Updated API Requests

**Single Scan Request:**
```javascript
// Before
{
  "query": "filename.cbz",
  "library_type": "doujinshi"
}

// After
{
  "query": "filename.cbz",
  "library_id": 4  // Uses actual library ID
}
```

**Bulk Scan Request:**
```javascript
// Before
{
  "queries": [...],
  "library_type": "doujinshi"
}

// After
{
  "queries": [...],
  "library_id": 4
}
```

### 3. Enhanced API Endpoints

#### Single Scan (`POST /v2/scanners/scan`)

Now supports both:
- `library_id` (preferred) - Uses library's configured scanner
- `library_type` (legacy) - Falls back to default scanners

**Process:**
1. If `library_id` provided → Look up library in database
2. Get scanner configuration from `library.settings['scanner']`
3. Use configured scanner or return error if not configured
4. If no library_id, fall back to legacy library_type

#### Bulk Scan (`POST /v2/scanners/scan/bulk`)

Same dual support:
- Primary: Uses `library_id` and library's scanner config
- Fallback: Uses `library_type` for backward compatibility

### 4. Default Scanner Type

For libraries without explicit type configuration, the scanner defaults to `'doujinshi'` when using nhentai scanner, since that's what nhentai provides.

This allows:
- Library "X" with nhentai scanner → Works with doujinshi content
- Library "Manga" (future) with AniList scanner → Would use manga type
- Library "Comics" (future) with ComicVine scanner → Would use comics type

## Files Changed

### Frontend
- `webui/src/routes/admin/scanners/+page.svelte`
  - Changed `testLibraryType` → `testLibraryId`
  - Replaced hardcoded dropdown with dynamic library list
  - Updated scan requests to use `library_id`

### Backend
- `src/api/routers/scanners.py`
  - Updated `scan_single()` to default to 'doujinshi' when needed
  - Updated `scan_bulk()` to support `library_id`
  - Added library configuration lookup for bulk scans

## Current State

### Libraries in Database
```
1. Manga          → No scanner configured
2. Comics         → No scanner configured
3. Webtoon        → No scanner configured
4. X              → nhentai scanner (40% threshold)
```

### Scanner Configuration

Only library "X" has a scanner configured:
- Primary Scanner: nhentai
- Confidence Threshold: 40%
- No fallback scanners

### Test Scanner UI

The test scanner now shows:
```
Library: [Dropdown ▼]
  - Manga (No scanner configured)
  - Comics (No scanner configured)
  - Webtoon (No scanner configured)
  - X (Scanner: nhentai)  ← Default selection

Filename to Scan: [text input]

[Run Scan]
```

## How to Configure Other Libraries

To configure scanners for the other libraries:

1. **Click "Configure" on a library** (e.g., Manga)
2. **Select a scanner** (currently only nhentai available)
3. **Adjust thresholds** if needed
4. **Save configuration**

The configuration will be saved to the library's `settings` JSON field in the database.

## Future Enhancements

When more scanners are added:

```
Manga library:
  - Primary: anilist
  - Fallback: jikan
  - Threshold: 50%

Comics library:
  - Primary: comicvine
  - Threshold: 60%

X library (doujinshi):
  - Primary: nhentai
  - Threshold: 40%
```

Each library can have its own scanner suited to its content type.

## Testing

### Test Single Scan

1. Go to http://localhost:5173/admin/scanners
2. Select library "X" (has nhentai configured)
3. Enter a doujinshi filename
4. Click "Run Scan"
5. See results with metadata

### Test Bulk Scan

1. Select library "X"
2. Paste multiple filenames (one per line)
3. Click "Scan All"
4. See batch results with statistics

### Expected Behavior

**If library has scanner configured:**
- Scan succeeds using configured scanner
- Uses library's confidence threshold

**If library has no scanner:**
- Error: "No scanner configured for library 'Manga'"
- User must configure a scanner first

---

**Version:** 1.1.2
**Fixed:** 2025-11-14
**Status:** ✅ Working
