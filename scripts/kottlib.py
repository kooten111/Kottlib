#!/usr/bin/env python3
"""
Kottlib - Single-Command Launcher

Simply run:
    ./kottlib.py

This will:
- Check and install dependencies
- Initialize database
- Create config if needed
- Start the server
- Open web interface

For first-time setup, it will guide you through library configuration.
"""

import sys
import subprocess
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))


def check_python_version():
    """Ensure Python 3.11+"""
    if sys.version_info < (3, 11):
        print("❌ Python 3.11 or higher is required")
        print(f"   Current version: {sys.version}")
        sys.exit(1)


def check_dependencies():
    """Check if dependencies are installed"""
    try:
        import fastapi
        import uvicorn
        import sqlalchemy
        import yaml
        import PIL
        return True
    except ImportError as e:
        return False


def install_dependencies():
    """Install dependencies"""
    print("\n📦 Installing dependencies...")
    print("This may take a few minutes...\n")

    requirements = Path(__file__).parent / 'requirements.txt'

    result = subprocess.run([
        sys.executable, '-m', 'pip', 'install', '-r', str(requirements)
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print("❌ Failed to install dependencies")
        print(result.stderr)
        sys.exit(1)

    print("✅ Dependencies installed successfully\n")


def first_time_setup():
    """Interactive first-time setup"""
    from config import get_config_path, create_example_config, load_config

    config_path = get_config_path()

    # Use local config.yml in project directory
    config_path = Path("config.yml")

    if not config_path.exists():
        print("\n" + "="*60)
        print("🎉 Welcome to Kottlib!")
        print("="*60)
        print("\nFirst-time setup - let's configure your comic libraries.\n")

        # Create example config
        print(f"Creating configuration file: {config_path}")
        create_example_config(config_path)

        print("\n" + "="*60)
        print("📚 Library Configuration")
        print("="*60)
        print("\nYou can add libraries now or later through the web interface.\n")

        response = input("Would you like to add a library now? [y/N] ")

        if response.lower() == 'y':
            from config import load_config, save_config, LibraryDefinition

            config = load_config(config_path)

            while True:
                print("\n" + "-"*60)
                name = input("Library name (e.g., 'Comics'): ").strip()
                if not name:
                    break

                path = input("Library path (e.g., '/mnt/Comics'): ").strip()
                if not path:
                    break

                # Validate path
                lib_path = Path(path)
                if not lib_path.exists():
                    print(f"⚠️  Warning: Path does not exist: {path}")
                    response = input("Add anyway? [y/N] ")
                    if response.lower() != 'y':
                        continue

                # Ask about reading direction
                print("\nReading direction:")
                print("  1. Left-to-right (Western comics)")
                print("  2. Right-to-left (Manga)")
                direction_choice = input("Choice [1]: ").strip() or "1"
                direction = "rtl" if direction_choice == "2" else "ltr"

                # Add library
                library = LibraryDefinition(
                    name=name,
                    path=str(lib_path.resolve()),
                    auto_scan=True,
                    scan_on_startup=False,
                    settings={
                        "sort_mode": "folders_first",
                        "default_reading_direction": direction
                    }
                )

                config.libraries.append(library)
                print(f"✅ Added library: {name}")

                # Ask for another
                response = input("\nAdd another library? [y/N] ")
                if response.lower() != 'y':
                    break

            # Save config
            save_config(config, config_path)
            print(f"\n✅ Configuration saved to {config_path}")

            # Ask about scanning
            if config.libraries:
                print("\n" + "="*60)
                print("📖 Library Scanning")
                print("="*60)
                print("\nYou can scan libraries now or later through the web interface.")
                print("Scanning will:")
                print("  - Find all comic files (CBZ, CBR, CB7)")
                print("  - Extract metadata")
                print("  - Generate thumbnails\n")

                response = input("Scan libraries now? [Y/n] ")
                if response.lower() != 'n':
                    scan_libraries(config)

        print("\n" + "="*60)
        print("✅ Setup Complete!")
        print("="*60)
        print("\nYou can:")
        print(f"  - Edit config: {config_path}")
        print("  - Manage via web interface (coming in Phase 3)")
        print("  - Use CLI: ./kottlib-cli.py --help")
        print()


def scan_libraries(config):
    """Scan all configured libraries"""
    from database import Database, get_default_db_path, get_library_by_path

    db = Database(get_default_db_path())
    db.init_db()

    for lib_def in config.libraries:
        print(f"\n📚 Scanning: {lib_def.name}")
        print(f"   Path: {lib_def.path}")

        # Check if already scanned
        with db.get_session() as session:
            existing = get_library_by_path(session, lib_def.path)
            if existing:
                print(f"   ℹ️  Already in database (skipping)")
                continue

        # Run scan script
        scan_script = Path(__file__).parent / 'examples' / 'scan_library.py'
        result = subprocess.run([
            sys.executable,
            str(scan_script),
            lib_def.path,
            lib_def.name
        ])

        if result.returncode != 0:
            print(f"   ⚠️  Scan failed")

    db.close()


def initialize_database():
    """Initialize database"""
    from database import Database, get_default_db_path

    db_path = get_default_db_path()

    if not db_path.exists():
        print(f"📊 Initializing database: {db_path}")
        db = Database(db_path)
        db.init_db()
        db.close()
        print("✅ Database initialized\n")


def start_server():
    """Start the FastAPI server"""
    from config import get_config
    import uvicorn

    config = get_config()

    print("\n" + "="*60)
    print("🚀 Starting Kottlib Server")
    print("="*60)
    print(f"\nServer will be available at:")
    print(f"  • http://localhost:{config.server.port}")
    print(f"  • http://localhost:{config.server.port}/docs (API Documentation)")
    print(f"\nPress Ctrl+C to stop the server\n")

    try:
        uvicorn.run(
            "src.api.main:app",
            host=config.server.host,
            port=config.server.port,
            reload=config.server.reload,
            log_level=config.server.log_level
        )
    except KeyboardInterrupt:
        print("\n\n✅ Server stopped")


def main():
    """Main entry point"""
    # Check Python version
    check_python_version()

    # Check/install dependencies
    if not check_dependencies():
        print("="*60)
        print("Kottlib - First Run Setup")
        print("="*60)
        print("\nDependencies need to be installed.")
        response = input("Install now? [Y/n] ")

        if response.lower() == 'n':
            print("\nPlease install dependencies manually:")
            print("  pip install -r requirements.txt")
            sys.exit(0)

        install_dependencies()

    # First-time setup if needed
    first_time_setup()

    # Initialize database
    initialize_database()

    # Start server
    start_server()


if __name__ == "__main__":
    main()
