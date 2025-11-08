# Thumbnails and Metadata Design

## Overview

YACLib Enhanced uses a dual-format thumbnail system to optimize for both mobile app compatibility (JPEG) and modern web performance (WebP).

## File Structure

### Per-Library Storage

Each library maintains its metadata and thumbnails in a `.yacreaderlibrary` folder within the library root:

```
/mnt/Blue/Ebooks_Comics/Manga/
├── .yacreaderlibrary/
│   ├── library.ydb                    # SQLite database
│   ├── id                             # Library UUID
│   ├── covers/                        # Cover thumbnails
│   │   ├── {hash}.jpg                 # Mobile-compatible (legacy)
│   │   └── {hash}.webp                # Web-optimized (new)
│   └── custom_covers/                 # User-selected covers (new)
│       ├── {hash}.jpg
│       └── {hash}.webp
├── Series A/
│   └── Issue 01.cbz
└── Series B/
    └── Issue 01.cbz
```

### Database Location

**Compatible Mode**: Uses existing YACReader database structure in `.yacreaderlibrary/library.ydb`

**Extended Mode** (optional): Additional SQLite DB at `/var/lib/yaclib/enhanced.db` for:
- Custom cover selections
- Extended metadata
- User preferences
- Collections/tags

## Thumbnail System

### Dual Format Strategy

Generate and serve thumbnails in two formats:

1. **JPEG** (for mobile app compatibility)
   - Format: JPEG, quality 85%
   - Size: 300px width (maintain aspect ratio)
   - Used by iOS/Android apps via legacy API
   - Stored in `covers/{hash}.jpg`

2. **WebP** (for web UI)
   - Format: WebP, quality 80%
   - Size: 400px width (maintain aspect ratio)
   - 25-35% smaller than JPEG at same quality
   - Modern browser support
   - Stored in `covers/{hash}.webp`

### Thumbnail Generation

```python
# Pseudocode
def generate_thumbnails(comic_path: str, hash: str):
    """Generate both JPEG and WebP thumbnails"""

    # Extract cover page (usually page 0 or 1)
    cover_image = extract_cover_from_comic(comic_path)

    # Generate JPEG for mobile compatibility
    jpeg_thumb = resize_image(cover_image, width=300)
    save_jpeg(jpeg_thumb, f"covers/{hash}.jpg", quality=85)

    # Generate WebP for web
    webp_thumb = resize_image(cover_image, width=400)
    save_webp(webp_thumb, f"covers/{hash}.webp", quality=80)
```

### Serving Strategy

**Legacy API** (`/library/{id}/cover/{hash}.jpg`):
- Always serves JPEG
- Mobile apps use this
- Maintains compatibility

**Modern API** (`/api/v1/comics/{id}/cover`):
- Content negotiation based on Accept header
- Serves WebP if client supports it
- Falls back to JPEG for older clients
- Returns appropriate Content-Type

```python
# Pseudocode
def serve_cover(hash: str, accept_header: str):
    if "image/webp" in accept_header:
        # Check if WebP exists
        if exists(f"covers/{hash}.webp"):
            return file(f"covers/{hash}.webp", "image/webp")

    # Fallback to JPEG
    return file(f"covers/{hash}.jpg", "image/jpeg")
```

## Custom Cover Selection

### Feature: Pick Custom Thumbnails

Allow users to select any page from a comic as its cover thumbnail.

### Storage

Custom covers are stored separately to avoid confusion with auto-generated covers:

```
.yacreaderlibrary/
├── covers/              # Auto-generated covers
│   └── {hash}.jpg
└── custom_covers/       # User-selected covers
    ├── {hash}.jpg
    └── {hash}.webp
```

### Database Schema Addition

```sql
-- Add to library.ydb (compatible mode)
CREATE TABLE IF NOT EXISTS custom_covers (
    comic_hash TEXT PRIMARY KEY,
    page_number INTEGER NOT NULL,
    created_at INTEGER NOT NULL,
    FOREIGN KEY (comic_hash) REFERENCES comic(hash)
);

-- Or in enhanced.db (extended mode)
CREATE TABLE custom_covers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    library_id INTEGER NOT NULL,
    comic_id INTEGER NOT NULL,
    comic_hash TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(library_id, comic_id)
);
```

### API Endpoints

```
# Set custom cover
POST /api/v1/comics/{id}/cover
Body: { "page_number": 5 }
Response: { "success": true, "cover_url": "/api/v1/comics/{id}/cover" }

# Get cover (auto or custom)
GET /api/v1/comics/{id}/cover
Returns: Image (JPEG or WebP based on Accept header)

# Reset to auto-generated cover
DELETE /api/v1/comics/{id}/cover/custom
Response: { "success": true }

# Preview page as potential cover
GET /api/v1/comics/{id}/pages/{page_num}/thumbnail
Returns: Thumbnail-sized version of page
```

### Implementation Flow

```python
def set_custom_cover(comic_id: int, page_number: int):
    """Set a custom cover for a comic"""

    # 1. Load the comic
    comic = get_comic(comic_id)

    # 2. Extract the specified page
    page_image = extract_page(comic.path, page_number)

    # 3. Generate thumbnails
    hash = comic.hash

    # JPEG for mobile
    jpeg_thumb = resize_image(page_image, width=300)
    save_jpeg(jpeg_thumb, f"custom_covers/{hash}.jpg", quality=85)

    # WebP for web
    webp_thumb = resize_image(page_image, width=400)
    save_webp(webp_thumb, f"custom_covers/{hash}.webp", quality=80)

    # 4. Record in database
    db.execute(
        "INSERT OR REPLACE INTO custom_covers VALUES (?, ?, ?)",
        (hash, page_number, int(time.time()))
    )

    return True

def get_cover_path(hash: str, format: str = "jpg") -> str:
    """Get the path to a comic's cover (custom or auto)"""

    # Check for custom cover first
    custom_path = f"custom_covers/{hash}.{format}"
    if exists(custom_path):
        return custom_path

    # Fallback to auto-generated
    return f"covers/{hash}.{format}"
```

## Performance Considerations

### Caching Strategy

1. **Browser Caching**
   - Set Cache-Control headers: `max-age=31536000` (1 year)
   - Use ETags based on file modification time
   - Immutable covers (hash-based filenames)

2. **Server-side Caching**
   - Keep frequently accessed covers in memory (LRU cache)
   - Pre-generate thumbnails during library scan
   - Background worker for thumbnail generation

3. **CDN/Reverse Proxy**
   - nginx can serve static covers directly
   - Reduce server load
   - Faster delivery

### Lazy Generation

For large libraries, generate thumbnails on-demand:

```python
def get_cover(hash: str, format: str):
    cover_path = get_cover_path(hash, format)

    if not exists(cover_path):
        # Generate on-demand
        comic = get_comic_by_hash(hash)
        generate_thumbnails(comic.path, hash)

    return serve_file(cover_path)
```

## Migration from YACReader

### Import Existing Thumbnails

```python
def migrate_existing_library(library_path: str):
    """Import existing YACReader library data"""

    yac_dir = os.path.join(library_path, ".yacreaderlibrary")

    # 1. Copy database
    shutil.copy(
        os.path.join(yac_dir, "library.ydb"),
        os.path.join(yac_dir, "library.ydb.backup")
    )

    # 2. Generate WebP versions of existing JPEG covers
    covers_dir = os.path.join(yac_dir, "covers")
    for jpeg_file in glob.glob(os.path.join(covers_dir, "*.jpg")):
        hash = os.path.splitext(os.path.basename(jpeg_file))[0]

        # Convert to WebP
        img = Image.open(jpeg_file)
        webp_path = os.path.join(covers_dir, f"{hash}.webp")
        img.save(webp_path, "WEBP", quality=80)

    # 3. Create custom_covers directory
    os.makedirs(os.path.join(yac_dir, "custom_covers"), exist_ok=True)

    # 4. Update database schema if needed
    add_custom_covers_table()
```

## Storage Estimates

Example library with 1000 comics:

**JPEG only** (current YACReader):
- Average JPEG cover: ~100 KB
- Total: 1000 × 100 KB = 100 MB

**Dual format** (YACLib Enhanced):
- Average JPEG cover: ~100 KB
- Average WebP cover: ~65 KB (35% smaller)
- Total: 1000 × (100 + 65) KB = 165 MB

**With custom covers** (10% customized):
- Additional storage: 100 × 165 KB = 16.5 MB
- Total: ~182 MB

The 82 MB increase (65 MB for WebP + 17 MB for custom) provides:
- Faster web UI load times
- Better user experience
- Flexibility for custom covers

## Thumbnail Quality Settings

Make quality configurable in settings:

```python
# config.yml
thumbnails:
  jpeg:
    width: 300
    quality: 85
  webp:
    width: 400
    quality: 80
  custom_covers:
    enabled: true
  lazy_generation: true
  cache_size_mb: 100
```

## Web UI Features

### Cover Selection Interface

```
┌─────────────────────────────────────────┐
│  Comic: All You Need Is Kill v01        │
├─────────────────────────────────────────┤
│  Current Cover:     [Change Cover]      │
│  ┌─────────────┐                        │
│  │   [Cover]   │                        │
│  │    Image    │                        │
│  └─────────────┘                        │
│                                         │
│  Select New Cover:                      │
│  ┌──────┬──────┬──────┬──────┬──────┐  │
│  │ Pg 0 │ Pg 1 │ Pg 2 │ Pg 3 │ Pg 4 │  │
│  │[img] │[img] │[img] │[img] │[img] │  │
│  └──────┴──────┴──────┴──────┴──────┘  │
│  ← Previous    Next →                   │
│                                         │
│  [Set as Cover] [Reset to Default]     │
└─────────────────────────────────────────┘
```

### Batch Operations

```
# Set covers for multiple comics
POST /api/v1/batch/covers
Body: [
  { "comic_id": 188, "page_number": 0 },
  { "comic_id": 189, "page_number": 5 },
  ...
]

# Regenerate all covers
POST /api/v1/libraries/{id}/regenerate-covers
Query: ?force=true  # Overwrite existing
```

## Implementation Priority

1. **Phase 1**: Basic dual-format support
   - Generate both JPEG and WebP during scan
   - Serve JPEG to legacy API
   - Serve WebP to modern API with fallback

2. **Phase 2**: Custom cover selection
   - API endpoints for setting custom covers
   - Database tracking
   - Web UI for selection

3. **Phase 3**: Advanced features
   - Lazy generation
   - Batch operations
   - Quality settings
   - Background workers

## Compatibility Notes

### Mobile App Compatibility

The iOS/Android apps will continue to work unchanged:
- They request JPEG via `/library/{id}/cover/{hash}.jpg`
- We serve the JPEG thumbnail
- No changes needed to mobile apps

### Web UI Advantages

Modern browsers get:
- Smaller WebP files (faster load)
- Higher quality at same size
- Progressive loading support
- Better compression

### Graceful Degradation

If WebP generation fails:
- Fall back to JPEG for web UI
- Log error for debugging
- System continues to function
