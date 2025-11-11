-- Migration 003: Add Series Tree Cache to Libraries
-- This migration adds caching fields to speed up series tree loading
-- Safe to run multiple times

-- Add cache fields to libraries table
ALTER TABLE libraries ADD COLUMN cached_series_tree TEXT;
ALTER TABLE libraries ADD COLUMN tree_cache_updated_at INTEGER;

-- Create index for cache timestamp lookups
CREATE INDEX IF NOT EXISTS idx_libraries_cache_updated ON libraries(tree_cache_updated_at);
