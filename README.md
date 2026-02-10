# Kottlib

**Comic library server and webui.**

- Compatible with YACReader mobile apps
- Just run `./start.sh`

```bash
git clone https://github.com/kooten111/Kottlib.git
cd Kottlib
./start.sh
```

Done!

- Web UI: <http://localhost:5173>
- API: <http://localhost:8081>
- API Docs: <http://localhost:8081/docs>

---

## What is Kottlib?

A comic library server written in Python that:
- Maintains backward compatibility with YACReader mobile apps
- Provides an API and web interface

## Screenshots

### Gallery View
![Gallery View](docs/screenshots/gallery_view.webp)

### Comic Reader
![Comic Reader](docs/screenshots/comic_view.webp)

## Features

### Core Features

- **Comic Formats** - CBZ, CBR, CB7 support with automatic format detection
- **Multi-threaded Scanning** - Library indexing with parallel processing
- **Dual Thumbnails** - JPEG (mobile) + WebP (web) for optimal performance
- **Database Layer** - SQLAlchemy ORM with extended YACReader schema
- **FastAPI Server** - Async API server
- **YACReader API** - Compatible with YACReader mobile apps (v1 & v2)
- **API** - RESTful JSON endpoints with OpenAPI documentation
- **One-Command Setup** - Interactive launcher for easy installation

### Web Interface

- **Web UI** - Responsive SvelteKit interface
- **Comic Reader** - Full-featured reader with keyboard shortcuts
- **Library Browser** - Grid/list views with folder navigation
- **Continue Reading** - Track and resume reading progress across devices
- **Favorites** - Mark and manage favorite comics
- **Advanced Search** - Full-text search with autocomplete, filters, and previews
- **Admin Dashboard** - Server stats and library management
- **Dark Theme** - Dark-first design
- **Responsive** - Works on desktop, tablet, and mobile

### Metadata Scanner System

- **Pluggable Architecture** - Easy to add new metadata sources
- **Multiple Scanners** - nhentai, AniList, MangaDex, Comic Vine, Metron
- **Smart Matching** - Fuzzy matching with confidence scoring
- **Per-Library Configuration** - Different scanners for different library types
- **Fallback Support** - Automatic fallback to secondary sources
- **API Integration** - RESTful endpoints for scanner management

### Reading Progress & Social

- **Reading Progress** - Per-user, per-comic progress tracking
- **Continue Reading** - Quick access to in-progress comics
- **Favorites** - Mark comics as favorites
- **Session Management** - Multi-user support with device tracking
- **Multi-library Support** - Multiple comic libraries with separate configurations

## Quick Start

### For New Users

```bash
# 1. Clone
git clone https://github.com/kooten111/Kottlib.git
cd Kottlib

# 2. Run
./start.sh
```

The launcher will:
1. Set up virtual environment
2. Install dependencies (if needed)
3. Initialize database
4. Start backend API and web UI

For detailed API documentation, start the server and visit:
- **Interactive API Docs**: <http://localhost:8081/docs> (Swagger UI - test endpoints)
- **API Reference**: <http://localhost:8081/redoc> (ReDoc - beautiful docs)

### After First Run

**Start Everything (Recommended)**

```bash
./start.sh
```

Starts both backend API and Web UI.

**Start Components Separately (for development)**

```bash
# Backend only
./start_backend.sh

# Web UI only (in another terminal, needs backend running)
./start_webui.sh
```

This gives you:
- Backend API on port 8081
- Web UI on port 5173
- Automatic dependency installation and database setup

Your configuration is saved in `config.yml`.

**Other Tools:**
- `./scripts/kottlib-cli.py` - CLI management tool

**Quick Library Scanning:**
```bash
./scan.sh /path/to/library              # Scan with defaults
./scan.sh /path/to/library --workers 8  # Scan with more workers
./scan.sh --help                        # Show all options
```

## Usage Examples

### Connect YACReader Mobile App

1. Start server: `./start.sh`
2. In YACReader mobile app, add server: `http://<your-ip>:8081`
3. Browse your libraries!

### Access API

Visit the auto-generated, interactive API documentation:
- **<http://localhost:8081/docs>** - Test endpoints, view request/response schemas
- **<http://localhost:8081/redoc>** - Clean, searchable API reference

**Quick Reference:**

REST Endpoints (Modern JSON API):

- `GET /api/v1/libraries` - List all libraries
- `GET /api/v1/libraries/{id}` - Get library details
- `POST /api/v1/libraries` - Create library

Legacy Endpoints (mobile apps):

- `GET /library/` - List libraries
- `GET /library/{lib_id}/folder/{folder_id}` - Browse folder
- `GET /library/{lib_id}/comic/{comic_id}` - Get comic info
- `GET /library/{lib_id}/comic/{comic_id}/page/{num}` - Get page

### Use Python Client

A Python client library is available at `src/client/kottlib.py`:

```python
from src.client.kottlib import KottlibClient

with KottlibClient("http://192.168.1.5:8081") as client:
    metadata = client.open_comic(library_id=2, comic_id=188)
    print(f"Pages: {metadata.num_pages}")

    page = client.get_page(2, 188, 0)
    with open('page.jpg', 'wb') as f:
        f.write(page)
```

## Configuration

### Edit Config File

After first run, edit `config.yml`:

```yaml
server:
  host: "0.0.0.0"
  port: 8081
  log_level: "info"

libraries:
  - name: "Comics"
    path: "/mnt/Comics"
    auto_scan: true
    settings:
      default_reading_direction: "ltr"

  - name: "Manga"
    path: "/mnt/Manga"
    auto_scan: true
    settings:
      default_reading_direction: "rtl"
```

See `config.example.yml` for all available configuration options.

### CLI Tool

For advanced users:

```bash
# Manage config
./scripts/kottlib-cli.py config init
./scripts/kottlib-cli.py config show

# Manage libraries
./scripts/kottlib-cli.py library add "Comics" /mnt/Comics
./scripts/kottlib-cli.py library scan Comics
./scripts/kottlib-cli.py library list

# Server control
./scripts/kottlib-cli.py server start
./scripts/kottlib-cli.py server info
```

## Documentation

**Live API Documentation** (when server is running):
- <http://localhost:8081/docs> - Interactive Swagger UI
- <http://localhost:8081/redoc> - ReDoc API reference
- <http://localhost:8081/openapi.json> - OpenAPI schema

**Project Documentation:**
- [docs/API.md](docs/API.md) - Complete API reference
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - System architecture
- [docs/SCANNERS.md](docs/SCANNERS.md) - Scanner system documentation
- [docs/SERVICES.md](docs/SERVICES.md) - Service layer guide
- [docs/ROADMAP.md](docs/ROADMAP.md) - Future development plans
- [docs/SEARCH.md](docs/SEARCH.md) - Search functionality guide
- `config.example.yml` - Configuration options and examples

## Project Structure

```text
Kottlib/
├── start.sh               # Start everything (backend + web UI)
├── start_backend.sh       # Start backend API only
├── start_webui.sh         # Start web UI only
├── scan.sh                # Library scanner
├── config.yml             # Your config (created on first run)
├── config.example.yml     # Example configuration
├── src/
│   ├── api/               # FastAPI server
│   │   ├── main.py        # Application entry point
│   │   ├── middleware/    # Session & CORS middleware
│   │   └── routers/       # API route handlers
│   │       ├── legacy_v1.py      # YACReader v1 API (text format)
│   │       ├── libraries.py      # Modern library management
│   │       ├── scanners.py       # Metadata scanner API
│   │       ├── user_interactions.py  # Favorites, progress
│   │       └── v2/               # YACReader v2 API (JSON format)
│   │           ├── comics.py
│   │           ├── collections.py
│   │           ├── folders.py
│   │           ├── libraries.py
│   │           ├── reading.py
│   │           ├── search.py
│   │           ├── series.py
│   │           └── session.py
│   ├── database/          # Database layer
│   │   ├── models/        # SQLAlchemy models (modular)
│   │   ├── operations/    # CRUD operations
│   │   ├── paths.py       # Path utilities
│   │   └── connection.py  # Database connection
│   ├── scanner/           # Core scanner engine
│   │   ├── loaders/       # Format-specific loaders (CBZ/CBR/CB7)
│   │   ├── comic_loader.py        # Archive factory
│   │   ├── comic_processor.py     # Comic processing
│   │   ├── thumbnail_generator.py # JPEG + WebP thumbnails
│   │   └── threaded_scanner.py    # Multi-threaded scanner
│   ├── metadata_providers/ # Metadata scanner system
│   │   ├── base.py                # Scanner interface
│   │   ├── manager.py             # Scanner registry
│   │   ├── schema.py              # Field mapping
│   │   └── providers/             # Scanner implementations
│   │       ├── nhentai/
│   │       ├── anilist/
│   │       ├── mangadex/
│   │       ├── comicvine/
│   │       └── metron/
│   ├── services/          # Business logic layer
│   │   ├── cover_service.py       # Cover generation/retrieval
│   │   ├── comic_info_service.py  # Shared V1/V2 comic info
│   │   ├── metadata_service.py    # Metadata application
│   │   ├── library_service.py     # Library management
│   │   └── scan_service.py        # Scan orchestration
│   ├── client/            # Python client library
│   │   └── kottlib.py     # API client for programmatic access
│   ├── utils/             # Utilities
│   │   ├── platform.py    # Platform-specific paths
│   │   ├── hashing.py     # Hash functions
│   │   └── pagination.py  # Pagination helpers
│   └── config.py          # Configuration management
├── scanners/              # Scanner plugins (legacy location, still supported)
│   ├── AniList/           # AniList scanner plugin
│   ├── ComicVine/         # Comic Vine scanner plugin
│   ├── mangadex/          # MangaDex scanner plugin
│   ├── metron/            # Metron scanner plugin
│   └── nhentai/           # nhentai scanner plugin
├── webui/                 # SvelteKit frontend
│   ├── src/
│   │   ├── routes/        # Page routes
│   │   │   ├── admin/             # Admin dashboard
│   │   │   ├── comic/             # Comic reader
│   │   │   ├── continue-reading/  # Continue reading list
│   │   │   ├── favorites/         # Favorites
│   │   │   ├── search/            # Search interface
│   │   │   └── series/            # Series browser
│   │   ├── lib/           # Reusable components & stores
│   │   └── app.html       # HTML template
│   ├── package.json       # Bun dependencies
│   └── vite.config.js     # Vite configuration
├── scripts/               # Utility scripts
│   ├── kottlib-cli.py     # CLI management tool
│   ├── scan_library.py    # Library scanning
│   ├── diagnose_missing_data.py   # Debug tools
│   └── regenerate_covers.py       # Cover regeneration
├── tests/                 # Test suite
│   ├── conftest.py        # Test fixtures
│   └── api/               # API tests
│       ├── test_v1_api.py
│       ├── test_v2_api.py
│       └── test_integration.py
├── docs/                  # Documentation
│   ├── API.md                 # Complete API reference
│   ├── ARCHITECTURE.md        # System architecture
│   ├── SCANNERS.md            # Scanner system guide
│   ├── SERVICES.md            # Service layer documentation
│   ├── ROADMAP.md             # Future development plans
│   └── SEARCH.md              # Search functionality guide
└── data/                  # Runtime data (created on first run, gitignored)
    ├── main.db            # SQLite database
    └── covers/            # Generated thumbnails (JPEG + WebP)
        └── <LibraryName>/ # Per-library cover storage
```

## Requirements

- Python 3.11+
- Linux, macOS, or Windows
- Comics in CBZ, CBR, or CB7 format
- Bun (for web UI) - https://bun.sh

### System Dependencies (for CBR support)

- **unrar** - Required for reading CBR (RAR) archives
  - Arch Linux: `sudo pacman -S unrar`
  - Debian/Ubuntu: `sudo apt install unrar`
  - macOS: `brew install unrar`

The launcher installs all Python dependencies automatically.

## License

MIT License - See LICENSE file for details.

## Acknowledgments

- [YACReader](https://www.yacreader.com/) - Original comic reader and server
- Built by reverse-engineering the YACReaderLibrary Server protocol

## Related Projects

- [YACReader](https://github.com/YACReader/yacreader) - Original desktop & server
- [YACReader iOS](https://apps.apple.com/app/yacreader/id635717885) - Official iOS app
- [YACReader Android](https://play.google.com/store/apps/details?id=com.yacreader.yacreader) - Official Android app

---

Get started:

```bash
./start.sh
```
