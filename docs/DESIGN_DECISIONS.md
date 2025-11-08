# Design Decisions

## Summary

This document captures key design decisions for YACLib Enhanced.

## 1. Complete Replacement vs. Proxy Layer

**Decision**: Build a complete replacement server, not a proxy layer.

**Rationale**:
- More control over features and performance
- Can optimize for modern use cases
- Easier to add new functionality
- Still maintain backward compatibility with mobile apps via legacy API

## 2. Centralized Application Database

**Decision**: Store all metadata in a centralized application database, not in comic folders.

**Structure**:
```
# Application data (Linux example)
~/.local/share/yaclib/
├── yaclib.db               # SQLite database with ALL libraries
└── covers/
    ├── {hash}.jpg          # JPEG for mobile (300px)
    └── {hash}.webp         # WebP for web (400px)

# Library folders (clean - just comics!)
/mnt/Blue/Ebooks_Comics/Manga/
├── Series A/
│   └── Issue 01.cbz
└── Series B/
    └── Issue 01.cbz
```

**Platform-specific paths**:
- **Linux**: `~/.local/share/yaclib/` or `~/.config/yaclib/`
- **macOS**: `~/Library/Application Support/YACLib/`
- **Windows**: `%APPDATA%\YACLib\`

**Rationale**:
- Clean comic folders (no hidden metadata cluttering user directories)
- Single database for all libraries (simpler management)
- Centralized backup location
- Standard application data location
- Easier to find and manage configuration
- Can reference multiple library paths from one database

**Alternatives Considered**:
- ❌ Per-library database in comic folders (`.yaclib/` subdirectory)
  - Clutters user's comic directories with hidden folders
  - Multiple databases harder to manage
  - Confusing for users
- ❌ Reuse YACReader's `.yacreaderlibrary/` folder
  - Unnecessary coupling to YACReader
  - Still clutters comic folders
  - Mobile app only needs HTTP API, not database compatibility

## 3. Dual-Format Thumbnail System

**Decision**: Generate both JPEG and WebP thumbnails.

**Formats**:
- **JPEG** (300px): For mobile app compatibility
- **WebP** (400px): For modern web UI (35% smaller)

**Rationale**:
- Mobile apps require JPEG (can't change them)
- WebP provides better compression for web
- Worth the extra storage (~65 MB per 1000 comics)
- Faster web UI load times
- Better user experience

**Implementation**:
- Content negotiation based on Accept header
- Legacy API always serves JPEG
- Modern API prefers WebP with JPEG fallback

## 4. Custom Cover Selection

**Decision**: Allow users to pick any page as the cover thumbnail.

**Storage**: Separate `custom_covers/` folder to distinguish from auto-generated.

**Rationale**:
- Common user request (many comics have blank/boring first pages)
- Easy to implement with dual thumbnail system
- Clear separation (auto vs. custom)
- Can reset to auto-generated easily
- Database tracks which page was selected

**Features**:
- Web UI for page selection
- Preview thumbnails before setting
- Batch operations for multiple comics
- Reset to auto-generated

## 5. Database Strategy

**Decision**: Use our own modern SQLite schema, with YACReader import tool.

**Schema Design**:
- Clean, normalized design optimized for our features
- Support for users, collections, reading lists, series detection
- Reading progress tracking per user
- Statistics and preferences
- Extensible metadata system

**YACReader Migration**:
- Dedicated import tool (`tools/import_yacreader.py`)
- Reads YACReader's `library.ydb` and converts to our format
- Imports comics, folders, covers, and reading progress
- One-time migration, not ongoing sync

**Rationale**:
- **Mobile app doesn't need database compatibility** - it only uses HTTP API
- Freedom to design optimal schema for features
- No constraints from YACReader's legacy schema
- Better support for modern features (users, collections, series)
- Cleaner codebase without compatibility shims
- Import tool provides easy migration path for existing YACReader users

**Alternatives Considered**:
- ❌ Reuse YACReader database format
  - Unnecessary for mobile app compatibility
  - Limits feature development
  - Couples us to their schema evolution
- ❌ Dual database system (compatibility + enhanced)
  - Added complexity
  - Synchronization issues
  - Not needed since mobile app only uses API

## 6. Technology Stack

**Backend**: Python + FastAPI

**Rationale**:
- Fast development
- Excellent async support
- Auto-generated API docs
- Type hints and validation
- WebSocket support built-in
- Large ecosystem for image processing

**Frontend**: Vue 3 or React (TBD)

**Rationale**:
- Modern component-based architecture
- Good comic reader libraries available
- Easy to build responsive UI
- Can be served as static files

**Database**: SQLite (primary) + PostgreSQL (optional advanced mode)

**Rationale**:
- SQLite: Lightweight, no setup, portable
- PostgreSQL: For production deployments needing multi-user/advanced features

## 7. API Versioning

**Decision**: Dual API support (v1 legacy + modern API)

**Structure**:
```
/                       → Legacy v1 (mobile apps)
/library/*              → Legacy v1 routes
/api/v1/*              → Modern REST API (web UI)
/ws/*                  → WebSocket API (real-time updates)
```

**Rationale**:
- Mobile app compatibility (legacy v1)
- Modern features for web UI
- Clear separation of concerns
- Can deprecate legacy eventually

## 8. Session Management

**Decision**: Implement in-memory session store with optional Redis backend.

**Features**:
- Session cookies (compatible with mobile apps)
- Token-based auth for web UI (JWT)
- Configurable session expiry
- Support for multiple concurrent sessions

**Rationale**:
- Mobile apps expect session cookies
- Web UI needs modern auth
- Both can coexist
- Optional Redis for production scaling

## 9. Comic File Processing

**Decision**: Lazy loading with background processing.

**Strategy**:
1. On library scan: Index files, extract metadata
2. On first access: Extract and cache pages
3. Background worker: Pre-generate popular comics

**Rationale**:
- Faster initial scan
- Don't waste resources on unread comics
- Better memory management
- Can prioritize popular/recent comics

## 10. Caching Strategy

**Multi-Layer Caching**:

1. **Browser Cache**:
   - Long-lived (1 year) for covers (immutable)
   - ETags for validation

2. **Server Memory Cache**:
   - LRU cache for frequent covers/pages
   - Configurable size limit

3. **Disk Cache**:
   - Extracted pages in `/var/lib/yaclib/cache/pages/`
   - TTL-based cleanup

4. **CDN/Reverse Proxy** (Optional):
   - nginx can serve static covers directly
   - Reduces server load

**Rationale**:
- Minimize disk I/O (archive extraction is expensive)
- Fast response times
- Scalable to large libraries

## 11. Feature Priorities

**Phase 1: Core Foundation**
1. Comic loader (CBZ/CBR/PDF)
2. Legacy API v1 implementation
3. Basic web reader
4. Database access layer

**Phase 2: Web UI**
1. Modern comic reader
2. Library browser
3. Basic metadata editing
4. Custom cover selection

**Phase 3: Management**
1. Library scanner
2. Upload functionality
3. Admin panel
4. Batch operations

**Phase 4: Advanced**
1. Collections and tags
2. Advanced search
3. Multi-user support
4. Metadata scraping

**Rationale**:
- Get mobile app working first (compatibility)
- Then build web features
- Management tools after UI is usable
- Advanced features last

## 12. Configuration

**Decision**: YAML configuration with environment variable overrides.

**Location**: `/var/lib/yaclib/config.yml`

**Example**:
```yaml
server:
  host: 0.0.0.0
  port: 8080

libraries:
  - path: /mnt/Blue/Ebooks_Comics/Manga
    name: Manga
  - path: /mnt/Blue/Ebooks_Comics/Comics
    name: Comics

thumbnails:
  jpeg_quality: 85
  webp_quality: 80
  lazy_generation: true

cache:
  memory_limit_mb: 512
  disk_path: /var/lib/yaclib/cache
  page_ttl_hours: 24
```

**Rationale**:
- Easy to edit
- Environment variables for Docker/k8s
- Sensible defaults
- Well-documented

## Future Considerations

### Multi-User Support
- User authentication and authorization
- Per-user reading progress
- Shared libraries with permissions

### Cloud Sync
- Sync reading progress across devices
- Backup metadata to cloud
- Optional media storage in cloud

### Advanced Metadata
- ComicVine integration
- Automatic series detection
- Publisher/creator databases
- Release date tracking

### Performance
- Distributed caching (Redis cluster)
- Database replication
- CDN integration
- Progressive web app (offline support)

## Migration Path from YACReader

For existing YACReader users:

1. **Keep YACReader Server Running**: Test YACLib alongside
2. **Import Library**: Point to existing `.yacreaderlibrary`
3. **Generate WebP**: Background task converts existing JPEGs
4. **Verify Compatibility**: Test with mobile app
5. **Switch**: Update mobile app to new server
6. **Disable YACReader**: Stop old server once confident

**Rollback Plan**:
- Keep YACReader database backup
- Can point mobile apps back to YACReader
- No data loss (we only add, don't modify)
