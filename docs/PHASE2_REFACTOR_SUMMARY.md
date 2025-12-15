# Phase 2 Refactor: Scanner Directory Consolidation

## Summary

This document describes the Phase 2 refactoring completed on the Kottlib project, 
which consolidated the confusing scanner directory structure into a clearer 
`metadata_providers` module.

## Problem

The project had three separate scanner-related directories causing confusion:

1. **`scanners/`** (root) - Provider implementations (AniList, ComicVine, etc.)
2. **`src/scanners/`** - Framework code (BaseScanner, ScannerManager, schemas)
3. **`src/scanner/`** - Core scanning engine (ThreadedScanner, file discovery)

This structure was confusing because:
- Two similarly named directories (`scanners` vs `scanner`)
- Unclear separation of concerns
- Provider implementations outside the `src/` tree

## Solution

### New Structure

```
src/metadata_providers/          # NEW: Clear name for metadata provider framework
├── __init__.py                 # Exports all public APIs
├── base.py                     # Base classes (BaseScanner, ScanResult, etc.)
├── manager.py                  # ScannerManager for registration/discovery
├── schema.py                   # Metadata field definitions
├── config.py                   # Configuration schemas
├── demo.py                     # Demo/example code
├── utils.py                    # Shared utilities
└── providers/                  # Provider implementations
    ├── __init__.py
    ├── anilist/
    │   ├── anilist_scanner.py
    │   ├── config.json
    │   └── requirements.txt
    ├── comicvine/
    │   ├── comic_vine_scanner.py
    │   └── requirements.txt
    ├── mangadex/
    │   ├── mangadex_scanner.py
    │   └── requirements.txt
    ├── metron/
    │   ├── metron_scanner.py
    │   └── requirements.txt
    └── nhentai/
        ├── nhentai_scanner.py
        └── requirements.txt

src/scanner/                    # Core scanning engine (unchanged)
├── threaded_scanner.py
├── file_discovery.py
├── structure_classifier.py
└── ...
```

### File Renames

For clarity and consistency:
- `base_scanner.py` → `base.py`
- `scanner_manager.py` → `manager.py`
- `metadata_schema.py` → `schema.py`
- `config_schema.py` → `config.py`
- `demo_scanners.py` → `demo.py`

## Changes Made

### 1. Created New Module Structure

- Created `src/metadata_providers/` directory
- Copied and renamed files from `src/scanners/`
- Updated internal imports within copied files
- Created comprehensive `__init__.py` with proper exports

### 2. Moved Provider Implementations

- Moved all providers from `scanners/` to `src/metadata_providers/providers/`
- Updated imports in all provider files to use new paths
- Cleaned up duplicate nested directories created during copy

### 3. Updated All References

Updated imports in:
- **API routers**: `src/api/routers/scanners/`
- **Services**: `src/services/metadata_service.py`
- **Scripts**: `scripts/scan_library.py`
- **Tests**: `tests/scanners/test_mangadex_scanner.py`

### 4. Backward Compatibility

- Kept `src/scanners/` directory with re-exports
- Added deprecation warning when importing from old location
- Allows smooth migration without breaking existing code

### 5. Documentation

- Added README files in deprecated directories
- Updated this summary document
- Maintained references in `docs/REFACTOR_PLAN.md`

## Migration Guide

### For Library Users

Update imports:
```python
# OLD
from src.scanners import BaseScanner, ScannerManager, init_default_scanners
from src.scanners.metadata_schema import get_scanner_capabilities

# NEW
from src.metadata_providers import BaseScanner, ScannerManager, init_default_scanners
from src.metadata_providers.schema import get_scanner_capabilities
```

### For Scanner Plugin Developers

Update imports in your scanner files:
```python
# OLD
from src.scanners.base_scanner import BaseScanner, ScanResult, ScanLevel
from src.scanners.config_schema import ConfigOption, ConfigType

# NEW
from src.metadata_providers.base import BaseScanner, ScanResult, ScanLevel
from src.metadata_providers.config import ConfigOption, ConfigType
```

Move your scanner to:
```
src/metadata_providers/providers/your_scanner/
```

## Validation

### Tests Pass

Ran test suite with 28/29 tests passing:
- All scanner initialization tests pass
- All metadata extraction tests pass
- Scanner discovery works correctly
- One pre-existing test failure (unrelated to refactor)

### Scanner Discovery Works

Scanner manager successfully discovers 5 providers:
- AniList
- Comic Vine  
- MangaDex
- Metron
- nhentai

### Backward Compatibility Verified

Old imports still work with deprecation warnings:
```python
from src.scanners import BaseScanner  # Works, shows DeprecationWarning
```

## Benefits

1. **Clearer naming**: `metadata_providers` clearly indicates purpose
2. **Better organization**: All providers together under `providers/`
3. **Consistent structure**: Everything under `src/` tree
4. **Improved discoverability**: Clear hierarchy for developers
5. **Backward compatible**: Existing code continues to work

## Future Work

After one major version release:
- Remove old `scanners/` root directory
- Remove `src/scanners/` re-export layer
- Update all remaining old imports
- Clean up deprecation warnings

## Related Documentation

- `docs/REFACTOR_PLAN.md` - Complete refactoring plan
- `src/metadata_providers/README.md` - Module documentation
- `src/scanners/README.md` - Deprecation notice
- `scanners/README.md` - Deprecation notice
