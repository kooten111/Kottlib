-- ============================================================================
-- LIBRARIES
-- ============================================================================

CREATE TABLE libraries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    path TEXT UNIQUE NOT NULL,

    -- NEW: Determines which scanner to use by default
    scanner_type TEXT DEFAULT 'comic',  -- 'comic', 'manga', 'nhentai', 'paper'

    -- Settings
    settings TEXT DEFAULT '{}',         -- JSON: exclude patterns, etc.

    -- Scan tracking
    scan_status TEXT DEFAULT 'pending',
    last_scan_started INTEGER,
    last_scan_completed INTEGER,

    -- Cached data
    cached_series_tree TEXT,            -- Precomputed JSON hierarchy
    tree_cache_updated_at INTEGER,

    -- Timestamps
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE INDEX idx_libraries_uuid ON libraries(uuid);
CREATE INDEX idx_libraries_path ON libraries(path);


-- ============================================================================
-- FOLDERS
-- ============================================================================

CREATE TABLE folders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    library_id INTEGER NOT NULL,
    parent_id INTEGER,

    name TEXT NOT NULL,
    path TEXT NOT NULL,

    -- NEW: YACReader uses this for folder cover thumbnails
    first_child_hash TEXT,

    -- User sorting
    position INTEGER DEFAULT 0,

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
    folder_id INTEGER,

    -- File metadata
    path TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    file_modified_at INTEGER NOT NULL,
    format TEXT NOT NULL,

    -- CHANGED: YACReader-compatible hash format
    -- Algorithm: hex(SHA1(first 512KB)) + str(file_size)
    -- Example: "a1b2c3d4e5f67890..." + "123456789"
    hash TEXT UNIQUE NOT NULL,

    -- ========================================================================
    -- CORE METADATA (Required for sorting/filtering in YACReader clients)
    -- ========================================================================
    title TEXT,
    series TEXT,
    normalized_series_name TEXT,
    volume TEXT,
    issue_number REAL,
    year INTEGER,
    month INTEGER,
    day INTEGER,
    publisher TEXT,

    -- Standard ComicInfo.xml credits
    writer TEXT,
    artist TEXT,
    penciller TEXT,
    inker TEXT,
    colorist TEXT,
    letterer TEXT,
    cover_artist TEXT,
    editor TEXT,

    -- Description
    description TEXT,

    -- Classification
    genre TEXT,
    language_iso TEXT,
    age_rating TEXT,
    imprint TEXT,
    format_type TEXT,
    is_color INTEGER,

    -- Series/Arc metadata
    story_arc TEXT,
    arc_number TEXT,
    arc_count INTEGER,
    alternate_series TEXT,
    alternate_number TEXT,
    alternate_count INTEGER,

    -- Characters/Teams/Locations
    characters TEXT,
    teams TEXT,
    locations TEXT,
    main_character_or_team TEXT,
    series_group TEXT,

    -- External IDs (YACReader compatible)
    comic_vine_id TEXT,
    web TEXT,

    -- ========================================================================
    -- NEW: FLEXIBLE SCANNER METADATA (JSON)
    -- ========================================================================
    -- This stores scanner-specific fields that don't map to standard columns
    -- Examples:
    --   Manga: {"circle": "X", "parody": "Y"}
    --   Papers: {"doi": "10.xxx", "abstract": "...", "citations": 42}
    --   Comics: {"variant_cover": "A", "printing": "2nd", "condition": "NM"}
    metadata_json TEXT,

    -- Scanner provenance
    scanner_source TEXT,           -- 'comicinfo', 'nhentai', 'anilist', 'filename'
    scanner_source_id TEXT,        -- External ID
    scanner_source_url TEXT,       -- Link to source
    scanned_at INTEGER,
    scan_confidence REAL,          -- 0.0-1.0

    -- Issue metadata
    is_bis INTEGER DEFAULT 0,
    count INTEGER,
    date TEXT,

    -- ========================================================================
    -- USER ANNOTATIONS
    -- ========================================================================
    notes TEXT,
    review TEXT,
    tags TEXT,
    rating REAL DEFAULT 0.0,

    -- ========================================================================
    -- READING METADATA
    -- ========================================================================
    num_pages INTEGER NOT NULL,
    reading_direction TEXT DEFAULT 'ltr',

    -- Display settings
    brightness INTEGER DEFAULT 0,
    contrast INTEGER DEFAULT 0,
    gamma REAL DEFAULT 1.0,

    -- Bookmarks
    bookmark1 INTEGER DEFAULT 0,
    bookmark2 INTEGER DEFAULT 0,
    bookmark3 INTEGER DEFAULT 0,

    -- ========================================================================
    -- COVER METADATA
    -- ========================================================================
    cover_page INTEGER DEFAULT 1,
    cover_hash TEXT,               -- Hash for generated thumbnail
    cover_size_ratio REAL DEFAULT 0.0,
    original_cover_size TEXT,

    -- ========================================================================
    -- TRACKING
    -- ========================================================================
    last_time_opened INTEGER,
    has_been_opened INTEGER DEFAULT 0,
    edited INTEGER DEFAULT 0,
    position INTEGER DEFAULT 0,

    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,

    FOREIGN KEY (library_id) REFERENCES libraries(id) ON DELETE CASCADE,
    FOREIGN KEY (folder_id) REFERENCES folders(id) ON DELETE SET NULL,
    UNIQUE(library_id, path)
);

-- Indexes (same as before, plus new ones)
CREATE INDEX idx_comics_library ON comics(library_id);
CREATE INDEX idx_comics_folder ON comics(folder_id);
CREATE INDEX idx_comics_hash ON comics(hash);
CREATE INDEX idx_comics_series ON comics(series);
CREATE INDEX idx_comics_normalized_series ON comics(normalized_series_name);
CREATE INDEX idx_comics_library_series ON comics(library_id, series);
CREATE INDEX idx_comics_scanner_source ON comics(scanner_source);
CREATE INDEX idx_comics_file_modified ON comics(file_modified_at);
CREATE INDEX idx_comics_folder_created ON comics(folder_id, created_at DESC);
CREATE INDEX idx_comics_library_created ON comics(library_id, created_at DESC);
CREATE INDEX idx_comics_library_path_created ON comics(library_id, path, created_at DESC);

-- Full-text search support (if using SQLite FTS5)
CREATE VIRTUAL TABLE IF NOT EXISTS comics_fts USING fts5(
    title, series, writer, penciller, publisher, description, tags,
    content=comics, content_rowid=id
);

-- Triggers to keep FTS index updated
CREATE TRIGGER comics_fts_insert AFTER INSERT ON comics BEGIN
  INSERT INTO comics_fts(rowid, title, series, writer, penciller, publisher, description, tags)
  VALUES (new.id, new.title, new.series, new.writer, new.penciller, new.publisher, new.description, new.tags);
END;

CREATE TRIGGER comics_fts_update AFTER UPDATE ON comics BEGIN
  UPDATE comics_fts SET
    title = new.title,
    series = new.series,
    writer = new.writer,
    penciller = new.penciller,
    publisher = new.publisher,
    description = new.description,
    tags = new.tags
  WHERE rowid = old.id;
END;

CREATE TRIGGER comics_fts_delete AFTER DELETE ON comics BEGIN
  DELETE FROM comics_fts WHERE rowid = old.id;
END;


-- ============================================================================
-- COVERS (Dual-format thumbnails)
-- ============================================================================

CREATE TABLE covers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comic_id INTEGER NOT NULL,
    type TEXT NOT NULL,            -- 'auto', 'custom'
    page_number INTEGER NOT NULL,

    -- Paths relative to covers directory
    jpeg_path TEXT NOT NULL,       -- 300px, mobile
    webp_path TEXT,                -- 400px, web

    generated_at INTEGER NOT NULL,

    FOREIGN KEY (comic_id) REFERENCES comics(id) ON DELETE CASCADE,
    UNIQUE(comic_id, type)
);

CREATE INDEX idx_covers_comic ON covers(comic_id);


-- ============================================================================
-- USERS & PROGRESS (Centralized in single DB)
-- ============================================================================

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email TEXT,
    is_admin INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at INTEGER NOT NULL,
    last_login_at INTEGER
);

CREATE INDEX idx_users_username ON users(username);


CREATE TABLE reading_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    comic_id INTEGER NOT NULL,

    -- Progress
    current_page INTEGER NOT NULL DEFAULT 0,
    total_pages INTEGER NOT NULL,
    progress_percent REAL NOT NULL DEFAULT 0.0,
    is_completed INTEGER NOT NULL DEFAULT 0,

    -- Timestamps
    started_at INTEGER NOT NULL,
    last_read_at INTEGER NOT NULL,
    completed_at INTEGER,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (comic_id) REFERENCES comics(id) ON DELETE CASCADE,
    UNIQUE(user_id, comic_id)
);

CREATE INDEX idx_reading_progress_user ON reading_progress(user_id);
CREATE INDEX idx_reading_progress_comic ON reading_progress(comic_id);
CREATE INDEX idx_reading_progress_user_last_read ON reading_progress(user_id, last_read_at DESC);


-- ============================================================================
-- SERIES (Auto-detected groupings)
-- ============================================================================

CREATE TABLE series (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    library_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    display_name TEXT,

    -- Metadata
    publisher TEXT,
    year_start INTEGER,
    year_end INTEGER,
    description TEXT,

    -- Stats (cached)
    comic_count INTEGER DEFAULT 0,
    total_issues INTEGER DEFAULT 0,

    -- Scanner metadata (for AniList, etc.)
    scanner_source TEXT,
    scanner_source_id TEXT,
    scanner_source_url TEXT,
    scanned_at INTEGER,
    scan_confidence REAL,

    -- Additional metadata
    writer TEXT,
    artist TEXT,
    genre TEXT,
    tags TEXT,
    status TEXT,
    format TEXT,
    chapters INTEGER,
    volumes INTEGER,

    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,

    FOREIGN KEY (library_id) REFERENCES libraries(id) ON DELETE CASCADE,
    UNIQUE(library_id, name)
);

CREATE INDEX idx_series_library ON series(library_id);
CREATE INDEX idx_series_name ON series(name);


-- ============================================================================
-- YACREADER COMPATIBILITY TABLES
-- ============================================================================

CREATE TABLE favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    comic_id INTEGER NOT NULL,
    added_at INTEGER NOT NULL,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (comic_id) REFERENCES comics(id) ON DELETE CASCADE,
    UNIQUE(user_id, comic_id)
);

CREATE TABLE labels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    color TEXT,
    created_at INTEGER NOT NULL,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, name)
);

CREATE TABLE comic_labels (
    comic_id INTEGER NOT NULL,
    label_id INTEGER NOT NULL,

    PRIMARY KEY (comic_id, label_id),
    FOREIGN KEY (comic_id) REFERENCES comics(id) ON DELETE CASCADE,
    FOREIGN KEY (label_id) REFERENCES labels(id) ON DELETE CASCADE
);

CREATE TABLE reading_lists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE reading_list_items (
    reading_list_id INTEGER NOT NULL,
    comic_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    added_at INTEGER NOT NULL,

    PRIMARY KEY (reading_list_id, comic_id),
    FOREIGN KEY (reading_list_id) REFERENCES reading_lists(id) ON DELETE CASCADE,
    FOREIGN KEY (comic_id) REFERENCES comics(id) ON DELETE CASCADE
);


-- ============================================================================
-- SESSIONS
-- ============================================================================

CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,

    current_library_id INTEGER,
    current_comic_id INTEGER,

    user_agent TEXT,
    ip_address TEXT,
    device_type TEXT,              -- 'web', 'mobile', 'desktop'

    created_at INTEGER NOT NULL,
    last_activity_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_expires ON sessions(expires_at);


-- ============================================================================
-- COLLECTIONS / READING LISTS (User-created)
-- ============================================================================

CREATE TABLE collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    is_public INTEGER DEFAULT 0,
    position INTEGER DEFAULT 0,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE collection_comics (
    collection_id INTEGER NOT NULL,
    comic_id INTEGER NOT NULL,
    position INTEGER DEFAULT 0,
    added_at INTEGER NOT NULL,

    PRIMARY KEY (collection_id, comic_id),
    FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE,
    FOREIGN KEY (comic_id) REFERENCES comics(id) ON DELETE CASCADE
);


-- ============================================================================
-- USER PREFERENCES
-- ============================================================================

CREATE TABLE user_preferences (
    user_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    value TEXT,

    PRIMARY KEY (user_id, key),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE folder_preferences (
    user_id INTEGER NOT NULL,
    folder_id INTEGER NOT NULL,
    sort_mode TEXT DEFAULT 'folders_first',
    view_mode TEXT DEFAULT 'grid',

    PRIMARY KEY (user_id, folder_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (folder_id) REFERENCES folders(id) ON DELETE CASCADE
);


-- ============================================================================
-- METADATA CACHE (External APIs)
-- ============================================================================

CREATE TABLE metadata_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comic_id INTEGER NOT NULL,
    source TEXT NOT NULL,
    data TEXT NOT NULL,            -- JSON
    fetched_at INTEGER NOT NULL,

    FOREIGN KEY (comic_id) REFERENCES comics(id) ON DELETE CASCADE,
    UNIQUE(comic_id, source)
);


-- ============================================================================
-- SCHEMA VERSION
-- ============================================================================

CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at INTEGER NOT NULL
);

INSERT INTO schema_version (version, applied_at)
VALUES (3, strftime('%s', 'now'));
