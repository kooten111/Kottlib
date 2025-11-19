# Data Storage Structure

All application data is now stored in the `./data` directory relative to the application root, making it self-contained and portable.

## Directory Structure

```
./data/
├── main.db                    # Main database (users, sessions, global settings)
├── Manga/                     # Manga library data
│   ├── library.db            # Manga library metadata (comics, folders, covers, etc.)
│   └── covers/               # Manga cover thumbnails
│       ├── ab/               # Hierarchical storage by hash prefix
│       │   ├── abc123.jpg    # JPEG thumbnail (300x450px)
│       │   └── abc123.webp   # WebP thumbnail (400x600px)
│       └── ...
├── Comics/                    # Comics library data
│   ├── library.db            # Comics library metadata
│   └── covers/               # Comics cover thumbnails
│       └── ...
└── <OtherLibraries>/         # Additional libraries follow same pattern
    ├── library.db
    └── covers/
```

## Database Architecture

### Main Database (`./data/main.db`)
Contains global application data:
- **Users** - User accounts and authentication
- **Sessions** - Active user sessions
- **Global Settings** - Application-wide configuration

### Library Databases (`./data/<LibraryName>/library.db`)
Each library has its own isolated database containing:
- **Comics** - Comic file metadata and information
- **Folders** - Folder structure within the library
- **Covers** - Thumbnail references (JPEG and WebP paths)
- **Reading Progress** - User reading progress per comic
- **Series** - Derived series groupings
- **Favorites** - User favorites
- **Labels/Tags** - Comic tagging system
- **Reading Lists** - Custom collections

## Benefits

### 1. Self-Contained
All data is in `./data`, making the application portable:
- No data in `~/.local/share` or system directories
- Easy to backup (just copy `./data`)
- Easy to migrate to different systems

### 2. Per-Library Isolation
Each library is completely self-contained:
- Own database with metadata
- Own covers directory
- Can be backed up independently
- Can be moved/shared separately

### 3. Clean Organization
```
./data/Manga/       - Everything related to manga
./data/Comics/      - Everything related to comics
./data/LightNovels/ - Everything related to light novels
```

## Configuration

The `config.yml` reflects this structure:

```yaml
database:
  # Main database for global settings, users, and sessions
  path: data/main.db
  echo: false

storage:
  # Note: Each library has its own covers directory under ./data/<LibraryName>/covers/
  # This setting is for legacy/fallback shared covers
  covers_dir: data/covers
  cache_dir: null

libraries:
  - name: Manga
    path: /path/to/manga/files
    auto_scan: true
    scan_on_startup: false
    settings:
      sort_mode: folders_first
      default_reading_direction: rtl

  - name: Comics
    path: /path/to/comics/files
    auto_scan: true
    scan_on_startup: false
    settings:
      sort_mode: folders_first
      default_reading_direction: ltr
```

## Cover Storage

Covers are stored hierarchically using file hash prefixes for performance:

```
./data/<LibraryName>/covers/
├── ab/
│   ├── abc123.jpg    # JPEG (300x450px, mobile-optimized)
│   └── abc123.webp   # WebP (400x600px, web-optimized)
├── cd/
│   ├── cdef45.jpg
│   └── cdef45.webp
└── ...
```

- First 2 characters of file hash used as subdirectory
- Prevents filesystem performance issues with large directories
- Both JPEG and WebP formats generated for compatibility

## API Functions

### Get Data Directories

```python
from database import (
    get_data_dir,           # Returns ./data
    get_library_data_dir,   # Returns ./data/<LibraryName>
    get_library_db_path,    # Returns ./data/<LibraryName>/library.db
    get_covers_dir,         # Returns ./data/<LibraryName>/covers/
)

# Example usage
data_dir = get_data_dir()  # ./data
manga_dir = get_library_data_dir("Manga")  # ./data/Manga
manga_db = get_library_db_path("Manga")    # ./data/Manga/library.db
manga_covers = get_covers_dir("Manga")     # ./data/Manga/covers
```

### Database Initialization

```python
# Main database
main_db = Database(get_default_db_path())  # Uses ./data/main.db

# Library-specific database
manga_db_path = get_library_db_path("Manga")
manga_db = Database(manga_db_path)  # Uses ./data/Manga/library.db
```

## Migration from Old Structure

If you have existing data in the old location (`~/.local/share/yaclib/`), you can migrate it:

```bash
# 1. Create new data directory
mkdir -p data

# 2. Move main database (rename to main.db)
mv ~/.local/share/yaclib/yaclib.db data/main.db

# 3. For each library, create directory and move covers
mkdir -p data/Manga
mv ~/.local/share/yaclib/covers data/Manga/covers

mkdir -p data/Comics
# If you had separate libraries, organize them here
```

**Note:** After migration, you may need to rescan libraries to rebuild the new per-library databases.

## Development Notes

- The main database path defaults to `./data/main.db` (changed from platform-specific paths)
- Each library gets its own database automatically when scanning
- Covers are automatically stored in library-specific directories
- All paths are relative to the current working directory
- Make sure to run the application from the project root
