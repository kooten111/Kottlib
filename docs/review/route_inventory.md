# API Route Inventory

**Date:** 2025-06-28  
**Total decorated routes:** 139 across `src/api/routers/`

## Namespace summary

| Namespace | Prefix | Router entry | Auth pattern | Notes |
|-----------|--------|--------------|--------------|-------|
| Legacy v1 | `/library` | `legacy_v1.py` | Session cookie; `get_request_user` fallback | Plain-text YACReader |
| YACReader v2 | `/v2` | `v2/__init__.py` | Session cookie; admin fallback | JSON compatibility |
| App API | `/api` | `app_api/__init__.py` | Mostly delegates to v2 | WebUI native |
| Libraries v1 | `/api/v1/libraries` | `libraries.py` | Minimal | Internal CRUD |
| User interactions | `/api/v2` | `user_interactions.py` | `get_request_user` | Favorites, labels |
| Config | `/api/v2` + `/api` | `config.py` | None | Bootstrap + DB settings |
| Scanners | `/api/scanners` | `scanners/router.py` | None | Metadata plugins |
| Top-level | `/`, `/health`, `/sync`, `/recoverSession` | `main.py` | Mixed | Legacy shortcuts |

## Unmounted / orphan modules

| File | Routes defined | Mounted in main.py? | Status |
|------|----------------|---------------------|--------|
| `src/api/routers/covers.py` | 4 | No | **Dead** — cover serving lives in `v2/comics.py` |
| `src/api/routers/v2/covers.py` | 2 | No | **Dead** — MangaDex cover endpoints unused |
| `src/api/routers/v2/tree.py` | 2 | No (not in v2 `__init__.py`) | Used via `app_api/libraries.py` imports |
| `src/api/routers/v2/series.py` | 4 | No (not in v2 `__init__.py`) | Used via `app_api/libraries.py` imports |
| `src/api/routers/v2/admin.py` | 4 | No | Used via `app_api/admin.py` |

## app_api → v2 bridge pattern

`app_api/` routers import and call v2 module functions directly (not HTTP proxy). Highest drift risk:

- `app_api/libraries.py` → `v2/libraries.py`, `v2/series.py`, `v2/folders.py`, `v2/tree.py`
- `app_api/comics.py` → `v2/comics.py`
- `app_api/collections.py` → `v2/collections.py` helper functions
- `app_api/admin.py` → `v2/admin.py`

## Documentation drift (verified)

| Doc claim | Reality |
|-----------|---------|
| TanStack Query in ARCHITECTURE.md, WEBUI.md, DATA_FLOW.md | **Wrong** — not in `webui/package.json`; uses custom `APIClient` + IndexedDB cache |
| Per-library SQLite DB in some docs | **Wrong** — single `data/main.db` with `library_id` FK |
| `v2/admin.py` in v2 router list | **Partial** — mounted via `app_api/admin`, not `v2/__init__.py` |

## Layering — fat routers (>500 LOC)

| File | LOC | Responsibilities |
|------|-----|------------------|
| `v2/series.py` | 1523 | Browse, cache, random sort, metadata overlay, progress |
| `legacy_v1.py` | 983 | Full v1 compatibility surface |
| `v2/comics.py` | 872 | Pages, covers, progress, metadata |
| `v2/collections.py` | 762 | Favorites, tags, reading lists |
| `v2/folders.py` | 583 | Folder browsing, stats |
| `v2/search.py` | 568 | Search + facets |
| `v2/libraries.py` | 566 | Library CRUD, scan progress |

Services layer is thinner; most business logic for browse/series remains in routers.
