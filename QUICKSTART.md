# YACLib Enhanced - Quick Start Guide

Get up and running with YACLib Enhanced in 5 minutes!

## Phase 1: Foundation - NOW COMPLETE ✅

All Phase 1 components have been implemented:

- ✅ Comic loader (CBZ/CBR/CB7 support)
- ✅ Thumbnail generator (dual JPEG/WebP)
- ✅ Database layer (SQLAlchemy ORM)
- ✅ FastAPI server skeleton
- ✅ Legacy API v1 endpoints (YACReader compatible)
- ✅ Modern JSON API
- ✅ Example scripts and tools

## Installation

### 1. Install Dependencies

```bash
cd /mnt/Black/Apps/KottLib/yaclib-enhanced
pip install -r requirements.txt
```

### 2. Initialize Database

The database will be automatically created on first run at:
- Linux: `~/.local/share/yaclib/yaclib.db`
- macOS: `~/Library/Application Support/YACLib/yaclib.db`
- Windows: `%APPDATA%/YACLib/yaclib.db`

## Quick Test

### Test Comic Loading

```bash
# Test loading a comic file
python examples/test_comic_loader.py /path/to/your/comic.cbz
```

This will:
- Open the comic archive
- Display page count and metadata
- Extract ComicInfo.xml if present

### Test Database

```bash
# Test database operations
python examples/test_database.py
```

This will:
- Create the database
- Add a test library
- Add test comics
- Show statistics

## Configure Your Libraries

### Quick Method: CLI Tool

```bash
# 1. Create configuration file
./yaclib-cli.py config init

# 2. Add your libraries
./yaclib-cli.py library add "Comics" /mnt/Comics
./yaclib-cli.py library add "Manga" /mnt/Manga

# 3. Scan libraries
./yaclib-cli.py library scan Comics
./yaclib-cli.py library scan Manga
```

### Manual Method: Edit Config

Edit `config.yml`:
```yaml
libraries:
  - name: "Comics"
    path: "/mnt/Comics"
    auto_scan: true

  - name: "Manga"
    path: "/mnt/Manga"
    auto_scan: true
    settings:
      default_reading_direction: "rtl"
```

Then scan:
```bash
./yaclib-cli.py library scan Comics
```

### Fast Scanner Method (Recommended for Large Libraries)

For libraries with 100+ comics, use the multi-threaded scanner:

```bash
# Scan with 8 worker threads (3-6x faster!)
python examples/scan_library_fast.py /path/to/comics "My Comics" 8
```

### Legacy Method: Direct Script

```bash
# Single-threaded scanner (simpler, but slower)
python examples/scan_library.py /path/to/comics "My Comics"
```

See [PERFORMANCE_IMPROVEMENTS.md](PERFORMANCE_IMPROVEMENTS.md) for details on performance optimizations.
See [CONFIGURATION.md](CONFIGURATION.md) for complete configuration guide.

## Start the Server

### Method 1: CLI Tool (Recommended)

```bash
./yaclib-cli.py server start
```

Uses settings from `config.yml`.

### Method 2: Startup Script

```bash
./run_server.sh
```

### Method 3: Direct

```bash
cd src/api
python main.py
```

The server will start on http://localhost:8081 (or configured port)

## Explore the API

Visit these URLs in your browser:

- **API Documentation:** http://localhost:8081/docs (Swagger UI)
- **Health Check:** http://localhost:8081/health
- **Server Info:** http://localhost:8081/api/v1/info
- **Libraries:** http://localhost:8081/api/v1/libraries

## Test with cURL

```bash
# Get server info
curl http://localhost:8081/api/v1/info

# List libraries
curl http://localhost:8081/api/v1/libraries

# Create a library
curl -X POST http://localhost:8081/api/v1/libraries \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Library", "path": "/path/to/comics"}'
```

## Connect YACReader Mobile App

1. Start the server:
   ```bash
   python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8081
   ```

2. In YACReader mobile app:
   - Add new server
   - Enter server address: `http://<your-ip>:8081`
   - Browse your libraries!

**Note:** The legacy API endpoints (`/library/*`) are compatible with YACReader mobile apps.

## Project Structure

```
yaclib-enhanced/
├── src/
│   ├── api/                    # FastAPI application
│   │   ├── main.py            # Server entry point
│   │   └── routers/           # API endpoints
│   │       ├── legacy_v1.py   # YACReader compatible
│   │       └── libraries.py   # Modern JSON API
│   ├── database/              # Database layer
│   │   ├── models.py          # SQLAlchemy models
│   │   ├── database.py        # Database operations
│   │   └── schema.sql         # Schema reference
│   ├── scanner/               # Comic processing
│   │   ├── comic_loader.py    # CBZ/CBR/CB7 reader
│   │   └── thumbnail_generator.py
│   └── client/                # Client library
│       └── yaclib.py          # YACReader client
├── examples/                   # Example scripts
│   ├── test_comic_loader.py
│   ├── test_database.py
│   └── scan_library.py
└── docs/                       # Documentation
```

## Common Tasks

### Add a New Library

```bash
# Via API
curl -X POST http://localhost:8081/api/v1/libraries \
  -H "Content-Type: application/json" \
  -d '{"name": "Comics", "path": "/mnt/Comics"}'

# Via scan script
python examples/scan_library.py /mnt/Comics "Comics"
```

### View Database Location

```bash
python -c "from src.database import get_default_db_path; print(get_default_db_path())"
```

### View Covers Directory

```bash
python -c "from src.database import get_covers_dir; print(get_covers_dir())"
```

## Next Steps

Now that Phase 1 is complete, you can:

1. **Test the system:**
   - Scan your comic library
   - Start the server
   - Browse the API documentation

2. **Connect mobile app:**
   - Configure YACReader mobile to use this server
   - Test backward compatibility

3. **Explore the code:**
   - Check out [src/scanner/comic_loader.py](src/scanner/comic_loader.py)
   - Review [src/api/routers/legacy_v1.py](src/api/routers/legacy_v1.py)
   - Read the architecture docs in `/docs`

4. **Plan Phase 2:**
   - Folders-first sorting
   - Continue reading list
   - Reading progress tracking
   - Custom cover selection

## Troubleshooting

### Import Errors

Make sure you're running from the project root:
```bash
cd /mnt/Black/Apps/KottLib/yaclib-enhanced
python examples/test_database.py
```

### Missing Dependencies

```bash
pip install -r requirements.txt
```

### RAR Support (for CBR files)

Install unrar:
```bash
# Ubuntu/Debian
sudo apt install unrar

# macOS
brew install unrar

# Then install Python package
pip install rarfile
```

## Documentation

Full documentation is available in the `/docs` directory:

- [PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) - Complete overview
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System architecture
- [YACLIB_API.md](docs/YACLIB_API.md) - API reference
- [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) - Full index

## Support

Check the documentation first, then:
1. Review example scripts
2. Check API docs at `/docs`
3. Test with provided examples

---

**Phase 1 Status:** ✅ COMPLETE

**Ready for Phase 2:** Mobile UX improvements!
