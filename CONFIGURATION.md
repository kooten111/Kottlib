# YACLib Enhanced - Configuration Guide

Complete guide to configuring YACLib Enhanced.

## Overview

YACLib Enhanced uses a **YAML configuration file** for managing server settings and libraries. This approach is:

- ✅ **Persistent** - Settings survive server restarts
- ✅ **Version controllable** - Can be committed to git
- ✅ **Easy to edit** - Simple YAML format
- ✅ **Centralized** - All settings in one place

The web UI will also provide configuration management (Phase 3).

## Quick Start

### 1. Initialize Configuration

```bash
./yaclib-cli.py config init
```

This creates `config.yml` in the current directory with example settings.

### 2. Add Your Libraries

Edit `config.yml` and add your comic libraries:

```yaml
libraries:
  - name: "Comics"
    path: "/mnt/Comics"
    auto_scan: true
    scan_on_startup: false

  - name: "Manga"
    path: "/mnt/Manga"
    auto_scan: true
    scan_on_startup: false
    settings:
      default_reading_direction: "rtl"
```

### 3. Scan Libraries

```bash
./yaclib-cli.py library scan Comics
./yaclib-cli.py library scan Manga
```

### 4. Start Server

```bash
./yaclib-cli.py server start
```

Done! Your libraries are configured and the server is running.

## Configuration File Location

YACLib Enhanced looks for `config.yml` in this order:

1. **Current directory** - `./config.yml`
2. **User config directory:**
   - Linux: `~/.config/yaclib/config.yml`
   - macOS: `~/Library/Application Support/YACLib/config.yml`
   - Windows: `%APPDATA%/YACLib/config.yml`
3. **System config** (Linux only): `/etc/yaclib/config.yml`

**Tip:** For development, keep `config.yml` in the project root.

## Configuration Structure

### Complete Example

```yaml
# Server settings
server:
  host: "0.0.0.0"
  port: 8081
  reload: false
  log_level: "info"
  cors_origins:
    - "*"

# Database settings
database:
  path: null              # null = auto-detect
  echo: false

# Storage settings
storage:
  covers_dir: null        # null = auto-detect
  cache_dir: null

# Feature flags
features:
  legacy_api: true
  modern_api: true
  reading_progress: true
  series_detection: true
  collections: true
  auto_thumbnails: true

# Library definitions
libraries:
  - name: "Comics"
    path: "/mnt/Comics"
    auto_scan: true
    scan_on_startup: false
    settings:
      sort_mode: "folders_first"
      default_reading_direction: "ltr"
```

## Configuration Sections

### Server Settings

```yaml
server:
  host: "0.0.0.0"       # Listen address (0.0.0.0 = all interfaces)
  port: 8081            # Server port
  reload: false         # Auto-reload on code changes (dev only)
  log_level: "info"     # debug, info, warning, error
  cors_origins:         # CORS allowed origins
    - "*"               # * = allow all (use specific domains in prod)
```

**Production recommendations:**
- Set `host` to `127.0.0.1` if using reverse proxy
- Use specific domains in `cors_origins`
- Set `reload: false` for production

### Database Settings

```yaml
database:
  path: null            # Database file path (null = auto-detect)
  echo: false           # Log all SQL queries (debugging)
```

**Auto-detected paths:**
- Linux: `~/.local/share/yaclib/yaclib.db`
- macOS: `~/Library/Application Support/YACLib/yaclib.db`
- Windows: `%APPDATA%/YACLib/yaclib.db`

**Custom path example:**
```yaml
database:
  path: "/var/lib/yaclib/database.db"
```

### Storage Settings

```yaml
storage:
  covers_dir: null      # Thumbnail storage (null = next to database)
  cache_dir: null       # Page cache (optional, future use)
```

### Feature Flags

Enable or disable features:

```yaml
features:
  legacy_api: true          # YACReader-compatible API
  modern_api: true          # Modern JSON REST API
  reading_progress: true    # Track reading progress
  series_detection: true    # Auto-detect series
  collections: true         # User collections
  auto_thumbnails: true     # Auto-generate thumbnails
```

**Use cases:**
- Disable `legacy_api` if you only use web UI
- Disable `auto_thumbnails` to generate manually
- Enable/disable features for testing

### Library Definitions

The most important section - your comic libraries:

```yaml
libraries:
  - name: "Display Name"
    path: "/absolute/path/to/comics"
    auto_scan: true
    scan_on_startup: false
    settings:
      sort_mode: "folders_first"
      default_reading_direction: "ltr"
```

**Fields:**
- `name` - Display name (shown in UI)
- `path` - Absolute path to library root
- `auto_scan` - Monitor for changes (future feature)
- `scan_on_startup` - Scan immediately on server start
- `settings` - Library-specific settings

**Example: Multiple libraries**
```yaml
libraries:
  # Western comics
  - name: "Marvel"
    path: "/mnt/Comics/Marvel"
    auto_scan: true
    settings:
      default_reading_direction: "ltr"

  # Manga
  - name: "Manga"
    path: "/mnt/Comics/Manga"
    auto_scan: true
    settings:
      default_reading_direction: "rtl"

  # European comics
  - name: "BD"
    path: "/mnt/Comics/BD"
    auto_scan: true
```

## CLI Management Tool

The `yaclib-cli.py` tool provides easy configuration management:

### Config Commands

```bash
# Create example config
./yaclib-cli.py config init

# Show current config
./yaclib-cli.py config show

# Edit config file
./yaclib-cli.py config edit
```

### Library Commands

```bash
# Add library to config
./yaclib-cli.py library add "Comics" /mnt/Comics

# List libraries in database
./yaclib-cli.py library list

# Scan a library
./yaclib-cli.py library scan Comics
```

### Server Commands

```bash
# Start server with config
./yaclib-cli.py server start

# Show server info
./yaclib-cli.py server info
```

## Environment Variables

Override configuration with environment variables:

```bash
# Server settings
export YACLIB_HOST="127.0.0.1"
export YACLIB_PORT="8082"
export YACLIB_LOG_LEVEL="debug"

# Database
export YACLIB_DB_PATH="/custom/path/yaclib.db"

# Start server
./yaclib-cli.py server start
```

**Priority:** Environment variables > Config file > Defaults

## Workflow Examples

### First-Time Setup

```bash
# 1. Create config
./yaclib-cli.py config init

# 2. Edit config.yml to add your libraries
nano config.yml

# 3. Scan libraries
./yaclib-cli.py library scan Comics
./yaclib-cli.py library scan Manga

# 4. Start server
./yaclib-cli.py server start
```

### Adding a New Library

**Option 1: Via CLI**
```bash
./yaclib-cli.py library add "New Comics" /path/to/comics
./yaclib-cli.py library scan "New Comics"
```

**Option 2: Via Config File**
```bash
# Edit config.yml
nano config.yml

# Add:
# libraries:
#   - name: "New Comics"
#     path: "/path/to/comics"

# Scan
./yaclib-cli.py library scan "New Comics"
```

### Development Setup

```yaml
server:
  host: "127.0.0.1"     # Local only
  port: 8081
  reload: true          # Auto-reload
  log_level: "debug"    # Verbose logging

database:
  echo: true            # Log SQL queries
```

### Production Setup

```yaml
server:
  host: "0.0.0.0"
  port: 8081
  reload: false
  log_level: "info"
  cors_origins:
    - "https://comics.example.com"

database:
  path: "/var/lib/yaclib/yaclib.db"
  echo: false

libraries:
  - name: "Comics"
    path: "/data/comics"
    scan_on_startup: true
```

## Migration from Phase 1 Examples

If you used the Phase 1 example scripts (`scan_library.py`), you can now:

1. **Create config** with your libraries
2. **Use CLI tool** instead of direct scripts
3. **Libraries persist** in config

**Before (Phase 1):**
```bash
python examples/scan_library.py /mnt/Comics "Comics"
```

**After (with config):**
```bash
# One-time: Add to config
./yaclib-cli.py library add "Comics" /mnt/Comics

# Scan anytime
./yaclib-cli.py library scan Comics

# Or add to config.yml and scan all at once
```

## Validation

Check your configuration:

```bash
# Show parsed config
./yaclib-cli.py config show

# Verify libraries exist
./yaclib-cli.py library list

# Check server settings
./yaclib-cli.py server info
```

## Troubleshooting

### Config file not found

```bash
# Create one
./yaclib-cli.py config init

# Or check location
./yaclib-cli.py config show
```

### Library path doesn't exist

Make sure paths in `config.yml` are:
- Absolute paths (not relative)
- Accessible to the user running the server
- Spelled correctly

```bash
# Verify path
ls -la /mnt/Comics
```

### Changes not taking effect

Restart the server after config changes:
```bash
# Stop server (Ctrl+C)
# Start again
./yaclib-cli.py server start
```

### YAML syntax errors

Common YAML mistakes:
```yaml
# ❌ Wrong - no quotes on paths with spaces
path: /mnt/My Comics

# ✅ Correct
path: "/mnt/My Comics"

# ❌ Wrong - inconsistent indentation
libraries:
 - name: "Comics"
   path: "/mnt/Comics"

# ✅ Correct - 2 spaces
libraries:
  - name: "Comics"
    path: "/mnt/Comics"
```

## Future: Web UI Configuration

In Phase 3, the web UI will provide:
- Visual library management
- Add/remove libraries via UI
- Edit settings with forms
- Real-time validation
- Preview changes before saving

The web UI will read/write the same `config.yml` file.

## Best Practices

1. **Version Control:** Commit `config.yml` (but not with sensitive paths)
2. **Comments:** Add comments to document your setup
3. **Backup:** Back up config before major changes
4. **Environment Variables:** Use for deployment-specific overrides
5. **Validation:** Run `config show` after changes

## Summary

- ✅ Configuration is in `config.yml`
- ✅ Use `yaclib-cli.py` for easy management
- ✅ Libraries are defined once, persist forever
- ✅ No more command-line arguments
- ✅ Clean, maintainable, version-controllable

**Next:** Use the CLI tool to manage your libraries!
