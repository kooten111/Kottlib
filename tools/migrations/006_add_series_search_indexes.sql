-- Migration 006: Add Search Indexes for Series Metadata
-- Add indexes to improve search performance on series metadata fields

-- Create indexes for searchable text fields
CREATE INDEX IF NOT EXISTS idx_series_writer ON series(writer);
CREATE INDEX IF NOT EXISTS idx_series_artist ON series(artist);
CREATE INDEX IF NOT EXISTS idx_series_genre ON series(genre);
CREATE INDEX IF NOT EXISTS idx_series_tags ON series(tags);
CREATE INDEX IF NOT EXISTS idx_series_status ON series(status);
CREATE INDEX IF NOT EXISTS idx_series_publisher ON series(publisher);
CREATE INDEX IF NOT EXISTS idx_series_description ON series(description);
CREATE INDEX IF NOT EXISTS idx_series_display_name ON series(display_name);

-- Composite index for common search scenarios
CREATE INDEX IF NOT EXISTS idx_series_library_search ON series(library_id, name, writer, artist);
