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

### [YACREADER_API_COMPATIBILITY.md](YACREADER_API_COMPATIBILITY.md)

**Complete YACReader compatibility reference** - Updated 2025-11-09 (100% complete).

**Contents**:

- Progress summary (100% complete) 🎉
- Recent updates (file size, UUIDs, sessions, root folders, bug fixes, favorites, tags, reading lists, search)
- V1 API (legacy text-based) reference
- V2 API (modern JSON-based) reference
- Database schema compatibility
- Session management details
- Implementation checklist
- Testing guide
- Implementation details with code references

**For**: Complete YACReader compatibility status and implementation details.

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

### [WEB_UI_PLAN.md](docs/WEB_UI_PLAN.md)

**Complete Web UI planning document** - Modern, responsive design.

**Contents**:

- Design philosophy and principles
- Technology stack (SvelteKit + Tailwind CSS)
- Architecture overview
- Feature breakdown (Reader, Browser, Search, Admin)
- UI component specifications
- Page layouts and wireframes
- Implementation phases (12-week plan)
- Technical decisions
- API integration details
- Performance and accessibility targets

**For**: Web UI development planning and implementation guide.

---

### [METADATA_ENRICHMENT.md](docs/METADATA_ENRICHMENT.md)

**Automated metadata enrichment system** - For collections without embedded metadata.

**Contents**:

- Problem statement (41k+ items without metadata)
- Filename parsing strategies
- Online database integration (AniList, Comic Vine)
- Fuzzy matching algorithms
- Batch processing workflow
- Admin UI for review and approval
- Performance optimization (rate limiting, caching)
- Implementation timeline

**For**: Automatically enriching large collections with metadata from online sources.

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

### Scripts & Tools

- **[scripts/scan_library.py](scripts/scan_library.py)** - Single-threaded library scanner
- **[scripts/scan_library_fast.py](scripts/scan_library_fast.py)** - Multi-threaded scanner for large libraries
- **[tools/import_yacreader.py](tools/import_yacreader.py)** - Import data from YACReader
- **[tools/debug_folders.py](tools/debug_folders.py)** - Debug folder relationships
- **[tools/test_folder_api.py](tools/test_folder_api.py)** - Test folder API responses
- **[tools/migrations/](tools/migrations/)** - Database migration scripts

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

### Phase 3: YACReader Compatibility ✅ 100% COMPLETE 🎉

- [x] Database schema extended (43 new fields + 5 tables)
- [x] V1 line endings fixed (CRLF)
- [x] Comic navigation (previousComic/nextComic)
- [x] Session management middleware
- [x] File size reporting fixed
- [x] Library UUID in all responses
- [x] Root folder implementation (`__ROOT__` convention)
- [x] Multi-library support
- [x] Bug fixes (folder recursion, cross-library contamination)
- [x] **Favorites endpoints (3 endpoints)** ✅ NEW
- [x] **Tags/Labels endpoints (7 endpoints)** ✅ NEW
- [x] **Reading Lists endpoints (7 endpoints)** ✅ NEW
- [x] **Search functionality** ✅ COMPLETE

**Optional Future Enhancements:**

- Metadata scanner integration (ComicInfo.xml) - Phase 5
- V1 HTML templates - Phase 4

**Documentation**: See [YACREADER_API_COMPATIBILITY.md](YACREADER_API_COMPATIBILITY.md) for detailed status

### Phase 4: Web UI ✅ **85% COMPLETE** (2025-11-09)

**Phase 1: Foundation** ✅ COMPLETE

- [x] SvelteKit project setup with Vite
- [x] Tailwind CSS v3 configured with custom design system
- [x] Layout components (Navbar, Sidebar, Footer)
- [x] Common UI components (Button, Card, Input, Modal, ProgressBar, Breadcrumbs)
- [x] API client with full backend integration
- [x] State management (theme, user, library, reader settings)
- [x] Dark/light theme system
- [x] Development server with API proxy
- [x] Integrated startup script (run_server.sh starts both backend + frontend)

**Phase 2: Comic Reader** ✅ COMPLETE

- [x] PageViewer component with multiple fit modes
- [x] Reader controls (prev/next, page slider)
- [x] Keyboard shortcuts (arrows, space, fullscreen)
- [x] Reading progress tracking and auto-save
- [x] Fullscreen mode
- [x] Manga mode (RTL reading) support
- [x] ReaderSettings panel (side drawer)

**Phase 3: Library Browser** ✅ COMPLETE

- [x] Comic grid/list views with toggle
- [x] Folder navigation with breadcrumbs
- [x] Sorting and filtering options
- [x] Library sidebar on home page
- [x] Folder covers (using first comic)
- [x] Continue reading page
- [x] Favorites page
- [x] Comic detail pages
- [x] Progress indicators on cards

**Phase 4: Search & Discovery** ✅ MOSTLY COMPLETE

- [x] Search interface with filters
- [x] Multi-library search
- [x] Status filters (unread/reading/completed)
- [x] Active filter chips
- [ ] Search autocomplete with covers (⏳ IN PROGRESS)
- [ ] Advanced faceted search

**Phase 5: User Features** ✅ PARTIAL

- [x] Favorites system (add/remove/view)
- [x] Comic detail pages with full metadata
- [x] Reading progress tracking
- [ ] Reading lists management UI (API ready, UI pending)
- [ ] Tags/labels UI (API ready, UI pending)

**Phase 6: Admin Panel** ⏳ BASIC

- [x] Basic admin dashboard
- [x] Library stats display
- [x] Recent activity feed
- [ ] Full library management UI
- [ ] User management UI
- [ ] Server settings UI
- [ ] Metadata enrichment UI

**Documentation**:

- See [WEB_UI_PLAN.md](docs/WEB_UI_PLAN.md) for detailed planning and implementation guide
- See [webui/README.md](webui/README.md) for setup and development instructions

### Phase 5: Advanced Features 🎯 FUTURE

**Metadata Enrichment** (High Priority for large collections):

- [ ] Filename parsing (extract series, volume, year)
- [ ] AniList integration (manga metadata)
- [ ] Comic Vine integration (Western comics)
- [ ] Fuzzy matching & auto-tagging
- [ ] Batch processing (41k+ items)
- [ ] Manual review interface
- [ ] Cover image downloads

**Other Features**:

- [ ] Series auto-detection
- [ ] Collections
- [ ] Smart search
- [ ] Statistics

**Documentation**:

- See [METADATA_ENRICHMENT.md](docs/METADATA_ENRICHMENT.md) for enrichment system
- See [IMPROVEMENTS_AND_FEATURES.md](docs/IMPROVEMENTS_AND_FEATURES.md) for other features

---

## 📊 Project Status

**Current Phase**: Phase 4 (Web UI) - 85% Complete 🚧

**Progress**:
- ✅ Phase 1: Foundation - Complete
- ✅ Phase 2: Mobile UX - Complete
- ✅ Phase 3: YACReader Compatibility - 100% complete 🎉
- ✅ Phase 4: Web UI - 85% Complete (5 of 6 phases done)
- 🎯 Phase 5: Advanced Features - Future

**Code Status**:

*Backend*:

- ✅ Python client library
- ✅ Comic loader
- ✅ Database layer (extended YACReader schema)
- ✅ FastAPI server
- ✅ Legacy API v1 (YACReader compatible)
- ✅ Modern API v2 (100% YACReader compatible) 🎉
- ✅ Mobile UX improvements
- ✅ Session management middleware
- ✅ Favorites, Tags, Reading Lists (17 endpoints)
- ✅ Search functionality
- ✅ **Enhanced run_server.sh with auto-setup** ✨ NEW
- ⏳ Metadata extraction (ComicInfo.xml - optional)

*Frontend*:

- ✅ **Web UI Foundation (SvelteKit + Tailwind)**
- ✅ **Layout & Common Components**
- ✅ **API Client & State Management**
- ✅ **Comic Reader** - Full-featured with keyboard shortcuts
- ✅ **Library Browser** - Grid/list views, folder navigation, covers
- ✅ **Home Page** - Continue reading, recently added, library sidebar
- ✅ **Search Page** - Full-text search with filters
- ✅ **Favorites Page** - Mark and browse favorites
- ✅ **Comic Detail Pages** - Full metadata display
- ⏳ **Search Autocomplete** - In progress
- ⏳ **Admin Panel** - Basic dashboard done, full UI pending
- ⏳ **Reading Lists UI** - API ready, UI pending
- ⏳ **Tags UI** - API ready, UI pending

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

**Backend**:
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pillow Documentation](https://pillow.readthedocs.io/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [Jinja2 Documentation](https://jinja.palletsprojects.com/)

**Frontend**:

- [SvelteKit Documentation](https://kit.svelte.dev/)
- [Tailwind CSS Documentation](https://tailwindcss.com/)
- [TanStack Query Documentation](https://tanstack.com/query/)
- [Lucide Icons](https://lucide.dev/)

---

## 📧 Questions?

Check existing documentation first - we've documented extensively!

If you can't find what you need:
1. Check the appropriate doc file (see index above)
2. Search docs for keywords
3. Check examples and code comments

---

**Last Updated**: 2025-11-09
**Documentation Version**: 4.1
**Project Status**: Phase 4 - 85% Complete (Web UI Fully Functional) ✨
