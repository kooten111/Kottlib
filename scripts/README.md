# Library Scanning Scripts

Production utilities for scanning and managing comic libraries.

## Available Scripts

### `scan_library.py` - Single-threaded Scanner

Basic library scanner suitable for small to medium libraries.

**Usage:**
```bash
python scripts/scan_library.py <library_path> [library_name]
```

**Example:**
```bash
python scripts/scan_library.py /mnt/Comics "My Comics"
```

**Features:**
- Recursively scans directories for comic files
- Creates folder hierarchy in database
- Extracts metadata from ComicInfo.xml
- Generates JPEG and WebP thumbnails
- Simple, straightforward progress output

**Best for:**
- Small libraries (< 100 comics)
- Single comic directory updates
- When simplicity is preferred

---

### `scan_library_fast.py` - Multi-threaded Scanner ⚡

High-performance scanner using parallel processing for large libraries.

**Usage:**
```bash
python scripts/scan_library_fast.py <library_path> [library_name] [workers]
```

**Arguments:**
- `library_path` - Path to comic library (required)
- `library_name` - Name for library (default: folder name)
- `workers` - Number of worker threads (default: 4)

**Example:**
```bash
# Use 8 worker threads for faster scanning
python scripts/scan_library_fast.py /mnt/Comics "My Comics" 8

# Use default 4 workers
python scripts/scan_library_fast.py /mnt/Comics
```

**Features:**
- Parallel processing with configurable worker threads
- Significantly faster for large libraries
- Real-time progress updates
- Performance metrics and optimization suggestions
- Same database structure as single-threaded scanner

**Performance:**
- 100 comics: ~2-3x faster than single-threaded
- 1000+ comics: ~5-8x faster (with 8 workers)
- Optimal workers: 1 per 50-100 comics (max 8-16)

**Best for:**
- Large libraries (100+ comics)
- Initial library scans
- Regular full rescans
- When speed matters

---

## Which Scanner Should I Use?

| Library Size | Recommended | Workers |
|-------------|-------------|---------|
| < 50 comics | `scan_library.py` | N/A |
| 50-100 comics | Either | 4 |
| 100-500 comics | `scan_library_fast.py` | 4-6 |
| 500-1000 comics | `scan_library_fast.py` | 6-8 |
| 1000+ comics | `scan_library_fast.py` | 8 |

## Database Location

Scanned libraries are stored in:
- **Linux:** `~/.local/share/kottlib/kottlib.db`
- **macOS:** `~/Library/Application Support/Kottlib/kottlib.db`
- **Windows:** `%APPDATA%/Kottlib/kottlib.db`

Thumbnails are stored in the `covers/` subdirectory.

## Supported Formats

- **CBZ** - ZIP-based comic archives
- **CBR** - RAR-based comic archives
- **CB7** - 7-Zip-based comic archives

## After Scanning

Once your library is scanned:

1. Start the server:
   ```bash
   ./kottlib.py
   ```

2. Access via YACReader mobile app:
   - Add server: `http://<your-ip>:8081`
   - Browse your scanned libraries!

3. Or explore via API:
   - Visit http://localhost:8081/docs

## See Also

- [examples/](../examples/) - Example usage scripts
- [tests/](../tests/) - Test scripts
- [tools/](../tools/) - Admin and debugging tools
