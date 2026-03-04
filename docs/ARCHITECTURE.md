# Kottlib (Kottlib) - Architecture Documentation

## Overview

Kottlib (Kottlib) is a modern comic library server with full backward compatibility with YACReader mobile apps. It provides a FastAPI backend, SQLite database, and SvelteKit web frontend for managing and reading comic collections.

## System Architecture Diagram

```mermaid
graph TB
    subgraph "Clients"
        WebUI[SvelteKit Web UI]
        YACReader[YACReader Mobile Apps]
        OtherClients[Third-party Clients]
    end

    subgraph "Backend - FastAPI Server"
        direction TB
        API[API Layer]
        
        subgraph "API Routers"
            LegacyV1[Legacy v1 API<br/>Plain Text Format]
            APIV2[API v2<br/>JSON Format]
            ModernV1[Modern API v1<br/>Libraries CRUD]
            ModernV2[Modern API v2<br/>User Interactions]
            ScannersAPI[Scanners API<br/>Metadata Operations]
        end
        
        subgraph "Services"
            MetadataService[Metadata Service]
            SchedulerService[Scheduler Service]
            MangaDexClient[MangaDex Client]
            LibraryService[Library Service]
            CoverService[Cover Service]
            ReadingService[Reading Service]
            ScanService[Scan Service]
            SearchService[Search Service]
            ComicInfoService[Comic Info Service]
            ConfigSync[Config Sync]
            LibraryCache[Library Cache]
        end
        
        subgraph "Scanner"
            ComicLoader[Comic Loader]
            ThumbnailGen[Thumbnail Generator]
            ThreadedScanner[Threaded Scanner]
            ToolCheck[Tool Check]
        end
        
        subgraph "Metadata Scanners"
            ScannerManager[Scanner Manager]
            BaseScanner[Base Scanner Framework]
            PluginScanners[Plugin Scanners<br/>nhentai, AniList, ComicVine, etc.]
        end
    end

    subgraph "Data Layer"
        Database[(SQLite Database)]
        Covers[/Covers Directory/]
        ComicFiles[/Comic Archives<br/>CBZ, CBR, CB7/]
    end

    WebUI --> APIV2
    WebUI --> ModernV2
    WebUI --> ScannersAPI
    YACReader --> LegacyV1
    YACReader --> APIV2
    OtherClients --> ModernV1

    API --> LegacyV1
    API --> APIV2
    API --> ModernV1
    API --> ModernV2
    API --> ScannersAPI

    APIV2 --> MetadataService
    ScannersAPI --> ScannerManager
    ScannerManager --> BaseScanner
    BaseScanner --> PluginScanners
    
    MetadataService --> Database
    SchedulerService --> ThreadedScanner
    ThreadedScanner --> ComicLoader
    ThreadedScanner --> ThumbnailGen
    ThreadedScanner --> Database

    ComicLoader --> ComicFiles
    ThumbnailGen --> Covers
    
    LegacyV1 --> Database
    APIV2 --> Database
    ModernV1 --> Database
    ModernV2 --> Database
```

## Component Relationships

### Frontend ↔ Backend Communication

```mermaid
sequenceDiagram
    participant Web as SvelteKit WebUI
    participant Mobile as YACReader Mobile
    participant API as FastAPI Backend
    participant DB as SQLite Database
    participant Files as Comic Archives

    Web->>API: GET /v2/libraries (JSON)
    API->>DB: Query libraries
    DB-->>API: Library list
    API-->>Web: JSON response

    Mobile->>API: GET /library/ (Plain text)
    API->>DB: Query libraries
    DB-->>API: Library list
    API-->>Mobile: Plain text response

    Web->>API: GET /v2/library/{id}/comic/{id}/cover
    API->>Files: Load cover from cache or archive
    Files-->>API: Image data
    API-->>Web: JPEG/WebP image

    Mobile->>API: POST /library/{id}/comic/{id}/setCurrentPage
    API->>DB: Update reading progress
    DB-->>API: Success
    API-->>Mobile: OK
```

## Technology Stack

### Backend
| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Web Framework | FastAPI | 0.104+ | Async REST API with automatic OpenAPI docs |
| Database ORM | SQLAlchemy | 2.0+ | Database abstraction with type hints |
| Database | SQLite | 3.x | Lightweight embedded database |
| Task Scheduler | APScheduler | 3.x | Background job scheduling for library scans |
| Image Processing | Pillow | 10.x | Thumbnail generation and image manipulation |
| Archive Handling | zipfile, rarfile, py7zr | stdlib/3rd party | Comic archive extraction |
| HTTP Client | requests | 2.x | External API calls (MangaDex, metadata scanners) |
| YAML Parser | PyYAML | 6.x | Configuration file parsing |

### Frontend
| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Framework | SvelteKit | 2.x | Modern SSR-capable frontend |
| Styling | TailwindCSS | 3.x | Utility-first CSS framework |
| State Management | Svelte Stores | native | Reactive state management |
| Data Fetching | TanStack Query | 5.x | Server state caching (15min stale, 30min cache) |
| Build Tool | Vite | 5.x | Fast development and production builds |

### External APIs
| Service | Purpose | Rate Limit |
|---------|---------|------------|
| MangaDex | Cover art, manga metadata | 5 req/sec |
| nhentai | Doujinshi metadata | Variable |
| AniList | Anime/manga metadata (GraphQL) | 90 req/min |
| Comic Vine | Western comics metadata | Requires API key |
| Metron | Comics database | Requires credentials |

## Data Flow Overview

```mermaid
flowchart LR
    subgraph Input
        UI[Web UI]
        Mobile[Mobile Apps]
        CLI[CLI/Scripts]
    end

    subgraph Processing
        Backend[FastAPI Backend]
        Scanner[Library Scanner]
        MetaScanner[Metadata Scanners]
    end

    subgraph Storage
        DB[(SQLite DB)]
        Covers[/Covers/]
        Archives[/Comic Files/]
    end

    subgraph External
        ExtAPIs[External APIs<br/>MangaDex, AniList, etc.]
    end

    UI --> Backend
    Mobile --> Backend
    CLI --> Backend

    Backend --> DB
    Backend --> Covers
    Backend --> Archives

    Scanner --> DB
    Scanner --> Covers
    Scanner --> Archives

    MetaScanner --> ExtAPIs
    MetaScanner --> DB
```

## Directory Structure

```
Kottlib/
├── src/                          # Backend source code
│   ├── api/                      # FastAPI application
│   │   ├── main.py              # Application entry point
│   │   ├── middleware/          # Request middleware (session, CORS)
│   │   └── routers/             # API endpoint definitions
│   │       ├── legacy_v1.py     # YACReader v1 compatible API
│   │       ├── libraries.py     # Modern library CRUD
│   │       ├── user_interactions.py  # Favorites, progress
│   │       ├── config.py        # Server configuration API
│   │       ├── covers.py        # Cover serving endpoints
│   │       ├── scanners/        # Metadata scanner endpoints (package)
│   │       │   ├── router.py    # Main router
│   │       │   ├── manager.py   # Scanner manager integration
│   │       │   ├── models.py    # Request/response models
│   │       │   ├── progress.py  # Scan progress tracking
│   │       │   ├── endpoints/   # Individual endpoint modules
│   │       │   └── tasks/       # Background scan tasks
│   │       └── v2/              # JSON-format v2 API
│   │           ├── libraries.py
│   │           ├── folders.py
│   │           ├── comics.py
│   │           ├── reading.py
│   │           ├── search.py
│   │           ├── series.py
│   │           ├── covers.py
│   │           ├── collections.py
│   │           ├── session.py
│   │           ├── admin.py
│   │           ├── tree.py      # Library tree endpoints
│   │           ├── _browse_helpers.py  # Browse utilities
│   │           ├── _item_builders.py   # Response builders
│   │           └── _shared.py          # Shared utilities
│   ├── database/                # Database layer
│   │   ├── connection.py       # Database connection manager
│   │   ├── enhanced_search.py  # FTS search implementation
│   │   ├── search_index.py     # FTS5 index management
│   │   ├── paths.py            # Path utilities
│   │   ├── models/             # SQLAlchemy ORM models (15 tables)
│   │   │   ├── base.py         # Declarative base
│   │   │   ├── library.py      # Library, Folder
│   │   │   ├── comic.py        # Comic, Cover
│   │   │   ├── series.py       # Series
│   │   │   ├── user.py         # User, Session
│   │   │   ├── reading.py      # ReadingProgress
│   │   │   ├── reading_list.py # ReadingList, ReadingListItem
│   │   │   ├── collection.py   # Collection
│   │   │   └── setting.py      # Setting
│   │   ├── operations/         # CRUD operations (12 modules)
│   │   │   ├── comic.py, cover.py, favorite.py, folder.py
│   │   │   ├── label.py, library.py, progress.py
│   │   │   ├── reading_list.py, session.py, setting.py
│   │   │   └── stats.py, user.py
│   │   └── migrations/         # Database migration scripts
│   ├── scanner/                 # Library file scanning
│   │   ├── base.py             # ScanResult dataclass
│   │   ├── comic_loader.py     # Archive extraction (CBZ/CBR/CB7)
│   │   ├── comic_processor.py  # Single comic processing
│   │   ├── file_discovery.py   # File discovery functions
│   │   ├── folder_manager.py   # Folder creation/management
│   │   ├── series_builder.py   # Series table rebuilding
│   │   ├── structure_classifier.py # Library structure classification
│   │   ├── threaded_scanner.py # Multi-threaded scanner
│   │   ├── thumbnail_generator.py # Cover generation
│   │   ├── cleanup.py          # Orphan cleanup
│   │   ├── tool_check.py       # External tool verification
│   │   └── loaders/            # Format-specific archive loaders
│   │       ├── base.py, zip.py, rar.py, sevenzip.py, utils.py
│   ├── metadata_providers/       # Metadata scanner framework (v2)
│   │   ├── base.py             # Abstract scanner interface (BaseScanner)
│   │   ├── manager.py          # Scanner registry and discovery
│   │   ├── schema.py           # Field mapping definitions
│   │   ├── config.py           # Configuration option definitions
│   │   ├── utils.py            # Utilities (clean_query, etc.)
│   │   └── demo.py             # Demo scanner for testing
│   ├── scanners/                # Deprecated compatibility shim
│   │   └── (re-exports from metadata_providers)
│   ├── services/                # Business logic services
│   │   ├── metadata_service.py # Apply scanner results to comics
│   │   ├── scheduler.py        # APScheduler integration
│   │   ├── mangadex_client.py  # MangaDex API client
│   │   ├── comic_info_service.py # Shared v1/v2 comic metadata
│   │   ├── config_sync.py      # Config file ↔ database sync
│   │   ├── cover_service.py    # Cover generation/retrieval
│   │   ├── library_cache.py    # File-based browse cache
│   │   ├── library_service.py  # Library CRUD with stats
│   │   ├── reading_service.py  # Progress, favorites, labels
│   │   ├── scan_service.py     # Scan orchestration
│   │   └── search_service.py   # FTS and advanced search
│   ├── covers/                  # Cover provider framework
│   │   ├── base_provider.py    # Abstract cover provider
│   │   └── provider_manager.py # Cover provider management
│   ├── utils/                   # Utilities
│   │   ├── errors.py           # Error types
│   │   ├── hashing.py          # Hash functions
│   │   ├── pagination.py       # Pagination helpers
│   │   ├── platform.py         # Platform-specific paths
│   │   ├── series_utils.py     # Series detection
│   │   └── sorting.py          # Natural sort
│   ├── config.py               # Configuration management
│   └── init_db.py              # Database initialization script
├── scanners/                    # Plugin metadata scanners
│   ├── nhentai/
│   │   └── nhentai_scanner.py
│   ├── AniList/
│   │   └── anilist_scanner.py
│   ├── ComicVine/
│   │   └── comic_vine_scanner.py
│   ├── mangadex/
│   │   └── mangadex_scanner.py
│   └── metron/
│       └── metron_scanner.py
├── webui/                       # SvelteKit frontend
│   ├── src/
│   │   ├── routes/             # Page routes
│   │   │   ├── +page.svelte    # Home/Library browser
│   │   │   ├── admin/          # Admin dashboard
│   │   │   ├── browse/         # Global browse
│   │   │   ├── comic/[libraryId]/[comicId]/  # Comic reader
│   │   │   ├── library/[libraryId]/browse/   # Library browser
│   │   │   ├── reading-lists/  # Reading lists
│   │   │   ├── search/         # Search interface
│   │   │   ├── favorites/      # User favorites
│   │   │   └── continue-reading/
│   │   └── lib/
│   │       ├── api/            # API client modules
│   │       ├── components/     # Reusable UI components
│   │       ├── stores/         # Svelte stores
│   │       ├── themes/         # Theme definitions (16 themes)
│   │       ├── actions/        # Svelte actions (tooltip, etc.)
│   │       ├── server/         # Server-side utilities
│   │       └── utils/          # Helper functions
│   ├── static/                 # Static assets
│   └── package.json
├── tests/                       # Test suite
├── docs/                        # Documentation
├── scripts/                     # Utility scripts
├── requirements.txt            # Python dependencies
├── start.sh                    # Full stack startup script
├── start_backend.sh            # Backend only startup
└── start_webui.sh              # Frontend only startup
```

## Key Design Decisions

### 1. Multi-API Architecture
The server exposes multiple API formats to support different clients:
- **Legacy v1**: Plain text format for YACReader mobile apps backward compatibility
- **API v2**: JSON format for enhanced YACReader features
- **Modern API**: RESTful JSON for web UI and third-party integrations

### 2. Pluggable Scanner System
Metadata scanners are discovered dynamically from the `scanners/` directory:
- Each scanner extends `BaseScanner`
- Scanners define their own configuration schemas
- ScannerManager handles registration and instantiation

### 3. Per-Library Database
While there's a main database for configuration, each library can have its own data:
- Enables library-specific settings
- Supports distributed/federated setups

### 4. Dual Thumbnail Format
Covers are generated in both JPEG and WebP:
- JPEG (300px) for mobile app compatibility
- WebP (400px) for web UI efficiency

### 5. Cached Series Tree
Library folder structures are pre-computed during scans:
- Stored as JSON in `library.cached_series_tree`
- Eliminates N+1 queries on page load
- Refreshed on each library scan
