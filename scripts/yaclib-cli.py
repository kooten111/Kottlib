#!/usr/bin/env python3
"""
Kottlib CLI

Command-line interface for managing Kottlib server.

Usage:
    yaclib-cli.py config init          # Create example config
    yaclib-cli.py config show          # Show current config
    yaclib-cli.py config edit          # Edit config file
    yaclib-cli.py library add NAME PATH  # Add library
    yaclib-cli.py library list         # List libraries
    yaclib-cli.py library scan NAME    # Scan library
    yaclib-cli.py server start         # Start server
    yaclib-cli.py server info          # Show server info
"""

import sys
import subprocess
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config import (
    get_config_path,
    load_config,
    save_config,
    create_example_config,
    LibraryDefinition,
)
from database import (
    Database,
    get_default_db_path,
    create_library,
    get_all_libraries,
    get_library_by_path,
)


def cmd_config_init():
    """Initialize configuration file"""
    config_path = Path("config.yml")

    if config_path.exists():
        response = input(f"Config file already exists at {config_path}. Overwrite? [y/N] ")
        if response.lower() != 'y':
            print("Aborted.")
            return

    print(f"Creating example configuration at: {config_path}")
    create_example_config(config_path)
    print(f"✅ Configuration created!")
    print(f"\nEdit the file to customize your setup:")
    print(f"  {config_path}")


def cmd_config_show():
    """Show current configuration"""
    config_path = get_config_path()
    print(f"Configuration file: {config_path}")
    print(f"Exists: {config_path.exists()}\n")

    config = load_config()

    print("="*60)
    print("SERVER CONFIGURATION")
    print("="*60)
    print(f"Host: {config.server.host}")
    print(f"Port: {config.server.port}")
    print(f"Log Level: {config.server.log_level}")
    print(f"Reload: {config.server.reload}")

    print("\n" + "="*60)
    print("DATABASE CONFIGURATION")
    print("="*60)
    if config.database.path:
        print(f"Path: {config.database.path}")
    else:
        print(f"Path: {get_default_db_path()} (auto-detected)")
    print(f"Echo SQL: {config.database.echo}")

    print("\n" + "="*60)
    print("FEATURES")
    print("="*60)
    print(f"Legacy API: {config.features.legacy_api}")
    print(f"Modern API: {config.features.modern_api}")
    print(f"Reading Progress: {config.features.reading_progress}")
    print(f"Series Detection: {config.features.series_detection}")
    print(f"Collections: {config.features.collections}")
    print(f"Auto Thumbnails: {config.features.auto_thumbnails}")

    print("\n" + "="*60)
    print(f"LIBRARIES ({len(config.libraries)})")
    print("="*60)
    for lib in config.libraries:
        print(f"\n📚 {lib.name}")
        print(f"   Path: {lib.path}")
        print(f"   Auto-scan: {lib.auto_scan}")
        print(f"   Scan on startup: {lib.scan_on_startup}")


def cmd_config_edit():
    """Edit configuration file"""
    config_path = get_config_path()

    if not config_path.exists():
        print(f"Configuration file not found: {config_path}")
        print("Run 'yaclib-cli.py config init' to create one.")
        return

    # Try to open with default editor
    import os
    editor = os.getenv('EDITOR', 'nano')

    print(f"Opening {config_path} with {editor}...")
    subprocess.run([editor, str(config_path)])


def cmd_library_add(name: str, path: str):
    """Add a library to configuration"""
    config = load_config()

    # Check if library already exists
    for lib in config.libraries:
        if lib.name == name:
            print(f"❌ Library '{name}' already exists!")
            return

    # Add library to config
    library = LibraryDefinition(
        name=name,
        path=str(Path(path).resolve()),
        auto_scan=True,
        scan_on_startup=False
    )

    config.libraries.append(library)

    # Save config
    config_path = get_config_path()
    save_config(config, config_path)

    print(f"✅ Library '{name}' added to config!")
    print(f"\nTo scan it, run:")
    print(f"  python examples/scan_library.py \"{path}\" \"{name}\"")


def cmd_library_list():
    """List libraries from database"""
    db_path = get_default_db_path()

    if not db_path.exists():
        print("Database not found. No libraries created yet.")
        return

    db = Database(db_path)

    print("\n" + "="*60)
    print("LIBRARIES IN DATABASE")
    print("="*60 + "\n")

    with db.get_session() as session:
        libraries = get_all_libraries(session)

        if not libraries:
            print("No libraries found in database.")
            print("\nScan a library to add it:")
            print("  python examples/scan_library.py /path/to/comics \"Comics\"")
            return

        for lib in libraries:
            print(f"📚 {lib.name} (ID: {lib.id})")
            print(f"   Path: {lib.path}")
            print(f"   Status: {lib.scan_status}")
            if lib.last_scan_at:
                import time
                scan_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(lib.last_scan_at))
                print(f"   Last scan: {scan_time}")
            print()

    db.close()


def cmd_library_scan(name: str):
    """Scan a library"""
    config = load_config()

    # Find library in config
    library_def = None
    for lib in config.libraries:
        if lib.name == name:
            library_def = lib
            break

    if not library_def:
        print(f"❌ Library '{name}' not found in config!")
        print("\nAvailable libraries:")
        for lib in config.libraries:
            print(f"  - {lib.name}")
        return

    # Run scan
    print(f"Scanning library: {library_def.name}")
    print(f"Path: {library_def.path}\n")

    scan_script = Path(__file__).parent / 'examples' / 'scan_library.py'
    subprocess.run([
        sys.executable,
        str(scan_script),
        library_def.path,
        library_def.name
    ])


def cmd_server_start():
    """Start the server"""
    config = load_config()

    print("Starting Kottlib Server...")
    print(f"Host: {config.server.host}")
    print(f"Port: {config.server.port}")
    print(f"\nServer will be available at:")
    print(f"  http://localhost:{config.server.port}")
    print(f"  http://localhost:{config.server.port}/docs (API docs)")
    print("\nPress Ctrl+C to stop\n")

    # Start server
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=config.server.host,
        port=config.server.port,
        reload=config.server.reload,
        log_level=config.server.log_level
    )


def cmd_server_info():
    """Show server information"""
    config = load_config()
    db_path = get_default_db_path()

    print("\n" + "="*60)
    print("Kottlib SERVER INFO")
    print("="*60 + "\n")

    print("Server:")
    print(f"  Host: {config.server.host}")
    print(f"  Port: {config.server.port}")
    print(f"  URL: http://localhost:{config.server.port}")
    print(f"  API Docs: http://localhost:{config.server.port}/docs")

    print(f"\nDatabase:")
    print(f"  Path: {db_path}")
    print(f"  Exists: {db_path.exists()}")

    print(f"\nConfiguration:")
    config_path = get_config_path()
    print(f"  Path: {config_path}")
    print(f"  Exists: {config_path.exists()}")

    print(f"\nLibraries in config: {len(config.libraries)}")
    for lib in config.libraries:
        print(f"  - {lib.name}: {lib.path}")


def show_help():
    """Show help message"""
    print(__doc__)


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        show_help()
        return

    command = sys.argv[1]

    # Config commands
    if command == 'config':
        if len(sys.argv) < 3:
            print("Usage: yaclib-cli.py config <init|show|edit>")
            return

        subcommand = sys.argv[2]
        if subcommand == 'init':
            cmd_config_init()
        elif subcommand == 'show':
            cmd_config_show()
        elif subcommand == 'edit':
            cmd_config_edit()
        else:
            print(f"Unknown config subcommand: {subcommand}")

    # Library commands
    elif command == 'library':
        if len(sys.argv) < 3:
            print("Usage: yaclib-cli.py library <add|list|scan>")
            return

        subcommand = sys.argv[2]
        if subcommand == 'add':
            if len(sys.argv) < 5:
                print("Usage: yaclib-cli.py library add NAME PATH")
                return
            cmd_library_add(sys.argv[3], sys.argv[4])
        elif subcommand == 'list':
            cmd_library_list()
        elif subcommand == 'scan':
            if len(sys.argv) < 4:
                print("Usage: yaclib-cli.py library scan NAME")
                return
            cmd_library_scan(sys.argv[3])
        else:
            print(f"Unknown library subcommand: {subcommand}")

    # Server commands
    elif command == 'server':
        if len(sys.argv) < 3:
            print("Usage: yaclib-cli.py server <start|info>")
            return

        subcommand = sys.argv[2]
        if subcommand == 'start':
            cmd_server_start()
        elif subcommand == 'info':
            cmd_server_info()
        else:
            print(f"Unknown server subcommand: {subcommand}")

    else:
        print(f"Unknown command: {command}")
        show_help()


if __name__ == "__main__":
    main()
