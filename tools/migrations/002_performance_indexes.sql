-- Performance Indexes Migration
-- Adds indexes to speed up common queries without changing schema structure
-- Safe to apply - no data changes, only performance improvements

-- ============================================================================
-- Comics Table Indexes
-- ============================================================================

-- Speed up searches by title (case-insensitive searches are common)
CREATE INDEX IF NOT EXISTS idx_comics_title ON comics(title COLLATE NOCASE);

-- Speed up searches by series (already exists but ensuring it's there)
-- CREATE INDEX IF NOT EXISTS idx_comics_series ON comics(series COLLATE NOCASE);

-- Speed up filtering by publisher
CREATE INDEX IF NOT EXISTS idx_comics_publisher ON comics(publisher COLLATE NOCASE);

-- Speed up year-based queries and sorting
CREATE INDEX IF NOT EXISTS idx_comics_year ON comics(year);

-- Speed up filename-based searches and sorting
CREATE INDEX IF NOT EXISTS idx_comics_filename ON comics(filename COLLATE NOCASE);

-- Composite index for library + series queries (very common pattern)
CREATE INDEX IF NOT EXISTS idx_comics_library_series ON comics(library_id, series COLLATE NOCASE);

-- Composite index for library + folder navigation
-- (Already exists as idx_comics_folder but adding explicit composite)
CREATE INDEX IF NOT EXISTS idx_comics_library_folder ON comics(library_id, folder_id);

-- Speed up queries for modified files (useful for re-scanning)
CREATE INDEX IF NOT EXISTS idx_comics_file_modified ON comics(file_modified_at);

-- ============================================================================
-- Reading Progress Indexes
-- ============================================================================

-- Composite index for "continue reading" queries (user + not completed + last read)
CREATE INDEX IF NOT EXISTS idx_reading_progress_continue ON reading_progress(user_id, is_completed, last_read_at DESC);

-- Composite index for completed comics by user
CREATE INDEX IF NOT EXISTS idx_reading_progress_completed ON reading_progress(user_id, is_completed, completed_at DESC);

-- Index for progress percentage (useful for "X% complete" queries)
CREATE INDEX IF NOT EXISTS idx_reading_progress_percent ON reading_progress(progress_percent);

-- ============================================================================
-- Series Table Indexes
-- ============================================================================

-- Speed up series name searches (case-insensitive)
-- CREATE INDEX IF NOT EXISTS idx_series_name ON series(name COLLATE NOCASE);

-- Composite index for library + name lookups
CREATE INDEX IF NOT EXISTS idx_series_library_name ON series(library_id, name COLLATE NOCASE);

-- Speed up sorting by year
CREATE INDEX IF NOT EXISTS idx_series_year_start ON series(year_start);

-- ============================================================================
-- Folders Table Indexes
-- ============================================================================

-- Composite index for path lookups within a library
CREATE INDEX IF NOT EXISTS idx_folders_library_path ON folders(library_id, path COLLATE NOCASE);

-- Index for folder name searches
CREATE INDEX IF NOT EXISTS idx_folders_name ON folders(name COLLATE NOCASE);

-- ============================================================================
-- Collections & Favorites Indexes
-- ============================================================================

-- Composite index for user's collections with position
CREATE INDEX IF NOT EXISTS idx_collections_user_position ON collections(user_id, position);

-- Composite index for favorites by user + creation date
CREATE INDEX IF NOT EXISTS idx_favorites_user_created ON favorites(user_id, created_at DESC);

-- ============================================================================
-- Reading Lists Indexes
-- ============================================================================

-- Composite index for reading list items with position (for ordering)
-- CREATE INDEX IF NOT EXISTS idx_reading_list_items_position ON reading_list_items(reading_list_id, position);

-- ============================================================================
-- Full-Text Search Support (Optional - SQLite FTS5)
-- ============================================================================

-- Note: Commented out by default. Uncomment if you want FTS5 support
-- This creates a virtual table for full-text search on comics
-- Requires SQLite compiled with FTS5 support

/*
CREATE VIRTUAL TABLE IF NOT EXISTS comics_fts USING fts5(
    title,
    series,
    filename,
    writer,
    publisher,
    description,
    genre,
    characters,
    content=comics,
    content_rowid=id
);

-- Triggers to keep FTS index in sync
CREATE TRIGGER IF NOT EXISTS comics_fts_insert AFTER INSERT ON comics BEGIN
    INSERT INTO comics_fts(rowid, title, series, filename, writer, publisher, description, genre, characters)
    VALUES (new.id, new.title, new.series, new.filename, new.writer, new.publisher, new.description, new.genre, new.characters);
END;

CREATE TRIGGER IF NOT EXISTS comics_fts_delete AFTER DELETE ON comics BEGIN
    DELETE FROM comics_fts WHERE rowid = old.id;
END;

CREATE TRIGGER IF NOT EXISTS comics_fts_update AFTER UPDATE ON comics BEGIN
    DELETE FROM comics_fts WHERE rowid = old.id;
    INSERT INTO comics_fts(rowid, title, series, filename, writer, publisher, description, genre, characters)
    VALUES (new.id, new.title, new.series, new.filename, new.writer, new.publisher, new.description, new.genre, new.characters);
END;
*/

-- ============================================================================
-- Statistics / Analytics Indexes
-- ============================================================================

-- Index for counting comics per library
CREATE INDEX IF NOT EXISTS idx_comics_library_count ON comics(library_id) WHERE library_id IS NOT NULL;

-- Index for finding unread comics
CREATE INDEX IF NOT EXISTS idx_comics_unread ON comics(id)
    WHERE id NOT IN (SELECT comic_id FROM reading_progress WHERE is_completed = 1);

-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Run these queries after applying migration to verify indexes were created:
-- SELECT name, sql FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%' ORDER BY name;
-- PRAGMA index_list(comics);
-- PRAGMA index_list(reading_progress);

-- ============================================================================
-- Performance Notes
-- ============================================================================

-- Expected improvements:
-- 1. Search queries: 3-10x faster (especially with COLLATE NOCASE indexes)
-- 2. Series grouping: 2-5x faster (library_series composite index)
-- 3. Continue reading: 5-10x faster (composite index on user+completed+last_read)
-- 4. Library browsing: 2-4x faster (library_folder composite index)
-- 5. Recently added/sorted queries: 2-3x faster (year, file_modified indexes)

-- Trade-offs:
-- - Slight increase in INSERT/UPDATE time (maintaining indexes)
-- - ~5-15% increase in database file size (index storage)
-- - Both are negligible compared to read performance gains

-- ============================================================================
-- Rollback (if needed)
-- ============================================================================

/*
-- To remove all indexes added by this migration:
DROP INDEX IF EXISTS idx_comics_title;
DROP INDEX IF EXISTS idx_comics_publisher;
DROP INDEX IF EXISTS idx_comics_year;
DROP INDEX IF EXISTS idx_comics_filename;
DROP INDEX IF EXISTS idx_comics_library_series;
DROP INDEX IF EXISTS idx_comics_library_folder;
DROP INDEX IF EXISTS idx_comics_file_modified;
DROP INDEX IF EXISTS idx_reading_progress_continue;
DROP INDEX IF EXISTS idx_reading_progress_completed;
DROP INDEX IF EXISTS idx_reading_progress_percent;
DROP INDEX IF EXISTS idx_series_library_name;
DROP INDEX IF EXISTS idx_series_year_start;
DROP INDEX IF EXISTS idx_folders_library_path;
DROP INDEX IF EXISTS idx_folders_name;
DROP INDEX IF EXISTS idx_collections_user_position;
DROP INDEX IF EXISTS idx_favorites_user_created;
DROP INDEX IF EXISTS idx_comics_library_count;
*/
