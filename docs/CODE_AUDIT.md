# Code Audit — Refactor Opportunities, Dead Code & Code Smells

**Date:** 2025-03-30  
**Scope:** Full `src/`, `tests/`, scanner plugins

---

## Table of Contents

1. [Critical Issues](#1-critical-issues)
2. [Dead Code](#2-dead-code)
3. [Code Duplication](#3-code-duplication)
4. [Code Smells](#4-code-smells)
5. [Refactor Opportunities](#5-refactor-opportunities)
6. [Potential Bugs](#6-potential-bugs)
7. [Inconsistencies](#7-inconsistencies)
8. [Test Coverage Gaps](#8-test-coverage-gaps)

---

## 1. Critical Issues

### 1.1 Entire `src/scanners/` duplicates `src/metadata_providers/`

Seven files in `src/scanners/` are near-exact copies of files in `src/metadata_providers/`:

| scanners/ file | metadata_providers/ file |
|---|---|
| `base_scanner.py` | `base.py` |
| `config_schema.py` | `config.py` |
| `demo_scanners.py` | `demo.py` |
| `scanner_manager.py` | `manager.py` |
| `metadata_schema.py` | `schema.py` |
| `utils.py` | `utils.py` |

**Impact:** Bug fixes only reach one copy. ~1000+ lines of duplicated code.  
**Fix:** Make `src/scanners/` a thin re-export layer importing from `src/metadata_providers/`.

### 1.2 Hardcoded admin password created at request time

- `src/api/middleware/session.py` (~L217–222): `get_request_user()` auto-creates an admin user with password `'changeme'` on every request if the user is missing.
- `src/database/connection.py` (~L87): Default admin stored with plain-text hash `'changeme'`.

**Fix:** Only create the admin user during database initialization, never in request handlers. Hash the default password properly.

### 1.3 Thread-unsafe singleton in scheduler

- `src/services/scheduler.py` (~L20–31): `ScanScheduler.__new__()` singleton check is not protected by a lock — two threads can both see `_instance is None`.

**Fix:** Use `threading.Lock` or module-level instance.

### 1.4 Global mutable state in v2/libraries scan progress

- `src/api/routers/v2/libraries.py` (~L60–80): `_file_scan_progress`, `_progress_lock`, `_active_scans` are module-level dicts mutated from request handlers and daemon threads without full thread safety.

**Fix:** Use a proper concurrent data structure or move progress tracking to the database/Redis.

---

## 2. Dead Code

| Location | Description |
|---|---|
| `src/api/routers/v2/collections.py` ~L280–330 | `create_tag()`, `delete_tag()`, `add_tag_to_comic()`, `remove_tag_from_comic()`, `check_is_favorite()` — defined but never registered as routes (no `@router` decorator) |
| `src/api/routers/v2/reading.py` ~L100–115 | `get_all_libraries_reading()` defined but never route-registered |
| `src/api/main.py` ~L250–270 | `server_info()` and `api_info()` return duplicate data — consolidate to one endpoint |
| `src/services/config_sync.py` ~L210–217 | `sync_config_to_db()` marked deprecated but still imported |
| `src/services/mangadex_client.py` ~L199 | `use_thumbnail` parameter in `download_cover_as_image()` accepted but never used |
| `src/services/metadata_service.py` L4 | `import sys` never used |
| `src/scanner/cleanup.py` ~L135 | Unreachable `return` after function body |
| `src/scanner/folder_manager.py` ~L135 | Same unreachable `return` |
| `src/scanners/demo_scanners.py` ~L58, L127 | Calls `manager.scan()` and `manager.get_configured_libraries()` — methods that don't exist |
| `src/metadata_providers/demo.py` | Same non-existent method calls |
| `src/database/enhanced_search.py` ~L355 | `get_searchable_fields()` TODO — dynamic field extraction never implemented |
| `src/database/migrations/` | `add_cover_source_columns.py` and `add_cover_source_fields.py` do the same thing — duplicate migrations |

---

## 3. Code Duplication

### 3.1 Service layer — library response dict built 4 times

`src/services/library_service.py`: The same ~11-field dictionary construction is copy-pasted in `create_library_with_stats()`, `get_library_with_stats()`, `list_libraries_with_stats()`, and `update_library_with_stats()`.

**Fix:** Extract `_build_library_response_dict(lib, stats)`.

### 3.2 Legacy router — 3 comic endpoints with ~90% identical logic

`src/api/routers/legacy_v1.py` ~L281–540: `/comic/{id}/info`, `/comic/{id}/remote`, `/comic/{id}` all build nearly identical responses.

**Fix:** Extract `_build_comic_info_response()` helper, parameterize differences.

### 3.3 Error handling duplication in cover endpoints

`src/api/routers/covers.py` ~L84–91, L135–142, L194–201: Identical `CoverProviderRateLimitError` / `CoverProviderError` handling in three endpoints.

**Fix:** Create `@handle_cover_errors` decorator.

### 3.4 Error handling duplication — file vs archive handlers

`src/api/error_handling.py` ~L32–102: `_handle_file_error()` and `_handle_archive_error()` follow identical isinstance-chain patterns.

**Fix:** Unified `_to_http_exception(error, status_map)`.

### 3.5 Archive loaders — case-insensitive filename lookup

`src/scanner/loaders/zip.py` ~L68–70 and `src/scanner/loaders/rar.py` ~L76–78: Exact same loop.

**Fix:** Move to `base.py`.

### 3.6 scan_service.py — scanner config extracted twice

`src/services/scan_service.py` ~L55–59 and ~L151–159: Identical 5-line config reading block.

**Fix:** Extract `_get_scanner_config()`.

### 3.7 scan_service.py — 16 repetitive field assignments

`src/services/scan_service.py` ~L196–214: 16 identical `if metadata.get(key) and should_update(…)` patterns.

**Fix:** Loop over a field mapping dict.

### 3.8 User/session retrieval pattern repeated across user_interactions

`src/api/routers/user_interactions.py` — same 5 lines (get DB → get session → get user → verify) in every endpoint.

**Fix:** `Depends(get_current_user_id)`.

### 3.9 Migration logic duplicated

`src/database/connection.py` ~L133–148 duplicates ALTER TABLE logic from `src/database/migrations/`.

**Fix:** Single source of truth in the migration system.

### 3.10 Type conversion duplication in settings

`src/database/operations/setting.py` ~L27–40 and ~L60–75: Conversion logic in both `get_setting()` and `set_setting()`.

**Fix:** Extract `_parse_setting_value()` / `_serialize_setting_value()`.

### 3.11 Cover path search pattern

`src/api/cover_utils.py` ~L43–75: Hierarchical and flat path search repeated for WebP then JPEG.

**Fix:** `for directory in [hierarchical, flat]: for fmt in ['webp', 'jpg']:`.

---

## 4. Code Smells

### 4.1 God functions (>60 lines)

| Function | File | Lines |
|---|---|---|
| `lifespan()` | `src/api/main.py` | ~127 lines |
| `extract_metadata()` | `src/scanner/comic_processor.py` | ~199 lines |
| `process_single_comic()` | `src/scanner/comic_processor.py` | ~128 lines |
| `scan_library()` | `src/scanner/threaded_scanner.py` | ~92 lines |
| `search_comics()` | `src/database/enhanced_search.py` | ~59 lines |
| `get_or_create_root_folder()` | `src/database/operations/folder.py` | ~84 lines |
| `set_custom_cover()` | `src/api/routers/legacy_v1.py` | ~80 lines |
| `sync_reading_progress_v1()` | `src/api/routers/legacy_v1.py` | ~60 lines |
| `migrate_legacy_config_to_db()` | `src/services/config_sync.py` | ~48 lines |
| `apply_scan_result_to_comic()` | `src/services/metadata_service.py` | ~45 lines |
| `dispatch()` | `src/api/middleware/session.py` | ~61 lines |

### 4.2 God classes

- **`Comic` model** (`src/database/models/comic.py`): 83+ columns spanning file metadata, comic metadata, credits, reading state, UI state. Should split into `Comic`, `ComicFile`, `ComicCredits`, `ComicUserData`.
- **`ThreadedScanner`** (`src/scanner/threaded_scanner.py`): ~15 responsibilities (discovery, classification, folder creation, processing, cleanup, series building, caching, progress, threading, error handling).
- **`ComicInfo` dataclass** (`src/scanner/comic_loader.py`): 50+ optional fields.

### 4.3 Magic numbers/strings

| Location | Value | Suggestion |
|---|---|---|
| `src/api/middleware/session.py` ~L49 | `_cleanup_interval = 100` | Named constant with rationale |
| `src/scanner/series_builder.py` ~L83 | `max_depth=10` | `MAX_TREE_DEPTH = 10` |
| `src/scanner/threaded_scanner.py` ~L155 | `time.sleep(0.3)` | `PROGRESS_UPDATE_INTERVAL` |
| `src/scanner/thumbnail_generator.py` ~L15–18 | `(300, 450)`, `(400, 600)`, `85`, `90` | `JPEG_SIZE`, `WEBP_SIZE`, etc. |
| `src/database/enhanced_search.py` ~L175–233 | Relevance weights `200, 150, 120` | Named constants |
| `src/api/routers/legacy_v1.py` ~L427, L511 | Cache-Control headers `31536000`, `86400` | `COVER_CACHE_TTL`, etc. |
| `src/utils/hashing.py` ~L20 | `512 * 1024` | `HASH_CHUNK_SIZE` |
| `src/utils/platform.py` ~L54 | `max_depth = 10` | `MAX_WALKUP_DEPTH` |

### 4.4 Broad exception handling

- `src/api/main.py` ~L173: `@app.exception_handler(Exception)` catches everything, hiding bugs.
- `src/database/connection.py` ~L95: String-matching `"UNIQUE constraint failed"` instead of catching `IntegrityError`.
- `src/api/error_handling.py` ~L62–80: `'badzipfile' in exc_name.lower()` instead of `except BadZipFile`.
- `src/api/routers/v2/session.py` ~L180: Cache invalidation errors silently swallowed.

### 4.5 Module-level side effects

- `src/scanner/loaders/rar.py` ~L16–18: Sets `rarfile.UNRAR_TOOL`, `NEED_COMMENTS`, `USE_DATETIME` at import time.
- `src/metadata_providers/manager.py` ~L101: `sys.path.insert(0, …)` at discovery time.
- `src/scanner/loaders/base.py` ~L53–67: `pages` property triggers I/O and logging.

### 4.6 Unbounded in-memory structures

- `src/api/routers/v2/_shared.py` ~L14: `series_tree_cache = {}` — no TTL or size limit.
- `src/api/routers/v2/_browse_helpers.py` ~L30–45: `apply_random_sort()` loads ALL folder/comic IDs into memory.

### 4.7 N+1 query patterns

- `src/database/operations/setting.py` ~L113–121: `get_all_settings()` calls `get_setting()` per row.
- `src/api/routers/libraries.py` ~L65–91: Each library hits `get_library_stats()` individually.
- `src/api/routers/v2/folders.py` ~L320–380: Fetches all comics/dirs to build stats.

### 4.8 Inconsistent response formats across services

Services return at least 4 different shapes:  
`{"success": bool, "message": str}`, `{"status": "success"|"error"|"skipped"}`, `{"comic_id": int, …}`, or raw model objects. Should standardize.

---

## 5. Refactor Opportunities

### 5.1 Extract startup tasks from lifespan

`src/api/main.py` `lifespan()` should delegate to `_init_db()`, `_init_scheduler()`, `_warmup_cache()`.

### 5.2 Use data-driven field mapping for metadata application

Replace 16+ if-statements in `src/services/scan_service.py` and `src/services/metadata_service.py` with a `FIELD_MAP` dict + loop.

### 5.3 Simplify root folder creation

`src/database/operations/folder.py` `get_or_create_root_folder()` has multiple overlapping lookup strategies. Should use a single unique constraint (`library_id` + `parent_id IS NULL`).

### 5.4 Config router feature-flag defaults

`src/api/routers/config.py` ~L121–138: `get_setting(…) or True` inverts intent — falsy values become True. Use `… if … is not None else True`.

### 5.5 Collapse v1 comic endpoints

Three nearly-identical endpoints in `legacy_v1.py` → one helper + thin wrappers.

### 5.6 Auto-page-count detection should not happen per-request

`src/api/routers/v2/comics.py` ~L77–100: `open_comic()` called on every request for comics with `num_pages=0`. Should batch-fix during scan.

### 5.7 Consolidate cover error handling into decorator

Covers router repeats try/except for rate limit + provider errors in every endpoint.

### 5.8 Standardize service response format

All services should return a consistent `ServiceResult(success, message, data)` or raise domain exceptions.

### 5.9 Replace `sys.path` manipulation with proper packaging

`src/init_db.py`, `src/metadata_providers/manager.py`, `src/scanner/comic_processor.py` all insert into `sys.path`. Use proper package installs or `importlib`.

### 5.10 Upgrade redundant HTTP status constants

`src/constants.py` ~L51–58: Replace hand-rolled constants with `from http import HTTPStatus`.

---

## 6. Potential Bugs

| Location | Description |
|---|---|
| `src/services/metadata_service.py` ~L113, L194 | References `application_result.message` but `MetadataApplicationResult` has no `message` attribute → `AttributeError` at runtime |
| `src/api/routers/v2/search.py` ~L250–300 | Series folder cover lookup: if no comics exist, `first_comic` is `None` and `first_comic[0]` → `TypeError` |
| `src/api/routers/v2/series.py` ~L200–250 | `random.Random(seed)` where `seed=0` treated as falsy → creates unseeded `Random()` |
| `src/api/routers/v2/comics.py` ~L350, L380 | `@handle_comic_archive_errors` applied to both `/page/` and `/remote/page/` — potential double-wrapping |
| `src/api/routers/v2/admin.py` ~L58–75 | Reindex spawns background task with no mutex — rapid calls may corrupt FTS |
| `src/api/routers/app_api/comics.py` ~L70–140 | Calls `get_comic_progress_v2()`, `update_comic_progress_v2_json()`, `get_cover_v2()` — functions that don't exist in v2 router |
| `src/api/routers/app_api/libraries.py` ~L80–100 | Calls `remove_library()`, `scan_library_manual()`, `get_file_scan_progress()`, `clear_file_scan_progress()` — functions missing from v2 |
| `src/database/operations/progress.py` ~L34 | `is_completed = current_page >= total_pages - 1` — marks complete before user reads last page (off-by-one if 0-indexed) |
| `src/scanner/folder_manager.py` ~L79–130 | `_get_or_create_parent_recursive()` has no depth limit → could hit Python recursion limit |
| `src/scanner/thumbnail_generator.py` ~L207–254 | `clean_orphaned_thumbnails()` iterates flat directory but thumbnails stored hierarchically (`hash[:2]/`) — won't find most thumbnails |
| `src/api/routers/config.py` ~L121–138 | `get_setting(…) or True` — falsy DB values (including explicit `False`) default to `True` |
| `src/services/mangadex_client.py` ~L143 | `cover_filename` can be `None` → builds invalid URL without validation |
| `src/api/cover_utils.py` ~L85–107 | `custom_cover_path` passed to `Path()` without checking if absolute |
| `src/api/routers/v2/covers.py` ~L165 | `f"{comic.hash}_mangadex"` — if `comic.hash` is None, produces `"None_mangadex"` |
| `src/database/migrations/add_search_indexes.py` ~L108 | FTS INSERT trigger uses empty `dynamic_metadata` — search index never populated for dynamic fields |

---

## 7. Inconsistencies

| Area | Description |
|---|---|
| **Naming** | `file_hash` vs `hash` property aliases on Comic model; `summary` vs `description`; `DBSession` vs `Session` naming collision in operations/session.py |
| **Import patterns** | `try: from ..X except ImportError: from X` scattered across 6+ files instead of fixing package structure |
| **Error handling** | Some services raise `ValueError`, others return `{"success": False}`. Some routers use decorators, others inline try/except |
| **Response shapes** | 4+ different response dict formats across services (see §4.8) |
| **Boolean storage** | `Library.exclude_from_webui` declared `bool` but backed by `Integer` column |
| **Logging prefixes** | `[COMIC_LOADER]`, `[FULLINFO]` manual prefixes only in some modules; others use `logger.name` |
| **Singleton patterns** | `provider_manager.py` uses module-level `_default_manager`; `scheduler.py` uses `__new__` override; `scanner_manager.py` uses another pattern. None are thread-safe |
| **Config override** | `get_config_dir()` has no env var override but `get_data_dir()` does |
| **API parameter naming** | `libraries/{library_id}` in some routers vs `library/{library_id}` in others |
| **Field casing** | v2/reading mixes `last_time_opened` (snake) vs `lastTimeOpened` (camel) |
| **Duplicate operations** | `get_comics_in_folder()` and `get_comics_in_folder_simple()` in operations/comic.py — latter is redundant |
| **v2/comics** | Routes `/page/{page_num}` and `/remote/page/{page_num}` are near-identical — should share handler |

---

## 8. Test Coverage Gaps

### Coverage by layer (approximate)

```
API Layer:           ████████░░  ~80%  (v1/v2 tested via integration, routers/middleware not directly)
Database Layer:      ██████░░░░  ~60%  (CRUD tested, most operations/*.py NOT)
Services Layer:      ███░░░░░░░  ~30%  (2 of 12 services have tests)
Scanner Layer:       ██░░░░░░░░  ~20%  (comic_loader + MangaDex plugin only)
Metadata Providers:  ░░░░░░░░░░  ~0%
Utils:               ░░░░░░░░░░  ~0%
Migrations:          ░░░░░░░░░░  ~0%
```

### Completely untested source modules

- `src/services/`: `scan_service`, `reading_service`, `library_service`, `cover_service`, `search_service`, `mangadex_client`, `comic_info_service`, `scheduler`, `library_cache`
- `src/scanner/`: `threaded_scanner`, `comic_processor`, `structure_classifier`, `folder_manager`, `file_discovery`, `series_builder`, `thumbnail_generator`, `tool_check`, all `loaders/`
- `src/database/operations/`: `cover`, `favorite`, `folder`, `label`, `progress`, `reading_list`, `user`, `stats`
- `src/database/`: `enhanced_search`, `search_index`, `paths`, all `migrations/`
- `src/utils/`: `sorting`, `hashing`, `series_utils`, `platform`
- `src/metadata_providers/`: all files
- `src/api/`: `error_handling`, `response_builders`, `cover_utils`, `dependencies`, `middleware/`
- `src/client/kottlib.py`

### Test anti-patterns found

- Weak assertions: some integration tests accept `status in [200, 404, 500]`
- `authenticated_client` fixture uses cookie injection instead of proper auth
- Fixture coupling: `test_get_all_libraries` depends on `create_library` working
- No negative tests for invalid archives, corrupted metadata, or SQL injection
- No concurrency tests for services or scheduler
