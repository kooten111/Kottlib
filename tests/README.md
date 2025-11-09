# Test Scripts

Test and validation scripts for YACLib Enhanced components.

## Available Tests

### `test_comic_loader.py`

Tests the comic loading functionality.

**Usage:**
```bash
python tests/test_comic_loader.py <path_to_comic>
```

**Example:**
```bash
python tests/test_comic_loader.py /mnt/Comics/Batman/issue1.cbz
```

**What it tests:**
- Opening CBZ/CBR/CB7 files
- Extracting page count
- Reading file list
- ComicInfo.xml metadata parsing
- Cover image extraction

**Expected output:**
```
Testing comic loader with: /mnt/Comics/Batman/issue1.cbz

✅ Comic opened successfully
📖 Format: cbz
📄 Pages: 24
📋 Files in archive: 24

ComicInfo.xml found:
  Title: Batman #1
  Series: Batman
  Number: 1
  Year: 2011
  Publisher: DC Comics

✅ Cover extracted successfully (1200x1800)
```

---

### `test_database.py`

Tests the database layer operations.

**Usage:**
```bash
python tests/test_database.py
```

**What it tests:**
- Database initialization
- Creating libraries
- Adding comics
- Creating folders
- Querying data
- Database relationships

**Expected output:**
```
Testing YACLib database layer...

✅ Database initialized
✅ Library created: Test Library (ID: 1)
✅ Comic added: test_comic.cbz (ID: 1)
✅ Folder created: Test Folder (ID: 1)

Database statistics:
  Libraries: 1
  Comics: 1
  Folders: 1

✅ All database operations successful!
```

---

### `test_phase1.py`

Comprehensive test of all Phase 1 components.

**Usage:**
```bash
python tests/test_phase1.py
```

**What it tests:**
- Database layer (full CRUD operations)
- Comic loader (all formats)
- Thumbnail generator (JPEG + WebP)
- API server basic startup
- End-to-end workflow

**Components tested:**
1. **Database:** Library/comic/folder creation and queries
2. **Scanner:** CBZ/CBR/CB7 file reading
3. **Thumbnails:** Cover extraction and dual-format generation
4. **API:** Server initialization and health check

**Best for:**
- Verifying Phase 1 completion
- Pre-deployment validation
- Regression testing after changes

---

### `test_phase2.py`

Tests Phase 2 Mobile UX improvements.

**Usage:**
```bash
python tests/test_phase2.py
```

**What it tests:**
- Folders-first sorting
- Reading progress tracking
- Continue reading feature
- Custom cover selection
- User session management

**Features tested:**

1. **Folders-first sorting:**
   - Folders appear before comics
   - Alphabetical ordering within each group

2. **Reading progress:**
   - Tracking current page
   - Per-user progress
   - Progress persistence

3. **Continue reading:**
   - Recent reading list
   - User-specific recents
   - Timestamp tracking

4. **Custom covers:**
   - Custom cover assignment
   - Fallback to default covers
   - Database storage

**Best for:**
- Verifying mobile UX features
- Testing multi-user scenarios
- Validating reading progress

---

## Test Library

### `testlibs/`

Contains test comic libraries for development and testing.

**Structure:**
```
tests/testlibs/
├── small/          # Small test library (< 10 comics)
├── medium/         # Medium test library (10-50 comics)
└── large/          # Large test library (50+ comics)
```

**Usage:**
```bash
# Scan test library
python scripts/scan_library.py tests/testlibs/small "Test Library"
```

---

## Running All Tests

To run all test scripts:

```bash
# Run each test individually
python tests/test_comic_loader.py /path/to/comic.cbz
python tests/test_database.py
python tests/test_phase1.py
python tests/test_phase2.py
```

## Test Database

Tests use a temporary database by default, but you can specify:

```python
# In test scripts, the database location is typically:
db_path = get_default_db_path()  # Uses standard location

# Or create temporary for testing:
import tempfile
db_path = tempfile.mktemp(suffix='.db')
```

## Expected Test Environment

- **Python:** 3.11+
- **Dependencies:** All from `requirements.txt`
- **Test data:** Sample comics (optional, tests create them)
- **Write access:** To database directory

## Interpreting Test Results

### ✅ Success Indicators
- Green checkmarks
- "✅ All tests passed"
- No errors in output

### ❌ Failure Indicators
- Red X marks
- Python exceptions/tracebacks
- "❌ Test failed" messages

### Common Issues

**Import errors:**
```
ModuleNotFoundError: No module named 'database'
```
→ Run from project root, not from tests/ directory

**Database locked:**
```
sqlite3.OperationalError: database is locked
```
→ Close other database connections

**Missing comic file:**
```
FileNotFoundError: comic.cbz not found
```
→ Provide valid path to test comic

## See Also

- [scripts/](../scripts/) - Production scanners
- [examples/](../examples/) - Usage examples
- [tools/](../tools/) - Admin tools
- [DOCUMENTATION_INDEX.md](../DOCUMENTATION_INDEX.md) - Full documentation
