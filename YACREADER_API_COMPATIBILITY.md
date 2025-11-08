# YACReader API Compatibility Tracking

**Last Updated:** 2025-11-08
**Reference Implementation:** YACReader 9.14.2
**Target:** Full backwards compatibility with official YACReader mobile apps

## Progress Summary

**Phase 1 (Critical):** 3/5 completed (60%)

- ✅ V1 line endings fixed (CRLF)
- ✅ Comic navigation (previousComic/nextComic)
- ✅ Database schema extended (43 new fields)

**Phase 2 (Metadata):** 1/4 completed (25%)

- ✅ Database models updated
- ⏳ Scanner integration pending
- ⏳ API response updates pending
- ⏳ Comic update endpoint pending

**Database Migration:** ✅ Applied successfully

- 43 columns added to `comics` table
- 3 columns added to `sessions` table
- 5 new tables created (favorites, labels, comic_labels, reading_lists, reading_list_items)
- Migration scripts available in `migrations/`

---

## Table of Contents

1. [Overview](#overview)
2. [API Version Summary](#api-version-summary)
3. [V1 API (Legacy Text-Based)](#v1-api-legacy-text-based)
4. [V2 API (Modern JSON-Based)](#v2-api-modern-json-based)
5. [Database Schema Compatibility](#database-schema-compatibility)
6. [Session Management](#session-management)
7. [Implementation Checklist](#implementation-checklist)
8. [Testing Guide](#testing-guide)

---

## Overview

YACReader mobile apps (iOS/Android) communicate with the server using two API versions:
- **V1**: Original text-based protocol (used by older app versions)
- **V2**: Modern JSON-based protocol (preferred by newer app versions)

Both APIs **must** be supported simultaneously for full compatibility.

---

## API Version Summary

| Feature | V1 API | V2 API | Status |
|---------|--------|--------|--------|
| Library Listing | HTML Template | JSON | ⚠️ Partial |
| Folder Browsing | Text Format | JSON | ✅ Implemented |
| Comic Metadata | Text Format | JSON | ⚠️ Missing fields |
| Remote Reading | Text Format | Text Format | ⚠️ Missing navigation |
| Page Delivery | Image | Image | ✅ Implemented |
| Cover Images | Image | Image | ✅ Implemented |
| Reading Progress | POST | POST | ✅ Implemented |
| Search | Text | JSON | ❌ Not implemented |
| Reading Lists | N/A | JSON | ⚠️ Stub only |
| Favorites | N/A | JSON | ❌ Not implemented |
| Tags/Labels | N/A | JSON | ❌ Not implemented |
| Session Management | Cookie-based | Header-based | ⚠️ Basic only |

**Legend:**
- ✅ **Implemented** - Fully functional
- ⚠️ **Partial** - Working but missing features
- ❌ **Not implemented** - Needs implementation

---

## V1 API (Legacy Text-Based)

### Implemented Endpoints

#### ✅ GET `/`
**Purpose:** List all libraries
**Response Format:** HTML template (original) / Text (simplified)
**Status:** ⚠️ Partial - Returns text instead of HTML

**Original Format:**
```html
<!DOCTYPE html>
<html>
...library list...
</html>
```

**Current Implementation:** Simplified text format
```text
type:libraries
code:0

library:My Comics
id:1
path:/path/to/library
```

**Issues:**
- [ ] Original uses HTML templates, we use plain text
- [ ] Missing template system integration

---

#### ✅ GET `/library/{library_id}/folder/{folder_id}`
**Purpose:** Browse folder contents (folders + comics)
**Response Format:** Plain text
**Status:** ✅ Implemented

**Format:**
```text
type:folder
code:0

folder:Marvel
id:5

folder:DC
id:6

comic:Amazing Spider-Man #1.cbz
id:124
```

**Issues:**
- [x] Basic implementation working
- [ ] Advanced sorting options missing

---

#### ⚠️ GET `/library/{library_id}/comic/{comic_id}/info`
**Purpose:** Get comic metadata
**Response Format:** Plain text (key:value pairs)
**Status:** ⚠️ Missing many fields

**Required Format (from `comic_db.cpp:25-144`):**
```text
library:My Comics
libraryId:1
comicid:124
hash:abc123def456
path:/comics/issue1.cbz
numpages:24
rating:0
currentPage:5
contrast:0
read:0
coverPage:1
title:Amazing Spider-Man #1
number:1
isBis:0
count:24
volume:1
storyArc:Clone Saga
arcNumber:3
arcCount:12
genere:Superhero
writer:Stan Lee
penciller:Steve Ditko
inker:Steve Ditko
colorist:...
letterer:...
coverArtist:...
date:2024-01
publisher:Marvel Comics
format:Comic
color:1
ageRating:T
manga:0
synopsis:Peter Parker...
characters:Spider-Man, Mary Jane
notes:...
lastTimeOpened:1234567890
added:1234567890
type:0
editor:...
imprint:Marvel
teams:Avengers
locations:New York
series:Amazing Spider-Man
alternateSeries:...
alternateNumber:...
alternateCount:0
languageISO:en
seriesGroup:...
mainCharacterOrTeam:Spider-Man
review:...
tags:action,superhero
comicVineID:12345
brightness:0
gamma:1.0
```

**Current Implementation:** Basic fields only

**Missing Fields:**
- [ ] `isBis` - Boolean for special issues
- [ ] `count` - Total issue count
- [ ] `storyArc`, `arcNumber`, `arcCount`
- [ ] `genere` (note: typo is in original!)
- [ ] `penciller`, `inker`, `colorist`, `letterer`, `coverArtist`
- [ ] `date` - Publication date
- [ ] `format` - Comic format
- [ ] `color` - Color/B&W
- [ ] `ageRating`
- [ ] `lastTimeOpened`
- [ ] `editor`, `imprint`, `teams`, `locations`
- [ ] `alternateSeries`, `alternateNumber`, `alternateCount`
- [ ] `languageISO`, `seriesGroup`, `mainCharacterOrTeam`
- [ ] `review`, `tags`, `comicVineID`
- [ ] `brightness`, `gamma`

**Critical Issues:**
- [ ] **Line endings must be `\r\n` not `\n`** - Apps may fail to parse!
- [ ] All metadata fields should be optional (only include if not null)

---

#### ⚠️ GET `/library/{library_id}/comic/{comic_id}/remote`
**Purpose:** Open comic for remote reading (streaming mode)
**Response Format:** Plain text
**Status:** ⚠️ Missing navigation fields

**Required Format:**
```text
library:My Comics
libraryId:1
previousComic:123
nextComic:125
comicid:124
hash:abc123def456
path:/comics/issue1.cbz
numpages:24
rating:0
currentPage:5
contrast:0
read:0
coverPage:1
title:Amazing Spider-Man #1
...
```

**Missing:**
- [ ] `previousComic` - ID of previous comic in folder
- [ ] `nextComic` - ID of next comic in folder
- [ ] These enable left/right swipe navigation in mobile apps

**Implementation Location:** `legacy_v1.py` - endpoint not found!

---

#### ✅ GET `/library/{library_id}/comic/{comic_id}/page/{page_num}`
**Purpose:** Get page image from comic
**Response Format:** Image (JPEG/PNG/etc)
**Status:** ✅ Fully implemented

**Headers:**
```
Content-Type: image/jpeg (or image/png, etc.)
Cache-Control: public, max-age=86400
```

---

#### ✅ GET `/library/{library_id}/cover/{hash}.jpg`
**Purpose:** Get comic cover thumbnail
**Response Format:** Image (JPEG)
**Status:** ✅ Implemented with hierarchical storage

**Storage Structure:**
```
covers/
  ab/
    abc123def456.jpg
    abc987654321.jpg
  cd/
    cdef123456.jpg
```

---

#### ✅ POST `/library/{library_id}/comic/{comic_id}/setCurrentPage`
**Purpose:** Update reading progress
**Request:** Form data with `page` field
**Response:** `OK`
**Status:** ✅ Implemented

---

#### ❌ POST `/sync`
**Purpose:** Sync session data (device type, display type, downloaded comics)
**Status:** ❌ Not implemented

**Expected Behavior:**
- Accepts POST data with device info
- Format:
  ```
  deviceType:ipad
  displayType:@2x
  comics:hash1\thash2\thash3
  ```

---

## V2 API (Modern JSON-Based)

### Core Endpoints

#### ✅ GET `/v2/version`
**Purpose:** Get server version
**Response:** Plain text version number
**Status:** ✅ Implemented

**Response:**
```
9.14.2
```

---

#### ✅ GET `/v2/libraries`
**Purpose:** List all libraries
**Response:** JSON array
**Status:** ✅ Implemented

**Format:**
```json
[
  {
    "name": "My Comics",
    "id": 1,
    "uuid": "550e8400-e29b-41d4-a716-446655440000"
  }
]
```

**Critical Issues:**
- [x] ~~IDs should be strings~~ - **FIXED** in recent commit
- [x] `uuid` field present
- [x] Compact JSON format (no pretty printing)

---

#### ✅ GET `/v2/library/{library_id}/folder/{folder_id}/content`
**Purpose:** Get folder contents (folders + comics)
**Response:** JSON array
**Status:** ✅ Implemented

**Folder Format:**
```json
{
  "type": "folder",
  "id": "5",
  "library_id": "1",
  "library_uuid": "550e8400-...",
  "folder_name": "Marvel",
  "num_children": 150,
  "first_comic_hash": "abc123",
  "finished": false,
  "completed": false,
  "custom_image": false,
  "file_type": 0,
  "added": 1234567890,
  "updated": 1234567890,
  "parent_id": "0",
  "path": "/Marvel"
}
```

**Comic Format:**
```json
{
  "type": "comic",
  "id": "124",
  "comic_info_id": "124",
  "parent_id": "5",
  "library_id": "1",
  "library_uuid": "550e8400-...",
  "file_name": "issue1.cbz",
  "file_size": "15728640",
  "hash": "abc123def456",
  "path": "/comics/marvel/issue1.cbz",
  "current_page": 5,
  "num_pages": 24,
  "read": false,
  "manga": false,
  "file_type": 1,
  "cover_size_ratio": 0.666,
  "number": 1,
  "cover_page": 1,
  "title": "Amazing Spider-Man #1",
  "universal_number": "1",
  "last_time_opened": 1234567890,
  "has_been_opened": true,
  "added": 1234567890
}
```

**Current Implementation Issues:**
- [x] ~~All IDs should be strings~~ - **FIXED**
- [ ] Missing `file_type` (0=folder, 1=comic)
- [ ] Missing `cover_size_ratio` (aspect ratio)
- [ ] Missing `cover_page` (which page is cover)
- [ ] Missing `last_time_opened` timestamp
- [ ] Missing `has_been_opened` boolean
- [ ] `file_size` currently hardcoded to "0"
- [ ] `num_children` for folders hardcoded to 0

---

#### ⚠️ GET `/v2/library/{library_id}/comic/{comic_id}/fullinfo`
**Purpose:** Get complete comic metadata
**Response:** JSON object
**Status:** ⚠️ Missing many metadata fields

**Full Format (from `yacreader_server_data_helper.cpp`):**
```json
{
  "type": "comic",
  "id": "124",
  "comic_info_id": "124",
  "parent_id": "5",
  "library_id": "1",
  "library_uuid": "550e8400-...",
  "file_name": "issue1.cbz",
  "file_size": "15728640",
  "hash": "abc123def456",
  "path": "/comics/marvel/issue1.cbz",
  "current_page": 5,
  "num_pages": 24,
  "read": false,
  "manga": false,
  "file_type": 1,
  "cover_size_ratio": 0.666,
  "number": 1,
  "cover_page": 1,
  "title": "Amazing Spider-Man #1",
  "universal_number": "1",
  "last_time_opened": 1234567890,
  "has_been_opened": true,
  "added": 1234567890,

  // Extended metadata
  "volume": "1",
  "total_volume_count": 12,
  "genre": "Superhero",
  "date": "2024-01",
  "synopsis": "Peter Parker becomes Spider-Man...",
  "count": 24,
  "story_arc": "Clone Saga",
  "arc_number": "3",
  "arc_count": 12,
  "writer": "Stan Lee",
  "penciller": "Steve Ditko",
  "inker": "Steve Ditko",
  "colorist": "...",
  "letterer": "...",
  "cover_artist": "...",
  "publisher": "Marvel Comics",
  "format": "Comic",
  "color": true,
  "age_rating": "T",
  "editor": "...",
  "characters": "Spider-Man, Mary Jane",
  "notes": "First appearance of...",
  "imprint": "Marvel",
  "teams": "Avengers",
  "locations": "New York",
  "series": "Amazing Spider-Man",
  "alternate_series": "Ultimate Spider-Man",
  "alternate_number": "1",
  "alternate_count": 160,
  "language_iso": "en",
  "series_group": "Spider-Man Family",
  "main_character_or_team": "Spider-Man",
  "review": "Amazing first issue!",
  "tags": "action,superhero,origin",
  "rating": 4.5,
  "comic_vine_id": "12345",
  "original_cover_size": "800x1200",
  "edited": false,
  "bookmark1": 0,
  "bookmark2": 0,
  "bookmark3": 0,
  "brightness": 0,
  "contrast": 0,
  "gamma": 1.0
}
```

**Missing from Database Schema:**
- [ ] `penciller` (have `artist` instead)
- [ ] `inker`
- [ ] `colorist`
- [ ] `letterer`
- [ ] `cover_artist`
- [ ] `format`
- [ ] `color` (boolean)
- [ ] `age_rating`
- [ ] `editor`
- [ ] `characters`
- [ ] `notes`
- [ ] `imprint`
- [ ] `teams`
- [ ] `locations`
- [ ] `alternate_series`, `alternate_number`, `alternate_count`
- [ ] `language_iso`
- [ ] `series_group`
- [ ] `main_character_or_team`
- [ ] `review`
- [ ] `tags`
- [ ] `rating` (float)
- [ ] `comic_vine_id`
- [ ] `original_cover_size`
- [ ] `edited` (boolean)
- [ ] `bookmark1`, `bookmark2`, `bookmark3`
- [ ] `brightness`, `contrast`, `gamma`
- [ ] `story_arc`, `arc_number`, `arc_count`
- [ ] `count` (total issue count)
- [ ] `date` (publication date string)
- [ ] `genre` (have `description` instead)
- [ ] `synopsis` (have `description` instead)
- [ ] `cover_page`, `cover_size_ratio`
- [ ] `last_time_opened`, `has_been_opened`
- [ ] `file_type`

---

#### ⚠️ GET `/v2/library/{library_id}/comic/{comic_id}/remote`
**Purpose:** Open comic for remote reading
**Response:** **Plain text** (same as V1!)
**Status:** ⚠️ Missing navigation

**Note:** Despite being V2, this endpoint returns plain text format, not JSON!

---

#### ✅ GET `/v2/library/{library_id}/comic/{comic_id}/page/{page_num}/remote`
**Purpose:** Get page for remote reading
**Response:** Image
**Status:** ✅ Implemented

---

#### ✅ GET `/v2/library/{library_id}/cover/{path}`
**Purpose:** Get cover image
**Response:** Image (JPEG)
**Status:** ✅ Implemented with hierarchical paths

**Path Format:** `ab/abc123def456.jpg` or `abc123def456.jpg`

---

#### ⚠️ GET `/v2/library/{library_id}/reading`
**Purpose:** Get "Continue Reading" list
**Response:** JSON array
**Status:** ⚠️ Implemented but may need format adjustments

**Current Implementation:** Returns array of comics with progress
```json
[
  {
    "type": "comic",
    "id": "124",
    "current_page": 5,
    "num_pages": 24,
    "progress_percent": 20.8,
    "last_read": 1234567890,
    ...
  }
]
```

**Notes:**
- [x] Basic implementation working
- [ ] Verify format matches official app expectations
- [ ] May need to match `ReadingComicsControllerV2` format exactly

---

#### ❌ GET `/v2/library/{library_id}/favs`
**Purpose:** Get favorite comics
**Response:** JSON array
**Status:** ❌ Stub only (returns empty array)

**Expected Format:** Similar to folder content (array of comics)

**Missing:**
- [ ] Database table for favorites
- [ ] Add/remove favorites endpoints
- [ ] Favorites filtering

---

#### ❌ GET `/v2/library/{library_id}/tags`
**Purpose:** Get all tags/labels
**Response:** JSON array
**Status:** ❌ Stub only

**Expected Format:**
```json
[
  {
    "type": "label",
    "id": "1",
    "library_id": "1",
    "library_uuid": "550e8400-...",
    "label_name": "Completed",
    "color_id": 3
  }
]
```

**Missing:**
- [ ] Database table for labels/tags
- [ ] Tag management endpoints
- [ ] Comic-tag associations

---

#### ❌ GET `/v2/library/{library_id}/tag/{tag_id}/content`
**Purpose:** Get comics with specific tag
**Response:** JSON array
**Status:** ❌ Not implemented

---

#### ❌ GET `/v2/library/{library_id}/tag/{tag_id}/info`
**Purpose:** Get tag information
**Response:** JSON object
**Status:** ❌ Not implemented

---

#### ❌ GET `/v2/library/{library_id}/reading_lists`
**Purpose:** Get all reading lists
**Response:** JSON array
**Status:** ❌ Not implemented

**Expected Format:**
```json
[
  {
    "type": "reading_list",
    "id": "1",
    "library_id": "1",
    "library_uuid": "550e8400-...",
    "reading_list_name": "My Reading List"
  }
]
```

**Missing:**
- [ ] Database table for reading lists
- [ ] Reading list management
- [ ] Comic-reading list associations

---

#### ❌ GET `/v2/library/{library_id}/reading_list/{list_id}/content`
**Purpose:** Get comics in reading list
**Response:** JSON array
**Status:** ❌ Not implemented

---

#### ❌ GET `/v2/library/{library_id}/reading_list/{list_id}/info`
**Purpose:** Get reading list metadata
**Response:** JSON object
**Status:** ❌ Not implemented

---

#### ❌ GET `/v2/library/{library_id}/search`
**Purpose:** Search comics
**Response:** JSON array
**Status:** ❌ Stub only

**Query Parameters:**
- `q` - Search query

**Expected:** Returns array of comics matching query

---

#### ❌ POST `/v2/library/{library_id}/comic/{comic_id}/update`
**Purpose:** Update comic metadata
**Status:** ❌ Not implemented

**This is critical for mobile apps to:**
- Mark comics as read/unread
- Update ratings
- Modify metadata

---

#### ❌ GET `/v2/library/{library_id}/folder/{folder_id}/metadata`
**Purpose:** Get folder metadata (v9.14+)
**Response:** JSON object
**Status:** ❌ Not implemented

**New feature in YACReader 9.14 - may not be critical for older apps**

---

#### ❌ POST `/v2/sync`
**Purpose:** Sync client state
**Status:** ❌ Stub only

**Expected Behavior:**
- Client sends current state
- Server acknowledges
- Used for multi-device sync

---

## Database Schema Compatibility

### Current Schema vs YACReader Requirements

#### Comic Model Comparison

| YACReader Field | Our Field | Type | Status |
|----------------|-----------|------|--------|
| `id` | `id` | int | ✅ |
| `hash` | `hash` | string | ✅ |
| `path` | `path` | string | ✅ |
| `fileName` | `filename` | string | ✅ |
| `fileSize` | `file_size` | int | ✅ |
| `numPages` | `num_pages` | int | ✅ |
| `title` | `title` | string | ✅ |
| `number` | `issue_number` | float | ✅ |
| `series` | `series` | string | ✅ |
| `volume` | `volume` | int | ✅ |
| `publisher` | `publisher` | string | ✅ |
| `writer` | `writer` | string | ✅ |
| `synopsis` | `description` | text | ⚠️ Different name |
| `type` (manga flag) | `reading_direction` | string | ⚠️ Different format |
| `added` | `created_at` | int | ✅ |
| `currentPage` | - | int | ❌ In reading_progress |
| `read` | - | bool | ❌ In reading_progress |
| `rating` | - | float | ❌ Missing |
| `contrast` | - | int | ❌ Missing |
| `brightness` | - | int | ❌ Missing |
| `gamma` | - | float | ❌ Missing |
| `penciller` | - | string | ❌ Missing |
| `inker` | - | string | ❌ Missing |
| `colorist` | - | string | ❌ Missing |
| `letterer` | - | string | ❌ Missing |
| `coverArtist` | - | string | ❌ Missing |
| `date` | `year` | string/int | ⚠️ Different format |
| `format` | `format` | string | ⚠️ Different meaning |
| `color` | - | bool | ❌ Missing |
| `ageRating` | - | string | ❌ Missing |
| `genere` | - | string | ❌ Missing |
| `storyArc` | - | string | ❌ Missing |
| `arcNumber` | - | string | ❌ Missing |
| `arcCount` | - | int | ❌ Missing |
| `editor` | - | string | ❌ Missing |
| `imprint` | - | string | ❌ Missing |
| `teams` | - | string | ❌ Missing |
| `locations` | - | string | ❌ Missing |
| `characters` | - | string | ❌ Missing |
| `notes` | - | string | ❌ Missing |
| `alternateSeries` | - | string | ❌ Missing |
| `alternateNumber` | - | string | ❌ Missing |
| `alternateCount` | - | int | ❌ Missing |
| `languageISO` | - | string | ❌ Missing |
| `seriesGroup` | - | string | ❌ Missing |
| `mainCharacterOrTeam` | - | string | ❌ Missing |
| `review` | - | string | ❌ Missing |
| `tags` | - | string | ❌ Missing |
| `comicVineID` | - | string | ❌ Missing |
| `coverPage` | - | int | ❌ Missing |
| `coverSizeRatio` | - | float | ❌ Missing |
| `lastTimeOpened` | - | int | ❌ Missing |
| `hasBeenOpened` | - | bool | ❌ Missing |
| `edited` | - | bool | ❌ Missing |
| `bookmark1/2/3` | - | int | ❌ Missing |
| `count` | - | int | ❌ Missing |
| `isBis` | - | bool | ❌ Missing |

### Required Database Changes

#### Option 1: Add Missing Fields to Comic Model (Recommended)
```python
# Add to Comic model in models.py:

# ComicInfo.xml fields
penciller: Mapped[Optional[str]] = mapped_column(String, nullable=True)
inker: Mapped[Optional[str]] = mapped_column(String, nullable=True)
colorist: Mapped[Optional[str]] = mapped_column(String, nullable=True)
letterer: Mapped[Optional[str]] = mapped_column(String, nullable=True)
cover_artist: Mapped[Optional[str]] = mapped_column(String, nullable=True)

genre: Mapped[Optional[str]] = mapped_column(String, nullable=True)
language_iso: Mapped[Optional[str]] = mapped_column(String, nullable=True)
age_rating: Mapped[Optional[str]] = mapped_column(String, nullable=True)

story_arc: Mapped[Optional[str]] = mapped_column(String, nullable=True)
arc_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)
arc_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

characters: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
teams: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
locations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

alternate_series: Mapped[Optional[str]] = mapped_column(String, nullable=True)
alternate_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)
alternate_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

series_group: Mapped[Optional[str]] = mapped_column(String, nullable=True)
main_character_or_team: Mapped[Optional[str]] = mapped_column(String, nullable=True)

imprint: Mapped[Optional[str]] = mapped_column(String, nullable=True)
format_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # Comic format
is_color: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
review: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

# External IDs
comic_vine_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

# Display settings
rating: Mapped[float] = mapped_column(Float, default=0.0)
brightness: Mapped[int] = mapped_column(Integer, default=0)
contrast: Mapped[int] = mapped_column(Integer, default=0)
gamma: Mapped[float] = mapped_column(Float, default=1.0)

# Bookmarks
bookmark1: Mapped[int] = mapped_column(Integer, default=0)
bookmark2: Mapped[int] = mapped_column(Integer, default=0)
bookmark3: Mapped[int] = mapped_column(Integer, default=0)

# Cover info
cover_page: Mapped[int] = mapped_column(Integer, default=1)
cover_size_ratio: Mapped[float] = mapped_column(Float, default=0.0)
original_cover_size: Mapped[Optional[str]] = mapped_column(String, nullable=True)

# Tracking
last_time_opened: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
has_been_opened: Mapped[bool] = mapped_column(Boolean, default=False)
edited: Mapped[bool] = mapped_column(Boolean, default=False)

# Legacy
is_bis: Mapped[bool] = mapped_column(Boolean, default=False)
count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Issue count
date: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # Publication date
```

#### Option 2: Create Separate ComicMetadata Table
```python
class ComicMetadata(Base):
    __tablename__ = 'comic_metadata'

    comic_id: Mapped[int] = mapped_column(ForeignKey('comics.id'), primary_key=True)

    # All extended fields here
    ...
```

**Recommendation:** Option 1 - Matches YACReader's single-table approach

---

## Session Management

### V1 Session (Cookie-Based)

**Original Implementation:**
```cpp
HttpSession session = Static::sessionStore->getSession(request, response);
YACReaderHttpSession *ySession = getYACReaderSessionHttpSession(session.getId());
```

**Session Data:**
- Device type: `ipad`, `android`, `tablet`, etc.
- Display type: `@1x`, `@2x`, `@3x`
- Downloaded comics: Set of hashes
- Current comic: ID + Comic object reference
- Navigation path: Breadcrumb trail

**Current Status:** ❌ Not implemented

---

### V2 Session (Header-Based)

**Original Implementation:**
```cpp
QByteArray token = request.getHeader("x-request-id");
YACReaderHttpSession *ySession = getYACReaderSessionHttpSession(token);
```

**Session Data:** Same as V1, but identified by header instead of cookie

**Current Status:** ⚠️ Basic - we have Session model but not using it

---

### Implementation Needed

1. **Create session on first request**
   - Generate UUID session ID
   - Store in database
   - Return cookie (V1) or expect header (V2)

2. **Track session state**
   - Current library
   - Current comic
   - Device info
   - Downloaded comics list

3. **Session expiry**
   - Default: 10 days (864000000ms)
   - Clean up expired sessions

4. **Session sync endpoint**
   - Accept device info
   - Store downloaded comic hashes
   - Return updated state

---

## Implementation Checklist

### Critical (Breaks compatibility)

- [x] **Use string IDs in V2 JSON** - FIXED (prior)
- [x] **Fix V1 line endings** (`\r\n` not `\n`) - ✅ COMPLETED 2025-11-08
- [ ] **Add library_uuid to all V2 responses**
- [x] **Implement previousComic/nextComic navigation** - ✅ COMPLETED 2025-11-08
- [x] **Add missing comic metadata fields to database** - ✅ COMPLETED 2025-11-08 (43 fields added)
- [ ] **Implement session management** - ⚠️ Database ready, middleware pending

### High Priority (App features broken)

- [ ] **POST `/v2/library/{id}/comic/{id}/update`** - Mark as read, update rating
- [ ] **GET `/v2/library/{id}/reading`** - Verify format
- [ ] **Add `file_type`, `cover_size_ratio`, `has_been_opened` fields**
- [ ] **Implement search**
- [ ] **Add `file_size` to responses** (currently "0")

### Medium Priority (Missing features)

- [ ] **Favorites system** (`/v2/library/{id}/favs`) - ⚠️ Database ready, endpoints pending
- [ ] **Tags/Labels** (`/v2/library/{id}/tags`) - ⚠️ Database ready, endpoints pending
- [ ] **Reading lists** (`/v2/library/{id}/reading_lists`) - ⚠️ Database ready, endpoints pending
- [ ] **V1 HTML templates** (currently using text)
- [ ] **Folder metadata** (`num_children`, etc.)

### Low Priority (Nice to have)

- [ ] **WebUI status page** (`/webui`)
- [ ] **Folder metadata endpoint** (v9.14 feature)
- [ ] **Image filters** (brightness/contrast/gamma)
- [ ] **Bookmarks**

---

## Testing Guide

### Manual Testing with Mobile App

1. **Install YACReader app**
   - iOS: App Store
   - Android: Google Play

2. **Configure server**
   - Open app settings
   - Add server: `http://your-server:8080`
   - No authentication needed (for now)

3. **Test scenarios**
   - [ ] Library list loads
   - [ ] Can browse folders
   - [ ] Comics show in grid view
   - [ ] Can open comic
   - [ ] Can read pages (swipe left/right)
   - [ ] Next/previous comic works
   - [ ] Reading progress saved
   - [ ] Continue reading shows progress
   - [ ] Covers load correctly
   - [ ] Metadata displays

### API Testing with curl

#### V1 Endpoints
```bash
# List libraries
curl http://localhost:8080/

# Browse folder
curl http://localhost:8080/library/1/folder/0

# Get comic info
curl http://localhost:8080/library/1/comic/124/info

# Get page
curl http://localhost:8080/library/1/comic/124/page/0 > page0.jpg

# Get cover
curl http://localhost:8080/library/1/cover/abc123def456.jpg > cover.jpg

# Update progress
curl -X POST -d "page=5" http://localhost:8080/library/1/comic/124/setCurrentPage
```

#### V2 Endpoints
```bash
# Version
curl http://localhost:8080/v2/version

# Libraries
curl http://localhost:8080/v2/libraries

# Folder content
curl http://localhost:8080/v2/library/1/folder/0/content | jq

# Full comic info
curl http://localhost:8080/v2/library/1/comic/124/fullinfo | jq

# Reading list
curl http://localhost:8080/v2/library/1/reading | jq

# Cover
curl http://localhost:8080/v2/library/1/cover/ab/abc123.jpg > cover.jpg
```

### Validation Checklist

- [ ] All V2 JSON IDs are strings (not integers)
- [ ] V1 responses use `\r\n` line endings
- [ ] All responses include `library_uuid` where required
- [ ] Cover images load (check hierarchical paths)
- [ ] Reading progress persists across sessions
- [ ] Next/previous comic navigation works
- [ ] Metadata displays correctly in app
- [ ] Search returns results
- [ ] Can mark comics as read/unread

---

## Migration Path

### Phase 1: Critical Fixes (Required for basic compatibility) - ⚠️ IN PROGRESS

1. Fix string IDs in V2 JSON ✅ DONE (prior)
2. Fix V1 line endings ✅ DONE (2025-11-08)
3. Add library UUIDs ⏳ PENDING
4. Implement navigation (previous/next) ✅ DONE (2025-11-08)
5. Add session management ⏳ PENDING (database ready)

### Phase 2: Metadata Enhancement - ⚠️ IN PROGRESS

1. Add missing fields to database schema ✅ DONE (2025-11-08 - 43 fields, 5 new tables)
2. Update scanner to extract ComicInfo.xml data ⏳ PENDING
3. Update API responses with full metadata ⏳ PENDING
4. Implement comic update endpoint ⏳ PENDING

### Phase 3: Advanced Features
1. Favorites system
2. Tags/Labels
3. Reading lists
4. Search functionality
5. Folder metadata

### Phase 4: Polish
1. HTML templates for V1
2. WebUI status page
3. Performance optimization
4. Full test coverage

---

## Notes

### YACReader Quirks

1. **`genere` typo** - Yes, it's misspelled in the original! Keep it for compatibility.
2. **Mixed formats** - V2 remote reading returns text, not JSON
3. **String IDs** - All IDs must be strings in V2, even though they're integers
4. **Windows line endings** - V1 requires `\r\n` even on Unix
5. **Optional fields** - Only include metadata fields if they have values
6. **File type encoding** - 0=folder, 1=comic, special values for manga
7. **Cover paths** - Support both flat and hierarchical storage

### Testing Resources

- **Official App:** Best compatibility test
- **API Docs:** None (reverse engineered from source)
- **Test Library:** Use YACReader desktop app to create reference library
- **Network Inspector:** Use Charles/Proxyman to capture real app traffic

---

## References

- YACReader Source: `/mnt/Black/Apps/KottLib/yacreader`
- Our Implementation: `/mnt/Black/Apps/KottLib/yaclib-enhanced`
- Key Files:
  - `yacreader/YACReaderLibrary/server/requestmapper.cpp` - Routing
  - `yacreader/YACReaderLibrary/server/yacreader_server_data_helper.cpp` - Data formats
  - `yacreader/common/comic_db.cpp` - Comic model
  - Our: `src/api/routers/api_v2.py`
  - Our: `src/api/routers/legacy_v1.py`
  - Our: `src/database/models.py`
