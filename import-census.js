#!/usr/bin/env node
/**
 * Census data importer for Nottingham Park Houses
 * Usage: DATABASE_URL="..." node import-census.js
 *
 * Add entries to the CENSUS_DATA array below, then run the script.
 * Each entry: { propId, year, people: [...] }
 */

const { Pool } = require('pg');

const db = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

function extractYear(str) {
  if (!str) return null;
  if (typeof str === 'number') return str;
  const m = String(str).match(/\b(1[0-9]{3}|20[0-2][0-9])\b/);
  return m ? parseInt(m[1]) : null;
}

// ─────────────────────────────────────────────────────────────────
// ADD CENSUS ENTRIES HERE
// Fields per person:
//   first_name, last_name, known_as (optional), born_date,
//   sex, occupation, marital_status, relationship (optional)
// ─────────────────────────────────────────────────────────────────
const CENSUS_DATA = [

  {
    propId: 189,
    year: 1939,
    people: [
      { first_name: 'William H', last_name: 'Heaton',         born_date: '26 Sep 1856', sex: 'Male',   occupation: 'College Principal (Retired)', marital_status: 'Married',  relationship: 'Head'      },
      { first_name: 'Anne S',    last_name: 'Heaton',         born_date: '01 Dec 1865', sex: 'Female', occupation: 'Domestic Duties',             marital_status: 'Married',  relationship: 'Wife'      },
      { first_name: 'Margaret',  last_name: 'Heaton',         born_date: '13 Apr 1900', sex: 'Female', occupation: 'Private Means',               marital_status: 'Single',   relationship: 'Daughter'  },
      { first_name: 'Nancy J',   last_name: 'Heaton',         born_date: '22 Jun 1902', sex: 'Female', occupation: 'Private Means',               marital_status: 'Single',   relationship: 'Daughter'  },
      { first_name: 'Minnie',    last_name: 'Dunant',         born_date: '29 Apr 1875', sex: 'Female', occupation: 'Cook',                        marital_status: 'Single',   relationship: 'Servant'   },
      { first_name: 'Sarah J',   last_name: 'Thorpe', known_as: 'Sarah J Thorpe (née Wyld)', born_date: '25 Oct 1904', sex: 'Female', occupation: 'Housemaid', marital_status: 'Single', relationship: 'Servant' },
    ]
  },

  {
    propId: 188,
    year: 1939,
    people: [
      { first_name: 'Emily',   last_name: 'Brown',   born_date: '03 Jul 1878', sex: 'Female', occupation: 'Housekeeper',   marital_status: 'Single', relationship: 'Housekeeper' },
      { first_name: 'Minnie',  last_name: 'Willmot', born_date: '26 Jul 1884', sex: 'Female', occupation: 'Cook',           marital_status: 'Single', relationship: 'Servant'     },
      { first_name: 'Edith',   last_name: 'Kirk',    born_date: '11 Nov 1915', sex: 'Female', occupation: "Ladies' Maid",   marital_status: 'Single', relationship: 'Servant'     },
      { first_name: 'Phyllis', last_name: 'Sleigh',  known_as: 'Phyllis Sleigh (née Meakin)',   born_date: '28 Sep 1912', sex: 'Female', occupation: 'Parlour Maid', marital_status: 'Single', relationship: 'Servant' },
      { first_name: 'Annie',   last_name: 'Mason',   known_as: 'Annie Mason (née Madgelt)',     born_date: '09 May 1922', sex: 'Female', occupation: 'Housemaid',   marital_status: 'Single', relationship: 'Servant' },
      { first_name: 'Lilian',  last_name: 'Gannon',  known_as: 'Lilian Gannon (née Brailford)', born_date: '07 Oct 1924', sex: 'Female', occupation: 'Kitchen Maid', marital_status: 'Single', relationship: 'Servant' },
    ]
  },

  {
    propId: 187,
    year: 1939,
    people: [
      { first_name: '[Unknown]', last_name: 'Kirk',      known_as: 'Mr Kirk (first name redacted in register)', born_date: '01 May 1876', sex: 'Male',    occupation: 'Bank Manager',                  marital_status: 'Married', relationship: 'Head'     },
      { first_name: 'Gertrude E', last_name: 'Kirk',     born_date: '08 Aug 1876', sex: 'Female', occupation: '',                              marital_status: 'Married', relationship: 'Wife'     },
      { first_name: 'Helen M G',  last_name: 'Woodward', born_date: '25 May 1914', sex: 'Female', occupation: 'Unpaid Domestic Duties',         marital_status: 'Married', relationship: 'Relative' },
      { first_name: 'Gladys',     last_name: 'Smith',    known_as: 'Gladys Smith (née Hollingworth)',  born_date: '19 Feb 1910', sex: 'Female', occupation: 'Cook',          marital_status: 'Single',  relationship: 'Servant'  },
      { first_name: 'Alice A',    last_name: 'Allen',    known_as: 'Alice A Allen (née Sutton)',       born_date: '02 Nov 1913', sex: 'Female', occupation: 'Housemaid',     marital_status: 'Single',  relationship: 'Servant'  },
      { first_name: 'Walter S',   last_name: 'Sission',  born_date: '23 Jul 1874', sex: 'Male',   occupation: 'Contractor For Food Supplies',  marital_status: 'Married', relationship: 'Lodger'   },
      { first_name: 'Margaret F', last_name: 'Sission',  born_date: '13 Nov 1882', sex: 'Female', occupation: 'Unpaid Domestic Duties',         marital_status: 'Married', relationship: 'Lodger'   },
      { first_name: 'Louise E',   last_name: 'Sission',  born_date: '17 Jan 1878', sex: 'Female', occupation: 'Librarian',                      marital_status: 'Single',  relationship: 'Lodger'   },
      { first_name: 'Eliza',      last_name: 'Gose',     born_date: '14 Oct 1860', sex: 'Female', occupation: 'Private Means',                  marital_status: 'Widowed', relationship: 'Lodger'   },
      { first_name: 'Mabel J',    last_name: 'Baldwin',  known_as: 'Mabel J Baldwin (née Gose)',      born_date: '09 Feb 1891', sex: 'Female', occupation: 'Private Means', marital_status: 'Single',  relationship: 'Lodger'   },
    ]
  },

  {
    propId: 182,
    year: 1939,
    people: [
      { first_name: 'Ellen M', last_name: 'Cowell',   born_date: '14 Sep 1857', sex: 'Female', occupation: 'Unpaid Domestic Duties', marital_status: 'Single',  relationship: 'Head'    },
      { first_name: 'Rose',    last_name: 'Hartmoll', known_as: 'Rose Ann Hartmoll', born_date: '28 Nov 1880', sex: 'Female', occupation: 'Domestic', marital_status: 'Married', relationship: 'Servant' },
    ]
  },

  {
    propId: 305,
    year: 1939,
    // Two schedules (238 & 241) suggest two separate households within the property
    people: [
      { first_name: 'Elsie L',    last_name: 'Manning',  born_date: '21 May 1865', sex: 'Female', occupation: 'Unpaid Domestic Duties', marital_status: 'Widowed', relationship: 'Head (Schedule 238)'    },
      { first_name: 'Agneta E',   last_name: 'Bevan',    born_date: '23 Jan 1871', sex: 'Female', occupation: 'Unpaid Domestic Duties', marital_status: 'Single',  relationship: 'Resident (Schedule 238)' },
      { first_name: 'Jemima',     last_name: 'Gregory',  born_date: '04 Dec',      sex: 'Female', occupation: 'Paid Domestic Duties',   marital_status: 'Single',  relationship: 'Servant (Schedule 238)'  },
      { first_name: 'Ada M',      last_name: 'Lowe',     born_date: '21 Nov 1869', sex: 'Female', occupation: 'Unpaid Domestic Duties', marital_status: 'Single',  relationship: 'Head (Schedule 241)'    },
      { first_name: 'Clarebell',  last_name: 'Mills',    born_date: '03 Jan 1891', sex: 'Female', occupation: 'Housekeeper',            marital_status: 'Single',  relationship: 'Servant (Schedule 241)'  },
    ]
  },

  {
    propId: 301,
    year: 1939,
    // Sub-number 6 is officially closed (sealed record — person born after 1920, still living)
    people: [
      { first_name: 'James',      last_name: 'Curnow',     born_date: '05 May 1864', sex: 'Male',   occupation: 'Fruit Merchant / Farmer',                       marital_status: 'Married', relationship: 'Head'     },
      { first_name: 'Edith',      last_name: 'Curnow',     born_date: '01 Aug 1872', sex: 'Female', occupation: 'Private Means',                                 marital_status: 'Married', relationship: 'Wife'     },
      { first_name: 'John J',     last_name: 'Curnow',     born_date: '01 Jan 1902', sex: 'Male',   occupation: 'Wholesale Fruit Merchant / Salesman / Farmer',  marital_status: 'Married', relationship: 'Son'      },
      { first_name: 'Ena H',      last_name: 'Boothroyd',  known_as: 'Ena H Boothroyd (née Curnow)', born_date: '12 Oct 1905', sex: 'Female', occupation: 'Private Means', marital_status: 'Single', relationship: 'Daughter' },
      { first_name: 'Elizabeth D',last_name: 'Robinson',   known_as: 'Elizabeth D Robinson (née Pears)', born_date: '21 May 1907', sex: 'Female', occupation: 'Private Means', marital_status: 'Married', relationship: 'Relative' },
      { first_name: '[Unknown]',  last_name: 'Sawer',      known_as: '[Unknown] Sawer (née Marshall) — first name sealed in register', born_date: '05 May 1923', sex: 'Female', occupation: 'Domestic Servant', marital_status: 'Single', relationship: 'Servant'  },
      { first_name: 'Ivy',        last_name: 'Hayes',      known_as: 'Ivy Hayes (née Swift)', born_date: '15 Feb 1921', sex: 'Female', occupation: 'Domestic Servant', marital_status: 'Single', relationship: 'Servant'  },
    ]
  },

  {
    propId: 303,
    year: 1939,
    people: [
      { first_name: 'George',   last_name: 'Halland',         born_date: '18 Oct 1871', sex: 'Male',   occupation: 'Coal Merchant / Estate Agent', marital_status: 'Widowed', relationship: 'Head'        },
      { first_name: 'Martha L', last_name: 'Withames',        born_date: '30 Jun 1889', sex: 'Female', occupation: 'Housekeeper',                  marital_status: 'Single',  relationship: 'Housekeeper' },
      { first_name: 'Florence', last_name: 'Morley-Williams', born_date: '16 Jun 1916', sex: 'Female', occupation: 'Domestic',                     marital_status: 'Single',  relationship: 'Servant'     },
    ]
  },

  // ── Add more properties below ──────────────────────────────────

];

// ─────────────────────────────────────────────────────────────────
// ARCHITECT / BUILDER CENSUS ENTRIES
// These people lived outside The Park. Only the named architect is
// added/updated — family members and servants are NOT imported.
// ─────────────────────────────────────────────────────────────────
const ARCHITECT_DATA = [

  {
    census_year: 1921,
    address: '130 Foxhall Road, Nottingham',
    first_name: 'Lawrence Lee', last_name: 'Bright',
    born_year: 1872, sex: 'Male',
    occupation: 'Architect', marital_status: 'Married', relationship: 'Head'
  },

  {
    census_year: 1921,
    address: '7 Mapperley Road, Nottingham',
    first_name: 'Watson', last_name: 'Fothergill',
    born_year: 1841, sex: 'Male',
    occupation: 'Architect (Retired)', marital_status: 'Married', relationship: 'Head'
  },

  {
    census_year: 1891,
    address: '25 Regent Street, St Mary, Nottingham',
    first_name: 'Thomas C', last_name: 'Hine',
    born_year: 1814, sex: 'Male',
    occupation: 'Architect', marital_status: 'Married', relationship: 'Head'
  },

  // ── Add more architects below ──────────────────────────────────

];

// ─────────────────────────────────────────────────────────────────
// IMPORT LOGIC — no need to edit below this line
// ─────────────────────────────────────────────────────────────────
async function run() {
  // Ensure address column exists (safe to run repeatedly)
  await db.query(`ALTER TABLE census_entries ADD COLUMN IF NOT EXISTS address TEXT`);
  console.log('Migration: address column ready.');

  let total = 0;

  // ── Park property entries ─────────────────────────────────────
  for (const entry of CENSUS_DATA) {
    const { propId, year, people } = entry;
    console.log(`\nProperty ${propId} — ${year} census (${people.length} people)`);

    for (const p of people) {
      const bornYear = extractYear(p.born_date);
      const ageAtCensus = bornYear ? year - bornYear : null;
      const source = [p.marital_status, p.sex].filter(Boolean).join(', ');

      // 1. Upsert person
      const existing = await db.query(
        `SELECT id FROM people WHERE LOWER(first_name)=LOWER($1) AND LOWER(last_name)=LOWER($2) LIMIT 1`,
        [p.first_name, p.last_name || '']
      );

      let personId;
      if (existing.rows[0]) {
        personId = existing.rows[0].id;
        // Update missing fields only (COALESCE keeps existing values)
        await db.query(
          `UPDATE people SET
             known_as   = COALESCE(known_as, $2),
             born_date  = COALESCE(born_date, $3),
             born_year  = COALESCE(born_year, $4),
             updated_at = NOW()
           WHERE id = $1`,
          [personId, p.known_as || null, p.born_date || null, bornYear]
        );
        console.log(`  ↺  Found existing: ${p.first_name} ${p.last_name} (id ${personId})`);
      } else {
        const r = await db.query(
          `INSERT INTO people (first_name, last_name, known_as, born_date, born_year)
           VALUES ($1, $2, $3, $4, $5) RETURNING id`,
          [p.first_name, p.last_name || null, p.known_as || null, p.born_date || null, bornYear]
        );
        personId = r.rows[0].id;
        console.log(`  +  Created: ${p.first_name} ${p.last_name} (id ${personId})`);
      }

      // 2. Add occupation record if provided
      if (p.occupation && p.occupation !== '???') {
        const eOcc = await db.query(
          `SELECT id FROM occupations WHERE person_id=$1 AND LOWER(occupation)=LOWER($2) LIMIT 1`,
          [personId, p.occupation]
        );
        if (!eOcc.rows[0]) {
          await db.query(
            `INSERT INTO occupations (person_id, occupation) VALUES ($1, $2)`,
            [personId, p.occupation]
          );
        }
      }

      // 3. Add census entry (skip if already exists for this person+property+year)
      const eCe = await db.query(
        `SELECT id FROM census_entries WHERE person_id=$1 AND property_id=$2 AND census_year=$3 LIMIT 1`,
        [personId, propId, year]
      );
      if (!eCe.rows[0]) {
        await db.query(
          `INSERT INTO census_entries (person_id, property_id, census_year, relationship, age_at_census, occupation_at_census, source)
           VALUES ($1, $2, $3, $4, $5, $6, $7)`,
          [personId, propId, year, p.relationship || null, ageAtCensus,
           (p.occupation && p.occupation !== '???') ? p.occupation : null, source || null]
        );
        console.log(`     ✓ Census entry added (age ${ageAtCensus}, ${p.relationship || 'no relationship'})`);
      } else {
        console.log(`     – Census entry already exists, skipped`);
      }

      total++;
    }
  }

  // ── Architect / builder entries (no property_id, address stored) ─
  console.log(`\n── Architects ──`);
  for (const a of ARCHITECT_DATA) {
    const existing = await db.query(
      `SELECT id FROM people WHERE LOWER(first_name)=LOWER($1) AND LOWER(last_name)=LOWER($2) LIMIT 1`,
      [a.first_name, a.last_name]
    );

    let personId;
    if (existing.rows[0]) {
      personId = existing.rows[0].id;
      await db.query(
        `UPDATE people SET born_year=COALESCE(born_year,$2), updated_at=NOW() WHERE id=$1`,
        [personId, a.born_year || null]
      );
      console.log(`  ↺  Found existing: ${a.first_name} ${a.last_name} (id ${personId})`);
    } else {
      const r = await db.query(
        `INSERT INTO people (first_name, last_name, born_year) VALUES ($1,$2,$3) RETURNING id`,
        [a.first_name, a.last_name, a.born_year || null]
      );
      personId = r.rows[0].id;
      console.log(`  +  Created: ${a.first_name} ${a.last_name} (id ${personId})`);
    }

    // Add occupation if not already recorded
    if (a.occupation) {
      const eOcc = await db.query(
        `SELECT id FROM occupations WHERE person_id=$1 AND LOWER(occupation)=LOWER($2) LIMIT 1`,
        [personId, a.occupation]
      );
      if (!eOcc.rows[0]) {
        await db.query(`INSERT INTO occupations (person_id, occupation) VALUES ($1,$2)`, [personId, a.occupation]);
      }
    }

    // Add census entry with address, no property_id
    const eCe = await db.query(
      `SELECT id FROM census_entries WHERE person_id=$1 AND census_year=$2 AND (property_id IS NULL) LIMIT 1`,
      [personId, a.census_year]
    );
    if (!eCe.rows[0]) {
      const ageAtCensus = a.born_year ? a.census_year - a.born_year : null;
      const source = [a.marital_status, a.sex].filter(Boolean).join(', ');
      await db.query(
        `INSERT INTO census_entries (person_id, property_id, address, census_year, relationship, age_at_census, occupation_at_census, source)
         VALUES ($1, NULL, $2, $3, $4, $5, $6, $7)`,
        [personId, a.address, a.census_year, a.relationship || null,
         ageAtCensus, a.occupation || null, source || null]
      );
      console.log(`     ✓ Census entry added: ${a.census_year} at ${a.address}`);
    } else {
      console.log(`     – Census entry already exists, skipped`);
    }

    total++;
  }

  console.log(`\nDone — ${total} people processed.`);
  await db.end();
}

run().catch(e => { console.error(e.message); process.exit(1); });
