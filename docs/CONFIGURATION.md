# Configuration Documentation

## Overview

Kottlib uses a **minimal bootstrap configuration** approach:
- **config.yml**: Contains only essential bootstrap settings (server + database path)
- **Database**: Stores all runtime settings (features, storage, libraries)

This design allows:
- Easy deployment with sensible defaults
- Settings changes via WebUI without file editing
- Clear separation between bootstrap and runtime configuration

---

## Configuration Architecture

### Bootstrap Settings (config.yml)

The configuration file contains **only** settings needed before the database can be accessed:

```yaml
server:
  host: "0.0.0.0"
  port: 8081
  log_level: "info"
  cors_origins:
    - "*"

database:
  path: null  # null = auto-detect platform default
```

**Why minimal?**
- These settings are needed to start the server and connect to the database
- Changes require a server restart anyway
- Environment variables can override these for Docker/production

### Runtime Settings (Database)

All other settings are stored in the database `settings` table:

**Storage Settings:**
- `storage.covers_dir` - Cover thumbnails directory
- `storage.cache_dir` - Cache directory

**Feature Flags:**
- `features.legacy_api` - Enable YACReader-compatible API
- `features.modern_api` - Enable modern JSON REST API
- `features.reading_progress` - Track reading progress
- `features.series_detection` - Auto-detect series
- `features.collections` - Enable user collections
- `features.auto_thumbnails` - Auto-generate thumbnails
- `features.ignore_series_metadata` - Ignore series metadata from files

**Database Settings:**
- `database.echo` - Log SQL queries (debugging)

**Libraries:**
- Stored in `libraries` table (managed via WebUI/API)

---

## Config File Locations

Configuration files are searched in the following order:

1. **Current Directory:** `./config.yml`
2. **Linux:** `~/.config/kottlib/config.yml`
3. **macOS:** `~/Library/Application Support/Kottlib/config.yml`
4. **Windows:** `%APPDATA%/Kottlib/config.yml`

If no config file exists, a default one is created on first run.

---

## Bootstrap Configuration Reference

### ServerConfig

Server binding and runtime configuration.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `host` | str | "0.0.0.0" | IP address to bind (0.0.0.0 = all interfaces) |
| `port` | int | 8081 | HTTP port number |
| `reload` | bool | False | Enable Uvicorn auto-reload (development only) |
| `log_level` | str | "info" | Logging level: debug, info, warning, error |
| `cors_origins` | List[str] | ["*"] | Allowed CORS origins |

### DatabaseConfig

Database connection settings.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `path` | str | None | SQLite database path (uses platform default if None) |

**Default Database Paths:**
- Linux: `~/.local/share/kottlib/kottlib.db`
- macOS: `~/Library/Application Support/Kottlib/kottlib.db`
- Windows: `%LOCALAPPDATA%/Kottlib/kottlib.db`

---

## Environment Variables

Bootstrap settings can be overridden via environment variables:

| Variable | Config Path | Description |
|----------|-------------|-------------|
| `KOTTLIB_HOST` | `server.host` | Server bind address |
| `KOTTLIB_PORT` | `server.port` | Server port number |
| `KOTTLIB_DB_PATH` | `database.path` | SQLite database path |
| `KOTTLIB_LOG_LEVEL` | `server.log_level` | Logging level |

### Example

```bash
export KOTTLIB_HOST=127.0.0.1
export KOTTLIB_PORT=8080
export KOTTLIB_DB_PATH=/data/kottlib.db
export KOTTLIB_LOG_LEVEL=DEBUG
```

---

## First Run Behavior

On first run with no configuration:

1. **Config file created** with bootstrap defaults at platform-appropriate location
2. **Database created** at platform-appropriate location  
3. **Default settings** initialized in database:
   - All features enabled
   - Auto-detect storage paths
   - No libraries configured

4. **WebUI accessible** at http://localhost:8081
   - Add libraries via Settings page
   - Configure features as needed
   - Settings saved to database

---

## Managing Settings

### Via WebUI (Recommended)

1. Navigate to Settings page
2. Modify settings as needed
3. Settings are automatically saved to the database
4. **Note:** Server/database changes require restart

### Via API

**GET /api/v2/config**

Get current configuration:

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8081,
    "log_level": "info",
    "cors_origins": ["*"]
  },
  "database": {
    "path": "/path/to/kottlib.db"
  },
  "storage": {
    "covers_dir": null,
    "cache_dir": null
  },
  "features": {
    "legacy_api": true,
    "modern_api": true,
    "reading_progress": true,
    "series_detection": true,
    "collections": true,
    "auto_thumbnails": true,
    "ignore_series_metadata": true
  }
}
```

**PUT /api/v2/config**

Update configuration:

```json
{
  "features": {
    "ignore_series_metadata": false
  },
  "storage": {
    "covers_dir": "/custom/path/covers"
  }
}
```

Response indicates if restart is required:

```json
{
  "success": true,
  "message": "Configuration updated successfully",
  "restart_required": false
}
```

---

## Migration from Legacy Config

If you have an existing `config.yml` with libraries, storage, or feature settings:

### Automatic Migration

On first startup with legacy config:

1. Bootstrap settings (server/database) are **kept** in config.yml
2. Libraries are **migrated** to database
3. Storage/features settings are **ignored** (database defaults used)
4. Legacy sections can be safely removed from config.yml

### Manual Migration

If you want to preserve custom storage/feature settings:

1. Note your custom settings from old config.yml
2. Start server (automatic migration occurs)
3. Configure settings via WebUI Settings page
4. Clean up config.yml to remove legacy sections

**Example Legacy Config:**

```yaml
# OLD - Will be migrated
storage:
  covers_dir: "/custom/covers"
features:
  legacy_api: false
libraries:
  - name: "Comics"
    path: "/mnt/comics"
```

**After Migration:**

Libraries moved to database → Manage via WebUI
Storage/features → Set via Settings page
config.yml → Only contains server/database

---

## Docker Configuration

For Docker deployments, use environment variables for bootstrap settings:

```dockerfile
ENV KOTTLIB_HOST=0.0.0.0
ENV KOTTLIB_PORT=8081
ENV KOTTLIB_DB_PATH=/data/kottlib.db
ENV KOTTLIB_LOG_LEVEL=INFO
```

Mount volumes for persistence:

```bash
docker run \
  -v ./data:/data \
  -p 8081:8081 \
  -e KOTTLIB_DB_PATH=/data/kottlib.db \
  kottlib
```

All other settings managed via WebUI after container starts.

---

## Feature Flags Details

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

## Storage Paths

### Default Locations

If not specified in database settings:

**covers_dir:** `{data_dir}/covers/`
**cache_dir:** `{data_dir}/cache/`

Where `{data_dir}` is:
- Linux: `~/.local/share/kottlib/`
- macOS: `~/Library/Application Support/Kottlib/`
- Windows: `%LOCALAPPDATA%/Kottlib/`

### Custom Paths

Set via Settings page or API:

```json
{
  "storage": {
    "covers_dir": "/mnt/storage/covers",
    "cache_dir": "/tmp/kottlib-cache"
  }
}
```

---

## Library Management

Libraries are managed entirely through the database.

### Add Library (via WebUI)

1. Go to Settings → Libraries
2. Click "Add Library"
3. Specify name and path
4. Configure scanner settings
5. Save

### Add Library (via API)

```http
POST /api/v2/libraries
Content-Type: application/json

{
  "name": "Comics",
  "path": "/mnt/comics",
  "settings": {
    "auto_scan": true,
    "scan_on_startup": false
  }
}
```

Libraries are stored in the `libraries` database table, **not** in config.yml.

---

## Troubleshooting

### Config file not updating

**Issue:** Changes via WebUI don't update config.yml

**Solution:** This is expected! Only server/database settings are saved to config.yml. Storage, features, and libraries are in the database.

### Settings lost after restart

**Issue:** Settings reset after server restart

**Solution:** Check database file permissions. Settings are in the database, not the config file.

### Migration not working

**Issue:** Legacy libraries not appearing after migration

**Solution:** Check server logs for migration messages. Libraries should be created in database on first startup.

---

## Advanced Configuration

### Custom Database Location

```yaml
database:
  path: "/custom/path/kottlib.db"
```

Or via environment:

```bash
KOTTLIB_DB_PATH=/custom/path/kottlib.db
```

### Production CORS Settings

```yaml
server:
  cors_origins:
    - "https://yourdomain.com"
    - "https://app.yourdomain.com"
```

### Debug Mode

```yaml
server:
  log_level: "debug"
```

And set database echo via Settings page:
- `database.echo = true` (logs all SQL queries)

---

## Summary

**What goes where:**

| Setting | Location | Change Method | Restart Required |
|---------|----------|---------------|------------------|
| Server host/port | config.yml | Edit file or env var | Yes |
| Log level | config.yml | Edit file or env var | Yes |
| CORS origins | config.yml | Edit file or env var | Yes |
| Database path | config.yml | Edit file or env var | Yes |
| Storage paths | Database | WebUI/API | No |
| Feature flags | Database | WebUI/API | No |
| Database echo | Database | WebUI/API | No |
| Libraries | Database | WebUI/API | No |

**Best Practices:**
- Use config.yml for deployment-specific settings (host, port, db path)
- Use database (via WebUI) for runtime settings (features, storage)
- Use environment variables for Docker/production deployments
- Backup both config.yml and database file for disaster recovery
