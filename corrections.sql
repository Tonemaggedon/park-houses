-- Park Houses — data corrections
-- Run in Railway PostgreSQL console (or psql)

-- ════════════════════════════════════════════════════════════════
-- SECTION 1: New grouping columns for census-unresolved page
-- Run this after deploying the code that adds the columns,
-- OR paste manually in Railway SQL editor.
-- ════════════════════════════════════════════════════════════════

-- 1921 Newcastle Circus — set household numbers based on count_house
-- Household 1 = the Hind / Ramsden / Selby / Sugars / Marrows / Baldry group
-- Household 2 = the Paget / Rossignot / Horne / Holmes / Harris group
-- (adjust the person_ids or unresolved_address pattern to match actual data)
UPDATE census_entries
SET census_household_num = 1
WHERE census_year = 1921
  AND unresolved_address ILIKE '%Newcastle%Circus%'
  AND person_id IN (
    SELECT id FROM people
    WHERE last_name IN ('Hind','Ramsden','Selby','Sugars','Marrows','Baldry')
  );

UPDATE census_entries
SET census_household_num = 2
WHERE census_year = 1921
  AND unresolved_address ILIKE '%Newcastle%Circus%'
  AND person_id IN (
    SELECT id FROM people
    WHERE last_name IN ('Paget','Rossignot','Horne','Holmes','Harris')
  );

-- Alternatively, if unresolved_address already has "1 Newcastle Circus" / "2 Newcastle Circus":
-- UPDATE census_entries SET census_household_num = 1
--   WHERE census_year = 1921 AND unresolved_address ILIKE '1 Newcastle%';
-- UPDATE census_entries SET census_household_num = 2
--   WHERE census_year = 1921 AND unresolved_address ILIKE '2 Newcastle%';

-- 1911 Pelham Crescent — set census_house_id from the PC number pattern
-- Each PC# maps to a property (e.g. PC7=14 Pelham Cres, PC8=5 Pelham Cres, etc.)
-- This reads the leading house-code from unresolved_address if stored as "PC7 Pelham Crescent"
UPDATE census_entries
SET census_house_id = substring(unresolved_address from '^([A-Z]+\d+)')
WHERE census_year = 1911
  AND property_id IS NULL
  AND unresolved_address ~ '^[A-Z]+\d+';

-- ════════════════════════════════════════════════════════════════
-- SECTION 2: Individual person corrections
-- ════════════════════════════════════════════════════════════════

-- Person 1092: occupation Cook (not servant), age 62
-- This is a 1921 census entry; born_year = 1921 - 62 = 1859
UPDATE census_entries
SET occupation_at_census = 'Cook',
    age_at_census = 62
WHERE person_id = 1092
  AND census_year = 1921;

UPDATE people SET born_year = 1859 WHERE id = 1092 AND born_year IS NULL;

