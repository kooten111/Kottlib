# Review Baseline Snapshot

**Date:** 2025-06-28  
**Git SHA:** `73766a696b9789e6783e31cb2001b900c8a9733a`  
**Source files:** 263 (py/js/svelte in src, tests, scanners, scripts, webui/src)  
**Total source LOC:** ~53,239 (py/svelte/js in src + webui/src)  
**Tests collected:** 269 (258 passed, 11 failed in baseline run)

## March 2025 Audit Delta (quick triage)

| Item | Status |
|------|--------|
| 1.1 Duplicate `src/scanners/` | **OPEN** — 6 duplicate files remain |
| 1.2 Request-time admin `changeme` | **OPEN** — `session.py` still auto-creates |
| 1.3 Scheduler thread-unsafe singleton | **FIXED** — `threading.Lock` in `scheduler.py` |
| 1.4 Scan progress module state | **PARTIAL** — locks added per library_id |
| 3.1 Library response dict 4× | **FIXED** — `_build_library_response_dict()` |
| Redis/Alembic in requirements | **OPEN** — zero imports in `src/` |

## Baseline scan artifacts

- `docs/review/ruff_f401_f841_f821.txt` — 2320 lines of findings
- `docs/review/vulture.txt` — 17 high-confidence dead code hits
- `docs/review/radon_complexity.txt` — 92 functions grade C+
- `docs/review/god_files.txt` — files >500 LOC
- `docs/review/coverage.txt` — 42% total coverage

## Severity rubric

| Severity | Criteria | Action |
|----------|----------|--------|
| Critical | Security exposure, data loss, confirmed dead duplicate modules | Fix immediately |
| High | God files, unauthenticated admin, global error leaks | Fix immediately |
| Medium | Duplication, weak error handling, test gaps | Backlog |
| Low | TODOs, doc drift, style | Backlog |
