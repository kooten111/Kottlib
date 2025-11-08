# YACLib Enhanced

A complete replacement for YACReaderLibrary Server, written in Python, that maintains 100% backward compatibility with existing YACReader mobile apps while adding powerful new features for both mobile and web users.

## 🎯 Project Goals

1. **100% Mobile App Compatibility** - Existing iOS/Android apps work without modification
2. **Enhanced Mobile UX** - Folders-first sorting, continue reading, progress tracking
3. **Modern Web UI** - Beautiful web-based comic reader and library manager
4. **Advanced Features** - Series detection, collections, smart search, statistics
5. **Better Performance** - Smart caching, page preloading, bandwidth awareness

## Features

### Current
- ✅ Complete Python client library for YACServer API
- ✅ Session management and automatic retry logic
- ✅ Async comic loading with smart wait times
- ✅ Full API documentation

### Planned
- 🚧 Modern web-based comic reader
- 🚧 Library management (scan, upload, organize)
- 🚧 Enhanced metadata editing
- 🚧 Collections and reading lists
- 🚧 Search and filtering
- 🚧 Admin panel

## Architecture

```
┌──────────────────┐
│  Mobile Apps     │ ← Existing YACReader iOS/Android apps
│  (iOS/Android)   │   (Full compatibility maintained)
└────────┬─────────┘
         │ Legacy API
         ▼
┌─────────────────────────────────────────┐
│  YACLib Enhanced Server (Python)        │
│  ┌────────────┐  ┌────────────────────┐ │
│  │ Legacy     │  │ Modern REST API    │ │
│  │ Proxy      │  │ (Web UI)           │ │
│  └─────┬──────┘  └──────┬─────────────┘ │
└────────┼─────────────────┼───────────────┘
         │                 │
         └────────┬────────┘
                  ▼
    ┌──────────────────────────┐
    │ YACReaderLibrary Server  │
    │ (Original C++/Qt)        │
    └──────────────────────────┘
```

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/yaclib-enhanced.git
cd yaclib-enhanced

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Using the Python Client

```python
from client.yaclib import YACLibClient

# Connect to your YACServer
with YACLibClient("http://192.168.1.5:25565") as client:
    # Open a comic
    metadata = client.open_comic(library_id=2, comic_id=188)
    print(f"Opened: {metadata.path}")
    print(f"Pages: {metadata.num_pages}")

    # Get cover
    cover = client.get_cover(metadata.library_id, metadata.hash)
    with open('cover.jpg', 'wb') as f:
        f.write(cover)

    # Read pages
    for page_num in range(metadata.num_pages):
        page_data = client.get_page(
            metadata.library_id,
            metadata.comic_id,
            page_num
        )
        # Do something with page_data
```

See [examples/basic_usage.py](examples/basic_usage.py) for more examples.

### Running Examples

```bash
cd yaclib-enhanced
python examples/basic_usage.py all
```

## Documentation

- [YACLibrary API Documentation](docs/YACLIB_API.md) - Complete reverse-engineered API docs
- [Architecture Design](docs/ARCHITECTURE.md) - System architecture and design decisions

## Project Structure

```
yaclib-enhanced/
├── docs/                    # Documentation
│   ├── YACLIB_API.md       # YACServer API reference
│   └── ARCHITECTURE.md     # Architecture design
├── src/
│   ├── client/             # Python client library
│   │   └── yaclib.py
│   ├── api/                # FastAPI server (planned)
│   └── web/                # Web UI (planned)
├── examples/               # Usage examples
│   └── basic_usage.py
├── tests/                  # Tests
└── requirements.txt        # Python dependencies
```

## Development Roadmap

### Phase 1: Core Infrastructure ✅
- [x] Reverse engineer YACServer API
- [x] Create Python client library
- [x] Document API protocol
- [x] Design architecture
- [ ] Basic FastAPI proxy server
- [ ] Database access layer

### Phase 2: Web Reader 🚧
- [ ] Basic comic reader UI
- [ ] Page navigation
- [ ] Zoom/pan controls
- [ ] Keyboard shortcuts
- [ ] Reading progress tracking

### Phase 3: Library Management 📋
- [ ] File system scanner
- [ ] Comic upload
- [ ] Metadata editing
- [ ] Library organization
- [ ] Admin panel

### Phase 4: Enhanced Features 🎯
- [ ] Advanced search
- [ ] Collections/tags
- [ ] Reading lists
- [ ] Recommendations
- [ ] Multi-user support
- [ ] Authentication

## API Client Reference

### YACLibClient

Main client class for interacting with YACServer.

**Methods**:
- `open_comic(library_id, comic_id)` - Open a comic for reading
- `get_page(library_id, comic_id, page_num)` - Get a page image
- `get_all_pages(library_id, comic_id, start, end)` - Get multiple pages
- `get_cover(library_id, hash)` - Get cover image
- `update_reading_progress(library_id, comic_id, page)` - Update progress

### YACLibAsyncClient

Enhanced client with better async handling.

**Additional Methods**:
- `is_comic_loaded()` - Check if comic is ready
- `wait_for_comic_load(timeout)` - Wait for loading to complete

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## YACServer Protocol Notes

### Important Discoveries

1. **Session-based**: Each client needs a session cookie
2. **Async loading**: Comics load in background (wait 2-5 seconds after opening)
3. **Page caching**: Pages are cached in server memory per session
4. **Auto-retry**: Client implements smart retry logic for loading pages

### Typical Flow

```
1. GET /library/{id}/comic/{id}/remote  → Open comic, get metadata
2. Wait 3 seconds                        → Let comic load
3. GET /library/{id}/comic/{id}/page/0/remote → Get first page
4. GET /library/{id}/comic/{id}/page/1/remote → Get second page
...
```

## License

MIT License - See LICENSE file for details

## Acknowledgments

- [YACReader](https://www.yacreader.com/) - Original comic reader and server
- Built with reverse engineering the YACReaderLibrary Server protocol

## Related Projects

- [YACReader](https://github.com/YACReader/yacreader) - Original desktop and server application
- [YACReader iOS](https://apps.apple.com/app/yacreader/id635717885) - Official iOS app
- [YACReader Android](https://play.google.com/store/apps/details?id=com.yacreader.yacreader) - Official Android app
