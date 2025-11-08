# Getting Started with YACLib Enhanced

**The easiest way to get started - just run one command!**

## For New Users

### Requirements

- **Python 3.11 or higher**
- Comics in CBZ, CBR, or CB7 format
- Linux, macOS, or Windows

### Installation

```bash
# 1. Download YACLib Enhanced
git clone https://github.com/yourusername/yaclib-enhanced.git
cd yaclib-enhanced

# 2. Run it!
./yaclib.py
```

That's it! The launcher will guide you through everything.

## What Happens When You Run `./yaclib.py`?

### First Time

The launcher will:

1. **Check Python version** - Makes sure you have Python 3.11+
2. **Install dependencies** - Asks to install required packages
3. **Interactive setup** - Asks you a few questions:
   - Would you like to add a library?
   - What's the library name? (e.g., "Comics")
   - Where are your comics? (e.g., "/mnt/Comics")
   - Reading direction? (left-to-right or right-to-left for manga)
   - Want to scan now?
4. **Start server** - Launches the server automatically

### Every Time After

Just runs the server with your saved configuration!

```bash
./yaclib.py
```

Visit http://localhost:8081/docs

## Example First-Time Setup

```
$ ./yaclib.py

==============================================================
🎉 Welcome to YACLib Enhanced!
==============================================================

First-time setup - let's configure your comic libraries.

Creating configuration file: config.yml

==============================================================
📚 Library Configuration
==============================================================

You can add libraries now or later through the web interface.

Would you like to add a library now? [y/N] y

------------------------------------------------------------
Library name (e.g., 'Comics'): My Comics
Library path (e.g., '/mnt/Comics'): /home/user/Comics

Reading direction:
  1. Left-to-right (Western comics)
  2. Right-to-left (Manga)
Choice [1]: 1

✅ Added library: My Comics

Add another library? [y/N] n

✅ Configuration saved to config.yml

==============================================================
📖 Library Scanning
==============================================================

You can scan libraries now or later through the web interface.
Scanning will:
  - Find all comic files (CBZ, CBR, CB7)
  - Extract metadata
  - Generate thumbnails

Scan libraries now? [Y/n] y

📚 Scanning: My Comics
   Path: /home/user/Comics
   📖 Comic1.cbz
     ✅ Added to database (ID: 1)
     🖼️  Generating thumbnails...
     ✅ Thumbnails generated (JPEG + WebP)
   ...

==============================================================
✅ Setup Complete!
==============================================================

You can:
  - Edit config: config.yml
  - Manage via web interface (coming in Phase 3)
  - Use CLI: ./yaclib-cli.py --help

==============================================================
🚀 Starting YACLib Enhanced Server
==============================================================

Server will be available at:
  • http://localhost:8081
  • http://localhost:8081/docs (API Documentation)

Press Ctrl+C to stop the server

INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8081
```

## After Setup

### Start the Server

```bash
./yaclib.py
```

### Access the Server

Open your browser:
- **API Documentation**: http://localhost:8081/docs
- **API Info**: http://localhost:8081/api/v1/info
- **Libraries**: http://localhost:8081/api/v1/libraries

### Connect YACReader Mobile App

1. Open YACReader app on your phone
2. Add server: `http://<your-computer-ip>:8081`
3. Browse your libraries!

## Configuration File

After first run, you'll have a `config.yml` file:

```yaml
server:
  host: "0.0.0.0"
  port: 8081
  log_level: "info"

libraries:
  - name: "My Comics"
    path: "/home/user/Comics"
    auto_scan: true
    settings:
      sort_mode: "folders_first"
      default_reading_direction: "ltr"
```

**Edit this file** to:
- Change server port
- Add more libraries
- Adjust settings

Then restart: `./yaclib.py`

## Managing Libraries

### Through Web Interface (Phase 3)

Coming soon! You'll be able to:
- Add/remove libraries
- Scan for new comics
- Edit metadata
- Create collections

### Through Configuration File

Edit `config.yml`:

```yaml
libraries:
  - name: "Comics"
    path: "/mnt/Comics"
    auto_scan: true

  - name: "Manga"
    path: "/mnt/Manga"
    auto_scan: true
    settings:
      default_reading_direction: "rtl"
```

Then rescan:
```bash
./yaclib-cli.py library scan Manga
```

### Through CLI Tool

```bash
# Add library
./yaclib-cli.py library add "Manga" /mnt/Manga

# Scan library
./yaclib-cli.py library scan Manga

# List libraries
./yaclib-cli.py library list
```

## Common Tasks

### Add Another Library

**Option 1: Edit config.yml**
```yaml
libraries:
  - name: "New Library"
    path: "/path/to/comics"
```

Then scan:
```bash
./yaclib-cli.py library scan "New Library"
```

**Option 2: Use CLI**
```bash
./yaclib-cli.py library add "New Library" /path/to/comics
./yaclib-cli.py library scan "New Library"
```

### Change Server Port

Edit `config.yml`:
```yaml
server:
  port: 9000
```

Restart server.

### View All Settings

```bash
./yaclib-cli.py config show
```

## Directory Structure

After setup:

```
yaclib-enhanced/
├── config.yml              # Your configuration (created on first run)
├── yaclib.py              # Main launcher (run this!)
├── yaclib-cli.py          # CLI tool (advanced)
├── src/                   # Source code
├── examples/              # Example scripts
└── docs/                  # Documentation

~/.local/share/yaclib/     # (Linux)
├── yaclib.db              # Database
└── covers/                # Thumbnails
```

## Troubleshooting

### Python Version Error

```
❌ Python 3.11 or higher is required
```

**Solution:** Install Python 3.11+
```bash
# Ubuntu/Debian
sudo apt install python3.11

# macOS
brew install python@3.11
```

### Permission Denied

```
bash: ./yaclib.py: Permission denied
```

**Solution:**
```bash
chmod +x yaclib.py
./yaclib.py
```

Or run with Python:
```bash
python3 yaclib.py
```

### Library Path Doesn't Exist

The launcher will warn you if a path doesn't exist. Make sure:
- Path is correct
- You have read permissions
- Comics are in CBZ/CBR/CB7 format

### Port Already in Use

Edit `config.yml`:
```yaml
server:
  port: 8082  # Use different port
```

## What's Next?

1. **Browse API Docs**: http://localhost:8081/docs
2. **Connect Mobile App**: Point YACReader to your server
3. **Add More Libraries**: Edit `config.yml` or use CLI
4. **Read Documentation**: Check out [CONFIGURATION.md](CONFIGURATION.md)

## Getting Help

- **Configuration**: See [CONFIGURATION.md](CONFIGURATION.md)
- **Quick Start**: See [QUICKSTART.md](QUICKSTART.md)
- **Full Docs**: See [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md)
- **CLI Help**: Run `./yaclib-cli.py --help`

## Summary

**To get started:**
1. Clone the repo
2. Run `./yaclib.py`
3. Follow the prompts
4. Done!

**To run after setup:**
```bash
./yaclib.py
```

**That's it!** Everything else is optional and can be done through the web interface (Phase 3) or configuration file.

---

**Questions?** Check the [documentation](docs/) or configuration guide!
