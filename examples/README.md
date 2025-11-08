# YACLib Enhanced - Examples

Example scripts demonstrating YACLib Enhanced functionality.

## Available Examples

### 1. `test_comic_loader.py`

Tests the comic loading functionality - reads CBZ/CBR/CB7 files and displays metadata.

**Usage:**
```bash
python test_comic_loader.py /path/to/comic.cbz
```

**What it does:**
- Opens a comic archive
- Displays page count and file list
- Extracts ComicInfo.xml metadata if present
- Tests cover extraction

### 2. `test_database.py`

Tests the database layer - creates libraries, adds comics, retrieves data.

**Usage:**
```bash
python test_database.py
```

**What it does:**
- Initializes the YACLib database
- Creates a test library
- Adds test comics
- Displays library statistics
- Shows all database operations working

### 3. `scan_library.py`

Scans a directory for comics and adds them to the database with thumbnails.

**Usage:**
```bash
python scan_library.py /path/to/comics "My Comics"
```

**What it does:**
- Recursively scans a directory for comic files
- Creates folders and comics in the database
- Generates JPEG and WebP thumbnails
- Extracts metadata from ComicInfo.xml
- Shows progress and summary

**Example:**
```bash
# Scan your manga library
python scan_library.py /mnt/Comics/Manga "Manga Collection"

# Scan with auto-detected name
python scan_library.py /mnt/Comics/Marvel
```

### 4. `basic_usage.py`

Demonstrates using the YACReader client library (already exists).

**Usage:**
```bash
python basic_usage.py
```

## Running the Server

To start the FastAPI server:

```bash
cd src/api
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8081
```

Or from the project root:

```bash
cd /mnt/Black/Apps/KottLib/yaclib-enhanced
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8081
```

Then visit:
- API docs: http://localhost:8081/docs
- Health check: http://localhost:8081/health
- Server info: http://localhost:8081/api/v1/info

## Testing with YACReader Mobile App

1. Start the server:
   ```bash
   python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8081
   ```

2. Add a library:
   ```bash
   curl -X POST http://localhost:8081/api/v1/libraries \
     -H "Content-Type: application/json" \
     -d '{"name": "Test", "path": "/path/to/comics"}'
   ```

3. Scan the library:
   ```bash
   python examples/scan_library.py /path/to/comics
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

1. Scan your comic library
2. Start the server
3. Test with YACReader mobile app
4. Explore the API at http://localhost:8081/docs
5. Check out the full documentation in `/docs`
