# API Routers Documentation

## Overview

Kottlib exposes multiple API layers for different clients:

| API Layer | Prefix | Format | Purpose |
|-----------|--------|--------|---------|
| Legacy v1 | `/library/*` | Plain text | YACReader mobile app compatibility |
| API v2 | `/v2/*` | JSON | Enhanced YACReader features |
| Kottlib Native API | `/api/*` | JSON | Primary WebUI/internal API surface |
| Modern API v1 | `/api/v1/*` | JSON | Libraries CRUD |
| Modern API v2 | `/api/v2/*` | JSON | Backward-compatible user/config aliases |
| Scanners API | `/v2/scanners/*`, `/api/scanners/*` | JSON | Metadata scanner operations |

---

## Legacy v1 API (`/library/*`)

**File:** `src/api/routers/legacy_v1.py`

Plain text format for YACReader mobile app compatibility. Uses `\r\n` line endings.

### Library Listing

#### GET /library/

List all libraries.

**Response Format:**
```
type:libraries\r\n
code:0\r\n
\r\n
library:Library Name\r\n
id:1\r\n
path:/path/to/library\r\n
\r\n
library:Another Library\r\n
id:2\r\n
path:/path/to/another\r\n
```

---

### Folder Browsing

#### GET /library/{library_id}/folder/{folder_id}

Get folder contents (folders and comics).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `library_id` | int | Yes | Library ID |
| `folder_id` | int | Yes | Folder ID (0 or 1 = root) |
| `sort` | string | No | Sort mode: folders_first, alphabetical, date_added, recently_read |

**Response Format:**
```
type:folder\r\n
code:0\r\n
\r\n
folder:Folder Name\r\n
id:123\r\n
\r\n
comic:Comic Name.cbz\r\n
id:456\r\n
\r\n
```

---

#### GET /library/{library_id}/folder/{folder_id}/info

Get folder information with recursive comic listing.

**Response Format:**
```
/library/1/comic/123:filename.cbz:1234567\r\n
/library/1/comic/124:another.cbz:2345678\r\n
```

---

### Comic Information

#### GET /library/{library_id}/comic/{comic_id}

Get basic comic metadata.

**Response Format:**
```
library:Library Name\r\n
libraryId:1\r\n
previousComic:122\r\n
nextComic:124\r\n
comicid:123\r\n
hash:abc123def456\r\n
path:/path/to/comic.cbz\r\n
numpages:24\r\n
rating:0\r\n
currentPage:5\r\n
contrast:-1\r\n
read:0\r\n
coverPage:1\r\n
manga:0\r\n
added:1234567890\r\n
type:0\r\n
```

---

#### GET /library/{library_id}/comic/{comic_id}/info

Get full comic information with all metadata fields.

**Additional Fields:**
- `title`, `series`, `volume`, `number`
- `year`, `writer`, `artist`, `publisher`
- `synopsis`, `genre`

---

#### GET /library/{library_id}/comic/{comic_id}/remote

Get comic info for remote reading (includes navigation).

---

### Page Reading

#### GET /library/{library_id}/comic/{comic_id}/page/{page_num}

Get a specific page image.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page_num` | int | Yes | 0-indexed page number |

**Response:** Image bytes with appropriate Content-Type

**Headers:**
- `Cache-Control: public, max-age=86400`

---

### Cover Images

#### GET /library/{library_id}/comic/{comic_id}/cover

Get comic cover thumbnail (JPEG).

**Response:** JPEG image

**Headers:**
- `Cache-Control: public, max-age=31536000`

---

#### POST /library/{library_id}/comic/{comic_id}/setCustomCover

Set custom cover from a specific page.

**Form Data:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `page` | int | Yes | Page number to use as cover (0-indexed) |

**Response:** `OK`

---

### Reading Progress

#### POST /library/{library_id}/comic/{comic_id}/setCurrentPage

Update reading progress.

**Form Data:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `page` | int | Yes | Current page number |

**Response:** `OK`

---

### Continue Reading

#### GET /library/continue-reading

Get "Continue Reading" list.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 10 | Maximum results |

**Response Format:**
```
type:continue-reading\r\n
code:0\r\n
\r\n
comic:filename.cbz\r\n
id:123\r\n
libraryId:1\r\n
library:Library Name\r\n
currentPage:5\r\n
totalPages:24\r\n
progress:20.8\r\n
lastRead:1234567890\r\n
hash:abc123\r\n
\r\n
```

---

### Search

#### GET/POST /library/{library_id}/search

Search for comics.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Search query |

**Response Format:**
```
type:search\r\n
code:0\r\n
\r\n
comic:matching-comic.cbz\r\n
id:123\r\n
\r\n
```

---

### Sync

#### POST /library/sync

Sync reading progress.

**Request Body (JSON):**
```json
{
    "comics": [
        {"comicId": 123, "currentPage": 5, "totalPages": 20},
        {"comicId": 124, "currentPage": 10, "totalPages": 30}
    ]
}
```

**Response:** `OK: Synced X comics`

---

## API v2 (`/v2/*`)

**Files:** `src/api/routers/v2/*.py`

JSON format API with enhanced features.

### Version

#### GET /v2/version

Get server version.

**Response:** Plain text `9.14.2`

---

### Libraries

**File:** `src/api/routers/v2/libraries.py`

#### GET /v2/libraries

List all libraries with stats.

**Response:**
```json
[
    {
        "id": 1,
        "uuid": "abc-123-def",
        "name": "Comics",
        "path": "/path/to/comics",
        "created_at": 1234567890,
        "updated_at": 1234567890,
        "last_scan_at": 1234567890,
        "scan_status": "idle",
        "scan_interval": 60,
        "comic_count": 500,
        "folder_count": 50
    }
]
```

---

#### GET /v2/library/{library_id}/info

Get single library details.

---

#### POST /v2/libraries

Create new library.

**Request Body:**
```json
{
    "name": "My Comics",
    "path": "/path/to/comics",
    "settings": {},
    "scan_interval": 60
}
```

---

#### PUT /v2/libraries/{library_id}

Update library.

**Request Body:**
```json
{
    "name": "Updated Name",
    "path": "/new/path",
    "settings": {},
    "scan_interval": 120
}
```

---

#### DELETE /v2/libraries/{library_id}

Delete library.

**Response:**
```json
{"success": true, "message": "Library deleted"}
```

---

#### POST /v2/libraries/{library_id}/scan

Trigger manual scan.

**Response:**
```json
{"success": true, "message": "Scan started"}
```

---

#### GET /v2/libraries/{library_id}/scan/progress

Get file scan progress.

**Response:**
```json
{
    "in_progress": true,
    "current": 150,
    "total": 500,
    "message": "Processing..."
}
```

---

### Folders

**File:** `src/api/routers/v2/folders.py`

#### GET /v2/library/{library_id}/folder/{folder_id}

Get folder contents (JSON format).

**Response:**
```json
[
    {
        "type": "folder",
        "id": "123",
        "name": "Subfolder"
    },
    {
        "type": "comic",
        "id": "456",
        "file_name": "comic.cbz",
        "file_size": "12345678",
        "hash": "abc123",
        "num_pages": 24,
        "current_page": 5,
        "read": false
    }
]
```

---

### Comics

**File:** `src/api/routers/v2/comics.py`

#### GET /v2/library/{library_id}/comic/{comic_id}/remote

Get comic info for remote reading.

---

### Reading

**File:** `src/api/routers/v2/reading.py`

#### POST /v2/library/{library_id}/comic/{comic_id}/progress

Update reading progress (JSON).

**Request Body:**
```json
{
    "current_page": 10,
    "is_completed": false
}
```

---

### Search

**File:** `src/api/routers/v2/search.py`

#### GET/POST /v2/library/{library_id}/search

Basic search.

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Search query |

**Response:**
```json
[
    {
        "type": "comic",
        "id": "123",
        "file_name": "comic.cbz",
        "hash": "abc123",
        "path": "/relative/path/comic.cbz",
        "current_page": 0,
        "num_pages": 24,
        "read": false
    }
]
```

---

#### GET/POST /v2/library/{library_id}/search/advanced

Advanced search with filters.

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Search query with field:value syntax |
| `limit` | int | Max results (default 100) |
| `offset` | int | Skip results (default 0) |

**Query Syntax:**
- `writer:Stan Lee`
- `genre:superhero`
- `year:1990`
- Boolean: AND, OR, NOT

**Response:**
```json
{
    "results": [...],
    "total": 150,
    "limit": 100,
    "offset": 0
}
```

---

#### GET /v2/library/{library_id}/search/fields

Get searchable fields.

---

#### GET /v2/search/query/parse

Parse and explain a search query.

---

### Tree

**File:** `src/api/routers/v2/tree.py`

#### GET /v2/library/{library_id}/tree

Get hierarchical folder tree.

**Response:**
```json
{
    "id": 1,
    "name": "Library Name",
    "type": "library",
    "comic_count": 500,
    "children": [
        {
            "id": 10,
            "name": "Folder",
            "type": "folder",
            "comic_count": 50,
            "children": [...]
        }
    ]
}
```

---

#### GET /v2/libraries/series-tree

Get tree of all libraries with cached folder structure.

---

### Series

**File:** `src/api/routers/v2/series.py`

#### GET /v2/library/{library_id}/series

Get all series in library.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sort` | string | "name" | Sort: name, recent, progress |
| `include_metadata` | bool | true | Include writer, artist, etc. |

**Response:**
```json
[
    {
        "id": 123,
        "name": "One Piece",
        "series_name": "One Piece",
        "volumes": [...],
        "publisher": "Shueisha",
        "total_issues": 105,
        "cover_hash": "abc123",
        "year": 1997
    }
]
```

---

#### GET /v2/library/{library_id}/series/{series_name}

Get detailed series information.

**Response:**
```json
{
    "id": 123,
    "name": "One Piece",
    "display_name": "One Piece",
    "total_issues": 105,
    "completed_volumes": 50,
    "overall_progress": 47.6,
    "cover_hash": "abc123",
    "synopsis": "...",
    "writer": "Eiichiro Oda",
    "volumes": [
        {
            "id": "1",
            "title": "Volume 1",
            "volume": 1,
            "hash": "abc123",
            "num_pages": 200,
            "current_page": 150,
            "is_completed": false
        }
    ]
}
```

---

### Covers

**File:** `src/api/routers/v2/covers.py`

#### GET /v2/cover/{hash}

Get cover by hash.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `format` | string | "jpeg" | jpeg or webp |

---

### Collections

**File:** `src/api/routers/v2/collections.py`

CRUD operations for user collections.

---

### Session

**File:** `src/api/routers/v2/session.py`

Session management for mobile apps.

---

### Admin

**File:** `src/api/routers/v2/admin.py`

Administrative operations.

---

### Internal Helpers

The v2 API uses shared internal modules (prefixed with `_`):

| Module | Purpose |
|--------|---------|
| `_browse_helpers.py` | Browse page data assembly and pagination |
| `_item_builders.py` | Response object builders for comics, folders, series |
| `_shared.py` | Shared utilities, dependency injection, common types |

---

## Top-Level Covers Router

**File:** `src/api/routers/covers.py`

Serves cover images by hash, used by both v1 and v2 APIs.

---

## Modern API v1 (`/api/v1/*`)

**File:** `src/api/routers/libraries.py`

### GET /api/v1/libraries

List libraries.

### POST /api/v1/libraries

Create library.

### PUT /api/v1/libraries/{id}

Update library.

### DELETE /api/v1/libraries/{id}

Delete library.

---

## Kottlib Native API (`/api/*`)

**Package:** `src/api/routers/app_api/`

Primary namespace used by the WebUI and internal clients. This layer exposes
stable, client-friendly endpoint naming and reuses v2 implementations where
possible.

### Key endpoint groups

- Libraries and browse: `/api/libraries`, `/api/libraries/tree`, `/api/browse/libraries/*`
- Comics and reading: `/api/libraries/{library_id}/comics/*`, `/api/reading`
- Collections: `/api/favorites`, `/api/libraries/{library_id}/reading-lists/*`
- Search: `/api/libraries/{library_id}/search*`, `/api/search/query/parse`
- Admin and config aliases: `/api/admin/*`, `/api/config`
- Scanners alias: `/api/scanners/*`

---

## Modern API v2 (`/api/v2/*`)

Compatibility namespace retained for legacy clients.

### User Interactions

**File:** `src/api/routers/user_interactions.py`

#### GET /api/v2/favorites

Get user favorites.

#### POST /api/v2/favorites

Add favorite.

#### DELETE /api/v2/favorites/{id}

Remove favorite.

---

### Configuration

**File:** `src/api/routers/config.py`

#### GET /api/v2/config

Get server configuration.

#### PUT /api/v2/config

Update configuration.

---

## Scanners API (`/v2/scanners/*`, `/api/scanners/*`)

**Package:** `src/api/routers/scanners/`

Also mounted under `/api/scanners/*` via the Kottlib-native API router.

The scanners API is organized as a package with the following modules:
- `router.py` — Main router definition
- `manager.py` — Scanner manager integration
- `models.py` — Request/response Pydantic models
- `progress.py` — Scan progress tracking
- `endpoints/` — Individual endpoint modules (`available.py`, `configure.py`, `scan_comic.py`, `scan_library.py`, `scan_single.py`, `apply_comic.py`, `metadata.py`)
- `tasks/` — Background scan task management

### Scanner Management

#### GET /v2/scanners/available

Get available scanners.

**Response:**
```json
[
    {
        "name": "AniList",
        "scan_level": "series",
        "description": "Manga metadata from AniList",
        "requires_config": false,
        "config_keys": [],
        "config_schema": [...],
        "provided_fields": ["title", "description", "genre"],
        "primary_fields": ["title", "description"]
    }
]
```

---

#### GET /v2/scanners/libraries

Get scanner configurations for all libraries.

**Response:**
```json
[
    {
        "library_id": 1,
        "library_name": "Manga",
        "library_path": "/path/to/manga",
        "primary_scanner": "AniList",
        "scan_level": "series",
        "fallback_scanners": [],
        "fallback_threshold": 0.7,
        "confidence_threshold": 0.4,
        "scanner_configs": {}
    }
]
```

---

#### PUT /v2/scanners/libraries/{library_id}/configure

Configure scanner for library.

**Request Body:**
```json
{
    "primary_scanner": "AniList",
    "fallback_scanners": [],
    "confidence_threshold": 0.4,
    "fallback_threshold": 0.7,
    "scanner_configs": {
        "ComicVine": {"api_key": "..."}
    }
}
```

---

#### POST /v2/scanners/verify-credentials/{scanner_name}

Verify scanner credentials.

**Request Body:**
```json
{
    "username": "user",
    "password": "pass"
}
```

---

### Scanning Operations

#### POST /v2/scanners/scan

Scan single file/series.

**Request Body:**
```json
{
    "query": "One Piece",
    "library_id": 1,
    "scanner_name": null,
    "confidence_threshold": 0.4
}
```

**Response:**
```json
{
    "confidence": 0.95,
    "confidence_level": "EXACT",
    "source_id": "21",
    "source_url": "https://anilist.co/manga/21",
    "metadata": {
        "title": "One Piece",
        "description": "...",
        "genre": "Action, Adventure"
    },
    "tags": ["action", "adventure", "pirates"]
}
```

---

#### POST /v2/scanners/scan/bulk

Bulk scan multiple items.

**Request Body:**
```json
{
    "queries": ["One Piece", "Naruto", "Bleach"],
    "library_id": 1,
    "confidence_threshold": 0.4
}
```

**Response:**
```json
{
    "total": 3,
    "matched": 2,
    "rejected": 1,
    "results": [...]
}
```

---

#### POST /v2/scanners/scan/comic

Scan single comic.

**Request Body:**
```json
{
    "comic_id": 123,
    "overwrite": false,
    "confidence_threshold": 0.4
}
```

---

#### POST /v2/scanners/scan/library

Scan entire library (background task).

**Request Body:**
```json
{
    "library_id": 1,
    "overwrite": false,
    "confidence_threshold": 0.4,
    "rescan_existing": false
}
```

**Response:**
```json
{
    "status": "started",
    "message": "Library scan started in background..."
}
```

---

#### GET /v2/scanners/scan/library/{library_id}/progress

Get library scan progress.

**Response:**
```json
{
    "in_progress": true,
    "completed": false,
    "processed": 50,
    "scanned": 45,
    "total": 100,
    "failed": 3,
    "skipped": 2,
    "error": null
}
```

---

#### DELETE /v2/scanners/scan/library/{library_id}/progress

Clear scan progress.

---

#### POST /v2/scanners/clear-metadata

Clear metadata from comics.

**Request Body:**
```json
{
    "comic_ids": [1, 2, 3],
    "library_id": null,
    "clear_scanner_info": true,
    "clear_tags": true,
    "clear_metadata": false
}
```

---

#### GET /v2/scanners/test/{scanner_name}

Test scanner with query.

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | string | Test query |

**Response:**
```json
{
    "scanner": "nhentai",
    "query": "test",
    "result": {...},
    "candidates_count": 5
}
```

---

## Common Response Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad request (validation error) |
| 404 | Resource not found |
| 409 | Conflict (scan already in progress) |
| 500 | Internal server error |

## Authentication

Currently, authentication is optional:
- Session cookie: `yacread_session`
- Auto-created admin user on first access
- User association via session middleware
