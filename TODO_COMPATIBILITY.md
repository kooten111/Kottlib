# YACReader Compatibility TODO

Quick reference checklist for achieving full backwards compatibility.
See [YACREADER_API_COMPATIBILITY.md](YACREADER_API_COMPATIBILITY.md) for detailed documentation.

---

## 🚨 CRITICAL (Must Fix for Basic Compatibility)

### Database Schema
- [ ] Add missing metadata fields to `Comic` model (see Phase 2 below)
- [ ] Add `library_uuid` generation if missing
- [ ] Migration script to update existing data

### API Response Format
- [x] ✅ **DONE** - Use string IDs in V2 JSON (not integers)
- [ ] Fix V1 line endings to `\r\n` (currently `\n`)
- [ ] Add `library_uuid` to all V2 responses that need it
- [ ] Add `file_size` (currently hardcoded to "0")
- [ ] Add `file_type` field (0=folder, 1=comic)
- [ ] Add `cover_size_ratio` field
- [ ] Add `has_been_opened` field
- [ ] Add `cover_page` field

### Navigation
- [ ] Add `previousComic` and `nextComic` to remote reading endpoints
  - V1: `/library/{id}/comic/{id}/remote`
  - V2: `/v2/library/{id}/comic/{id}/remote`
  - Need to get siblings from parent folder
  - Find current comic position
  - Return adjacent IDs

### Session Management
- [ ] Implement session creation on first request
- [ ] V1: Cookie-based sessions
- [ ] V2: `x-request-id` header-based sessions
- [ ] Store device type, display type
- [ ] Track downloaded comics
- [ ] Session expiry and cleanup

---

## ⚠️ HIGH PRIORITY (Core Features)

### Comic Update Endpoint
- [ ] `POST /v2/library/{id}/comic/{id}/update`
  - Mark as read/unread
  - Update rating
  - Update current page
  - Update metadata
  - Update image settings (brightness/contrast/gamma)
  - Update bookmarks

### Missing V1 Endpoints
- [ ] `GET /library/{id}/comic/{id}/remote` (may already exist, verify format)
- [ ] `POST /sync` - Session sync endpoint
- [ ] Fix `/` to return HTML template (currently returns text)

### Folder Metadata
- [ ] Calculate `num_children` for folders (currently 0)
- [ ] Get `first_comic_hash` for folder thumbnails
- [ ] Add `finished`, `completed` flags
- [ ] Add `custom_image` support

---

## 📊 MEDIUM PRIORITY (Feature Parity)

### Reading List (Continue Reading)
- [x] ✅ **DONE** - Basic implementation of `/v2/library/{id}/reading`
- [ ] Verify format matches official app expectations
- [ ] Test with real mobile app

### Search
- [ ] `GET /library/{id}/search` (V1)
- [ ] `GET /v2/library/{id}/search` (V2)
- [ ] Full-text search in comic metadata
- [ ] Search by series, writer, publisher, etc.
- [ ] Return results in correct format

### Favorites
- [ ] Database table for favorites
- [ ] `GET /v2/library/{id}/favs`
- [ ] `POST /v2/library/{id}/comic/{id}/favorite` (toggle)
- [ ] Add `favorite` field to comic responses

### Tags/Labels
- [ ] Database table for labels
- [ ] Database table for comic-label associations
- [ ] `GET /v2/library/{id}/tags`
- [ ] `GET /v2/library/{id}/tag/{id}/content`
- [ ] `GET /v2/library/{id}/tag/{id}/info`
- [ ] Tag management endpoints

### Reading Lists
- [ ] Database table for reading lists
- [ ] Database table for comic-reading list associations
- [ ] `GET /v2/library/{id}/reading_lists`
- [ ] `GET /v2/library/{id}/reading_list/{id}/content`
- [ ] `GET /v2/library/{id}/reading_list/{id}/info`
- [ ] `GET /v2/library/{id}/reading_list/{id}/comic/{id}/remote`
- [ ] Reading list management endpoints

---

## 📝 LOW PRIORITY (Nice to Have)

### WebUI
- [ ] `GET /webui` - Status page
- [ ] Show server info, libraries, statistics
- [ ] QR code for mobile app connection

### Advanced Features
- [ ] Folder metadata endpoint (v9.14 feature)
- [ ] Image filters (brightness/contrast/gamma) application
- [ ] Bookmark support
- [ ] ComicVine integration
- [ ] Multi-user support (currently single admin user)

---

## 📋 Detailed Task Breakdown

### Phase 1: Critical Fixes (Week 1)

#### Task 1.1: Database Schema Update
**File:** `src/database/models.py`

Add to `Comic` model:
```python
# Creator fields
penciller: Mapped[Optional[str]] = mapped_column(String, nullable=True)
inker: Mapped[Optional[str]] = mapped_column(String, nullable=True)
colorist: Mapped[Optional[str]] = mapped_column(String, nullable=True)
letterer: Mapped[Optional[str]] = mapped_column(String, nullable=True)
cover_artist: Mapped[Optional[str]] = mapped_column(String, nullable=True)

# Metadata fields
genre: Mapped[Optional[str]] = mapped_column(String, nullable=True)
language_iso: Mapped[Optional[str]] = mapped_column(String, nullable=True)
age_rating: Mapped[Optional[str]] = mapped_column(String, nullable=True)
format_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
is_color: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

# Story arc
story_arc: Mapped[Optional[str]] = mapped_column(String, nullable=True)
arc_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)
arc_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

# Additional info
characters: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
teams: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
locations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
imprint: Mapped[Optional[str]] = mapped_column(String, nullable=True)
notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
review: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

# Alternate series
alternate_series: Mapped[Optional[str]] = mapped_column(String, nullable=True)
alternate_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)
alternate_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

# Series info
series_group: Mapped[Optional[str]] = mapped_column(String, nullable=True)
main_character_or_team: Mapped[Optional[str]] = mapped_column(String, nullable=True)

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
count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
```

**Migration:**
```bash
# Create migration
alembic revision --autogenerate -m "Add YACReader compatibility fields"
alembic upgrade head
```

#### Task 1.2: Fix V1 Line Endings
**File:** `src/api/routers/legacy_v1.py`

Find/replace all:
- `"\n"` → `"\r\n"`
- `response_text += f"...` → `response_text += f"...\r\n"`

#### Task 1.3: Add Navigation to Remote Reading
**Files:**
- `src/api/routers/legacy_v1.py`
- `src/api/routers/api_v2.py`

Add to both `/remote` endpoints:
```python
# Get sibling comics in same folder
siblings = get_comics_in_folder(session, comic.folder_id)
sorted_siblings = sorted(siblings, key=lambda c: c.filename.lower())

# Find current position
current_index = next(
    (i for i, c in enumerate(sorted_siblings) if c.id == comic_id),
    None
)

if current_index is not None:
    if current_index > 0:
        response_text += f"previousComic:{sorted_siblings[current_index - 1].id}\r\n"
    if current_index < len(sorted_siblings) - 1:
        response_text += f"nextComic:{sorted_siblings[current_index + 1].id}\r\n"
```

#### Task 1.4: Update V2 Responses with Missing Fields
**File:** `src/api/routers/api_v2.py`

Update folder content response:
```python
{
    # ... existing fields ...
    "file_type": 1,  # Add this
    "cover_size_ratio": comic.cover_size_ratio if hasattr(comic, 'cover_size_ratio') else 0.0,
    "cover_page": comic.cover_page if hasattr(comic, 'cover_page') else 1,
    "has_been_opened": comic.has_been_opened if hasattr(comic, 'has_been_opened') else False,
    "last_time_opened": comic.last_time_opened if hasattr(comic, 'last_time_opened') else None,
}
```

#### Task 1.5: Implement Basic Session Management
**File:** `src/api/session.py` (new file)

```python
from fastapi import Request, Response
from typing import Optional
import uuid
import time

class SessionManager:
    def __init__(self, db):
        self.db = db

    def get_or_create_session(
        self,
        request: Request,
        response: Response,
        session_id: Optional[str] = None
    ) -> str:
        """Get existing session or create new one"""
        # V2: Check x-request-id header
        if not session_id:
            session_id = request.headers.get('x-request-id')

        # V1: Check cookie
        if not session_id:
            session_id = request.cookies.get('yacread_session')

        # Create new session
        if not session_id:
            session_id = str(uuid.uuid4())
            # Set cookie for V1 compatibility
            response.set_cookie(
                key='yacread_session',
                value=session_id,
                max_age=864000,  # 10 days
                httponly=True
            )

        # TODO: Store in database
        return session_id
```

---

### Phase 2: Metadata Enhancement (Week 2)

#### Task 2.1: Update Scanner to Extract ComicInfo.xml
**File:** `src/scanner/metadata_extractor.py`

Extract all ComicInfo.xml fields and map to database model.

#### Task 2.2: Update API Responses
**Files:**
- `src/api/routers/api_v2.py`
- `src/api/routers/legacy_v1.py`

Add all metadata fields to responses (only if not null).

#### Task 2.3: Implement Comic Update Endpoint
**File:** `src/api/routers/api_v2.py`

```python
@router.post("/library/{library_id}/comic/{comic_id}/update")
async def update_comic(
    library_id: int,
    comic_id: int,
    request: Request
):
    """Update comic metadata and reading state"""
    # Parse request body (could be JSON or form data)
    # Update comic in database
    # Return success
```

---

### Phase 3: Advanced Features (Week 3-4)

See detailed tasks in main compatibility document.

---

## Testing Checklist

### Manual Testing
- [ ] Install official YACReader iOS/Android app
- [ ] Add server connection
- [ ] Browse library
- [ ] Open comic and read
- [ ] Check navigation works
- [ ] Verify progress saves
- [ ] Test continue reading
- [ ] Check metadata display
- [ ] Test search
- [ ] Test favorites
- [ ] Test reading lists

### API Testing
- [ ] All V2 IDs are strings
- [ ] V1 line endings are correct
- [ ] Navigation links present
- [ ] Metadata fields populated
- [ ] Sessions persist
- [ ] Cover images load
- [ ] File sizes correct

### Performance Testing
- [ ] Large library (10,000+ comics)
- [ ] Concurrent users
- [ ] Mobile network conditions
- [ ] Cover loading speed

---

## Priority Order for Implementation

1. **Fix line endings** (30 minutes)
2. **Add database fields** (2 hours)
3. **Update API responses** (2 hours)
4. **Add navigation** (1 hour)
5. **Basic sessions** (2 hours)
6. **Comic update endpoint** (2 hours)
7. **Search** (4 hours)
8. **Favorites** (4 hours)
9. **Reading lists** (8 hours)
10. **Tags** (8 hours)

**Total Estimate:** ~33 hours for full compatibility

---

## Quick Wins

Start with these for maximum impact:
1. ✅ String IDs (already done!)
2. Fix line endings (30 min)
3. Add file_type/cover_size_ratio/has_been_opened (1 hour)
4. Add navigation (1 hour)

These 4 fixes will make the app mostly functional.
