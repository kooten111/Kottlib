# Phase 1 Testing Guide

This document outlines how to test all Phase 1 components of YACLib Enhanced.

## Quick Test: Run All Tests

```bash
# Comprehensive automated test
python examples/test_phase1.py
```

This will test:
- ✅ Database operations
- ✅ Comic loading (with auto-generated test comic)
- ✅ Thumbnail generation (JPEG + WebP)
- ✅ Full integration workflow
- ✅ API module verification

---

## Individual Component Tests

### 1. Database Layer

Test basic database operations:

```bash
python examples/test_database.py
```

**What it tests:**
- Database initialization
- Creating libraries
- Adding comics
- Querying data
- Getting statistics

**Expected output:**
```
✅ Database initialized
✅ Using library: Test Comics (ID: 1)
✅ Using comic: test.cbz (ID: 1)
✅ All tests completed successfully!
```

---

### 2. Comic Loader

Test loading real comic files (requires an actual comic file):

```bash
python examples/test_comic_loader.py /path/to/your/comic.cbz
```

**What it tests:**
- Format detection (CBZ/CBR/CB7)
- Opening archive files
- Reading page count
- Extracting ComicInfo.xml metadata
- Extracting cover image

**Supported formats:**
- `.cbz` (ZIP archives)
- `.cbr` (RAR archives - requires unrar)
- `.cb7` (7-Zip archives)

**Expected output:**
```
✅ Successfully opened comic
Format: CBZ
Pages: 24
📖 Comic Metadata (from ComicInfo.xml):
  Title: Amazing Comic
  Series: Amazing Series
  Issue: #1
✅ Cover extracted (45231 bytes)
```

---

### 3. Library Scanner

Test scanning a directory with comic files:

```bash
python examples/scan_library.py /path/to/comics "My Comics"
```

**What it tests:**
- Recursive directory scanning
- Comic file detection
- Metadata extraction
- Database insertion
- Thumbnail generation
- Duplicate detection (via hash)

**Expected output:**
```
Creating library...
✅ Library created (ID: 1)

Scanning directory...

📁 Series A/
  📖 issue_001.cbz
     ✅ Added to database (ID: 1)
     🖼️  Generating thumbnails...
     ✅ Thumbnails generated (JPEG + WebP)

Scan Complete!
Comics found: 150
Folders found: 12
Time elapsed: 45.23s
```

---

### 4. API Server

#### Start the Server

**Method 1: Using uvicorn (recommended)**
```bash
cd /mnt/Black/Apps/KottLib/yaclib-enhanced
uvicorn src.api.main:app --host 0.0.0.0 --port 8081 --reload
```

**Method 2: Using the startup script**
```bash
./run_server.sh
```

#### Test Endpoints

Once the server is running, test these endpoints:

**1. Health Check**
```bash
curl http://localhost:8081/health
# Expected: {"status":"healthy"}
```

**2. Server Info**
```bash
curl http://localhost:8081/api/v1/info
# Returns server version, features, database path
```

**3. List Libraries**
```bash
curl http://localhost:8081/api/v1/libraries
# Returns array of libraries with their comics
```

**4. Interactive API Documentation**

Open in browser: http://localhost:8081/docs

This shows the full Swagger UI with all endpoints and allows interactive testing.

---

### 5. Thumbnail Generator

The thumbnail generator is tested as part of the library scanner, but you can test it directly:

```python
from pathlib import Path
from scanner import open_comic
from scanner.thumbnail_generator import generate_dual_thumbnails, get_covers_dir

# Open a comic
with open_comic(Path('/path/to/comic.cbz')) as comic:
    # Extract cover
    cover_image = comic.extract_page_as_image(0)

    # Generate thumbnails
    covers_dir = get_covers_dir()
    jpeg_ok, webp_ok = generate_dual_thumbnails(
        cover_image,
        covers_dir,
        "test_hash_123"
    )

    print(f"JPEG: {jpeg_ok}, WebP: {webp_ok}")
```

**What it generates:**
- `{hash}.jpg` - 300x450px JPEG @ 85% quality (mobile compatible)
- `{hash}.webp` - 400x600px WebP @ 90% quality (web UI)

**Location:** `~/.local/share/yaclib/covers/`

---

## Testing Checklist

Use this checklist to verify Phase 1 is fully working:

### Core Components
- [ ] Database initializes without errors
- [ ] Can create libraries
- [ ] Can add comics to database
- [ ] Can query comics and libraries
- [ ] Database persists between runs

### Comic Loading
- [ ] CBZ files open correctly
- [ ] CBR files open (if unrar installed)
- [ ] CB7 files open (if py7zr installed)
- [ ] Page count is correct
- [ ] ComicInfo.xml is parsed
- [ ] Cover extraction works

### Scanning
- [ ] Scanner finds all comics in directory
- [ ] Nested folders are handled
- [ ] Metadata is extracted correctly
- [ ] Duplicates are detected (won't add twice)
- [ ] File hashes are calculated
- [ ] Thumbnails are generated

### Thumbnails
- [ ] JPEG thumbnails are created
- [ ] WebP thumbnails are created
- [ ] Thumbnails are correct size
- [ ] Thumbnails are stored in covers directory
- [ ] Duplicate thumbnails aren't regenerated

### API Server
- [ ] Server starts without errors
- [ ] Health check responds
- [ ] Info endpoint returns correct data
- [ ] Libraries endpoint works
- [ ] API docs are accessible at /docs
- [ ] CORS headers are present

### Integration
- [ ] Complete workflow: scan → database → thumbnails → API
- [ ] Can view comics via API
- [ ] Can get thumbnail paths
- [ ] Database stays consistent

---

## Common Issues

### Issue: "ModuleNotFoundError: No module named 'sqlalchemy'"
**Solution:** Install dependencies
```bash
pip install -r requirements.txt
```

### Issue: "Failed to open CBR files"
**Solution:** Install unrar
```bash
# Ubuntu/Debian
sudo apt install unrar
pip install rarfile

# macOS
brew install unrar
pip install rarfile
```

### Issue: "Permission denied" on database
**Solution:** Check database directory permissions
```bash
ls -la ~/.local/share/yaclib/
chmod 755 ~/.local/share/yaclib/
```

### Issue: "Import errors when running API"
**Solution:** Use uvicorn instead of running directly
```bash
uvicorn src.api.main:app --reload
# NOT: python src/api/main.py
```

---

## Performance Testing

### Large Library Test

Test with a large comic library (1000+ comics):

```bash
time python examples/scan_library.py /large/comic/library "Big Library"
```

**Expectations:**
- ~100-200 comics per minute (depending on file size and disk speed)
- Memory usage stays reasonable (< 500MB)
- No crashes or hangs
- Thumbnails generate correctly for all comics

### Concurrent API Requests

Test API performance:

```bash
# Install apache bench
sudo apt install apache2-utils

# Test 1000 requests with 10 concurrent
ab -n 1000 -c 10 http://localhost:8081/health

# Test library endpoint
ab -n 100 -c 5 http://localhost:8081/api/v1/libraries
```

**Expectations:**
- Health endpoint: > 1000 req/sec
- Library endpoint: > 100 req/sec (depends on DB size)
- No errors or timeouts

---

## Database Inspection

### View Database Contents

```bash
# Using sqlite3
sqlite3 ~/.local/share/yaclib/yaclib.db

# Useful queries
.tables                           # List all tables
SELECT COUNT(*) FROM comics;      # Count comics
SELECT COUNT(*) FROM libraries;   # Count libraries
SELECT * FROM libraries;          # View all libraries
SELECT filename, title FROM comics LIMIT 10;  # First 10 comics
```

### View Covers Directory

```bash
# List generated thumbnails
ls -lh ~/.local/share/yaclib/covers/

# Count thumbnails
ls ~/.local/share/yaclib/covers/*.jpg | wc -l
ls ~/.local/share/yaclib/covers/*.webp | wc -l
```

---

## Next Steps After Testing

Once all Phase 1 tests pass:

1. **Scan your actual comic library:**
   ```bash
   python examples/scan_library.py /path/to/your/comics "My Library"
   ```

2. **Start the server:**
   ```bash
   uvicorn src.api.main:app --host 0.0.0.0 --port 8081
   ```

3. **Test with YACReader mobile app:**
   - Point the app to: `http://your-server-ip:8081`
   - Browse your libraries
   - Verify covers load correctly

4. **Review Phase 2 features:**
   - Folders-first sorting
   - Reading progress tracking
   - Continue reading list
   - Custom cover selection

---

## Automated Testing Script

All the above tests are automated in:

```bash
python examples/test_phase1.py
```

This creates a test comic, tests all components, and reports results.

**Advantages:**
- No need for real comic files
- Consistent, repeatable results
- Fast execution (~5 seconds)
- Tests all major components

**What it doesn't test:**
- Real-world comic formats (only CBZ)
- Large library performance
- Network/API performance
- YACReader app compatibility

For comprehensive testing, run both the automated test AND manual tests with real comics.
