# Services Documentation

## Overview

The `src/services/` directory contains business logic services that handle metadata application, scheduling, external API integration, and core application operations.

### Service Overview

| Service | Location | Purpose |
|---------|----------|---------|
| MetadataService | `metadata_service.py` | Apply scanner results to comics |
| SchedulerService | `scheduler.py` | APScheduler-based periodic library scans |
| MangaDexClient | `mangadex_client.py` | MangaDex API client for covers |
| ComicInfoService | `comic_info_service.py` | Shared v1/v2 comic metadata retrieval |
| ConfigSync | `config_sync.py` | Config file ↔ database synchronization |
| CoverService | `cover_service.py` | Cover generation, retrieval, external fetch |
| LibraryCacheService | `library_cache.py` | File-based browse response caching |
| LibraryService | `library_service.py` | Library CRUD with statistics |
| ReadingService | `reading_service.py` | Progress, favorites, labels, reading lists |
| ScanService | `scan_service.py` | Metadata scan orchestration |
| SearchService | `search_service.py` | FTS and advanced search |

## MetadataService

**Location:** `src/services/metadata_service.py`

Handles applying scanner results to comics in the database.

### MetadataApplicationResult

Result class for metadata application operations.

```python
class MetadataApplicationResult:
    """Result of applying metadata to a comic"""
    comic_id: int        # ID of the comic that was updated
    success: bool        # Whether the operation succeeded
    fields_updated: List[str]  # List of field names that were updated
    error: Optional[str] # Error message if failed
```

**Methods:**
- `to_dict() → Dict[str, Any]`: Convert to dictionary for JSON serialization

### MetadataService Class

Static methods for metadata operations.

#### apply_scan_result_to_comic

Apply scan result metadata to a comic.

```python
@staticmethod
def apply_scan_result_to_comic(
    session: Session,
    comic: Comic,
    scan_result: ScanResult,
    scanner_name: str,
    overwrite: bool = False,
    selected_fields: Optional[List[str]] = None
) -> MetadataApplicationResult
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `session` | Session | Yes | - | SQLAlchemy database session |
| `comic` | Comic | Yes | - | Comic object to update |
| `scan_result` | ScanResult | Yes | - | Scanner result with metadata |
| `scanner_name` | str | Yes | - | Name of scanner that produced result |
| `overwrite` | bool | No | False | If True, overwrite existing metadata |
| `selected_fields` | List[str] | No | None | Specific fields to apply (all if None) |

**Returns:** `MetadataApplicationResult` with update status

**Side Effects:**
- Updates Comic record in database
- Commits transaction
- Stores scanner metadata fields (scanner_source, scanner_source_id, etc.)
- Stores flexible metadata in metadata_json field

**Error Handling:**
- On exception: rolls back transaction, returns failed result with error message

**Example:**
```python
from src.services.metadata_service import MetadataService
from src.metadata_providers.base import ScanResult

result = MetadataService.apply_scan_result_to_comic(
    session=db_session,
    comic=comic,
    scan_result=ScanResult(
        confidence=0.95,
        source_id="12345",
        source_url="https://example.com/12345",
        metadata={"title": "Comic Title", "writer": "Author Name"}
    ),
    scanner_name="example_scanner",
    overwrite=False
)

if result.success:
    print(f"Updated {len(result.fields_updated)} fields")
else:
    print(f"Failed: {result.error}")
```

---

#### get_metadata_preview

Get a preview of what metadata would be applied.

```python
@staticmethod
def get_metadata_preview(
    comic: Comic,
    scan_result: ScanResult,
    scanner_name: str
) -> Dict[str, Any]
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `comic` | Comic | Yes | Comic to preview changes for |
| `scan_result` | ScanResult | Yes | Scanner result with metadata |
| `scanner_name` | str | Yes | Name of the scanner |

**Returns:** Dict showing current vs new values:
```python
{
    "comic_id": 123,
    "comic_filename": "comic.cbz",
    "scanner": "nhentai",
    "confidence": 0.95,
    "confidence_level": "EXACT",
    "source_url": "https://nhentai.net/g/123",
    "fields": [
        {
            "field": "title",
            "display_name": "Title",
            "current_value": None,
            "new_value": "New Title",
            "will_change": True,
            "is_empty": True,
            "is_primary": True
        },
        # ... more fields
    ]
}
```

---

#### batch_apply_metadata

Apply metadata to multiple comics at once.

```python
@staticmethod
def batch_apply_metadata(
    session: Session,
    comic_scan_pairs: List[Tuple[Comic, ScanResult, str]],
    overwrite: bool = False
) -> List[MetadataApplicationResult]
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session` | Session | Yes | Database session |
| `comic_scan_pairs` | List[Tuple] | Yes | List of (comic, scan_result, scanner_name) tuples |
| `overwrite` | bool | No | Whether to overwrite existing metadata |

**Returns:** List of `MetadataApplicationResult` objects

---

#### get_scanner_field_mapping

Get information about what fields a scanner provides.

```python
@staticmethod
def get_scanner_field_mapping(scanner_name: str) -> Dict[str, Any]
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `scanner_name` | str | Yes | Name of the scanner |

**Returns:** Dict with fields organized by category:
```python
{
    "scanner": "AniList",
    "description": "Manga/anime metadata from AniList",
    "total_fields": 15,
    "primary_fields": 5,
    "fields_by_category": {
        "basic": [
            {
                "field": "title",
                "display_name": "Title",
                "description": "Comic title",
                "db_column": "title",
                "is_primary": True,
                "data_type": "string"
            }
        ],
        "creators": [...],
        "publishing": [...]
    }
}
```

---

## SchedulerService

**Location:** `src/services/scheduler.py`

Manages periodic tasks using APScheduler for automatic library scanning.

### Architecture

Uses **Singleton pattern** to ensure only one scheduler instance exists.

```python
class SchedulerService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

### SchedulerService Class

#### Constructor

```python
def __init__(self, db: Database)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `db` | Database | Yes | Database instance for accessing library configurations |

**Notes:**
- Uses in-memory job store (avoids Python 3.13 pickle issues)
- Jobs are reloaded from DB on each server restart
- Starts scheduler immediately

---

#### schedule_library_scan

Schedule a periodic scan for a library.

```python
def schedule_library_scan(self, library_id: int, interval_minutes: int)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `library_id` | int | Yes | Library ID to schedule scan for |
| `interval_minutes` | int | Yes | Interval in minutes (0 = remove schedule) |

**Side Effects:**
- Removes existing job if present
- Creates new APScheduler job with IntervalTrigger
- Job ID format: `scan_library_{library_id}`

**Example:**
```python
scheduler = get_scheduler(db)

# Schedule scan every 60 minutes
scheduler.schedule_library_scan(library_id=1, interval_minutes=60)

# Disable scheduled scanning
scheduler.schedule_library_scan(library_id=1, interval_minutes=0)
```

---

#### _run_scan

Execute the library scan (internal method).

```python
def _run_scan(self, library_id: int)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `library_id` | int | Yes | Library ID to scan |

**Side Effects:**
- Creates new ThreadedScanner instance
- Retrieves library path from database
- Executes scan_library()
- Logs start and completion

**Error Handling:**
- Logs errors with full traceback
- Does not raise exceptions (background task)

---

#### load_schedules_from_db

Load scan schedules from library configurations on startup.

```python
def load_schedules_from_db(self)
```

**Side Effects:**
- Queries all libraries
- Schedules scans for libraries with `scan_interval > 0`
- Called during application startup

---

#### start / shutdown

```python
def start(self)     # Start scheduler (idempotent)
def shutdown(self)  # Shutdown scheduler
```

### Global Accessor

```python
_scheduler_service: Optional[SchedulerService] = None

def get_scheduler(db: Optional[Database] = None) -> SchedulerService
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `db` | Database | Conditional | Required on first call, optional afterwards |

**Returns:** SchedulerService singleton instance

**Raises:** `RuntimeError` if called without db before initialization

---

## MangaDexClient

**Location:** `src/services/mangadex_client.py`

Client for MangaDex API, used for fetching cover art.

### Configuration

```python
MANGADEX_API_BASE = "https://api.mangadex.org"
MANGADEX_COVER_BASE = "https://uploads.mangadex.org/covers"
RATE_LIMIT_DELAY = 0.2  # 5 requests/second
```

### Data Classes

#### MangaDexCover

```python
@dataclass
class MangaDexCover:
    cover_id: str          # MangaDex cover ID
    manga_id: str          # Parent manga ID
    filename: str          # Cover filename
    volume: Optional[str]  # Volume number
    description: Optional[str]
    locale: Optional[str]  # Language locale
    thumbnail_url: str     # 256px thumbnail URL
    full_url: str          # Full resolution URL
    created_at: Optional[str]
```

#### MangaDexManga

```python
@dataclass
class MangaDexManga:
    manga_id: str           # MangaDex manga ID
    title: str              # Primary title
    alt_titles: List[str]   # Alternative titles
    description: Optional[str]
    year: Optional[int]
    status: Optional[str]   # ongoing, completed, etc.
    cover_id: Optional[str]
    cover_filename: Optional[str]
```

### MangaDexClient Class

#### Constructor

```python
def __init__(self)
```

Initializes:
- requests.Session with custom User-Agent
- Rate limiting timestamp tracker

---

#### search_manga

Search for manga by title.

```python
def search_manga(self, title: str, limit: int = 10) -> List[MangaDexManga]
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `title` | str | Yes | - | Manga title to search for |
| `limit` | int | No | 10 | Maximum results (max 100) |

**Returns:** List of `MangaDexManga` objects

**Example:**
```python
client = get_mangadex_client()
results = client.search_manga("One Piece", limit=5)
for manga in results:
    print(f"{manga.title} ({manga.year})")
```

---

#### get_manga_covers

Get all covers for a manga.

```python
def get_manga_covers(self, manga_id: str, limit: int = 100) -> List[MangaDexCover]
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `manga_id` | str | Yes | - | MangaDex manga ID |
| `limit` | int | No | 100 | Maximum covers to return |

**Returns:** List of `MangaDexCover` objects sorted by volume

---

#### download_cover

Download a cover image.

```python
def download_cover(self, cover: MangaDexCover, use_thumbnail: bool = False) -> Optional[bytes]
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `cover` | MangaDexCover | Yes | - | Cover to download |
| `use_thumbnail` | bool | No | False | Download 256px thumbnail vs full image |

**Returns:** Image bytes or None on error

---

#### download_cover_as_image

Download cover and return as PIL Image.

```python
def download_cover_as_image(self, cover: MangaDexCover, use_thumbnail: bool = False) -> Optional[Image.Image]
```

**Returns:** PIL Image or None on error

---

#### search_and_get_covers

Convenience method combining search and cover fetching.

```python
def search_and_get_covers(
    self,
    title: str,
    limit_manga: int = 5,
    limit_covers: int = 20
) -> List[Dict[str, Any]]
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `title` | str | Yes | - | Search query |
| `limit_manga` | int | No | 5 | Max manga results |
| `limit_covers` | int | No | 20 | Max covers per manga |

**Returns:** List of dicts with manga info and covers:
```python
[
    {
        "manga_id": "...",
        "title": "One Piece",
        "alt_titles": [...],
        "description": "...",
        "year": 1997,
        "status": "ongoing",
        "covers": [
            {
                "cover_id": "...",
                "volume": "1",
                "thumbnail_url": "...",
                "full_url": "..."
            }
        ]
    }
]
```

### Global Accessor

```python
def get_mangadex_client() -> MangaDexClient
```

Returns singleton MangaDexClient instance.

---

## ComicInfoService

**Location:** `src/services/comic_info_service.py`

Provides shared logic for retrieving comic metadata used by both v1 and v2 API routers. Reduces duplication between `legacy_v1.py` and `v2/comics.py`.

### ComicMetadata

Container dataclass holding all data needed by both API versions:
- `comic` — Comic ORM object
- `library` — Library ORM object
- `progress` — Optional ReadingProgress
- `relative_path` — Path relative to library root
- `prev_comic_id` / `next_comic_id` — Navigation IDs

---

## ConfigSync

**Location:** `src/services/config_sync.py`

Manages synchronization between the minimal bootstrap `config.yml` and the database settings table. Handles legacy config migration on first startup (moving libraries from config file to database).

---

## CoverService

**Location:** `src/services/cover_service.py`

Cover generation and retrieval operations:
- Get covers for comics (from cache or archive)
- Fetch external covers from providers (MangaDex, etc.)
- Set custom covers
- Generate dual-format thumbnails (JPEG + WebP)

---

## LibraryCacheService

**Location:** `src/services/library_cache.py`

File-based caching for library browse responses. Caches separate JSON files per browse path/query combination under `data/cache/{library_id}/browse/`. Keys are MD5 hashes of path + query parameters.

**Methods:**
- `get_cached_response(path, params)` — Retrieve cached JSON if available
- `set_cached_response(path, params, data)` — Store response JSON
- `invalidate(path)` — Invalidate cache for a specific path
- `invalidate_all()` — Clear all cache for the library

---

## LibraryService

**Location:** `src/services/library_service.py`

High-level library operations:
- `create_library_with_stats()` — Create library and return with statistics
- `get_library_info()` — Retrieve library with computed stats
- `update_library_details()` — Update library properties
- `delete_library_with_cleanup()` — Delete library and clean up covers/cache
- `get_all_libraries_with_stats()` — List all libraries with statistics

---

## ReadingService

**Location:** `src/services/reading_service.py`

Reading progress and user interaction operations:
- `update_reading_progress()` — Track reading position per user/comic
- Favorites management (add/remove/list)
- Labels management (create/assign/remove)
- Reading lists management (create/add items/reorder)

---

## ScanService

**Location:** `src/services/scan_service.py`

Orchestrates metadata scanning operations:
- `scan_single_comic()` — Scan one comic with a metadata scanner
- Series-level scanning
- Library-wide scanning
- Progress tracking and result aggregation

Uses `MetadataService` internally to apply scan results.

---

## SearchService

**Location:** `src/services/search_service.py`

Search logic including:
- `search_comics()` — Basic search using query string
- Full-text search via FTS5 index
- Advanced search with field-specific filters and pagination

---

## Rate Limiting

All external API clients implement rate limiting:

| Service | Rate Limit | Implementation |
|---------|------------|----------------|
| MangaDex | 5 req/sec | Sleep between requests |
| External scanners | Varies | Scanner-specific handling |

## Error Handling

Services use consistent error handling:

1. **MetadataService**: Catches exceptions, rolls back DB, returns error in result
2. **SchedulerService**: Logs errors, continues running other jobs
3. **MangaDexClient**: Returns None on failure, logs errors

## Thread Safety

- **SchedulerService**: Singleton with internal APScheduler thread pool
- **MetadataService**: Static methods, thread-safe with session isolation
- **MangaDexClient**: Thread-safe singleton with rate limiting
