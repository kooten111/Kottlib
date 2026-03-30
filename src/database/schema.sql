-- Kottlib Database Schema
-- Version: 1.0
-- Modern, clean schema designed for flexibility and future features

-- ============================================================================
-- LIBRARIES
-- ============================================================================

CREATE TABLE libraries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE NOT NULL,           -- Unique identifier
    name TEXT NOT NULL,                   -- Library display name
    path TEXT UNIQUE NOT NULL,            -- Filesystem path
    created_at INTEGER NOT NULL,          -- Unix timestamp
    updated_at INTEGER NOT NULL,          -- Unix timestamp
    last_scan_at INTEGER,                 -- Last scan timestamp
    scan_status TEXT DEFAULT 'pending',   -- pending, scanning, complete, error
    settings JSON                         -- Library-specific settings
);

CREATE INDEX idx_libraries_uuid ON libraries(uuid);
CREATE INDEX idx_libraries_path ON libraries(path);


-- ============================================================================
-- FOLDERS
-- ============================================================================

CREATE TABLE folders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    library_id INTEGER NOT NULL,
    parent_id INTEGER,                    -- NULL for root folders
    path TEXT NOT NULL,                   -- Full filesystem path
    name TEXT NOT NULL,                   -- Display name
    position INTEGER DEFAULT 0,           -- Sort order (user-defined)
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    FOREIGN KEY (library_id) REFERENCES libraries(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES folders(id) ON DELETE CASCADE,
    UNIQUE(library_id, path)
);

CREATE INDEX idx_folders_library ON folders(library_id);
CREATE INDEX idx_folders_parent ON folders(parent_id);
CREATE INDEX idx_folders_path ON folders(library_id, path);


-- ============================================================================
-- COMICS
-- ============================================================================

CREATE TABLE comics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    library_id INTEGER NOT NULL,
    folder_id INTEGER,                    -- NULL if in library root
    path TEXT NOT NULL,                   -- Full filesystem path
    filename TEXT NOT NULL,               -- Just the filename
    hash TEXT UNIQUE NOT NULL,            -- SHA256 of file for deduplication

    -- File metadata
    file_size INTEGER NOT NULL,           -- Bytes
    file_modified_at INTEGER NOT NULL,    -- Filesystem mtime
    format TEXT NOT NULL,                 -- cbz, cbr, cb7, pdf, etc.

    -- Comic metadata
    title TEXT,                           -- Comic title (from metadata or filename)
    series TEXT,                          -- Series name (auto-detected or manual)
    normalized_series_name TEXT,          -- Pre-computed normalized name
    volume INTEGER,                       -- Volume number
    issue_number REAL,                    -- Issue/chapter number (can be decimal)
    year INTEGER,                         -- Publication year
    publisher TEXT,
    writer TEXT,
    artist TEXT,
    description TEXT,

    -- Extended ComicInfo.xml metadata (YACReader compatibility)
    penciller TEXT,
    inker TEXT,
    colorist TEXT,
    letterer TEXT,
    cover_artist TEXT,
    editor TEXT,

    -- Series/Arc metadata
    story_arc TEXT,
    arc_number TEXT,
    arc_count INTEGER,
    alternate_series TEXT,
    alternate_number TEXT,
    alternate_count INTEGER,

    -- Additional metadata
    genre TEXT,
    language_iso TEXT,
    age_rating TEXT,
    imprint TEXT,
    format_type TEXT,
    is_color INTEGER,

    -- Characters, teams, locations
    characters TEXT,
    teams TEXT,
    locations TEXT,
    main_character_or_team TEXT,
    series_group TEXT,

    -- User content
    notes TEXT,
    review TEXT,
    tags TEXT,

    -- External IDs
    comic_vine_id TEXT,
    web TEXT,

    -- Scanner metadata
    scanner_source TEXT,                  -- Scanner name (e.g., 'nhentai')
    scanner_source_id TEXT,               -- External source ID
    scanner_source_url TEXT,              -- External source URL
    scanned_at INTEGER,                   -- Timestamp of last scan
    scan_confidence REAL,                 -- Confidence score (0.0-1.0)

    -- Issue metadata
    is_bis INTEGER DEFAULT 0,
    count INTEGER,
    date TEXT,

    -- Reading metadata
    num_pages INTEGER NOT NULL,
    reading_direction TEXT DEFAULT 'ltr', -- ltr, rtl (manga)

    -- Display settings (per-comic)
    rating REAL DEFAULT 0.0,
    brightness INTEGER DEFAULT 0,
    contrast INTEGER DEFAULT 0,
    gamma REAL DEFAULT 1.0,

    -- Bookmarks (page numbers)
    bookmark1 INTEGER DEFAULT 0,
    bookmark2 INTEGER DEFAULT 0,
    bookmark3 INTEGER DEFAULT 0,

    -- Cover info
    cover_page INTEGER DEFAULT 1,
    cover_size_ratio REAL DEFAULT 0.0,
    original_cover_size TEXT,

    -- Access tracking
    last_time_opened INTEGER,
    has_been_opened INTEGER DEFAULT 0,
    edited INTEGER DEFAULT 0

    -- Status
    position INTEGER DEFAULT 0,           -- Sort order (user-defined)
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,

    FOREIGN KEY (library_id) REFERENCES libraries(id) ON DELETE CASCADE,
    FOREIGN KEY (folder_id) REFERENCES folders(id) ON DELETE SET NULL
);

CREATE INDEX idx_comics_library ON comics(library_id);
CREATE INDEX idx_comics_folder ON comics(folder_id);
CREATE INDEX idx_comics_hash ON comics(hash);
CREATE INDEX idx_comics_series ON comics(series);
CREATE INDEX idx_comics_path ON comics(library_id, path);

-- Performance indexes for common query patterns
CREATE INDEX idx_comics_title ON comics(title);
CREATE INDEX idx_comics_publisher ON comics(publisher);
CREATE INDEX idx_comics_year ON comics(year);
CREATE INDEX idx_comics_filename ON comics(filename);
CREATE INDEX idx_comics_library_updated ON comics(library_id, updated_at DESC);
CREATE INDEX idx_comics_library_series ON comics(library_id, series);
CREATE INDEX idx_comics_series_issue ON comics(series, issue_number);
CREATE INDEX idx_comics_file_modified ON comics(file_modified_at);
CREATE INDEX idx_comics_library_count ON comics(library_id);
CREATE INDEX idx_comics_normalized_series ON comics(normalized_series_name);
CREATE INDEX idx_comics_library_normalized_series ON comics(library_id, normalized_series_name);

-- Scanner metadata indexes
CREATE INDEX idx_comics_scanner_source ON comics(scanner_source);
CREATE INDEX idx_comics_scanned_at ON comics(scanned_at);


-- ============================================================================
-- THUMBNAILS / COVERS
-- ============================================================================

CREATE TABLE covers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comic_id INTEGER NOT NULL,
    type TEXT NOT NULL,                   -- auto, custom
    page_number INTEGER NOT NULL,         -- Which page this is from

    -- File info
    jpeg_path TEXT NOT NULL,              -- Path to JPEG version (300px, mobile)
    webp_path TEXT,                       -- Path to WebP version (400px, web)

    -- Generation metadata
    generated_at INTEGER NOT NULL,

    FOREIGN KEY (comic_id) REFERENCES comics(id) ON DELETE CASCADE,
    UNIQUE(comic_id, type)
);

CREATE INDEX idx_covers_comic ON covers(comic_id);


-- ============================================================================
-- READING PROGRESS
-- ============================================================================

CREATE TABLE reading_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,             -- For future multi-user support
    comic_id INTEGER NOT NULL,

    -- Progress tracking
    current_page INTEGER NOT NULL DEFAULT 0,
    total_pages INTEGER NOT NULL,
    progress_percent REAL NOT NULL DEFAULT 0.0,
    is_completed INTEGER NOT NULL DEFAULT 0, -- Boolean

    -- Timestamps
    started_at INTEGER NOT NULL,          -- First opened
    last_read_at INTEGER NOT NULL,        -- Last interaction
    completed_at INTEGER,                 -- When finished

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (comic_id) REFERENCES comics(id) ON DELETE CASCADE,
    UNIQUE(user_id, comic_id)
);

CREATE INDEX idx_reading_progress_user ON reading_progress(user_id);
CREATE INDEX idx_reading_progress_comic ON reading_progress(comic_id);
CREATE INDEX idx_reading_progress_last_read ON reading_progress(last_read_at DESC);

-- Performance indexes for "continue reading" queries
CREATE INDEX idx_reading_progress_user_last_read ON reading_progress(user_id, last_read_at DESC);


-- ============================================================================
-- FAVORITES
-- ============================================================================

CREATE TABLE IF NOT EXISTS favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 1,
    library_id INTEGER NOT NULL,
    comic_id INTEGER NOT NULL,
    created_at INTEGER NOT NULL,

    FOREIGN KEY (comic_id) REFERENCES comics(id) ON DELETE CASCADE,
    UNIQUE(user_id, comic_id)
);

CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites(user_id);
CREATE INDEX IF NOT EXISTS idx_favorites_comic ON favorites(comic_id);


-- ============================================================================
-- SERIES (Auto-detected groupings)
-- ============================================================================

CREATE TABLE series (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    library_id INTEGER NOT NULL,
    name TEXT NOT NULL,                   -- Series name
    display_name TEXT,                    -- User-customizable display name

    -- Metadata
    publisher TEXT,
    year_start INTEGER,
    year_end INTEGER,
    description TEXT,

    -- Stats (cached for performance)
    comic_count INTEGER DEFAULT 0,
    total_issues INTEGER DEFAULT 0,

    -- Scanner metadata (for series-level scanners like AniList)
    scanner_source TEXT,                  -- Scanner name (e.g., "AniList")
    scanner_source_id TEXT,               -- ID from external source
    scanner_source_url TEXT,              -- URL to source page
    scanned_at INTEGER,                   -- Timestamp of scan
    scan_confidence REAL,                 -- Match confidence (0.0-1.0)

    -- Additional metadata from scanners
    writer TEXT,                          -- Writer/author name(s)
    artist TEXT,                          -- Artist name(s)
    genre TEXT,                           -- Comma-separated genres
    tags TEXT,                            -- Comma-separated tags
    status TEXT,                          -- Publication status
    format TEXT,                          -- Format type (e.g., "Manga")
    chapters INTEGER,                     -- Total chapter count
    volumes INTEGER,                      -- Total volume count

    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,

    FOREIGN KEY (library_id) REFERENCES libraries(id) ON DELETE CASCADE,
    UNIQUE(library_id, name)
);

CREATE INDEX idx_series_library ON series(library_id);
CREATE INDEX idx_series_name ON series(name);
CREATE INDEX idx_series_scanner_source ON series(scanner_source);
CREATE INDEX idx_series_scanned_at ON series(scanned_at);

-- Search performance indexes (added in migration 006)
CREATE INDEX IF NOT EXISTS idx_series_writer ON series(writer);
CREATE INDEX IF NOT EXISTS idx_series_artist ON series(artist);
CREATE INDEX IF NOT EXISTS idx_series_genre ON series(genre);
CREATE INDEX IF NOT EXISTS idx_series_tags ON series(tags);
CREATE INDEX IF NOT EXISTS idx_series_status ON series(status);
CREATE INDEX IF NOT EXISTS idx_series_publisher ON series(publisher);
CREATE INDEX IF NOT EXISTS idx_series_description ON series(description);
CREATE INDEX IF NOT EXISTS idx_series_display_name ON series(display_name);
CREATE INDEX IF NOT EXISTS idx_series_library_search ON series(library_id, name, writer, artist);


-- Link comics to series (many-to-many for omnibus editions)
CREATE TABLE series_comics (
    series_id INTEGER NOT NULL,
    comic_id INTEGER NOT NULL,
    issue_order INTEGER,                  -- Order within series

    PRIMARY KEY (series_id, comic_id),
    FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE CASCADE,
    FOREIGN KEY (comic_id) REFERENCES comics(id) ON DELETE CASCADE
);

CREATE INDEX idx_series_comics_series ON series_comics(series_id);
CREATE INDEX idx_series_comics_comic ON series_comics(comic_id);


-- ============================================================================
-- COLLECTIONS / READING LISTS
-- ============================================================================

CREATE TABLE collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    is_public INTEGER DEFAULT 0,          -- Boolean
    position INTEGER DEFAULT 0,           -- Sort order
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_collections_user ON collections(user_id);


CREATE TABLE collection_comics (
    collection_id INTEGER NOT NULL,
    comic_id INTEGER NOT NULL,
    position INTEGER DEFAULT 0,           -- Order within collection
    added_at INTEGER NOT NULL,

    PRIMARY KEY (collection_id, comic_id),
    FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE,
    FOREIGN KEY (comic_id) REFERENCES comics(id) ON DELETE CASCADE
);

CREATE INDEX idx_collection_comics_collection ON collection_comics(collection_id);
CREATE INDEX idx_collection_comics_comic ON collection_comics(comic_id);


-- ============================================================================
-- USERS (For future multi-user support)
-- ============================================================================

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email TEXT,
    is_admin INTEGER DEFAULT 0,           -- Boolean
    is_active INTEGER DEFAULT 1,          -- Boolean
    created_at INTEGER NOT NULL,
    last_login_at INTEGER
);

CREATE INDEX idx_users_username ON users(username);

-- Default admin user is created programmatically by Database.init_db()
-- with a properly hashed password. Do not use this raw SQL INSERT.
-- INSERT INTO users (id, username, password_hash, is_admin, is_active, created_at)
-- VALUES (1, 'admin', '<hashed>', 1, 1, strftime('%s', 'now'));


-- ============================================================================
-- USER PREFERENCES
-- ============================================================================

CREATE TABLE user_preferences (
    user_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    value TEXT,                           -- JSON or simple value

    PRIMARY KEY (user_id, key),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);


-- ============================================================================
-- FOLDER PREFERENCES (Sort modes, view settings)
-- ============================================================================

CREATE TABLE folder_preferences (
    user_id INTEGER NOT NULL,
    folder_id INTEGER NOT NULL,
    sort_mode TEXT DEFAULT 'folders_first', -- folders_first, alphabetical, date_added, recently_read
    view_mode TEXT DEFAULT 'grid',          -- grid, list

    PRIMARY KEY (user_id, folder_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (folder_id) REFERENCES folders(id) ON DELETE CASCADE
);


-- ============================================================================
-- READING STATISTICS
-- ============================================================================

CREATE TABLE reading_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    comic_id INTEGER NOT NULL,

    -- Stats
    total_read_time INTEGER DEFAULT 0,    -- Seconds
    page_turns INTEGER DEFAULT 0,
    sessions INTEGER DEFAULT 0,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (comic_id) REFERENCES comics(id) ON DELETE CASCADE,
    UNIQUE(user_id, comic_id)
);


-- ============================================================================
-- SESSIONS (For API session management)
-- ============================================================================

CREATE TABLE sessions (
    id TEXT PRIMARY KEY,                  -- Session UUID
    user_id INTEGER NOT NULL,

    -- Session state
    current_library_id INTEGER,
    current_comic_id INTEGER,

    -- Metadata
    user_agent TEXT,
    ip_address TEXT,
    created_at INTEGER NOT NULL,
    last_activity_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_expires ON sessions(expires_at);


-- ============================================================================
-- METADATA CACHE (For future external metadata providers)
-- ============================================================================

CREATE TABLE metadata_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comic_id INTEGER NOT NULL,
    source TEXT NOT NULL,                 -- comicvine, metron, manual, etc.
    data JSON NOT NULL,                   -- Full metadata response
    fetched_at INTEGER NOT NULL,

    FOREIGN KEY (comic_id) REFERENCES comics(id) ON DELETE CASCADE,
    UNIQUE(comic_id, source)
);


-- ============================================================================
-- DATABASE METADATA
-- ============================================================================

CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at INTEGER NOT NULL
);

INSERT INTO schema_version (version, applied_at)
VALUES (3, strftime('%s', 'now'));
