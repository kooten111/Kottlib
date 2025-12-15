# Scanners Documentation

## Overview

Kottlib has a dual scanner system:

1. **Core Scanner Engine** (`src/scanner/`) - Discovers and processes comic files in libraries
2. **Metadata Scanner System** (`src/metadata_providers/`) - Fetches metadata from external sources

This document covers both systems and how they work together.

---

## Core Scanner Engine

The core scanner engine in `src/scanner/` handles the discovery, processing, and indexing of comic files in your libraries.

### Architecture

The scanner system has been refactored into focused modules:

| Module | Purpose |
|--------|---------|
| `base.py` | ScanResult dataclass |
| `file_discovery.py` | File discovery functions |
| `structure_classifier.py` | Library structure classification |
| `folder_manager.py` | Folder creation and management |
| `comic_processor.py` | Single comic processing |
| `series_builder.py` | Series table rebuilding |
| `threaded_scanner.py` | Multi-threaded scanner orchestrator |
| `comic_loader.py` | Archive extraction (CBZ/CBR/CB7) |
| `thumbnail_generator.py` | Cover image generation |

### Comic Loading

The `comic_loader.py` module handles reading comic archives:

**Supported Formats:**
- **CBZ** - ZIP-based archives (native Python support)
- **CBR** - RAR-based archives (requires `unrar` tool)
- **CB7** - 7-Zip archives (uses `py7zr` library)

**Key Classes:**

```python
@dataclass
class ComicPage:
    filename: str           # Page filename within archive
    index: int              # 0-based page index
    size: Optional[int]     # File size in bytes

class ComicArchive:
    pages: List[ComicPage]              # Lazy-loaded list of pages
    page_count: int                     # Number of pages
    comic_info: Optional[ComicInfo]     # Parsed ComicInfo.xml
    
    def get_page(index: int) -> Optional[bytes]
    def get_cover() -> Optional[bytes]
    def extract_page_as_image(index: int) -> Optional[Image.Image]
```

**Usage:**

```python
from src.scanner.comic_loader import open_comic

with open_comic(Path("comic.cbz")) as comic:
    print(f"Pages: {comic.page_count}")
    cover_data = comic.get_cover()
    
    # Access ComicInfo.xml metadata if present
    if comic.comic_info:
        print(f"Title: {comic.comic_info.title}")
        print(f"Series: {comic.comic_info.series}")
```

### Multi-threaded Scanning

The `ThreadedScanner` class provides high-performance parallel scanning:

```python
from src.scanner.threaded_scanner import ThreadedScanner
from src.database import Database

db = Database()
scanner = ThreadedScanner(
    db=db,
    library_id=1,
    max_workers=4,  # Number of parallel workers
    progress_callback=my_progress_fn
)

result = scanner.scan_library(Path("/path/to/library"))
print(f"Added: {result.comics_added}, Errors: {result.errors}")
```

**Features:**
- Parallel processing with configurable workers
- Progress callbacks for UI updates
- Atomic commits (interrupted scans leave database consistent)
- Automatic series detection and grouping
- Thumbnail generation (JPEG for mobile, WebP for web)

---

## Metadata Scanner System

The metadata scanner system (`src/metadata_providers/`) provides a pluggable framework for fetching comic metadata from external sources like AniList, MangaDex, Comic Vine, etc.

### Framework Architecture

The metadata scanner framework is located in `src/metadata_providers/` (formerly `src/scanners/`):

| Module | Purpose |
|--------|---------|
| `base.py` | Abstract scanner interface and data classes |
| `manager.py` | Scanner registry and instantiation |
| `schema.py` | Field mapping between scanners and database |
| `providers/` | Individual scanner implementations |

### Core Concepts

#### Scan Levels

Scanners operate at different levels:

```python
class ScanLevel(Enum):
    FILE = "file"       # Per-file metadata (e.g., nhentai)
    SERIES = "series"   # Per-series metadata (e.g., AniList, MangaDex)
    LIBRARY = "library" # Library-wide metadata
```

#### Match Confidence

All scanner results include a confidence score:

| Level | Range | Meaning |
|-------|-------|---------|
| EXACT | 90-100% | Perfect or near-perfect match |
| HIGH | 70-89% | Very confident match |
| MEDIUM | 40-69% | Possible match, review recommended |
| LOW | 1-39% | Poor match, likely incorrect |
| NONE | 0% | No match found |

#### ScanResult

Scanner results are returned in a standardized format:

```python
@dataclass
class ScanResult:
    confidence: float              # Match confidence (0.0 to 1.0)
    source_id: Optional[str]       # ID from external source
    source_url: Optional[str]      # URL to source entry
    metadata: Dict                 # Extracted metadata fields
    tags: List[str]                # Tags/genres
    raw_response: Optional[Dict]   # Raw API response (debugging)
    extra_metadata: Optional[Dict] # Flexible metadata
    
    @property
    def confidence_level(self) -> MatchConfidence:
        """Get confidence as enum"""
```

### Available Scanners

#### nhentai Scanner
- **Level:** FILE (per-file)
- **Path:** `src/metadata_providers/providers/nhentai/`
- **Best for:** Doujinshi with structured filenames
- **Features:**
  - Extracts event codes (C101, Kemoket, etc.)
  - Artist/Circle name detection
  - Language and parody detection
  - Fallback search strategies

#### AniList Scanner
- **Level:** SERIES
- **Path:** `src/metadata_providers/providers/anilist/`
- **Best for:** Manga series
- **Features:**
  - GraphQL API integration
  - Rich metadata (genres, tags, ratings)
  - Cover image URLs
  - Character information

#### MangaDex Scanner
- **Level:** SERIES
- **Path:** `src/metadata_providers/providers/mangadex/`
- **Best for:** Manga with MangaDex presence
- **Features:**
  - REST API v5 integration
  - Multiple language support
  - Author and artist information
  - Chapter tracking

#### Comic Vine Scanner
- **Level:** SERIES
- **Path:** `src/metadata_providers/providers/comicvine/`
- **Best for:** Western comics
- **Requirements:** API key
- **Features:**
  - Comprehensive western comics database
  - Publisher information
  - Character and team data
  - Story arc tracking

#### Metron Scanner
- **Level:** SERIES
- **Path:** `src/metadata_providers/providers/metron/`
- **Best for:** Western comics
- **Requirements:** Username and password
- **Features:**
  - Modern comics database
  - Detailed creator credits
  - Publisher and imprint data
  - Issue-level metadata

### Using Scanners

#### Basic Usage

```python
from src.metadata_providers import get_manager

manager = get_manager()

# Scan a file
result, candidates = manager.scan('nhentai', '[Artist] Title [English].cbz')

if result:
    print(f"Title: {result.metadata['title']}")
    print(f"Confidence: {result.confidence:.0%}")
    print(f"URL: {result.source_url}")
```

#### Library Configuration

Configure scanners per library:

```python
from src.metadata_providers import get_manager

manager = get_manager()
manager.configure_library(
    'manga_library',
    primary_scanner='anilist',
    fallback_scanners=['mangadex'],
    fallback_threshold=0.7,
    scanner_configs={
        'anilist': {
            'preferred_language': 'ENGLISH'
        }
    }
)
```

#### Via API

Scanners are accessible via the REST API:

```bash
# Get available scanners
GET /v2/scanners/available

# Configure library scanner
PUT /v2/scanners/libraries/1/configure
{
    "primary_scanner": "nhentai",
    "fallback_scanners": [],
    "confidence_threshold": 0.4
}

# Scan a file
POST /v2/scanners/scan
{
    "query": "[Artist] Title [English].cbz",
    "library_id": 1
}
```

### Creating Custom Scanners

You can add new metadata scanners by creating a plugin in `src/metadata_providers/providers/`:

#### 1. Create Scanner Class

```python
from src.metadata_providers.base import BaseScanner, ScanResult, ScanLevel
from typing import Optional, List, Tuple, Dict

class MyScanner(BaseScanner):
    @property
    def source_name(self) -> str:
        return "my_source"
    
    @property
    def scan_level(self) -> ScanLevel:
        return ScanLevel.SERIES  # or ScanLevel.FILE
    
    def scan(self, query: str, **kwargs) -> Tuple[Optional[ScanResult], List[ScanResult]]:
        # Implement your scanning logic
        # Return (best_result, all_candidates)
        
        # Example result:
        result = ScanResult(
            confidence=0.95,
            source_id="12345",
            source_url="https://mysource.com/series/12345",
            metadata={
                'title': 'Series Title',
                'summary': 'Series description...',
                'year': 2024,
                'status': 'ongoing'
            },
            tags=['action', 'comedy']
        )
        return result, [result]
    
    def get_config_schema(self) -> List[ConfigOption]:
        """Define configuration options for WebUI"""
        return [
            ConfigOption(
                key='api_key',
                display_name='API Key',
                description='Your API key from mysource.com',
                data_type='string',
                required=True,
                secret=True
            )
        ]
```

#### 2. Register Scanner

Add your scanner to the manager in `src/metadata_providers/__init__.py`:

```python
from .providers.mysource.my_scanner import MyScanner

def init_default_scanners():
    manager = ScannerManager()
    # ... existing scanners
    manager.register_scanner_class(MyScanner)
    return manager
```

#### 3. Add Provider-Specific Documentation

Create a README in your scanner's directory: `src/metadata_providers/providers/mysource/README.md`

See existing scanner READMEs for examples:
- `scanners/AniList/README.md`
- `src/metadata_providers/providers/mangadex/README.md`

### Configuration

#### Library-Level Configuration

Libraries can be configured with different scanners:

```yaml
# config.yml
libraries:
  - name: "Doujinshi"
    path: "/comics/doujinshi"
    settings:
      scanner:
        primary: nhentai
        confidence_threshold: 0.4
        
  - name: "Manga"
    path: "/comics/manga"
    settings:
      scanner:
        primary: anilist
        fallback: [mangadex]
        fallback_threshold: 0.7
```

#### Scanner-Specific Configuration

Each scanner can have its own configuration:

```python
scanner_configs = {
    'comicvine': {
        'api_key': 'YOUR_API_KEY',
        'preferred_format': 'issue'
    },
    'metron': {
        'username': 'your_username',
        'password': 'your_password'
    },
    'anilist': {
        'preferred_language': 'ENGLISH',
        'include_adult': False
    }
}
```

### Metadata Field Mapping

The `schema.py` module defines how scanner metadata maps to database fields:

```python
from src.metadata_providers.schema import map_scanner_metadata_to_comic

# Scanner metadata
scanner_data = {
    'title': 'My Comic',
    'summary': 'A great story...',
    'year': 2024,
    'authors': ['John Doe']
}

# Map to database columns
db_data = map_scanner_metadata_to_comic(scanner_data)
# Result: {'title': 'My Comic', 'summary': 'A great story...', ...}
```

**Field Categories:**
- **Basic**: title, series, issue number
- **Publishing**: publisher, year, language
- **Creator**: writer, artist, penciller, etc.
- **Content**: genre, tags, age rating
- **Story**: summary, story arc information

### Error Handling

Scanners raise specific exceptions:

```python
from src.metadata_providers.base import (
    ScannerError,
    ScannerConfigError,
    ScannerAPIError,
    ScannerRateLimitError
)

try:
    result, _ = manager.scan('comicvine', 'Batman')
except ScannerConfigError as e:
    print(f"Configuration error: {e}")
except ScannerAPIError as e:
    print(f"API error: {e}")
except ScannerRateLimitError as e:
    print(f"Rate limited: {e}")
```

### Performance Considerations

- **Caching**: Scanner results can be cached to avoid re-scanning
- **Rate Limiting**: Respect API rate limits (built into scanners)
- **Batch Processing**: Process multiple files in parallel when possible
- **Fallback Strategy**: Use fallback scanners judiciously to avoid excessive API calls

### Testing Scanners

Test scanners using the CLI or API:

```bash
# Via API
GET /v2/scanners/test/nhentai?query=[Artist]%20Title%20[English].cbz

# Via Python
from src.metadata_providers import get_manager

manager = get_manager()
result, candidates = manager.scan('nhentai', '[Artist] Title [English].cbz')

print(f"Confidence: {result.confidence}")
print(f"Metadata: {result.metadata}")
print(f"Candidates: {len(candidates)}")
```

---

## Integration

The two scanner systems work together:

1. **Core Scanner** discovers comic files and extracts basic info (filename, page count, hash)
2. **Metadata Scanners** are then used to enrich the metadata from external sources
3. Results are merged and stored in the database

**Workflow:**

```
1. Core Scanner discovers: my_comic.cbz
2. Core Scanner extracts: 24 pages, hash, basic metadata
3. Metadata Scanner searches: nhentai for "my_comic"
4. Metadata Scanner returns: title, artists, tags, etc.
5. Service layer merges: all metadata into database
```

This separation allows:
- Fast library scanning without external API calls
- On-demand metadata enrichment
- Flexible scanner selection per library
- Offline operation for basic functionality

---

## See Also

- **Provider-specific docs:** `scanners/AniList/README.md`, etc.
- **API Documentation:** `docs/API.md`
- **Service Layer:** `docs/SERVICES.md`
- **Architecture:** `docs/ARCHITECTURE.md`
