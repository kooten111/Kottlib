# Scripts

Maintained utility scripts for Kottlib.

## Available Scripts

### `scan_library.py`
Scan and index a library into the database.

```bash
python3 scripts/scan_library.py <library_path> [--name "Library Name"] [--workers 4]
```

### `regenerate_covers.py`
Regenerate missing or stale covers for an existing library.

```bash
python3 scripts/regenerate_covers.py <library_id> [--force] [--workers 4]
```

### `diagnose_missing_data.py`
Diagnose missing files/covers and inspect specific comic records.

```bash
python3 scripts/diagnose_missing_data.py <library_id> [comic_id]
```

### `kottlib-cli.py`
CLI helper for config, library, and server operations.

```bash
./scripts/kottlib-cli.py --help
```

### `kottlib.py`
Thin launcher wrapper that delegates to `./start.sh`.

```bash
./scripts/kottlib.py
```

## Notes

- One-off migration and dataset-specific cleanup scripts were removed from this folder.
- For day-to-day usage, prefer `./start.sh` and `./scan.sh` from the project root.
