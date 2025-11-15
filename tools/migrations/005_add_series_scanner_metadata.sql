-- Migration: Add scanner metadata fields to series table
-- Date: 2025-11-15
-- Description: Adds scanner metadata tracking fields to the series table

-- Add scanner metadata fields
ALTER TABLE series ADD COLUMN scanner_source TEXT;
ALTER TABLE series ADD COLUMN scanner_source_id TEXT;
ALTER TABLE series ADD COLUMN scanner_source_url TEXT;
ALTER TABLE series ADD COLUMN scanned_at INTEGER;
ALTER TABLE series ADD COLUMN scan_confidence REAL;

-- Add additional metadata fields
ALTER TABLE series ADD COLUMN writer TEXT;
ALTER TABLE series ADD COLUMN artist TEXT;
ALTER TABLE series ADD COLUMN genre TEXT;
ALTER TABLE series ADD COLUMN tags TEXT;
ALTER TABLE series ADD COLUMN status TEXT;
ALTER TABLE series ADD COLUMN format TEXT;
ALTER TABLE series ADD COLUMN chapters INTEGER;
ALTER TABLE series ADD COLUMN volumes INTEGER;

-- Create index on scanner_source for faster queries
CREATE INDEX IF NOT EXISTS idx_series_scanner_source ON series(scanner_source);
CREATE INDEX IF NOT EXISTS idx_series_scanned_at ON series(scanned_at);
