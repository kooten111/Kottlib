# YACLib Scanner System

A pluggable metadata scanner framework for different library types.

## Architecture

```
scanners/
├── base_scanner.py          # Base classes and interfaces
├── scanner_manager.py       # Central registry and orchestrator
├── nhentai/                 # nhentai scanner
│   ├── nhentai_scanner.py
│   └── __init__.py
├── AniList/                 # AniList scanner (manga) [TODO]
├── Jikan/                   # Jikan scanner (manga fallback) [TODO]
└── Comic Vine/              # Comic Vine scanner (comics) [TODO]
```

## Features

- **Pluggable Architecture**: Easy to add new metadata sources
- **Per-Library Configuration**: Different scanners for different library types
- **Fallback Support**: Automatic fallback to secondary sources
- **Confidence Scoring**: All matches include confidence scores (0-100%)
- **Smart Matching**: Uses fuzzy matching, metadata extraction, and validation

## Usage

### Basic Usage

```python
from scanners import init_default_scanners

# Initialize with default configuration
manager = init_default_scanners()

# Scan a file
result, candidates = manager.scan('file_type', 'comic_filename.cbz')

if result:
    print(f"Title: {result.metadata['title']}")
    print(f"Confidence: {result.confidence:.0%}")
    print(f"URL: {result.source_url}")
```

### Direct Scanner Use

```python
from scanners.nhentai import scan_file

# Scan without manager
result = scan_file("[Artist] Title [English].cbz")

if result:
    print(f"Artists: {result.metadata['artists']}")
    print(f"Tags: {result.tags}")
```

### Custom Configuration

```python
from scanners import ScannerManager, NhentaiScanner

manager = ScannerManager()
manager.register_scanner_class(NhentaiScanner)

# Configure for file_type library
manager.configure_library(
    'file_type',
    primary_scanner='nhentai',
    fallback_scanners=None,
    scanner_configs={
        'nhentai': {
            'confidence_threshold': 0.5,
            'use_fallback_searches': True
        }
    }
)

# Scan
result, _ = manager.scan('individual releases', 'file.cbz')
```

## Scanner Types

### File-Level Scanners
Operate on individual files (individual releases):
- **nhentai**: Extracts metadata per file using filename matching

### Series-Level Scanners
Operate on series/collections (manga, comics):
- **AniList**: [TODO] Manga/anime metadata
- **Jikan**: [TODO] MyAnimeList via Jikan API
- **Comic Vine**: [TODO] Western comics metadata

## Confidence Levels

| Level | Range | Meaning |
|-------|-------|---------|
| EXACT | 90-100% | Perfect or near-perfect match |
| HIGH | 70-89% | Very confident match |
| MEDIUM | 40-69% | Possible match, review recommended |
| LOW | 1-39% | Poor match, likely incorrect |
| NONE | 0% | No match found |

## nhentai Scanner Details

### Metadata Extraction
Automatically extracts from filename:
- Event codes (C101, C102, Kemoket, etc.)
- Artist/Circle names
- Parody/Series
- Language
- Translator

### Scoring System
- **Base Score**: Title similarity (0-100%)
- **Artist Match**: +15% (if unique in results)
- **Group Match**: +15% (if unique in results)
- **Parody Match**: +10% (if unique in results)
- **Event Match**: +10% (always - highly specific)
- **Artist Mismatch Penalty**: -50% (if expected artist not found)

### Fallback Searches
When initial search returns >20 results:
1. Try `artist + title`
2. Try `group + title`
3. Try `event + title`
4. Try `parody + title`

### Example Results

```python
ScanResult(
    confidence=1.0,
    source_id='573470',
    source_url='https://nhentai.net/g/573470',
    metadata={
        'title': '(C102) [Yachan Coffee] ...',
        'artists': ['yachan'],
        'groups': ['yachan coffee'],
        'parodies': ['love live nijigasaki high school idol club'],
        'language': ['english', 'translated'],
        ...
    },
    tags=[
        'tag:swimsuit',
        'tag:nakadashi',
        'artist:yachan',
        'parody:love live nijigasaki high school idol club',
        ...
    ]
)
```

## Adding New Scanners

### 1. Create Scanner Class

```python
from scanners.base_scanner import BaseScanner, ScanResult, ScanLevel

class MyScanner(BaseScanner):
    @property
    def source_name(self) -> str:
        return "my_source"

    @property
    def scan_level(self) -> ScanLevel:
        return ScanLevel.SERIES  # or ScanLevel.FILE

    def scan(self, query: str, **kwargs):
        # Implement your scanning logic
        # Return (best_result, all_candidates)
        pass
```

### 2. Register Scanner

```python
from scanners import get_manager

manager = get_manager()
manager.register_scanner_class(MyScanner)
```

### 3. Configure for Library

```python
manager.configure_library(
    'my_library_type',
    primary_scanner='my_source',
    fallback_scanners=['backup_source']
)
```

## Configuration File Support

Future enhancement: Load scanner configuration from YAML/JSON:

```yaml
libraries:
  individual releases:
    primary: nhentai
    fallback: []
    config:
      nhentai:
        confidence_threshold: 0.4

  manga:
    primary: AniList
    fallback: [Jikan]
    fallback_threshold: 0.7
    config:
      AniList:
        api_key: ${ANILIST_API_KEY}
```

## Testing

Run the demo:
```bash
cd /mnt/Black/Apps/KottLib/yaclib-enhanced
python3 scanners/demo_scanners.py
```

## Performance

- **nhentai Scanner**: ~1-2 seconds per file (network dependent)
- **Caching**: Results can be cached to avoid re-scanning
- **Batch Processing**: Process multiple files in parallel

## Future Enhancements

- [ ] AniList scanner for manga
- [ ] Jikan scanner as fallback
- [ ] Comic Vine scanner for western comics
- [ ] MangaDex scanner
- [ ] Result caching
- [ ] Batch processing API
- [ ] Web UI for manual review
- [ ] Database integration
- [ ] Config file support
