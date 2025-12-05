# Data Flow Documentation

## Overview

This document describes the end-to-end data flows through the Kottlib system with sequence diagrams.

---

## Flow 1: Library Scanning

The process of discovering and indexing comics in a library.

```mermaid
sequenceDiagram
    participant User
    participant WebUI
    participant FastAPI
    participant ThreadedScanner
    participant ComicLoader
    participant ThumbnailGen
    participant Database
    participant FileSystem

    User->>WebUI: Click "Scan Library"
    WebUI->>FastAPI: POST /v2/libraries/{id}/scan
    FastAPI->>FastAPI: Start background task
    FastAPI-->>WebUI: {"status": "started"}

    loop Progress Polling
        WebUI->>FastAPI: GET /v2/libraries/{id}/scan/progress
        FastAPI-->>WebUI: {"current": N, "total": M}
    end

    FastAPI->>ThreadedScanner: scan_library(path)
    
    Note over ThreadedScanner: Phase 1: Discovery
    ThreadedScanner->>FileSystem: Scan directory tree
    FileSystem-->>ThreadedScanner: List of comic files
    
    ThreadedScanner->>Database: Create folder records
    
    Note over ThreadedScanner: Phase 2: Processing (Multi-threaded)
    loop For each comic file
        ThreadedScanner->>ComicLoader: open_comic(path)
        ComicLoader->>FileSystem: Read archive
        ComicLoader-->>ThreadedScanner: ComicArchive
        
        ThreadedScanner->>ComicLoader: Extract ComicInfo.xml
        ComicLoader-->>ThreadedScanner: Metadata
        
        ThreadedScanner->>ThumbnailGen: Generate thumbnails
        ThumbnailGen->>ComicLoader: Extract cover page
        ThumbnailGen->>FileSystem: Save JPEG + WebP
        
        ThreadedScanner->>Database: Create comic record
    end
    
    Note over ThreadedScanner: Phase 3: Post-processing
    ThreadedScanner->>Database: Rebuild series table
    ThreadedScanner->>Database: Cache series tree
    
    ThreadedScanner-->>FastAPI: ScanResult
    FastAPI->>Database: Update scan status
```

### Key Steps

1. **User Trigger**: Manual scan via Web UI or scheduled job
2. **Background Task**: Scan runs asynchronously to not block API
3. **Discovery Phase**: Fast single-threaded file enumeration
4. **Processing Phase**: Multi-threaded comic processing
5. **Post-Processing**: Series aggregation and cache building

---

## Flow 2: Mobile App Reading

YACReader mobile app reading a comic.

```mermaid
sequenceDiagram
    participant App as YACReader App
    participant FastAPI
    participant Database
    participant ComicLoader
    participant FileSystem
    participant Covers

    Note over App: Initial Sync
    App->>FastAPI: GET /library/
    FastAPI->>Database: Query libraries
    Database-->>FastAPI: Library list
    FastAPI-->>App: text: library:Name\nid:1\n...

    Note over App: Browse Library
    App->>FastAPI: GET /library/1/folder/0
    FastAPI->>Database: Query folders + comics
    Database-->>FastAPI: Results
    FastAPI-->>App: text: folder:Name\nid:10\ncomic:file.cbz\n...

    Note over App: Load Cover
    App->>FastAPI: GET /library/1/comic/123/cover
    FastAPI->>Covers: Find thumbnail
    Covers-->>FastAPI: JPEG data
    FastAPI-->>App: image/jpeg

    Note over App: Start Reading
    App->>FastAPI: GET /library/1/comic/123
    FastAPI->>Database: Get comic + progress
    Database-->>FastAPI: Comic metadata
    FastAPI-->>App: text: numpages:24\ncurrentPage:5\n...

    loop Read Pages
        App->>FastAPI: GET /library/1/comic/123/page/5
        FastAPI->>ComicLoader: open_comic(path)
        ComicLoader->>FileSystem: Read archive
        ComicLoader-->>FastAPI: Page bytes
        FastAPI-->>App: image/jpeg
        
        App->>FastAPI: POST /library/1/comic/123/setCurrentPage
        FastAPI->>Database: Update progress
        FastAPI-->>App: OK
    end
```

### Key Points

- **Plain Text Format**: Legacy API uses `\r\n` delimited text
- **Session Cookie**: `yacread_session` for user identification
- **Progress Tracking**: Page updates sent on navigation
- **Cover Caching**: 1-year cache headers for covers

---

## Flow 3: Web UI Browsing

Modern web interface browsing experience.

```mermaid
sequenceDiagram
    participant Browser
    participant SvelteKit
    participant TanStackQuery
    participant FastAPI
    participant Database

    Browser->>SvelteKit: Navigate to /
    SvelteKit->>FastAPI: GET /v2/libraries
    FastAPI->>Database: Query libraries
    Database-->>FastAPI: Libraries
    FastAPI-->>SvelteKit: JSON [{id, name, ...}]
    SvelteKit-->>Browser: Render library list

    Note over Browser: TanStack Query caching
    Browser->>TanStackQuery: Check cache
    TanStackQuery-->>Browser: Cached data (if fresh)

    Browser->>SvelteKit: Select library
    SvelteKit->>FastAPI: GET /v2/libraries/series-tree
    FastAPI->>Database: Get cached tree
    Database-->>FastAPI: JSON tree structure
    FastAPI-->>SvelteKit: Tree data
    
    TanStackQuery->>TanStackQuery: Cache response
    Note over TanStackQuery: 15min stale, 30min cache
    
    SvelteKit-->>Browser: Render folder tree

    Browser->>SvelteKit: Open series
    SvelteKit->>FastAPI: GET /v2/library/1/series/SeriesName
    FastAPI->>Database: Query comics in series
    Database-->>FastAPI: Comics with progress
    FastAPI-->>SvelteKit: Series detail JSON
    SvelteKit-->>Browser: Render volumes grid
```

### Caching Strategy

- **TanStack Query**: Client-side caching
  - `staleTime`: 15 minutes
  - `cacheTime`: 30 minutes
- **HTTP Cache**: Server sets appropriate headers
- **Series Tree Cache**: Pre-computed during scans

---

## Flow 4: Metadata Scanning

Fetching metadata from external sources.

```mermaid
sequenceDiagram
    participant User
    participant WebUI
    participant FastAPI
    participant ScannerAPI
    participant ScannerManager
    participant Scanner as BaseScanner
    participant ExternalAPI
    participant MetadataService
    participant Database

    User->>WebUI: Configure scanner
    WebUI->>FastAPI: PUT /v2/scanners/libraries/1/configure
    FastAPI->>Database: Save scanner config
    FastAPI-->>WebUI: Updated config

    User->>WebUI: Scan library metadata
    WebUI->>ScannerAPI: POST /v2/scanners/scan/library
    ScannerAPI->>ScannerAPI: Start background task
    ScannerAPI-->>WebUI: {"status": "started"}

    ScannerAPI->>ScannerManager: get_scanner("AniList")
    ScannerManager-->>ScannerAPI: AniListScanner instance

    loop For each series/comic
        ScannerAPI->>Scanner: scan(query)
        Scanner->>ExternalAPI: API request
        
        alt Rate Limited
            ExternalAPI-->>Scanner: 429 Too Many Requests
            Scanner->>Scanner: Wait and retry
            Scanner->>ExternalAPI: Retry request
        end
        
        ExternalAPI-->>Scanner: Metadata response
        Scanner-->>ScannerAPI: ScanResult
        
        alt Confidence >= threshold
            ScannerAPI->>MetadataService: apply_scan_result_to_comic()
            MetadataService->>Database: Update comic/series
            Database-->>MetadataService: Success
        else Low confidence
            ScannerAPI->>ScannerAPI: Skip or try fallback
        end
        
        ScannerAPI->>Database: Update progress
    end

    ScannerAPI->>Database: Mark scan complete
```

### Scanner Levels

| Level | Behavior | Example |
|-------|----------|---------|
| FILE | Scan each comic individually | nhentai (by ID) |
| SERIES | Scan unique series names | AniList, Comic Vine |

### Rate Limiting

- **AniList**: 90 requests/minute
- **MangaDex**: 5 requests/second
- **Comic Vine**: Varies by API tier

---

## Flow 5: Scheduled Scanning

Automatic periodic library scans.

```mermaid
sequenceDiagram
    participant APScheduler
    participant SchedulerService
    participant Database
    participant ThreadedScanner
    participant FileSystem

    Note over APScheduler: Server Startup
    APScheduler->>SchedulerService: Initialize
    SchedulerService->>Database: Load library schedules
    Database-->>SchedulerService: Libraries with scan_interval > 0
    
    loop For each scheduled library
        SchedulerService->>APScheduler: Add job (IntervalTrigger)
    end

    Note over APScheduler: Timer Fires
    APScheduler->>SchedulerService: _run_scan(library_id)
    
    SchedulerService->>Database: Get library path
    Database-->>SchedulerService: Library record
    
    SchedulerService->>ThreadedScanner: scan_library(path)
    
    ThreadedScanner->>FileSystem: Discover files
    
    alt File Unchanged
        ThreadedScanner->>Database: Check path + mtime
        Database-->>ThreadedScanner: Existing record
        ThreadedScanner->>ThreadedScanner: Skip (fast path)
    else File Modified
        ThreadedScanner->>ThreadedScanner: Calculate hash
        ThreadedScanner->>Database: Create/update record
    end
    
    ThreadedScanner-->>SchedulerService: ScanResult
    SchedulerService->>Database: Update last_scan_completed
```

### Schedule Management

- **Job ID Format**: `scan_library_{library_id}`
- **Trigger**: `IntervalTrigger(minutes=scan_interval)`
- **Persistence**: In-memory (reloaded from DB on restart)
- **Disable**: Set `scan_interval = 0`

---

## Flow 6: Cover Generation

Custom cover selection and generation.

```mermaid
sequenceDiagram
    participant User
    participant WebUI
    participant FastAPI
    participant ComicLoader
    participant ThumbnailGen
    participant Database
    participant FileSystem

    User->>WebUI: Open comic reader
    User->>WebUI: Select page as cover
    
    WebUI->>FastAPI: POST /library/1/comic/123/setCustomCover
    Note over FastAPI: Form: page=5
    
    FastAPI->>Database: Get comic record
    Database-->>FastAPI: Comic with path
    
    FastAPI->>ComicLoader: open_comic(path)
    ComicLoader->>FileSystem: Read archive
    ComicLoader-->>FastAPI: ComicArchive
    
    FastAPI->>ComicLoader: get_page(5)
    ComicLoader-->>FastAPI: Page image data
    
    FastAPI->>ThumbnailGen: generate_dual_thumbnails(image, hash_custom)
    ThumbnailGen->>FileSystem: Save covers/ab/{hash}_custom.jpg
    ThumbnailGen->>FileSystem: Save covers/ab/{hash}_custom.webp
    
    FastAPI->>Database: Create cover record (type=custom)
    
    FastAPI-->>WebUI: OK

    Note over User: Later: Load cover
    WebUI->>FastAPI: GET /library/1/comic/123/cover
    FastAPI->>Database: get_best_cover(comic_id)
    Database-->>FastAPI: Custom cover record
    FastAPI->>FileSystem: Read custom cover
    FileSystem-->>FastAPI: JPEG data
    FastAPI-->>WebUI: image/jpeg
```

### Cover Priority

1. **Custom Cover**: User-selected page
2. **Auto Cover**: First page extracted during scan
3. **Fallback**: Extract on-demand if missing

### Storage Structure

```
covers/
├── ab/
│   ├── abc123def456.jpg      # Auto JPEG
│   ├── abc123def456.webp     # Auto WebP
│   ├── abc123def456_custom.jpg   # Custom JPEG
│   └── abc123def456_custom.webp  # Custom WebP
└── cd/
    └── ...
```

---

## Flow 7: Search Query

Full-text search execution.

```mermaid
sequenceDiagram
    participant User
    participant WebUI
    participant FastAPI
    participant EnhancedSearch
    participant SQLite
    participant Database

    User->>WebUI: Enter search query
    WebUI->>FastAPI: GET /v2/library/1/search?q=batman

    FastAPI->>EnhancedSearch: search_with_fts(session, library_id, "batman")
    
    EnhancedSearch->>EnhancedSearch: Parse query
    Note over EnhancedSearch: field:value → field-specific search<br/>plain text → FTS match
    
    alt FTS Available
        EnhancedSearch->>SQLite: FTS5 MATCH query
        SQLite-->>EnhancedSearch: Ranked results
    else Fallback
        EnhancedSearch->>Database: LIKE query on title, series, etc.
        Database-->>EnhancedSearch: Results
    end
    
    EnhancedSearch->>Database: Get reading progress
    Database-->>EnhancedSearch: Progress records
    
    EnhancedSearch-->>FastAPI: Comics with metadata
    FastAPI-->>WebUI: JSON results
    WebUI-->>User: Display results
```

### Search Features

- **Full-Text Search**: SQLite FTS5 when available
- **Field-Specific**: `writer:Stan Lee`, `genre:action`
- **Boolean Logic**: AND, OR, NOT
- **Fallback**: LIKE queries if FTS unavailable

---

## Data Synchronization

### Reading Progress Sync

```
Mobile App → setCurrentPage → Database ← Web UI
                                ↓
                          Reading Progress Record
                                ↓
                          Continue Reading List
```

### Library State

```
File System Changes
        ↓
Scheduled/Manual Scan
        ↓
Database Records Updated
        ↓
Series Tree Cache Rebuilt
        ↓
UI Receives Fresh Data
```

---

## Error Handling Flows

### Scan Error Recovery

```mermaid
flowchart TD
    A[Start Scan] --> B{File Accessible?}
    B -->|Yes| C[Process Comic]
    B -->|No| D[Log Error]
    D --> E[Increment Error Count]
    E --> F[Continue Next File]
    
    C --> G{Parse Success?}
    G -->|Yes| H[Save to DB]
    G -->|No| D
    
    H --> I{Thumbnail Generated?}
    I -->|Yes| F
    I -->|No| J[Log Warning]
    J --> F
    
    F --> K{More Files?}
    K -->|Yes| B
    K -->|No| L[Complete Scan]
    L --> M[Return ScanResult with error count]
```

### API Error Responses

| Code | Scenario | User Action |
|------|----------|-------------|
| 400 | Invalid request | Check parameters |
| 404 | Resource not found | Verify ID exists |
| 409 | Scan in progress | Wait for completion |
| 500 | Server error | Check logs |
