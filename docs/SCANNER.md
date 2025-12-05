# Scanner Documentation

## Overview

The `src/scanner/` directory contains the comic file scanning system that discovers, processes, and indexes comic archives in libraries.

## Modules

| Module | Purpose |
|--------|---------|
| `comic_loader.py` | Archive extraction (CBZ/CBR/CB7) |
| `threaded_scanner.py` | Multi-threaded library scanner |
| `thumbnail_generator.py` | Cover image generation |
| `tool_check.py` | External tool verification |

---

## comic_loader.py

Handles loading comic files from various archive formats with unified interface for page extraction and metadata reading.

### Constants

```python
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif'}
```

### ComicPage

Represents a single page in a comic archive.

```python
@dataclass
class ComicPage:
    filename: str           # Page filename within archive
    index: int              # 0-based page index
    size: Optional[int]     # File size in bytes
```

**Properties:**
- `is_image: bool` - Check if page is an image file based on extension

---

### ComicInfo

Comic metadata from ComicInfo.xml (30+ fields).

```python
@dataclass
class ComicInfo:
    # Basic information
    title: Optional[str]
    series: Optional[str]
    number: Optional[str]      # Issue number as string
    count: Optional[int]       # Total issues in series
    volume: Optional[int]
    summary: Optional[str]
    notes: Optional[str]

    # Date fields
    year: Optional[int]
    month: Optional[int]
    day: Optional[int]

    # Creator fields
    writer: Optional[str]
    penciller: Optional[str]
    inker: Optional[str]
    colorist: Optional[str]
    letterer: Optional[str]
    cover_artist: Optional[str]
    editor: Optional[str]

    # Publishing information
    publisher: Optional[str]
    imprint: Optional[str]
    genre: Optional[str]
    web: Optional[str]

    # Story arc information
    story_arc: Optional[str]
    story_arc_number: Optional[str]
    series_group: Optional[str]

    # Alternate series (for cross-overs)
    alternate_series: Optional[str]
    alternate_number: Optional[str]
    alternate_count: Optional[int]

    # Ratings and reviews
    age_rating: Optional[str]
    community_rating: Optional[float]  # 0.0 to 5.0

    # Characters and locations
    characters: Optional[str]
    teams: Optional[str]
    locations: Optional[str]

    # Other metadata
    page_count: Optional[int]
    language_iso: Optional[str]
    format: Optional[str]
    black_and_white: Optional[bool]
    manga: Optional[bool]
    gtin: Optional[str]
```

**Class Methods:**

```python
@classmethod
def from_xml(cls, xml_data: bytes) -> 'ComicInfo'
```

Parse ComicInfo.xml data from bytes.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `xml_data` | bytes | Yes | XML file contents |

**Returns:** `ComicInfo` instance (empty if parsing fails)

---

### ComicArchive

Abstract base class for comic archives.

```python
class ComicArchive:
    def __init__(self, file_path: Path)
```

| Property | Type | Description |
|----------|------|-------------|
| `pages` | List[ComicPage] | Lazy-loaded list of pages |
| `page_count` | int | Number of pages |
| `comic_info` | Optional[ComicInfo] | Parsed ComicInfo.xml |

**Methods:**

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_file` | `(filename: str) → Optional[bytes]` | Get file by name |
| `get_page` | `(index: int) → Optional[bytes]` | Get page by index |
| `get_cover` | `() → Optional[bytes]` | Get first page (cover) |
| `extract_page_as_image` | `(index: int) → Optional[Image.Image]` | Get page as PIL Image |
| `close` | `() → None` | Close archive |

**Context Manager Support:**
```python
with open_comic(Path("comic.cbz")) as comic:
    print(f"Pages: {comic.page_count}")
    cover = comic.get_cover()
```

---

### CBZArchive

ZIP-based comic archive handler.

```python
class CBZArchive(ComicArchive):
    def __init__(self, file_path: Path)
```

**Features:**
- Standard ZIP format support
- Case-insensitive file lookup
- Automatic ComicInfo.xml detection

---

### CBRArchive

RAR-based comic archive handler.

```python
class CBRArchive(ComicArchive):
    def __init__(self, file_path: Path)
```

**Requirements:**
- External `unrar` tool required
- Raises `RuntimeError` if unrar not found

**Installation:**
```bash
# Arch Linux
sudo pacman -S unrar

# Debian/Ubuntu
sudo apt install unrar
```

---

### CB7Archive

7-Zip-based comic archive handler.

```python
class CB7Archive(ComicArchive):
    def __init__(self, file_path: Path)
```

**Features:**
- Uses py7zr library
- In-memory extraction
- Custom writer factory pattern

---

### Utility Functions

#### detect_archive_format

Detect actual archive format by magic numbers.

```python
def detect_archive_format(file_path: Path) -> Optional[str]
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `file_path` | Path | Path to archive file |

**Returns:** `'zip'`, `'rar'`, `'7z'`, or `None`

**Magic Numbers:**
- ZIP: `PK` (0x504B)
- RAR: `Rar!` (0x52617221)
- 7z: `7z\xbc\xaf\x27\x1c`

---

#### open_comic

Open a comic archive file with automatic format detection.

```python
def open_comic(file_path: Path) -> Optional[ComicArchive]
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `file_path` | Path | Path to comic file |

**Returns:** `ComicArchive` instance or `None`

**Behavior:**
1. Tries detected format first (magic numbers)
2. Falls back to extension-based detection
3. Returns None if all formats fail

**Example:**
```python
from src.scanner.comic_loader import open_comic
from pathlib import Path

with open_comic(Path("/comics/issue1.cbz")) as comic:
    print(f"Title: {comic.comic_info.title if comic.comic_info else 'Unknown'}")
    print(f"Pages: {comic.page_count}")
    
    # Get cover image
    cover_bytes = comic.get_cover()
    
    # Get specific page
    page_5 = comic.get_page(4)  # 0-indexed
```

---

#### is_comic_file

Check if file is a supported comic format.

```python
def is_comic_file(file_path: Path) -> bool
```

**Supported Extensions:** `.cbz`, `.cbr`, `.cb7`, `.zip`

---

#### get_comic_format

Get comic format type string.

```python
def get_comic_format(file_path: Path) -> Optional[str]
```

**Returns:** `'CBZ'`, `'CBR'`, `'CB7'`, or `None`

---

## thumbnail_generator.py

Generates dual-format thumbnails for comic covers.

### Configuration

```python
JPEG_SIZE = (300, 450)   # Width x Height for mobile
WEBP_SIZE = (400, 600)   # Width x Height for web
JPEG_QUALITY = 85
WEBP_QUALITY = 90
```

### calculate_yacreader_hash

Calculate hash exactly as YACReader expects.

```python
def calculate_yacreader_hash(file_path: Path) -> str
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `file_path` | Path | Path to comic file |

**Returns:** Hash string: `SHA1(first 512KB) + file_size`

**Format:** `"a1b2c3d4e5...{sha1}" + "123456789{size}"`

**Critical:** Must match YACReader's algorithm or mobile clients will fail.

---

### get_thumbnail_path

Get path to thumbnail file using hierarchical storage.

```python
def get_thumbnail_path(
    covers_dir: Path,
    file_hash: str,
    format: str = 'JPEG',
    custom: bool = False
) -> Path
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `covers_dir` | Path | Yes | - | Base covers directory |
| `file_hash` | str | Yes | - | File hash |
| `format` | str | No | 'JPEG' | 'JPEG' or 'WEBP' |
| `custom` | bool | No | False | Use custom_covers subdirectory |

**Returns:** Path like `covers/ab/abc123.jpg`

**Storage Strategy:** Uses first 2 characters of hash as subdirectory to avoid thousands of files in single directory.

---

### generate_thumbnail_from_image

Generate thumbnail from PIL Image.

```python
def generate_thumbnail_from_image(
    image: Image.Image,
    output_path: Path,
    format: str = 'JPEG',
    size: Tuple[int, int] = JPEG_SIZE,
    quality: int = JPEG_QUALITY
) -> bool
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `image` | Image.Image | Yes | - | Source image |
| `output_path` | Path | Yes | - | Output file path |
| `format` | str | No | 'JPEG' | Output format |
| `size` | Tuple | No | JPEG_SIZE | Target dimensions |
| `quality` | int | No | JPEG_QUALITY | Compression quality |

**Returns:** `True` if successful

**Behavior:**
- Converts RGBA to RGB for JPEG (white background)
- Maintains aspect ratio
- Creates parent directories

---

### generate_dual_thumbnails

Generate both JPEG and WebP thumbnails.

```python
def generate_dual_thumbnails(
    cover_image: Image.Image,
    covers_dir: Path,
    file_hash: str
) -> Tuple[bool, bool]
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `cover_image` | Image.Image | PIL Image of cover |
| `covers_dir` | Path | Covers directory |
| `file_hash` | str | Comic file hash |

**Returns:** `(jpeg_success, webp_success)` tuple

---

### thumbnail_exists

Check if thumbnail already exists.

```python
def thumbnail_exists(covers_dir: Path, file_hash: str, format: str = 'JPEG') -> bool
```

---

### clean_orphaned_thumbnails

Remove thumbnails for comics that no longer exist.

```python
def clean_orphaned_thumbnails(covers_dir: Path, valid_hashes: set) -> int
```

**Returns:** Number of thumbnails removed

---

## threaded_scanner.py

High-performance multi-threaded scanner for large comic libraries.

### ScanResult

Result from scanning operation.

```python
@dataclass
class ScanResult:
    comics_found: int = 0
    comics_added: int = 0
    comics_skipped: int = 0
    comics_skipped_unchanged: int = 0   # Fast path: unchanged files
    comics_updated: int = 0             # Moved/renamed files
    folders_found: int = 0
    thumbnails_generated: int = 0
    errors: int = 0
    duration: float = 0.0
```

---

### ThreadedScanner

Multi-threaded comic library scanner.

```python
class ThreadedScanner:
    def __init__(
        self,
        db: Database,
        library_id: int,
        max_workers: int = 4,
        progress_callback=None
    )
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `db` | Database | Yes | - | Database instance |
| `library_id` | int | Yes | - | Library ID to scan |
| `max_workers` | int | No | 4 | Number of worker threads |
| `progress_callback` | callable | No | None | Callback(current, total, message, ...) |

#### scan_library

Main entry point for scanning.

```python
def scan_library(self, library_path: Path) -> ScanResult
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `library_path` | Path | Path to library root |

**Returns:** `ScanResult` with statistics

**Phases:**
1. **Structure Analysis**: Classify folder types (simple, nested, unpacked)
2. **File Discovery**: Find all comic files (single-threaded, fast)
3. **Folder Creation**: Create folder records in database
4. **Comic Processing**: Process comics in parallel (multi-threaded)
5. **Series Rebuild**: Rebuild series table from comics
6. **Cache Building**: Build and cache series tree

**Structure Detection:**
- **simple**: Series folder contains archives directly (`/Series/Vol1.cbz`)
- **nested**: Franchise folder with sub-series (`/Batman/Night of Owls/Vol1.cbz`)
- **unpacked**: Raw image folders (`/Series/Chapter1/001.jpg`)

---

#### Progress Callback

```python
def progress_callback(
    current: int,           # Comics processed
    total: int,             # Total comics
    message: str,           # Status message
    series_name: str,       # Current series (optional)
    filename: str,          # Current file (optional)
    running_comics: list    # List of (series, filename) being processed
)
```

---

### Convenience Function

```python
def scan_library_threaded(
    db: Database,
    library_id: int,
    library_path: Path,
    max_workers: int = 4,
    progress_callback=None
) -> ScanResult
```

---

## tool_check.py

External tool verification for RAR and 7z support.

```python
def check_unrar_available() -> bool
def check_7z_available() -> bool
def get_missing_tools() -> List[str]
```

---

## Performance Optimizations

### Fast Path for Unchanged Files

The scanner checks `(path, mtime)` before calculating hash:

```python
existing = get_comic_by_path_and_mtime(session, path, mtime, library_id)
if existing:
    # Skip hash calculation - file unchanged
    return
```

### Slow Path for Modified Files

Only calculates YACReader hash when file has changed:

```python
file_hash = calculate_yacreader_hash(comic_path)
existing = get_comic_by_hash(session, file_hash, library_id)
if existing:
    # Update path/filename if moved
    existing.path = str(comic_path)
    existing.filename = comic_path.name
```

### Thread Safety

- Uses `threading.Lock` for counter updates
- Each thread has its own database session
- Commits are per-comic for interrupt safety

### Ordered Processing

Comics are processed in file order (not completion order). If scan is interrupted, all processed comics are fully complete with metadata and thumbnails.

---

## Usage Example

```python
from src.database import Database
from src.scanner.threaded_scanner import ThreadedScanner
from pathlib import Path

# Initialize
db = Database("/path/to/yaclib.db")
library_id = 1

# Create scanner with progress callback
def on_progress(current, total, message, *args):
    percent = (current / total * 100) if total > 0 else 0
    print(f"[{percent:.1f}%] {message}")

scanner = ThreadedScanner(db, library_id, max_workers=8, progress_callback=on_progress)

# Run scan
result = scanner.scan_library(Path("/comics/manga"))

print(f"Scan complete in {result.duration:.2f}s")
print(f"  Found: {result.comics_found}")
print(f"  Added: {result.comics_added}")
print(f"  Skipped: {result.comics_skipped} ({result.comics_skipped_unchanged} unchanged)")
print(f"  Updated: {result.comics_updated}")
print(f"  Errors: {result.errors}")
```
