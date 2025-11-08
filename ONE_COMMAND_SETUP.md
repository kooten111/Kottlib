# One-Command Setup - Complete! 🎉

**YACLib Enhanced now has the simplest possible setup.**

## The Vision

You wanted:
> "one config file and one launcher. No dependency on a bunch of commands"

**Done!** ✅

## What You Get

### Single Launcher: `./yaclib.py`

```bash
./yaclib.py
```

That's it. One command handles **everything**:

1. ✅ Checks Python version
2. ✅ Installs dependencies automatically
3. ✅ Interactive first-time setup
4. ✅ Creates config file
5. ✅ Helps you add libraries
6. ✅ Scans comics (optional)
7. ✅ Starts the server

### Single Config File: `config.yml`

**One file** contains all settings:
- Server configuration (host, port, logging)
- Library definitions
- Feature flags
- Database paths

**That's it.** No scattered config files, no environment variables required.

## User Experience

### New User

```bash
# Download
git clone repo
cd yaclib-enhanced

# Run
./yaclib.py

# Interactive setup walks you through everything
# Server starts automatically
```

### Returning User

```bash
# Just run it
./yaclib.py

# Uses saved config from last time
```

## What About All Those Other Commands?

They still exist, but they're **optional advanced tools**:

- `yaclib-cli.py` - For power users who want CLI management
- `examples/*.py` - For testing and development
- Scripts in `/examples` - For manual scanning/testing

**Most users will never need them.**

## Configuration Philosophy

### One File: `config.yml`

```yaml
# Everything in one place
server:
  host: "0.0.0.0"
  port: 8081

libraries:
  - name: "Comics"
    path: "/mnt/Comics"

  - name: "Manga"
    path: "/mnt/Manga"
    settings:
      default_reading_direction: "rtl"
```

### Three Ways to Manage

1. **Launcher (easiest)** - Interactive setup on first run
2. **Web UI (coming in Phase 3)** - Visual management
3. **Text editor** - Edit `config.yml` directly

Pick whatever works for you!

## Web Interface (Phase 3)

When the web UI is ready, you'll be able to:

- ✅ Add/remove libraries through the UI
- ✅ Scan for new comics
- ✅ Edit metadata
- ✅ Manage all settings visually

All reading/writing the **same `config.yml` file**.

No database-only config. No hidden settings. One file.

## Benefits of This Approach

✅ **Simple** - New users: just run `./yaclib.py`
✅ **Discoverable** - All settings in one readable file
✅ **Version-controllable** - Commit `config.yml` to git
✅ **Portable** - Copy config file to new machine
✅ **Transparent** - No hidden configuration
✅ **Flexible** - Edit by hand or through UI

## Comparison

### Before (typical server)

```bash
# Install dependencies manually
pip install -r requirements.txt

# Set environment variables
export DB_PATH=/var/lib/app/db
export LOG_LEVEL=info
export PORT=8080

# Create config in one place
nano /etc/app/config.ini

# Add libraries in another place
app-cli add-library Comics /mnt/Comics

# Configure server in yet another place
nano /etc/app/server.conf

# Finally start
app-server start
```

### After (YACLib Enhanced)

```bash
./yaclib.py
```

Interactive setup handles everything.

## Developer Experience

### Quick Test

```bash
# Clone and test
git clone repo
cd yaclib-enhanced
./yaclib.py

# Done - server running!
```

### Production Deployment

```bash
# 1. Copy to server
scp -r yaclib-enhanced server:/opt/

# 2. Edit config once
ssh server
cd /opt/yaclib-enhanced
nano config.yml

# 3. Run
./yaclib.py
```

### Development

```bash
# Dev mode - auto-reload on code changes
# Just edit config.yml:
server:
  reload: true
  log_level: "debug"

# Run
./yaclib.py
```

## File Structure

**After running once:**

```
yaclib-enhanced/
├── yaclib.py              ⭐ THE launcher (one command!)
├── config.yml             ⭐ THE config (one file!)
├── yaclib-cli.py          # Optional CLI tool
├── src/                   # Code (you don't touch this)
├── examples/              # Optional examples
└── docs/                  # Documentation

~/.local/share/yaclib/     # Data (auto-created)
├── yaclib.db              # Database
└── covers/                # Thumbnails
```

**Two files matter:**
1. `yaclib.py` - Run this
2. `config.yml` - Edit this (optional, can use launcher/web UI)

## Advanced Users

The CLI tools are available for power users:

```bash
# Config management
./yaclib-cli.py config show
./yaclib-cli.py config edit

# Library management
./yaclib-cli.py library add "Name" /path
./yaclib-cli.py library scan "Name"
```

**But not required!** The launcher handles everything interactively.

## Philosophy

**Simple things should be simple.**

- New user? Run `./yaclib.py`
- Need to change port? Edit one line in `config.yml`
- Add library? Use launcher or web UI or edit config
- Advanced needs? CLI tools available

**One launcher. One config file. Zero complexity.**

## Summary

Your request:
> "one config file and one launcher"

**Delivered:**
- ✅ One launcher: `./yaclib.py`
- ✅ One config file: `config.yml`
- ✅ One command to rule them all

Everything else is optional.

**Web UI in Phase 3 will make it even easier** - but the fundamentals are perfect now:

```bash
./yaclib.py
```

**That's the entire setup.** 🚀

---

**New to YACLib Enhanced?**

```bash
./yaclib.py
```

**That's all you need to know!**
