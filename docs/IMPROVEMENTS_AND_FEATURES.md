# Architecture Improvements & Mobile Features

## Proposed Improvements

### 1. Smart Folder/Comic Sorting

**Problem**: Current YACReader mixes folders and comics together, making navigation harder.

**Solution**: Implement smart sorting in the HTML response.

**Implementation**:
```python
def get_folder_contents(library_id, folder_id, sort_mode='folders_first'):
    """
    Sort modes:
    - 'folders_first': Folders on top, then comics (alphabetically within each)
    - 'alphabetical': All items mixed alphabetically
    - 'date_added': Newest first
    - 'recently_read': Recently accessed first
    - 'custom': User-defined order
    """
    folders = get_subfolders(library_id, folder_id)
    comics = get_comics_in_folder(library_id, folder_id)

    if sort_mode == 'folders_first':
        # Sort folders alphabetically
        folders.sort(key=lambda x: x.name.lower())
        # Sort comics alphabetically
        comics.sort(key=lambda x: x.name.lower())
        # Folders first, then comics
        items = folders + comics

    return render_folder_page(items)
```

**Database Addition**:
```sql
-- Store user's preferred sort order per folder
CREATE TABLE folder_preferences (
    library_id INTEGER,
    folder_id INTEGER,
    sort_mode TEXT DEFAULT 'folders_first',
    PRIMARY KEY (library_id, folder_id)
);
```

**Benefits**:
- Better mobile navigation (folders easier to find)
- User can choose preferred sorting
- Remembers preference per folder

---

### 2. Improved Page Preloading

**Problem**: Current implementation loads pages on-demand, causing wait times.

**Solution**: Intelligent preloading based on reading direction.

**Implementation**:
```python
class PagePreloader:
    def __init__(self, lookahead=3):
        self.lookahead = lookahead

    def preload_pages(self, comic_id, current_page, reading_direction='ltr'):
        """
        Preload next N pages in reading direction
        - LTR: preload current+1, current+2, current+3
        - RTL (manga): preload current-1, current-2, current-3
        """
        if reading_direction == 'rtl':
            # Manga mode - preload backwards
            pages_to_load = range(current_page - 1,
                                  max(0, current_page - self.lookahead - 1),
                                  -1)
        else:
            # Normal mode - preload forwards
            pages_to_load = range(current_page + 1,
                                  min(total_pages, current_page + self.lookahead + 1))

        for page_num in pages_to_load:
            self.load_page_async(comic_id, page_num)
```

**Benefits**:
- Instant page turns on mobile
- Respects reading direction (manga vs western comics)
- Configurable lookahead distance

---

### 3. Bandwidth-Aware Image Quality

**Problem**: Mobile users on cellular data waste bandwidth on full-quality images.

**Solution**: Serve different quality based on connection or user preference.

**API Addition**:
```python
# Accept quality parameter in page requests
GET /library/2/comic/188/page/1/remote?quality=medium

# Quality levels:
# - high: Full quality JPEG (q=95)
# - medium: Balanced (q=75) - default for mobile
# - low: Cellular-friendly (q=60)
# - thumbnail: Quick preview (200px wide)
```

**Session-Based Quality**:
```python
# Mobile app can set preferred quality in session
POST /library/2/comic/188/remote
Body: deviceType:iphone
      displayType:@2x
      quality:medium  # New field
```

**Benefits**:
- Saves mobile data
- Faster loading on slow connections
- User can choose quality vs speed

---

### 4. Continue Reading Feature

**Problem**: Hard to find where you left off across multiple comics.

**Solution**: Add "continue reading" endpoint.

**Database Schema**:
```sql
CREATE TABLE reading_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    library_id INTEGER NOT NULL,
    comic_id INTEGER NOT NULL,
    comic_hash TEXT NOT NULL,
    current_page INTEGER NOT NULL,
    total_pages INTEGER NOT NULL,
    last_read TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(library_id, comic_id)
);

CREATE INDEX idx_last_read ON reading_progress(last_read DESC);
```

**New Endpoints**:
```python
# Get continue reading list (10 most recent)
GET /continue-reading
Response: HTML list of comics with progress

# Example HTML:
<ul id="continueReading">
  <li>
    <div class="comic">
      <img src="/library/2/cover/hash.jpg" />
      <div class="info">
        <p>All You Need Is Kill v01</p>
        <div class="progress">Page 45/207 (22%)</div>
      </div>
      <a href="/library/2/comic/188/remote">Continue</a>
    </div>
  </li>
  ...
</ul>
```

**Benefits**:
- Quick access to in-progress comics
- Shows progress percentage
- Mobile app can display prominently

---

### 5. Smart Comic Grouping

**Problem**: Series spread across folders are hard to track.

**Solution**: Auto-detect series and group comics.

**Implementation**:
```python
def detect_series(comic_name):
    """
    Detect series patterns:
    - "Series Name v01.cbz" -> "Series Name"
    - "Series Name #001.cbz" -> "Series Name"
    - "Series Name - 001.cbz" -> "Series Name"
    """
    patterns = [
        r'^(.+?)\s+v\d+',     # Volume number
        r'^(.+?)\s+#\d+',     # Issue number
        r'^(.+?)\s+-\s+\d+',  # Dash number
        r'^(.+?)\s+\d+',      # Space number
    ]

    for pattern in patterns:
        match = re.match(pattern, comic_name, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return None

# Database
CREATE TABLE series (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE comic_series (
    comic_id INTEGER PRIMARY KEY,
    series_id INTEGER,
    issue_number REAL,  -- Support "1.5" variants
    FOREIGN KEY (series_id) REFERENCES series(id)
);
```

**New Feature**:
```python
# View comics grouped by series
GET /library/2/series
Response: HTML with series groups

# View specific series
GET /library/2/series/5
Response: All comics in series, sorted by issue number
```

**Benefits**:
- Easy series browsing
- Auto-sorting by issue number
- Track series completion

---

### 6. Download Queue for Mobile

**Problem**: Mobile apps can't bulk download for offline reading.

**Solution**: Server-side download queue and bundling.

**Implementation**:
```python
# Create download bundle
POST /api/v1/downloads/create
Body: {
  "comic_ids": [188, 189, 190],
  "quality": "medium"
}
Response: {
  "download_id": "abc123",
  "status": "preparing"
}

# Check status
GET /api/v1/downloads/abc123/status
Response: {
  "status": "ready",
  "total_size": 245000000,  # bytes
  "download_url": "/api/v1/downloads/abc123/bundle.zip"
}

# Download bundle
GET /api/v1/downloads/abc123/bundle.zip
Response: ZIP file with all comics
```

**Benefits**:
- Bulk download for offline reading
- Optimized file size (configurable quality)
- Mobile-friendly

---

### 7. Reading Statistics

**Problem**: No insights into reading habits.

**Solution**: Track and display reading statistics.

**Database**:
```sql
CREATE TABLE reading_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comic_id INTEGER,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    pages_read INTEGER
);
```

**Features**:
- Comics read this month
- Average reading speed
- Favorite genres/series
- Reading streaks

**Endpoint**:
```python
GET /stats
Response: HTML dashboard with charts and stats
```

---

### 8. Smart Search

**Problem**: Basic filename search only.

**Solution**: Full-text search with smart features.

**Implementation**:
```sql
-- SQLite FTS5 full-text search
CREATE VIRTUAL TABLE comics_fts USING fts5(
    title,
    series,
    description,
    tags,
    content=comic
);

-- Search query
SELECT c.* FROM comic c
JOIN comics_fts fts ON c.id = fts.rowid
WHERE comics_fts MATCH 'title:batman OR tags:dc'
ORDER BY rank
LIMIT 20;
```

**Search Features**:
- Search by title, series, tags
- Fuzzy matching (typos)
- Search suggestions
- Recent searches

**Endpoint**:
```python
GET /search?q=batman&suggestions=true
Response: HTML with results + suggestions
```

---

### 9. Collections/Reading Lists

**Problem**: Can't create custom collections across folders.

**Solution**: User-defined reading lists.

**Database**:
```sql
CREATE TABLE collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE collection_items (
    collection_id INTEGER,
    comic_id INTEGER,
    sort_order INTEGER,
    PRIMARY KEY (collection_id, comic_id)
);
```

**Features**:
- "Currently Reading"
- "Favorites"
- "To Read"
- Custom collections

**Endpoints**:
```python
# List collections
GET /collections

# View collection
GET /collections/5

# Add to collection
POST /api/v1/collections/5/comics
Body: { "comic_id": 188 }
```

---

### 10. Improved Caching Strategy

**Architecture Improvement**: Add Redis for distributed caching.

```python
# Cache hierarchy
1. Browser cache (1 year for covers)
2. Redis cache (hot pages/metadata)
3. Disk cache (extracted pages)
4. Source files (CBZ/CBR)

# Benefits:
- Faster page serving
- Reduced disk I/O
- Horizontal scaling support
- Session sharing across instances
```

---

## Mobile-Specific Improvements

### 1. Optimized HTML for Mobile

**Current Issue**: Desktop-focused HTML.

**Solution**: Responsive, mobile-first HTML templates.

```html
<!-- Mobile-optimized folder listing -->
<div id="contentLibraries">
  <h1>{{folder_name}}</h1>

  <!-- Folders first -->
  <div class="folders-section">
    <h2>Folders</h2>
    <ul class="folder-list">
      {{#folders}}
      <li class="folder-item">
        <div class="folder-icon">📁</div>
        <a href="/library/{{library_id}}/folder/{{id}}">
          {{name}}
        </a>
        <div class="folder-meta">{{comic_count}} comics</div>
      </li>
      {{/folders}}
    </ul>
  </div>

  <!-- Comics after folders -->
  <div class="comics-section">
    <h2>Comics</h2>
    <ul class="comic-grid">
      {{#comics}}
      <li class="comic-item">
        <img loading="lazy" src="/library/{{library_id}}/cover/{{hash}}.jpg" />
        <div class="comic-info">
          <p class="title">{{title}}</p>
          {{#progress}}
          <div class="progress-bar">
            <div class="progress-fill" style="width: {{percent}}%"></div>
          </div>
          {{/progress}}
        </div>
        <a href="/library/{{library_id}}/comic/{{id}}/remote">Read</a>
      </li>
      {{/comics}}
    </ul>
  </div>
</div>
```

---

### 2. Query Parameters for Sorting

**Allow mobile app to request specific sorting**:

```python
GET /library/2/folder/1?sort=folders_first
GET /library/2/folder/1?sort=alphabetical
GET /library/2/folder/1?sort=date_added
GET /library/2/folder/1?sort=recently_read
```

Mobile app can remember user's preferred sort and include in requests.

---

### 3. Pagination Improvements

**Current**: Page numbers in dropdown (not mobile-friendly).

**Better**: Infinite scroll or "Load More" button.

```python
GET /library/2/folder/1?page=0&limit=20
Response: First 20 items

GET /library/2/folder/1?page=1&limit=20
Response: Next 20 items

# Include hasMore flag
<div class="pagination" data-has-more="true" data-next-page="1">
  <button class="load-more">Load More</button>
</div>
```

---

## Recommended Implementation Order

### Phase 1: Quick Wins (Mobile UX)
1. ✅ **Folders-first sorting** - Easy, high impact
2. ✅ **Continue reading list** - Simple database query
3. ✅ **Reading progress tracking** - Already partially implemented
4. ✅ **Query parameters for sorting** - Small change

### Phase 2: Performance
5. Page preloading
6. Image quality options
7. Improved caching with Redis

### Phase 3: Advanced Features
8. Series detection and grouping
9. Smart search with FTS
10. Collections/reading lists
11. Download queue
12. Reading statistics

---

## Configuration

Add to `config.yml`:

```yaml
mobile:
  # Sorting
  default_sort: folders_first  # folders_first, alphabetical, date_added

  # Performance
  page_preload_count: 3
  default_image_quality: medium  # high, medium, low

  # Features
  enable_continue_reading: true
  enable_series_detection: true
  enable_collections: true

  # Pagination
  items_per_page: 20
  enable_infinite_scroll: false
```

---

## Summary

**Immediate Benefits** (Phase 1):
- ✅ Folders on top (requested feature)
- ✅ Continue reading list
- ✅ Better mobile sorting
- ✅ Progress tracking

**Medium-term** (Phase 2):
- Faster page loading
- Bandwidth savings
- Better caching

**Long-term** (Phase 3):
- Smart features (series, search, collections)
- Advanced analytics
- Offline support

All features maintain **100% backward compatibility** with existing mobile apps.
