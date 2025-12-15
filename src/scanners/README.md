# DEPRECATED: src/scanners Module

**This module has been renamed to `src.metadata_providers` for clarity.**

## Migration Guide

Update your imports:
```python
# OLD (deprecated, shows warning)
from src.scanners import BaseScanner, ScannerManager

# NEW
from src.metadata_providers import BaseScanner, ScannerManager
```

## Backward Compatibility

This module currently re-exports everything from `src.metadata_providers` 
with a deprecation warning. The re-exports will be maintained for one more 
major version to allow smooth migration.

## What Changed

- `src/scanners/` → `src/metadata_providers/`
- `scanners/` (root) → `src/metadata_providers/providers/`
- File renames for clarity:
  - `base_scanner.py` → `base.py`
  - `scanner_manager.py` → `manager.py`
  - `metadata_schema.py` → `schema.py`
  - `config_schema.py` → `config.py`

See `docs/REFACTOR_PLAN.md` for the complete refactoring plan.
