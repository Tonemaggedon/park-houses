-- Add birth_place column to census_entries
ALTER TABLE census_entries ADD COLUMN IF NOT EXISTS birth_place TEXT;

-- Geocode cache table
CREATE TABLE IF NOT EXISTS geocode_cache (
  place_text TEXT PRIMARY KEY,
  lat DOUBLE PRECISION,
  lng DOUBLE PRECISION,
  status TEXT DEFAULT 'unknown',
  formatted_address TEXT
);
