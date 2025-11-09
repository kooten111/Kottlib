# YACLib Enhanced

**Modern comic library server with one-command setup.**

✨ 100% compatible with YACReader mobile apps
✨ Zero configuration required
✨ Just run `./yaclib.py`

```bash
git clone https://github.com/yourusername/yaclib-enhanced.git
cd yaclib-enhanced
./yaclib.py
```

**Done!** Visit http://localhost:8081/docs

---

## What is YACLib Enhanced?

A complete replacement for YACReaderLibrary Server, written in Python, that:
- Maintains 100% backward compatibility with YACReader mobile apps
- Provides a modern API and web interface
- Makes setup incredibly simple

**No complex configuration. No dependencies to manually install. Just works.**

## Features

### Phase 1: Foundation ✅ **COMPLETE**

- ✅ **Comic Loader** - Read CBZ, CBR, CB7 files
- ✅ **Dual Thumbnails** - JPEG (mobile) + WebP (web)
- ✅ **Database Layer** - SQLAlchemy ORM with extended YACReader schema
- ✅ **FastAPI Server** - Production-ready async server
- ✅ **Legacy API** - YACReader mobile app compatible
- ✅ **Modern API** - JSON REST endpoints
- ✅ **Configuration System** - YAML-based config
- ✅ **One-Command Setup** - Interactive launcher

### Phase 2: Mobile UX ✅ **COMPLETE**

- ✅ **Folders-first sorting** - Proper folder hierarchy
- ✅ **Continue reading list** - Track reading progress
- ✅ **Reading progress tracking** - Per-user progress
- ✅ **Custom cover selection** - Database ready

### Phase 3: YACReader Compatibility 🚧 **90% COMPLETE**

- ✅ **Database schema** - 43 new fields + 5 tables
- ✅ **Session management** - Multi-user support
- ✅ **File size reporting** - Actual sizes, not "0"
- ✅ **Library UUIDs** - In all V2 responses
- ✅ **Root folder convention** - `__ROOT__` folders
- ✅ **Multi-library support** - Same file in multiple libraries
- ⏳ **ComicInfo.xml extraction** - Scanner integration pending
- ⏳ **Search functionality** - Pending
- ⏳ **Favorites/Tags/Lists** - Database ready, endpoints pending

### Phase 4: Web UI 📋 **PLANNED**

- 📋 Modern web-based comic reader
- 📋 Library management UI
- 📋 Metadata editing
- 📋 Admin panel

### Phase 5: Advanced Features 🎯 **FUTURE**

- 🎯 Series auto-detection
- 🎯 Smart search with FTS
- 🎯 Reading statistics
- 🎯 Enhanced collections

## Quick Start

### For New Users

```bash
# 1. Clone
git clone https://github.com/yourusername/yaclib-enhanced.git
cd yaclib-enhanced

# 2. Run
./yaclib.py
```

The launcher will:
1. Check Python 3.11+
2. Install dependencies (if needed)
3. Guide you through setup
4. Help configure libraries
5. Scan comics (optional)
6. Start the server

**See [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) for detailed documentation.**

### After First Run

Just run:
```bash
./yaclib.py
```

Your configuration is saved in `config.yml`.

## Usage Examples

### Connect YACReader Mobile App

1. Start server: `./yaclib.py`
2. In YACReader mobile app, add server: `http://<your-ip>:8081`
3. Browse your libraries!

### Access API

Visit http://localhost:8081/docs for interactive API documentation.

**REST Endpoints:**
- `GET /api/v1/libraries` - List all libraries
- `GET /api/v1/libraries/{id}` - Get library details
- `POST /api/v1/libraries` - Create library

**Legacy Endpoints (mobile apps):**
- `GET /library/` - List libraries
- `GET /library/{lib_id}/folder/{folder_id}` - Browse folder
- `GET /library/{lib_id}/comic/{comic_id}` - Get comic info
- `GET /library/{lib_id}/comic/{comic_id}/page/{num}` - Get page

### Use Python Client

```python
from client.yaclib import YACLibClient

with YACLibClient("http://192.168.1.5:25565") as client:
    metadata = client.open_comic(library_id=2, comic_id=188)
    print(f"Pages: {metadata.num_pages}")

    page = client.get_page(2, 188, 0)
    with open('page.jpg', 'wb') as f:
        f.write(page)
```

See [examples/basic_usage.py](examples/basic_usage.py).

## Configuration

### Simple: Use the Launcher

The interactive launcher (`./yaclib.py`) handles everything on first run.

### Advanced: Edit Config File

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

See [CONFIGURATION.md](CONFIGURATION.md) for complete guide.

### CLI Tool

For advanced users:

```bash
# Manage config
./yaclib-cli.py config init
./yaclib-cli.py config show

# Manage libraries
./yaclib-cli.py library add "Comics" /mnt/Comics
./yaclib-cli.py library scan Comics
./yaclib-cli.py library list

# Server control
./yaclib-cli.py server start
./yaclib-cli.py server info
```

## Documentation

- **[DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)** - Complete documentation index
- **[CONFIGURATION.md](CONFIGURATION.md)** - Configuration guide
- **[YACREADER_API_COMPATIBILITY.md](YACREADER_API_COMPATIBILITY.md)** - YACReader compatibility status
- **[docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md)** - Full project overview
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture
- **[docs/YACLIB_API.md](docs/YACLIB_API.md)** - API reference

## Project Structure

```
yaclib-enhanced/
├── yaclib.py              ⭐ Main launcher (run this!)
├── yaclib-cli.py          # CLI tool
├── config.yml             # Your config (created on first run)
├── src/
│   ├── api/               # FastAPI server
│   ├── database/          # Database layer
│   ├── scanner/           # Comic loader & thumbnails
│   ├── client/            # Python client library
│   └── config.py          # Configuration management
├── examples/              # Example scripts
└── docs/                  # Documentation

~/.local/share/yaclib/     # Database & thumbnails (Linux)
├── yaclib.db
└── covers/
```

## Requirements

- **Python 3.11+**
- **Linux, macOS, or Windows**
- Comics in CBZ, CBR, or CB7 format

The launcher installs all Python dependencies automatically.

## Development Status

**Current Phase:** Phase 3 - YACReader Compatibility (90% complete)

**Completed:**
- ✅ Phase 1: Foundation - All core infrastructure
- ✅ Phase 2: Mobile UX - Reading progress, folder navigation
- ✅ Phase 3 (90%): YACReader Compatibility
  - Database schema extended
  - Session management
  - Root folder implementation
  - Multi-library support
  - Bug fixes (folder recursion, cross-library contamination)

**Remaining (10%):**
- Scanner ComicInfo.xml metadata extraction
- Search functionality
- Favorites/Tags/Reading Lists endpoints

**See [YACREADER_API_COMPATIBILITY.md](YACREADER_API_COMPATIBILITY.md) for detailed compatibility status.**

## Contributing

Contributions welcome! Please:
1. Check [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) for architecture
2. Follow existing code style
3. Add tests for new features
4. Update documentation

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

**Get started in seconds:**

```bash
./yaclib.py
```

That's it! 🚀
