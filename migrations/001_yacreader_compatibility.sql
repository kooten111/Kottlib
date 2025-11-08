-- Migration: YACReader API Compatibility
-- Date: 2025-11-08
-- Description: Add missing fields for full YACReader API compatibility

-- ============================================================================
-- COMICS TABLE - Extended Metadata
-- ============================================================================

-- Extended ComicInfo.xml metadata
ALTER TABLE comics ADD COLUMN IF NOT EXISTS penciller TEXT;
ALTER TABLE comics ADD COLUMN IF NOT EXISTS inker TEXT;
ALTER TABLE comics ADD COLUMN IF NOT EXISTS colorist TEXT;
ALTER TABLE comics ADD COLUMN IF NOT EXISTS letterer TEXT;
ALTER TABLE comics ADD COLUMN IF NOT EXISTS cover_artist TEXT;
ALTER TABLE comics ADD COLUMN IF NOT EXISTS editor TEXT;

-- Series/Arc metadata
ALTER TABLE comics ADD COLUMN IF NOT EXISTS story_arc TEXT;
ALTER TABLE comics ADD COLUMN IF NOT EXISTS arc_number TEXT;
ALTER TABLE comics ADD COLUMN IF NOT EXISTS arc_count INTEGER;

-- Alternate series
ALTER TABLE comics ADD COLUMN IF NOT EXISTS alternate_series TEXT;
ALTER TABLE comics ADD COLUMN IF NOT EXISTS alternate_number TEXT;
ALTER TABLE comics ADD COLUMN IF NOT EXISTS alternate_count INTEGER;

-- Additional metadata
ALTER TABLE comics ADD COLUMN IF NOT EXISTS genre TEXT;
ALTER TABLE comics ADD COLUMN IF NOT EXISTS language_iso TEXT;
ALTER TABLE comics ADD COLUMN IF NOT EXISTS age_rating TEXT;
ALTER TABLE comics ADD COLUMN IF NOT EXISTS imprint TEXT;
ALTER TABLE comics ADD COLUMN IF NOT EXISTS format_type TEXT;
ALTER TABLE comics ADD COLUMN IF NOT EXISTS is_color BOOLEAN;

-- Characters, teams, locations
ALTER TABLE comics ADD COLUMN IF NOT EXISTS characters TEXT;
ALTER TABLE comics ADD COLUMN IF NOT EXISTS teams TEXT;
ALTER TABLE comics ADD COLUMN IF NOT EXISTS locations TEXT;
ALTER TABLE comics ADD COLUMN IF NOT EXISTS main_character_or_team TEXT;

-- Series organization
ALTER TABLE comics ADD COLUMN IF NOT EXISTS series_group TEXT;

-- User content
ALTER TABLE comics ADD COLUMN IF NOT EXISTS notes TEXT;
ALTER TABLE comics ADD COLUMN IF NOT EXISTS review TEXT;
ALTER TABLE comics ADD COLUMN IF NOT EXISTS tags TEXT;

-- External IDs
ALTER TABLE comics ADD COLUMN IF NOT EXISTS comic_vine_id TEXT;

-- Issue metadata
ALTER TABLE comics ADD COLUMN IF NOT EXISTS is_bis BOOLEAN DEFAULT FALSE;
ALTER TABLE comics ADD COLUMN IF NOT EXISTS count INTEGER;
ALTER TABLE comics ADD COLUMN IF NOT EXISTS date TEXT;

-- Display settings (per-comic)
ALTER TABLE comics ADD COLUMN IF NOT EXISTS rating REAL DEFAULT 0.0;
ALTER TABLE comics ADD COLUMN IF NOT EXISTS brightness INTEGER DEFAULT 0;
ALTER TABLE comics ADD COLUMN IF NOT EXISTS contrast INTEGER DEFAULT 0;
ALTER TABLE comics ADD COLUMN IF NOT EXISTS gamma REAL DEFAULT 1.0;

-- Bookmarks (page numbers)
ALTER TABLE comics ADD COLUMN IF NOT EXISTS bookmark1 INTEGER DEFAULT 0;
ALTER TABLE comics ADD COLUMN IF NOT EXISTS bookmark2 INTEGER DEFAULT 0;
ALTER TABLE comics ADD COLUMN IF NOT EXISTS bookmark3 INTEGER DEFAULT 0;

-- Cover info
ALTER TABLE comics ADD COLUMN IF NOT EXISTS cover_page INTEGER DEFAULT 1;
ALTER TABLE comics ADD COLUMN IF NOT EXISTS cover_size_ratio REAL DEFAULT 0.0;
ALTER TABLE comics ADD COLUMN IF NOT EXISTS original_cover_size TEXT;

-- Access tracking
ALTER TABLE comics ADD COLUMN IF NOT EXISTS last_time_opened INTEGER;
ALTER TABLE comics ADD COLUMN IF NOT EXISTS has_been_opened BOOLEAN DEFAULT FALSE;
ALTER TABLE comics ADD COLUMN IF NOT EXISTS edited BOOLEAN DEFAULT FALSE;

-- ============================================================================
-- SESSIONS TABLE - Device Tracking
-- ============================================================================

ALTER TABLE sessions ADD COLUMN IF NOT EXISTS device_type TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS display_type TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS downloaded_comics TEXT;

-- ============================================================================
-- NEW TABLES - Favorites, Labels, Reading Lists
-- ============================================================================

-- Favorites
CREATE TABLE IF NOT EXISTS favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    library_id INTEGER NOT NULL,
    comic_id INTEGER NOT NULL,
    created_at INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (library_id) REFERENCES libraries (id) ON DELETE CASCADE,
    FOREIGN KEY (comic_id) REFERENCES comics (id) ON DELETE CASCADE,
    UNIQUE (user_id, comic_id)
);

CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites (user_id);
CREATE INDEX IF NOT EXISTS idx_favorites_library ON favorites (library_id);
CREATE INDEX IF NOT EXISTS idx_favorites_comic ON favorites (comic_id);

-- Labels/Tags
CREATE TABLE IF NOT EXISTS labels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    library_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    color_id INTEGER DEFAULT 0,
    position INTEGER DEFAULT 0,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    FOREIGN KEY (library_id) REFERENCES libraries (id) ON DELETE CASCADE,
    UNIQUE (library_id, name)
);

CREATE INDEX IF NOT EXISTS idx_labels_library ON labels (library_id);

-- Comic-Label junction table
CREATE TABLE IF NOT EXISTS comic_labels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comic_id INTEGER NOT NULL,
    label_id INTEGER NOT NULL,
    created_at INTEGER NOT NULL,
    FOREIGN KEY (comic_id) REFERENCES comics (id) ON DELETE CASCADE,
    FOREIGN KEY (label_id) REFERENCES labels (id) ON DELETE CASCADE,
    UNIQUE (comic_id, label_id)
);

CREATE INDEX IF NOT EXISTS idx_comic_labels_comic ON comic_labels (comic_id);
CREATE INDEX IF NOT EXISTS idx_comic_labels_label ON comic_labels (label_id);

-- Reading Lists
CREATE TABLE IF NOT EXISTS reading_lists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    library_id INTEGER NOT NULL,
    user_id INTEGER,
    name TEXT NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    position INTEGER DEFAULT 0,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    FOREIGN KEY (library_id) REFERENCES libraries (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_reading_lists_library ON reading_lists (library_id);
CREATE INDEX IF NOT EXISTS idx_reading_lists_user ON reading_lists (user_id);

-- Reading List Items junction table
CREATE TABLE IF NOT EXISTS reading_list_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reading_list_id INTEGER NOT NULL,
    comic_id INTEGER NOT NULL,
    position INTEGER DEFAULT 0,
    added_at INTEGER NOT NULL,
    FOREIGN KEY (reading_list_id) REFERENCES reading_lists (id) ON DELETE CASCADE,
    FOREIGN KEY (comic_id) REFERENCES comics (id) ON DELETE CASCADE,
    UNIQUE (reading_list_id, comic_id)
);

CREATE INDEX IF NOT EXISTS idx_reading_list_items_list ON reading_list_items (reading_list_id);
CREATE INDEX IF NOT EXISTS idx_reading_list_items_comic ON reading_list_items (comic_id);
CREATE INDEX IF NOT EXISTS idx_reading_list_items_position ON reading_list_items (reading_list_id, position);

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
