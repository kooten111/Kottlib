# Scanner Configuration UI - Implementation Complete

## Overview

The scanner system now includes a full configuration UI that allows you to manage which scanners are assigned to which libraries through the admin interface.

## What Was Added

### Backend Changes

#### 1. Database Integration (`src/api/routers/scanners.py`)

**New Imports:**
```python
from sqlalchemy.orm import Session
from src.database.session import get_db
from src.database.models import Library
```

**Updated Models:**
- `LibraryScannerConfig` - Now includes `library_path`
- `UpdateLibraryScannerConfig` - New model for configuration updates

**Modified Endpoints:**

##### GET `/v2/scanners/libraries`
- Now fetches **actual libraries from the database**
- Reads scanner configuration from `library.settings['scanner']` JSON field
- Returns all libraries with their current scanner settings

##### PUT `/v2/scanners/libraries/{library_id}/configure`
- **Validates** library exists in database
- **Validates** selected scanners are available
- **Saves configuration** to database in `library.settings['scanner']`
- **Persists** across server restarts

**Configuration Storage Format:**
```json
{
  "scanner": {
    "primary_scanner": "nhentai",
    "fallback_scanners": [],
    "confidence_threshold": 0.4,
    "fallback_threshold": 0.7
  }
}
```

### Frontend Changes

#### Configuration Modal (`webui/src/routes/admin/scanners/+page.svelte`)

**New Features:**

1. **Configure Button** on each library
   - Opens modal dialog for that library
   - Pre-fills current settings

2. **Primary Scanner Selection**
   - Dropdown with all available scanners
   - Shows scanner name and description
   - Required field

3. **Confidence Threshold Slider**
   - Visual slider (0-100%)
   - Real-time percentage display
   - Explanatory text about what it does

4. **Fallback Threshold Slider**
   - Visual slider (0-100%)
   - Recommended default: 70%
   - Controls when fallback scanners are used

5. **Fallback Scanner Checkboxes**
   - Multi-select checkboxes
   - Excludes primary scanner from options
   - Optional field

6. **Error Handling**
   - Validation errors displayed in modal
   - Network errors caught and shown
   - Form validation before submission

7. **Loading States**
   - "Saving..." indicator during save
   - Disabled buttons while processing
   - Prevents duplicate submissions

## How to Use

### 1. Access the Scanner Configuration

Navigate to: **http://localhost:5173/admin/scanners**

Scroll to the **Library Scanner Configuration** section.

### 2. Configure a Library

1. **Click "Configure"** button on any library

2. **Select Primary Scanner:**
   - Choose from dropdown (e.g., "nhentai")
   - This is the main scanner that will be used

3. **Adjust Confidence Threshold:**
   - Drag slider to set minimum confidence
   - Default: 40%
   - Lower = More results (may be less accurate)
   - Higher = Fewer results (more accurate)

4. **Adjust Fallback Threshold (optional):**
   - Controls when fallback scanners kick in
   - Default: 70%
   - If primary scanner confidence < this, try fallbacks

5. **Select Fallback Scanners (optional):**
   - Check additional scanners to try if primary fails
   - Currently only "nhentai" available
   - More scanners can be added in future

6. **Click "Save Configuration"**

### 3. Configuration is Saved

The configuration is immediately saved to the database and will persist across server restarts.

## Configuration Examples

### Example 1: Doujinshi Library with nhentai Only

```
Library: My Doujinshi Collection
Primary Scanner: nhentai
Confidence Threshold: 40%
Fallback Threshold: 70%
Fallback Scanners: (none)
```

**Behavior:**
- All files scanned with nhentai
- Accepts results with 40%+ confidence
- No fallback behavior

### Example 2: Manga Library (Future)

```
Library: Manga Collection
Primary Scanner: anilist
Confidence Threshold: 50%
Fallback Threshold: 70%
Fallback Scanners: jikan
```

**Behavior:**
- Try AniList first
- If confidence < 70%, also try Jikan
- Accept best result with 50%+ confidence

### Example 3: High Quality Only

```
Library: Premium Collection
Primary Scanner: nhentai
Confidence Threshold: 80%
Fallback Threshold: 90%
Fallback Scanners: (none)
```

**Behavior:**
- Only accept very high confidence matches (80%+)
- Very selective, fewer false positives

## Visual Guide

### Library Configuration Card

```
┌─────────────────────────────────────────────────────┐
│  My Doujinshi Collection                [Configure] │
│  /path/to/library                                   │
│                                                     │
│  Primary Scanner: nhentai                           │
│  Confidence Threshold: 40%                          │
│  Fallback Scanners: (none)                          │
└─────────────────────────────────────────────────────┘
```

### Configuration Modal

```
┌───────────────────────────────────────────────────┐
│ Configure Scanner for My Doujinshi Collection  ✕ │
├───────────────────────────────────────────────────┤
│                                                   │
│ Primary Scanner *                                 │
│ [nhentai - File-level scanner for doujinshi  ▼]  │
│                                                   │
│ Confidence Threshold: 40%                         │
│ ┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫  │
│ 0%            50%            100%                 │
│                                                   │
│ Fallback Threshold: 70%                           │
│ ┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫  │
│ 0%            70%            100%                 │
│                                                   │
│ Fallback Scanners (Optional)                      │
│ ☐ anilist - Manga metadata (planned)             │
│ ☐ jikan - Manga fallback (planned)               │
│                                                   │
├───────────────────────────────────────────────────┤
│                     [Cancel] [Save Configuration] │
└───────────────────────────────────────────────────┘
```

## Technical Details

### Database Schema

Scanner configuration is stored in the `libraries.settings` JSON column:

```sql
-- Example data in libraries table
UPDATE libraries
SET settings = json_set(
  COALESCE(settings, '{}'),
  '$.scanner',
  json_object(
    'primary_scanner', 'nhentai',
    'fallback_scanners', json_array(),
    'confidence_threshold', 0.4,
    'fallback_threshold', 0.7
  )
)
WHERE id = 1;
```

### API Request/Response

**Request:**
```bash
curl -X PUT http://localhost:8081/v2/scanners/libraries/1/configure \
  -H "Content-Type: application/json" \
  -d '{
    "primary_scanner": "nhentai",
    "fallback_scanners": [],
    "confidence_threshold": 0.4,
    "fallback_threshold": 0.7
  }'
```

**Response:**
```json
{
  "library_id": 1,
  "library_name": "My Doujinshi Collection",
  "library_path": "/path/to/library",
  "primary_scanner": "nhentai",
  "fallback_scanners": [],
  "confidence_threshold": 0.4,
  "fallback_threshold": 0.7
}
```

### Validation Rules

1. **Library must exist** - 404 if library_id not found
2. **Primary scanner required** - 400 if not provided
3. **Scanner must be available** - 400 if scanner not registered
4. **Thresholds must be 0.0-1.0** - Validated by Pydantic
5. **Fallback scanners must be available** - 400 if unknown scanner

## Backward Compatibility

The system maintains backward compatibility:

1. **Libraries without configuration**
   - Show "Not configured" warning
   - Still work with default scanner (if library_type provided)
   - Can be configured through UI

2. **Old scan endpoints**
   - `library_type` parameter still supported
   - Falls back to default scanner configuration
   - Gradual migration to library-based config

3. **Legacy scanner manager**
   - Still works for backward compatibility
   - Default configurations preserved
   - Future: migrate to database-only config

## Future Enhancements

### Planned Features

1. **Per-Library Scan History**
   - Track scan success rates per library
   - Show statistics in configuration

2. **Scanner Recommendations**
   - Suggest best scanner based on library content
   - Auto-configure new libraries

3. **Batch Configuration**
   - Configure multiple libraries at once
   - Copy configuration from one library to another

4. **Scanner-Specific Settings**
   - Different settings per scanner
   - Advanced options in modal

5. **Test Configuration**
   - Test button in modal
   - Run sample scan with new settings before saving

## Troubleshooting

### "Not configured" Warning

**Symptom:** Library shows "Not configured" in orange text

**Solution:** Click "Configure" and select a primary scanner

### Configuration Not Saving

**Symptom:** Modal closes but configuration not updated

**Solution:**
1. Check browser console for errors
2. Verify backend is running
3. Check database write permissions
4. Look at network tab for 4xx/5xx responses

### Scanner Not Available

**Symptom:** "Scanner 'xxx' not available" error

**Solution:**
1. Verify scanner is registered in scanner manager
2. Check `/v2/scanners/available` endpoint
3. Restart backend if scanner was recently added

### "No libraries found"

**Symptom:** Configuration section shows empty message

**Solution:**
1. Create a library first through main UI
2. Verify libraries exist in database
3. Check `/v2/scanners/libraries` endpoint returns data

## Testing the Feature

### 1. Verify Backend

```bash
# Check libraries endpoint
curl http://localhost:8081/v2/scanners/libraries

# Should return list of libraries
```

### 2. Configure a Library

1. Open http://localhost:5173/admin/scanners
2. Click "Configure" on a library
3. Select nhentai as primary scanner
4. Adjust thresholds
5. Save

### 3. Verify Configuration Saved

```bash
# Check library was updated
curl http://localhost:8081/v2/scanners/libraries

# Should show your configuration
```

### 4. Test Scanning

Use the test scanner tool on the same page to verify the configuration is being used.

## Files Modified

```
src/api/routers/scanners.py          (Enhanced with DB integration)
webui/src/routes/admin/scanners/+page.svelte  (Added configuration modal)
```

## Summary

Scanner configuration is now:
- ✅ Stored in database (persistent)
- ✅ Managed through web UI (user-friendly)
- ✅ Per-library (flexible)
- ✅ Validated (safe)
- ✅ Real-time (immediate effect)

You can now fully manage scanner assignments without editing code or config files!

---

**Version:** 1.1.0
**Last Updated:** 2025-11-14
