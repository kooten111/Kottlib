# Issue Tracker

Tracks all issues identified in the [code audit](CODE_AUDIT.md).  
Mark items `[x]` when resolved.

---

## Critical — Security & Concurrency

- [ ] **CRIT-01** — `src/scanners/` duplicates `src/metadata_providers/` (7 files, ~1000+ lines)
  - Make `src/scanners/` a thin re-export layer
---

## Bugs — Likely Runtime Failures

- [ ] **BUG-07** — Off-by-one in reading completion: marks done before last page
  - `src/database/operations/progress.py` ~L34
---

## Dead Code

- [ ] **DEAD-08** — Calls to non-existent manager methods in demo files
  - `src/scanners/demo_scanners.py` ~L58, L127
  - `src/metadata_providers/demo.py` — same
- [ ] **DEAD-09** — `get_searchable_fields()` TODO never implemented
  - `src/database/enhanced_search.py` ~L355
- [ ] **DEAD-10** — Duplicate migrations do the same thing
  - `src/database/migrations/add_cover_source_columns.py`
  - `src/database/migrations/add_cover_source_fields.py`
- [ ] **DEAD-11** — `get_comics_in_folder_simple()` is redundant
  - `src/database/operations/comic.py` — `get_comics_in_folder()` with `library_id=None` does the same

---

## Code Duplication

- [ ] **DUP-02** — 3 comic endpoints ~90% identical in `legacy_v1.py` ~L281–540
  - Extract `_build_comic_info_response()`
- [ ] **DUP-03** — Cover error handling copy-pasted 3× in `covers.py`
  - Create `@handle_cover_errors` decorator
- [ ] **DUP-04** — `_handle_file_error()` / `_handle_archive_error()` same pattern
  - `src/api/error_handling.py` ~L32–102 — unify into `_to_http_exception()`
- [ ] **DUP-05** — Case-insensitive filename lookup duplicated in zip.py & rar.py
  - Move to `src/scanner/loaders/base.py`
- [ ] **DUP-06** — Scanner config extraction duplicated in `scan_service.py`
  - ~L55–59 and ~L151–159 — extract `_get_scanner_config()`
- [ ] **DUP-07** — 16 repetitive field assignments in `scan_service.py` ~L196–214
  - Replace with field mapping dict + loop
- [ ] **DUP-08** — User/session retrieval repeated across `user_interactions.py`
  - Replace with `Depends(get_current_user_id)`
- [ ] **DUP-09** — Migration logic in `connection.py` duplicates `migrations/`
  - `src/database/connection.py` ~L133–148 — use migration system as single source
- [ ] **DUP-10** — Type conversion logic duplicated in `setting.py`
  - `src/database/operations/setting.py` ~L27–40 & ~L60–75
  - Extract `_parse_setting_value()` / `_serialize_setting_value()`
- [ ] **DUP-11** — Cover path search pattern repeated for hierarchical/flat × webp/jpg
  - `src/api/cover_utils.py` ~L43–75 — nest two loops

---

## Code Smells

### God functions (>60 lines)

- [ ] **SMELL-01** — `lifespan()` ~127 lines — `src/api/main.py`
  - Split into `_init_db()`, `_init_scheduler()`, `_warmup_cache()`
- [ ] **SMELL-02** — `extract_metadata()` ~199 lines — `src/scanner/comic_processor.py`
  - Extract `_classify_series()`, `_parse_comicinfo()`, `_validate_metadata()`
- [ ] **SMELL-03** — `process_single_comic()` ~128 lines — `src/scanner/comic_processor.py`
  - Extract `_check_fast_path()`, `_check_hash_path()`, `_open_and_process()`
- [ ] **SMELL-04** — `scan_library()` ~92 lines — `src/scanner/threaded_scanner.py`
  - Break into `_phase_discovery()`, `_phase_process()`, `_phase_cleanup()`, `_phase_build()`
- [ ] **SMELL-05** — `get_or_create_root_folder()` ~84 lines — `src/database/operations/folder.py`
  - Simplify overlapping lookup strategies
- [ ] **SMELL-06** — `set_custom_cover()` ~80 lines — `src/api/routers/legacy_v1.py`
  - Move to service layer with transaction management
- [ ] **SMELL-07** — `dispatch()` ~61 lines — `src/api/middleware/session.py`
  - Extract `_validate_session()`, `_create_session()`, `_cleanup_sessions()`
- [ ] **SMELL-08** — `apply_scan_result_to_comic()` ~45 lines — `src/services/metadata_service.py`
  - Extract `_should_update_field()`, `_apply_field_value()`

### God classes

- [ ] **SMELL-09** — `Comic` model has 83+ columns across 5 concerns
  - `src/database/models/comic.py`
  - Consider splitting: core, file, credits, user state
- [ ] **SMELL-10** — `ThreadedScanner` has ~15 responsibilities
  - `src/scanner/threaded_scanner.py`
- [ ] **SMELL-11** — `ComicInfo` dataclass has 50+ optional fields
  - `src/scanner/comic_loader.py`

### Magic numbers / strings

- [ ] **SMELL-12** — `_cleanup_interval = 100` unexplained — `session.py` ~L49
- [ ] **SMELL-13** — `max_depth=10` hardcoded — `series_builder.py` ~L83
- [ ] **SMELL-14** — `time.sleep(0.3)` magic — `threaded_scanner.py` ~L155
- [ ] **SMELL-15** — Thumbnail dimensions/quality hardcoded — `thumbnail_generator.py` ~L15–18
- [ ] **SMELL-16** — Relevance weights `200, 150, 120` — `enhanced_search.py` ~L175–233
- [ ] **SMELL-17** — Cache-Control TTLs in literals — `legacy_v1.py` ~L427, L511
- [ ] **SMELL-18** — `512 * 1024` chunk size — `hashing.py` ~L20
- [ ] **SMELL-19** — `max_depth = 10` — `platform.py` ~L54

### Broad exception handling

- [ ] **SMELL-20** — Catch-all `Exception` handler hides bugs — `main.py` ~L173
- [ ] **SMELL-22** — String-matching for `BadZipFile` — `error_handling.py` ~L62–80
- [ ] **SMELL-23** — Cache invalidation errors silently swallowed — `v2/session.py` ~L180

### Module-level side effects

- [ ] **SMELL-24** — `rar.py` sets global `rarfile` config at import — ~L16–18
- [ ] **SMELL-25** — `manager.py` mutates `sys.path` at discovery — ~L101
- [ ] **SMELL-26** — `base.py` loader `pages` property triggers I/O — ~L53–67

### N+1 queries

- [ ] **SMELL-27** — `get_all_settings()` fires per-row query — `setting.py` ~L113–121
- [ ] **SMELL-28** — Per-library `get_library_stats()` — `routers/libraries.py` ~L65–91
- [ ] **SMELL-29** — Folder stats fetch all comics — `v2/folders.py` ~L320–380

### Unbounded in-memory structures

- [ ] **SMELL-30** — `series_tree_cache = {}` no TTL/limit — `v2/_shared.py` ~L14
- [ ] **SMELL-31** — `apply_random_sort()` loads all IDs into memory — `v2/_browse_helpers.py` ~L30–45

### Other smells

- [ ] **SMELL-32** — Inconsistent response formats across services (4+ shapes)
- [ ] **SMELL-33** — `auto-page-count` detection on every request for `num_pages=0` comics
  - `src/api/routers/v2/comics.py` ~L77–100 — should batch-fix during scan

---

## Refactor Opportunities

- [ ] **REFAC-01** — Extract startup tasks from `lifespan()` in `main.py`
- [ ] **REFAC-02** — Data-driven field mapping for metadata application
  - `scan_service.py`, `metadata_service.py`
- [ ] **REFAC-03** — Simplify `get_or_create_root_folder()` with unique constraint
- [ ] **REFAC-04** — Fix feature-flag defaults (`or True` → `is not None`)
  - `src/api/routers/config.py` ~L121–138
- [ ] **REFAC-05** — Collapse 3 legacy v1 comic endpoints into one helper
- [ ] **REFAC-06** — Consolidate cover error handling into decorator
- [ ] **REFAC-07** — Standardize service response format into `ServiceResult`
- [ ] **REFAC-08** — Replace `sys.path` manipulation with proper packaging
  - `init_db.py`, `metadata_providers/manager.py`, `scanner/comic_processor.py`
- [ ] **REFAC-09** — Replace hand-rolled HTTP status constants with `http.HTTPStatus`
  - `src/constants.py` ~L51–58
- [ ] **REFAC-10** — Use `Depends(get_current_user_id)` in user_interactions router

---

## Inconsistencies

- [ ] **INCON-01** — `file_hash`/`hash` and `summary`/`description` aliases on Comic model
- [ ] **INCON-02** — Fallback import pattern (`try: from ..X except: from X`) in 6+ files
- [ ] **INCON-03** — Error handling: some services `raise`, others return error dicts
- [ ] **INCON-04** — `Library.exclude_from_webui` typed `bool` but stored as `Integer`
- [ ] **INCON-05** — Manual logging prefixes (`[COMIC_LOADER]`, `[FULLINFO]`) in some modules only
- [ ] **INCON-06** — Three different singleton patterns, none thread-safe
- [ ] **INCON-07** — `get_config_dir()` has no env var override, `get_data_dir()` does
- [ ] **INCON-08** — API path: `libraries/{library_id}` vs `library/{library_id}`
- [ ] **INCON-09** — Field casing: snake `last_time_opened` vs camel `lastTimeOpened` in v2/reading
- [ ] **INCON-10** — `/page/{page_num}` and `/remote/page/{page_num}` nearly identical routes

---

## Test Coverage

- [ ] **TEST-01** — Add tests for `src/services/` (9 of 12 files untested)
  - `scan_service`, `reading_service`, `library_service`, `cover_service`, `search_service`, `mangadex_client`, `comic_info_service`, `scheduler`, `library_cache`
- [ ] **TEST-02** — Add tests for `src/scanner/` infrastructure
  - `threaded_scanner`, `comic_processor`, `structure_classifier`, `folder_manager`, `file_discovery`, `series_builder`, `thumbnail_generator`, `tool_check`
- [ ] **TEST-03** — Add tests for all `src/scanner/loaders/`
- [ ] **TEST-04** — Add tests for `src/database/operations/`
  - `cover`, `favorite`, `folder`, `label`, `progress`, `reading_list`, `user`, `stats`
- [ ] **TEST-05** — Add tests for `src/database/` search & migrations
  - `enhanced_search`, `search_index`, `paths`, all `migrations/`
- [ ] **TEST-06** — Add tests for `src/utils/`
  - `sorting`, `hashing`, `series_utils`, `platform`
- [ ] **TEST-07** — Add tests for `src/metadata_providers/`
- [ ] **TEST-08** — Add tests for `src/api/` internals
  - `error_handling`, `response_builders`, `cover_utils`, `dependencies`, `middleware/`
- [ ] **TEST-09** — Fix test anti-patterns
  - Weak assertions (`status in [200, 404, 500]`)
  - Cookie-injected `authenticated_client`
  - Coupled fixtures
  - No negative / concurrency tests

---

## UI Responsiveness (Manual QA - 2026-04-24)

- [ ] **UI-RESP-01** - Sort action latency spike on `Last Updated` in Manga browse
  - **Where:** `/library/2/browse`
  - **Repro:** Open Manga -> click `Name` sort -> choose `Last Updated`
  - **Observed:** URL update to `?sort=updated` took about 4.07s in this session; library switching was much faster (about 0.19s to 0.78s for URL changes)
  - **Likely cause:** Expensive sort query or missing DB/index optimization for updated timestamp sorting

- [ ] **UI-RESP-02** - Repeated aborted route data requests during normal SPA navigation
  - **Where:** Browse routes (All/Manga/Comics and sorted variants)
  - **Repro:** Switch libraries repeatedly and change sort mode
  - **Observed:** Frequent `__data.json?...x-sveltekit-invalidated=01` `net::ERR_ABORTED` requests on route/sort changes
  - **Likely cause:** Overlapping invalidations/prefetches where previous request is canceled by next navigation; may be expected in part, but volume suggests redundant fetch churn
  - **Mitigation:** Sidebar browse navigation now skips same-URL `goto()` calls to avoid redundant route churn from repeated clicks
  - **Latest retest:** Three repeated Manga -> All -> Manga passes now consistently produced two aborted `__data.json` requests per roundtrip (one per route transition), with stable timings (Manga -> All about 137-158ms, All -> Manga about 849-865ms)

- [ ] **UI-RESP-03** - Aborted image/favorite requests when entering a series route from sidebar
  - **Where:** Sidebar entry into series browse routes (for example `/library/2/browse/67%25%20Inertia?sort=updated`)
  - **Repro:** In Manga browse, click a folder entry in sidebar (for example `67% Inertia`)
  - **Observed:** Multiple cover and favorite-check requests logged as `net::ERR_ABORTED` during route transition
  - **Likely cause:** In-flight requests from prior view are not fully canceled/debounced before new view fetch starts; possible over-eager parallel loading
  - **Mitigation:** Favorite status checks in series/detail panels now use `AbortController` so stale requests are canceled cleanly during fast route or selection changes
  - **Local root cause identified:** Sidebar folder nodes were issuing both the anchor's default navigation and the parent `goto()` navigation on plain clicks, and those two paths could differ (`/browse/{id}` vs `/browse/{encoded-name}`), creating competing route loads plus duplicate favorite checks
  - **Local fix applied:** `SeriesTreeNode` now prevents the default plain-click navigation and aligns folder href generation to the encoded folder path
  - **Latest retest:** Three repeated clicks into `67% Inertia` all navigated directly to the encoded-name route in about 358-426ms with no `/browse/{id}` fallback observed; residual aborted requests remain (1-2 `__data.json` plus occasional `/api/favorites/{id}/check` per entry)

- [x] **UI-RESP-04** - Sort dropdown overlay blocks other controls until explicitly closed or option selected
  - **Where:** Browse header sort control
  - **Repro:** Click `Name` to open sort menu, then immediately try clicking a library button in sidebar
  - **Observed:** Full-screen overlay intercepts pointer events; background click target is blocked
  - ~~**Likely cause:** Modal-style click-capture layer (`fixed inset-0`) is intentional, but interaction can feel sticky because users must close dropdown first~~
  - **Fixed:** Replaced the blocking full-screen overlay with local click-outside handling and `Escape` close behavior in the browse sort dropdown

- [x] **UI-RESP-05** - Toolbar discoverability issue for view controls
  - **Where:** Browse header controls (`Cover Size`, `Grid View`, `List View`)
  - **Repro:** Use view controls without prior context/tooltips
  - **Observed:** Icon-only controls are not self-explanatory; slows first-time interaction despite controls functioning correctly
  - ~~**Likely cause:** Missing visible text labels/tooltips and reduced affordance for icon-only actions~~
  - **Fixed:** Added visible text labels alongside the icons while retaining titles/ARIA labels for the controls

### Notes from this pass

- Visible (in-viewport) cover image loading looked good during library switches in this run (about 0.4ms to 0.6ms to reach >=95% loaded for visible covers after route update).
- I could not reliably force a true mobile viewport in this browser harness, so mobile-specific responsiveness still needs a real-device or emulation pass.

### Re-test (2026-04-24, later pass)

- Library switch times improved and stabilized in this run:
  - Manga -> All: median about 180ms (3 runs)
  - All -> Manga: median about 437ms (3 runs)
- Sort latency for `Last Updated` in Manga improved significantly:
  - Previous sample: about 4.07s
  - Re-test median: about 484ms (3 runs)
- Visible cover image readiness remained strong (>=95% in-viewport covers effectively immediate after route update in measured runs).
- `__data.json` `net::ERR_ABORTED` requests still appear during fast route/sort transitions, but UX responsiveness is currently much better than the earlier baseline.

### Re-test (2026-04-24, post-restart pass)

- Library switching remained stable over 3 repeat runs:
  - Manga -> All: about 137-158ms
  - All -> Manga: about 849-865ms
  - Aborted route data fetches were consistent at 2 per roundtrip (one per transition), with no large burst behavior seen.
- Sidebar series entry (`67% Inertia`) now consistently lands on encoded-name route over 3 runs:
  - Click-to-route timing: about 358-426ms
  - No competing `/browse/{id}` route loads detected in failed-request traces.
  - Residual aborts still occur during transition (`__data.json` and occasional `/api/favorites/{id}/check`), but route targeting behavior appears corrected.
