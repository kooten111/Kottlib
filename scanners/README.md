# DEPRECATED: Scanner Implementations Moved

**This directory is deprecated and will be removed in a future release.**

Scanner implementations have been moved to:
```
src/metadata_providers/providers/
```

## Migration Guide

If you were importing from the old location:
```python
# OLD (deprecated)
from scanners.mangadex.mangadex_scanner import MangaDexScanner

# NEW
from src.metadata_providers.providers.mangadex.mangadex_scanner import MangaDexScanner
```

Or use the scanner manager for dynamic discovery:
```python
from src.metadata_providers import init_default_scanners

manager = init_default_scanners()
scanner = manager.get_scanner('MangaDex')
```

## Backward Compatibility

The old `src/scanners` module provides backward compatibility by re-exporting 
from `src.metadata_providers`. A deprecation warning will be shown when using 
the old imports.

See `docs/REFACTOR_PLAN.md` for more details on the refactoring.
