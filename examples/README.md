# YACLib Enhanced - Examples

Example scripts demonstrating YACLib Enhanced functionality.

## Available Examples

### `basic_usage.py`

Demonstrates using the YACReader client library to interact with a YACLib server.

**Usage:**
```bash
python examples/basic_usage.py
```

**What it demonstrates:**
- Connecting to YACLib server
- Opening comics remotely
- Fetching comic metadata
- Downloading comic pages
- Proper client session handling

### `create_test_library.py`

Creates a test library with sample comics for development and testing.

**Usage:**
```bash
python examples/create_test_library.py
```

**What it does:**
- Generates sample CBZ files
- Creates a test library structure
- Useful for development without real comic files

### `profile_scan.py`

Performance profiling tool for the library scanner.

**Usage:**
```bash
python examples/profile_scan.py /path/to/comics
```

**What it does:**
- Profiles scanner performance
- Identifies bottlenecks
- Generates performance reports
- Useful for optimization work

## Production Scripts

For actual library management, use the scripts in the `scripts/` directory:

### Library Scanning

```bash
# Single-threaded scanner (good for small libraries)
python scripts/scan_library.py /path/to/comics "My Comics"

# Multi-threaded scanner (recommended for large libraries)
python scripts/scan_library_fast.py /path/to/comics "My Comics" 8
```

See [scripts/](../scripts/) for more information.

## Testing Scripts

Test scripts have been moved to the `tests/` directory:

```bash
# Test comic loader
python tests/test_comic_loader.py /path/to/comic.cbz

# Test database layer
python tests/test_database.py

# Test Phase 1 features
python tests/test_phase1.py

# Test Phase 2 features
python tests/test_phase2.py
```

See [tests/](../tests/) for more information.

## Utility Tools

Administrative and debugging tools are in the `tools/` directory:

```bash
# Debug folder relationships
python tools/debug_folders.py

# Test folder API responses
python tools/test_folder_api.py 1 0

# Import from YACReader
python tools/import_yacreader.py

# Run database migrations
python tools/migrations/migrate_to_yacreader_schema.py
```

See [tools/](../tools/) for more information.

## Running the Server

To start the FastAPI server:

```bash
# Using the main launcher (recommended)
./yaclib.py

# Or using uvicorn directly
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8081
```

Then visit:
- API docs: http://localhost:8081/docs
- Health check: http://localhost:8081/health
- Server info: http://localhost:8081/api/v1/info

## Testing with YACReader Mobile App

1. Start the server:
   ```bash
   ./yaclib.py
   ```

2. Add a library (if not already configured):
   ```bash
   ./yaclib-cli.py library add "Comics" /path/to/comics
   ```

3. Scan the library:
   ```bash
   python scripts/scan_library_fast.py /path/to/comics "Comics" 8
   ```

4. In YACReader mobile app:
   - Add server: `http://<your-ip>:8081`
   - Browse libraries and comics!

## Database Location

The database is created at:
- **Linux:** `~/.local/share/yaclib/yaclib.db`
- **macOS:** `~/Library/Application Support/YACLib/yaclib.db`
- **Windows:** `%APPDATA%/YACLib/yaclib.db`

Thumbnails are stored in the `covers/` subdirectory next to the database.

## Requirements

Make sure you have installed all dependencies:

```bash
pip install -r requirements.txt
```

## Next Steps

After running these examples:

1. Scan your comic library using `scripts/scan_library_fast.py`
2. Start the server with `./yaclib.py`
3. Test with YACReader mobile app
4. Explore the API at http://localhost:8081/docs
5. Check out the full documentation in [DOCUMENTATION_INDEX.md](../DOCUMENTATION_INDEX.md)
