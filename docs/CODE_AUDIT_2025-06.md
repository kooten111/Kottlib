# Code Audit — June 2025

**Date:** 2025-06-28  
**Git SHA:** `73766a696b9789e6783e31cb2001b900c8a9733a`  
**Scope:** Full codebase — `src/`, `webui/`, `tests/`, `scanners/`, `scripts/`  
**Baseline:** Diff against [CODE_AUDIT.md](CODE_AUDIT.md) (2025-03-30)  
**Artifacts:** `docs/review/snapshot.md`, `docs/review/route_inventory.md`, `docs/review/coverage.txt`

---

## Executive Summary — Top 10 Findings

| # | ID | Severity | Finding |
|---|-----|----------|---------|
| 1 | D1 | Critical | ~1,000 LOC duplicate scanner framework in `src/scanners/` (canonical: `src/metadata_providers/`) |
| 2 | S1 | Critical | Request-time admin user creation with password `changeme` in `session.py` |
| 3 | S2 | High | Global exception handler returns `str(exc)` to clients |
| 4 | S3 | High | Admin endpoints (`v2/admin.py`, `app_api/admin.py`) have no auth checks |
| 5 | A1 | High | `v2/series.py` (1,523 LOC) and browse `+page.svelte` (1,686 LOC) are unmaintainable god files |
| 6 | A2 | High | Four overlapping API namespaces with app_api→v2 bridge drift risk |
| 7 | T1 | Medium | 42% test coverage; core services (`scan_service`, `reading_service`, `cover_service`) largely untested |
| 8 | D2 | Medium | Orphan routers `covers.py`, `v2/covers.py` never mounted |
| 9 | DOC1 | Medium | Docs claim TanStack Query and per-library DBs — both incorrect |
| 10 | DEP1 | Low | `redis` and `alembic` in requirements.txt with zero usage in `src/` |

---

## Delta from March 2025 Audit

### Fixed since March 2025

| Item | Evidence |
|------|----------|
| 1.3 Scheduler thread-unsafe singleton | `threading.Lock` in `ScanScheduler.__new__` and `_scheduler_lock` |
| 3.1 Library response dict built 4× | `_build_library_response_dict()` in `library_service.py` |
| 1.4 Scan progress locks | Per-library locks in `v2/libraries.py` (`_progress_lock`, `_active_scans_lock`) |

### Still open from March 2025

| Item | Status |
|------|--------|
| 1.1 Duplicate `src/scanners/` | 6 duplicate files remain |
| 1.2 Request-time admin `changeme` | Still in `session.py` L246–255 |
| Dead cover routers | `covers.py`, `v2/covers.py` unmounted |
| Duplicate cover migrations | Both migration scripts still present |
| God files, N+1 queries, fat Comic model | Unchanged |
| Most potential bugs (BUG-01 through BUG-15) | Not re-verified; assume open until tested |
| Test coverage gaps | Still ~42% overall |

### New findings (June 2025)

| ID | Finding |
|----|---------|
| CI1 | No CI pipeline existed; added `.github/workflows/ci.yml` |
| CI2 | No lint config existed; added `pyproject.toml` |
| B1 | `scripts/scan_library.py` imports non-existent `sync_db_to_config` |
| T2 | 11 pre-existing test failures in v2/integration suite |
| DOC2 | `webui/src/lib/stores/user.js` has zero imports — dead store |
| DEP2 | 2,320 ruff F401/F841/F821 findings (mostly scanner plugins) |

---

## Findings Table

| ID | Sev | Area | Location | Description | Fix | Effort |
|----|-----|------|----------|-------------|-----|--------|
| D1 | Critical | Dead code | `src/scanners/*.py` (6 files) | Full duplicate of `metadata_providers/`; only `__init__.py` re-exports | Delete duplicates | S |
| S1 | Critical | Security | `session.py` L246–255 | Creates admin+`changeme` at request time | Remove; rely on `init_db()` only | S |
| S2 | High | Security | `main.py` L224–231 | Global handler leaks exception strings | Generic client message; log server-side | S |
| S3 | High | Security | `v2/admin.py`, `app_api/admin.py` | Reindex/migrate with no auth | Add session check | M |
| S4 | High | Security | `config.py` defaults | `cors_origins: ["*"]` + credentials | Document LAN-only; tighten for exposure | S |
| A1 | High | Architecture | `v2/series.py`, browse page | 1,523 / 1,686 LOC god files | Extract services + components | L |
| A2 | High | Architecture | 4 API namespaces | `/library`, `/v2`, `/api`, `/api/v2` overlap | Consolidation design (Tier 3) | L |
| A3 | Medium | Architecture | `app_api/*` bridges | Direct v2 function imports — drift risk | Shared service layer | L |
| A4 | Medium | Architecture | Dual fetch paths | SSR uses `API_BASE_URL`; client uses proxy | Document; unify error handling | M |
| D2 | Medium | Dead code | `covers.py`, `v2/covers.py` | Defined but never mounted | Delete | S |
| D3 | Medium | Dead code | `webui/stores/user.js` | Zero imports | Delete or wire up | S |
| D4 | Medium | Dead code | `requirements.txt` | redis, alembic unused | Remove from deps | S |
| B1 | Medium | Bug | `scripts/scan_library.py` L408 | `sync_db_to_config` does not exist | Remove dead sync block | S |
| B2 | Medium | Bug | `config.py` L121–138 | `get_setting() or True` inverts falsy | Use `is not None` check | S |
| B3 | Medium | Bug | `progress.py` L34 | Off-by-one reading completion | Fix comparison | S |
| C1 | Medium | Duplication | Archive loaders | Case-insensitive lookup in zip/rar/sevenzip | Extract to `base.py` | S |
| C2 | Medium | Duplication | Cover migrations | Two scripts add same columns | Keep one; deprecate other | S |
| C3 | Medium | Duplication | `covers.py` error handling | 3× identical try/except (if kept) | Decorator | S |
| E1 | Medium | Errors | `legacy_v1.py`, `v2/search.py`, `v2/series.py` | Bare `except:` clauses | Typed exceptions + logging | M |
| E2 | Medium | Errors | `v2/libraries.py` L191 | Scan status failure swallowed | Log warning | S |
| E3 | Medium | Errors | `comic_processor.py` L252 | `except Exception: pass` | Log at debug | S |
| M1 | Medium | Migrations | 3 parallel strategies | `create_all`, inline PRAGMA, standalone scripts | Unified runner (Tier 3) | L |
| M2 | Low | Migrations | Duplicate cover scripts | `add_cover_source_columns` vs `_fields` | Consolidate | S |
| T1 | Medium | Tests | Services layer | scan/reading/cover/search at 11–29% cov | Add unit tests | L |
| T2 | Medium | Tests | v2 integration | 11 failing tests in baseline run | Investigate fixtures/API drift | M |
| T3 | Low | Tests | Weak assertions | `status in [200, 404, 500]` | Assert expected status | M |
| DOC1 | Medium | Docs | ARCHITECTURE, WEBUI, DATA_FLOW | TanStack Query documented but not used | Update docs | S |
| DOC2 | Medium | Docs | DATABASE.md | Per-library DB claim | Clarify single SQLite | S |
| G1 | Low | God fn | `comic_processor.py` | `extract_metadata()` ~199 LOC | Split by source type | M |
| G2 | Low | God class | `Comic` model | 80+ columns | Split domain model (Tier 3) | L |
| ST1 | Low | State | `_shared.py` | Unbounded `series_tree_cache` | TTL/size limit | M |
| ST2 | Low | State | `_browse_helpers.py` | `apply_random_sort()` loads all IDs | Pagination/stream | M |

---

## Architecture Recommendations

### API consolidation (Tier 3 — do not implement in this pass)

1. **Target state:** Single native `/api/v1/*` namespace; keep `/library` and `/v2` as thin compatibility shims.
2. **Move logic from routers to services:** Especially `v2/series.py` browse/cache/random-sort logic → `library_service` or new `browse_service`.
3. **Replace app_api bridges:** Instead of importing v2 functions, both namespaces call shared service functions.

### Data layer

- Single SQLite DB (`data/main.db`) is correct; update docs that imply per-library DB files.
- Adopt one migration runner: either wire Alembic properly or consolidate standalone scripts + inline PRAGMA into ordered `migrations/runner.py`.

### Frontend

- Custom `APIClient` + IndexedDB (`client.js`, `persistentCache.js`) replaces TanStack Query — update architecture docs accordingly.
- Split browse page into: data loader (`+page.server.js`), grid component, filter/sort bar, series panel.

---

## Test Coverage Matrix

**Overall:** 42% (10,026 statements, 5,807 missed)

| Module group | Coverage | Test files | Gap |
|--------------|----------|------------|-----|
| API routers | ~55–80% | `tests/api/*` | Middleware, error_handling untested |
| Database operations | ~40–70% | `test_database_operations.py` | cover, favorite, folder, label, progress |
| Services | 11–81% | `test_services.py`, `test_metadata_service.py` | scan, reading, cover, search, scheduler |
| Scanner pipeline | ~20% | `tests/scanner/*` | threaded_scanner, comic_processor, loaders |
| Metadata providers | ~0% | `tests/scanners/test_mangadex*` only | manager, base, config |
| Utils | 0–58% | None dedicated | hashing, series_utils |
| Migrations | 0% | None | All scripts |
| Web UI | N/A | None | No frontend tests |

**Baseline test run:** 258 passed, 11 failed (pre-existing; mostly v2 library/folder/reading tests).

---

## Remediation Roadmap

### Tier 1 — Fix immediately (Phase 5)

| ID | Action | Status |
|----|--------|--------|
| D1 | Delete `src/scanners/` duplicate files (keep `__init__.py`) | **Done** |
| S1 | Remove request-time admin creation in `session.py` | **Done** |
| S2 | Sanitize global exception handler in `main.py` | **Done** |
| B1 | Remove broken `sync_db_to_config` call in `scan_library.py` | **Done** |
| D2 | Delete orphan `covers.py` and `v2/covers.py` | **Done** |
| D4 | Remove unused `redis`, `alembic` from requirements | **Done** |
| CI1 | Add `pyproject.toml` + GitHub Actions CI | **Done** |
| T4 | Test fixture uses `init_db()` for default admin | **Done** |

### Tier 2 — Next sprint

| ID | Action | Status |
|----|--------|--------|
| C1 | Extract shared archive loader filename helper | **Done** |
| C2 | Consolidate duplicate cover migrations | **Done** — removed `add_cover_source_fields.py` |
| S3 | Add auth guard to admin routes | **Done** — `require_admin_user()` |
| B2 | Fix `get_setting() or True` bug | **Done** (already fixed via `_flag()` helper) |
| E1 | Replace bare `except:` clauses | **Done** |
| E2/E3 | Scan status + config load logging | **Done** |
| T2 | Fix 11 failing v2 tests | **Done** — 269 passing |
| DOC1/DOC2 | Update TanStack Query + single DB docs | **Done** |
| D3 | Delete unused `user.js` store | **Done** |

### Tier 3 — Structural (multi-PR)

| ID | Action | Status |
|----|--------|--------|
| M1 | Unified migration runner | **Done** — `migrations/runner.py` + `inline_schema.py` |
| A1 | Extract browse logic from `v2/series.py` | **Partial** — helpers moved to `browse_service.py` (~100 LOC) |
| T1 | Service-layer tests | **Partial** — `test_reading_service.py`, `test_browse_service.py` |
| T3 | Tighten weak assertions | **Partial** — progress/search endpoints |
| A2 | API namespace consolidation | Open |
| G2 | Split fat `Comic` model | Open |
| A1b | Split browse `+page.svelte` | Open |

---

## Review Methodology Used

1. Diffed March 2025 audit items against current code
2. Added `pyproject.toml` and `.github/workflows/ci.yml`
3. Ran ruff (F401/F841/F821), vulture, radon, pytest-cov, svelte-check
4. Built route inventory (139 decorated routes)
5. Manual review: security, dead code, doc drift, scanner pipeline, frontend stores
6. Produced this report and Tier 1 fix list

See `docs/review/` for raw scan outputs.
