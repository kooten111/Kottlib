# YACLib Enhanced - Documentation Index

All project documentation in one convenient index.

## 📚 Core Documentation

### [PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md)
**Start here!** Comprehensive overview of the entire project.

**Contents**:
- Executive summary
- Project genesis and discoveries
- Core principles and decisions
- Feature roadmap
- Implementation plan
- Current status

**Read this first** to understand the big picture.

---

### [YACREADER_COMPATIBILITY_IMPROVEMENTS.md](YACREADER_COMPATIBILITY_IMPROVEMENTS.md)

**Latest updates!** Recent improvements to YACReader compatibility (2025-11-09).

**Contents**:

- File size reporting fixes
- Library UUID implementation
- Folder metadata enhancements
- Session management middleware
- Testing recommendations
- Status update: 60% → 80% complete

**For**: Understanding recent compatibility work and next steps.

---

### [ARCHITECTURE.md](docs/ARCHITECTURE.md)
System architecture and component design.

**Contents**:
- Architecture diagrams
- Component details
- Technology stack
- Database strategy
- Deployment options
- File structure

**For**: Understanding how everything fits together.

---

### [YACLIB_API.md](docs/YACLIB_API.md)
Complete YACReaderLibrary Server API reference.

**Contents**:
- All API endpoints (v1 and v2)
- Request/response formats
- Session management
- Typical usage flows
- Implementation notes

**For**: Understanding the protocol we need to implement.

---

## 🎨 Design Documentation

### [DESIGN_DECISIONS.md](docs/DESIGN_DECISIONS.md)
Key design decisions with rationale.

**Contents**:
- Complete replacement vs. proxy layer
- Per-library metadata storage
- Dual-format thumbnail system
- Custom cover selection
- Database strategy
- Technology choices
- Feature priorities

**For**: Understanding WHY we made specific choices.

---

### [THUMBNAILS_AND_METADATA.md](docs/THUMBNAILS_AND_METADATA.md)
Thumbnail system and metadata storage design.

**Contents**:
- Dual format strategy (JPEG + WebP)
- File structure
- Custom cover selection
- Performance considerations
- Migration from YACReader
- Storage estimates

**For**: Understanding thumbnail generation and storage.

---

### [IMPROVEMENTS_AND_FEATURES.md](docs/IMPROVEMENTS_AND_FEATURES.md)
Proposed improvements and feature specifications.

**Contents**:
- Smart folder/comic sorting
- Page preloading
- Bandwidth-aware quality
- Continue reading feature
- Series grouping
- Collections/reading lists
- Search improvements
- Reading statistics
- Mobile-specific improvements

**For**: Feature specifications and implementation details.

---

### [SERVER_CONTROL_ANALYSIS.md](docs/SERVER_CONTROL_ANALYSIS.md)
Analysis of server-side control over mobile app UI.

**Contents**:
- Template system analysis
- What we can control (spoiler: everything!)
- What we cannot control
- Mobile app behavior
- HTML/CSS customization examples
- Implementation strategies

**For**: Understanding mobile app control capabilities.

---

## 💻 Code Documentation

### [src/client/yaclib.py](src/client/yaclib.py)
Python client library for YACReaderLibrary Server.

**Status**: ✅ Complete and working!

**Features**:
- Session management
- Automatic retry logic
- Async comic loading handling
- Easy-to-use API

**Example**:
```python
from client.yaclib import YACLibClient

with YACLibClient("http://192.168.1.5:25565") as client:
    metadata = client.open_comic(library_id=2, comic_id=188)
    page = client.get_page(2, 188, 0)
```

See [examples/basic_usage.py](examples/basic_usage.py) for more examples.

---

### [examples/basic_usage.py](examples/basic_usage.py)
Example usage of the Python client library.

**Examples**:
- Basic usage
- Context manager
- Async client
- Error handling
- Reading session simulation

**Run**: `python examples/basic_usage.py`

---

## 📖 Quick Start Guide

### For New Contributors

1. **Read**: [PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) - Understand the project
2. **Read**: [ARCHITECTURE.md](docs/ARCHITECTURE.md) - Understand the system
3. **Read**: [DESIGN_DECISIONS.md](docs/DESIGN_DECISIONS.md) - Understand the choices
4. **Try**: Run `python examples/basic_usage.py` - See it work!
5. **Code**: Pick a task from the implementation plan

### For Users

1. **Installation**: See [README.md](README.md) - Setup instructions
2. **Configuration**: See [CONFIGURATION.md](CONFIGURATION.md) - Configuration guide
3. **Compatibility**: See [YACREADER_API_COMPATIBILITY.md](YACREADER_API_COMPATIBILITY.md) - YACReader compatibility status

### For API Developers

1. **API Reference**: [YACLIB_API.md](docs/YACLIB_API.md)
2. **Client Library**: [src/client/yaclib.py](src/client/yaclib.py)
3. **Examples**: [examples/basic_usage.py](examples/basic_usage.py)

---

## 🗺️ Implementation Roadmap

### Phase 1: Foundation ✅ COMPLETE

- [x] Reverse engineer API
- [x] Design architecture
- [x] Create Python client library
- [x] Build comic loader
- [x] Implement database layer
- [x] Create FastAPI server
- [x] Implement legacy API v1

**Status**: All components implemented and tested!

### Phase 2: Mobile UX ✅ COMPLETE

- [x] Folders-first sorting
- [x] Continue reading list
- [x] Reading progress tracking
- [x] Custom cover selection

**Status**: All mobile UX improvements implemented!

### Phase 3: YACReader Compatibility 🚧 IN PROGRESS

- [x] Database schema extended (43 new fields)
- [x] V1 line endings fixed (CRLF)
- [x] Comic navigation (previousComic/nextComic)
- [ ] Session management
- [ ] Metadata scanner integration
- [ ] Full API compatibility

**Documentation**: See [YACREADER_API_COMPATIBILITY.md](YACREADER_API_COMPATIBILITY.md) for detailed status

### Phase 4: Web UI 📋 PLANNED

- [ ] Basic comic reader
- [ ] Library browser
- [ ] Admin panel

### Phase 5: Advanced Features 🎯 FUTURE

- [ ] Series auto-detection
- [ ] Collections
- [ ] Smart search
- [ ] Statistics

**Documentation**: See [IMPROVEMENTS_AND_FEATURES.md](docs/IMPROVEMENTS_AND_FEATURES.md)

---

## 📊 Project Status

**Current Phase**: Phase 3 (YACReader Compatibility) 🚧

**Progress**:
- ✅ Phase 1: Foundation - Complete
- ✅ Phase 2: Mobile UX - Complete
- 🚧 Phase 3: YACReader Compatibility - 60% complete
- 📋 Phase 4: Web UI - Planned
- 🎯 Phase 5: Advanced Features - Future

**Code Status**:
- ✅ Python client library
- ✅ Comic loader
- ✅ Database layer (extended for compatibility)
- ✅ FastAPI server
- ✅ Legacy API v1 (basic compatibility)
- ✅ Mobile UX improvements
- 🚧 YACReader full compatibility (in progress)
- ⏳ Web UI (planned)

---

## 📝 Contributing

Documentation contributions welcome! Please ensure:

1. **Clarity**: Write for someone new to the project
2. **Examples**: Include code examples where relevant
3. **Context**: Explain WHY, not just WHAT
4. **Updates**: Keep index updated when adding new docs

---

## 🔗 External Resources

### YACReader
- [YACReader Website](https://www.yacreader.com/)
- [GitHub Repository](https://github.com/YACReader/yacreader)
- [YACReader Forum](https://www.yacreader.com/forum/)

### Technologies
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pillow Documentation](https://pillow.readthedocs.io/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [Jinja2 Documentation](https://jinja.palletsprojects.com/)

---

## 📧 Questions?

Check existing documentation first - we've documented extensively!

If you can't find what you need:
1. Check the appropriate doc file (see index above)
2. Search docs for keywords
3. Check examples and code comments

---

**Last Updated**: 2025-11-09
**Documentation Version**: 2.1
**Project Status**: Phase 3 In Progress (YACReader Compatibility)
