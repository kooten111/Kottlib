# Code Refactoring Checklist

**Status**: Planning Phase
**Last Updated**: 2025-11-27
**Priority**: High items should be addressed first

> **Note**: API response formats (v1 text format, v2 mixed formats) are intentional for YACReader mobile app compatibility and should NOT be changed.

---

## 🔴 High Priority

### Dead Code Removal

- [ ] **Remove deprecated database functions**
  - [ ] Remove `get_library_database()` at `src/database/database.py:312-319`
  - [ ] Remove `get_library_db_path()` at `src/database/database.py:132-138`
  - [ ] Update any callers to use current functions
  - [ ] Add migration notes if breaking changes

- [ ] **Fix unreachable code in database.py**
  - [ ] Fix `get_folders_in_library()` at line 770 - has unreachable return statement
  - [ ] Review logic flow

- [ ] **Clean up TODO comments**
  - [ ] Review TODOs in `src/api/main.py:174-185`
  - [ ] Remove if features already exist in v2
  - [ ] Convert to GitHub issues if still needed

### Code Duplication (Critical)

- [ ] **Consolidate user retrieval pattern (10+ duplicates)**
  - [ ] Create helper function `get_request_user(request, session)` in shared utility module
  - [ ] Replace pattern in `src/api/routers/legacy_v1.py` (6 locations)
  - [ ] Replace pattern in `src/api/routers/v2/comics.py` (3 locations)
  - [ ] Add tests for new helper function
  - **Files affected:**
    - `src/api/routers/legacy_v1.py:280-284, 348-354, 423-429, 509-515, 795-806, 844-850`
    - `src/api/routers/v2/comics.py:68-73, 247-251, 556-560`

- [ ] **Create magic string constants**
  - [ ] Create `src/constants.py` or add to existing constants file
  - [ ] Define: `DEFAULT_USER = "admin"` (used 10+ times)
  - [ ] Define: `ROOT_FOLDER_MARKER = "__ROOT__"`
  - [ ] Define: `DEFAULT_CONFIDENCE_THRESHOLD = 0.4`
  - [ ] Define: `FALLBACK_CONFIDENCE_THRESHOLD = 0.7`
  - [ ] Define: `CACHE_DURATION_SECONDS = 86400`
  - [ ] Define: `DEFAULT_WORKER_COUNT = 4`
  - [ ] Replace all hardcoded instances throughout codebase

- [ ] **Fix global state in scan progress tracking**
  - [ ] Review `_scan_progress` dict in `src/api/routers/scanners.py:39`
  - [ ] Move to database-backed solution OR document single-process limitation
  - [ ] Add warning if multi-process deployment detected

### Error Handling Standardization

- [ ] **Standardize file operation error handling**
  - [ ] Review cover file access in API routers - add try/catch
  - [ ] Review comic archive opening - ensure consistent error handling
  - [ ] Create error handling patterns/decorators for common operations

- [ ] **Review silent failures**
  - [ ] Review `_rebuild_series_table()` error handling in `src/scanner/threaded_scanner.py:273-275`
  - [ ] Determine if silent continuation is appropriate
  - [ ] Add better logging/metrics if failures should be tracked

---

## 🟡 Medium Priority

### Refactoring for Maintainability

- [ ] **Extract cover path resolution utility (4+ duplicates)**
  - [ ] Create `get_cover_file_path()` utility function
  - [ ] Replace duplicated logic in `src/api/routers/legacy_v1.py:596-624`
  - [ ] Replace duplicated logic in `src/api/routers/v2/comics.py:634-681`

- [ ] **Consolidate progress bar implementations**
  - [ ] Review progress bar logic in `scripts/scan_library.py:47-84, 149-160`
  - [ ] Extract common progress display logic
  - [ ] Create reusable progress reporter class/function

- [ ] **Break down long functions**
  - [ ] Refactor `search_comics()` in `src/database/database.py:560-680` (120 lines)
    - [ ] Extract relevance scoring logic
    - [ ] Extract series metadata matching
  - [ ] Refactor `_build_series_tree_cache()` in `src/scanner/threaded_scanner.py:878-1020` (140+ lines)
    - [ ] Extract tree node building logic
    - [ ] Simplify nested conditionals
  - [ ] Refactor `get_folder_content()` in `src/api/routers/legacy_v1.py:176-314` (138 lines)
    - [ ] Extract folder filtering logic
    - [ ] Extract comic sorting logic
  - [ ] Refactor `get_folder_info()` in `src/api/routers/legacy_v1.py:112-173` (61 lines)
    - [ ] Simplify recursive traversal

- [ ] **Standardize import patterns**
  - [ ] Audit all files for import style
  - [ ] Choose: relative (`from ...database`) OR absolute (`from src.database`)
  - [ ] Update all imports to use consistent pattern
  - [ ] Document decision in CONTRIBUTING.md

- [ ] **Create service layer for business logic**
  - [ ] Identify business logic currently in API routes
  - [ ] Create service modules (e.g., `src/services/comic_service.py`)
  - [ ] Move logic from routes to services
  - [ ] Update routes to call services

### Code Quality Improvements

- [ ] **Improve metadata extraction logic**
  - [ ] Review `_extract_metadata()` in `src/scanner/threaded_scanner.py:592-772`
  - [ ] Consider using field mapping dict instead of if chains
  - [ ] Add documentation for field mappings

- [ ] **Standardize database session patterns**
  - [ ] Audit session.commit() usage - some explicit, some implicit
  - [ ] Choose and document pattern
  - [ ] Update all database operations to match

- [ ] **Flatten nested conditionals**
  - [ ] Review `src/scanner/threaded_scanner.py:621-657`
  - [ ] Use early returns to reduce nesting
  - [ ] Improve readability

- [ ] **Improve search relevance scoring**
  - [ ] Review complex scoring in `src/database/database.py:645-678`
  - [ ] Consider weight-based scoring system
  - [ ] Add documentation for scoring algorithm

---

## 🟢 Low Priority (Polish)

### Code Style Consistency

- [ ] **Standardize string formatting**
  - [ ] Audit all string formatting (f-strings, .format(), %)
  - [ ] Convert all to f-strings (Python 3.6+ standard)
  - [ ] Update style guide

- [ ] **Standardize logging practices**
  - [ ] Define when to use debug/info/warning/error
  - [ ] Standardize exception logging (when to use `exc_info=True`)
  - [ ] Update logging calls throughout codebase
  - [ ] Document in CONTRIBUTING.md

- [ ] **Standardize boolean comparisons**
  - [ ] Choose: `if var:` OR `if var is not None:`
  - [ ] Document when each is appropriate
  - [ ] Update inconsistent usages

- [ ] **Add missing type hints**
  - [ ] Add type hints to `scripts/scan_library.py` functions
  - [ ] Add type hints to `src/scanner/comic_loader.py` helpers
  - [ ] Run mypy to verify type coverage

### Anti-pattern Fixes

- [ ] **Replace string-based exception checking**
  - [ ] Review `src/database/database.py:242`
  - [ ] Replace `if "UNIQUE constraint failed" in str(e)` with specific exception types
  - [ ] Use SQLAlchemy exception hierarchy

- [ ] **Review hardcoded paths**
  - [ ] Audit hardcoded paths: `log_dir = Path('logs')`, etc.
  - [ ] Ensure all paths use configuration system
  - [ ] Document path configuration

### Documentation

- [ ] **Document complex algorithms**
  - [ ] Add docstring for relevance scoring algorithm
  - [ ] Add docstring for series detection logic
  - [ ] Add docstring for tree building algorithm

- [ ] **Module separation documentation**
  - [ ] Document responsibilities of `scripts/scan_library.py`
  - [ ] Consider splitting into separate concerns
  - [ ] Update architecture documentation

---

## 📊 Metrics Tracking

**Codebase Stats:**
- Total Python Files: 47
- Lines of Code: ~19,000
- Functions >100 lines: 8+
- Dead code instances: 5+
- Major duplication patterns: 3

**Progress:**
- High Priority: 0/14 completed
- Medium Priority: 0/18 completed
- Low Priority: 0/11 completed
- **Overall: 0/43 completed (0%)**

---

## Notes

### Intentional Design Decisions (DO NOT CHANGE)

These patterns are intentional for YACReader mobile app compatibility:

- ✅ **v1 API text format** with CRLF line endings (`format_v1_response()`)
- ✅ **v2 API mixed formats** (JSON for metadata, text for comic operations)
- ✅ **Response format inconsistencies** between v1/v2 (compatibility requirement)
- ✅ **Custom delimited formats** for folder info and comic info

### Testing Strategy

For each refactoring task:
1. Ensure existing tests pass before changes
2. Add tests for new helper functions/utilities
3. Verify YACReader mobile app compatibility for API changes
4. Run integration tests with actual comic files
5. Test scanner functionality end-to-end

### Review Process

- Each HIGH priority item should be reviewed in a separate PR
- MEDIUM priority items can be batched by related functionality
- LOW priority items can be combined into style/polish PRs
