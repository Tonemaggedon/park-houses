// One person entered twice, made one again.
//
// Lifted out of server.js so the site and the command line run the SAME merge.
// Twenty-odd statements have to happen in the right order - fill the keeper's
// blanks, move every link, collapse what the move duplicates, and leave an
// alias behind so a file still written in the old spelling finds the keeper
// instead of making the person for a third time. Two copies of that would
// drift apart, and the day they did nobody would notice.
//
// The caller owns the transaction: pass a client already inside BEGIN.

async function mergePeopleInto(client, keepId, deleteId) {
  // Fill biographical gaps on the kept person from the deleted person
  await client.query(`
    UPDATE people SET
      known_as       = COALESCE(known_as,       (SELECT known_as       FROM people WHERE id=$2)),
      born_date      = COALESCE(born_date,      (SELECT born_date      FROM people WHERE id=$2)),
      born_year      = COALESCE(born_year,      (SELECT born_year      FROM people WHERE id=$2)),
      born_place     = COALESCE(born_place,     (SELECT born_place     FROM people WHERE id=$2)),
      died_date      = COALESCE(died_date,      (SELECT died_date      FROM people WHERE id=$2)),
      died_year      = COALESCE(died_year,      (SELECT died_year      FROM people WHERE id=$2)),
      died_place     = COALESCE(died_place,     (SELECT died_place     FROM people WHERE id=$2)),
      photo_url      = COALESCE(photo_url,      (SELECT photo_url      FROM people WHERE id=$2)),
      wikipedia_url  = COALESCE(wikipedia_url,  (SELECT wikipedia_url  FROM people WHERE id=$2)),
      grave_location = COALESCE(grave_location, (SELECT grave_location FROM people WHERE id=$2)),
      grave_number   = COALESCE(grave_number,   (SELECT grave_number   FROM people WHERE id=$2)),
      bio = CASE
        WHEN bio IS NULL THEN (SELECT bio FROM people WHERE id=$2)
        WHEN (SELECT bio FROM people WHERE id=$2) IS NULL THEN bio
        ELSE bio || E'\n\n' || (SELECT bio FROM people WHERE id=$2)
      END
    WHERE id=$1
  `, [keepId, deleteId]);

  await client.query('UPDATE census_entries    SET person_id=$1 WHERE person_id=$2', [keepId, deleteId]);
  // Merging a person who was imported twice leaves them with two records of
  // the same census night in the same house — and the crowding page would go
  // on counting both. Nobody is in one house twice in one year, so collapse
  // them, keeping the fuller row.
  await client.query(`
    DELETE FROM census_entries WHERE id IN (
      SELECT id FROM (
        SELECT id, ROW_NUMBER() OVER (
          PARTITION BY person_id, census_year, COALESCE(property_id, -1)
          ORDER BY (occupation_at_census IS NOT NULL)::int
                 + (birth_place IS NOT NULL)::int
                 + (relationship IS NOT NULL)::int
                 + (age_at_census IS NOT NULL)::int
                 + (marital_status IS NOT NULL)::int DESC, id) AS rn
          FROM census_entries WHERE person_id=$1
      ) t WHERE rn > 1)`, [keepId]);
  await client.query('UPDATE occupations       SET person_id=$1 WHERE person_id=$2', [keepId, deleteId]);
  await client.query('UPDATE people_places     SET person_id=$1 WHERE person_id=$2', [keepId, deleteId]);
  await client.query('UPDATE person_media      SET person_id=$1 WHERE person_id=$2', [keepId, deleteId]);
  await client.query('UPDATE person_links      SET person_id=$1 WHERE person_id=$2', [keepId, deleteId]);
  await client.query('UPDATE bibliography      SET author_person_id=$1 WHERE author_person_id=$2', [keepId, deleteId]);
  try {
    await client.query('UPDATE property_residents SET person_id=$1 WHERE person_id=$2', [keepId, deleteId]);
    // Both records were linked to the same house, so the merge leaves the link
    // sitting there twice. Collapse it rather than leave work for the tool that
    // clears duplicate links.
    await client.query(`
      DELETE FROM property_residents WHERE id IN (
        SELECT id FROM (
          SELECT id, ROW_NUMBER() OVER (PARTITION BY person_id, property_id ORDER BY id) AS rn
            FROM property_residents WHERE person_id=$1
        ) t WHERE rn > 1)`, [keepId]);
  } catch(_) {}
  // The same job entered from two spellings of one name is one job.
  await client.query(`
    DELETE FROM occupations WHERE id IN (
      SELECT id FROM (
        SELECT id, ROW_NUMBER() OVER (
          PARTITION BY person_id, LOWER(occupation), from_year, to_year
          ORDER BY (employer IS NOT NULL)::int + (notes IS NOT NULL)::int DESC, id) AS rn
          FROM occupations WHERE person_id=$1
      ) t WHERE rn > 1)`, [keepId]);

  // Relationships: drop conflicts first, then reassign, then clean up
  await client.query(`DELETE FROM people_relationships WHERE person_a_id=$2 AND (person_b_id, relationship) IN (SELECT person_b_id, relationship FROM people_relationships WHERE person_a_id=$1)`, [keepId, deleteId]);
  await client.query(`DELETE FROM people_relationships WHERE person_b_id=$2 AND (person_a_id, relationship) IN (SELECT person_a_id, relationship FROM people_relationships WHERE person_b_id=$1)`, [keepId, deleteId]);
  await client.query('UPDATE people_relationships SET person_a_id=$1 WHERE person_a_id=$2', [keepId, deleteId]);
  await client.query('UPDATE people_relationships SET person_b_id=$1 WHERE person_b_id=$2', [keepId, deleteId]);
  await client.query('DELETE FROM people_relationships WHERE person_a_id=person_b_id');
  await client.query(`DELETE FROM people_relationships WHERE id IN (
    SELECT a.id FROM people_relationships a
    JOIN people_relationships b ON a.person_a_id=b.person_a_id AND a.person_b_id=b.person_b_id
      AND a.relationship=b.relationship AND a.id > b.id
  )`);

  // Remember what the absorbed person was called, so a file still written in
  // that spelling finds the keeper instead of making the person again. Only
  // where the spellings actually differ: an alias pointing a name at itself
  // says nothing. If that name has been merged away before, the older alias
  // stands — it was recorded closer to the event.
  await client.query(`
    INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
    SELECT $1, p.first_name, p.last_name, p.born_year, 'merge'
      FROM people p
     WHERE p.id = $2
       AND COALESCE(TRIM(p.first_name),'') <> ''
       AND COALESCE(TRIM(p.last_name),'') <> ''
       AND NOT EXISTS (
         SELECT 1 FROM people k WHERE k.id = $1
            AND LOWER(TRIM(k.first_name)) = LOWER(TRIM(p.first_name))
            AND LOWER(TRIM(k.last_name))  = LOWER(TRIM(p.last_name)))
    ON CONFLICT DO NOTHING`, [keepId, deleteId]);
  // An alias that pointed at the absorbed person now points at the keeper.
  await client.query('UPDATE person_alias SET person_id=$1 WHERE person_id=$2', [keepId, deleteId]);

  await client.query('DELETE FROM people WHERE id=$1', [deleteId]);
}

module.exports = { mergePeopleInto };
