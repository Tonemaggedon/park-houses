#!/usr/bin/env node
// Merge the duplicate pairs listed in data/duplicate_merges.json.
//
// It calls the SAME mergePeopleInto the site's own merge button calls, so a
// merge from here and a merge from the Duplicate People page leave the record
// in exactly the same state - including the alias that stops a file written in
// the old spelling making the person for a third time.
//
// Every pair is checked before it runs: both people must exist, and neither may
// be present in the same census year at the same house as the other, because
// that is a family and not a duplicate. A pair that fails is skipped and named,
// and the rest still run.
//
//   railway run node tools_merge_duplicates.js          # show what would happen
//   railway run node tools_merge_duplicates.js --apply  # do it

const fs = require('fs');
const { Pool } = require('pg');
const { mergePeopleInto } = require('./merge_people');

const APPLY = process.argv.includes('--apply');

// Railway injects the internal host, which only resolves inside Railway's own
// network. The public URL is the one that works from a laptop.
const url = [process.env.DATABASE_PUBLIC_URL, process.env.DATABASE_URL]
  .find(v => v && !v.includes('railway.internal')) || process.env.DATABASE_URL;
if (!url) { console.error('No DATABASE_URL. Run with: railway run node tools_merge_duplicates.js'); process.exit(1); }

const pairs = JSON.parse(fs.readFileSync('data/duplicate_merges.json', 'utf8')).merges;
const pool = new Pool({ connectionString: url, ssl: { rejectUnauthorized: false } });

(async () => {
  const client = await pool.connect();
  let did = 0, skipped = 0;
  for (const p of pairs) {
    const { keep, drop, why } = p;
    const who = await client.query(
      'SELECT id, first_name, last_name, born_year FROM people WHERE id = ANY($1)', [[keep, drop]]);
    if (who.rows.length !== 2) {
      console.log(`  skip  #${keep} + #${drop} - one of them is not there (already merged?)`);
      skipped++; continue;
    }
    const clash = await client.query(`
      SELECT a.census_year, a.property_id FROM census_entries a
        JOIN census_entries b ON a.census_year=b.census_year AND a.property_id=b.property_id
       WHERE a.person_id=$1 AND b.person_id=$2 AND a.property_id IS NOT NULL LIMIT 1`, [keep, drop]);
    if (clash.rowCount) {
      const c = clash.rows[0];
      console.log(`  SKIP  #${keep} + #${drop} - both in house ${c.property_id} in ${c.census_year}. That is a family, not a duplicate.`);
      skipped++; continue;
    }
    const k = who.rows.find(r => r.id === keep), d = who.rows.find(r => r.id === drop);
    console.log(`  keep #${k.id} ${k.first_name} ${k.last_name} (b.${k.born_year || '?'})   <-   #${d.id} ${d.first_name} ${d.last_name} (b.${d.born_year || '?'})`);
    if (why) console.log(`        ${why}`);
    if (!APPLY) { did++; continue; }
    try {
      await client.query('BEGIN');
      await mergePeopleInto(client, keep, drop);
      await client.query('COMMIT');
      did++;
    } catch (e) {
      await client.query('ROLLBACK');
      console.log(`        FAILED: ${e.message}`);
      skipped++;
    }
  }
  console.log();
  console.log(APPLY ? `Merged ${did}. Skipped ${skipped}.`
                    : `${did} would be merged, ${skipped} skipped. Nothing written. Run again with --apply.`);
  client.release();
  await pool.end();
})();
