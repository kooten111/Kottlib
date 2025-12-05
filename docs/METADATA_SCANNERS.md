# Metadata Scanners Documentation

## Overview

The metadata scanner system provides a pluggable framework for fetching comic metadata from external sources. Scanners are discovered dynamically from the `scanners/` directory.

## Base Framework (`src/scanners/`)

### Module Structure

| File | Purpose |
|------|---------|
| `base_scanner.py` | Abstract scanner interface and data classes |
| `scanner_manager.py` | Scanner registry, discovery, and instantiation |
| `config_schema.py` | Configuration option definitions |
| `metadata_schema.py` | Field mapping between scanners and database |
| `utils.py` | Shared utility functions |

---

## base_scanner.py

### ScanLevel

Defines what level the scanner operates at.

```python
class ScanLevel(Enum):
    FILE = "file"      # Per-file metadata (e.g., nhentai)
    SERIES = "series"  # Per-series metadata (e.g., AniList, Comic Vine)
    LIBRARY = "library"  # Library-wide metadata
```

---

### MatchConfidence

Confidence level for metadata matches.

```python
class MatchConfidence(Enum):
    NONE = 0     # No match found (0.0)
    LOW = 1      # 0.0-0.4 confidence
    MEDIUM = 2   # 0.4-0.7 confidence
    HIGH = 3     # 0.7-0.9 confidence
    EXACT = 4    # 0.9-1.0 confidence
```

---

### ScanResult

Result from a metadata scan.

```python
@dataclass
class ScanResult:
    confidence: float           # Match confidence (0.0 to 1.0)
    source_id: Optional[str]    # ID from external source
    source_url: Optional[str]   # URL to source entry
    metadata: Dict              # Extracted metadata fields
    tags: List[str]             # Tags/genres
    raw_response: Optional[Dict]  # Raw API response (debugging)
    extra_metadata: Optional[Dict]  # Flexible metadata (display hints)
```

**Properties:**
- `confidence_level → MatchConfidence`: Get confidence as enum

**Methods:**
- `to_dict() → Dict`: Convert to dictionary for storage

**Confidence Thresholds:**
| Confidence | Level | Range |
|------------|-------|-------|
| NONE | 0 | 0.0 |
| LOW | 1 | 0.0-0.4 |
| MEDIUM | 2 | 0.4-0.7 |
| HIGH | 3 | 0.7-0.9 |
| EXACT | 4 | 0.9-1.0 |

---

### BaseScanner

Abstract base class for all metadata scanners.

```python
class BaseScanner(ABC):
    def __init__(self, config: Optional[Dict] = None)
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `config` | Dict | No | None | Scanner-specific configuration |

#### Abstract Properties

```python
@property
@abstractmethod
def source_name(self) -> str:
    """Name of the metadata source (e.g., 'nhentai', 'AniList')"""
    pass

@property
@abstractmethod
def scan_level(self) -> ScanLevel:
    """What level this scanner operates at"""
    pass
```

#### Abstract Methods

```python
@abstractmethod
def scan(self, query: str, **kwargs) -> Tuple[Optional[ScanResult], List[ScanResult]]:
    """
    Scan for metadata based on a query.
    
    Args:
        query: Search query (filename for FILE level, series name for SERIES level)
        **kwargs: Additional scanner-specific parameters
    
    Returns:
        Tuple of (best_match, all_matches)
        - best_match: Best matching result (or None if no good match)
        - all_matches: All potential matches for manual selection
    
    Raises:
        ScannerError: If scanning fails
    """
    pass
```

#### Optional Methods

```python
def get_config_schema(self) -> List[ConfigOption]:
    """
    Get declarative configuration schema.
    Returns list of ConfigOption objects for WebUI rendering.
    """
    return []

def get_required_config_keys(self) -> List[str]:
    """
    [DEPRECATED] Use get_config_schema() instead.
    Returns list of required config keys.
    """
    return []

def _validate_config(self):
    """Override to validate scanner configuration."""
    pass
```

---

### Exception Classes

```python
class ScannerError(Exception):
    """Base exception for scanner errors"""
    pass

class ScannerConfigError(ScannerError):
    """Configuration error (missing API key, invalid settings)"""
    pass

class ScannerAPIError(ScannerError):
    """API communication error"""
    pass

class ScannerRateLimitError(ScannerError):
    """Rate limit exceeded"""
    pass
```

---

## scanner_manager.py

### FallbackStrategy

How to handle fallback scanners.

```python
class FallbackStrategy(Enum):
    NONE = "none"                     # Don't use fallback
    ON_LOW_CONFIDENCE = "on_low_confidence"  # Use if confidence < threshold
    ON_FAILURE = "on_failure"         # Use only if primary fails
    ALWAYS = "always"                 # Always try all, merge results
```

---

### ScannerConfig

Configuration for a scanner in a library.

```python
@dataclass
class ScannerConfig:
    scanner_class: Type[BaseScanner]  # Scanner class to instantiate
    is_primary: bool = True           # Primary scanner flag
    is_fallback: bool = False         # Fallback scanner flag
    fallback_threshold: float = 0.7   # Confidence threshold for fallback
    config: Dict = None               # Scanner-specific configuration
```

---

### ScannerManager

Central registry and orchestrator for scanners.

```python
class ScannerManager:
    def __init__(self)
```

#### register_scanner_class

Register a scanner class.

```python
def register_scanner_class(self, scanner_class: Type[BaseScanner])
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `scanner_class` | Type[BaseScanner] | Scanner class to register |

**Side Effects:**
- Instantiates temporarily to get `source_name`
- Stores in `_available_scanners` dict

---

#### get_scanner

Get a scanner instance by name.

```python
def get_scanner(self, scanner_name: str, config: Optional[Dict] = None) -> BaseScanner
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `scanner_name` | str | Yes | Scanner name (e.g., "nhentai") |
| `config` | Dict | No | Scanner configuration |

**Returns:** Scanner instance

**Raises:** `ValueError` if scanner not found

---

#### get_available_scanners

Get list of available scanner names.

```python
def get_available_scanners(self) -> List[str]
```

**Returns:** List of scanner names

---

### discover_scanners

Automatically discover scanner plugins.

```python
def discover_scanners(scanners_dir: str = None) -> List[Type[BaseScanner]]
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `scanners_dir` | str | None | Scanners directory (default: project root/scanners) |

**Returns:** List of discovered scanner classes

**Discovery Rules:**
- Scans `scanners/` subdirectories
- Looks for `*_scanner.py` or `scanner.py` files
- Finds classes extending `BaseScanner`

---

### init_default_scanners

Initialize and register all discovered scanners.

```python
def init_default_scanners() -> ScannerManager
```

**Returns:** Configured ScannerManager instance

---

### Global Accessors

```python
def get_manager() -> ScannerManager
```

Get the global singleton ScannerManager instance.

---

## config_schema.py

### ConfigType

Configuration option types.

```python
class ConfigType(Enum):
    STRING = "string"     # Plain text input
    SECRET = "secret"     # Password-style input
    INTEGER = "integer"   # Numeric input
    FLOAT = "float"       # Decimal input
    BOOLEAN = "boolean"   # Toggle/checkbox
    SELECT = "select"     # Dropdown selection
    MULTISELECT = "multiselect"  # Multiple selection
```

---

### ConfigOption

Declarative configuration option.

```python
@dataclass
class ConfigOption:
    key: str                          # Configuration key name
    type: ConfigType                  # Input type
    label: str                        # Display label
    description: Optional[str] = None # Help text
    required: bool = False            # Required field
    default: Any = None               # Default value
    options: List[Dict] = None        # For SELECT/MULTISELECT
    min_value: Optional[float] = None # For numeric types
    max_value: Optional[float] = None
    step: Optional[float] = None
    placeholder: Optional[str] = None
```

**Methods:**
- `to_dict() → Dict`: Convert to dictionary for API

**Example:**
```python
from src.scanners.config_schema import ConfigOption, ConfigType

schema = [
    ConfigOption(
        key="api_key",
        type=ConfigType.SECRET,
        label="API Key",
        description="Your API key from the service",
        required=True
    ),
    ConfigOption(
        key="confidence_threshold",
        type=ConfigType.FLOAT,
        label="Confidence Threshold",
        description="Minimum confidence score for matches",
        default=0.6,
        min_value=0.0,
        max_value=1.0,
        step=0.05
    ),
    ConfigOption(
        key="language",
        type=ConfigType.SELECT,
        label="Preferred Language",
        options=[
            {"value": "en", "label": "English"},
            {"value": "ja", "label": "Japanese"}
        ],
        default="en"
    )
]
```

---

## Plugin Scanners (`scanners/`)

### Directory Structure

```
scanners/
├── nhentai/
│   ├── nhentai_scanner.py
│   ├── config.json
│   └── requirements.txt
├── AniList/
│   ├── anilist_scanner.py
│   ├── README.md
│   └── requirements.txt
├── ComicVine/
│   └── comic_vine_scanner.py
├── mangadex/
│   └── mangadex_scanner.py
└── metron/
    └── metron_scanner.py
```

---

### nhentai Scanner

**File:** `scanners/nhentai/nhentai_scanner.py`

| Property | Value |
|----------|-------|
| source_name | "nhentai" |
| scan_level | FILE |
| Description | Doujinshi metadata from nhentai.net |

**Scan Behavior:**
- Extracts numeric ID from filename
- Fetches gallery metadata via web scraping
- Returns high confidence for ID matches

**Metadata Fields:**
- title, artists, groups, tags, pages, language

**Example Query:** `[123456] Title.cbz` → Extracts ID 123456

---

### AniList Scanner

**File:** `scanners/AniList/anilist_scanner.py`

| Property | Value |
|----------|-------|
| source_name | "AniList" |
| scan_level | SERIES |
| Description | Manga/anime metadata from AniList (GraphQL API) |

**Scan Behavior:**
- Searches by series name
- Uses GraphQL API
- Supports romaji and native title matching

**Metadata Fields:**
- title, description, format, status, genres, year
- chapters, volumes, coverImage, bannerImage

**Rate Limits:** 90 requests/minute

**Example Query:** `"One Piece"` → Searches manga database

---

### Comic Vine Scanner

**File:** `scanners/ComicVine/comic_vine_scanner.py`

| Property | Value |
|----------|-------|
| source_name | "Comic Vine" |
| scan_level | SERIES |
| Description | Western comics from Comic Vine |

**Requirements:**
- API key required (free registration)

**Configuration:**
```python
get_config_schema() → [
    ConfigOption(key="api_key", type=SECRET, required=True)
]
```

**Metadata Fields:**
- name, publisher, start_year, count_of_issues
- description, image, characters

---

### MangaDex Scanner

**File:** `scanners/mangadex/mangadex_scanner.py`

| Property | Value |
|----------|-------|
| source_name | "MangaDex" |
| scan_level | SERIES |
| Description | Manga metadata from MangaDex |

**Features:**
- Multi-language title support
- Cover art URLs
- Status and publication info

**Rate Limits:** 5 requests/second

---

### Metron Scanner

**File:** `scanners/metron/metron_scanner.py`

| Property | Value |
|----------|-------|
| source_name | "Metron" |
| scan_level | SERIES |
| Description | Comics database metadata |

**Requirements:**
- Username and password required

**Configuration:**
```python
get_config_schema() → [
    ConfigOption(key="username", type=STRING, required=True),
    ConfigOption(key="password", type=SECRET, required=True)
]
```

---

## Creating a Custom Scanner

### Step 1: Create Directory

```bash
mkdir scanners/my_scanner
```

### Step 2: Create Scanner File

```python
# scanners/my_scanner/my_scanner.py

from typing import Tuple, Optional, List
from src.scanners.base_scanner import (
    BaseScanner, ScanResult, ScanLevel, MatchConfidence,
    ScannerError, ScannerConfigError, ScannerAPIError
)
from src.scanners.config_schema import ConfigOption, ConfigType


class MyScanner(BaseScanner):
    """Custom metadata scanner for My Source"""
    
    @property
    def source_name(self) -> str:
        return "My Source"
    
    @property
    def scan_level(self) -> ScanLevel:
        return ScanLevel.SERIES  # or ScanLevel.FILE
    
    def get_config_schema(self) -> List[ConfigOption]:
        return [
            ConfigOption(
                key="api_key",
                type=ConfigType.SECRET,
                label="API Key",
                required=True
            )
        ]
    
    def _validate_config(self):
        if not self.config.get("api_key"):
            raise ScannerConfigError("API key is required")
    
    def scan(
        self, 
        query: str, 
        **kwargs
    ) -> Tuple[Optional[ScanResult], List[ScanResult]]:
        """
        Search for metadata.
        
        Args:
            query: Series name or filename
            confidence_threshold: Minimum confidence (default 0.4)
        
        Returns:
            (best_match, all_matches) tuple
        """
        confidence_threshold = kwargs.get("confidence_threshold", 0.4)
        
        try:
            # Call external API
            results = self._search_api(query)
            
            if not results:
                return None, []
            
            # Convert to ScanResults
            all_matches = []
            for result in results:
                match = ScanResult(
                    confidence=result["score"],
                    source_id=str(result["id"]),
                    source_url=f"https://example.com/{result['id']}",
                    metadata={
                        "title": result["title"],
                        "description": result.get("description"),
                        "writer": result.get("author"),
                        "year": result.get("year"),
                    },
                    tags=result.get("tags", [])
                )
                all_matches.append(match)
            
            # Find best match above threshold
            best_match = None
            for match in all_matches:
                if match.confidence >= confidence_threshold:
                    if best_match is None or match.confidence > best_match.confidence:
                        best_match = match
            
            return best_match, all_matches
            
        except Exception as e:
            raise ScannerAPIError(f"API request failed: {e}")
    
    def _search_api(self, query: str) -> List[dict]:
        """Internal API call"""
        import requests
        
        response = requests.get(
            "https://api.example.com/search",
            params={"q": query},
            headers={"Authorization": f"Bearer {self.config['api_key']}"}
        )
        response.raise_for_status()
        return response.json()["results"]
```

### Step 3: Optional Files

**requirements.txt:**
```
requests>=2.28.0
```

**config.json:**
```json
{
    "display_name": "My Source",
    "description": "Custom scanner for My Source API",
    "website": "https://example.com"
}
```

---

## Scanner API Endpoints

See `docs/API_ROUTERS.md` for full API documentation.

### Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v2/scanners/available` | List available scanners |
| GET | `/v2/scanners/libraries` | Get library scanner configs |
| PUT | `/v2/scanners/libraries/{id}/configure` | Configure library scanner |
| POST | `/v2/scanners/scan` | Scan single item |
| POST | `/v2/scanners/scan/bulk` | Bulk scan |
| POST | `/v2/scanners/scan/library` | Scan entire library |
| GET | `/v2/scanners/scan/library/{id}/progress` | Get scan progress |

---

## Field Mapping

The `metadata_schema.py` file defines how scanner fields map to database columns:

```python
FIELD_MAPPINGS = {
    "title": "title",
    "description": "description",
    "writer": "writer",
    "artist": "artist",
    "year": "year",
    "publisher": "publisher",
    "genre": "genre",
    # ... more mappings
}
```

Scanners should use these standardized field names in their `metadata` dict for automatic mapping.
