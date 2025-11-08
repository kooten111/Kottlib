# Configuration System Added! 🎉

**Enhancement to Phase 1 - Configuration Management**

## What Was Added

You correctly identified that using command-line arguments for library management wasn't ideal for production use. I've added a comprehensive **YAML-based configuration system**!

### New Features

1. **Configuration File** (`config.yml`)
   - Persistent library definitions
   - Server settings (host, port, logging)
   - Database and storage paths
   - Feature flags

2. **CLI Management Tool** (`yaclib-cli.py`)
   - Initialize config: `./yaclib-cli.py config init`
   - Add libraries: `./yaclib-cli.py library add NAME PATH`
   - Scan libraries: `./yaclib-cli.py library scan NAME`
   - Start server: `./yaclib-cli.py server start`
   - View config: `./yaclib-cli.py config show`

3. **Configuration Module** (`src/config.py`)
   - YAML parsing
   - Environment variable overrides
   - Auto-detection of config location
   - Validation and defaults

4. **Example Config** (`config.example.yml`)
   - Well-documented example
   - Copy and customize

5. **Documentation** (`CONFIGURATION.md`)
   - Complete configuration guide
   - Examples and workflows
   - Troubleshooting

## Files Created

```
yaclib-enhanced/
├── src/
│   └── config.py                 ✨ NEW - Config management
├── yaclib-cli.py                 ✨ NEW - CLI tool
├── config.example.yml            ✨ NEW - Example config
├── CONFIGURATION.md              ✨ NEW - Config guide
└── CONFIGURATION_ADDED.md        ✨ NEW - This file
```

## Files Modified

- `src/api/main.py` - Now uses config system
- `requirements.txt` - Added pyyaml
- `QUICKSTART.md` - Updated with config instructions

## Usage Example

### Before (Phase 1)
```bash
# Had to specify path every time
python examples/scan_library.py /mnt/Comics "Comics"
python examples/scan_library.py /mnt/Manga "Manga"

# Server used hardcoded defaults
python -m uvicorn src.api.main:app --port 8081
```

### After (With Config)
```bash
# One-time setup
./yaclib-cli.py config init
./yaclib-cli.py library add "Comics" /mnt/Comics
./yaclib-cli.py library add "Manga" /mnt/Manga

# Scan anytime by name
./yaclib-cli.py library scan Comics
./yaclib-cli.py library scan Manga

# Start server with all settings from config
./yaclib-cli.py server start
```

## Configuration Example

**config.yml:**
```yaml
server:
  host: "0.0.0.0"
  port: 8081
  log_level: "info"

libraries:
  - name: "Comics"
    path: "/mnt/Comics"
    auto_scan: true
    settings:
      default_reading_direction: "ltr"

  - name: "Manga"
    path: "/mnt/Manga"
    auto_scan: true
    settings:
      default_reading_direction: "rtl"
```

## CLI Tool Commands

### Configuration Management
```bash
./yaclib-cli.py config init      # Create config.yml
./yaclib-cli.py config show      # Display current config
./yaclib-cli.py config edit      # Edit in text editor
```

### Library Management
```bash
./yaclib-cli.py library add "Name" /path    # Add to config
./yaclib-cli.py library list                # List from DB
./yaclib-cli.py library scan "Name"         # Scan by name
```

### Server Management
```bash
./yaclib-cli.py server start     # Start with config
./yaclib-cli.py server info      # Show server info
```

## Benefits

✅ **Persistent** - Libraries defined once, used forever
✅ **Clean** - No more long command lines
✅ **Manageable** - Easy to add/remove libraries
✅ **Flexible** - Environment variable overrides
✅ **Production-ready** - Proper configuration system
✅ **Version-controllable** - Config file can be committed
✅ **Well-documented** - Complete configuration guide

## Configuration Locations

Config file searched in order:
1. `./config.yml` (current directory)
2. `~/.config/yaclib/config.yml` (user config)
3. `/etc/yaclib/config.yml` (system config, Linux only)

**Tip:** For development, keep `config.yml` in project root.

## Environment Variable Overrides

```bash
export YACLIB_HOST="127.0.0.1"
export YACLIB_PORT="8082"
export YACLIB_DB_PATH="/custom/db.db"

./yaclib-cli.py server start
```

## Migration Path

If you used Phase 1 examples:

1. **Create config:**
   ```bash
   ./yaclib-cli.py config init
   ```

2. **Add existing libraries:**
   ```bash
   ./yaclib-cli.py library add "Comics" /mnt/Comics
   ```

3. **Use CLI going forward:**
   ```bash
   ./yaclib-cli.py library scan Comics
   ./yaclib-cli.py server start
   ```

**Note:** Old example scripts still work, but config is now preferred.

## Web UI Integration (Future)

In Phase 3, the web UI will:
- Read from `config.yml`
- Provide visual library management
- Add/edit/remove libraries via forms
- Save changes back to `config.yml`

Same config file, multiple interfaces!

## Quick Start (Updated)

```bash
# 1. Initialize config
./yaclib-cli.py config init

# 2. Edit config.yml to add your libraries
nano config.yml

# 3. Scan your libraries
./yaclib-cli.py library scan Comics
./yaclib-cli.py library scan Manga

# 4. Start server
./yaclib-cli.py server start
```

That's it! Visit http://localhost:8081/docs

## What This Solves

Your original concern:
> "setting the actual libraries should be done in a config file and/or through the web interface"

✅ **Config file** - Done! Full YAML configuration system
⏳ **Web interface** - Phase 3 (will read/write same config.yml)

The test scripts (`test_comic_loader.py`) are still command-line based because they're meant for testing individual files, not managing libraries. For library management, use the config system!

## Documentation

- **[CONFIGURATION.md](CONFIGURATION.md)** - Complete configuration guide
- **[QUICKSTART.md](QUICKSTART.md)** - Updated with config usage
- **[config.example.yml](config.example.yml)** - Well-documented example

## Status

✅ **Phase 1 Complete** - All core functionality
✅ **Configuration Added** - Production-ready config system
⏳ **Phase 2 Next** - Mobile UX improvements

**You now have a professional, configurable comic server!**
