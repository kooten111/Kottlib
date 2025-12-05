# Configuration Documentation

## Overview

Kottlib uses a layered configuration system with support for YAML files and environment variables.

## Configuration Sources (Priority Order)

1. **Environment Variables** (highest priority)
2. **Config File** (`config.yml`)
3. **Default Values** (lowest priority)

---

## Config File Locations

Configuration files are searched in the following order:

1. **Current Directory:** `./config.yml`
2. **Linux:** `~/.config/yaclib/config.yml`
3. **macOS:** `~/Library/Application Support/YACLib/config.yml`
4. **Windows:** `%APPDATA%/YACLib/config.yml`

---

## Data Classes (`src/config.py`)

### ServerConfig

Server binding and runtime configuration.

```python
@dataclass
class ServerConfig:
    host: str = "0.0.0.0"         # Bind address
    port: int = 8081              # Server port
    reload: bool = False          # Auto-reload on file changes
    log_level: str = "INFO"       # Logging level
    cors_origins: List[str] = None  # CORS allowed origins
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `host` | str | "0.0.0.0" | IP address to bind (0.0.0.0 = all interfaces) |
| `port` | int | 8081 | HTTP port number |
| `reload` | bool | False | Enable Uvicorn auto-reload |
| `log_level` | str | "INFO" | DEBUG, INFO, WARNING, ERROR |
| `cors_origins` | List[str] | None | Allowed CORS origins (None = allow all) |

---

### DatabaseConfig

Database connection settings.

```python
@dataclass
class DatabaseConfig:
    path: str = None              # SQLite database path
    echo: bool = False            # SQLAlchemy SQL logging
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `path` | str | None | SQLite database path (uses platform default if None) |
| `echo` | bool | False | Log all SQL statements (debugging) |

**Default Paths:**
- Linux: `~/.local/share/yaclib/yaclib.db`
- macOS: `~/Library/Application Support/YACLib/yaclib.db`
- Windows: `%LOCALAPPDATA%/YACLib/yaclib.db`

---

### StorageConfig

File storage paths.

```python
@dataclass
class StorageConfig:
    covers_dir: str = None        # Cover thumbnails directory
    cache_dir: str = None         # Cache directory
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `covers_dir` | str | None | Cover thumbnails (default: `{data_dir}/covers/`) |
| `cache_dir` | str | None | General cache (default: `{data_dir}/cache/`) |

---

### LibraryDefinition

Library configuration for auto-creation.

```python
@dataclass
class LibraryDefinition:
    name: str                     # Library display name
    path: str                     # Filesystem path
    auto_scan: bool = True        # Enable auto-scanning
    scan_on_startup: bool = True  # Scan when server starts
    settings: Dict = None         # Library-specific settings
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | str | Required | Library display name |
| `path` | str | Required | Full path to comic directory |
| `auto_scan` | bool | True | Enable periodic scanning |
| `scan_on_startup` | bool | True | Scan when server starts |
| `settings` | Dict | None | Library-specific settings (scanner config, etc.) |

---

### FeaturesConfig

Feature flags for enabling/disabling functionality.

```python
@dataclass
class FeaturesConfig:
    legacy_api: bool = True           # Enable legacy v1 API
    modern_api: bool = True           # Enable modern REST API
    reading_progress: bool = True     # Track reading progress
    series_detection: bool = True     # Auto-detect series from folder structure
    collections: bool = True          # Enable user collections
    auto_thumbnails: bool = True      # Generate thumbnails automatically
    ignore_series_metadata: bool = True  # Ignore ComicInfo.xml series field
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `legacy_api` | bool | True | Enable `/library/*` endpoints for YACReader |
| `modern_api` | bool | True | Enable modern JSON APIs |
| `reading_progress` | bool | True | Track per-user reading progress |
| `series_detection` | bool | True | Auto-detect series from folder structure |
| `collections` | bool | True | Enable user collections feature |
| `auto_thumbnails` | bool | True | Generate cover thumbnails during scan |
| `ignore_series_metadata` | bool | True | Use folder-based series instead of ComicInfo.xml |

---

### Config

Root configuration aggregating all sections.

```python
@dataclass
class Config:
    server: ServerConfig = None
    database: DatabaseConfig = None
    storage: StorageConfig = None
    libraries: List[LibraryDefinition] = None
    features: FeaturesConfig = None
```

---

## Environment Variables

All configuration can be overridden via environment variables.

| Variable | Config Path | Description |
|----------|-------------|-------------|
| `YACLIB_HOST` | `server.host` | Server bind address |
| `YACLIB_PORT` | `server.port` | Server port number |
| `YACLIB_DB_PATH` | `database.path` | SQLite database path |
| `YACLIB_LOG_LEVEL` | `server.log_level` | Logging level |
| `YACLIB_RELOAD` | `server.reload` | Auto-reload (true/false) |
| `YACLIB_CORS_ORIGINS` | `server.cors_origins` | Comma-separated origins |

### Example

```bash
export YACLIB_HOST=127.0.0.1
export YACLIB_PORT=8080
export YACLIB_DB_PATH=/data/yaclib.db
export YACLIB_LOG_LEVEL=DEBUG
```

---

## Config File Example

`config.yml`:

```yaml
server:
  host: "0.0.0.0"
  port: 8081
  reload: false
  log_level: "INFO"
  cors_origins:
    - "http://localhost:5173"
    - "http://localhost:3000"

database:
  path: "/data/yaclib/yaclib.db"
  echo: false

storage:
  covers_dir: "/data/yaclib/covers"
  cache_dir: "/data/yaclib/cache"

libraries:
  - name: "Manga"
    path: "/comics/manga"
    auto_scan: true
    scan_on_startup: true
    settings:
      scanner:
        primary_scanner: "AniList"
        confidence_threshold: 0.6

  - name: "Western Comics"
    path: "/comics/western"
    auto_scan: true
    settings:
      scanner:
        primary_scanner: "Comic Vine"
        scanner_configs:
          "Comic Vine":
            api_key: "your-api-key-here"

features:
  legacy_api: true
  modern_api: true
  reading_progress: true
  series_detection: true
  collections: true
  auto_thumbnails: true
  ignore_series_metadata: true
```

---

## Configuration Functions

### get_config_path

Get path to config file.

```python
def get_config_path() -> Path
```

**Returns:** Path to config file, or None if not found

**Search Order:**
1. `./config.yml`
2. Platform-specific config directory

---

### load_config

Load configuration from file.

```python
def load_config(config_path: Optional[Path] = None) -> Config
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `config_path` | Path | No | None | Config file path (auto-detect if None) |

**Returns:** Config instance

**Behavior:**
1. Load from file if exists
2. Apply defaults for missing values
3. Apply environment variable overrides

---

### save_config

Save configuration to file.

```python
def save_config(config: Config, config_path: Optional[Path] = None)
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `config` | Config | Yes | - | Configuration to save |
| `config_path` | Path | No | None | Output path (uses default if None) |

---

### apply_env_overrides

Apply environment variable overrides to config.

```python
def apply_env_overrides(config: Config) -> Config
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `config` | Config | Yes | Configuration to modify |

**Returns:** Modified Config instance

---

### get_config

Get global configuration singleton.

```python
def get_config() -> Config
```

**Returns:** Global Config instance

**Note:** Loads config on first call, caches for subsequent calls.

---

### reload_config

Reload configuration from file.

```python
def reload_config()
```

**Side Effects:**
- Clears cached config
- Reloads from file on next `get_config()` call

---

## Library-Specific Settings

Each library can have custom settings stored in `settings` JSON:

```python
{
    "scanner": {
        "primary_scanner": "AniList",
        "fallback_scanners": ["MangaDex"],
        "confidence_threshold": 0.6,
        "fallback_threshold": 0.7,
        "scanner_configs": {
            "Comic Vine": {
                "api_key": "..."
            }
        }
    },
    "scanner_progress": {
        "in_progress": false,
        "processed": 0,
        "total": 0
    },
    "file_scan_progress": {
        "in_progress": false,
        "current": 0,
        "total": 0
    }
}
```

---

## Feature Flag Details

### ignore_series_metadata

When `true` (default):
- Uses folder structure to determine series name
- Ignores `<Series>` tag from ComicInfo.xml
- Better for folder-organized libraries

When `false`:
- Prefers ComicInfo.xml `<Series>` metadata
- Falls back to folder name if no metadata

### series_detection

When `true` (default):
- Analyzes folder structure during scan
- Classifies folders as: simple, nested, unpacked
- Applies series/group metadata accordingly

When `false`:
- No automatic series detection
- Series must come from ComicInfo.xml or scanners

---

## Docker Configuration

For Docker deployments, use environment variables:

```dockerfile
ENV YACLIB_HOST=0.0.0.0
ENV YACLIB_PORT=8081
ENV YACLIB_DB_PATH=/data/yaclib.db
ENV YACLIB_LOG_LEVEL=INFO
```

Or mount a config file:

```bash
docker run -v ./config.yml:/app/config.yml yaclib
```

---

## Configuration API

The server exposes configuration via REST API:

### GET /api/v2/config

Get current configuration (excluding secrets).

**Response:**
```json
{
    "server": {
        "host": "0.0.0.0",
        "port": 8081,
        "log_level": "INFO"
    },
    "features": {
        "legacy_api": true,
        "modern_api": true,
        "reading_progress": true
    }
}
```

### PUT /api/v2/config

Update configuration.

**Request Body:**
```json
{
    "features": {
        "ignore_series_metadata": false
    }
}
```

**Note:** Some settings require server restart to take effect.
