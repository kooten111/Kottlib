-- Migration: Add scanner metadata fields to comics table
-- Date: 2025-11-14
-- Description: Adds fields to track scanner metadata for each comic

BEGIN TRANSACTION;

-- Add scanner metadata fields
ALTER TABLE comics ADD COLUMN web TEXT;
ALTER TABLE comics ADD COLUMN scanner_source TEXT;
ALTER TABLE comics ADD COLUMN scanner_source_id TEXT;
ALTER TABLE comics ADD COLUMN scanner_source_url TEXT;
ALTER TABLE comics ADD COLUMN scanned_at INTEGER;
ALTER TABLE comics ADD COLUMN scan_confidence REAL;

-- Add indexes for scanner fields to improve query performance
CREATE INDEX IF NOT EXISTS idx_comics_scanner_source ON comics(scanner_source);
CREATE INDEX IF NOT EXISTS idx_comics_scanned_at ON comics(scanned_at);

COMMIT;
