# Comprehensive Refactor Plan for Kottlib

## 📊 Current State Analysis

### Critical File Size Issues

| File | Size | Lines | Primary Issue |
|------|------|-------|---------------|
| `src/api/routers/scanners.py` | **65 KB** | 1743 | Massive - multiple concerns mixed |
| `src/database/database.py` | **54 KB** | 1799 | Too many operations in one file |
| `src/scanner/threaded_scanner.py` | **42 KB** | 1078 | Multiple responsibilities |
| `src/api/routers/legacy_v1.py` | **33 KB** | 960 | Large but acceptable (legacy compat) |
| `src/api/routers/v2/series.py` | **31 KB** | ~800 | Could be split |
| `src/api/routers/v2/comics.py` | **28 KB** | ~750 | Could be split |
| `src/database/models.py` | **27 KB** | ~700 | Acceptable for models |
| `src/api/routers/v2/folders.py` | **24 KB** | ~650 | Could be split |

### Structural Issues Identified

1. **Duplicate Scanner Directories** - Three separate locations for scanners:
   - `scanners/` (root level) - Contains scanner implementations
   - `src/scanners/` - Contains base scanner, manager, schemas
   - `src/scanner/` - Core scanning engine (different purpose)

2. **Inconsistent Import Patterns** - Many files have try/except import blocks for relative vs absolute imports

3. **Mixed Concerns in API Routers** - Business logic embedded in route handlers

4. **Duplicate Code Patterns** - Progress tracking, path utilities, error handling

5. **No Clear Service Layer** - Only `src/services/` has 3 files, business logic scattered

---

## 🏗️ Proposed Refactor Plan

### Phase 1: Break Down Critical Large Files (High Priority)

#### 1.1 Split `src/api/routers/scanners.py` (65KB → ~8 files)

**Current problems:**
- Progress tracking logic (~200 lines)
- 15+ Pydantic models (~150 lines)
- Scanner manager singleton
- 12+ API endpoints
- Background task functions (~400 lines)
- Library scan task (~300 lines)

**Proposed structure:**
```
src/api/routers/scanners/
├── __init__.py              # Re-exports router
├── router.py                # Main router with endpoint registrations only
├── models.py                # All Pydantic models (ScanRequest, ScanResult, etc.)
├── progress.py              # Progress tracking (_scan_progress, update/get/clear)
├── endpoints/
│   ├── __init__.py
│   ├── available.py         # GET /available, GET /libraries
│   ├── configure.py         # PUT /libraries/{id}/configure
│   ├── scan_single.py       # POST /scan, POST /scan/series
│   ├── scan_bulk.py         # POST /scan/bulk
│   ├── scan_library.py      # POST /scan/library, GET progress, DELETE progress
│   ├── scan_comic.py        # POST /scan/comic
│   └── metadata.py          # POST /clear-metadata, POST /verify-credentials
└── tasks/
    ├── __init__.py
    └── library_scan_task.py # _run_library_scan_task background function
```

#### 1.2 Split `src/database/database.py` (54KB → ~10 files)

**Current problems:**
- Path utilities (~100 lines)
- Database class (~150 lines)
- Library operations (~150 lines)
- Comic operations (~300 lines)
- Folder operations (~200 lines)
- User/Session operations (~100 lines)
- Reading progress (~150 lines)
- Cover operations (~150 lines)
- Favorites operations (~100 lines)
- Labels operations (~200 lines)
- Reading lists (~200 lines)

**Proposed structure:**
```
src/database/
├── __init__.py              # Re-exports (update existing)
├── connection.py            # Database class, engine, session management
├── paths.py                 # get_project_root, get_default_db_path, get_data_dir, etc.
├── migrations.py            # _run_migrations method extracted
├── models.py                # Keep as-is
├── operations/
│   ├── __init__.py          # Re-exports all operations
│   ├── library.py           # create_library, get_library_by_id, update_library, etc.
│   ├── comic.py             # create_comic, get_comic_by_id, search_comics, etc.
│   ├── folder.py            # create_folder, get_folder_by_path, get_or_create_root_folder
│   ├── user.py              # get_user_by_username, get_user_by_id
│   ├── session.py           # create_session, get_session_by_id, cleanup_expired
│   ├── progress.py          # update_reading_progress, get_continue_reading
│   ├── cover.py             # create_cover, get_cover, get_best_cover, delete_cover
│   ├── favorite.py          # add_favorite, remove_favorite, get_user_favorites
│   ├── label.py             # create_label, add_label_to_comic, get_comic_labels
│   └── reading_list.py      # create_reading_list, add_comic_to_reading_list
├── enhanced_search.py       # Keep as-is
├── search_index.py          # Keep as-is
└── migrations/              # Keep as-is
```

#### 1.3 Split `src/scanner/threaded_scanner.py` (42KB → ~6 files)

**Current problems:**
- ScanResult dataclass
- Structure classification logic (~100 lines)
- File discovery (~50 lines)
- Folder creation (~100 lines)
- Parallel processing (~150 lines)
- Metadata extraction (~200 lines)
- Thumbnail generation
- Series table rebuild (~100 lines)
- Series tree cache building (~200 lines)

**Proposed structure:**
```
src/scanner/
├── __init__.py              # Update exports
├── base.py                  # ScanResult dataclass, base scanner interface
├── file_discovery.py        # _discover_files, is_comic_file checks
├── structure_classifier.py  # _classify_series_structure, _scan_structure
├── folder_manager.py        # _create_folders, folder mapping logic
├── comic_processor.py       # _process_single_comic, _extract_metadata
├── thumbnail_manager.py     # _generate_thumbnails (calls thumbnail_generator)
├── series_builder.py        # _rebuild_series_table, _build_series_tree_cache
├── threaded_scanner.py      # ThreadedScanner class (orchestrator only, ~200 lines)
├── comic_loader.py          # Keep as-is
├── thumbnail_generator.py   # Keep as-is
└── tool_check.py            # Keep as-is
```

---

### Phase 2: Consolidate Duplicate Code (Medium Priority)

#### 2.1 Consolidate Scanner Directories

**Current state (confusing):**
```
scanners/                    # Root level - scanner implementations
├── AniList/
├── ComicVine/
├── mangadex/
├── metron/
└── nhentai/

src/scanners/                # Framework code
├── base_scanner.py
├── scanner_manager.py
├── metadata_schema.py
└── config_schema.py

src/scanner/                 # Core scanning engine (different!)
├── threaded_scanner.py
├── comic_loader.py
└── thumbnail_generator.py
```

**Proposed structure:**
```
src/scanner/                 # Core scanning engine (keep, rename for clarity)
├── ... (as restructured above)

src/metadata_providers/      # Rename from scanners - clearer purpose
├── __init__.py
├── base.py                  # BaseScanner class
├── manager.py               # ScannerManager
├── schema.py                # Metadata schemas
├── config.py                # Config schemas
├── utils.py                 # Keep
└── providers/               # Move from root scanners/
    ├── __init__.py
    ├── anilist/
    ├── comicvine/
    ├── mangadex/
    ├── metron/
    └── nhentai/
```

Then delete root `scanners/` directory after migration.

#### 2.2 Create Shared Utilities Module

**Identified duplications:**
- Path handling in `database.py`, `threaded_scanner.py`, `config.py`
- Error handling patterns in multiple routers
- Progress tracking in `scanners.py` (could be reusable)

**Proposed structure:**
```
src/utils/
├── __init__.py
├── paths.py                 # Centralize: get_project_root, resolve_path, etc.
├── hashing.py               # File hashing utilities
├── exceptions.py            # Custom exception classes (YACLibError, ScanError, etc.)
├── progress.py              # Generic progress tracking utility
├── series_utils.py          # Keep existing
└── validators.py            # Input validation helpers
```

#### 2.3 Fix Import Patterns

**Current problem:** Many files have this pattern:
```python
try:
    from ..database import ...
except ImportError:
    from database import ...
```

**Solution:**
- Ensure all code runs as a package
- Use absolute imports consistently: `from src.database import ...`
- Update `__init__.py` files for proper exports
- Add `src` to Python path in entry points only

---

### Phase 3: Create Proper Service Layer (Medium Priority)

**Current state:** Only 3 files in `src/services/`:
- `mangadex_client.py` (11KB)
- `metadata_service.py` (9KB)
- `scheduler.py` (4KB)

**Proposed expansion:**
```
src/services/
├── __init__.py
├── library_service.py       # High-level library operations
│                            # - create_library_with_scan()
│                            # - delete_library_with_cleanup()
│                            # - get_library_statistics()
├── scan_service.py          # Orchestrates scanning
│                            # - scan_library()
│                            # - scan_single_comic()
│                            # - get_scan_progress()
├── search_service.py        # Search logic extracted from routers
│                            # - search_comics()
│                            # - advanced_search()
│                            # - autocomplete()
├── cover_service.py         # Cover generation/retrieval
│                            # - get_cover_for_comic()
│                            # - set_custom_cover()
│                            # - regenerate_covers()
├── reading_service.py       # Reading progress & lists
│                            # - update_progress()
│                            # - get_continue_reading()
│                            # - manage_reading_lists()
├── metadata_service.py      # Keep existing, expand
├── mangadex_client.py       # Keep as-is
└── scheduler.py             # Keep as-is
```

---

### Phase 4: Performance Improvements (Medium Priority)

#### 4.1 Database Layer
- [ ] **Add database indexes** - Verify indexes on: `comic.hash`, `comic.path`, `comic.library_id`, `comic.folder_id`, `comic.series`
- [ ] **Implement query batching** - Bulk inserts in scanner instead of individual commits
- [ ] **Review N+1 queries** - Add eager loading where appropriate (e.g., comic.folder)
- [ ] **Connection pool tuning** - Currently using NullPool; evaluate for production

#### 4.2 Scanner Optimizations
- [ ] **Async file I/O** - Use `aiofiles` for file operations in scanner
- [ ] **Memory-efficient thumbnails** - Stream processing for large images
- [ ] **Configurable batch sizes** - Allow tuning commit frequency
- [ ] **Parallel hash calculation** - Hash multiple files concurrently

#### 4.3 API Layer
- [ ] **Add response caching** - Cache library listings, folder trees (they change rarely)
- [ ] **Implement ETags** - For cover images (already have `Cache-Control`)
- [ ] **Async database sessions** - Consider SQLAlchemy async if needed
- [ ] **Pagination consistency** - Ensure all list endpoints support pagination

---

### Phase 5: Code Quality Improvements (Lower Priority)

#### 5.1 Type Hints
- Add type hints to all public functions
- Use `TypedDict` for complex dict returns
- Add `py.typed` marker for type checking

#### 5.2 Documentation
- Add docstrings to all public modules
- Update API documentation
- Add architecture documentation

#### 5.3 Testing
- Add unit tests for new service layer
- Add integration tests for refactored modules
- Ensure test coverage for database operations

#### 5.4 Duplicate Endpoint Detection
**Found duplicate route registration:**
```python
# In scanners.py - same endpoint defined twice!
@router.put("/libraries/{library_id}/configure", ...)  # Line 498
async def configure_library_scanner(...):
    ...

@router.put("/libraries/{library_id}/configure", ...)  # Line 981
async def configure_library_scanner(...):
    ...
```
This needs to be fixed - remove the duplicate.

---

## 📋 Implementation Priority & Checklist

### 🔴 Phase 1: Critical (Do First)
- [ ] Split `src/api/routers/scanners.py` (65KB)
- [ ] Split `src/database/database.py` (54KB)
- [ ] Split `src/scanner/threaded_scanner.py` (42KB)
- [ ] Fix duplicate endpoint in scanners.py

### 🟡 Phase 2: Important (Do Second)
- [ ] Consolidate scanner directories
- [ ] Create shared utilities module
- [ ] Fix import patterns
- [ ] Create service layer

### 🟢 Phase 3: Performance (Do Third)
- [ ] Add database indexes
- [ ] Implement query batching
- [ ] Add response caching
- [ ] Review N+1 queries

### 🔵 Phase 4: Quality (Ongoing)
- [ ] Add type hints
- [ ] Improve documentation
- [ ] Add tests for refactored code

---

## 🧪 Testing Strategy

For each refactored module:
1. **Before refactoring:** Ensure existing tests pass
2. **During refactoring:** Keep tests passing at each step
3. **After refactoring:** Add new unit tests for extracted modules
4. **Integration tests:** Verify API endpoints still work correctly

---

## 📁 Final Proposed Directory Structure

```
src/
├── api/
│   ├── main.py
│   ├── cover_utils.py
│   ├── error_handling.py
│   ├── middleware/
│   └── routers/
│       ├── __init__.py
│       ├── config.py
│       ├── covers.py
│       ├── legacy_v1.py
│       ├── libraries.py
│       ├── user_interactions.py
│       ├── scanners/              # NEW: Split from single file
│       │   ├── __init__.py
│       │   ├── router.py
│       │   ├── models.py
│       │   ├── progress.py
│       │   ├── endpoints/
│       │   └── tasks/
│       └── v2/
│           ├── ... (keep as-is for now)
├── database/
│   ├── __init__.py
│   ├── connection.py              # NEW: Extracted
│   ├── paths.py                   # NEW: Extracted
│   ├── migrations.py              # NEW: Extracted
│   ├── models.py
│   ├── operations/                # NEW: Split operations
│   │   ├── __init__.py
│   │   ├── library.py
│   │   ├── comic.py
│   │   ├── folder.py
│   │   ├── user.py
│   │   ├── session.py
│   │   ├── progress.py
│   │   ├── cover.py
│   │   ├── favorite.py
│   │   ├── label.py
│   │   └── reading_list.py
│   ├── enhanced_search.py
│   └── search_index.py
├── scanner/
│   ├── __init__.py
│   ├── base.py                    # NEW: Extracted
│   ├── file_discovery.py          # NEW: Extracted
│   ├── structure_classifier.py    # NEW: Extracted
│   ├── folder_manager.py          # NEW: Extracted
│   ├── comic_processor.py         # NEW: Extracted
│   ├── series_builder.py          # NEW: Extracted
│   ├── threaded_scanner.py        # Simplified orchestrator
│   ├── comic_loader.py
│   ├── thumbnail_generator.py
│   └── tool_check.py
├── metadata_providers/            # NEW: Renamed from src/scanners
│   ├── __init__.py
│   ├── base.py
│   ├── manager.py
│   ├── schema.py
│   ├── config.py
│   └── providers/                 # Moved from root scanners/
│       ├── anilist/
│       ├── comicvine/
│       ├── mangadex/
│       ├── metron/
│       └── nhentai/
├── services/
│   ├── __init__.py
│   ├── library_service.py         # NEW
│   ├── scan_service.py            # NEW
│   ├── search_service.py          # NEW
│   ├── cover_service.py           # NEW
│   ├── reading_service.py         # NEW
│   ├── metadata_service.py
│   ├── mangadex_client.py
│   └── scheduler.py
├── utils/
│   ├── __init__.py
│   ├── paths.py                   # NEW: Centralized
│   ├── hashing.py                 # NEW
│   ├── exceptions.py              # NEW
│   ├── progress.py                # NEW
│   ├── validators.py              # NEW
│   └── series_utils.py
├── config.py                      # Could split later if needed
├── constants.py
└── init_db.py
```

---

## Related Documentation

- [Scanners Refactor Details](./refactor/SCANNERS_REFACTOR.md)
- [Database Refactor Details](./refactor/DATABASE_REFACTOR.md)
- [Scanner Engine Refactor Details](./refactor/SCANNER_ENGINE_REFACTOR.md)
- [Code Examples and References](./refactor/CODE_REFERENCES.md)
