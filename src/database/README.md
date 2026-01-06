# Kottlib Database Schema

Modern, feature-rich SQLite database schema for Kottlib.

## Design Philosophy

- **Independent from YACReader** - We implement the HTTP API, not the database format
- **Feature-rich** - Built-in support for users, collections, series, reading progress
- **Extensible** - Easy to add new features without migrations
- **Centralized** - One database for all libraries in standard application data location

## Schema Overview

### Core Tables

**libraries** - Library metadata and settings
- Stores library name, path, UUID, scan status
- Each library is self-contained with its own database

**folders** - Folder hierarchy
- Nested folder structure with parent/child relationships
- Full path tracking for filesystem sync

**comics** - Comic book metadata
- File information (path, size, hash, format)
- Comic metadata (title, series, issue number, etc.)
- Support for auto-detection of series/volumes

**covers** - Thumbnail management
- Dual format (JPEG for mobile, WebP for web)
- Auto-generated and custom covers
- References which page the cover is from

### User Features

**users** - Multi-user support
- Username/password authentication
- Admin vs regular users
- Prepared for future multi-user scenarios

**reading_progress** - Track reading per user
- Current page, progress percentage
- Started/last read/completed timestamps
- Foundation for "continue reading" feature

**user_preferences** - User settings
- Key-value store for user preferences
- Flexible for new settings without schema changes

**folder_preferences** - Per-folder view settings
- Sort mode (folders_first, alphabetical, etc.)
- View mode (grid, list)
- Remembers user's preferred view per folder

### Advanced Features

**series** - Auto-detected series grouping
- Groups related comics into series
- Tracks issue order
- Supports series metadata

**series_comics** - Many-to-many series relationship
- Links comics to series
- Handles multi-volume omnibus editions

**collections** - User-created reading lists
- Custom comic collections
- Public/private collections
- Ordered lists

**reading_stats** - Reading statistics
- Total read time, page turns, session count
- Foundation for reading analytics

### API Support

**sessions** - Session management
- Session-based authentication (like YACReader)
- Tracks current library/comic per session
- Auto-expiration

**metadata_cache** - External metadata
- Cache for ComicVine, Metron, etc.
- Reduces API calls to external services

**schema_version** - Database versioning
- Tracks schema version for migrations
- Ensures compatibility

## Database Location

Centralized application database location:

**Linux:**
```
~/.local/share/yaclib/
├── yaclib.db               ← Single SQLite database for all libraries
└── covers/
    ├── {hash}.jpg          ← All cover thumbnails
    └── {hash}.webp
```

**macOS:**
```
~/Library/Application Support/Kottlib/
├── yaclib.db
└── covers/
    ├── {hash}.jpg
    └── {hash}.webp
```

**Windows:**
```
%APPDATA%\Kottlib\
├── yaclib.db
└── covers\
    ├── {hash}.jpg
    └── {hash}.webp
```

**Comic libraries remain clean:**
```
/mnt/Blue/Ebooks_Comics/Manga/
├── Series A/
│   └── Issue 01.cbz
└── Series B/
    └── Issue 01.cbz
```

No metadata folders in your comic directories!

## Key Features

### 1. File Hash-based Deduplication
Comics are identified by SHA256 hash, allowing:
- Detection of duplicate files
- Reliable identity even if files move
- Efficient caching

### 2. Flexible Metadata
JSON fields for extensibility:
- Library settings
- User preferences
- Cached metadata

### 3. Reading Progress Tracking
Per-user progress tracking enables:
- Continue reading feature
- Reading history
- Statistics and insights

### 4. Series Auto-detection
Foundation for intelligent series grouping:
- Auto-detect series from filenames
- Manual series assignment
- Reading order tracking

### 5. Multi-user Ready
Built-in user support for:
- Personal reading lists
- Individual progress tracking
- Shared libraries

## Migration from YACReader

Use the import tool to migrate existing YACReader libraries:

```bash
python tools/import_yacreader.py \
  --yacreader-db /path/to/Comics/.yacreaderlibrary/library.ydb \
  --output-db ~/.local/share/kottlib/kottlib.db \
  --library-path /path/to/Comics \
  --library-name "My Comics"
```

This performs a one-time conversion of:
- Comics and folders
- Cover thumbnails
- Reading progress
- Library metadata

All data is imported into the centralized Kottlib database.

## Schema File

See [schema.sql](schema.sql) for the complete SQL schema definition.

## Future Enhancements

Potential additions without breaking changes:
- Tags system (new `tags` and `comic_tags` tables)
- Comments/notes (new `comic_notes` table)
- Reading goals (new `reading_goals` table)
- Recommendations engine (new `recommendations` table)
- External integrations (expand `metadata_cache`)

The schema is designed to grow with new features!
