# YACLib Enhanced - Project Overview

## Executive Summary

**YACLib Enhanced** is a complete replacement for YACReaderLibrary Server, written in Python, that maintains 100% backward compatibility with existing YACReader mobile apps while adding powerful new features for both mobile and web users.

## Project Genesis

### Discovery Phase

1. **Reverse Engineered YACReaderLibrary Server Protocol**
   - Analyzed network traffic from mobile app
   - Discovered session-based HTTP API
   - Identified async comic loading behavior
   - Documented all endpoints and data formats

2. **Analyzed YACReader Source Code**
   - Cloned GitHub repository
   - Examined C++/Qt server implementation
   - **Key Discovery**: Mobile app is HTML-based (WebView)
   - Found server-side template system (`.tpl` files)
   - Identified complete control over mobile UI

3. **Key Insight**: Mobile app is essentially a browser that displays server-generated HTML
   - We have 100% control over the UI by controlling HTML output
   - Can implement any feature without modifying mobile apps
   - Complete replacement server is feasible

## Core Principles

### 1. Complete Replacement, Not a Proxy

**Decision**: Build from scratch in Python, replacing the C++/Qt server entirely.

**Why**:
- More control over features
- Modern async architecture
- Easier to extend and maintain
- Better performance optimization opportunities
- Still 100% compatible with mobile apps

### 2. Backward Compatibility First

**Requirement**: Existing YACReader mobile apps must work without modification.

**Implementation**:
- Implement legacy API v1 (text/HTML format)
- Maintain session cookie behavior
- Serve HTML templates compatible with mobile app
- Support existing URL structure

### 3. Per-Library Metadata Storage

**Decision**: Store metadata in `.yacreaderlibrary/` folder within each library root.

**Structure**:
```
/path/to/Library/
├── .yacreaderlibrary/
│   ├── library.ydb          # SQLite database (compatible with YACReader)
│   ├── id                   # Library UUID
│   ├── covers/              # Thumbnails
│   │   ├── {hash}.jpg       # JPEG for mobile
│   │   └── {hash}.webp      # WebP for web
│   └── custom_covers/       # User-selected covers
├── Series A/
│   └── Issue 01.cbz
└── ...
```

**Benefits**:
- Compatible with YACReader database
- Self-contained libraries (portable)
- Easy backup
- Can run alongside YACReader for testing

### 4. Dual Format Thumbnails

**Decision**: Generate both JPEG and WebP thumbnails.

**Formats**:
- **JPEG** (300px): Mobile app compatibility
- **WebP** (400px): Web UI (35% smaller, better quality)

**Serving Strategy**:
- Legacy API: Always serves JPEG
- Modern API: Content negotiation (WebP with JPEG fallback)

### 5. Dual API Architecture

**APIs**:
- **Legacy v1** (`/library/*`): Text/HTML for mobile apps
- **Modern API** (`/api/v1/*`): JSON REST for web UI
- **WebSocket** (`/ws/*`): Real-time updates

**Why Both**:
- Mobile app requires legacy format
- Web UI benefits from modern JSON API
- Can deprecate legacy eventually (when we build our own mobile app)

## Key Features

### Phase 1: Core & Mobile UX Improvements

#### 1. Folders-First Sorting ⭐
**Problem**: YACReader mixes folders and comics together, making navigation harder.

**Solution**:
```python
# Current YACReader behavior (foldercontroller.cpp:73)
folderContent.append(folderComics)  # Mixes them!
std::sort(folderContent.begin(), folderContent.end())

# Our implementation
folders.sort(key=lambda x: x.name.lower())
comics.sort(key=lambda x: x.name.lower())
items = folders + comics  # Folders FIRST!
```

**Implementation**: Sort folders and comics separately, render folders first in HTML.

**Impact**: Immediate UX improvement for mobile users.

#### 2. Continue Reading List
**Feature**: Show recently-read comics with progress indicators.

**Database**:
```sql
CREATE TABLE reading_progress (
    library_id INTEGER,
    comic_id INTEGER,
    current_page INTEGER,
    total_pages INTEGER,
    last_read TIMESTAMP,
    PRIMARY KEY (library_id, comic_id)
);
```

**UI**: Widget showing 5-10 most recent in-progress comics with progress bars.

#### 3. Custom Cover Selection
**Feature**: Pick any page as comic's cover thumbnail.

**Storage**: `custom_covers/` folder separate from auto-generated covers.

**Web UI**: Page selector showing all pages, click to set as cover.

#### 4. Reading Progress Tracking
**Feature**: Visual progress indicators throughout the app.

**Display**:
- Progress bars on comic thumbnails
- "45% complete" badges
- Resume reading from last page

### Phase 2: Performance & Intelligence

#### 5. Smart Page Preloading
**Feature**: Preload next 3 pages while reading.

**Implementation**:
```python
def preload_pages(comic_id, current_page, direction='ltr'):
    if direction == 'rtl':  # Manga mode
        preload = range(current_page-1, current_page-4, -1)
    else:  # Normal mode
        preload = range(current_page+1, current_page+4)

    for page in preload:
        load_page_async(comic_id, page)
```

**Benefit**: Instant page turns on mobile.

#### 6. Bandwidth-Aware Quality
**Feature**: Serve different image quality based on connection.

**Quality Levels**:
- High (q=95): WiFi, desktop
- Medium (q=75): Default mobile
- Low (q=60): Cellular data
- Thumbnail (200px): Quick preview

**API**: `GET /library/2/comic/188/page/1/remote?quality=medium`

#### 7. Series Auto-Detection
**Feature**: Automatically group comics into series.

**Detection**:
```python
# Detect patterns:
# "Batman v01.cbz" → "Batman"
# "Spider-Man #001.cbz" → "Spider-Man"
# "X-Men - 001.cbz" → "X-Men"

patterns = [
    r'^(.+?)\s+v\d+',     # Volume
    r'^(.+?)\s+#\d+',     # Issue
    r'^(.+?)\s+-\s+\d+',  # Dash
]
```

**Display**: Group view showing all comics in series, sorted by issue number.

### Phase 3: Advanced Features

#### 8. Collections/Reading Lists
**Feature**: Custom user-defined collections.

**Examples**:
- "Currently Reading"
- "Favorites"
- "To Read"
- "Best of Marvel"

#### 9. Smart Search
**Features**:
- Full-text search (SQLite FTS5)
- Fuzzy matching (typo tolerance)
- Search suggestions
- Grouped results (series, comics, tags)

#### 10. Reading Statistics
**Tracked Data**:
- Comics read per month
- Pages read
- Reading speed
- Favorite genres
- Reading streaks

## Mobile App Control

### What We Discovered

The YACReader mobile app is a **WebView-based browser** that displays server-generated HTML.

**Mobile App Architecture**:
```
┌────────────────────┐
│   YACReader App    │
│  ┌──────────────┐  │
│  │   WebView    │  │ ← Renders our HTML
│  │  (Browser)   │  │
│  └──────────────┘  │
└────────────────────┘
```

### Complete Control Over

✅ **Everything visible in browsing interface**:
- Library list display
- Folder contents layout
- Comic listings
- Search results
- Sort order
- Filters
- Progress indicators
- Custom widgets/panels

**How**: Server generates HTML using templates → Mobile app displays it.

### Cannot Control

❌ **Native app elements**:
- Top navigation bar
- Comic reader/page viewer (native for performance)
- Settings menu
- Native gestures

### Template System

**Current YACReader**: Uses `.tpl` files with custom template engine.

**Example** (folder.tpl):
```html
<ul id="itemContainer">
  {loop element}
  <li>
    <div class="{element.class}">
      <img src="{element.image.url}"/>
    </div>
    <div class="info">
      <p>{element.name}</p>
    </div>
  </li>
  {end element}
</ul>
```

**Our Implementation**: Use Jinja2 templates (Python standard).

**Enhanced Template**:
```html
<!-- Folders Section -->
<h2 class="section">📁 Folders</h2>
<ul class="folder-list">
  {% for folder in folders %}
  <li class="folder-item">
    📁 {{ folder.name }}
    <span class="count">{{ folder.comic_count }}</span>
  </li>
  {% endfor %}
</ul>

<!-- Comics Section -->
<h2 class="section">📚 Comics</h2>
<ul class="comic-grid">
  {% for comic in comics %}
  <li class="comic-item">
    <img src="{{ comic.cover }}"/>
    <p>{{ comic.name }}</p>
    {% if comic.progress %}
    <div class="progress-bar">
      <div class="fill" style="width: {{ comic.progress }}%"></div>
    </div>
    {% endif %}
  </li>
  {% endfor %}
</ul>
```

## Technology Stack

### Backend

**Framework**: FastAPI (Python 3.11+)
- Async/await support
- Auto-generated API docs
- WebSocket support
- Type hints & validation
- Fast performance

**Database**: SQLite (primary) / PostgreSQL (optional)
- Compatible with YACReader's library.ydb
- Optional enhanced.db for extended features

**Image Processing**: Pillow
- Thumbnail generation
- WebP conversion
- Page extraction from archives

**Archive Support**:
- zipfile (CBZ - built-in)
- rarfile (CBR)
- py7zr (CB7)

**Caching**: Redis (optional)
- Session storage
- Page cache
- Metadata cache

### Frontend (Web UI)

**Framework**: Vue 3 or React (TBD)
- Component-based architecture
- Reactive state management
- Modern tooling

**UI Library**: Tailwind CSS + shadcn/ui
- Modern design
- Responsive
- Customizable

**Comic Reader**: Custom canvas-based or library
- Page navigation
- Zoom/pan
- Keyboard shortcuts
- Fullscreen mode

## Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Layer                           │
├─────────────────┬───────────────────────────────────────────┤
│  Mobile App     │  Web UI                                   │
│  (iOS/Android)  │  - Comic Reader                           │
│  - Uses legacy  │  - Library Browser                        │
│    API v1       │  - Admin Panel                            │
│  - Compatible!  │  - Uses modern API                        │
└────────┬────────┴──────────────┬────────────────────────────┘
         │                       │
         │ Legacy API v1         │ Modern REST API (JSON)
         │ (text/html)           │
         ▼                       ▼
┌─────────────────────────────────────────────────────────────┐
│          YACLib Replacement Server (Python)                 │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────────────────────┐│
│  │  Legacy API v1   │  │  Modern API                      ││
│  │  - Text format   │  │  - JSON REST endpoints           ││
│  │  - HTML pages    │  │  - WebSocket updates             ││
│  │  - Compatible    │  │  - Streaming support             ││
│  └────────┬─────────┘  └───────┬──────────────────────────┘│
│           │                    │                            │
│           └────────┬───────────┘                            │
│                    │                                        │
│         ┌──────────┴───────────────────────────┐            │
│         │  Core Services                       │            │
│         ├──────────────────────────────────────┤            │
│         │ - Comic Loader (CBZ/CBR/PDF)         │            │
│         │ - Page Renderer & Cache              │            │
│         │ - Page Preloader (smart lookahead)   │            │
│         │ - Session Manager                    │            │
│         │ - Scanner & Indexer                  │            │
│         │ - Upload Handler                     │            │
│         │ - Metadata Manager                   │            │
│         │ - Series Detector (auto-grouping)    │            │
│         │ - Library Organizer                  │            │
│         │ - Reading Progress Tracker           │            │
│         └──────────────────────────────────────┘            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ Direct file access
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    File System                              │
│  /path/to/Library1/  (e.g., /mnt/Blue/Ebooks_Comics/Manga) │
│    ├── .yacreaderlibrary/          # Per-library metadata  │
│    │   ├── library.ydb              # SQLite DB (compat)   │
│    │   ├── covers/                  # Thumbnails           │
│    │   └── custom_covers/           # User-selected        │
│    └── Comics/                                             │
└─────────────────────────────────────────────────────────────┘
```

### Request Flow

**Mobile App Request**:
```
1. Mobile App: GET /library/2/folder/1?sort=folders_first
2. Server: Query database for folders and comics
3. Server: Apply sorting (folders first!)
4. Server: Render HTML template with data
5. Server: Return HTML
6. Mobile App: Display HTML in WebView
```

**Web UI Request**:
```
1. Web UI: GET /api/v1/libraries/2/folders/1?sort=folders_first
2. Server: Query database
3. Server: Apply sorting
4. Server: Return JSON
5. Web UI: Render with React/Vue components
```

## Implementation Plan

### Phase 1: Foundation (Week 1-2)
1. ✅ Reverse engineer API
2. ✅ Design architecture
3. ✅ Create Python client library
4. ⏳ Build comic loader (CBZ/CBR support)
5. ⏳ Implement database layer
6. ⏳ Create basic FastAPI server
7. ⏳ Implement legacy API v1 endpoints
8. ⏳ Test with mobile app

### Phase 2: Mobile UX (Week 3)
1. Folders-first sorting
2. Continue reading list
3. Reading progress tracking
4. Custom cover selection UI (web)
5. Query parameters for sorting

### Phase 3: Web UI (Week 4-5)
1. Basic comic reader
2. Library browser
3. Search interface
4. Admin panel
5. Upload functionality

### Phase 4: Advanced Features (Week 6+)
1. Series auto-detection
2. Collections/reading lists
3. Smart search with FTS
4. Reading statistics
5. Metadata scraping

## Migration Path

### For Existing YACReader Users

**Step 1: Test Alongside**
- Keep YACReader Server running
- Install YACLib Enhanced on different port
- Point test device to new server
- Verify compatibility

**Step 2: Import Data**
- Point YACLib to existing `.yacreaderlibrary` folders
- Import existing database
- Generate WebP thumbnails (background task)
- Verify all comics are accessible

**Step 3: Switch**
- Update mobile app server URL
- Test all features
- Keep YACReader as backup

**Step 4: Enhanced Features**
- Enable new features gradually
- Custom covers
- Continue reading
- Collections

**Rollback**: If issues, just point mobile app back to YACReader - no data loss!

## File Structure

```
yaclib-enhanced/
├── docs/
│   ├── YACLIB_API.md              # Reverse-engineered API docs
│   ├── ARCHITECTURE.md            # System architecture
│   ├── THUMBNAILS_AND_METADATA.md # Thumbnail system design
│   ├── DESIGN_DECISIONS.md        # Key decisions & rationale
│   ├── IMPROVEMENTS_AND_FEATURES.md # Feature proposals
│   ├── SERVER_CONTROL_ANALYSIS.md # Mobile app control analysis
│   └── PROJECT_OVERVIEW.md        # This document
├── src/
│   ├── client/
│   │   └── yaclib.py              # Python client library (working!)
│   ├── api/
│   │   ├── main.py                # FastAPI application
│   │   ├── routers/
│   │   │   ├── legacy_v1.py       # Legacy API compatibility
│   │   │   ├── comics.py          # Modern API
│   │   │   └── libraries.py
│   │   ├── services/
│   │   │   ├── comic_loader.py    # CBZ/CBR parsing
│   │   │   ├── scanner.py         # Library scanner
│   │   │   ├── metadata.py        # Metadata management
│   │   │   └── session.py         # Session management
│   │   ├── models/
│   │   │   ├── comic.py
│   │   │   └── library.py
│   │   └── database/
│   │       ├── yacreader.py       # YACReader DB access
│   │       └── enhanced.py        # Enhanced features DB
│   ├── web/                       # Frontend (Vue/React)
│   │   ├── src/
│   │   │   ├── components/
│   │   │   ├── pages/
│   │   │   └── api/
│   │   └── public/
│   └── templates/                 # Jinja2 templates for legacy API
│       ├── libraries.html
│       └── folder.html
├── examples/
│   └── basic_usage.py             # Client library examples
├── tests/
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Success Metrics

### Mobile App Compatibility
- ✅ All existing features work
- ✅ No visual regressions
- ✅ Performance equal or better

### New Features
- 📁 Folders appear first in listings
- 📖 Continue reading list visible
- 📊 Progress tracking on all comics
- 🎨 Custom covers selectable
- 🔍 Better search results

### Performance
- < 100ms response time for folder listings
- < 50ms for cached thumbnails
- < 2s for comic page loads (first time)
- < 200ms for cached pages

### User Experience
- Intuitive web UI
- Mobile-responsive design
- Fast navigation
- Clear visual feedback

## Current Status

### ✅ Completed
1. Complete API reverse engineering
2. Architecture design
3. Python client library (working!)
4. Thumbnail system design
5. Mobile app control analysis
6. Comprehensive documentation

### ⏳ In Progress
- Preparing to implement Phase 1

### 📋 Next Steps
1. Build comic loader module
2. Implement database layer
3. Create FastAPI server skeleton
4. Implement legacy API v1 endpoints
5. Test with mobile app

## Resources

### Documentation
- [YACReader GitHub](https://github.com/YACReader/yacreader)
- [YACReader Website](https://www.yacreader.com/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Pillow Docs](https://pillow.readthedocs.io/)

### Our Documentation
All documentation is in the `docs/` folder:
- API protocol reference
- Architecture diagrams
- Design decisions with rationale
- Feature specifications
- Implementation guides

## Conclusion

YACLib Enhanced represents a complete modernization of YACReaderLibrary Server while maintaining perfect backward compatibility. By understanding that the mobile app is HTML-based, we can deliver enhanced features to mobile users immediately without waiting for app updates.

The project is well-architected, thoroughly documented, and ready for implementation.

---

**Status**: Design phase complete. Ready to begin implementation.

**Next Action**: Begin Phase 1 - Comic Loader and Database Layer implementation.
