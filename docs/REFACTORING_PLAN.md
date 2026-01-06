# Kottlib Refactoring Plan

**Repository:** kooten111/Kottlib  
**Created:** 2026-01-06  
**Status:** Planning Phase

---

## Table of Contents

1. [YACReader Reference Cleanup](#1-yacreader-reference-cleanup)
2. [Dead & Legacy Code Removal](#2-dead--legacy-code-removal)
3. [File Size Reduction / Modularization](#3-file-size-reduction--modularization)
4. [Utility Consolidation & Deduplication](#4-utility-consolidation--deduplication)
5. [Inconsistent Coding Style Fixes](#5-inconsistent-coding-style-fixes)
6. [Duplicate Frontend Logic](#6-duplicate-frontend-logic)
7. [Standardized Error Handling & Logging](#7-standardized-error-handling--logging)
8. [Large Function Decomposition](#8-large-function-decomposition)

---

## 1. YACReader Reference Cleanup

All references to "YACReader" and ".yacreaderlibrary" MUST be removed or renamed to "Kottlib". This is a high priority for consistent branding and to avoid confusion.

> [!IMPORTANT]
> The user has explicitly requested that **any specific reference to yacreader library needs to be removed**. This includes hidden directories, function names, and comments.

### Code Changes Required

| File | Location | Current | Proposed |
|------|----------|---------|----------|
| `src/scanner/thumbnail_generator.py` | Line 8 | `Stores thumbnails in . yacreaderlibrary/covers/` | `Stores thumbnails in covers/ directory` |
| `src/scanner/thumbnail_generator.py` | Line 28 | `calculate_yacreader_hash()` | `calculate_comic_hash()` |
| `src/scanner/thumbnail_generator. py` | Line 30 | `Calculate hash exactly as YACReader expects` | `Calculate hash for comic identification (YACReader protocol compatible)` |
| `src/scanner/thumbnail_generator.py` | Line 35 | `This MUST match YACReader's algorithm... ` | `This MUST match the protocol algorithm... ` |
| `src/scanner/comic_processor.py` | Line 20 | `calculate_yacreader_hash` | `calculate_comic_hash` (after renaming) |
| `src/client/kottlib. py` | Line 91 | `Client for YACReaderLibrary Server` | `Client for Kottlib Server` |
| `webui/src/lib/components/layout/Footer.svelte` | Line 15-21 | Link to YACReader GitHub | Consider removing or updating |
| `src/database/README.md` | Line 164-184 | `import_yacreader. py` references | Update tool name if renaming |
| `src/database/README.md` | Various | `~/.local/share/yaclib/` paths | Renaming to `kottlib` |
| **Global Search** | **All files** | `.yacreaderlibrary` | Rename to `.kottlib` or remove entirely if redundant |
| **Global Search** | **All files** | `YACReaderLibrary` | Rename to `KottlibLibrary` or `Kottlib` |

### Documentation Updates

| File | Action |
|------|--------|
| `docs/YACREADER_COMPATIBILITY_ANALYSIS.md` | **Keep** - This is protocol documentation, YACReader references are appropriate |
| `docs/API.md` | Review and clarify where "YACReader" refers to protocol vs.  implementation |
| `README.md` | Update acknowledgments section wording; keep YACReader credit but clarify |

---

## 2. Dead & Legacy Code Removal

### Legacy Configuration Classes

**File:** `src/config.py`

| Class | Status | Action |
|-------|--------|--------|
| `StorageConfig` | Marked "LEGACY - now in database" | Remove if migration complete |
| `FeaturesConfig` | Marked "kept for backward compatibility" | Remove if migration complete |
| `LibraryDefinition` | Marked legacy | Remove if database-driven |

**Associated code to remove:**
- Migration logic in `load_config()` (lines 180-188) that handles these legacy sections

### Legacy Path Handling

**File:** `src/database/paths.py`

| Function/Logic | Status | Action |
|----------------|--------|--------|
| `get_covers_dir()` - fallback for `library_name=None` | Marked "shared/legacy" | Remove if fully migrated to library-specific dirs |

### Stale Comments/References

| File | Issue | Action |
|------|-------|--------|
| `src/database/models. py` | References to removed fields like `normalized_series_name` | Clean up comments |

### Potentially Redundant Scripts

| File | Issue | Action |
|------|-------|--------|
| `scripts/regenerate_covers.py` | Manually implements cover logic that overlaps with `thumbnail_generator.py` | Refactor to use centralized functions |

---

## 3. File Size Reduction / Modularization

### Large Files to Split

#### `src/database/models.py` (~600 lines)

**Current:** All SQLAlchemy models in one file

**Proposed structure:**
```
src/database/models/
├── __init__.py       # Re-exports all models
├── base. py           # Base class, common mixins
├── library.py        # Library model
├── comic.py          # Comic, ComicInfo models
├── user.py           # User model
├── reading. py        # ReadingProgress, ReadingStats
├── series.py         # Series-related models
├── collection.py     # Collections, ReadingLists
└── session.py        # Sessions model
```

---

#### `src/scanner/comic_loader.py` (~800 lines)

**Current:** Contains `ComicInfo` dataclass + all archive format implementations

**Proposed structure:**
```
src/scanner/
├── comic_loader.py   # Keep:  open_comic() factory, ComicInfo dataclass
└── loaders/
    ├── __init__.py   # Re-exports all loaders
    ├── base.py       # BaseArchive abstract class
    ├── zip.py        # CBZArchive implementation
    ├── rar.py        # CBRArchive implementation
    ├── sevenzip.py   # CB7Archive, SevenZipCliArchive
    └── utils.py      # Shared utilities (natsort, etc.)
```

**Alternative:** Move `ComicInfo` to `src/scanner/schema.py` to separate data model from I/O logic. 

---

#### `src/database/operations/comic. py` (growing large)

**Suggested internal organization:**
- Move complex query builders (`search_comics`, `get_comics_in_folder_simple`) to `src/database/operations/queries. py`
- Keep simple CRUD (create, update, delete) in `comic.py`

---

#### Metadata Provider Modularization

**Current:** Scanners in `src/metadata_providers/providers/` (e.g., `nhentai_scanner.py`, `anilist_scanner.py`) are monolithic files (~1000+ lines) containing API clients, HTML scrapers, and scanner logic.

**Proposed structure for each provider:**
```
src/metadata_providers/providers/[name]/
├── __init__.py
├── scanner.py        # The Core Scanner class
├── api_client.py     # API communication logic
├── scraper.py        # HTML parsing/scraping logic
└── schema.py         # Provider-specific data models
```

---

#### API Router Complexity Reduction

**Target:** `src/api/routers/v2/series.py`, `src/api/routers/v2/comics.py`

**Issue:** These files contain complex business logic (e.g., recursive folder counting, metadata extraction formatting) directly inside route handlers.

**Proposed Action:**
- Move complex query builders to `src/database/operations/`
- Move business logic to specific Service classes (e.g., `BrowsingService`, `MetadataService`)

---

### Inconsistent Path Handling

**Issue:** The scanner and thumbnail generator often refer to `.yacreaderlibrary/covers/`, while other parts of the system use library-specific configuration or default to a `covers/` directory in the project root.

**Proposed Action:**
- Standardize on a single, configurable `covers_dir` per library.
- Remove all hardcoded references to `.yacreaderlibrary`.

---

### Metadata vs Folder Structure Consistency

**Issue:** Some API endpoints group comics by metadata (Series/Volume), while the primary browsing interface is folder-based. This leads to inconsistencies where a "Series" in the UI might not match the folder structure.

**Proposed Action:**
- Standardize all "Series" views to be folder-based by default.
- Use metadata as an optional overlay/filter rather than the primary structural element.

---

## 4. Utility Consolidation & Deduplication

### Create New Utility Modules

#### `src/utils/hashing.py`

**Consolidate from:**
- `src/scanner/thumbnail_generator.py` → `calculate_yacreader_hash()` (rename to `calculate_comic_hash`)
- `src/services/library_cache.py` → MD5 cache key generation

```python
# src/utils/hashing.py
"""Centralized hashing utilities for Kottlib"""

def calculate_comic_hash(file_path: Path) -> str:
    """
    Calculate hash for comic file identification.
    
    Protocol:  SHA1(first 512KB) + file_size_as_string
    """
    ... 

def calculate_cache_key(data: str) -> str:
    """Calculate MD5 hash for cache keys."""
    ...
```

---

#### `src/utils/platform.py`

**Consolidate from:**
- `src/config.py` → Manual `platform. system()` checks for config directories
- `src/database/paths.py` → Project root detection, platform-specific data directories

```python
# src/utils/platform.py
"""Platform-specific path and configuration utilities"""

def get_config_dir() -> Path:
    """Get platform-appropriate config directory."""
    ...

def get_data_dir() -> Path:
    """Get platform-appropriate data directory."""
    ... 

def get_project_root() -> Path:
    """Find project root by walking up looking for markers."""
    ...
```

---

#### `src/utils/serialization.py`

**Move from:** `src/api/routers/config.py` → `dataclass_to_dict()` helper

```python
# src/utils/serialization.py
"""Serialization helpers for dataclasses and Pydantic models"""

def dataclass_to_dict(obj) -> dict:
    """Recursively convert dataclass to dictionary."""
    ...
```

---

#### `src/utils/pagination.py`

**Consolidate from:** `series.py`, `search.py`, `comics.py`

**Proposed Action:**
- Standardize pagination parameter handling (`limit`, `offset`).
- Create a helper for injecting pagination headers into the response.

---

#### `src/utils/errors.py`

**Proposed Action:**
- Centralize mapping of custom exceptions to FastAPI `HTTPException` codes.
- Standardize error response bodies.
```

---

### Database Operations Improvement

**File:** `src/database/operations/setting.py`

**Current (lines 34-45):**
```python
if setting.value_type == 'string':
    return setting.value
elif setting.value_type == 'int':
    return int(setting.value)
# ... etc
```

**Proposed:**
```python
TYPE_CONVERTERS = {
    'string':  str,
    'int': int,
    'float': float,
    'bool': lambda v: v.lower() in ('true', '1', 'yes'),
    'json': json.loads,
}

def get_setting(session, key: str, default=None):
    setting = session.query(Setting).filter_by(key=key).first()
    if not setting:
        return default
    converter = TYPE_CONVERTERS.get(setting.value_type, str)
    return converter(setting.value)
```

---

### Tool Check Integration

**File:** `src/scanner/tool_check.py`

**Current:** Called manually in some scripts like `scan_library.py`

**Proposed:** Integrate into `ThreadedScanner.__init__()` or `open_comic()` factory to automatically check/warn when tools are missing. 

---

## 5. Inconsistent Coding Style Fixes

### Import Statement Organization

**Issue:** Mixed import styles across files

**Examples:**
- `src/scanner/thumbnail_generator.py` imports `hashlib` at module level (line 11) **and** again inside `calculate_yacreader_hash()` (line 37) - redundant
- Some files use `from x import y`, others use `import x` for the same modules

**Standard to adopt:**
```python
# Standard library imports (alphabetically)
import hashlib
import logging
from pathlib import Path
from typing import Optional, Tuple

# Third-party imports
from PIL import Image

# Local imports
from src.database import Database
```

---

### Docstring Inconsistencies

**Issue:** Mixed docstring styles

| Style | Example Location |
|-------|-----------------|
| Google style with Args/Returns | `src/scanner/thumbnail_generator.py` |
| Simple one-liner | `scripts/kottlib-cli.py` |
| Triple-quoted module docs | `src/api/routers/__init__.py` |

**Recommendation:** Standardize on Google-style docstrings: 
```python
def function_name(param1: str, param2: int) -> bool:
    """
    Brief description of function.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises: 
        ValueError: When something is wrong
    """
```

---

### Environment Variable Override Pattern

**File:** `src/config.py` → `apply_env_overrides()`

**Current (lines 210-235):** Repetitive manual `os.getenv` checks

**Proposed:** Use a mapping or Pydantic settings: 
```python
ENV_OVERRIDES = {
    'KOTTLIB_HOST': ('server', 'host', str),
    'KOTTLIB_PORT': ('server', 'port', int),
    'KOTTLIB_LOG_LEVEL': ('server', 'log_level', str),
    # ... etc
}

def apply_env_overrides(config: Config) -> Config:
    for env_var, (section, field, converter) in ENV_OVERRIDES.items():
        value = os.getenv(env_var)
        if value:
            setattr(getattr(config, section), field, converter(value))
    return config
```

---

### Naming Conventions

| Issue | Location | Current | Suggested |
|-------|----------|---------|-----------|
| Mixed case for constants | Various | Some `UPPER_CASE`, some `lowercase` | Use `UPPER_CASE` for module-level constants |
| File naming | `src/database/paths.py` | - | Consider `src/utils/paths.py` for consistency |

---

## 6. Duplicate Frontend Logic

### Svelte Component Duplication

**Files:**
- `webui/src/lib/components/FolderCard.svelte`
- `webui/src/lib/components/SeriesCard.svelte`

**Duplicate function:** `get_gradient_colors()` - generates fallback cover backgrounds from a hash

**Solution:** Create shared utility: 
```javascript
// webui/src/lib/utils/colors.js
export function getGradientColors(hash) {
    // Implementation moved from components
}
```

Then import in both components:
```svelte
<script>
    import { getGradientColors } from '$lib/utils/colors.js';
</script>
```

---

### Large Svelte Component Modularization

Several pages have grown too complex and should be split into smaller, focused components.

| Page | Current File | Suggested Split |
|------|--------------|-----------------|
| Scanners Admin | `admin/scanners/+page.svelte` | `ScannerForm.svelte`, `ScannerResults.svelte`, `LibraryScannerPanel.svelte` |
| Settings Admin | `admin/settings/+page.svelte` | `SettingsSection.svelte`, `ConfigField.svelte` |
| Advanced Search | `AdvancedSearchModal.svelte` | `FilterGroup.svelte`, `QueryBuilder.js` |

---

## 7. Standardized Error Handling & Logging

### Consistent Logging

**Issue:** Some modules use `logging.getLogger(__name__)` while others use `print` or inconsistent logger names.

**Action:**
- Audit all modules in `src/` to ensure `logger = logging.getLogger(__name__)` is used.
- Standardize log levels (e.g., `DEBUG` for scan details, `INFO` for lifecycle events, `ERROR` for failures).

### Structured Error Responses

**Issue:** Mixed use of `HTTPException` and raw `JSONResponse` with different body formats.

**Action:**
- Use a standard error model for all API responses.
- Implement a global exception handler in FastAPI for unhandled exceptions.

## 8. Large Function Decomposition

### Giant Route Handler Functions

**Target:** `src/api/routers/v2/series.py`

The `browse_folder` function (lines 199-653, **~454 lines**) is excessively long and contains:
- Cache key generation
- Path parsing and validation  
- Comic view detection (`/_comic/ID`)
- Breadcrumb building
- Random sort implementation (duplicated in `get_series_list`)
- Standard sort implementation
- Folder item building
- Comic item building
- Response construction

**Proposed Split:**

```
src/api/routers/v2/
├── series.py           # Keep route definitions only
└── _browse_helpers.py  # New file with extracted logic
```

**Functions to extract:**

| Function | Purpose |
|----------|---------|
| `build_folder_item(folder, series_map, has_children, breadcrumbs)` | Construct folder response dict |
| `build_comic_item(comic, progress)` | Construct comic response dict |
| `parse_browse_path(path, library_id, session)` | Parse path, detect comic view, build breadcrumbs |
| `apply_random_sort(session, folder_id, library_id, offset, limit, seed)` | Encapsulate random sort logic |
| `batch_fetch_folder_metadata(folder_ids, library_id, session)` | Batch load Series records + children info |
| `batch_fetch_comic_progress(comic_ids, user_id, session)` | Batch load ReadingProgress |

---

### V1/V2 API Duplication

**Files:**
- `src/api/routers/legacy_v1.py` (960 lines)
- `src/api/routers/v2/comics.py` (712 lines)

**Issue:** Many endpoints duplicate logic between V1 (text format) and V2 (JSON format):
- `get_comic_info` vs `get_comic_fullinfo_v2`
- `get_folder_content` vs `browse_folder`
- `get_comic_page` vs `get_comic_page_v2_remote`

**Proposed:** Create shared service layer functions that both routers call:

```python
# src/services/comic_info_service.py
def get_comic_metadata(session, comic_id, user_id=None) -> dict:
    """Returns comic metadata dict used by both V1 and V2."""
    ...
```

Then:
- V1 routes call service + format to text
- V2 routes call service + return JSON

---

### Response Item Builder Patterns

**Issue:** The same item-building pattern is repeated across:
- `browse_folder()` in `series.py` (lines 449-482, 570-617)
- `get_series_list()` in `series.py` (lines 758-781, 793-817)
- `browse_all_content()` in `series.py` (similar pattern)

**Proposed:** Create `src/api/routers/v2/_item_builders.py`:

```python
def build_browse_folder_item(
    folder: FolderModel,
    series_record: Optional[Series],
    has_children: bool,
    breadcrumbs: List[dict]
) -> dict:
    """Build standardized folder item for browse responses."""
    ...

def build_browse_comic_item(
    comic: Comic,
    progress: Optional[ReadingProgress]
) -> dict:
    """Build standardized comic item for browse responses."""
    ...
```

---

### Frontend Store Persistence Patterns

**File:** `webui/src/lib/stores/preferences.js`

**Issue:** localStorage persistence is repeated in every setter method. Line pattern:
```javascript
if (browser) {
    localStorage.setItem('libraryPreferences', JSON.stringify(newPrefs));
}
return newPrefs;
```

This appears in: `set`, `update`, `setGridCoverSize`, `setFolderCoverSize`, `setViewMode`, `toggleViewMode`, `setSortBy` (7 times).

**Proposed Refactor:**

```javascript
// Helper to persist and return
function persistAndReturn(newPrefs) {
    if (browser) {
        localStorage.setItem('libraryPreferences', JSON.stringify(newPrefs));
    }
    return newPrefs;
}

// Then in setters:
setGridCoverSize: (size) => {
    update(current => persistAndReturn({ ...current, gridCoverSize: size }));
}
```

---

### Frontend Gradient Color Duplication

**Current Location:** `webui/src/lib/components/library/FolderCard.svelte` (lines 60-76)

The `getGradientColors(hash)` function generates fallback cover gradient colors from a hash. This is also referenced in the existing plan for `SeriesCard.svelte`.

**Note:** Already covered in Section 6, but confirmed `FolderCard.svelte` is the primary location.

---

## Implementation Checklist

### Phase 1: Quick Wins (Low Risk)
- [x] Rename `calculate_yacreader_hash` → `calculate_comic_hash`
- [x] Remove redundant `import hashlib` in `thumbnail_generator.py`
- [x] Create `src/utils/hashing.py` and move hash functions
- [x] Create `webui/src/lib/utils/colors.js` for shared gradient logic
- [x] Clean up stale comments in `models.py`
- [x] Add `src/utils/pagination.py` and `src/utils/errors.py` stubs
- [x] Standardize logger initialization across `src/`
- [x] **Global audit/rename of all remaining "yacreader" strings in non-protocol code**
- [x] **Rename `.yacreaderlibrary` hidden directories to `.kottlib`**

### Phase 2: Modularization (Medium Risk)
- [x] Split `src/database/models.py` into `models/` package
- [x] Split `src/scanner/comic_loader.py` into `loaders/` package
- [ ] Split largest metadata scanners (nHentai, AniList) into provider packages
- [ ] Refactor `admin/scanners/+page.svelte` into smaller components
- [x] Create `src/utils/platform.py`
- [x] **Extract `browse_folder` helper functions to `_browse_helpers.py`**
- [x] **Create `_item_builders.py` with shared folder/comic item builders**
- [x] **Create `persistAndReturn()` helper in preferences store**
- [x] **Create `src/services/comic_info_service.py` for V1/V2 shared logic**

### Phase 3: Legacy Cleanup (Higher Risk - Test Thoroughly)
- [x] Remove legacy config classes (after verifying migration complete)
- [x] Remove legacy path fallbacks in `get_covers_dir()`
- [x] Refactor `scripts/regenerate_covers.py` to use centralized functions
- [x] Move complex logic from `series.py` and `comics.py` routers to `src/services/`
- [x] Standardize on library-specific `covers_dir` and remove fallback path logic
- [x] Update environment variable override pattern

### Phase 4: Documentation
- [x] Update docstrings to consistent Google style
- [x] Update README and docs with new module locations
- [x] Keep YACReader references in protocol documentation only

---

## Notes

- **Search Results Limitation:** The code searches performed may not have captured all instances.  View more results in GitHub: 
  - [Search for "yacreader" in repo](https://github.com/search?q=repo%3Akooten111%2FKottlib+yacreader&type=code)
  - [Search for ". yacreaderlibrary" in repo](https://github.com/search?q=repo%3Akooten111%2FKottlib+.yacreaderlibrary&type=code)
  
- **Testing:** Each refactoring should include running the existing test suite (`./run_tests.sh`)

- **Backward Compatibility:** Some YACReader references (like the hash algorithm) are required for protocol compatibility - these should be kept but documented as "protocol requirement"