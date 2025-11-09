# YACLib Enhanced - Architecture Update 2025

## Current Status (As of 2025-11-09)

### Implemented Features

#### Phase 4: Web UI ✅ **COMPLETE**
- Modern SvelteKit Interface with Tailwind CSS
- Comic Reader with basic keyboard shortcuts
- Library Browser (grid/list views)
- Continue Reading functionality
- Favorites system
- Search with autocomplete
- Admin Dashboard
- Dark/Light theme
- Responsive design

#### Reader Features (Partially Implemented)
- ✅ Page-by-page viewing
- ✅ Keyboard shortcuts (Arrow keys, Space, F, S, Esc, 1-9)
- ✅ Fit modes (fit-width, fit-height, original)
- ✅ Reading modes (single, double, continuous)
- ✅ Reading direction (LTR, RTL for manga)
- ✅ Full-screen mode
- ✅ Settings persistence (localStorage)
- ✅ Page preloading
- ✅ Auto-hide controls
- ⚠️ Mouse navigation zones (needs enhancement)
- ⚠️ Middle-click menu (not implemented)
- ⚠️ Page Up/Down navigation (not implemented)

---

## Planned Improvements

### 1. Hierarchical Tree Navigation (Priority: HIGH)

#### Current Implementation
- **File**: [webui/src/lib/components/layout/Sidebar.svelte](../webui/src/lib/components/layout/Sidebar.svelte)
- **Structure**: Generic collapsible sidebar with slot content
- **Issue**: Not designed for hierarchical folder tree

#### Planned Changes

**New Component**: `LibraryTree.svelte`

```
Library
├── Comics
│   ├── Batman
│   │   └── Nightowls
│   │       └── Batman Vol. 1 The Court of Owls (The New 52).cbz
│   ├── Superman
│   │   └── ...
├── Manga
│   ├── One Piece
│   │   └── ...
```

**Features**:
- Recursive folder tree rendering
- Click-to-expand/collapse folders
- Click folder name to filter main view
- Active state highlighting
- No icons (text-only tree)
- Lazy-loading of folder contents
- Breadcrumb sync with tree state

**API Changes Required**:
- `GET /api/v2/libraries/{libraryId}/tree` - Get full folder hierarchy
- `GET /api/v2/libraries/{libraryId}/folders/{folderId}/tree` - Get subtree

**Backend Changes**:
```python
# src/api/routers/folders.py
@router.get("/libraries/{library_id}/tree")
async def get_folder_tree(library_id: int, max_depth: int = 5):
    """
    Return nested folder structure for library
    Format:
    {
        "id": 1,
        "name": "Library",
        "type": "library",
        "children": [
            {
                "id": 2,
                "name": "Comics",
                "type": "folder",
                "parent_id": 1,
                "comic_count": 150,
                "children": [...]
            }
        ]
    }
    """
    pass
```

**Implementation Steps**:
1. Create recursive folder query in backend
2. Build `LibraryTree.svelte` component
3. Integrate with `Sidebar.svelte`
4. Add click handlers for filtering
5. Implement expand/collapse state (localStorage persistence)
6. Remove icon dependencies

---

### 2. Context-Aware Continue Reading (Priority: MEDIUM)

#### Current Implementation
- **File**: [webui/src/routes/continue-reading/+page.svelte](../webui/src/routes/continue-reading/+page.svelte)
- **Behavior**: Global continue reading list across all libraries
- **Issue**: Not context-aware to current folder/library

#### Planned Changes

**New Behavior**:
- If viewing "Library" level → Show all in-progress from that library
- If viewing "Comics/Batman" folder → Show only Batman in-progress
- If viewing root → Show global continue reading

**API Changes**:
```python
# src/api/routers/reading.py
@router.get("/continue-reading")
async def get_continue_reading(
    library_id: Optional[int] = None,
    folder_id: Optional[int] = None,
    user_id: Optional[int] = None
):
    """
    Get continue reading list filtered by context
    - No params: Global list
    - library_id: Library-scoped
    - folder_id: Folder-scoped (recursive)
    """
    pass
```

**Frontend Changes**:
- Add context detection to continue reading component
- Create mini continue reading widget for sidebar
- Update query params based on current route

---

### 3. Search UI Fixes (Priority: HIGH)

#### Issues Identified
1. **Icon positioning**: Search icon appears under searchbar
2. **Transparent autocomplete**: Dropdown has transparency issues

#### Current Implementation
- **File**: [webui/src/lib/components/common/SearchAutocomplete.svelte](../webui/src/lib/components/common/SearchAutocomplete.svelte)
- **Lines**: 278-287 (icon positioning), 306-318 (dropdown styling)

#### Fixes Required

**CSS Changes** ([SearchAutocomplete.svelte:278-287](../webui/src/lib/components/common/SearchAutocomplete.svelte#L278-L287)):
```css
.search-icon {
    position: absolute;
    left: 0.75rem;
    top: 50%;
    transform: translateY(-50%);
    width: 1.25rem;
    height: 1.25rem;
    color: var(--color-text-secondary);
    pointer-events: none;
    z-index: 1; /* Add this */
}
```

**Dropdown Background** ([SearchAutocomplete.svelte:306-318](../webui/src/lib/components/common/SearchAutocomplete.svelte#L306-L318)):
```css
.search-dropdown {
    position: absolute;
    top: calc(100% + 0.5rem);
    left: 0;
    right: 0;
    background: var(--color-secondary-bg); /* Ensure solid color */
    background: #242424; /* Fallback solid color */
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
    max-height: 400px;
    overflow-y: auto;
    z-index: 100;
    backdrop-filter: none; /* Remove if present */
}
```

---

### 4. Advanced Search Page (Priority: MEDIUM)

#### New Page
**Route**: `/search/advanced`
**File**: Create `webui/src/routes/search/advanced/+page.svelte`

#### Features

**Filter Options**:
- **Tags**: Multi-select tag filter
- **Libraries**: Select one or multiple libraries
- **Reading Status**: Unread, In Progress, Completed
- **Series**: Filter by series name
- **Year**: Range slider (e.g., 2010-2024)
- **Publisher**: Dropdown
- **Genre**: Multi-select
- **File Type**: CBZ, CBR, CB7, PDF

**Sort Options**:
- Title (A-Z, Z-A)
- Recently Added
- Recently Read
- Year (Newest, Oldest)
- File Size
- Page Count

**View Options**:
- Grid (small, medium, large thumbnails)
- List (compact, detailed)
- Cover flow

**API Endpoint**:
```python
# src/api/routers/search.py
@router.get("/search/advanced")
async def advanced_search(
    query: Optional[str] = None,
    library_ids: Optional[List[int]] = None,
    tags: Optional[List[str]] = None,
    reading_status: Optional[str] = None,
    series: Optional[str] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    publisher: Optional[str] = None,
    genres: Optional[List[str]] = None,
    file_types: Optional[List[str]] = None,
    sort_by: str = "title",
    sort_order: str = "asc",
    page: int = 1,
    limit: int = 50
):
    """
    Advanced search with multiple filters
    Returns paginated results with metadata
    """
    pass
```

---

### 5. Comic Reader Enhancements (Priority: HIGH)

#### Current Implementation
- **Main Reader**: [webui/src/routes/comic/[libraryId]/[comicId]/read/+page.svelte](../webui/src/routes/comic/[libraryId]/[comicId]/read/+page.svelte)
- **Page Viewer**: [webui/src/lib/components/reader/PageViewer.svelte](../webui/src/lib/components/reader/PageViewer.svelte)
- **Settings**: [webui/src/lib/components/reader/ReaderSettings.svelte](../webui/src/lib/components/reader/ReaderSettings.svelte)

#### 5.1 Enhanced Fit Modes ✅ (Already Implemented)

Current fit modes are already implemented:
- Fit Width ✅
- Fit Height ✅
- Original Size ✅

**Verification**: [ReaderSettings.svelte:48-83](../webui/src/lib/components/reader/ReaderSettings.svelte#L48-L83)

---

#### 5.2 Continuous Scroll (Webtoon Mode) - Priority: HIGH

**Current**: Continuous mode exists but needs enhancement for webtoon-style vertical scrolling

**Required Changes**:

**New Settings**:
```javascript
// src/lib/stores/reader.js
{
    readingMode: 'continuous', // existing
    continuousScrollDirection: 'vertical', // new: 'vertical' | 'horizontal'
    continuousPageGap: 10, // new: gap in pixels between pages
    continuousAutoAdvance: true, // new: auto-mark page as read when scrolled past
}
```

**Per-Library/Series Defaults**:
```python
# Database schema addition
# src/database/models.py

class LibrarySettings:
    library_id: int
    default_reading_mode: str  # 'single', 'double', 'continuous'
    default_scroll_direction: str  # 'vertical', 'horizontal'
    default_fit_mode: str
    # ...

class SeriesSettings:
    series_name: str
    library_id: int
    reading_mode_override: Optional[str]
    scroll_direction_override: Optional[str]
    # ...
```

**API Endpoints**:
```python
# Save/retrieve library-specific defaults
GET  /api/v2/libraries/{library_id}/reader-settings
PUT  /api/v2/libraries/{library_id}/reader-settings

# Save/retrieve series-specific overrides
GET  /api/v2/series/{series_name}/reader-settings
PUT  /api/v2/series/{series_name}/reader-settings
```

**Frontend Implementation**:
- Update `PageViewer.svelte` to render vertical scroll container
- Implement IntersectionObserver for auto-page-advance
- Add settings UI for continuous scroll preferences
- Load library/series defaults on reader mount
- Allow user override (session-only or permanent)

---

#### 5.3 Keyboard Navigation Enhancement

**Current**: Arrow keys, Space, F, S, Esc, 1-9 ✅

**Missing**: Page Up/Down

**Add to Reader** ([read/+page.svelte](../webui/src/routes/comic/[libraryId]/[comicId]/read/+page.svelte)):
```javascript
function handleKeydown(e) {
    // ... existing code ...

    case 'PageDown':
        e.preventDefault();
        if (readingDirection === 'rtl') {
            previousPage();
        } else {
            nextPage();
        }
        break;
    case 'PageUp':
        e.preventDefault();
        if (readingDirection === 'rtl') {
            nextPage();
        } else {
            previousPage();
        }
        break;
    case 'Home':
        e.preventDefault();
        goToPage(0);
        break;
    case 'End':
        e.preventDefault();
        goToPage(totalPages - 1);
        break;
}
```

---

#### 5.4 Mouse Navigation Zones

**Current**: Basic click navigation exists

**Enhancement Required**: Three-zone click detection

**Implementation**:

```javascript
// PageViewer.svelte
function handlePageClick(e) {
    const { clientX } = e;
    const { left, width } = e.currentTarget.getBoundingClientRect();
    const clickPosition = (clientX - left) / width;

    const leftZone = 0.33;
    const rightZone = 0.67;

    if (clickPosition < leftZone) {
        // Left third: Previous page
        if (readingDirection === 'rtl') {
            nextPage();
        } else {
            previousPage();
        }
    } else if (clickPosition > rightZone) {
        // Right third: Next page
        if (readingDirection === 'rtl') {
            previousPage();
        } else {
            nextPage();
        }
    } else {
        // Middle third: Toggle menu
        toggleReaderMenu();
    }
}
```

**Visual Feedback**:
- Add hover zones with CSS (subtle overlay)
- Show cursor icons (←, menu, →)

```css
.page-viewer {
    cursor: url('data:image/svg+xml,...'), auto; /* Custom cursors per zone */
}
```

---

#### 5.5 Reader Menu (Middle-Click) - NEW COMPONENT

**Create**: `webui/src/lib/components/reader/ReaderMenu.svelte`

**Features**:
- Page jump (input or slider)
- Chapter/Volume navigation (if metadata available)
- Quick settings (fit mode, reading direction)
- Info panel (current page, total pages, chapter title)

**Component Structure**:
```svelte
<script>
    export let currentPage;
    export let totalPages;
    export let chapters = []; // Array of chapter metadata
    export let onPageChange;
    export let onChapterChange;
    export let show = false;
</script>

{#if show}
<div class="reader-menu-overlay" on:click={() => show = false}>
    <div class="reader-menu" on:click|stopPropagation>
        <!-- Page Navigator -->
        <div class="menu-section">
            <h3>Jump to Page</h3>
            <input type="number" min="1" max={totalPages} bind:value={currentPage} />
            <input type="range" min="0" max={totalPages - 1} bind:value={currentPage} />
            <span>{currentPage + 1} / {totalPages}</span>
        </div>

        <!-- Chapter Navigator -->
        {#if chapters.length > 0}
        <div class="menu-section">
            <h3>Chapters</h3>
            <ul class="chapter-list">
                {#each chapters as chapter}
                <li on:click={() => onChapterChange(chapter.startPage)}>
                    {chapter.name} (Page {chapter.startPage})
                </li>
                {/each}
            </ul>
        </div>
        {/if}

        <!-- Quick Settings -->
        <div class="menu-section">
            <h3>Quick Settings</h3>
            <!-- Fit mode buttons, reading direction toggle -->
        </div>
    </div>
</div>
{/if}
```

**Trigger**:
- Middle click on page
- Click center zone of page
- Keyboard shortcut: `M`

---

### 6. Database Schema Updates

#### New Tables

```sql
-- Library-specific reader defaults
CREATE TABLE library_reader_settings (
    library_id INTEGER PRIMARY KEY,
    default_reading_mode TEXT DEFAULT 'single',
    default_fit_mode TEXT DEFAULT 'fit-width',
    default_scroll_direction TEXT DEFAULT 'vertical',
    default_reading_direction TEXT DEFAULT 'ltr',
    FOREIGN KEY (library_id) REFERENCES library(id) ON DELETE CASCADE
);

-- Series-specific overrides
CREATE TABLE series_reader_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_name TEXT NOT NULL,
    library_id INTEGER NOT NULL,
    reading_mode_override TEXT,
    fit_mode_override TEXT,
    scroll_direction_override TEXT,
    reading_direction_override TEXT,
    UNIQUE(series_name, library_id),
    FOREIGN KEY (library_id) REFERENCES library(id) ON DELETE CASCADE
);

-- Chapter metadata (for reader menu navigation)
CREATE TABLE comic_chapters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comic_id INTEGER NOT NULL,
    chapter_number INTEGER,
    chapter_name TEXT,
    start_page INTEGER NOT NULL,
    end_page INTEGER NOT NULL,
    FOREIGN KEY (comic_id) REFERENCES comic(id) ON DELETE CASCADE
);
```

---

## Implementation Priority

### Phase 1: Critical UX Fixes (Week 1)
1. ✅ Document current architecture
2. Fix search UI issues (icon positioning, transparent dropdown)
3. Implement hierarchical tree navigation
4. Enhance mouse navigation zones

### Phase 2: Reader Enhancements (Week 2)
1. Add Page Up/Down keyboard support
2. Create ReaderMenu component (middle-click menu)
3. Enhance continuous scroll mode for webtoons
4. Implement library/series reader defaults

### Phase 3: Search & Discovery (Week 3)
1. Create advanced search page
2. Implement context-aware continue reading
3. Add filter/sort capabilities to advanced search

### Phase 4: Backend & Database (Week 4)
1. Create folder tree API endpoints
2. Add library/series reader settings tables
3. Implement advanced search API
4. Add chapter metadata extraction

---

## Updated Technology Stack

### Frontend (No Changes)
- **Framework**: SvelteKit 2.x
- **Language**: JavaScript (ESM)
- **UI**: Tailwind CSS
- **Icons**: Lucide Svelte
- **State**: Svelte stores + TanStack Query
- **Build**: Vite

### Backend (No Changes)
- **Framework**: FastAPI
- **Language**: Python 3.11+
- **Database**: SQLite (SQLAlchemy ORM)
- **File Processing**: rarfile, zipfile, Pillow

---

## File Structure Updates

```diff
webui/src/
├── lib/
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Navbar.svelte
│   │   │   ├── Sidebar.svelte
+│   │   │   └── LibraryTree.svelte          # NEW: Hierarchical tree
│   │   ├── reader/
│   │   │   ├── PageViewer.svelte
│   │   │   ├── ReaderControls.svelte
│   │   │   ├── ReaderSettings.svelte
+│   │   │   └── ReaderMenu.svelte           # NEW: Middle-click menu
│   │   └── common/
│   │       └── SearchAutocomplete.svelte   # FIX: Icon & transparency
│   └── api/
+│       ├── folders.js                      # NEW: Tree API
+│       └── reader-settings.js              # NEW: Reader defaults API
├── routes/
│   ├── search/
│   │   ├── +page.svelte
+│   │   └── advanced/                       # NEW: Advanced search
+│   │       └── +page.svelte
```

---

## Migration Notes

### Breaking Changes
- None (all changes are additive)

### Database Migrations
```bash
# Create new tables
python tools/migrations/add_reader_settings_tables.py

# Extract chapter metadata from existing comics
python tools/migrations/extract_chapter_metadata.py
```

### Config Changes
No config changes required. All new features are opt-in.

---

## Testing Checklist

### Tree Navigation
- [ ] Folder tree loads correctly
- [ ] Click to expand/collapse works
- [ ] Click folder filters main view
- [ ] Active state highlighting works
- [ ] Tree state persists across refreshes
- [ ] No icons displayed

### Search Fixes
- [ ] Search icon displays correctly (not under bar)
- [ ] Autocomplete dropdown is fully opaque
- [ ] Results are clickable
- [ ] Keyboard navigation works

### Reader Enhancements
- [ ] Page Up/Down navigates correctly
- [ ] Mouse zones work (left=prev, right=next, middle=menu)
- [ ] Middle-click menu appears centered
- [ ] Page jump works
- [ ] Chapter navigation works (if metadata available)
- [ ] Continuous scroll works vertically
- [ ] Library defaults apply on reader load
- [ ] Series overrides take precedence

### Advanced Search
- [ ] All filters work independently
- [ ] Combined filters work correctly
- [ ] Sort options apply
- [ ] Pagination works
- [ ] Results match filter criteria

---

## Performance Considerations

### Tree Navigation
- Lazy-load folder contents (don't fetch entire tree upfront)
- Cache tree structure in memory (invalidate on scan)
- Use virtual scrolling for large trees (1000+ folders)

### Continuous Scroll
- Use IntersectionObserver for page visibility tracking
- Unload off-screen images to save memory
- Preload only N pages ahead/behind
- Implement variable-height virtual scrolling for webtoons

### Advanced Search
- Add database indexes on frequently filtered fields
- Implement full-text search (SQLite FTS5)
- Cache common filter combinations
- Use pagination (max 100 results per page)

---

## Future Enhancements (Post-2025)

### Reader
- Pinch-to-zoom on mobile
- Swipe gestures
- Panel detection (for zoom-to-panel)
- AI upscaling for low-res pages
- Read-aloud with text extraction

### Organization
- Drag-and-drop file management
- Batch metadata editing
- Auto-series detection with ML
- Duplicate detection

### Social
- Reading lists sharing
- User reviews/ratings
- Activity feed

---

## Documentation Updates Required

- [ ] Update [README.md](../README.md) with new features
- [ ] Update [YACLIB_API.md](YACLIB_API.md) with new endpoints
- [ ] Create [READER_GUIDE.md](READER_GUIDE.md) for users
- [ ] Update [ARCHITECTURE.md](ARCHITECTURE.md) (merge this document)

---

**Last Updated**: 2025-11-09
**Status**: Planning Complete, Implementation Pending
**Estimated Completion**: 4 weeks (Phase 1-4)
