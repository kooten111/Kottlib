# YACLib Enhanced - Architecture Design

## Project Goals

Build a modern web-based interface and management system for YACReaderLibrary Server while maintaining full backward compatibility with the existing mobile apps.

### Core Requirements

1. **Backward Compatibility**: Keep existing YACReaderLibrary Server running and accessible
2. **Web Reader**: Modern web UI for reading comics
3. **Library Management**: Scan, upload, organize comics
4. **Administration**: Manage libraries, metadata, settings

## Architecture Overview

**COMPLETE REPLACEMENT** - This server replaces YACReaderLibrary Server entirely.

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
│  │  - Compatible    │  │  - GraphQL (optional)            ││
│  │    with mobile   │  │  - Streaming support             ││
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
│                                                              │
│         ┌──────────────────────────────────────┐            │
│         │  Database (SQLite or PostgreSQL)     │            │
│         ├──────────────────────────────────────┤            │
│         │ - Libraries                          │            │
│         │ - Comics metadata                    │            │
│         │ - Reading progress                   │            │
│         │ - User preferences                   │            │
│         │ - Collections/Tags                   │            │
│         └──────────────────────────────────────┘            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ Direct file access
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    File System                              │
│                                                              │
│  /path/to/Library1/  (e.g., /mnt/Blue/Ebooks_Comics/Manga) │
│    ├── .yacreaderlibrary/          # Per-library metadata  │
│    │   ├── library.ydb              # SQLite DB (compat)   │
│    │   ├── id                       # Library UUID         │
│    │   ├── covers/                  # Cover thumbnails     │
│    │   │   ├── {hash}.jpg           # JPEG (mobile compat)│
│    │   │   └── {hash}.webp          # WebP (web optimized)│
│    │   └── custom_covers/           # User-selected covers│
│    │       ├── {hash}.jpg                                  │
│    │       └── {hash}.webp                                 │
│    ├── Series A/                                           │
│    │   ├── Issue 01.cbz                                    │
│    │   └── Issue 02.cbz                                    │
│    └── Series B/                                           │
│        └── Issue 01.cbz                                    │
│                                                              │
│  /path/to/Library2/                                         │
│    ├── .yacreaderlibrary/                                  │
│    └── ...                                                  │
│                                                              │
│  /var/lib/yaclib/                   # Server config        │
│    ├── config.yml                   # Server settings      │
│    ├── libraries.json               # Library registry     │
│    ├── enhanced.db (optional)       # Extended features    │
│    └── cache/                       # Temp page cache      │
│        └── pages/                   # Extracted pages      │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. YACLib Enhanced Server (Python)

**Technology Stack**:
- **Framework**: FastAPI (async, modern, auto-docs)
- **WebSocket**: For live updates (scan progress, new comics)
- **Database**: Direct access to YACServer SQLite DB (read-only for compatibility)
- **Cache**: Redis (optional, for performance)
- **File Processing**: Pillow (thumbnails), rarfile/zipfile (comic parsing)

**Port**: 8081 (separate from YACServer on 8080)

#### 1.1 Legacy Proxy Module

Forwards mobile app requests to YACServer and manages compatibility.

**Responsibilities**:
- Proxy `/library/*` requests to YACServer:8080
- Session cookie management
- Handle async loading delays (auto-retry logic)
- Monitor YACServer health

**Why needed**:
- Single entry point for mobile apps
- Can add features without modifying YACServer
- Graceful degradation if YACServer is down

#### 1.2 Enhanced API Module

Modern REST API for web UI.

**Endpoints**:

```
# Comics
GET    /api/v1/libraries                    # List all libraries
GET    /api/v1/libraries/{id}/comics        # List comics (paginated, filtered)
GET    /api/v1/comics/{id}                  # Get comic details
GET    /api/v1/comics/{id}/pages            # List all pages
GET    /api/v1/comics/{id}/pages/{num}      # Get page image (proxied)
PUT    /api/v1/comics/{id}                  # Update metadata
DELETE /api/v1/comics/{id}                  # Delete comic

# Library Management
POST   /api/v1/libraries                    # Create library
PUT    /api/v1/libraries/{id}               # Update library
DELETE /api/v1/libraries/{id}               # Delete library
POST   /api/v1/libraries/{id}/scan          # Scan for new comics
GET    /api/v1/libraries/{id}/scan/status   # Get scan progress

# Upload
POST   /api/v1/upload                       # Upload comic file
GET    /api/v1/upload/status/{id}           # Upload progress

# Metadata
GET    /api/v1/comics/{id}/metadata         # Get detailed metadata
PUT    /api/v1/comics/{id}/metadata         # Update metadata
POST   /api/v1/comics/{id}/metadata/scrape  # Auto-scrape metadata

# Organization
GET    /api/v1/folders                      # Browse folder structure
POST   /api/v1/folders                      # Create folder
PUT    /api/v1/comics/{id}/move             # Move comic

# Reading
POST   /api/v1/reading/progress             # Update reading progress
GET    /api/v1/reading/continue             # Get continue reading list
POST   /api/v1/reading/mark-read            # Mark as read

# Search
GET    /api/v1/search                       # Search comics
```

**WebSocket Endpoints**:
```
WS     /ws/scan                             # Live scan progress
WS     /ws/upload                           # Live upload progress
```

#### 1.3 Core Services

**Comic Scanner**:
- Watch directories for new files
- Parse CBZ/CBR/PDF files
- Extract metadata (ComicInfo.xml if present)
- Generate thumbnails
- Update YACServer database

**Upload Handler**:
- Accept file uploads (multipart)
- Validate file types
- Extract to correct location
- Trigger scanner

**Metadata Manager**:
- Parse ComicInfo.xml
- Scrape metadata from online sources (ComicVine, Marvel API, etc.)
- Manage custom tags/collections

**Library Organizer**:
- Move/rename files
- Create folder structures
- Batch operations

**Cache Manager**:
- Cache thumbnails
- Cache frequent pages
- Manage memory usage

### 2. Web UI (Frontend)

**Technology Stack**:
- **Framework**: Vue.js 3 or React (modern, component-based)
- **UI Library**: Tailwind CSS + shadcn/ui or Vuetify
- **Image Viewer**: Custom canvas-based reader or library like react-comic-viewer
- **State**: Pinia (Vue) or Zustand (React)

**Pages**:

1. **Library Browser**
   - Grid/list view of comics
   - Filters (genre, year, read status)
   - Sort options
   - Search

2. **Comic Reader**
   - Page navigation (keyboard, swipe, click)
   - Zoom/pan
   - Reading modes (single, double-page, continuous scroll)
   - RTL support for manga
   - Fullscreen mode
   - Remember reading position

3. **Admin Panel**
   - Library management
   - Scan for new comics (with progress)
   - Upload comics
   - Edit metadata
   - Organize files
   - Server settings

4. **Reading List / Collections**
   - Custom collections
   - Reading lists
   - Continue reading
   - Recently added

### 3. Database Strategy

**Approach**: Dual database access

1. **YACServer SQLite** (read-only from our server)
   - Query for comic data
   - Never write directly (compatibility risk)

2. **Enhanced DB** (optional, PostgreSQL or separate SQLite)
   - Store extended metadata
   - User preferences
   - Custom collections
   - Reading progress (if not using YACServer's)
   - Upload history
   - Scan logs

**Sync Strategy**:
- Read from YACServer DB for core data
- Write enhanced data to our DB
- Join in application layer when needed

## Deployment Architecture

### Option A: Separate Processes (Recommended)

```
┌────────────────────────────────────────┐
│  Reverse Proxy (nginx)                 │
│  Port 80/443                           │
├────────────────────────────────────────┤
│  /              → Web UI (static)      │
│  /api/*         → Enhanced Server:8081 │
│  /library/*     → Enhanced Server:8081 │
│                   (proxies to :8080)   │
└────────────────────────────────────────┘
         │                    │
         ▼                    ▼
┌─────────────────┐  ┌──────────────────┐
│  Static Files   │  │ Enhanced Server  │
│  (Web UI)       │  │ Python:8081      │
└─────────────────┘  └────────┬─────────┘
                              │
                              ▼
                     ┌──────────────────┐
                     │ YACServer        │
                     │ C++/Qt:8080      │
                     └──────────────────┘
```

### Option B: All-in-One (Development)

```
┌────────────────────────────────────────┐
│  Enhanced Server (FastAPI)             │
│  Port 8081                             │
├────────────────────────────────────────┤
│  - Serves Web UI (static files)        │
│  - Serves API                          │
│  - Proxies to YACServer                │
└──────────────┬─────────────────────────┘
               │
               ▼
┌────────────────────────────────────────┐
│  YACServer                             │
│  Port 8080                             │
└────────────────────────────────────────┘
```

## Security Considerations

1. **Authentication** (Phase 2)
   - JWT tokens for web UI
   - Session tokens for mobile (existing)
   - Optional: OAuth2, LDAP

2. **Authorization**
   - Role-based access (admin, user, readonly)
   - Per-library permissions

3. **File Access**
   - Validate all file paths
   - Prevent directory traversal
   - Sandboxed uploads

4. **API Security**
   - Rate limiting
   - CORS configuration
   - Input validation
   - SQL injection prevention (use ORM)

## Performance Optimizations

1. **Caching**
   - Page thumbnails
   - Comic metadata
   - Library listings
   - CDN for static assets

2. **Lazy Loading**
   - Infinite scroll for large libraries
   - Progressive image loading
   - Virtual scrolling for page lists

3. **Compression**
   - Gzip/Brotli for API responses
   - WebP thumbnails (with JPEG fallback)
   - Minified JS/CSS

4. **Database**
   - Index frequently queried fields
   - Connection pooling
   - Query optimization

## Development Phases

### Phase 1: Core Infrastructure
- Basic FastAPI server
- Proxy to YACServer
- Simple web reader
- Database access layer

### Phase 2: Library Management
- Comic scanner
- Upload functionality
- Basic admin panel

### Phase 3: Enhanced Features
- Metadata scraping
- Advanced search
- Collections/tags
- Reading progress sync

### Phase 4: Polish
- Authentication
- Mobile-responsive UI
- Performance optimization
- Documentation

## Technology Decisions

### Why FastAPI?
- Modern async Python framework
- Auto-generated API docs
- Native WebSocket support
- Type hints and validation
- Fast performance

### Why Keep YACServer Running?
- Proven, stable codebase
- Mobile app compatibility
- Complex comic loading logic already implemented
- SQLite database schema we can reuse
- No need to reinvent the wheel

### Database Access Strategy
- Read-only access to YACServer SQLite
- Extended data in separate DB (optional)
- Avoids breaking mobile app compatibility
- Can sync data both ways if needed

## File Structure

```
yaclib-enhanced/
├── docs/
│   ├── API.md
│   └── ARCHITECTURE.md
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app
│   │   ├── routers/
│   │   │   ├── comics.py
│   │   │   ├── libraries.py
│   │   │   ├── upload.py
│   │   │   └── admin.py
│   │   ├── services/
│   │   │   ├── scanner.py
│   │   │   ├── metadata.py
│   │   │   └── proxy.py         # YACServer proxy
│   │   ├── models/
│   │   │   ├── comic.py
│   │   │   └── library.py
│   │   └── database/
│   │       ├── yacserver.py     # YACServer DB access
│   │       └── enhanced.py      # Enhanced DB
│   ├── web/                     # Frontend
│   │   ├── public/
│   │   ├── src/
│   │   │   ├── components/
│   │   │   ├── pages/
│   │   │   ├── api/
│   │   │   └── App.vue
│   │   └── package.json
│   └── client/                  # Python client library
│       ├── __init__.py
│       └── yaclib.py
├── tests/
│   ├── test_api.py
│   └── test_scanner.py
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Next Steps

1. Create Python client library for YACServer
2. Build basic FastAPI proxy
3. Implement comic scanner
4. Create basic web reader UI
5. Add upload functionality
6. Build admin panel
