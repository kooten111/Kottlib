# Scanner Plugin Development Guide

This guide explains how to create a pluggable metadata scanner for YACLib Enhanced.

## Overview

The scanner system uses a plugin architecture where scanner implementations are discovered automatically from the `/scanners/` directory at the project root. Each scanner is a Python module that extends the `BaseScanner` class from the core framework in `/src/scanners/`.

## Directory Structure

### Where to Place Your Scanner

Scanners are **pluggable plugins** located in the `/scanners/` directory (at project root):

```
/scanners/                          # Plugin directory (where you add your scanner)
├── YourScanner/                    # Your new scanner folder
│   ├── __init__.py                 # Module init (can be empty)
│   ├── your_scanner.py             # Main scanner implementation (*_scanner.py)
│   └── requirements.txt            # Optional: scanner-specific dependencies
├── AniList/                        # Existing: AniList scanner
├── ComicVine/                      # Existing: Comic Vine scanner
├── mangadex/                       # Existing: MangaDex scanner
├── metron/                         # Existing: Metron scanner
└── nhentai/                        # Existing: nhentai scanner

/src/scanners/                      # Core framework (do not modify)
├── base_scanner.py                 # Base classes: BaseScanner, ScanResult, ScanLevel
├── scanner_manager.py              # Discovery and registration
├── config_schema.py                # ConfigOption, ConfigType for UI configuration
├── metadata_schema.py              # Metadata schema definitions
└── utils.py                        # Utility functions (clean_query, etc.)
```

### File Naming Convention

Scanner files must follow the naming pattern `*_scanner.py` or `scanner.py` to be discovered automatically.

Good examples:
- `anilist_scanner.py`
- `comic_vine_scanner.py`
- `mangadex_scanner.py`
- `scanner.py`

## Required Structure

### BaseScanner Class

Every scanner must extend `BaseScanner` and implement the required abstract methods:

```python
#!/usr/bin/env python3
"""
My Scanner - Metadata Scanner for [Description]

Brief description of what this scanner does and what API it uses.
"""

from typing import List, Tuple, Optional, Dict

try:
    # Import from src.scanners package
    from src.scanners.base_scanner import (
        BaseScanner, ScanResult, ScanLevel, MatchConfidence,
        ScannerAPIError, ScannerRateLimitError, ScannerConfigError
    )
    from src.scanners.config_schema import ConfigOption, ConfigType
    from src.scanners.utils import clean_query
except ImportError:
    # Fallback for standalone execution
    from abc import ABC
    BaseScanner = ABC
    ScanResult = None
    ScanLevel = None
    MatchConfidence = None
    ScannerAPIError = Exception
    ScannerRateLimitError = Exception
    ScannerConfigError = Exception


class MyScanner(BaseScanner):
    """
    My metadata scanner implementation
    
    Describe your scanner's purpose, API source, and special features.
    """
    
    @property
    def source_name(self) -> str:
        """
        Unique identifier for this scanner.
        
        This name is used in configuration and UI.
        Examples: "AniList", "ComicVine", "MangaDex", "nhentai"
        """
        return "MySource"
    
    @property
    def scan_level(self) -> ScanLevel:
        """
        What level this scanner operates at.
        
        Returns:
            ScanLevel.FILE - Per-file scanning (e.g., individual doujinshi)
            ScanLevel.SERIES - Per-series scanning (e.g., manga, comics)
            ScanLevel.LIBRARY - Library-wide scanning (rare)
        """
        return ScanLevel.SERIES
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize scanner with configuration.
        
        Args:
            config: Dictionary of configuration options
        """
        super().__init__(config)
        
        # Extract configuration options
        self.confidence_threshold = self.config.get('confidence_threshold', 0.6)
        self.timeout = self.config.get('timeout', 30)
        
        # Initialize your API client
        # self.api = MyAPIClient(...)
    
    def scan(self, query: str, **kwargs) -> Tuple[Optional[ScanResult], List[ScanResult]]:
        """
        Scan for metadata based on a query.
        
        Args:
            query: Search query (filename for FILE level, series name for SERIES level)
            **kwargs: Additional scanner-specific parameters
        
        Returns:
            Tuple of (best_match, all_matches)
            - best_match: The best matching result (or None if no good match)
            - all_matches: List of all potential matches for manual selection
        """
        # 1. Clean the query if needed
        search_query = clean_query(query) if self.config.get('use_normalized_search', True) else query
        
        # 2. Call your API
        # results = self.api.search(search_query)
        
        # 3. Score and convert results to ScanResult objects
        all_results = []
        # for item in results:
        #     result = self._convert_to_scan_result(item, query)
        #     all_results.append(result)
        
        # 4. Sort by confidence
        all_results.sort(key=lambda r: r.confidence, reverse=True)
        
        # 5. Return best match (if above threshold) and all candidates
        best_match = None
        if all_results and all_results[0].confidence >= self.confidence_threshold:
            best_match = all_results[0]
        
        return best_match, all_results
    
    def get_config_schema(self) -> List[ConfigOption]:
        """
        Declarative configuration schema for WebUI rendering.
        
        Returns a list of ConfigOption objects that define what configuration
        this scanner needs. The WebUI automatically renders appropriate
        input controls based on option types.
        """
        try:
            from src.scanners.config_schema import ConfigOption, ConfigType
        except ImportError:
            return []
        
        return [
            ConfigOption(
                key="api_key",
                type=ConfigType.SECRET,
                label="API Key",
                description="Your API key from the service",
                required=True,
                placeholder="Enter your API key"
            ),
            ConfigOption(
                key="confidence_threshold",
                type=ConfigType.FLOAT,
                label="Confidence Threshold",
                description="Minimum confidence score (0.0-1.0) to accept a match",
                default=0.6,
                min_value=0.0,
                max_value=1.0,
                step=0.05
            ),
            ConfigOption(
                key="timeout",
                type=ConfigType.INTEGER,
                label="Request Timeout",
                description="API request timeout in seconds",
                default=30,
                min_value=5,
                max_value=120,
                advanced=True
            ),
        ]
```

## Required Properties

### `source_name` (Required)

A unique string identifier for the scanner:

```python
@property
def source_name(self) -> str:
    return "MySource"  # Must be unique across all scanners
```

### `scan_level` (Required)

Defines what level the scanner operates at:

```python
from src.scanners.base_scanner import ScanLevel

@property
def scan_level(self) -> ScanLevel:
    # Choose one:
    return ScanLevel.FILE      # Per-file (e.g., nhentai for doujinshi)
    return ScanLevel.SERIES    # Per-series (e.g., AniList, ComicVine)
    return ScanLevel.LIBRARY   # Library-wide (rare use case)
```

## Required Methods

### `scan(query, **kwargs)` (Required)

The main scanning method:

```python
def scan(self, query: str, **kwargs) -> Tuple[Optional[ScanResult], List[ScanResult]]:
    """
    Args:
        query: Search query (filename or series name)
        **kwargs: Override configuration options
    
    Returns:
        Tuple of (best_match, all_candidates)
    """
    # Implementation here
    pass
```

### `get_config_schema()` (Recommended)

Declarative configuration for WebUI:

```python
def get_config_schema(self) -> List[ConfigOption]:
    """Returns list of ConfigOption objects for UI rendering"""
    return [
        ConfigOption(
            key="api_key",
            type=ConfigType.SECRET,
            label="API Key",
            description="Your API key",
            required=True
        ),
        # More options...
    ]
```

## ScanResult Object

The `ScanResult` dataclass holds scan results:

```python
from src.scanners.base_scanner import ScanResult

result = ScanResult(
    confidence=0.95,                    # Match confidence (0.0 to 1.0)
    source_id="12345",                  # ID from external source
    source_url="https://example.com/12345",  # URL to source entry
    metadata={                          # Extracted metadata dictionary
        'title': 'My Comic Title',
        'series': 'Series Name',
        'description': 'A description...',
        'writer': 'Author Name',
        'artist': 'Artist Name',
        'genre': 'Action, Adventure',
        'year': 2023,
        'characters': 'Character1, Character2',
        # ... more fields
    },
    tags=['genre:action', 'genre:adventure', 'artist:name'],  # Tag list
    extra_metadata={                    # Optional: UI display hints
        "items": [
            {"label": "Status", "value": "Completed", "display": "tag", "color": "green"}
        ]
    },
    raw_response=api_response           # Optional: raw API response for debugging
)
```

## Configuration Types

The `ConfigType` enum defines available input types:

| Type | Description | UI Control |
|------|-------------|------------|
| `STRING` | Plain text | Text input |
| `SECRET` | Sensitive data | Password field with show/hide |
| `INTEGER` | Whole numbers | Number input |
| `FLOAT` | Decimal numbers | Number input or slider |
| `BOOLEAN` | True/False | Toggle switch |
| `SELECT` | Single choice | Dropdown |
| `MULTI_SELECT` | Multiple choices | Checkboxes |

### ConfigOption Properties

```python
ConfigOption(
    key="option_key",           # Unique identifier (stored in config)
    type=ConfigType.STRING,     # Input type
    label="Display Label",      # Human-readable label
    description="Help text",    # Description shown to user
    required=False,             # Whether option is required
    default="default_value",    # Default value
    advanced=False,             # Show in "Advanced" section
    min_value=0,                # Minimum (INTEGER/FLOAT)
    max_value=100,              # Maximum (INTEGER/FLOAT)
    step=0.1,                   # Step increment (FLOAT sliders)
    options=["a", "b", "c"],    # Choices (SELECT/MULTI_SELECT)
    placeholder="Enter...",     # Placeholder text
    validation_pattern="^[A-Z]+$",  # Regex validation (STRING)
    validation_message="Must be uppercase"  # Validation error message
)
```

## Integration with Framework

### Automatic Discovery

Scanners are automatically discovered when the application starts:

1. The `discover_scanners()` function in `/src/scanners/scanner_manager.py` scans `/scanners/`
2. It looks for directories containing `*_scanner.py` or `scanner.py` files
3. It loads these modules and finds classes that extend `BaseScanner`
4. Found scanners are registered with the `ScannerManager`

### Using Your Scanner

Once discovered, your scanner can be used:

```python
from src.scanners.scanner_manager import get_manager, init_default_scanners

# Initialize all scanners
manager = init_default_scanners()

# Get your scanner
scanner = manager.get_scanner('MySource', config={'api_key': 'xxx'})

# Scan
result, candidates = scanner.scan('Batman')
```

## Best Practices

### 1. Rate Limiting

Always implement rate limiting to respect API quotas:

```python
import time

class MyScanner(BaseScanner):
    def __init__(self, config=None):
        super().__init__(config)
        self.rate_limit_delay = self.config.get('rate_limit_delay', 1.0)
        self.last_request_time = 0
    
    def _wait_for_rate_limit(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()
```

### 2. Error Handling

Use the provided exception classes:

```python
from src.scanners.base_scanner import (
    ScannerError,           # Base exception
    ScannerConfigError,     # Configuration problems
    ScannerAPIError,        # API communication issues
    ScannerRateLimitError   # Rate limit exceeded
)

def scan(self, query, **kwargs):
    try:
        response = self.api.search(query)
    except requests.Timeout:
        raise ScannerAPIError("API request timed out")
    except requests.HTTPError as e:
        if e.response.status_code == 429:
            raise ScannerRateLimitError("Rate limit exceeded")
        raise ScannerAPIError(f"API error: {e}")
```

### 3. Confidence Scoring

Implement meaningful confidence scores:

```python
from difflib import SequenceMatcher

def _calculate_confidence(self, query: str, result_title: str) -> float:
    """Calculate confidence based on title similarity"""
    # Normalize strings for comparison
    query_lower = query.lower().strip()
    title_lower = result_title.lower().strip()
    
    # Exact match
    if query_lower == title_lower:
        return 1.0
    
    # Substring match
    if query_lower in title_lower or title_lower in query_lower:
        return 0.9
    
    # Fuzzy matching
    ratio = SequenceMatcher(None, query_lower, title_lower).ratio()
    return ratio
```

### 4. Standalone Execution

Allow your scanner to run independently for testing:

```python
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='My Scanner')
    parser.add_argument('query', help='Search query')
    parser.add_argument('--api-key', help='API key')
    args = parser.parse_args()
    
    scanner = MyScanner({'api_key': args.api_key})
    result, candidates = scanner.scan(args.query)
    
    if result:
        print(f"Best Match: {result.metadata.get('title')}")
        print(f"Confidence: {result.confidence:.0%}")
    else:
        print("No match found")
```

## Minimal Scanner Template

Here's a minimal working scanner template:

```python
#!/usr/bin/env python3
"""Minimal Scanner Template"""

from typing import List, Tuple, Optional, Dict

try:
    from src.scanners.base_scanner import BaseScanner, ScanResult, ScanLevel
    from src.scanners.config_schema import ConfigOption, ConfigType
except ImportError:
    from abc import ABC
    BaseScanner = ABC
    ScanResult = None
    ScanLevel = None


class MinimalScanner(BaseScanner):
    """Minimal scanner implementation"""
    
    @property
    def source_name(self) -> str:
        return "Minimal"
    
    @property
    def scan_level(self) -> ScanLevel:
        return ScanLevel.SERIES
    
    def scan(self, query: str, **kwargs) -> Tuple[Optional[ScanResult], List[ScanResult]]:
        # Your implementation here
        result = ScanResult(
            confidence=1.0,
            source_id="1",
            source_url=f"https://example.com/1",
            metadata={'title': query, 'series': query}
        )
        return result, [result]
    
    def get_config_schema(self) -> List[ConfigOption]:
        return []


if __name__ == "__main__":
    scanner = MinimalScanner()
    result, _ = scanner.scan("Test Query")
    print(f"Result: {result.metadata}")
```

## Testing Your Scanner

1. **Standalone Test**: Run your scanner directly:
   ```bash
   cd /path/to/project
   python scanners/YourScanner/your_scanner.py "test query"
   ```

2. **Integration Test**: Test with the framework:
   ```python
   from src.scanners.scanner_manager import init_default_scanners
   
   manager = init_default_scanners()
   print(f"Available scanners: {manager.get_available_scanners()}")
   
   scanner = manager.get_scanner('YourScanner')
   result, _ = scanner.scan('test')
   ```

3. **Demo Script**: Use the provided demo:
   ```bash
   python src/scanners/demo_scanners.py
   ```

## See Also

- `/src/scanners/base_scanner.py` - Base classes and interfaces
- `/src/scanners/config_schema.py` - Configuration schema types
- `/scanners/AniList/anilist_scanner.py` - Complete example (GraphQL API)
- `/scanners/metron/metron_scanner.py` - Complete example (REST API with auth)
- `/docs/scanners/README.md` - Scanner system overview
- `/docs/METADATA_SCANNERS.md` - Framework documentation
