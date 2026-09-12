const express  = require('express');
const session  = require('express-session');
const path     = require('path');
const fs       = require('fs');
const bcrypt   = require('bcrypt');
const multer   = require('multer');

const app  = express();
const PORT = process.env.PORT || 3000;

// ── Global CORS ───────────────────────────────────────────────────────────────
// Reads are public, so other origins may GET. Writes must come from our own
// pages: allowing cross-origin POST/PUT/DELETE let any website drive the API on
// a visitor's behalf. The site's own pages are same-origin and never use CORS.
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'GET,OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.sendStatus(204);
  next();
});

// ── Config ────────────────────────────────────────────────────────────────────
const IS_PROD        = process.env.NODE_ENV === 'production';
const ADMIN_USER     = process.env.ADMIN_USER || 'admin';

// These defaults are public (this repo is on GitHub), so in production they must
// never be used: the fallback password would be a known admin login, and the
// fallback session secret would let anyone forge an admin cookie. Rather than
// take the site down, fall back to something safe-but-degraded and say so.
const ADMIN_PASS_SET = !!process.env.ADMIN_PASS;
const ADMIN_PASS     = process.env.ADMIN_PASS || (IS_PROD ? null : 'parkhouses2024');
const SESSION_SECRET = process.env.SESSION_SECRET
  || (IS_PROD ? require('crypto').randomBytes(32).toString('hex') : 'ph-secret-change-in-prod');

if (IS_PROD && !process.env.SESSION_SECRET) {
  console.error('[SECURITY] SESSION_SECRET is not set. Using a random secret for this ' +
                'process — everyone will be logged out on each restart. Set it in Railway Variables.');
}
// Compare in constant time so the admin password can't be recovered a character
// at a time from response timings. Hashing first keeps lengths equal.
// ── Login throttling ─────────────────────────────────────────────────────────
// Both login routes were unlimited, so a password could be worked out at
// whatever rate the host would serve. Counts failures per IP over a rolling
// window and refuses once they pile up; a success clears the count, so an
// ordinary person who mistypes twice is unaffected.
const LOGIN_WINDOW_MS = 15 * 60 * 1000;
const LOGIN_MAX_FAILS = 8;
const loginFails = new Map();   // ip -> { count, first }

function loginKey(req) {
  // trust proxy is on in production, so req.ip is the real client address
  return req.ip || req.connection?.remoteAddress || 'unknown';
}
function loginBlocked(req) {
  const rec = loginFails.get(loginKey(req));
  if (!rec) return 0;
  if (Date.now() - rec.first > LOGIN_WINDOW_MS) { loginFails.delete(loginKey(req)); return 0; }
  return rec.count >= LOGIN_MAX_FAILS
    ? Math.ceil((LOGIN_WINDOW_MS - (Date.now() - rec.first)) / 1000)
    : 0;
}
function loginFailed(req) {
  const k = loginKey(req);
  const rec = loginFails.get(k);
  if (!rec || Date.now() - rec.first > LOGIN_WINDOW_MS) loginFails.set(k, { count: 1, first: Date.now() });
  else rec.count++;
}
function loginSucceeded(req) { loginFails.delete(loginKey(req)); }

// Keep the map from growing without bound on a long-running process.
setInterval(() => {
  const cutoff = Date.now() - LOGIN_WINDOW_MS;
  for (const [k, v] of loginFails) if (v.first < cutoff) loginFails.delete(k);
}, LOGIN_WINDOW_MS).unref();

function timingSafeEqualStr(a, b) {
  const crypto = require('crypto');
  const ha = crypto.createHash('sha256').update(String(a)).digest();
  const hb = crypto.createHash('sha256').update(String(b)).digest();
  return crypto.timingSafeEqual(ha, hb);
}

if (IS_PROD && !ADMIN_PASS_SET) {
  console.error('[SECURITY] ADMIN_PASS is not set. The built-in admin login is DISABLED ' +
                'so the public default cannot be used. Set it in Railway Variables.');
}
const COORDS_FILE    = path.join(__dirname, 'data', 'coords_overrides.json');
const PROPS_FILE     = path.join(__dirname, 'data', 'property_overrides.json');
const USERS_FILE     = path.join(__dirname, 'data', 'users.json');
const PHOTOS_DIR     = path.join(__dirname, 'data', 'photos');
const PROFILE_DIR    = path.join(__dirname, 'data', 'photos', 'profiles');

// Ensure data dir + files exist (used as fallback when no DB)
if (!fs.existsSync(path.join(__dirname, 'data'))) fs.mkdirSync(path.join(__dirname, 'data'));
if (!fs.existsSync(PHOTOS_DIR)) fs.mkdirSync(PHOTOS_DIR);
if (!fs.existsSync(PROFILE_DIR)) fs.mkdirSync(PROFILE_DIR);

// ── Cloudinary (optional — set env vars to enable persistent uploads) ─────────
let cloudinary = null;
if (process.env.CLOUDINARY_CLOUD_NAME && process.env.CLOUDINARY_API_KEY && process.env.CLOUDINARY_API_SECRET) {
  try {
    cloudinary = require('cloudinary').v2;
    cloudinary.config({
      cloud_name: process.env.CLOUDINARY_CLOUD_NAME,
      api_key:    process.env.CLOUDINARY_API_KEY,
      api_secret: process.env.CLOUDINARY_API_SECRET,
    });
    console.log('Cloudinary configured — uploads will be stored persistently');
  } catch(e) {
    console.warn('cloudinary package not installed, falling back to local disk');
    cloudinary = null;
  }
}

// Upload a buffer: uses Cloudinary if configured, otherwise saves to local disk
// Upload a photo buffer to Cloudinary using the unsigned "park-houses" preset.
// Uses https + multipart form (no extra packages, no signing required).
async function uploadPhoto(buf, filename, contentType) {
  const cloudName = process.env.CLOUDINARY_CLOUD_NAME;
  if (cloudName) {
    const ext = filename.split('.').pop().toLowerCase() || 'jpg';
    const mimeByExt = {
      jpg: 'image/jpeg', jpeg: 'image/jpeg', png: 'image/png',
      gif: 'image/gif', webp: 'image/webp', heic: 'image/jpeg', heif: 'image/jpeg'
    };
    const mimeType = mimeByExt[ext] || contentType || 'image/jpeg';
    // Use .jpg extension for HEIC so Cloudinary processes it correctly
    const safeFilename = (ext === 'heic' || ext === 'heif') ? filename.replace(/\.[^.]+$/, '.jpg') : filename;
    const publicId = `park-houses/${safeFilename.replace(/\.[^.]+$/, '')}`;

    return new Promise((resolve, reject) => {
      const https = require('https');
      const boundary = '----ParkHousesBoundary' + Date.now().toString(16);

      const parts = [
        `--${boundary}\r\nContent-Disposition: form-data; name="upload_preset"\r\n\r\npark-houses`,
        `--${boundary}\r\nContent-Disposition: form-data; name="public_id"\r\n\r\n${publicId}`,
      ];
      const prelude = Buffer.from(parts.join('\r\n') + '\r\n');
      const fileHeader = Buffer.from(
        `--${boundary}\r\nContent-Disposition: form-data; name="file"; filename="${safeFilename}"\r\nContent-Type: ${mimeType}\r\n\r\n`
      );
      const epilogue = Buffer.from(`\r\n--${boundary}--\r\n`);
      const body = Buffer.concat([prelude, fileHeader, buf, epilogue]);

      const req = https.request({
        hostname: 'api.cloudinary.com',
        path: `/v1_1/${cloudName}/image/upload`,
        method: 'POST',
        headers: {
          'Content-Type': `multipart/form-data; boundary=${boundary}`,
          'Content-Length': body.length,
        },
      }, res => {
        let data = '';
        res.on('data', c => data += c);
        res.on('end', () => {
          try {
            const json = JSON.parse(data);
            if (json.secure_url) { resolve(json.secure_url); }
            else { reject(new Error(json.error?.message || data)); }
          } catch(e) { reject(new Error(data)); }
        });
      });
      req.on('error', reject);
      req.write(body);
      req.end();
    });
  }
  // Fallback: local disk (ephemeral on Railway — only used in local dev without Cloudinary)
  const dest = path.join(PHOTOS_DIR, filename);
  fs.writeFileSync(dest, buf);
  return `/data/photos/${filename}`;
}
// Upload a video buffer to Cloudinary.
// 1) Uses Cloudinary SDK if available (handles signing automatically)
// 2) Falls back to manual signed upload using env vars
// 3) Last resort: local disk (ephemeral on Railway)
// Photographs and documents attached to a person. Cloudinary where it is
// configured — 'auto' so a PDF or a Word file is stored as a raw asset rather
// than being rejected as an image. Falls back to the local disk only when
// Cloudinary is not set up, which is the case locally and nowhere else; on a
// host with an ephemeral filesystem that fallback does not survive a deploy.
async function uploadMedia(buf, filename, contentType) {
  if (cloudinary) {
    return new Promise((resolve, reject) => {
      const stream = cloudinary.uploader.upload_stream(
        { resource_type: 'auto', folder: 'park-houses', public_id: filename.replace(/\.[^.]+$/, ''),
          use_filename: true, unique_filename: false },
        (error, result) => {
          if (error) return reject(new Error(error.message || JSON.stringify(error)));
          resolve(result.secure_url);
        });
      stream.end(buf);
    });
  }
  if (process.env.CLOUDINARY_CLOUD_NAME && /^image\//.test(contentType || '')) {
    return uploadPhoto(buf, filename, contentType);   // unsigned preset path
  }
  fs.mkdirSync(PHOTOS_DIR, { recursive: true });
  fs.writeFileSync(path.join(PHOTOS_DIR, filename), buf);
  return `/data/photos/${filename}`;
}

async function uploadVideo(buf, filename) {
  const cloudName  = process.env.CLOUDINARY_CLOUD_NAME;
  const apiKey     = (process.env.CLOUDINARY_API_KEY    || '').trim();
  const apiSecret  = (process.env.CLOUDINARY_API_SECRET || '').trim();

  if (cloudinary) {
    // SDK available — use upload_stream (signing handled internally)
    return new Promise((resolve, reject) => {
      const stream = cloudinary.uploader.upload_stream(
        { resource_type: 'video', folder: 'park-houses', use_filename: true, unique_filename: true },
        (error, result) => {
          if (error) reject(new Error(error.message || JSON.stringify(error)));
          else resolve(result.secure_url);
        }
      );
      stream.end(buf);
    });
  }

  if (cloudName && apiKey && apiSecret) {
    // No SDK but have credentials — manual signed upload
    const crypto   = require('crypto');
    const https    = require('https');
    const safeFile = filename.replace(/[^a-z0-9._-]/gi, '_');
    const ext      = safeFile.split('.').pop().toLowerCase();
    const mimes    = { mp4:'video/mp4', mov:'video/quicktime', avi:'video/x-msvideo', mkv:'video/x-matroska', webm:'video/webm', m4v:'video/mp4', wmv:'video/x-ms-wmv', ogv:'video/ogg' };
    const mime     = mimes[ext] || 'video/mp4';
    const ts       = Math.floor(Date.now() / 1000);
    // Cloudinary signature: SHA1(sorted_params_string + api_secret)
    const sig = crypto.createHash('sha1').update(`timestamp=${ts}${apiSecret}`).digest('hex');
    const boundary = '----VidBound' + Date.now().toString(16);
    const textPart = (name, val) =>
      `--${boundary}\r\nContent-Disposition: form-data; name="${name}"\r\n\r\n${val}\r\n`;
    const prelude = Buffer.from(
      textPart('api_key', apiKey) +
      textPart('timestamp', ts) +
      textPart('signature', sig)
    );
    const fileHeader = Buffer.from(
      `--${boundary}\r\nContent-Disposition: form-data; name="file"; filename="${safeFile}"\r\nContent-Type: ${mime}\r\n\r\n`
    );
    const epilogue = Buffer.from(`\r\n--${boundary}--\r\n`);
    const body = Buffer.concat([prelude, fileHeader, buf, epilogue]);
    return new Promise((resolve, reject) => {
      const req = https.request({
        hostname: 'api.cloudinary.com',
        path: `/v1_1/${cloudName}/video/upload`,
        method: 'POST',
        headers: { 'Content-Type': `multipart/form-data; boundary=${boundary}`, 'Content-Length': body.length },
        timeout: 300000,
      }, resp => {
        let data = '';
        resp.on('data', c => data += c);
        resp.on('end', () => {
          try {
            const json = JSON.parse(data);
            if (json.secure_url) resolve(json.secure_url);
            else reject(new Error(json.error?.message || data.slice(0, 300)));
          } catch(e) { reject(new Error(data.slice(0, 300))); }
        });
      });
      req.on('error', reject);
      req.on('timeout', () => { req.destroy(); reject(new Error('Upload timed out')); });
      req.end(body);
    });
  }

  // Last resort: local disk (ephemeral on Railway)
  const dest = path.join(PHOTOS_DIR, filename.replace(/[^a-z0-9._-]/gi, '_'));
  fs.writeFileSync(dest, buf);
  return `/data/photos/${path.basename(dest)}`;
}

if (!fs.existsSync(COORDS_FILE)) fs.writeFileSync(COORDS_FILE, JSON.stringify({}));
if (!fs.existsSync(PROPS_FILE))  fs.writeFileSync(PROPS_FILE, JSON.stringify({}));
if (!fs.existsSync(USERS_FILE))  fs.writeFileSync(USERS_FILE, JSON.stringify({}));

// ── Database (PostgreSQL when DATABASE_URL set, JSON files otherwise) ─────────
let db = null;  // pg Pool, or null for file mode

async function dbInit() {
  if (!process.env.DATABASE_URL) {
    console.log('No DATABASE_URL — using local JSON files');
    return;
  }
  try {
    const { Pool } = require('pg');
    db = new Pool({ connectionString: process.env.DATABASE_URL, ssl: { rejectUnauthorized: false } });
    await db.query(`
      CREATE TABLE IF NOT EXISTS coords (
        id INTEGER PRIMARY KEY,
        lat DOUBLE PRECISION NOT NULL,
        lng DOUBLE PRECISION NOT NULL,
        placed_by TEXT,
        placed_at TIMESTAMPTZ DEFAULT NOW()
      );
      CREATE TABLE IF NOT EXISTS property_data (
        id INTEGER PRIMARY KEY,
        data JSONB NOT NULL DEFAULT '{}',
        updated_by TEXT,
        updated_at TIMESTAMPTZ DEFAULT NOW()
      );
      CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        profile_photo TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
      );

      -- ── People database ──────────────────────────────────────────────────────
      CREATE TABLE IF NOT EXISTS people (
        id SERIAL PRIMARY KEY,
        first_name TEXT NOT NULL,
        last_name TEXT,
        known_as TEXT,               -- title, nickname, or alternate name
        born_date TEXT,              -- full date string if known
        born_year INTEGER,
        born_place TEXT,
        died_date TEXT,
        died_year INTEGER,
        died_place TEXT,
        bio TEXT,                    -- narrative story
        wikipedia_url TEXT,
        photo_url TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
      );

      CREATE TABLE IF NOT EXISTS occupations (
        id SERIAL PRIMARY KEY,
        person_id INTEGER REFERENCES people(id) ON DELETE CASCADE,
        occupation TEXT NOT NULL,    -- normalised job title
        from_year INTEGER,
        to_year INTEGER,
        employer TEXT,
        notes TEXT
      );

      -- Census appearances link a person to a property in a given year
      CREATE TABLE IF NOT EXISTS census_entries (
        id SERIAL PRIMARY KEY,
        person_id INTEGER REFERENCES people(id) ON DELETE CASCADE,
        property_id INTEGER,         -- references the property number
        census_year INTEGER NOT NULL,
        relationship TEXT,           -- head / wife / son / servant etc.
        age_at_census INTEGER,
        occupation_at_census TEXT,   -- as recorded in that census
        source TEXT
      );

      -- Relationships between people (parent/child/spouse/sibling/employer/employee)
      CREATE TABLE IF NOT EXISTS people_relationships (
        id SERIAL PRIMARY KEY,
        person_a_id INTEGER REFERENCES people(id) ON DELETE CASCADE,
        person_b_id INTEGER REFERENCES people(id) ON DELETE CASCADE,
        relationship TEXT NOT NULL,  -- "parent_of","child_of","spouse_of","sibling_of","employer_of","employee_of"
        notes TEXT,
        UNIQUE(person_a_id, person_b_id, relationship)
      );

      -- Significant places
      CREATE TABLE IF NOT EXISTS significant_places (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        location TEXT,
        place_type TEXT,             -- church / hall / colliery / tannery / school etc.
        description TEXT,
        wikipedia_url TEXT,
        lat DOUBLE PRECISION,
        lng DOUBLE PRECISION
      );

      -- Links: person ↔ place
      CREATE TABLE IF NOT EXISTS people_places (
        id SERIAL PRIMARY KEY,
        person_id INTEGER REFERENCES people(id) ON DELETE CASCADE,
        place_id INTEGER REFERENCES significant_places(id) ON DELETE CASCADE,
        connection TEXT              -- "owned","memorial at","born at","employed at" etc.
      );

      -- Links: property ↔ place
      CREATE TABLE IF NOT EXISTS property_places (
        id SERIAL PRIMARY KEY,
        property_id INTEGER NOT NULL,
        place_id INTEGER REFERENCES significant_places(id) ON DELETE CASCADE,
        connection TEXT
      );

      -- Bibliography
      CREATE TABLE IF NOT EXISTS bibliography (
        id SERIAL PRIMARY KEY,
        author_person_id INTEGER REFERENCES people(id) ON DELETE SET NULL,
        title TEXT NOT NULL,
        year INTEGER,
        publisher TEXT,
        notes TEXT,
        url TEXT,
        property_id INTEGER          -- which property record surfaced this book
      );
    `);
    // Migrations — safe to run every startup
    await db.query(`ALTER TABLE people ADD COLUMN IF NOT EXISTS photo_url TEXT`);
    await db.query(`ALTER TABLE census_entries ADD COLUMN IF NOT EXISTS address TEXT`);
    await db.query(`ALTER TABLE people ADD COLUMN IF NOT EXISTS grave_location TEXT`);
    await db.query(`ALTER TABLE people ADD COLUMN IF NOT EXISTS grave_number TEXT`);
    // Selected by several endpoints but previously only ever added by hand, so a
    // fresh database would fail on them.
    await db.query(`ALTER TABLE people ADD COLUMN IF NOT EXISTS postnominals TEXT`);
    await db.query(`ALTER TABLE people ADD COLUMN IF NOT EXISTS maiden_name TEXT`);
    await db.query(`ALTER TABLE occupations ADD COLUMN IF NOT EXISTS source TEXT`);
    // 'M' or 'F'
    await db.query(`ALTER TABLE people ADD COLUMN IF NOT EXISTS sex TEXT`);
    await db.query(`ALTER TABLE people ADD COLUMN IF NOT EXISTS sex_source TEXT`);

    // Gazette references. Created here rather than lazily inside one endpoint,
    // so every caller can rely on it existing.
    await db.query(`CREATE TABLE IF NOT EXISTS person_gazette (
      id SERIAL PRIMARY KEY,
      person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
      url TEXT NOT NULL,
      gazette TEXT,               -- London, Edinburgh, Belfast
      issue TEXT,
      page TEXT,
      supplement BOOLEAN DEFAULT FALSE,
      found_in TEXT,              -- which field the link came from
      status TEXT DEFAULT 'confirmed',  -- confirmed | suggested | dismissed
      title TEXT,
      notice_date TEXT,
      created_at TIMESTAMPTZ DEFAULT NOW()
    )`);
    await db.query(`ALTER TABLE person_gazette ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'confirmed'`);
    await db.query(`ALTER TABLE person_gazette ADD COLUMN IF NOT EXISTS title TEXT`);
    await db.query(`ALTER TABLE person_gazette ADD COLUMN IF NOT EXISTS notice_date TEXT`);
    await db.query(`CREATE INDEX IF NOT EXISTS person_gazette_person_idx ON person_gazette(person_id)`);
    await db.query(`CREATE UNIQUE INDEX IF NOT EXISTS person_gazette_unique_idx
                      ON person_gazette(person_id, url)`);

    // Documents about the estate as a whole rather than one person or house:
    // maps, deeds, newsletters, photographs of the place itself.
    await db.query(`CREATE TABLE IF NOT EXISTS archive_documents (
      id SERIAL PRIMARY KEY,
      title TEXT NOT NULL,
      description TEXT,
      url TEXT NOT NULL,
      filename TEXT,
      kind TEXT,                  -- map | plan | photograph | document | newsletter
      dated TEXT,                 -- free text: "2003", "c.1880", "Fourth Edition, 2004"
      credit TEXT,                -- who made it, who gave it
      source TEXT,                -- where it came from
      added_by TEXT,
      created_at TIMESTAMPTZ DEFAULT NOW()
    )`);
    await db.query(`CREATE INDEX IF NOT EXISTS archive_documents_kind_idx
                      ON archive_documents(kind)`);

    // "Not the same person" has to be remembered, or a pair that has already been
    // judged is offered again every time the page is opened. Stored lowest id
    // first so the pair is one row whichever way round it is sent.
    await db.query(`CREATE TABLE IF NOT EXISTS duplicate_dismissed (
      id SERIAL PRIMARY KEY,
      person_a_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
      person_b_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
      note TEXT,
      dismissed_by TEXT,
      dismissed_at TIMESTAMPTZ DEFAULT NOW()
    )`);
    await db.query(`CREATE UNIQUE INDEX IF NOT EXISTS duplicate_dismissed_pair_idx
                      ON duplicate_dismissed(person_a_id, person_b_id)`);

    // The 1939 Register records marital status, and a slipped column dropped it
    // into `source` along with the sex. It is real information and wants a
    // column of its own rather than clearing.
    await db.query(`ALTER TABLE census_entries ADD COLUMN IF NOT EXISTS marital_status TEXT`);

    // A house genuinely full of people — a boarding house, a large staff — is
    // not a fault, and should stop being offered once someone has said so.
    await db.query(`CREATE TABLE IF NOT EXISTS crowding_reviewed (
      id SERIAL PRIMARY KEY,
      property_id INTEGER NOT NULL,
      census_year INTEGER NOT NULL,
      note TEXT,
      reviewed_by TEXT,
      reviewed_at TIMESTAMPTZ DEFAULT NOW()
    )`);
    await db.query(`CREATE UNIQUE INDEX IF NOT EXISTS crowding_reviewed_unique_idx
                      ON crowding_reviewed(property_id, census_year)`);

    // Wikidata identifications. A dismissal has to be remembered, or the sweep
    // offers the same wrong match every time it is run.
    await db.query(`CREATE TABLE IF NOT EXISTS person_wikidata (
      id SERIAL PRIMARY KEY,
      person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
      qid TEXT NOT NULL,
      name TEXT,
      url TEXT,
      status TEXT NOT NULL DEFAULT 'suggested',  -- confirmed | dismissed
      decided_by TEXT,
      decided_at TIMESTAMPTZ DEFAULT NOW()
    )`);
    await db.query(`CREATE INDEX IF NOT EXISTS person_wikidata_person_idx
                      ON person_wikidata(person_id)`);
    await db.query(`CREATE UNIQUE INDEX IF NOT EXISTS person_wikidata_unique_idx
                      ON person_wikidata(person_id, qid)`);

    // A person's own published works. Kept as rows rather than a block of text
    // so the list can be ordered by year and each entry cited on its own.
    await db.query(`CREATE TABLE IF NOT EXISTS person_works (
      id SERIAL PRIMARY KEY,
      person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
      title TEXT NOT NULL,
      year INTEGER,
      work_type TEXT,              -- novel, collection, short story, edited, non-fiction…
      publisher TEXT,
      notes TEXT,                  -- pseudonym, series, first appearance
      source TEXT,                 -- where the entry came from
      created_at TIMESTAMPTZ DEFAULT NOW()
    )`);
    await db.query(`CREATE INDEX IF NOT EXISTS person_works_person_idx ON person_works(person_id)`);
    await db.query(`ALTER TABLE person_works ADD COLUMN IF NOT EXISTS source TEXT`);
    // Significance is a curated judgement, not a computed score: a person is
    // featured because someone decided they should be, and says why.
    await db.query(`ALTER TABLE people ADD COLUMN IF NOT EXISTS significant BOOLEAN DEFAULT FALSE`);
    await db.query(`ALTER TABLE people ADD COLUMN IF NOT EXISTS significance_note TEXT`);
    await db.query(`ALTER TABLE people ADD COLUMN IF NOT EXISTS significant_by TEXT`);
    await db.query(`ALTER TABLE people ADD COLUMN IF NOT EXISTS significant_at TIMESTAMPTZ`);
    await db.query(`CREATE TABLE IF NOT EXISTS census_unoccupied (
      property_id INTEGER NOT NULL,
      census_year INTEGER NOT NULL,
      notes TEXT,
      PRIMARY KEY (property_id, census_year)
    )`);
    await db.query(`CREATE TABLE IF NOT EXISTS property_residents (
      id SERIAL PRIMARY KEY,
      property_id INTEGER NOT NULL,
      person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
      from_year INTEGER,
      to_year INTEGER,
      notes TEXT,
      created_at TIMESTAMPTZ DEFAULT NOW()
    )`);
    await db.query(`ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'viewer'`);
    await db.query(`ALTER TABLE users ADD COLUMN IF NOT EXISTS approved BOOLEAN DEFAULT FALSE`);
    await db.query(`ALTER TABLE users ADD COLUMN IF NOT EXISTS approved_by TEXT`);
    await db.query(`CREATE TABLE IF NOT EXISTS person_links (
      id SERIAL PRIMARY KEY,
      person_id INTEGER REFERENCES people(id) ON DELETE CASCADE,
      title TEXT NOT NULL,
      url TEXT NOT NULL,
      link_type TEXT DEFAULT 'website',
      notes TEXT,
      created_by TEXT,
      created_at TIMESTAMPTZ DEFAULT NOW()
    )`);
    await db.query(`CREATE TABLE IF NOT EXISTS change_log (
      id SERIAL PRIMARY KEY,
      entity_type TEXT NOT NULL,
      entity_id INTEGER NOT NULL,
      username TEXT,
      action TEXT NOT NULL,
      field TEXT,
      old_value TEXT,
      new_value TEXT,
      created_at TIMESTAMPTZ DEFAULT NOW()
    )`);
    await db.query(`CREATE INDEX IF NOT EXISTS change_log_entity ON change_log(entity_type, entity_id)`);
    await db.query(`CREATE INDEX IF NOT EXISTS change_log_time ON change_log(created_at DESC)`);
    await db.query(`CREATE TABLE IF NOT EXISTS architect_works (
      id SERIAL PRIMARY KEY,
      person_id INTEGER REFERENCES people(id) ON DELETE CASCADE,
      name TEXT NOT NULL,
      location_text TEXT,
      address TEXT,
      city TEXT DEFAULT 'Nottingham',
      year_start INTEGER,
      year_end INTEGER,
      notes TEXT,
      wikipedia_url TEXT,
      lat DOUBLE PRECISION,
      lng DOUBLE PRECISION,
      location_uncertain BOOLEAN DEFAULT FALSE,
      created_at TIMESTAMPTZ DEFAULT NOW()
    )`);
    await db.query(`CREATE INDEX IF NOT EXISTS architect_works_person ON architect_works(person_id)`);
    await db.query(`CREATE TABLE IF NOT EXISTS architect_firms (
      id SERIAL PRIMARY KEY,
      name TEXT NOT NULL UNIQUE,
      active_from INTEGER,
      active_to INTEGER,
      notes TEXT,
      wikipedia_url TEXT,
      created_at TIMESTAMPTZ DEFAULT NOW()
    )`);
    await db.query(`CREATE TABLE IF NOT EXISTS firm_members (
      id SERIAL PRIMARY KEY,
      firm_id INTEGER REFERENCES architect_firms(id) ON DELETE CASCADE,
      person_id INTEGER REFERENCES people(id) ON DELETE CASCADE,
      role TEXT DEFAULT 'Partner',
      from_year INTEGER,
      to_year INTEGER,
      UNIQUE(firm_id, person_id)
    )`);
    // Session store table for persistent login across restarts
    await db.query(`CREATE TABLE IF NOT EXISTS sessions (
      sid VARCHAR PRIMARY KEY,
      sess JSONB NOT NULL,
      expire TIMESTAMPTZ NOT NULL
    )`);
    await db.query(`CREATE INDEX IF NOT EXISTS sessions_expire_idx ON sessions(expire)`);

    await db.query(`CREATE TABLE IF NOT EXISTS property_research (
      id SERIAL PRIMARY KEY,
      property_id INTEGER NOT NULL,
      user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
      username TEXT,
      started_at TIMESTAMPTZ DEFAULT NOW()
    )`);
    await db.query(`CREATE UNIQUE INDEX IF NOT EXISTS uniq_property_research ON property_research(property_id, username)`);

    // Open questions about the estate that only somebody standing in front of the
    // house can settle. Seeded from data/research_questions.json and keyed on the
    // slug, so a redeploy neither duplicates a question nor overwrites an answer.
    await db.query(`CREATE TABLE IF NOT EXISTS research_questions (
      id SERIAL PRIMARY KEY,
      slug TEXT UNIQUE,
      title TEXT NOT NULL,
      detail TEXT,
      kind TEXT,
      property_id INTEGER,
      person_id INTEGER,
      status TEXT NOT NULL DEFAULT 'open',
      answer TEXT,
      answered_by TEXT,
      answered_at TIMESTAMPTZ,
      created_by TEXT,
      created_at TIMESTAMPTZ DEFAULT NOW(),
      edited_at TIMESTAMPTZ
    )`);
    await db.query(`CREATE TABLE IF NOT EXISTS research_claims (
      id SERIAL PRIMARY KEY,
      question_id INTEGER REFERENCES research_questions(id) ON DELETE CASCADE,
      username TEXT NOT NULL,
      note TEXT,
      started_at TIMESTAMPTZ DEFAULT NOW()
    )`);
    await db.query(`CREATE UNIQUE INDEX IF NOT EXISTS uniq_research_claim ON research_claims(question_id, username)`);
    // Addresses the census itself cannot resolve — the return gave no house
    // name and no number, so no amount of census review will place them. They
    // are set aside rather than left in the queue looking like work.
    await db.query(`CREATE TABLE IF NOT EXISTS unfiled_set_aside (
      address TEXT PRIMARY KEY,
      note TEXT,
      set_by TEXT,
      set_at TIMESTAMPTZ DEFAULT NOW()
    )`);
    // Set aside is per record, not per address: one household on a street can be
    // placeable while the rest are not. Anything set aside by address before
    // this is expanded to its records, and the address rows go.
    // The working list, tickable and shared, seeded from data/tasks.json. Same
    // rule as the research questions: a slug keys it, so a redeploy neither
    // duplicates a task nor un-ticks one.
    await db.query(`CREATE TABLE IF NOT EXISTS tasks (
      id SERIAL PRIMARY KEY,
      slug TEXT UNIQUE,
      area TEXT,
      title TEXT NOT NULL,
      detail TEXT,
      size TEXT,
      link TEXT,
      sort_order INTEGER DEFAULT 100,
      done BOOLEAN DEFAULT FALSE,
      done_by TEXT,
      done_at TIMESTAMPTZ,
      created_by TEXT,
      created_at TIMESTAMPTZ DEFAULT NOW(),
      edited_at TIMESTAMPTZ
    )`);
    await seedTasks();

    // Buildings OpenStreetMap names that the record deliberately does not want —
    // blocks of flats on demolished plots, garages, an estate agent's office.
    await db.query(`CREATE TABLE IF NOT EXISTS osm_dismissed (
      osm_id TEXT PRIMARY KEY,
      name TEXT,
      note TEXT,
      set_by TEXT,
      set_at TIMESTAMPTZ DEFAULT NOW()
    )`);
    await db.query(`CREATE TABLE IF NOT EXISTS census_set_aside (
      entry_id INTEGER PRIMARY KEY REFERENCES census_entries(id) ON DELETE CASCADE,
      note TEXT,
      set_by TEXT,
      set_at TIMESTAMPTZ DEFAULT NOW()
    )`);
    try {
      const moved = await db.query(`
        INSERT INTO census_set_aside (entry_id, note, set_by)
        SELECT c.id, a.note, a.set_by
          FROM unfiled_set_aside a
          JOIN census_entries c ON c.unresolved_address = a.address AND c.property_id IS NULL
         ON CONFLICT (entry_id) DO NOTHING`);
      if (moved.rowCount) {
        await db.query(`DELETE FROM unfiled_set_aside`);
        console.log(`Set aside: ${moved.rowCount} record(s) moved from address to record level`);
      }
    } catch (e) { console.warn('set-aside migration:', e.message); }
    await seedResearchQuestions();
    // Deduplicate relationships and add unique constraint (non-fatal)
    try {
      await db.query(`DELETE FROM people_relationships WHERE id IN (
        SELECT a.id FROM people_relationships a
        JOIN people_relationships b ON a.person_a_id=b.person_a_id AND a.person_b_id=b.person_b_id AND a.relationship=b.relationship
        WHERE a.id > b.id
      )`);
      await db.query(`CREATE UNIQUE INDEX IF NOT EXISTS uniq_relationship ON people_relationships(person_a_id, person_b_id, relationship)`);
    } catch(migErr) { console.warn('Relationship dedup migration:', migErr.message); }
    await db.query(`CREATE TABLE IF NOT EXISTS person_media (
      id SERIAL PRIMARY KEY,
      person_id INTEGER REFERENCES people(id) ON DELETE CASCADE,
      url TEXT NOT NULL,
      caption TEXT,
      media_type TEXT DEFAULT 'photo',
      filename TEXT,
      created_at TIMESTAMPTZ DEFAULT NOW()
    )`);
    await db.query(`CREATE TABLE IF NOT EXISTS property_watches (
      id SERIAL PRIMARY KEY,
      user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
      property_id INTEGER NOT NULL,
      created_at TIMESTAMPTZ DEFAULT NOW(),
      UNIQUE(user_id, property_id)
    )`);
    await db.query(`ALTER TABLE census_entries ADD COLUMN IF NOT EXISTS unresolved_address TEXT`);
    await db.query(`ALTER TABLE census_entries ADD COLUMN IF NOT EXISTS census_house_id TEXT`);
    await db.query(`ALTER TABLE census_entries ADD COLUMN IF NOT EXISTS census_household_num INTEGER`);
    await db.query(`ALTER TABLE census_entries ADD COLUMN IF NOT EXISTS birth_place TEXT`);
    await db.query(`ALTER TABLE people ADD COLUMN IF NOT EXISTS title TEXT`);
    await db.query(`CREATE TABLE IF NOT EXISTS geocode_cache (
      place_text        TEXT PRIMARY KEY,
      lat               NUMERIC,
      lng               NUMERIC,
      formatted_address TEXT,
      status            TEXT DEFAULT 'found',
      corrected_from    TEXT,
      queried_at        TIMESTAMPTZ DEFAULT NOW()
    )`);
    // A table made by an older version keeps its old columns — CREATE TABLE IF NOT
    // EXISTS never adds one — so make sure the ones written to are there.
    for (const col of ['formatted_address TEXT', 'corrected_from TEXT', 'queried_at TIMESTAMPTZ DEFAULT NOW()']) {
      await db.query(`ALTER TABLE geocode_cache ADD COLUMN IF NOT EXISTS ${col}`).catch(e => console.warn('geocode_cache column:', e.message));
    }
    await seedGeocodeManual();
    // Gate House and North Lodge are separate properties — no migration needed
    // Fix Huntingdon Drive 1921 — split into correct households by house name
    const hdFixes = [
      {first:'Frederick Percy', last:'Johnson',          hh:1, addr:'Huntingdon Drive (Acacia)'},
      {first:'Madeline Beatrice',last:'Johnson',         hh:1, addr:'Huntingdon Drive (Acacia)'},
      {first:'Sylvia Millicent', last:'Johnson',         hh:1, addr:'Huntingdon Drive (Acacia)'},
      {first:'Maria Elizabeth',  last:'Buckingham',      hh:1, addr:'Huntingdon Drive (Acacia)'},
      {first:'Gertrude Margaret',last:'Dobrashian',      hh:2, addr:'Huntingdon Drive (Brampton)'},
      {first:'John',             last:'Clark',           hh:2, addr:'Huntingdon Drive (Brampton)'},
      {first:'Mary Dorcas',      last:'Clark',           hh:2, addr:'Huntingdon Drive (Brampton)'},
      {first:'Joseph',           last:'Spray',           hh:3, addr:'Huntingdon Drive (Greendale)'},
      {first:'Martha',           last:'Spray',           hh:3, addr:'Huntingdon Drive (Greendale)'},
      {first:'Jessie',           last:'Spray',           hh:3, addr:'Huntingdon Drive (Greendale)'},
      {first:'Louisa',           last:'Paecy',           hh:3, addr:'Huntingdon Drive (Greendale)'},
      {first:'Samuel Ritchie',   last:'Jackson',         hh:4, addr:'Huntingdon Drive (Kenmore)'},
      {first:'Margaret Emily',   last:'Jackson',         hh:4, addr:'Huntingdon Drive (Kenmore)'},
      {first:'Margaret Alys',    last:'Jackson',         hh:4, addr:'Huntingdon Drive (Kenmore)'},
      {first:'Geoffrey William', last:'Jackson',         hh:4, addr:'Huntingdon Drive (Kenmore)'},
      {first:'Beryl Louise',     last:'Jackson',         hh:4, addr:'Huntingdon Drive (Kenmore)'},
      {first:'Millicent',        last:'Thomas',          hh:4, addr:'Huntingdon Drive (Kenmore)'},
      {first:'Sidney Richard',   last:'Tann',            hh:6, addr:'Huntingdon Drive (The Cottage)'},
      {first:'Daisy Chrisball',  last:'Tann',            hh:6, addr:'Huntingdon Drive (The Cottage)'},
    ];
    for (const f of hdFixes) {
      await db.query(`
        UPDATE census_entries ce
        SET census_household_num=$1, unresolved_address=$2
        FROM people p
        WHERE ce.person_id=p.id
          AND LOWER(p.first_name)=LOWER($3) AND LOWER(p.last_name)=LOWER($4)
          AND ce.census_year=1921 AND ce.property_id IS NULL
      `, [f.hh, f.addr, f.first, f.last]).catch(()=>{});
    }
    console.log('PostgreSQL connected and tables ready');
  } catch(e) {
    console.error('DB init failed, falling back to JSON files:', e.message);
    db = null;
  }
}

// ── Coords storage (DB-backed or file-backed) ─────────────────────────────────
async function loadCoords() {
  if (db) {
    const r = await db.query('SELECT id, lat, lng, placed_by, placed_at FROM coords');
    const out = {};
    r.rows.forEach(row => { out[row.id] = { lat: row.lat, lng: row.lng, placedBy: row.placed_by, placedAt: row.placed_at }; });
    return out;
  }
  try { return JSON.parse(fs.readFileSync(COORDS_FILE, 'utf8')); } catch(e) { return {}; }
}

async function saveCoord(id, lat, lng, username) {
  if (db) {
    await db.query(
      `INSERT INTO coords (id, lat, lng, placed_by, placed_at) VALUES ($1,$2,$3,$4,NOW())
       ON CONFLICT (id) DO UPDATE SET lat=$2, lng=$3, placed_by=$4, placed_at=NOW()`,
      [id, lat, lng, username]
    );
    return;
  }
  const coords = JSON.parse(fs.readFileSync(COORDS_FILE, 'utf8') || '{}');
  coords[id] = { lat, lng, placedBy: username, placedAt: new Date().toISOString() };
  fs.writeFileSync(COORDS_FILE, JSON.stringify(coords, null, 2));
  autoCommit('Update marker positions');
}

async function deleteCoord(id) {
  if (db) { await db.query('DELETE FROM coords WHERE id=$1', [id]); return; }
  const coords = JSON.parse(fs.readFileSync(COORDS_FILE, 'utf8') || '{}');
  delete coords[id];
  fs.writeFileSync(COORDS_FILE, JSON.stringify(coords, null, 2));
  autoCommit('Remove marker override');
}

// Admin: bulk save multiple coords at once
async function saveCoordsBulk(entries, username) {
  if (db) {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      for (const { id, lat, lng } of entries) {
        await client.query(
          `INSERT INTO coords (id, lat, lng, placed_by, placed_at) VALUES ($1,$2,$3,$4,NOW())
           ON CONFLICT (id) DO UPDATE SET lat=$2, lng=$3, placed_by=$4, placed_at=NOW()`,
          [id, lat, lng, username]
        );
      }
      await client.query('COMMIT');
    } catch(e) { await client.query('ROLLBACK'); throw e; }
    finally { client.release(); }
    return;
  }
  const coords = JSON.parse(fs.readFileSync(COORDS_FILE, 'utf8') || '{}');
  for (const { id, lat, lng } of entries) {
    coords[id] = { lat, lng, placedBy: username, placedAt: new Date().toISOString() };
  }
  fs.writeFileSync(COORDS_FILE, JSON.stringify(coords, null, 2));
  autoCommit('Bulk update marker positions');
}

// ── Property data storage (DB-backed or file-backed) ──────────────────────────
async function loadProps() {
  if (db) {
    const r = await db.query('SELECT id, data FROM property_data');
    const out = {};
    r.rows.forEach(row => { out[row.id] = row.data; });
    return out;
  }
  try { return JSON.parse(fs.readFileSync(PROPS_FILE, 'utf8')); } catch(e) { return {}; }
}

async function loadProp(id) {
  if (db) {
    const r = await db.query('SELECT data FROM property_data WHERE id=$1', [id]);
    return r.rows[0]?.data || {};
  }
  const all = JSON.parse(fs.readFileSync(PROPS_FILE, 'utf8') || '{}');
  return all[id] || {};
}

async function saveProp(id, fields, username) {
  if (db) {
    const current = await loadProp(id);
    const merged = { ...current, ...fields, updatedBy: username, updatedAt: new Date().toISOString() };
    await db.query(
      `INSERT INTO property_data (id, data, updated_by, updated_at) VALUES ($1,$2,$3,NOW())
       ON CONFLICT (id) DO UPDATE SET data=$2, updated_by=$3, updated_at=NOW()`,
      [id, JSON.stringify(merged), username]
    );
    return merged;
  }
  const all = JSON.parse(fs.readFileSync(PROPS_FILE, 'utf8') || '{}');
  const current = all[id] || {};
  all[id] = { ...current, ...fields, updatedBy: username, updatedAt: new Date().toISOString() };
  fs.writeFileSync(PROPS_FILE, JSON.stringify(all, null, 2));
  autoCommit('Update property data');
  return all[id];
}

async function deleteProp(id) {
  if (db) { await db.query('DELETE FROM property_data WHERE id=$1', [id]); return; }
  const all = JSON.parse(fs.readFileSync(PROPS_FILE, 'utf8') || '{}');
  delete all[id];
  fs.writeFileSync(PROPS_FILE, JSON.stringify(all, null, 2));
}

// Auto-commit JSON files to git (file-mode only fallback)
function autoCommit(msg) {
  const { execSync } = require('child_process');
  try {
    execSync('git add data/coords_overrides.json data/property_overrides.json', { cwd: __dirname, stdio: 'ignore' });
    execSync(`git commit -m "${msg}" --allow-empty`, { cwd: __dirname, stdio: 'ignore' });
    require('child_process').spawn('git', ['push'], { cwd: __dirname, stdio: 'ignore', detached: true }).unref();
  } catch(e) { }
}

// ── User storage (DB-backed or JSON-file fallback) ────────────────────────────
function loadUsersFile() {
  try { return JSON.parse(fs.readFileSync(USERS_FILE, 'utf8')); } catch(e) { return {}; }
}
function saveUsersFile(data) { fs.writeFileSync(USERS_FILE, JSON.stringify(data, null, 2)); }

async function findUserByEmail(email) {
  if (db) {
    const r = await db.query('SELECT * FROM users WHERE email=$1', [email.toLowerCase()]);
    return r.rows[0] || null;
  }
  const all = loadUsersFile();
  return Object.values(all).find(u => u.email === email.toLowerCase()) || null;
}

async function findUserById(id) {
  if (db) {
    const r = await db.query('SELECT id,email,first_name,last_name,profile_photo,role,approved,created_at FROM users WHERE id=$1', [id]);
    return r.rows[0] || null;
  }
  const all = loadUsersFile();
  return all[id] || null;
}

async function createUser(email, passwordHash, firstName, lastName) {
  if (db) {
    const r = await db.query(
      `INSERT INTO users (email,password_hash,first_name,last_name) VALUES ($1,$2,$3,$4) RETURNING id,email,first_name,last_name,created_at`,
      [email.toLowerCase(), passwordHash, firstName, lastName]
    );
    return r.rows[0];
  }
  const all = loadUsersFile();
  const id = Date.now();
  all[id] = { id, email: email.toLowerCase(), password_hash: passwordHash, first_name: firstName, last_name: lastName, profile_photo: null, created_at: new Date().toISOString() };
  saveUsersFile(all);
  return all[id];
}

async function updateUserPhoto(id, photoUrl) {
  if (db) {
    await db.query('UPDATE users SET profile_photo=$1 WHERE id=$2', [photoUrl, id]);
    return;
  }
  const all = loadUsersFile();
  if (all[id]) { all[id].profile_photo = photoUrl; saveUsersFile(all); }
}

// Public user info (no password hash)
function publicUser(u) {
  if (!u) return null;
  return { id: u.id, email: u.email, firstName: u.first_name, lastName: u.last_name, profilePhoto: u.profile_photo, role: u.role||'viewer', approved: u.approved||false, createdAt: u.created_at };
}

// ── Middleware ────────────────────────────────────────────────────────────────
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// ── Custom PostgreSQL session store (no extra npm package needed) ─────────────
// Stores sessions in DB so they survive Railway restarts and redeployments.
class PgStore extends session.Store {
  async get(sid, cb) {
    if (!db) return cb(null, null);
    try {
      const r = await db.query(
        "SELECT sess FROM sessions WHERE sid=$1 AND expire > NOW()", [sid]);
      cb(null, r.rows[0]?.sess || null);
    } catch(e) { cb(null, null); }
  }
  async set(sid, data, cb) {
    if (!db) return cb(null);
    try {
      const exp = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);
      await db.query(
        `INSERT INTO sessions(sid,sess,expire) VALUES($1,$2,$3)
         ON CONFLICT(sid) DO UPDATE SET sess=$2, expire=$3`,
        [sid, data, exp]);
      cb(null);
    } catch(e) { cb(null); }
  }
  async destroy(sid, cb) {
    if (!db) return cb(null);
    try { await db.query("DELETE FROM sessions WHERE sid=$1", [sid]); cb(null); }
    catch(e) { cb(null); }
  }
}

if (process.env.NODE_ENV === 'production') app.set('trust proxy', 1);

app.use(session({
  secret: SESSION_SECRET,
  resave: false,
  saveUninitialized: false,
  store: new PgStore(),
  cookie: {
    maxAge: 7 * 24 * 60 * 60 * 1000, // 7 days
    httpOnly: true,
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production'
  }
}));

function requireAdmin(req, res, next) {
  if (req.session && req.session.isAdmin) return next();
  res.status(401).json({ error: 'Not authenticated' });
}
async function requireContributor(req, res, next) {
  if (!req.session) return res.status(403).json({ error: 'Contributor access required' });
  if (req.session.isAdmin) return next();
  if (req.session.userRole === 'contributor') return next();
  // userRole might not be set in old sessions — look up from DB
  if (req.session.userId) {
    try {
      const u = await findUserById(req.session.userId);
      if (u && (u.role === 'contributor' || u.role === 'admin') && u.approved) {
        req.session.userRole = u.role; // cache for next time
        return next();
      }
    } catch(e) {}
  }
  res.status(403).json({ error: 'Contributor access required' });
}
function isContributor(req) {
  return !!(req.session && (req.session.isAdmin || req.session.userRole === 'contributor' || req.session.userRole === 'admin'));
}

// ── Auth routes ───────────────────────────────────────────────────────────────
app.post('/api/login', (req, res) => {
  const { username, password } = req.body;
  const wait = loginBlocked(req);
  if (wait) return res.status(429).json({ error: 'Too many failed attempts. Try again in '
    + Math.ceil(wait / 60) + ' minutes.' });
  if (!ADMIN_PASS) return res.status(503).json({ error: 'Admin login is not configured' });
  if (typeof username !== 'string' || typeof password !== 'string') {
    return res.status(400).json({ error: 'Invalid credentials' });
  }
  if (username === ADMIN_USER && timingSafeEqualStr(password, ADMIN_PASS)) {
    loginSucceeded(req);
    req.session.isAdmin = true;
    req.session.username = username;
    res.json({ ok: true });
  } else {
    loginFailed(req);
    res.status(401).json({ error: 'Invalid credentials' });
  }
});

app.post('/api/logout', (req, res) => {
  req.session.destroy(() => res.json({ ok: true }));
});

app.get('/api/me', async (req, res) => {
  const resp = { isAdmin: false, user: null, researchKey: null };
  if (req.session && req.session.isAdmin) {
    resp.isAdmin = true;
    resp.username = req.session.username;
    resp.researchKey = 'admin';
  }
  if (req.session && req.session.userId) {
    try {
      const u = await findUserById(req.session.userId);
      resp.user = publicUser(u);
      // researchKey is the display name stored in property_research table
      resp.researchKey = u ? ((u.first_name || '') + ' ' + (u.last_name || '')).trim() : null;
    } catch(e) {}
  }
  res.json(resp);
});

// ── User auth routes ──────────────────────────────────────────────────────────
app.post('/api/user/register', async (req, res) => {
  const { email, password, firstName, lastName } = req.body;
  if (!email || !password || !firstName || !lastName)
    return res.status(400).json({ error: 'email, password, firstName, lastName required' });
  if (password.length < 6)
    return res.status(400).json({ error: 'Password must be at least 6 characters' });
  try {
    const existing = await findUserByEmail(email);
    if (existing) return res.status(409).json({ error: 'An account with this email already exists' });
    const hash = await bcrypt.hash(password, 10);
    const user = await createUser(email, hash, firstName.trim(), lastName.trim());
    req.session.userId = user.id;
    res.json({ ok: true, user: publicUser(user) });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/user/login', async (req, res) => {
  const { email, password } = req.body;
  const wait = loginBlocked(req);
  if (wait) return res.status(429).json({ error: 'Too many failed attempts. Try again in '
    + Math.ceil(wait / 60) + ' minutes.' });
  if (!email || !password)
    return res.status(400).json({ error: 'email and password required' });
  try {
    const user = await findUserByEmail(email);
    if (!user) { loginFailed(req); return res.status(401).json({ error: 'Invalid email or password' }); }
    const ok = await bcrypt.compare(password, user.password_hash);
    if (!ok) { loginFailed(req); return res.status(401).json({ error: 'Invalid email or password' }); }
    // A correct password on an unapproved account is not a failed attempt.
    if (!user.approved) return res.status(403).json({ error: 'Your account is awaiting admin approval' });
    loginSucceeded(req);
    req.session.userId   = user.id;
    req.session.userRole = user.role || 'viewer';
    res.json({ ok: true, user: publicUser(user) });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/user/logout', (req, res) => {
  req.session.userId = null;
  res.json({ ok: true });
});

// Upload/replace profile photo
app.post('/api/user/photo', async (req, res) => {
  if (!req.session.userId) return res.status(401).json({ error: 'Not logged in' });
  const chunks = [];
  req.on('data', c => chunks.push(c));
  req.on('end', async () => {
    try {
      const buf = Buffer.concat(chunks);
      if (buf.length < 100) return res.status(400).json({ error: 'Empty file' });
      const ext = (req.headers['x-filename'] || 'photo.jpg').split('.').pop().replace(/[^a-z]/gi,'').toLowerCase() || 'jpg';
      const filename = `profile_${req.session.userId}_${Date.now()}.${ext}`;
      const url = await uploadPhoto(buf, filename, req.headers["content-type"]);
      await updateUserPhoto(req.session.userId, url);
      res.json({ ok: true, url });
    } catch(e) { res.status(500).json({ error: e.message }); }
  });
  req.on('error', e => res.status(500).json({ error: e.message }));
});

app.use('/data/photos/profiles', express.static(PROFILE_DIR));

// ── Coords API ────────────────────────────────────────────────────────────────
app.get('/api/coords', async (req, res) => {
  try { res.json(await loadCoords()); } catch(e) { res.status(500).json({ error: e.message }); }
});

// Admin: save a single property's position
app.post('/api/coords/:id', requireAdmin, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  const { lat, lng } = req.body;
  if (!id || lat === undefined || lng === undefined)
    return res.status(400).json({ error: 'id, lat, lng required' });
  try {
    await saveCoord(id, parseFloat(lat), parseFloat(lng), req.session.username);
    res.json({ ok: true, id, lat: parseFloat(lat), lng: parseFloat(lng) });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// Admin: bulk save multiple positions at once
app.post('/api/coords-bulk', requireAdmin, async (req, res) => {
  const { entries } = req.body; // [{id, lat, lng}, ...]
  if (!Array.isArray(entries) || entries.length === 0)
    return res.status(400).json({ error: 'entries array required' });
  try {
    await saveCoordsBulk(entries, req.session.username);
    res.json({ ok: true, saved: entries.length });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// Admin: revert a property to auto-geocoded position
app.delete('/api/coords/:id', requireAdmin, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  try { await deleteCoord(id); res.json({ ok: true }); }
  catch(e) { res.status(500).json({ error: e.message }); }
});

// Admin: download full coords JSON
app.get('/api/coords/export', requireAdmin, async (req, res) => {
  try {
    const coords = await loadCoords();
    res.setHeader('Content-Disposition', 'attachment; filename="park_coords_export.json"');
    res.setHeader('Content-Type', 'application/json');
    res.send(JSON.stringify(coords, null, 2));
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// ── All properties (base data, no overrides) ──────────────────────────────────
const ALL_PROPS_FILE = path.join(__dirname, 'data', 'all_props.json');

// Build a fast id→display-name lookup from the static props file
let propNameMap = {};
try {
  const allProps = JSON.parse(fs.readFileSync(ALL_PROPS_FILE, 'utf8'));
  allProps.forEach(p => {
    // Build a readable address: "57 Elmhurst, Cavendish Road East" or "Elmhurst, Cavendish Road East"
    // Use the pre-formatted address field, cleaning up trailing colons
    const addr = (p.address || p.name || '').replace(/:\s*([A-Z])/g, ', $1').replace(/:\s*$/, '').trim();
    const houseName = (p.house_name || '').trim();
    propNameMap[p.id] = houseName ? `${addr} (${houseName})` : (addr || `Property ${p.id}`);
  });
} catch(e) { /* file may not exist in some envs */ }

function propName(id) { return propNameMap[id] || `Property ${id}`; }

// Every map page load hits this, and the file is ~800KB, so serve a cached
// string and re-read only when the file actually changes on disk.
let allPropsCache = null; // { mtimeMs, body, etag }
function readAllPropsCached() {
  const mtimeMs = fs.statSync(ALL_PROPS_FILE).mtimeMs;
  if (!allPropsCache || allPropsCache.mtimeMs !== mtimeMs) {
    const body = fs.readFileSync(ALL_PROPS_FILE, 'utf8');
    allPropsCache = { mtimeMs, body, etag: '"props-' + mtimeMs + '-' + body.length + '"' };
  }
  return allPropsCache;
}

app.get('/api/all-props', (req, res) => {
  try {
    const c = readAllPropsCached();
    res.set('ETag', c.etag);
    if (req.headers['if-none-match'] === c.etag) return res.status(304).end();
    res.type('application/json').send(c.body);
  }
  catch(e) { res.json([]); }
});

// ── A person's published works ───────────────────────────────────────────────
app.get('/api/person/:id/works', async (req, res) => {
  if (!db) return res.json([]);
  try {
    const r = await db.query(
      `SELECT id, title, year, work_type, publisher, notes, source FROM person_works
        WHERE person_id=$1 ORDER BY year NULLS LAST, title`, [parseInt(req.params.id, 10)]);
    res.json(r.rows);
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// Accepts one work or a list, so a whole bibliography can be loaded in one go.
app.post('/api/person/:id/works', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  const personId = parseInt(req.params.id, 10);
  const items = Array.isArray(req.body) ? req.body : [req.body];
  const clean = items
    .map(w => ({
      title: String(w.title || '').trim().slice(0, 400),
      year: Number.isFinite(parseInt(w.year, 10)) ? parseInt(w.year, 10) : null,
      work_type: w.work_type ? String(w.work_type).trim().slice(0, 60) : null,
      publisher: w.publisher ? String(w.publisher).trim().slice(0, 200) : null,
      notes: w.notes ? String(w.notes).trim().slice(0, 500) : null,
    }))
    .filter(w => w.title);
  if (!clean.length) return res.status(400).json({ error: 'Each work needs a title' });
  try {
    for (const w of clean) {
      await db.query(
        `INSERT INTO person_works (person_id,title,year,work_type,publisher,notes)
         VALUES ($1,$2,$3,$4,$5,$6)`,
        [personId, w.title, w.year, w.work_type, w.publisher, w.notes]);
    }
    await logChange('person', personId, req, 'add', 'works', null, clean.length + ' work(s)');
    res.json({ ok: true, added: clean.length });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

app.delete('/api/person/:personId/works/:workId', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  try {
    await db.query(`DELETE FROM person_works WHERE id=$1 AND person_id=$2`,
      [parseInt(req.params.workId, 10), parseInt(req.params.personId, 10)]);
    await logChange('person', parseInt(req.params.personId, 10), req, 'delete', 'works', null, null);
    res.json({ ok: true });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// Gazette references pasted into a biography are invisible to everything else —
// not searchable, not listed, not citable. This lifts them into person_gazette
// so each one becomes a proper reference with its issue and page.
app.post('/api/admin/extract-gazette', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  const dryRun = req.body && req.body.dryRun === true;
  try {

    const rows = await db.query(
      `SELECT id, bio FROM people WHERE bio ILIKE '%thegazette.co.uk%'`);
    const LINK = /https?:\/\/(?:www\.)?thegazette\.co\.uk\/[^\s"'<>)\]]+/gi;
    let found = 0, added = 0, already = 0;
    const people = new Set();
    for (const person of rows.rows) {
      for (const raw of (person.bio.match(LINK) || [])) {
        const url = raw.replace(/[.,;]+$/, '');
        found++;
        const m = url.match(/thegazette\.co\.uk\/([A-Za-z]+)\/issue\/(\d+)\/(supplement|page)\/(\d+)/i);
        const rec = {
          gazette: m ? m[1] : null, issue: m ? m[2] : null,
          page: m ? m[4] : null, supplement: m ? m[3].toLowerCase() === 'supplement' : false,
        };
        if (dryRun) { added++; people.add(person.id); continue; }
        const r = await db.query(
          `INSERT INTO person_gazette (person_id,url,gazette,issue,page,supplement,found_in)
           VALUES ($1,$2,$3,$4,$5,$6,'biography')
           ON CONFLICT (person_id, url) DO NOTHING RETURNING id`,
          [person.id, url, rec.gazette, rec.issue, rec.page, rec.supplement]);
        if (r.rows.length) { added++; people.add(person.id); } else already++;
      }
    }
    res.json({ ok: true, dryRun, peopleWithLinks: rows.rows.length,
               linksFound: found, added, alreadyRecorded: already, peopleAffected: people.size });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// Search The Gazette for people already carrying an honours signal, rather than
// for everyone. A national record of three centuries of notices will return a
// different Mary Adcock for most of the 2,500 residents, and attaching those
// would put wrong citations on real people. Restricting it to people whose
// record already suggests an honour or public office keeps the hit rate worth
// reading — and everything lands as a suggestion for a person to confirm.
app.post('/api/admin/gazette-sweep', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  const dryRun = req.body && req.body.dryRun === true;
  // Each search is a round trip to an external service, so a full sweep runs for
  // minutes and a hosting proxy kills the request long before it finishes — that
  // showed up as a 502. The work is done a few people at a time and the caller
  // comes back for the next slice.
  const batch = Math.min(parseInt(req.body && req.body.batch, 10) || 6, 20);
  const offset = Math.max(parseInt(req.body && req.body.offset, 10) || 0, 0);
  try {
    const all = await db.query(`
      SELECT p.id, p.first_name, p.last_name, p.born_year, p.died_year
        FROM people p
       WHERE COALESCE(p.last_name,'') <> '' AND COALESCE(p.first_name,'') <> ''
         AND (${SIGNAL_SQL}) > 0
       ORDER BY (${SIGNAL_SQL}) DESC, p.last_name, p.id`);

    if (dryRun) {
      return res.json({ ok: true, dryRun: true, wouldSearch: all.rows.length,
        names: all.rows.slice(0, 12).map(p => p.first_name + ' ' + p.last_name) });
    }

    const people = { rows: all.rows.slice(offset, offset + batch) };
    let searched = 0, hits = 0, added = 0, already = 0;
    for (const person of people.rows) {
      const name = (person.first_name + ' ' + person.last_name).replace(/\s+/g, ' ').trim();
      searched++;
      let rows = [];
      try {
        const r = await fetch('https://www.thegazette.co.uk/all-notices/notice/data.feed?text='
            + encodeURIComponent('"' + name + '"'), {
          headers: { 'User-Agent': 'NottinghamParkHouses/1.0 (conservation record)' },
          signal: AbortSignal.timeout(12000),
        });
        if (r.ok) {
          const xml = await r.text();
          rows = [...xml.matchAll(/<entry>([\s\S]*?)<\/entry>/g)].map(m => {
            const g = re => ((m[1].match(re) || [])[1] || '').trim();
            const date = g(/<published>(.*?)<\/published>/) || g(/<updated>(.*?)<\/updated>/);
            const href = g(/<link[^>]*href="(.*?)"/);
            return { title: g(/<title>([\s\S]*?)<\/title>/).replace(/\s+/g, ' '),
                     date: date.slice(0, 10),
                     year: parseInt(date.slice(0, 4), 10) || null,
                     url: href.startsWith('http') ? href : 'https://www.thegazette.co.uk' + href };
          }).filter(x => x.url);
        }
      } catch (e) { /* one failed search should not stop the sweep */ }

      // A notice printed after they died, or long before they were born, is not them.
      const plausible = rows.filter(x => {
        if (!x.year) return false;
        if (person.born_year && x.year < person.born_year + 15) return false;
        if (person.died_year && x.year > person.died_year + 2) return false;
        return true;
      }).slice(0, 5);
      hits += plausible.length;

      for (const n of plausible) {
        const m = n.url.match(/thegazette\.co\.uk\/([A-Za-z]+)\/issue\/(\d+)\/(supplement|page)\/(\d+)/i);
        const r2 = await db.query(
          `INSERT INTO person_gazette (person_id,url,gazette,issue,page,supplement,found_in,status,title,notice_date)
           VALUES ($1,$2,$3,$4,$5,$6,'gazette search','suggested',$7,$8)
           ON CONFLICT (person_id, url) DO NOTHING RETURNING id`,
          [person.id, n.url, m ? m[1] : null, m ? m[2] : null, m ? m[4] : null,
           m ? m[3].toLowerCase() === 'supplement' : false, n.title, n.date]);
        if (r2.rows.length) added++; else already++;
      }
      await new Promise(r => setTimeout(r, 400));   // be a good neighbour
    }
    const nextOffset = offset + people.rows.length;
    res.json({ ok: true, searched, plausibleHits: hits, added, alreadyRecorded: already,
               offset: nextOffset, total: all.rows.length, done: nextOffset >= all.rows.length });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// Every pending suggestion in one list, so they can be worked through rather
// than found one person at a time.
app.get('/api/gazette/pending', async (req, res) => {
  if (!db) return res.json({ people: [], total: 0 });
  try {
    const r = await db.query(`
      SELECT g.id, g.url, g.gazette, g.issue, g.page, g.supplement, g.title, g.notice_date,
             p.id AS person_id, p.first_name, p.last_name, p.known_as, p.title AS person_title,
             p.postnominals, p.born_year, p.died_year, p.bio
        FROM person_gazette g
        JOIN people p ON p.id = g.person_id
       WHERE g.status = 'suggested'
       ORDER BY p.last_name, p.first_name, g.notice_date`);
    const people = [];
    const byPerson = new Map();
    for (const row of r.rows) {
      if (!byPerson.has(row.person_id)) {
        const bio = (row.bio || '').replace(/\s+/g, ' ').trim();
        const person = {
          id: row.person_id, first_name: row.first_name, last_name: row.last_name,
          known_as: row.known_as, title: row.person_title, postnominals: row.postnominals,
          born_year: row.born_year, died_year: row.died_year,
          bio: bio.length > 260 ? bio.slice(0, 260) + '…' : bio,
          notices: [],
        };
        byPerson.set(row.person_id, person);
        people.push(person);
      }
      byPerson.get(row.person_id).notices.push({
        id: row.id, url: row.url, gazette: row.gazette, issue: row.issue,
        page: row.page, supplement: row.supplement, title: row.title, notice_date: row.notice_date,
      });
    }
    res.json({ people, total: r.rows.length });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// Every notice with the person it was found against, whatever has been decided
// about it. The review page works through the backlog and can take a decision
// back, which needs the confirmed and dismissed ones as well as the new.
app.get('/api/gazette/review', requireContributor, async (req, res) => {
  if (!db) return res.json({ people: [], totals: { suggested: 0, confirmed: 0, dismissed: 0 } });
  try {
    const r = await db.query(`
      SELECT g.id, g.url, g.gazette, g.issue, g.page, g.supplement, g.title, g.notice_date,
             COALESCE(g.status,'confirmed') AS status,
             p.id AS person_id, p.first_name, p.last_name, p.known_as, p.title AS person_title,
             p.postnominals, p.born_year, p.died_year, p.bio
        FROM person_gazette g
        JOIN people p ON p.id = g.person_id
       ORDER BY p.last_name, p.first_name, g.notice_date NULLS LAST`);
    const people = [], byPerson = new Map();
    const totals = { suggested: 0, confirmed: 0, dismissed: 0 };
    for (const row of r.rows) {
      if (!byPerson.has(row.person_id)) {
        const bio = (row.bio || '').replace(/\s+/g, ' ').trim();
        const person = {
          id: row.person_id, first_name: row.first_name, last_name: row.last_name,
          known_as: row.known_as, title: row.person_title, postnominals: row.postnominals,
          born_year: row.born_year, died_year: row.died_year,
          bio: bio.length > 260 ? bio.slice(0, 260) + '…' : bio,
          notices: [],
        };
        byPerson.set(row.person_id, person);
        people.push(person);
      }
      byPerson.get(row.person_id).notices.push({
        id: row.id, url: row.url, gazette: row.gazette, issue: row.issue, page: row.page,
        supplement: row.supplement, title: row.title, notice_date: row.notice_date,
        status: row.status,
      });
      if (totals[row.status] !== undefined) totals[row.status]++;
    }
    res.json({ people, totals });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/person/:personId/gazette/:refId', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  // "suggested" puts a notice back in the queue, so a decision can be undone.
  const wanted = String((req.body && req.body.status) || '');
  const status = ['confirmed', 'dismissed', 'suggested'].includes(wanted) ? wanted : 'dismissed';
  try {
    await db.query(`UPDATE person_gazette SET status=$3 WHERE id=$1 AND person_id=$2`,
      [parseInt(req.params.refId, 10), parseInt(req.params.personId, 10), status]);
    res.json({ ok: true, status });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

app.get('/api/person/:id/gazette', async (req, res) => {
  if (!db) return res.json([]);
  try {
    const r = await db.query(
      `SELECT id, url, gazette, issue, page, supplement, status, title, notice_date
         FROM person_gazette
        WHERE person_id=$1 AND COALESCE(status,'confirmed') <> 'dismissed'
        ORDER BY CASE WHEN COALESCE(status,'confirmed')='confirmed' THEN 0 ELSE 1 END,
                 notice_date NULLS LAST`, [parseInt(req.params.id, 10)]);
    res.json(r.rows);
  } catch(e) { res.json([]); }
});

// Census occupations were written onto the census entry but never onto the
// person, so the People page, the group chips and the occupation filter — which
// all read the occupations table — saw about a third of what the census holds.
// This copies them across, dated to the census year. Idempotent: a person who
// already has that occupation is left alone.
// POST /api/admin/fill-occupation-years — an occupation with no year beside a
// census record that names it is undated only because the row came in before the
// census did. Matched on the person's own records: the same wording, or the
// census wording with a qualifier added ("Nurse" and "Nurse (domestic)"). A
// looser match would date "Servant" from "Domestic Servant", so it stops there.
app.post('/api/admin/fill-occupation-years', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  const dryRun = req.body && req.body.dryRun === true;
  try {
    const bare = (await db.query(
      `SELECT o.id, o.person_id, o.occupation, p.first_name, p.last_name
         FROM occupations o JOIN people p ON p.id = o.person_id
        WHERE o.from_year IS NULL AND o.occupation IS NOT NULL AND TRIM(o.occupation) <> ''`)).rows;
    const census = (await db.query(
      `SELECT person_id, census_year, TRIM(occupation_at_census) AS occ
         FROM census_entries
        WHERE occupation_at_census IS NOT NULL AND TRIM(occupation_at_census) <> ''
          AND person_id = ANY($1::int[])`, [[...new Set(bare.map(b => b.person_id))]])).rows;
    const byPerson = new Map();
    for (const c of census) (byPerson.get(c.person_id) || byPerson.set(c.person_id, []).get(c.person_id)).push(c);
    const norm = v => String(v || '').toLowerCase().replace(/\s+/g, ' ').trim();
    const dated = [], undatable = [];
    for (const o of bare) {
      const want = norm(o.occupation);
      const rows = byPerson.get(o.person_id) || [];
      let hits = rows.filter(c => norm(c.occ) === want), how = 'same wording';
      if (!hits.length) {
        hits = rows.filter(c => { const n = norm(c.occ); return n.startsWith(want + ' (') || n.startsWith(want + ','); });
        how = 'census adds a qualifier';
      }
      const name = `${o.first_name} ${o.last_name}`.trim();
      if (!hits.length) { undatable.push(`${name} — ${o.occupation}`); continue; }
      const years = hits.map(h => h.census_year).sort((a, b) => a - b);
      const from = years[0], to = years[years.length - 1];
      dated.push({ name, occupation: o.occupation, from, to: to !== from ? to : null, how });
      if (!dryRun) {
        await db.query(
          `UPDATE occupations SET from_year=$1, to_year=COALESCE(to_year, $2), source=COALESCE(source, $3)
            WHERE id=$4 AND from_year IS NULL`,
          [from, to !== from ? to : null, from + ' census', o.id]);
      }
    }
    res.json({ ok: true, dryRun, yearless: bare.length, dated: dated.length,
               undatable: undatable.length, examples: dated.slice(0, 40),
               undatableExamples: undatable.slice(0, 25) });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/admin/backfill-occupations', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  const dryRun = req.body && req.body.dryRun === true;
  try {
    const candidates = await db.query(`
      SELECT DISTINCT ce.person_id, TRIM(ce.occupation_at_census) AS occupation, ce.census_year
        FROM census_entries ce
       WHERE ce.person_id IS NOT NULL
         AND ce.occupation_at_census IS NOT NULL
         AND TRIM(ce.occupation_at_census) <> ''
       ORDER BY ce.person_id, occupation, ce.census_year`);

    // Skip anything that would read as an absence of work rather than a job.
    const NOT_AN_OCCUPATION = /^(none|nil|n\/?a|-+|\.+|unknown|not stated|no occupation|blank)$/i;

    let added = 0, alreadyHad = 0, skipped = 0;
    const peopleTouched = new Set();
    // Someone can hold the same occupation in both censuses. Ordering by year
    // means the earliest is recorded; this set stops the later one being counted
    // again, which otherwise made a dry run forecast more than the real run did.
    const accountedFor = new Set();
    for (const row of candidates.rows) {
      if (NOT_AN_OCCUPATION.test(row.occupation)) { skipped++; continue; }
      const key = row.person_id + '|' + row.occupation.toLowerCase();
      if (accountedFor.has(key)) { alreadyHad++; continue; }
      const existing = await db.query(
        `SELECT id, from_year FROM occupations WHERE person_id=$1 AND LOWER(TRIM(occupation))=LOWER($2)`,
        [row.person_id, row.occupation]);
      if (existing.rows.length) {
        // Already there — but an earlier import often wrote it with no year, and
        // skipping it left "Domestic Servant" undated beside an 1891 return that
        // says exactly that. Give a yearless row the census year it came from.
        const bare = existing.rows.find(r => r.from_year == null);
        if (bare && !dryRun) {
          await db.query(`UPDATE occupations SET from_year=$1, source=COALESCE(source, $2) WHERE id=$3`,
            [row.census_year, row.census_year + ' census', bare.id]);
        }
        alreadyHad++; accountedFor.add(key); continue;
      }
      accountedFor.add(key);
      if (!dryRun) {
        await db.query(
          `INSERT INTO occupations (person_id, occupation, from_year, source)
           VALUES ($1,$2,$3,$4)`,
          [row.person_id, row.occupation, row.census_year, row.census_year + ' census']);
      }
      added++; peopleTouched.add(row.person_id);
    }
    if (!dryRun) await logChange('person', 0, req, 'backfill', 'occupations', null, added + ' added');
    res.json({ ok: true, dryRun, candidates: candidates.rows.length,
               added, alreadyHad, skipped, peopleAffected: peopleTouched.size });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// Load people prepared as data/people_*.json — for figures found in the prose of
// someone else's biography, who have no record of their own. Matches on name, so
// running it twice does not create duplicates.
app.post('/api/admin/import-people', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  const dryRun = req.body && req.body.dryRun === true;
  try {
    const files = fs.readdirSync(path.join(__dirname, 'data'))
      .filter(f => /^people_.*\.json$/.test(f));
    const report = [];
    // A dry run inserts nothing, so without this it cannot see the people an
    // earlier file in the same run would have created, and reports them as new
    // twice. Remember what it decided to add and treat those as present.
    const pending = new Set();
    const pkey = (fn, ln, by) =>
      `${String(fn || '').trim().toLowerCase()}|${String(ln || '').trim().toLowerCase()}|${by ?? ''}`;
    for (const file of files) {
      const doc = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', file), 'utf8'));
      let added = 0, already = 0, linked = 0, census = 0, enriched = 0, rels = 0, relsSkipped = 0, occs = 0, occsFilled = 0;
      const noSuchId = [];
      // A preview that says "20 would be added" without saying who is a preview
      // nobody can check. Name them, capped so a large file stays readable.
      const addedNames = [], censusNames = [];
      const NAME_CAP = 24;
      const nameOf = q => `${q.first_name} ${q.last_name}`.trim();
      for (const person of (doc.people || [])) {
        if (!person.first_name || !person.last_name) continue;
        // A person the record already holds can be named by number instead. The
        // name match is exact, so "William F" and "William Froggatt" are two
        // different people to it — a spelling the source disagrees with, or one
        // about to be corrected by hand, would quietly become a second record.
        // An id says which person is meant and survives the rename either way.
        const byId = Number.isInteger(person.id);
        // A son named after his father is the other half of the same problem.
        // Matching on the name alone would hang the son's census record on the
        // father, and there is no way to ask for a new person of an existing
        // name without making the import add another one every time it runs.
        // Matching on the birth year as well distinguishes them and stays
        // idempotent: the first run creates him, later runs find him.
        const byYear = !byId && person.match_born_year === true && person.born_year;
        const found = byId
          ? await db.query(
              `SELECT id, born_date, born_year, born_place, sex, died_date, died_year, died_place, maiden_name, title, postnominals, wikipedia_url, bio FROM people WHERE id=$1`,
              [person.id])
          : byYear
          ? await db.query(
              `SELECT id, born_date, born_year, born_place, sex, died_date, died_year, died_place, maiden_name, title, postnominals, wikipedia_url, bio FROM people
                WHERE LOWER(first_name)=LOWER($1) AND LOWER(last_name)=LOWER($2)
                  AND born_year=$3`,
              [person.first_name, person.last_name, person.born_year])
          : await db.query(
              `SELECT id, born_date, born_year, born_place, sex, died_date, died_year, died_place, maiden_name, title, postnominals, wikipedia_url, bio FROM people
                WHERE LOWER(first_name)=LOWER($1) AND LOWER(last_name)=LOWER($2)`,
              [person.first_name, person.last_name]);
        if (byId && !found.rows.length) {
          // Never fall back to creating one: the file asked for a specific
          // person, and inventing another is the mistake it was avoiding.
          noSuchId.push(`#${person.id} ${person.first_name} ${person.last_name}`);
          continue;
        }
        let id = null;
        if (found.rows.length) {
          id = found.rows[0].id; already++;
          // Fill blanks only. A register gives an exact birth date where the
          // record often holds nothing — but someone else's entered value is
          // never overwritten by an import.
          const have = found.rows[0];
          const fills = [];
          // Only take the date when it does not contradict a year already held:
          // filling born_date "1 August 1870" beside an existing born_year of
          // 1872 would leave the record disagreeing with itself.
          const yearAgrees = !have.born_year || !person.born_year
                             || Number(have.born_year) === Number(person.born_year);
          if (!have.born_date  && person.born_date && yearAgrees)
            fills.push(['born_date', person.born_date]);
          if (!have.born_year  && person.born_year)  fills.push(['born_year',  person.born_year]);
          if (!have.born_place && person.born_place) fills.push(['born_place', person.born_place]);
          if (!have.sex        && person.sex)        fills.push(['sex',        person.sex]);
          // A death found later — a roll of honour, a probate notice — fills in
          // a person already in the record, never over what is there.
          if (!have.died_date  && person.died_date)  fills.push(['died_date',  person.died_date]);
          if (!have.died_year  && person.died_year)  fills.push(['died_year',  person.died_year]);
          if (!have.died_place && person.died_place) fills.push(['died_place', person.died_place]);
          if (!have.maiden_name && person.maiden_name) fills.push(['maiden_name', person.maiden_name]);
          if (!have.title       && person.title)       fills.push(['title',       person.title]);
          if (!have.postnominals && person.postnominals) fills.push(['postnominals', person.postnominals]);
          if (!have.wikipedia_url && person.wikipedia_url) fills.push(['wikipedia_url', person.wikipedia_url]);
          if (!have.bio && person.bio) fills.push(['bio', person.bio]);
          if (fills.length) {
            enriched++;
            if (!dryRun) {
              await db.query(
                `UPDATE people SET ${fills.map((f, i) => `${f[0]}=$${i + 2}`).join(', ')} WHERE id=$1`,
                [id, ...fills.map(f => f[1])]);
            }
          }
        }
        else if (dryRun) {
          // Would this file be creating somebody an earlier file already made?
          const seen = pending.has(pkey(person.first_name, person.last_name,
                                        byYear ? person.born_year : ''));
          if (seen) { already++; }
          else {
            added++; addedNames.push(nameOf(person));
            pending.add(pkey(person.first_name, person.last_name, ''));
            if (person.born_year) pending.add(pkey(person.first_name, person.last_name, person.born_year));
          }
        }
        else {
          const r = await db.query(
            // died_date and died_place too: a Gazette or probate notice gives an
            // exact date of death and nothing else, and the importer used to drop it.
            `INSERT INTO people (first_name,last_name,known_as,title,postnominals,sex,
                                 born_date,born_year,born_place,died_date,died_year,died_place,
                                 bio,wikipedia_url)
             VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14) RETURNING id`,
            [person.first_name, person.last_name, person.known_as || null, person.title || null,
             person.postnominals || null, person.sex || null, person.born_date || null,
             person.born_year || null, person.born_place || null,
             person.died_date || null, person.died_year || null, person.died_place || null,
             person.bio || null, person.wikipedia_url || null]);
          id = r.rows[0].id; added++; addedNames.push(nameOf(person));
          await logChange('person', id, req, 'create', 'import', null, file);
        }
        for (const propId of (person.properties || [])) {
          // A person who does not exist yet has no links either, so every one counts.
          if (id === null) { linked++; continue; }
          const dup = await db.query(
            `SELECT 1 FROM property_residents WHERE person_id=$1 AND property_id=$2`, [id, propId]);
          if (dup.rows.length) continue;
          if (dryRun) { linked++; continue; }
          if (true) {
            await db.query(`INSERT INTO property_residents (person_id, property_id) VALUES ($1,$2)`,
              [id, propId]);
            linked++;
          }
        }
        // Relationships to other people, named rather than given as ids so a file
        // can be written before knowing what number anybody has.
        for (const rel of (person.relationships || [])) {
          if (!rel || !rel.to || !rel.type) continue;
          // The other end can be given by number too, for the same reason as above.
          // Look it up before bailing out on a person who has no id yet, or a dry
          // run counts relationships whose far end does not exist.
          const other = Number.isInteger(rel.to.id)
            ? await db.query(`SELECT id FROM people WHERE id=$1`, [rel.to.id])
            : await db.query(
                `SELECT id FROM people WHERE LOWER(TRIM(first_name))=LOWER($1)
                                         AND LOWER(TRIM(last_name))=LOWER($2)`,
                [String(rel.to.first_name || '').trim(), String(rel.to.last_name || '').trim()]);
          if (other.rows.length !== 1) { relsSkipped++; continue; }   // ambiguous or absent
          const otherId = other.rows[0].id;
          if (id === null) { rels++; continue; }   // new in this dry run: far end checked, id unknown
          if (otherId === id) { relsSkipped++; continue; }
          const dup = await db.query(
            `SELECT 1 FROM people_relationships
              WHERE person_a_id=$1 AND person_b_id=$2 AND relationship=$3`,
            [id, otherId, rel.type]);
          if (dup.rows.length) continue;
          rels++;
          if (dryRun) continue;
          await db.query(
            `INSERT INTO people_relationships (person_a_id, person_b_id, relationship, notes)
                  VALUES ($1,$2,$3,$4) ON CONFLICT DO NOTHING`,
            [id, otherId, rel.type, rel.notes || null]);
          // Record it both ways where the word is its own opposite.
          if (rel.reciprocal !== false) {
            const back = { spouse_of:'spouse_of', sibling_of:'sibling_of', cousin_of:'cousin_of',
                           parent_of:'child_of', child_of:'parent_of',
                           employer_of:'employee_of', employee_of:'employer_of' }[rel.type];
            if (back) {
              await db.query(
                `INSERT INTO people_relationships (person_a_id, person_b_id, relationship, notes)
                      VALUES ($1,$2,$3,$4) ON CONFLICT DO NOTHING`,
                [otherId, id, back, rel.notes || null]);
            }
          }
        }
        // Census (and 1939 Register) appearances. Keyed on person, year and
        // property so running the import twice does not double the record.
        for (const c of (person.census || [])) {
          if (!c.census_year) continue;
          // A person who does not exist yet has no census record either, so every
          // one of theirs counts — and wants naming, or a dry run of an entirely
          // new household lists nobody at all.
          if (id === null) { census++; censusNames.push(`${nameOf(person)} ${c.census_year}`); continue; }
          // A row the file leaves without a house matches any record of that
          // person in that year, filed or not. Matching on the house alone let a
          // second run enter a household again the moment somebody had placed
          // it: the file still says Clumber Lodge, the record now says number
          // 21, the two no longer meet, and everyone in the house gets a second
          // census entry sitting back on the unfiled page.
          const dup = await db.query(
            c.property_id
              ? `SELECT 1 FROM census_entries
                  WHERE person_id=$1 AND census_year=$2
                    AND property_id IS NOT DISTINCT FROM $3`
              : `SELECT 1 FROM census_entries WHERE person_id=$1 AND census_year=$2`,
            c.property_id ? [id, c.census_year, c.property_id] : [id, c.census_year]);
          if (dup.rows.length) continue;
          census++;
          censusNames.push(`${nameOf(person)} ${c.census_year}`);
          if (dryRun) continue;
          await db.query(
            `INSERT INTO census_entries
               (person_id, property_id, address, unresolved_address, census_year, relationship,
                age_at_census, occupation_at_census, birth_place, marital_status, source)
             VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)`,
            [id, c.property_id || null, c.address || null,
             // A record added without a house needs the address it was returned
             // under, or it lands in the "no address recorded" heap on the
             // unfiled page instead of beside the household it belongs to.
             (!c.property_id && c.unresolved_address) ? c.unresolved_address : null,
             c.census_year,
             c.relationship || null, c.age_at_census || null,
             c.occupation_at_census || null, c.birth_place || null,
             c.marital_status || null, c.source || null]);
        }
        // What a person did, as against what one census night caught them doing.
        // Keyed on the title and the year it started, so a second run does not
        // stack the same job twice and two spells of the same job stay separate.
        for (const o of (person.occupations || [])) {
          if (!o || !o.occupation) continue;
          if (id === null) { occs++; continue; }
          const dup = await db.query(
            `SELECT id, employer, notes, to_year FROM occupations
              WHERE person_id=$1 AND LOWER(occupation)=LOWER($2)
                AND from_year IS NOT DISTINCT FROM $3`,
            [id, o.occupation, o.from_year ?? null]);
          if (dup.rows.length) {
            // Already there — but the file may carry what the row lacks. The
            // employer especially: it comes from a census column the occupation
            // table was never filled from, so on an existing job it is usually
            // the only new thing there is, and skipping the row threw it away.
            // Blanks only; nobody's entered value is overwritten.
            const have = dup.rows[0], fills = [];
            if (!have.employer && o.employer) fills.push(['employer', o.employer]);
            if (!have.notes && o.notes) fills.push(['notes', o.notes]);
            if (have.to_year == null && o.to_year != null) fills.push(['to_year', o.to_year]);
            if (fills.length) {
              occsFilled++;
              if (!dryRun) {
                await db.query(
                  `UPDATE occupations SET ${fills.map((f, k) => `${f[0]}=$${k + 2}`).join(', ')} WHERE id=$1`,
                  [have.id, ...fills.map(f => f[1])]);
              }
            }
            continue;
          }
          occs++;
          if (dryRun) continue;
          await db.query(
            `INSERT INTO occupations (person_id, occupation, from_year, to_year, employer, notes)
             VALUES ($1,$2,$3,$4,$5,$6)`,
            [id, o.occupation, o.from_year ?? null, o.to_year ?? null,
             o.employer || null, o.notes || null]);
        }
      }
      const trim = list => list.length > NAME_CAP
        ? list.slice(0, NAME_CAP).concat(`and ${list.length - NAME_CAP} more`) : list;
      report.push({ file, added, alreadyPresent: already, enriched, propertyLinks: linked,
                    census, occupations: occs, occupationsFilled: occsFilled,
                    relationships: rels, relationshipsSkipped: relsSkipped,
                    ...(addedNames.length ? { addedNames: trim(addedNames) } : {}),
                    ...(censusNames.length ? { censusNames: trim(censusNames) } : {}),
                    ...(noSuchId.length ? { noSuchPerson: noSuchId } : {}) });
    }
    res.json({ ok: true, dryRun, report });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// Bulk-load a bibliography prepared as data/works_*.json. Idempotent: a work
// already recorded for that person by the same title and year is left alone, so
// running it twice does not duplicate the list.
app.post('/api/admin/import-works', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  try {
    const files = fs.readdirSync(path.join(__dirname, 'data'))
      .filter(f => /^works_.*\.json$/.test(f));
    const report = [];
    for (const file of files) {
      const doc = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', file), 'utf8'));
      const who = doc.person || {};
      const found = await db.query(
        `SELECT id FROM people WHERE LOWER(first_name)=LOWER($1) AND LOWER(last_name)=LOWER($2)`,
        [who.first_name || '', who.last_name || '']);
      if (found.rows.length !== 1) {
        report.push({ file, skipped: found.rows.length ? 'several people match that name' : 'no person of that name' });
        continue;
      }
      const personId = found.rows[0].id;
      let added = 0, already = 0;
      for (const w of (doc.works || [])) {
        if (!w.title) continue;
        // Type matters to the key: a collection is routinely named after the
        // title story inside it, so "Spawn of Satan" is legitimately both a
        // 1970 collection and a 1970 short story.
        const dup = await db.query(
          `SELECT 1 FROM person_works WHERE person_id=$1 AND LOWER(title)=LOWER($2)
             AND COALESCE(year,-1)=COALESCE($3,-1)
             AND COALESCE(LOWER(work_type),'')=COALESCE(LOWER($4),'')`,
          [personId, w.title, w.year ?? null, w.work_type || null]);
        if (dup.rows.length) { already++; continue; }
        await db.query(
          `INSERT INTO person_works (person_id,title,year,work_type,publisher,notes,source)
           VALUES ($1,$2,$3,$4,$5,$6,$7)`,
          [personId, w.title, w.year ?? null, w.work_type || null, w.publisher || null,
           w.notes || null, doc.source || null]);
        added++;
      }
      report.push({ file, person: personId, added, alreadyPresent: already });
    }
    res.json({ ok: true, report });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// Forenames still needing a sex, worked through a name at a time rather than a
// person at a time — setting "Mary" once covers every Mary in the record.
// Relationship evidence from the census is offered as a suggestion so the
// obvious ones can be confirmed at a glance.
app.get('/api/names/sex-queue', async (req, res) => {
  if (!db) return res.json({ names: [], remaining: 0, peopleRemaining: 0 });
  try {
    const r = await db.query(`
      WITH forename AS (
        SELECT p.id, INITCAP(SPLIT_PART(TRIM(p.first_name), ' ', 1)) AS name, p.sex
          FROM people p
         WHERE COALESCE(TRIM(p.first_name),'') <> ''
      ), rel AS (
        SELECT INITCAP(SPLIT_PART(TRIM(p.first_name), ' ', 1)) AS name,
               LOWER(TRIM(COALESCE(ce.relationship,''))) AS r
          FROM census_entries ce JOIN people p ON p.id = ce.person_id
      ), evidence AS (
        SELECT name,
               COUNT(*) FILTER (WHERE r IN ('wife','daughter','mother','sister','widow','niece',
                 'aunt','granddaughter','housekeeper','maid','housemaid','parlourmaid',
                 'kitchenmaid','cook','nurse','governess')) AS female,
               COUNT(*) FILTER (WHERE r IN ('son','father','brother','nephew','uncle','grandson',
                 'husband','butler','footman','groom','coachman','gardener')) AS male
          FROM rel GROUP BY name
      )
      SELECT f.name,
             COUNT(*) AS people,
             COUNT(*) FILTER (WHERE f.sex IS NULL) AS unset,
             COALESCE(e.female,0) AS female_evidence,
             COALESCE(e.male,0)   AS male_evidence
        FROM forename f LEFT JOIN evidence e ON e.name = f.name
       WHERE LENGTH(f.name) > 1
       GROUP BY f.name, e.female, e.male
      HAVING COUNT(*) FILTER (WHERE f.sex IS NULL) > 0
       ORDER BY COUNT(*) FILTER (WHERE f.sex IS NULL) DESC, f.name`);

    const names = r.rows.map(row => {
      const f = Number(row.female_evidence), m = Number(row.male_evidence);
      let suggested = null;
      if (f + m >= 1) {
        if (f >= (f + m) * 0.8) suggested = 'F';
        else if (m >= (f + m) * 0.8) suggested = 'M';
      }
      return { name: row.name, people: Number(row.people), unset: Number(row.unset),
               evidence: { female: f, male: m }, suggested };
    });
    res.json({ names,
               remaining: names.length,
               peopleRemaining: names.reduce((t, n) => t + n.unset, 0) });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// Apply a sex to everyone sharing a forename. By default it only fills blanks;
// with correct:true it also changes people already set by a previous forename
// pass — a wrong click is easy when working quickly. People whose sex was set
// individually on their own record are never overwritten either way.
app.post('/api/names/sex', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  const name = String(req.body && req.body.name || '').trim();
  const sex = req.body && req.body.sex;
  const correct = req.body && req.body.correct === true;
  if (!name) return res.status(400).json({ error: 'name required' });
  if (sex !== 'M' && sex !== 'F') return res.status(400).json({ error: "sex must be 'M' or 'F'" });
  try {
    const who = 'forename review by ' + (req.session.username || 'contributor');
    const r = await db.query(
      `UPDATE people SET sex=$2, sex_source=$3
        WHERE INITCAP(SPLIT_PART(TRIM(first_name), ' ', 1)) = INITCAP($1)
          AND (sex IS NULL ${correct ? "OR COALESCE(sex_source,'') LIKE 'forename review%'" : ''})`,
      [name, sex, who]);
    await logChange('person', 0, req, correct ? 'correct-sex' : 'set-sex', name, null,
      sex + ' × ' + r.rowCount);
    res.json({ ok: true, name, sex, updated: r.rowCount, corrected: correct });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// Forenames already classified, for putting a mistake right.
app.get('/api/names/sex-set', async (req, res) => {
  if (!db) return res.json([]);
  const q = String(req.query.q || '').trim();
  try {
    const r = await db.query(`
      SELECT INITCAP(SPLIT_PART(TRIM(first_name), ' ', 1)) AS name,
             COUNT(*) FILTER (WHERE sex='F') AS female,
             COUNT(*) FILTER (WHERE sex='M') AS male,
             COUNT(*) FILTER (WHERE COALESCE(sex_source,'') NOT LIKE 'forename review%'
                                AND sex IS NOT NULL) AS individually_set
        FROM people
       WHERE sex IS NOT NULL AND COALESCE(TRIM(first_name),'') <> ''
         ${q ? "AND INITCAP(SPLIT_PART(TRIM(first_name),' ',1)) ILIKE $1" : ''}
       GROUP BY 1 ORDER BY COUNT(*) DESC, 1 LIMIT 40`, q ? ['%' + q + '%'] : []);
    res.json(r.rows.map(x => ({
      name: x.name, female: Number(x.female), male: Number(x.male),
      individuallySet: Number(x.individually_set),
      sex: Number(x.female) >= Number(x.male) ? 'F' : 'M',
    })));
  } catch(e) { res.json([]); }
});

// Most common forenames by census year, split by sex.
//
// There is no sex field: the census import parses one but census_entries has no
// column for it, so it is discarded. Rather than guess from a list of names, the
// sex of each *name* is inferred from the relationships its bearers hold — a
// name borne by daughters, wives and sisters is a girl's name. That uses the
// record's own evidence, and any name without enough of it stays unclassified
// rather than being assigned on a hunch.
app.get('/api/stats/first-names', async (req, res) => {
  if (!db) return res.json({});
  const limit = Math.min(parseInt(req.query.limit, 10) || 8, 25);
  try {
    const r = await db.query(`
      WITH named AS (
        SELECT ce.census_year,
               INITCAP(SPLIT_PART(TRIM(p.first_name), ' ', 1)) AS name,
               p.id AS person_id,
               LOWER(TRIM(COALESCE(ce.relationship,''))) AS rel
          FROM census_entries ce
          JOIN people p ON p.id = ce.person_id
         WHERE ce.census_year IS NOT NULL
           AND COALESCE(TRIM(p.first_name),'') <> ''
      ), gendered AS (
        SELECT name,
               COUNT(*) FILTER (WHERE rel IN ('wife','daughter','mother','sister','widow',
                 'niece','aunt','granddaughter','housekeeper','maid','housemaid','parlourmaid',
                 'kitchenmaid','cook','nurse','governess','lady')) AS female,
               COUNT(*) FILTER (WHERE rel IN ('son','father','brother','nephew','uncle',
                 'grandson','husband','butler','footman','groom','coachman','gardener')) AS male
          FROM named GROUP BY name
      ), sexed AS (
        SELECT name,
               CASE WHEN female + male < 2 THEN 'unknown'
                    WHEN female >= (female + male) * 0.8 THEN 'girls'
                    WHEN male   >= (female + male) * 0.8 THEN 'boys'
                    ELSE 'unknown' END AS sex
          FROM gendered
      ), counted AS (
        SELECT n.census_year, n.name, s.sex, COUNT(DISTINCT n.person_id) AS count
          FROM named n JOIN sexed s ON s.name = n.name
         WHERE LENGTH(n.name) > 1
         GROUP BY n.census_year, n.name, s.sex
      ), ranked AS (
        SELECT *, ROW_NUMBER() OVER (PARTITION BY census_year, sex
                                     ORDER BY count DESC, name) AS rn
          FROM counted
      )
      SELECT census_year, sex, name, count FROM ranked
       WHERE rn <= $1 ORDER BY census_year, sex, count DESC, name`, [limit]);

    const totals = await db.query(`
      SELECT ce.census_year, COUNT(DISTINCT p.id) AS total
        FROM census_entries ce JOIN people p ON p.id = ce.person_id
       WHERE ce.census_year IS NOT NULL AND COALESCE(TRIM(p.first_name),'') <> ''
       GROUP BY ce.census_year`);

    const out = {};
    for (const t of totals.rows) out[String(t.census_year)] = { total: Number(t.total), girls: [], boys: [], unknown: [] };
    for (const row of r.rows) {
      const y = out[String(row.census_year)];
      if (y) y[row.sex].push({ name: row.name, count: Number(row.count) });
    }
    res.json(out);
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// ── Significant people ───────────────────────────────────────────────────────
// Who is featured is a human decision. These endpoints surface *candidates* —
// people carrying a signal worth a second look — and record the curator's
// choice; nothing promotes itself. Deliberately no length-of-biography test: a
// long entry means someone had time to write, not that the subject mattered.
const SIGNAL_SQL = `
  CASE WHEN COALESCE(p.title,'') <> '' THEN 1 ELSE 0 END
+ CASE WHEN COALESCE(p.postnominals,'') <> '' THEN 1 ELSE 0 END
+ CASE WHEN COALESCE(p.wikipedia_url,'') <> '' THEN 1 ELSE 0 END
+ CASE WHEN p.bio ~* '(knight|baronet|lord mayor|high sheriff|deputy lieutenant|\\mM\\.?P\\.?\\M|O\\.?B\\.?E|M\\.?B\\.?E|C\\.?B\\.?E|K\\.?B\\.?E|C\\.?M\\.?G|D\\.?S\\.?O|alderman|mayor of)' THEN 1 ELSE 0 END
+ CASE WHEN COALESCE(p.known_as,'') ~* '(^|\\s)(sir|dame|lord|lady|rev|col|capt|major|hon)\\M' THEN 1 ELSE 0 END`;

function signalsOf(p) {
  const out = [];
  if ((p.title || '').trim()) out.push('has a title');
  if ((p.postnominals || '').trim()) out.push('has post-nominals');
  if ((p.wikipedia_url || '').trim()) out.push('has a Wikipedia article');
  const bio = p.bio || '';
  const m = bio.match(/(knight\w*|baronet|Lord Mayor|High Sheriff|Deputy Lieutenant|O\.?B\.?E|M\.?B\.?E|C\.?B\.?E|K\.?B\.?E|C\.?M\.?G|D\.?S\.?O|alderman|Mayor of)/i);
  if (m) out.push('biography mentions “' + m[1] + '”');
  if (/(^|\s)(Sir|Dame|Lord|Lady|Rev|Col|Capt|Major|Hon)\b/.test(p.known_as || '')) out.push('honorific in the name');
  if (p.property_count >= 3) out.push('linked to ' + p.property_count + ' properties');
  return out;
}

// Weeks run Monday to Sunday (1970-01-05 was a Monday), so the feature changes
// on a predictable day. splitmix32's finaliser mixes consecutive week numbers
// properly — a plain xorshift on a sequential seed clumps badly, repeating the
// same person three weeks running. If the draw lands on last week's person
// anyway, step on by one.
function weekNumber(d) {
  const t = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate());
  return Math.floor((t - Date.UTC(1970, 0, 5)) / 604800000);
}
function mix32(n) {
  let x = (n + 0x9e3779b9) >>> 0;
  x = Math.imul(x ^ (x >>> 16), 0x21f0aaad) >>> 0;
  x = Math.imul(x ^ (x >>> 15), 0x735a2d97) >>> 0;
  return (x ^ (x >>> 15)) >>> 0;
}
function weeklyIndex(date, n) {
  if (n <= 1) return 0;
  const w = weekNumber(date);
  const i = mix32(w) % n;
  return i === mix32(w - 1) % n ? (i + 1) % n : i;
}

// People already chosen for the page
app.get('/api/significant', async (req, res) => {
  if (!db) return res.json([]);
  try {
    const r = await db.query(`
      SELECT p.*, (SELECT COUNT(*) FROM (
                SELECT ce.property_id AS pid FROM census_entries ce WHERE ce.person_id=p.id AND ce.property_id IS NOT NULL
                UNION
                SELECT pr.property_id AS pid FROM property_residents pr WHERE pr.person_id=p.id
              ) linked) AS property_count
      FROM people p WHERE p.significant = TRUE
      ORDER BY COALESCE(p.last_name,''), COALESCE(p.first_name,'')`);
    res.json(r.rows.map(p => ({ ...p, signals: signalsOf(p) })));
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// Suggestions for the curator: a signal, but not yet chosen
app.get('/api/significant/candidates', async (req, res) => {
  if (!db) return res.json([]);
  try {
    const r = await db.query(`
      SELECT p.*, (SELECT COUNT(*) FROM (
                SELECT ce.property_id AS pid FROM census_entries ce WHERE ce.person_id=p.id AND ce.property_id IS NOT NULL
                UNION
                SELECT pr.property_id AS pid FROM property_residents pr WHERE pr.person_id=p.id
              ) linked) AS property_count,
             (${SIGNAL_SQL}) AS signal_count
      FROM people p
      WHERE COALESCE(p.significant,FALSE) = FALSE AND (${SIGNAL_SQL}) > 0
      ORDER BY (${SIGNAL_SQL}) DESC, COALESCE(p.last_name,'')
      LIMIT 200`);
    res.json(r.rows.map(p => ({ ...p, signals: signalsOf(p) })));
  } catch(e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/person/:id/significant', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  const id = parseInt(req.params.id, 10);
  const on = !!req.body.significant;
  const note = typeof req.body.note === 'string' ? req.body.note.slice(0, 500) : null;
  try {
    await db.query(
      `UPDATE people SET significant=$2, significance_note=$3, significant_by=$4,
         significant_at = CASE WHEN $2 THEN NOW() ELSE NULL END WHERE id=$1`,
      [id, on, on ? note : null, on ? (req.session.username || 'contributor') : null]);
    await logChange('person', id, req, on ? 'featured' : 'unfeatured', 'significant', null, String(on));
    res.json({ ok: true });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// Person of the week — random, but the same person all week for everyone, and
// it moves on by itself. Seeded by ISO week so it needs no stored state.
app.get('/api/person-of-week', async (req, res) => {
  if (!db) return res.json(null);
  try {
    const r = await db.query(`
      SELECT p.*, (SELECT COUNT(*) FROM (
                SELECT ce.property_id AS pid FROM census_entries ce WHERE ce.person_id=p.id AND ce.property_id IS NOT NULL
                UNION
                SELECT pr.property_id AS pid FROM property_residents pr WHERE pr.person_id=p.id
              ) linked) AS property_count
      FROM people p WHERE p.significant = TRUE ORDER BY p.id`);
    if (!r.rows.length) return res.json(null);
    const n = r.rows.length;
    const pick = r.rows[weeklyIndex(new Date(), n)];
    res.json({ ...pick, signals: signalsOf(pick), of: n });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// ── The Gazette (official public record) ──────────────────────────────────────
// Full-text search over scanned notices. Genuine finds are mostly deceased
// estates and winding-up notices naming a resident at a house — e.g. "Frederick
// Goddard, of Gartree House, the Park" (1909). Modern hits are usually
// companies that happen to share the name, so results carry their date and the
// caller decides. Proxied server-side for CORS, and cached for an hour so
// repeated panel views do not hammer their service.
const gazetteCache = new Map(); // query -> { at, rows }
const GAZETTE_TTL = 60 * 60 * 1000;

// The Gazette's feed gives .../page/9047/data.pdf. Strip the data.* tail to get
// the notice's own page, which is what a reader wants and what a citation needs.
const gazettePage = u => String(u || '').replace(/\/data\.(pdf|htm|html|xml|json)(\?.*)?$/i, '');

app.get('/api/gazette', async (req, res) => {
  const name = String(req.query.name || '').trim();
  if (name.length < 5) return res.json([]);
  const key = name.toLowerCase();
  const hit = gazetteCache.get(key);
  if (hit && Date.now() - hit.at < GAZETTE_TTL) return res.json(hit.rows);

  const url = 'https://www.thegazette.co.uk/all-notices/notice/data.feed?text='
    + encodeURIComponent('"' + name + '" Nottingham');
  try {
    const r = await fetch(url, {
      headers: { 'User-Agent': 'NottinghamParkHouses/1.0 (conservation record)' },
      signal: AbortSignal.timeout(12000),
    });
    if (!r.ok) return res.json([]);
    const xml = await r.text();
    const rows = [...xml.matchAll(/<entry>([\s\S]*?)<\/entry>/g)].map(m => {
      const e = m[1];
      const grab = re => ((e.match(re) || [])[1] || '').trim();
      const date = grab(/<published>(.*?)<\/published>/) || grab(/<updated>(.*?)<\/updated>/);
      const href = grab(/<link[^>]*href="(.*?)"/);
      const abs = href.startsWith('http') ? href : 'https://www.thegazette.co.uk' + href;
      return {
        title: grab(/<title>([\s\S]*?)<\/title>/).replace(/\s+/g, ' '),
        date: date.slice(0, 10),
        year: parseInt(date.slice(0, 4), 10) || null,
        // The feed points at the raw PDF. Send people to the notice page
        // instead: it shows the text in context with the rest of the issue,
        // it is the citable address, and it does not force a download.
        link: gazettePage(abs),
      };
    }).filter(x => x.link).sort((a, b) => (a.year || 9999) - (b.year || 9999)).slice(0, 10);
    gazetteCache.set(key, { at: Date.now(), rows });
    res.json(rows);
  } catch (e) {
    res.json([]);   // a search aid; never break the panel over it
  }
});

// ── Wikidata: notable people connected to Nottingham ──────────────────────────
// A cached cohort (born 1780-1920, born/died/resident in Nottingham) that the
// people page can check a resident against. Suggestions only — a shared surname
// is not an identification, so a birth year within 3 years is required before
// a match is called strong.
const WIKIDATA_FILE = path.join(__dirname, 'data', 'wikidata_nottingham.json');
let wikidataCache = null;
function readWikidata() {
  if (!wikidataCache) {
    try { wikidataCache = JSON.parse(fs.readFileSync(WIKIDATA_FILE, 'utf8')); }
    catch(e) { wikidataCache = []; }
  }
  return wikidataCache;
}

// How far apart two birth years may be and still count as the same person.
// Deliberately forgiving: many birth years here are derived from an age given
// at a census, which is a year out as often as not, and plainly wrong more
// rarely. Widening this finds more matches but admits more wrong ones — the
// year gap is shown on every suggestion so a person can judge.
const WD_YEAR_TOLERANCE = 3;

const wdNorm = v => String(v || '').toLowerCase().replace(/[^a-z ]/g, '').trim();

// The furniture a peerage or a baronetcy leaves on the end of a name, which is
// no part of what anybody was called in a census.
const WD_TITLE_WORDS = new Set([
  'st', 'nd', 'rd', 'th', 'bt', 'baronet', 'jr', 'sr', 'junior', 'senior',
  'baron', 'baroness', 'earl', 'countess', 'count', 'viscount', 'viscountess',
  'duke', 'duchess', 'marquess', 'marchioness', 'lord', 'lady', 'sir', 'dame',
  'of', 'the',
]);

// Every surname an entry could answer to. "Jesse Boot, 1st Baron Trent" is one
// man under two names: Boot to a census, Trent to Debrett. Indexed under the
// last word alone he sits under "trent" and no search for Boot can reach him —
// which is exactly why the sweep never found the most familiar name in the
// record. Forty-five entries are built this way, so it is the rule rather than
// the exception: Sir Ernest Jardine files under "baronet", and Albert Bingham
// under "bt".
function wdSurnames(name) {
  const whole = wdNorm(name).split(' ').filter(Boolean);
  if (whole.length < 2) return { first: null, surnames: [] };
  const first = whole[0];
  const out = new Set();
  // The name as given, up to any comma — the family name in nearly every case.
  const beforeComma = wdNorm(String(name || '').split(',')[0]).split(' ').filter(Boolean);
  const plain = beforeComma.filter(w => !WD_TITLE_WORDS.has(w));
  if (plain.length >= 2) out.add(plain[plain.length - 1]);
  // And the whole name stripped of its titles, which catches the territorial
  // half of a peerage — Trent, Belper, Middleton — since the record may hold
  // either.
  const stripped = whole.filter(w => !WD_TITLE_WORDS.has(w));
  if (stripped.length >= 2) out.add(stripped[stripped.length - 1]);
  if (!out.size) out.add(whole[whole.length - 1]);
  return { first, surnames: [...out] };
}

// Surname -> entries, built once. The sweep compares every resident against the
// whole pool, which is far too much work to do by scanning the list each time.
let wikidataBySurname = null;
function wikidataIndex() {
  if (!wikidataBySurname) {
    wikidataBySurname = new Map();
    for (const p of readWikidata()) {
      const { first, surnames } = wdSurnames(p.name);
      if (!first) continue;
      for (const surname of surnames) {
        if (!wikidataBySurname.has(surname)) wikidataBySurname.set(surname, []);
        wikidataBySurname.get(surname).push({ entry: p, firstPart: first });
      }
    }
  }
  return wikidataBySurname;
}

// Shared by the per-person suggestion and the sweep, so the two never disagree.
function matchWikidata({ first, last, born }) {
  const lastN = wdNorm(last), firstN = wdNorm(first).split(' ')[0];
  if (!lastN) return [];
  const bornY = parseInt(born, 10);
  const hits = [];
  for (const { entry, firstPart } of wikidataIndex().get(lastN) || []) {
    const firstMatches = firstN && firstPart === firstN;
    const yearGap = (bornY && entry.born) ? Math.abs(bornY - parseInt(entry.born, 10)) : null;
    if (yearGap !== null && yearGap > WD_YEAR_TOLERANCE) continue;  // same surname, wrong person
    let confidence = 'surname only';
    if (firstMatches && yearGap !== null) confidence = 'name and birth year';
    else if (firstMatches) confidence = 'name only';
    hits.push({ ...entry, confidence, yearGap });
  }
  const rank = { 'name and birth year': 0, 'name only': 1, 'surname only': 2 };
  return hits.sort((a, b) => rank[a.confidence] - rank[b.confidence]);
}

app.get('/api/wikidata-match', (req, res) => {
  res.json(matchWikidata({
    first: req.query.first, last: req.query.last, born: req.query.born,
  }).slice(0, 8));
});

// Every resident checked against the pool at once, so matches can be worked
// through rather than stumbled upon one person at a time. The per-person
// suggestion on the People page still works exactly as before; this is the
// same matching, run across everybody.
app.get('/api/wikidata/sweep', requireContributor, async (req, res) => {
  if (!db) return res.json({ matches: [], total: 0, scanned: 0 });
  try {
    const r = await db.query(`
      SELECT p.id, p.first_name, p.last_name, p.known_as, p.title, p.postnominals,
             p.born_year, p.died_year, p.bio,
             ARRAY(SELECT w.qid FROM person_wikidata w WHERE w.person_id = p.id) AS decided
        FROM people p
       WHERE p.wikipedia_url IS NULL OR p.wikipedia_url = ''
       ORDER BY p.last_name, p.first_name`);

    const matches = [];
    for (const p of r.rows) {
      const decided = new Set(p.decided || []);
      const strong = matchWikidata({
        first: p.first_name, last: p.last_name, born: p.born_year,
      }).filter(m => m.confidence === 'name and birth year' && !decided.has(m.qid));
      if (!strong.length) continue;
      const bio = (p.bio || '').replace(/\s+/g, ' ').trim();
      matches.push({
        id: p.id, first_name: p.first_name, last_name: p.last_name,
        known_as: p.known_as, title: p.title, postnominals: p.postnominals,
        born_year: p.born_year, died_year: p.died_year,
        bio: bio.length > 240 ? bio.slice(0, 240) + '…' : bio,
        candidates: strong.slice(0, 4),
      });
    }
    res.json({
      matches, total: matches.reduce((n, m) => n + m.candidates.length, 0),
      scanned: r.rows.length, tolerance: WD_YEAR_TOLERANCE,
    });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// What has already been decided, newest first — so a wrong click can be found
// and undone rather than being permanent.
app.get('/api/wikidata/decided', requireContributor, async (req, res) => {
  if (!db) return res.json([]);
  try {
    const r = await db.query(`
      SELECT w.person_id, w.qid, w.name, w.url, w.status, w.decided_at,
             p.first_name, p.last_name, p.born_year
        FROM person_wikidata w
        JOIN people p ON p.id = w.person_id
       ORDER BY w.decided_at DESC
       LIMIT 200`);
    res.json(r.rows);
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// Confirming records the article on the person; dismissing remembers the 'no'
// so the sweep stops offering it.
app.post('/api/person/:id/wikidata', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  const personId = parseInt(req.params.id, 10);
  const { qid, name, url } = req.body || {};
  const asked = req.body && req.body.status;
  const status = asked === 'confirmed' ? 'confirmed' : asked === 'reset' ? 'reset' : 'dismissed';
  if (!personId || !qid) return res.status(400).json({ error: 'person and qid required' });
  const who = (req.session && (req.session.username || req.session.researchKey)) || null;
  try {
    // Undoing a wrong click: forget the decision so the sweep offers it again.
    // A confirmation also wrote the article onto the person, and someone with a
    // Wikipedia link is out of the sweep's scope entirely — so that has to come
    // off too, or undoing a confirmation would quietly do nothing. Only clear it
    // when it is still the link this decision set, never someone else's work.
    if (status === 'reset') {
      const prev = await db.query(
        `DELETE FROM person_wikidata WHERE person_id=$1 AND qid=$2 RETURNING status, url`,
        [personId, String(qid)]);
      const row = prev.rows[0];
      if (row && row.status === 'confirmed' && row.url) {
        await db.query(`UPDATE people SET wikipedia_url=NULL WHERE id=$1 AND wikipedia_url=$2`,
          [personId, row.url]);
      }
      return res.json({ ok: true, status });
    }
    await db.query(
      `INSERT INTO person_wikidata (person_id, qid, name, url, status, decided_by)
            VALUES ($1,$2,$3,$4,$5,$6)
       ON CONFLICT (person_id, qid)
       DO UPDATE SET status=EXCLUDED.status, decided_by=EXCLUDED.decided_by, decided_at=NOW()`,
      [personId, String(qid), name || null, url || null, status, who]);
    if (status === 'confirmed' && url) {
      await db.query(`UPDATE people SET wikipedia_url=$2 WHERE id=$1`, [personId, String(url)]);
    }
    res.json({ ok: true, status });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// ── Historic England listed entries ───────────────────────────────────────────
// The National Heritage List treats gateways, walls and railings as separate
// entries, so a nearest-match is unreliable. This returns the candidates near a
// property and leaves the identification to a person.
const NHLE_FILE = path.join(__dirname, 'data', 'nhle.json');
let nhleCache = null;
function readNhle() {
  if (!nhleCache) {
    try { nhleCache = JSON.parse(fs.readFileSync(NHLE_FILE, 'utf8')); }
    catch(e) { nhleCache = []; }
  }
  return nhleCache;
}

// The list itself, live from Historic England's own feed, falling back to the
// snapshot in data/nhle.json when they cannot be reached. The snapshot was 101
// entries against their 120 for the same ground, so it had drifted.
let nhleLive = null, nhleLiveAt = 0;
const NHLE_TTL = 12 * 60 * 60 * 1000;
const NHLE_URL = 'https://services-eu1.arcgis.com/ZOdPfBS3aqqDYPUQ/arcgis/rest/services/'
  + 'National_Heritage_List_for_England_NHLE_v02_VIEW/FeatureServer/0/query';
async function readNhleLive() {
  if (nhleLive && Date.now() - nhleLiveAt < NHLE_TTL) return nhleLive;
  const [s, w, n, e] = PARK_BBOX;
  const q = new URLSearchParams({
    where: '1=1',
    geometry: JSON.stringify({ xmin: w, ymin: s, xmax: e, ymax: n, spatialReference: { wkid: 4326 } }),
    geometryType: 'esriGeometryEnvelope', inSR: '4326',
    spatialRel: 'esriSpatialRelIntersects', outFields: '*',
    returnGeometry: 'true', outSR: '4326', f: 'json',
  });
  try {
    const r = await fetch(NHLE_URL + '?' + q.toString(), {
      headers: { 'User-Agent': 'NottinghamParkHouses/1.0 (conservation record)' },
      signal: AbortSignal.timeout(20000),
    });
    if (!r.ok) return nhleLive;
    const d = await r.json();
    if (d.error || !Array.isArray(d.features)) return nhleLive;
    nhleLive = d.features.filter(f => f.geometry && f.geometry.points && f.geometry.points[0])
      .map(f => {
        const a = f.attributes, pt = f.geometry.points[0];
        return {
          entry: a.ListEntry, name: a.Name, grade: a.Grade,
          listed: a.ListDate ? new Date(a.ListDate).toISOString().slice(0, 10) : null,
          ngr: a.NGR || null,
          link: a.hyperlink || ('https://historicengland.org.uk/listing/the-list/list-entry/' + a.ListEntry),
          lat: pt[1], lng: pt[0],
        };
      });
    nhleLiveAt = Date.now();
  } catch (err) { console.warn('nhle live:', err.message); }
  return nhleLive;
}

// Where a property actually is: a hand placement beats the imported position.
// The panels were searching around the imported one, which for a hand-placed
// house can be hundreds of metres out — 21 Lenton Road's is 400m away, so the
// plaque on its own front wall never showed.
async function propertyPosition(id) {
  const coords = await loadCoords();
  const c = coords[id] || coords[String(id)];
  if (c && c.lat != null) return { lat: Number(c.lat), lng: Number(c.lng) };
  try {
    const p = JSON.parse(readAllPropsCached().body).find(x => x.id === Number(id));
    if (p && p.lat != null) return { lat: Number(p.lat), lng: Number(p.lng) };
  } catch (e) {}
  return null;
}

// Every list entry recorded against a house. The list covers a house, its
// gateway and its boundary wall as separate entries — 14 Cavendish Crescent
// North holds Park House and the gateway and wall in front of it — so a house
// often holds several. The extras are kept as bare entry numbers: the name and
// grade are read from the list itself, so nothing recorded here goes stale.
// list_entries holds the ones added from the site, nhle_also the ones recorded
// in all_props.json.
function recordedEntries(ov, row) {
  return new Set([
    ...(ov && ov.list_entry ? [String(ov.list_entry)] : []),
    ...((ov && ov.list_entries) || []).map(String),
    ...((row && row.nhle_also) || []).map(String),
  ]);
}

// Every house's suggestions in one request. The map asks house by house, which
// is four hundred requests to work through the estate, and the answer is the
// same list of entries measured against four hundred positions.
app.get('/api/nhle/review', requireContributor, async (req, res) => {
  try {
    const entries = (await readNhleLive()) || readNhle();
    const radius = Math.min(parseFloat(req.query.radius) || 40, 1000);
    const [coords, ovs] = await Promise.all([loadCoords(), loadProps()]);
    let props = [];
    try { props = JSON.parse(readAllPropsCached().body); } catch (e) {}
    const taken = new Map();
    // An entry can belong to two houses — 1247219 is "numbers 119 and 121 and
    // attached boundary wall and railings" — so who holds it is a list.
    const holders = new Map();
    for (const p of props) {
      for (const e of recordedEntries(ovs[p.id] || ovs[String(p.id)], p)) {
        taken.set(e, p.id);
        holders.set(e, [...(holders.get(e) || []), p.id]);
      }
    }
    for (const [id, ov] of Object.entries(ovs)) {
      for (const e of recordedEntries(ov, null)) if (!taken.has(e)) taken.set(e, Number(id));
    }
    const byEntry = new Map(entries.map(e => [String(e.entry), e]));
    const out = props.map(p => {
      const c = coords[p.id] || coords[String(p.id)];
      const lat = c && c.lat != null ? Number(c.lat) : (p.lat != null ? Number(p.lat) : null);
      const lng = c && c.lng != null ? Number(c.lng) : (p.lng != null ? Number(p.lng) : null);
      const ov = ovs[p.id] || ovs[String(p.id)] || {};
      const dismissed = (ov.nhle_dismissed || []).map(String);
      const gone = new Set(dismissed);
      const recorded = recordedEntries(ov, p);
      const fromFile = new Set(((p.nhle_also) || []).map(String));
      const always = new Set([...recorded, ...((p.nhle_extra) || []).map(String)]);
      const away = e => (lat == null || lng == null || e.lat == null) ? null : Math.round(Math.hypot(
        (e.lng - lng) * Math.cos(lat * Math.PI / 180) * 111320, (e.lat - lat) * 110540));
      // The extras this house holds besides its main entry, named from the list.
      const also = [...recorded]
        .filter(id => id !== String(ov.list_entry || ''))
        .map(id => {
          const e = byEntry.get(id);
          return {
            entry: id, name: e ? e.name : null, grade: e ? e.grade : null,
            listed: e ? e.listed : null, distance: e ? away(e) : null,
            link: e ? e.link : 'https://historicengland.org.uk/listing/the-list/list-entry/' + id,
            fromFile: fromFile.has(id),
            heldBy: (holders.get(id) || []).filter(x => x !== p.id),
          };
        });
      let suggestions = [];
      if (lat != null && lng != null) {
        suggestions = entries.map(e => ({ ...e, distance: away(e) }))
          .filter(e => (e.distance <= radius || always.has(String(e.entry)))
            && !recorded.has(String(e.entry))
            && !gone.has(String(e.entry))
            && !(taken.has(String(e.entry)) && taken.get(String(e.entry)) !== p.id))
          .sort((a, b) => a.distance - b.distance)
          .slice(0, 12);
      }
      return {
        id: p.id, address: p.address || p.name || ('Property ' + p.id), street: p.street || '',
        listed: p.listed || null, hasPosition: lat != null, placedByHand: !!(c && c.lat != null),
        chosen: ov.list_entry ? {
          entry: ov.list_entry, name: ov.list_name || null, grade: ov.list_grade || null,
          listed: ov.list_date || null,
          link: ov.list_link || ('https://historicengland.org.uk/listing/the-list/list-entry/' + ov.list_entry),
          heldBy: (holders.get(String(ov.list_entry)) || []).filter(x => x !== p.id),
        } : null,
        also, dismissed, suggestions,
        // Named, not just counted: "three dismissed here" tells nobody which
        // three, and a dismissal made in error cannot be found again.
        dismissedEntries: dismissed.map(id => {
          const e = byEntry.get(id);
          return {
            entry: id, name: e ? e.name : null, grade: e ? e.grade : null,
            listed: e ? e.listed : null, distance: e ? away(e) : null,
            link: e ? e.link : 'https://historicengland.org.uk/listing/the-list/list-entry/' + id,
            heldBy: (holders.get(id) || []).filter(x => x !== p.id),
          };
        }),
      };
    });
    res.json({
      radius,
      properties: out,
      totals: {
        properties: out.length,
        withSuggestions: out.filter(p => p.suggestions.length).length,
        suggestions: out.reduce((n, p) => n + p.suggestions.length, 0),
        chosen: out.filter(p => p.chosen).length,
        dismissed: out.reduce((n, p) => n + p.dismissed.length, 0),
        noPosition: out.filter(p => !p.hasPosition).length,
      },
    });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.get('/api/nhle', async (req, res) => {
  let entries = (await readNhleLive()) || readNhle();
  let always = new Set(), mineRecorded = new Set(), mineFromFile = new Set();
  let lat = parseFloat(req.query.lat), lng = parseFloat(req.query.lng);
  const propId = parseInt(req.query.property, 10);
  if (Number.isInteger(propId)) {
    const here = await propertyPosition(propId);
    if (here) { lat = here.lat; lng = here.lng; }
    // An entry already recorded as another property's is not a suggestion for
    // this one, and one this property has been told is not its own stays gone.
    const ovs = await loadProps();
    let props = [];
    try { props = JSON.parse(readAllPropsCached().body); } catch (e) {}
    const taken = new Set();
    for (const p of props) {
      if (p.id === propId) continue;
      for (const e of recordedEntries(ovs[p.id] || ovs[String(p.id)], p)) taken.add(e);
    }
    for (const [id, ov] of Object.entries(ovs)) {
      if (Number(id) === propId) continue;
      for (const e of recordedEntries(ov, null)) taken.add(e);
    }
    const mine = ovs[propId] || ovs[String(propId)] || {};
    const dismissed = new Set((mine.nhle_dismissed || []).map(String));
    const row = props.find(p => p.id === propId) || null;
    mineRecorded = recordedEntries(mine, row);
    mineFromFile = new Set(((row && row.nhle_also) || []).map(String));
    // Entries this house always shows, however far off: the ones recorded
    // against it, and any named in nhle_extra in all_props.json. The list's
    // points do not always sit on the building they describe, so a house can
    // want an entry that falls outside the radius.
    always = new Set([...mineRecorded, ...((row && row.nhle_extra) || []).map(String)]);
    entries = entries.filter(e => always.has(String(e.entry))
      || (!taken.has(String(e.entry)) && !dismissed.has(String(e.entry))));
  }
  if (!isFinite(lat) || !isFinite(lng)) return res.json(entries);
  // 40m: the list entry for a house sits on or near the house. At 120m every
  // house in a street was offered every neighbour's walls and gate piers.
  const radius = Math.min(parseFloat(req.query.radius) || 40, 1000);
  const m = (a, b) => Math.hypot(
    (a.lng - b.lng) * Math.cos(lat * Math.PI / 180) * 111320,
    (a.lat - b.lat) * 110540);
  res.json(entries
    .map(e => ({ ...e, distance: Math.round(m(e, { lat, lng })),
                 recorded: mineRecorded.has(String(e.entry)),
                 fromFile: mineFromFile.has(String(e.entry)) }))
    .filter(e => e.distance <= radius || always.has(String(e.entry)))
    .sort((a, b) => a.distance - b.distance)
    .slice(0, 12));
});

// ── Open Plaques ──────────────────────────────────────────────────────────────
// Commemorative plaques, from the open data at openplaques.org. Fetched once and
// held, because the list for a city changes about as often as the plaques do.
let plaqueCache = null, plaqueAt = 0;
const PLAQUE_TTL = 12 * 60 * 60 * 1000;
async function readPlaques() {
  if (plaqueCache && Date.now() - plaqueAt < PLAQUE_TTL) return plaqueCache;
  try {
    const r = await fetch('https://openplaques.org/places/gb/areas/nottingham/plaques.json', {
      headers: { 'User-Agent': 'NottinghamParkHouses/1.0 (conservation record)' },
      signal: AbortSignal.timeout(15000),
    });
    if (!r.ok) return plaqueCache || [];
    const raw = await r.json();
    const list = Array.isArray(raw) ? raw : (raw.plaques || []);
    plaqueCache = list
      .filter(p => p.latitude && p.longitude)
      .map(p => ({
        id: p.id, inscription: p.inscription || null, title: p.title || null,
        address: p.address || null, colour: p.colour_name || null,
        erected: p.erected_at || null, uri: p.uri || null,
        lat: Number(p.latitude), lng: Number(p.longitude),
        // subjects comes back as a plain string, not the array the shape suggests.
        people: typeof p.subjects === 'string'
          ? p.subjects.split(/\s+and\s+|,\s*/).map(x => x.trim()).filter(Boolean)
          : (Array.isArray(p.subjects) ? p.subjects.map(x => x && x.name).filter(Boolean) : []),
      }));
    plaqueAt = Date.now();
  } catch (e) { console.warn('plaques:', e.message); }
  return plaqueCache || [];
}

// Open Plaques' own pins are placed by hand and are often a street out; its
// address field is more reliable. Where the address names a house this record
// holds — "21 Lenton Road", "Adam House, Clumber Road East" — the plaque is
// put on that house, and says so.
async function placedPlaques() {
  const all = await readPlaques();
  let props = [];
  try { props = JSON.parse(readAllPropsCached().body); } catch (e) {}
  const coords = await loadCoords();
  const norm = v => ' ' + String(v || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim() + ' ';
  const keys = [];
  for (const p of props) {
    const street = norm(p.street).trim();
    if (!street) continue;
    const no = String(p.no || '').trim().toLowerCase();
    if (/^\d+[a-z]?$/.test(no)) keys.push({ p, key: norm(no + ' ' + street), how: 'number' });
    for (const n of [p.name, p.house_name, ...String(p.prev_house_name || '').split('\n')]) {
      const k = norm(n).trim();
      if (k.length > 5) keys.push({ p, key: ' ' + k + ' ', street, how: 'name' });
    }
  }
  // What the record knows that the feed does not — above all, that a plaque is
  // a landmark and not on any house.
  let notes = {};
  try { notes = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'plaque_notes.json'), 'utf8')).plaques || {}; }
  catch (e) {}
  return all.map(raw => {
    const n = notes[String(raw.id)];
    const pl = n ? { ...raw, landmark: !!n.landmark, setting: n.setting || null,
                     note: n.note || null, note_source: n.source || null } : raw;
    if (pl.landmark) return pl;
    const a = norm(pl.address);
    const hit = keys.find(k => a.includes(k.key)
      && (k.how === 'number' || a.includes(' ' + k.street + ' ') || a.includes(' the park ')));
    if (!hit) return pl;
    const c = coords[hit.p.id] || coords[String(hit.p.id)];
    const lat = c ? Number(c.lat) : (hit.p.lat != null ? Number(hit.p.lat) : pl.lat);
    const lng = c ? Number(c.lng) : (hit.p.lng != null ? Number(hit.p.lng) : pl.lng);
    return { ...pl, property_id: hit.p.id, lat, lng, feed_lat: pl.lat, feed_lng: pl.lng };
  });
}

app.get('/api/plaques', async (req, res) => {
  const all = await placedPlaques();
  let lat = parseFloat(req.query.lat), lng = parseFloat(req.query.lng);
  const propId = parseInt(req.query.property, 10);
  if (Number.isInteger(propId)) {
    const here = await propertyPosition(propId);
    if (here) { lat = here.lat; lng = here.lng; }
  }
  if (!isFinite(lat) || !isFinite(lng)) return res.json(all);
  const radius = Math.min(parseFloat(req.query.radius) || 120, 2000);
  const m = p => Math.hypot(
    (p.lng - lng) * Math.cos(lat * Math.PI / 180) * 111320, (p.lat - lat) * 110540);
  res.json(all.map(p => ({ ...p, distance: Math.round(m(p)),
                           atThisHouse: Number.isInteger(propId) && p.property_id === propId }))
              .filter(p => p.atThisHouse || p.distance <= radius)
              .sort((a, b) => (b.atThisHouse - a.atThisHouse) || (a.distance - b.distance)).slice(0, 8));
});

// ── OpenStreetMap building outlines ───────────────────────────────────────────
// Overpass knows the footprint and often the address of every building in The
// Park. That is a survey, which is what a good many of this record's positions
// are not: houses created from a census address are placed by reasoning about
// the enumerator's round and marked provisional. This is how they get fixed.
let osmCache = null, osmAt = 0;
const OSM_TTL = 24 * 60 * 60 * 1000;
const PARK_BBOX = [52.9475, -1.1720, 52.9560, -1.1545];   // s, w, n, e
async function readOsmBuildings() {
  if (osmCache && Date.now() - osmAt < OSM_TTL) return osmCache;
  const [s, w, n, e] = PARK_BBOX;
  const q = `[out:json][timeout:40];(way["building"](${s},${w},${n},${e});` +
            `relation["building"](${s},${w},${n},${e}););out tags center;`;
  try {
    const r = await fetch('https://overpass-api.de/api/interpreter', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded',
                 'User-Agent': 'NottinghamParkHouses/1.0 (conservation record)' },
      body: 'data=' + encodeURIComponent(q),
      signal: AbortSignal.timeout(60000),
    });
    if (!r.ok) return osmCache || [];
    const d = await r.json();
    osmCache = (d.elements || []).filter(el => el.center).map(el => ({
      id: el.type + '/' + el.id,
      lat: el.center.lat, lng: el.center.lon,
      name: (el.tags && (el.tags.name || el.tags['addr:housename'])) || null,
      number: (el.tags && el.tags['addr:housenumber']) || null,
      street: (el.tags && el.tags['addr:street']) || null,
      building: (el.tags && el.tags.building) || null,
    }));
    osmAt = Date.now();
  } catch (err) { console.warn('overpass:', err.message); }
  return osmCache || [];
}

app.get('/api/osm-buildings', async (req, res) => {
  const all = await readOsmBuildings();
  const lat = parseFloat(req.query.lat), lng = parseFloat(req.query.lng);
  if (!isFinite(lat) || !isFinite(lng)) {
    return res.json({ count: all.length, named: all.filter(b => b.name || b.number).length });
  }
  const radius = Math.min(parseFloat(req.query.radius) || 60, 500);
  const m = b => Math.hypot(
    (b.lng - lng) * Math.cos(lat * Math.PI / 180) * 111320, (b.lat - lat) * 110540);
  res.json(all.map(b => ({ ...b, distance: Math.round(m(b)) }))
              .filter(b => b.distance <= radius)
              .sort((a, b) => a.distance - b.distance).slice(0, 10));
});

// Match the record's houses to the buildings OpenStreetMap holds, and report
// where they disagree. A good many positions here were reasoned rather than
// surveyed — placed from the enumerator's round and marked provisional — and
// this is the only cheap way to find the ones that are simply wrong.
app.get('/api/osm-audit', requireContributor, async (req, res) => {
  try {
    const buildings = await readOsmBuildings();
    if (!buildings.length) return res.json({ error: 'OpenStreetMap did not answer; try again in a minute', rows: [], orphans: [] });
    const props = JSON.parse(readAllPropsCached().body);
    const coords = await loadCoords();
    const norm = v => String(v || '').toLowerCase().replace(/[^a-z0-9 ]/g, '').replace(/\s+/g, ' ').trim();
    const numKey = v => String(v || '').toLowerCase().replace(/\s/g, '');

    const byAddr = new Map(), byName = new Map();
    for (const b of buildings) {
      if (b.street && b.number) {
        const k = norm(b.street) + '|' + numKey(b.number);
        if (!byAddr.has(k)) byAddr.set(k, b);
      }
      if (b.name) {
        const k = norm(b.name);
        if (!byName.has(k)) byName.set(k, b);
      }
    }
    const claimed = new Set();
    const metres = (a, b) => Math.hypot(
      (a.lng - b.lng) * Math.cos(a.lat * Math.PI / 180) * 111320, (a.lat - b.lat) * 110540);

    const rows = [];
    for (const p of props) {
      const c = coords[p.id];
      const here = c ? { lat: Number(c.lat), lng: Number(c.lng) }
                     : (p.lat != null ? { lat: Number(p.lat), lng: Number(p.lng) } : null);
      const names = [p.name, p.house_name, ...String(p.prev_house_name || '').split('\n')]
        .map(norm).filter(Boolean);
      let hit = null, how = null;
      if (p.street && p.no) {
        hit = byAddr.get(norm(p.street) + '|' + numKey(p.no)) || null;
        if (hit) how = 'number and street';
      }
      if (!hit) {
        for (const n of names) { if (byName.has(n)) { hit = byName.get(n); how = 'house name'; break; } }
      }
      if (!hit) continue;
      claimed.add(hit.id);
      rows.push({
        property_id: p.id,
        label: [(p.no || '').trim(), p.street].filter(Boolean).join(' ')
             + (p.name ? ` (${p.name})` : ''),
        how, osm: hit, here,
        placed: !!c,
        distance: here ? Math.round(metres(here, hit)) : null,
        provisional: !!(p.sources && /provisional/i.test(JSON.stringify(p.sources))),
      });
    }
    rows.sort((a, b) => (b.distance === null ? 1e9 : b.distance) - (a.distance === null ? 1e9 : a.distance));

    // Buildings OpenStreetMap has a name for that the record does not.
    const recordNames = new Set();
    for (const p of props) for (const n of [p.name, p.house_name, ...String(p.prev_house_name || '').split('\n')])
      if (norm(n)) recordNames.add(norm(n));
    let dismissed = new Set();
    if (db) {
      try { dismissed = new Set((await db.query('SELECT osm_id FROM osm_dismissed')).rows.map(r => r.osm_id)); }
      catch (e) {}
    }
    const orphans = buildings
      .filter(b => b.name && !claimed.has(b.id) && !recordNames.has(norm(b.name)))
      .filter(b => !/^(flats?|garages?|shed|outbuilding)$/i.test(b.name))
      .filter(b => !dismissed.has(b.id))
      .map(b => ({ id: b.id, name: b.name, number: b.number, street: b.street, lat: b.lat, lng: b.lng }))
      .sort((a, b) => String(a.street || '').localeCompare(String(b.street || '')));

    res.json({ buildings: buildings.length, matched: rows.length, rows, orphans,
               dismissedCount: dismissed.size });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// Put a named building out of the orphan list for good — it is not a house this
// record wants, and saying so once should stop it being offered again.
app.post('/api/osm-dismiss', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  const id = String((req.body && req.body.osm_id) || '').trim();
  if (!id) return res.status(400).json({ error: 'an OpenStreetMap id is required' });
  const on = !(req.body && req.body.on === false);
  const who = (await getResearchKey(req.session)) || null;
  try {
    if (!on) {
      await db.query('DELETE FROM osm_dismissed WHERE osm_id=$1', [id]);
      return res.json({ ok: true, dismissed: false });
    }
    await db.query(
      `INSERT INTO osm_dismissed (osm_id, name, note, set_by) VALUES ($1,$2,$3,$4)
       ON CONFLICT (osm_id) DO UPDATE SET note=EXCLUDED.note, set_by=EXCLUDED.set_by, set_at=NOW()`,
      [id, (req.body && req.body.name) || null, (req.body && req.body.note) || null, who]);
    res.json({ ok: true, dismissed: true });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// ── Stats API ─────────────────────────────────────────────────────────────────
app.get('/api/stats', async (req, res) => {
  try {
    const allProps = JSON.parse(fs.readFileSync(ALL_PROPS_FILE, 'utf8'));
    const totalProps = allProps.length;
    const propsWithDesc = allProps.filter(p => p.desc && p.desc.length > 50).length;

    let totalPeople = 0, propsWithPeople = 0, totalOccupations = 0;
    let jobsByCensusYear = {}, topJobs = {};
    let propsWithPhotos = 0;

    // Stats from DB — each query independent so one failure doesn't kill the rest
    if (db) {
      const safe = q => db.query(q).catch(() => ({ rows: [{ cnt: 0 }] }));
      const [pplRes, occRes, propPplRes, photoRes, topOccRes, censusRes] = await Promise.all([
        safe('SELECT COUNT(*) as cnt FROM people'),
        safe('SELECT COUNT(*) as cnt FROM occupations'),
        safe('SELECT COUNT(DISTINCT property_id) as cnt FROM census_entries WHERE property_id IS NOT NULL'),
        safe(`SELECT COUNT(DISTINCT property_id) as cnt FROM property_overrides WHERE photo_url IS NOT NULL AND photo_url != ''`),
        db.query(`SELECT LOWER(occupation) as occ, COUNT(*) as cnt FROM occupations GROUP BY LOWER(occupation) ORDER BY cnt DESC LIMIT 15`).catch(() => ({ rows: [] })),
        db.query(`SELECT ce.census_year, LOWER(o.occupation) as occ, COUNT(DISTINCT ce.person_id) as cnt
                  FROM census_entries ce JOIN occupations o ON o.person_id=ce.person_id
                  GROUP BY ce.census_year, LOWER(o.occupation) ORDER BY ce.census_year, cnt DESC`).catch(() => ({ rows: [] }))
      ]);
      totalPeople = parseInt(pplRes.rows[0]?.cnt || 0);
      totalOccupations = parseInt(occRes.rows[0]?.cnt || 0);
      propsWithPeople = parseInt(propPplRes.rows[0]?.cnt || 0);
      propsWithPhotos = parseInt(photoRes.rows[0]?.cnt || 0);

      topOccRes.rows.forEach(r => { topJobs[r.occ] = parseInt(r.cnt); });
      censusRes.rows.forEach(r => {
        const yr = String(r.census_year);
        if (!jobsByCensusYear[yr]) jobsByCensusYear[yr] = {};
        jobsByCensusYear[yr][r.occ] = parseInt(r.cnt);
      });
    }

    const topJobsList = Object.entries(topJobs).sort((a,b)=>b[1]-a[1]).slice(0,15).map(([job,count])=>({job,count}));

    // Building decades from allProps built years
    const decades = {};
    allProps.forEach(p => {
      const yr = parseInt(p.built);
      if (yr > 1700 && yr < 1980) {
        const dec = Math.floor(yr / 10) * 10;
        decades[dec] = (decades[dec] || 0) + 1;
      }
    });

    // Top streets
    const streets = {};
    allProps.forEach(p => { if (p.street) streets[p.street] = (streets[p.street] || 0) + 1; });
    const topStreets = Object.entries(streets).sort((a,b)=>b[1]-a[1]).slice(0,20).map(([s,n])=>({street:s,count:n}));

    // Architects by property count (from architect_works, where each work can have property_id or address matching Park estate)
    let topArchitects = [];
    if (db) {
      const archRes = await db.query(`
        SELECT p.id, p.first_name, p.last_name, p.known_as, COUNT(aw.id) as works
        FROM people p JOIN architect_works aw ON aw.person_id = p.id
        GROUP BY p.id ORDER BY works DESC LIMIT 15
      `).catch(() => ({ rows: [] }));
      topArchitects = archRes.rows.map(r => ({
        id: r.id,
        name: r.known_as || `${r.first_name} ${r.last_name}`.trim(),
        works: parseInt(r.works)
      }));
    }

    res.json({
      properties: { total: totalProps, withDesc: propsWithDesc, withPeople: propsWithPeople, withPhotos: propsWithPhotos },
      people: { total: totalPeople, occupations: totalOccupations },
      jobs: { byCensusYear: jobsByCensusYear, topJobs: topJobsList },
      decades,
      topStreets,
      topArchitects
    });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// ── Census coverage API (for map slider) ─────────────────────────────────────
// Returns {propId: [years...]} for all properties with any census/resident record
app.get('/api/census-coverage', async (req, res) => {
  if (!db) return res.json({});
  try {
    const [ceRes, prRes] = await Promise.all([
      db.query(`SELECT property_id, census_year FROM census_entries WHERE property_id IS NOT NULL GROUP BY property_id, census_year`),
      db.query(`SELECT property_id, from_year, to_year FROM property_residents`)
    ]);
    const coverage = {};
    const censusYears = [1841,1851,1861,1871,1881,1891,1901,1911];
    ceRes.rows.forEach(r => {
      const id = String(r.property_id);
      if (!coverage[id]) coverage[id] = new Set();
      coverage[id].add(r.census_year);
    });
    // Also infer from property_residents from_year/to_year ranges
    prRes.rows.forEach(r => {
      if (!r.from_year && !r.to_year) return;
      const id = String(r.property_id);
      if (!coverage[id]) coverage[id] = new Set();
      censusYears.forEach(yr => {
        const from = r.from_year || 0;
        const to = r.to_year || 9999;
        if (yr >= from && yr <= to) coverage[id].add(yr);
      });
    });
    // Serialise sets to arrays
    const out = {};
    Object.entries(coverage).forEach(([id, s]) => { out[id] = [...s].sort(); });
    res.json(out);
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// ── Property timeline API ─────────────────────────────────────────────────────
app.get('/api/property/:id/timeline', async (req, res) => {
  if (!db) return res.json({ events: [] });
  const propId = parseInt(req.params.id);
  try {
    const [resRes, censusRes] = await Promise.all([
      db.query(`SELECT pr.id as resident_id, pr.from_year, pr.to_year, pr.notes,
                       p.first_name, p.last_name, p.known_as, p.title, p.postnominals, p.born_year, p.died_year, p.id as person_id
                FROM property_residents pr JOIN people p ON p.id=pr.person_id
                WHERE pr.property_id=$1 ORDER BY pr.from_year NULLS LAST`, [propId]),
      db.query(`SELECT ce.census_year, ce.relationship, ce.age_at_census, ce.occupation_at_census,
                       p.first_name, p.last_name, p.known_as, p.id as person_id
                FROM census_entries ce JOIN people p ON p.id=ce.person_id
                WHERE ce.property_id=$1 ORDER BY ce.census_year, ce.relationship`, [propId])
    ]);
    res.json({ residents: resRes.rows, censusEntries: censusRes.rows });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// ── My Contributions API ──────────────────────────────────────────────────────
app.get('/api/my-contributions', async (req, res) => {
  if (!req.session || !req.session.userId) return res.status(401).json({ error: 'Login required' });
  if (!db) return res.json([]);
  try {
    const userId = req.session.userId;
    const username = req.session.username || req.session.email;
    const r = await db.query(`
      SELECT cl.entity_type, cl.entity_id, cl.action, cl.field, cl.new_value, cl.created_at
      FROM change_log cl
      WHERE cl.username = $1
      ORDER BY cl.created_at DESC
      LIMIT 200
    `, [username]);
    res.json(r.rows);
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// ── Watchlist API ─────────────────────────────────────────────────────────────
app.get('/api/watchlist', async (req, res) => {
  if (!req.session || !req.session.userId) return res.status(401).json({ error: 'Login required' });
  if (!db) return res.json([]);
  try {
    const r = await db.query(
      `SELECT property_id, created_at FROM property_watches WHERE user_id=$1 ORDER BY created_at DESC`,
      [req.session.userId]
    );
    res.json(r.rows);
  } catch(e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/watchlist/:propId', async (req, res) => {
  if (!req.session || !req.session.userId) return res.status(401).json({ error: 'Login required' });
  if (!db) return res.status(503).json({ error: 'DB unavailable' });
  try {
    await db.query(
      `INSERT INTO property_watches(user_id, property_id) VALUES($1,$2) ON CONFLICT DO NOTHING`,
      [req.session.userId, parseInt(req.params.propId)]
    );
    res.json({ ok: true });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

app.delete('/api/watchlist/:propId', async (req, res) => {
  if (!req.session || !req.session.userId) return res.status(401).json({ error: 'Login required' });
  if (!db) return res.status(503).json({ error: 'DB unavailable' });
  try {
    await db.query(
      `DELETE FROM property_watches WHERE user_id=$1 AND property_id=$2`,
      [req.session.userId, parseInt(req.params.propId)]
    );
    res.json({ ok: true });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// ── Property overrides API ────────────────────────────────────────────────────
app.get('/api/properties', async (req, res) => {
  try { res.json(await loadProps()); } catch(e) { res.status(500).json({ error: e.message }); }
});

app.get('/api/property/:id', async (req, res) => {
  const id = parseInt(req.params.id, 10);
  try { res.json(await loadProp(id)); } catch(e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/property/:id', requireContributor, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (!id) return res.status(400).json({ error: 'invalid id' });
  try {
    const data = await saveProp(id, req.body, req.session.username);
    res.json({ ok: true, data });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

app.delete('/api/property/:id', requireAdmin, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  try { await deleteProp(id); res.json({ ok: true }); }
  catch(e) { res.status(500).json({ error: e.message }); }
});

// ── Property Names API ────────────────────────────────────────────────────────
app.get('/api/property/:id/names', async (req, res) => {
  const id = parseInt(req.params.id, 10);
  try {
    const r = await db.query(
      `SELECT id, house_name, year_from, year_to, notes FROM property_names WHERE property_id=$1 ORDER BY year_from NULLS LAST, id`,
      [id]
    );
    res.json(r.rows);
  } catch(e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/property/:id/names', requireContributor, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  const { house_name, year_from, year_to, notes } = req.body;
  if (!house_name) return res.status(400).json({ error: 'house_name required' });
  try {
    const r = await db.query(
      `INSERT INTO property_names (property_id, house_name, year_from, year_to, notes) VALUES ($1,$2,$3,$4,$5) RETURNING id`,
      [id, house_name.trim(), year_from||null, year_to||null, notes||null]
    );
    res.json({ ok: true, id: r.rows[0].id });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

app.delete('/api/property/:id/names/:nameId', requireContributor, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  const nameId = parseInt(req.params.nameId, 10);
  try {
    await db.query(`DELETE FROM property_names WHERE id=$1 AND property_id=$2`, [nameId, id]);
    res.json({ ok: true });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// ── Photo API ─────────────────────────────────────────────────────────────────
// Serve uploaded photos
app.use('/data/photos', express.static(PHOTOS_DIR));

// Admin: upload a photo for a property
app.post('/api/property/:id/photo', requireContributor, (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (!id) return res.status(400).json({ error: 'invalid id' });
  const chunks = [];
  req.on('data', c => chunks.push(c));
  req.on('end', async () => {
    try {
      const buf = Buffer.concat(chunks);
      const cd = req.headers['x-filename'] || `photo_${Date.now()}.jpg`;
      const filename = `prop-${id}_${Date.now()}_${cd.replace(/[^a-z0-9._-]/gi, '_')}`;
      const url = await uploadPhoto(buf, filename, req.headers["content-type"]);
      const current = await loadProp(id);
      const photos = [...(current.photos || []), {
        url,
        caption: '',
        addedAt: new Date().toISOString(),
        uploadedBy: req.session.userId || null
      }];
      await saveProp(id, { ...current, photos }, req.session.username);
      res.json({ ok: true, url });
    } catch(e) { res.status(500).json({ error: e.message }); }
  });
  req.on('error', e => res.status(500).json({ error: e.message }));
});

// Upload a video file for a property
app.post('/api/property/:id/video/upload', requireContributor, (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (!id) return res.status(400).json({ error: 'invalid id' });
  const chunks = [];
  let size = 0;
  req.on('data', c => { size += c.length; if (size > 200 * 1024 * 1024) req.destroy(new Error('File too large (max 200MB)')); else chunks.push(c); });
  req.on('end', async () => {
    try {
      const buf = Buffer.concat(chunks);
      if (buf.length < 100) return res.status(400).json({ error: 'Empty file' });
      const origName = (req.headers['x-filename'] || `video_${Date.now()}.mp4`).replace(/[^a-z0-9._-]/gi, '_');
      const filename = `prop-${id}_vid_${Date.now()}_${origName}`;
      const url = await uploadVideo(buf, filename);
      const title = req.headers['x-title'] || origName.replace(/\.[^.]+$/, '').replace(/_/g, ' ');
      const current = await loadProp(id);
      const videos = [...(current.videos || []), { url, title }];
      await saveProp(id, { ...current, videos }, req.session.username);
      res.json({ ok: true, url, title });
    } catch(e) { res.status(500).json({ error: e.message }); }
  });
  req.on('error', e => res.status(500).json({ error: e.message }));
});

// Admin: fetch photo from original site and save locally
app.post('/api/property/:id/fetch-photo', requireAdmin, async (req, res) => {
  const http = require('http');
  const id = parseInt(req.params.id, 10);
  const { pageId, variant } = req.body;
  const num = String(pageId || id).padStart(3, '0');
  const v = variant === 'B' ? 'B' : 'T';
  const url = `http://www.nottinghamparkhouses.co.uk/imagesDB/propertyimages/PIC${num}${v}.jpg`;
  http.get(url, { timeout: 10000 }, (upstream) => {
    if (upstream.statusCode !== 200) return res.json({ ok: false, reason: `HTTP ${upstream.statusCode}` });
    const chunks = [];
    upstream.on('data', c => chunks.push(c));
    upstream.on('end', async () => {
      try {
        const buf = Buffer.concat(chunks);
        if (buf.length < 500) return res.json({ ok: false, reason: 'No image found' });
        const filename = `prop-${id}_orig_${num}${v}.jpg`;
        const photoUrl = await uploadPhoto(buf, filename, req.headers["content-type"]);
        const current = await loadProp(id);
        const photos = current.photos || [];
        if (!photos.find(p => p.url === photoUrl)) {
          photos.push({ url: photoUrl, caption: 'Original site photo', addedAt: new Date().toISOString() });
          await saveProp(id, { ...current, photos }, req.session.username);
        }
        res.json({ ok: true, url: photoUrl });
      } catch(e) { res.json({ ok: false, reason: e.message }); }
    });
  }).on('error', e => res.json({ ok: false, reason: e.message }))
    .on('timeout', () => res.json({ ok: false, reason: 'timeout' }));
});

// Admin or photo owner: delete a photo
app.delete('/api/property/:id/photo', requireContributor, async (req, res) => {
  // authorization handled by requireContributor in the route signature
  const id = parseInt(req.params.id, 10);
  const { url } = req.body;
  try {
    const current = await loadProp(id);
    const photo = (current.photos || []).find(p => p.url === url);
    if (!photo) return res.status(404).json({ error: 'Photo not found' });
    // Only admin or the contributor who uploaded it can delete
    const isOwner = photo.uploadedBy && photo.uploadedBy === req.session.userId;
    if (!req.session.isAdmin && !isOwner) return res.status(403).json({ error: 'Not authorised to delete this photo' });
    current.photos = current.photos.filter(p => p.url !== url);
    await saveProp(id, current, req.session.isAdmin ? 'admin' : 'user:' + req.session.userId);
    try { if (url.startsWith('/data/photos/')) fs.unlinkSync(path.join(PHOTOS_DIR, path.basename(url))); } catch(e) {}
    res.json({ ok: true });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// ── Scrape proxy (admin only) ─────────────────────────────────────────────────
// Lets the browser scraper fetch original site pages through Node (avoids CORS/extension blocks)
app.get('/api/scrape-proxy', requireAdmin, (req, res) => {
  const http = require('http');
  const id = parseInt(req.query.id, 10);
  if (!id || id < 1 || id > 500) return res.status(400).json({ error: 'invalid id' });
  const url = `http://www.nottinghamparkhouses.co.uk/propertypagedetail.asp?pageId=${id}&infoId=${id}&linkid=${id}&id=101&pageName=The+Park+Houses`;
  http.get(url, { timeout: 15000 }, (upstream) => {
    let html = '';
    upstream.setEncoding('utf8');
    upstream.on('data', chunk => html += chunk);
    upstream.on('end', () => res.send(html));
  }).on('error', e => res.status(502).json({ error: e.message }))
    .on('timeout', () => res.status(504).json({ error: 'timeout' }));
});

// ── Submissions API ───────────────────────────────────────────────────────────
// POST /api/property/:id/submission  — requires user login
app.post('/api/property/:id/submission', async (req, res) => {
  if (!req.session.userId && !req.session.isAdmin) return res.status(401).json({ error: 'Must be logged in to submit' });
  const propId = parseInt(req.params.id, 10);
  if (!propId) return res.status(400).json({ error: 'invalid id' });
  try {
    let firstName = 'Admin', lastName = '', profilePhoto = null, userId = null;
    if (req.session.userId) {
      const user = await findUserById(req.session.userId);
      if (!user) return res.status(401).json({ error: 'User not found' });
      req.session.userRole = user.role || 'viewer';
      firstName   = user.first_name;
      lastName    = user.last_name;
      profilePhoto = user.profile_photo || null;
      userId      = user.id;
    }
    const { type, text, photoUrl } = req.body;
    if (!text && !photoUrl) return res.status(400).json({ error: 'text or photoUrl required' });

    const current = await loadProp(propId);
    const submissions = current.submissions || [];
    const entry = {
      id: Date.now(),
      userId,
      firstName,
      lastName,
      profilePhoto,
      type: type || 'Other',
      text: text || '',
      photoUrl: photoUrl || null,
      submittedAt: new Date().toISOString()
    };
    submissions.push(entry);
    await saveProp(propId, { ...current, submissions }, userId ? 'user:' + userId : 'admin');
    res.json({ ok: true, submission: entry });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// Delete a submission (admin or the original submitter)
app.delete('/api/property/:id/submission/:subId', async (req, res) => {
  // authorization handled by requireContributor in the route signature
  const propId = parseInt(req.params.id);
  const subId  = parseInt(req.params.subId);
  try {
    const current = await loadProp(propId);
    const submissions = (current.submissions || []).filter(s => {
      if (s.id === subId) {
        // Allow if admin or the submitter themselves
        return !(req.session.isAdmin || s.userId === req.session.userId);
      }
      return true;
    });
    await saveProp(propId, { ...current, submissions }, req.session.isAdmin ? 'admin' : 'user:' + req.session.userId);
    res.json({ ok: true });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// Upload photo for a submission (returns URL, caller includes in submission)
app.post('/api/property/:id/submission-photo', async (req, res) => {
  // authorization handled by requireContributor in the route signature
  const propId = parseInt(req.params.id, 10);
  const chunks = [];
  req.on('data', c => chunks.push(c));
  req.on('end', async () => {
    try {
      const buf = Buffer.concat(chunks);
      if (buf.length < 100) return res.status(400).json({ error: 'Empty file' });
      const cd = req.headers['x-filename'] || `sub_${Date.now()}.jpg`;
      const filename = `prop-${propId}_sub_${Date.now()}_${cd.replace(/[^a-z0-9._-]/gi,'_')}`;
      const url = await uploadPhoto(buf, filename, req.headers["content-type"]);
      res.json({ ok: true, url });
    } catch(e) { res.status(500).json({ error: e.message }); }
  });
  req.on('error', e => res.status(500).json({ error: e.message }));
});

// ── People API ────────────────────────────────────────────────────────────────

// GET /api/people — list all people, optional ?occupation= ?property= ?q= filters
app.get('/api/people', async (req, res) => {
  if (!db) return res.json([]);
  try {
    const { occupation, property, q } = req.query;
    // Use subqueries to avoid cartesian product of occupations × census_entries
    let query = `
      SELECT p.id, p.first_name, p.last_name, p.known_as, p.maiden_name, p.title, p.postnominals,
             p.born_year, p.born_place, p.died_year, p.died_place,
             p.wikipedia_url, p.photo_url,
             (SELECT ARRAY_AGG(DISTINCT o.occupation) FROM occupations o WHERE o.person_id=p.id AND o.occupation IS NOT NULL) AS occupations,
             (SELECT ARRAY_AGG(DISTINCT pid) FROM (
               SELECT ce.property_id AS pid FROM census_entries ce WHERE ce.person_id=p.id AND ce.property_id IS NOT NULL
               UNION
               SELECT pr.property_id AS pid FROM property_residents pr WHERE pr.person_id=p.id
             ) all_props) AS property_ids,
             (SELECT ARRAY_AGG(DISTINCT ce.census_year) FROM census_entries ce WHERE ce.person_id=p.id AND ce.census_year IS NOT NULL) AS census_years,
             EXISTS(SELECT 1 FROM census_entries ce WHERE ce.person_id=p.id AND ce.property_id IS NULL) AS has_unresolved_census
      FROM people p
    `;
    const params = [];
    const wheres = [];
    if (occupation) {
      params.push(`%${occupation.toLowerCase()}%`);
      wheres.push(`EXISTS (SELECT 1 FROM occupations ox WHERE ox.person_id=p.id AND LOWER(ox.occupation) LIKE $${params.length})`);
    }
    if (property) {
      params.push(parseInt(property));
      wheres.push(`(
        EXISTS (SELECT 1 FROM census_entries cx WHERE cx.person_id=p.id AND cx.property_id=$${params.length})
        OR EXISTS (SELECT 1 FROM property_residents rx WHERE rx.person_id=p.id AND rx.property_id=$${params.length})
      )`);
    }
    if (q) {
      params.push(`%${q.toLowerCase()}%`);
      wheres.push(`(LOWER(p.first_name) LIKE $${params.length} OR LOWER(p.last_name) LIKE $${params.length} OR LOWER(COALESCE(p.known_as,'')) LIKE $${params.length} OR LOWER(p.first_name || ' ' || COALESCE(p.last_name,'')) LIKE $${params.length})`);
    }
    if (wheres.length) query += ' WHERE ' + wheres.join(' AND ');
    query += ' ORDER BY p.last_name, p.first_name';
    const r = await db.query(query, params);
    const rows = r.rows.map(row => ({
      ...row,
      property_names: (row.property_ids || []).map(id => propName(id))
    }));
    res.json(rows);
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// GET /api/person/:id — full profile
app.get('/api/person/:id', async (req, res) => {
  if (!db) return res.json(null);
  try {
    const id = parseInt(req.params.id);
    const [pRes, occRes, censusRes, relRes, placesRes, bibRes] = await Promise.all([
      db.query('SELECT * FROM people WHERE id=$1', [id]),
      db.query('SELECT * FROM occupations WHERE person_id=$1 ORDER BY from_year', [id]),
      db.query(`SELECT ce.* FROM census_entries ce WHERE ce.person_id=$1 ORDER BY ce.census_year`, [id]),
      db.query(`SELECT pr.*,
                pa.id as pid, pa.first_name as a_first, pa.last_name as a_last, pa.known_as as a_known,
                pb.id as bid, pb.first_name as b_first, pb.last_name as b_last, pb.known_as as b_known
                FROM people_relationships pr
                JOIN people pa ON pa.id=pr.person_a_id
                JOIN people pb ON pb.id=pr.person_b_id
                WHERE pr.person_a_id=$1 OR pr.person_b_id=$1`, [id]),
      db.query(`SELECT pp.connection, sp.*
                FROM people_places pp JOIN significant_places sp ON sp.id=pp.place_id
                WHERE pp.person_id=$1`, [id]),
      db.query('SELECT b.*, p.first_name, p.last_name FROM bibliography b LEFT JOIN people p ON p.id=b.author_person_id WHERE b.author_person_id=$1 ORDER BY b.year', [id])
    ]);
    if (!pRes.rows[0]) return res.status(404).json({ error: 'Person not found' });
    const person = pRes.rows[0];
    person.occupations = occRes.rows;
    person.census_entries = censusRes.rows.map(ce => ({
      ...ce, property_name: propName(ce.property_id)
    }));
    person.relationships = relRes.rows;
    person.places = placesRes.rows;
    person.bibliography = bibRes.rows;
    res.json(person);
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// GET /api/occupations — list all unique occupation strings (for filter dropdowns)
app.get('/api/occupations', async (req, res) => {
  if (!db) return res.json([]);
  try {
    // The count has to mean "people you will get if you pick this", so it must
    // match the filter, which is a substring test — picking "author" also
    // returns "Author (Bacon-Shakespeare controversy)". Counting rows grouped by
    // exact label said 4 where the filter returned 5. Distinct people, too: one
    // person can hold the same occupation over several date ranges.
    const r = await db.query(`
      SELECT labels.occupation,
             (SELECT COUNT(DISTINCT ox.person_id) FROM occupations ox
               WHERE LOWER(ox.occupation) LIKE '%' || labels.occupation || '%') AS count
      FROM (SELECT DISTINCT LOWER(occupation) AS occupation FROM occupations
             WHERE occupation IS NOT NULL AND TRIM(occupation) <> '') labels
      ORDER BY count DESC, labels.occupation`);
    res.json(r.rows);
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// NOTE: /api/census/unresolved and /api/census/resolve/:id MUST be registered BEFORE
// /api/census/:year, otherwise Express matches "unresolved" as the :year param.

// GET /api/census/unresolved — people saved with no matched property
app.get('/api/census/unresolved', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });

  // Two separate queries — avoids JOIN issues with node-postgres
  let ceRows;
  try {
    ceRows = (await db.query(`
      SELECT id, census_year, unresolved_address, relationship,
             age_at_census, occupation_at_census, source, person_id,
             census_house_id, census_household_num
      FROM census_entries
      WHERE property_id IS NULL AND person_id IS NOT NULL
      ORDER BY census_year, census_house_id NULLS LAST, census_household_num NULLS LAST, unresolved_address
    `)).rows;
  } catch(e) { return res.status(500).json({ error: e.message }); }

  if (!ceRows.length) return res.json([]);

  const personIds = [...new Set(ceRows.map(r => r.person_id).filter(id => Number.isInteger(id)))];

  let peopleRows;
  try {
    peopleRows = (await db.query(
      `SELECT id, first_name, last_name, known_as FROM people WHERE id = ANY($1)`,
      [personIds]
    )).rows;
  } catch(e) { return res.status(500).json({ error: e.message }); }

  const peopleMap = {};
  peopleRows.forEach(p => { peopleMap[p.id] = p; });

  const grouped = {};
  ceRows.forEach(ce => {
    const p = peopleMap[ce.person_id];
    if (!p) return;

    let key, displayAddress;
    if (ce.census_year === 1911 && ce.census_house_id) {
      // 1911: group by House ID (PD1, PeD1, etc.)
      key = `hid:${ce.census_house_id}|${ce.census_year}`;
      // Extract trailing number from house_id (PD1→1, PeD2→2)
      const hhNum = (ce.census_house_id.match(/(\d+)$/) || [,''])[1] || ce.census_house_id;
      // Strip leading code prefix from unresolved_address (e.g. "PD1 Park Drive" → "Park Drive")
      const street1911 = (ce.unresolved_address || '').replace(/^[A-Za-z]+\d+\s*/,'').trim()
                       || ce.unresolved_address || ce.census_house_id;
      displayAddress = `Household ${hhNum} — ${street1911}`;
    } else if (ce.census_year === 1921 && ce.census_household_num != null) {
      // 1921: group by street (strip leading number) + household number
      const street = (ce.unresolved_address || '').replace(/^\d+\s+/i, '');
      key = `${street.toLowerCase()}|hh:${ce.census_household_num}|${ce.census_year}`;
      displayAddress = `Household ${ce.census_household_num} — ${street}`;
    } else {
      // Fallback: existing behaviour (group by full unresolved_address + year)
      key = (ce.unresolved_address || '') + '|' + ce.census_year;
      displayAddress = ce.unresolved_address;
    }

    if (!grouped[key]) grouped[key] = {
      address: displayAddress,
      year: ce.census_year,
      house_id: ce.census_house_id,
      household_num: ce.census_household_num,
      people: []
    };
    grouped[key].people.push({
      entry_id: ce.id, person_id: ce.person_id,
      name: p.known_as || (p.first_name + ' ' + p.last_name),
      relationship: ce.relationship, age: ce.age_at_census,
      occupation: ce.occupation_at_census, source: ce.source
    });
  });
  // Sort people within each group: Head first, then by relationship, then by name
  const relOrder = ['head','wife','husband','son','daughter','brother','sister','visitor','boarder','lodger','servant','cook'];
  Object.values(grouped).forEach(g =>
    g.people.sort((a, b) => {
      const ra = relOrder.indexOf((a.relationship||'').toLowerCase());
      const rb = relOrder.indexOf((b.relationship||'').toLowerCase());
      if (ra !== rb) return (ra < 0 ? 99 : ra) - (rb < 0 ? 99 : rb);
      return (a.name||'').localeCompare(b.name||'');
    })
  );
  res.json(Object.values(grouped));
});

// POST /api/census/resolve/:id — assign an unresolved census entry to a property
app.post('/api/census/resolve/:id', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  try {
    const entryId = parseInt(req.params.id);
    const { property_id } = req.body;
    if (!property_id) return res.status(400).json({ error: 'property_id required' });
    await db.query(
      `UPDATE census_entries SET property_id=$1, unresolved_address=NULL WHERE id=$2 AND property_id IS NULL`,
      [property_id, entryId]
    );
    res.json({ ok: true });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// GET /api/census/:year — all people recorded at a census year, optionally ?property=
app.get('/api/census/:year', async (req, res, next) => {
  // ":year" happily swallows any word, so /api/census/crowding arrived here and
  // was parsed as a year, giving a Postgres error instead of the route that
  // actually exists further down. Anything that is not a year is not ours.
  if (!/^\d{4}$/.test(String(req.params.year))) return next();
  if (!db) return res.json([]);
  try {
    const year = parseInt(req.params.year);
    const propId = req.query.property ? parseInt(req.query.property) : null;
    let query = `SELECT ce.*, p.first_name, p.last_name, p.known_as, p.wikipedia_url
                 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                 WHERE ce.census_year=$1`;
    const params = [year];
    if (propId) { params.push(propId); query += ` AND ce.property_id=$${params.length}`; }
    // Entry id is import order, which is the enumerator's own order: each schedule
    // runs head, family, servants, then the next house. Ordering by relationship
    // sorted that into "all the daughters, all the servants" and lost the household
    // boundaries — the one thing that makes a crowded address readable.
    query += ' ORDER BY ce.property_id, ce.id';
    const r = await db.query(query, params);
    res.json(r.rows);
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// ── Property Residents API ────────────────────────────────────────────────────
// GET /api/property/:id/residents
app.get('/api/property/:id/residents', async (req, res) => {
  if (!db) return res.json([]);
  try {
    const r = await db.query(`
      SELECT pr.id, pr.property_id, pr.person_id, pr.from_year, pr.to_year, pr.notes,
             p.first_name, p.last_name, p.known_as, p.born_year, p.died_year, p.born_date, p.died_date
      FROM property_residents pr
      JOIN people p ON p.id = pr.person_id
      WHERE pr.property_id = $1
      ORDER BY pr.from_year NULLS LAST, p.last_name
    `, [parseInt(req.params.id)]);
    res.json(r.rows);
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// POST /api/property/:id/residents
app.post('/api/property/:id/residents', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  try {
    const propId = parseInt(req.params.id);
    const { person_id, from_year, to_year, notes } = req.body;
    if (!person_id) return res.status(400).json({ error: 'person_id required' });
    // Prevent duplicates
    const exists = await db.query('SELECT id FROM property_residents WHERE property_id=$1 AND person_id=$2', [propId, person_id]);
    if (exists.rows.length) return res.status(409).json({ error: 'This person is already linked to this property' });
    const r = await db.query(
      `INSERT INTO property_residents (property_id, person_id, from_year, to_year, notes)
       VALUES ($1,$2,$3,$4,$5) RETURNING id`,
      [propId, person_id, from_year||null, to_year||null, notes||null]
    );
    await logChange('property', propId, req, 'add_resident', 'person_id', null, person_id);
    res.json({ ok: true, id: r.rows[0].id });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// PATCH /api/property/:propId/residents/:residentId
app.patch('/api/property/:propId/residents/:residentId', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  try {
    const { from_year, to_year, notes } = req.body;
    await db.query(
      `UPDATE property_residents SET from_year=$1, to_year=$2, notes=$3 WHERE id=$4 AND property_id=$5`,
      [from_year||null, to_year||null, notes||null, parseInt(req.params.residentId), parseInt(req.params.propId)]
    );
    res.json({ ok: true });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// GET /api/admin/occupations-export
app.get('/api/admin/occupations-export', async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  try {
    const [occ, census] = await Promise.all([
      db.query(`SELECT occupation, COUNT(*) as count FROM occupations WHERE occupation IS NOT NULL AND TRIM(occupation)!='' GROUP BY occupation ORDER BY count DESC, occupation`),
      db.query(`SELECT occupation_at_census as occupation, COUNT(*) as count FROM census_entries WHERE occupation_at_census IS NOT NULL AND TRIM(occupation_at_census)!='' GROUP BY occupation_at_census ORDER BY count DESC, occupation_at_census`)
    ]);
    res.json({ occupations: occ.rows, censusOccupations: census.rows });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// DELETE /api/property/:propId/residents/:residentId
app.delete('/api/property/:propId/residents/:residentId', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  try {
    await db.query('DELETE FROM property_residents WHERE id=$1 AND property_id=$2', [parseInt(req.params.residentId), parseInt(req.params.propId)]);
    res.json({ ok: true });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// ── Geocoding ─────────────────────────────────────────────────────────────────
async function geocodePlace(placeText, searchText) {
  // placeText = the key stored in census_entries (original as-imported)
  // searchText = what to actually search (corrected version, or same as placeText)
  if (!db) return null;
  const key = process.env.GOOGLE_MAPS_KEY;
  if (!key) { console.warn('geocodePlace: no GOOGLE_MAPS_KEY'); return null; }
  const query = (searchText || placeText || '').trim();
  if (!query) return null;
  try {
    const url = `https://maps.googleapis.com/maps/api/geocode/json?address=${encodeURIComponent(query)}&key=${key}`;
    const resp = await fetch(url);
    const json = await resp.json();
    if (json.status === 'OK' && json.results[0]) {
      const loc = json.results[0].geometry.location;
      const formatted = json.results[0].formatted_address;
      await db.query(
        `INSERT INTO geocode_cache (place_text, lat, lng, formatted_address, status, corrected_from)
         VALUES ($1,$2,$3,$4,'found',$5)
         ON CONFLICT (place_text) DO UPDATE
           SET lat=$2, lng=$3, formatted_address=$4, status='found',
               corrected_from=$5, queried_at=NOW()`,
        [placeText.trim(), loc.lat, loc.lng, formatted,
         searchText && searchText !== placeText ? placeText.trim() : null]
      );
      return { lat: loc.lat, lng: loc.lng, formatted_address: formatted };
    } else {
      await db.query(
        `INSERT INTO geocode_cache (place_text, status) VALUES ($1,'not_found')
         ON CONFLICT (place_text) DO UPDATE SET status='not_found', queried_at=NOW()`,
        [placeText.trim()]
      );
      return null;
    }
  } catch(e) {
    console.error('geocodePlace error:', e.message);
    return null;
  }
}

// Geocode an array of unique place strings (skip already cached), fire-and-forget
async function geocodePlacesBatch(places) {
  for (const p of places) {
    const existing = await db.query(
      `SELECT status FROM geocode_cache WHERE place_text=$1`, [p.trim()]
    ).catch(()=>({rows:[]}));
    if (existing.rows[0]) continue; // already attempted
    await geocodePlace(p, p);
    await new Promise(r => setTimeout(r, 200)); // stay under rate limit
  }
}

// A spreadsheet's own column headings sometimes survive a copy-paste and arrive
// looking like a person. No resident is called "Last name", so treat an exact
// match on a heading as the header row it is.
const COLUMN_HEADINGS = new Set([
  'last name', 'lastname', 'first name', 'first names', 'firstname', 'forename',
  'forenames', 'given name', 'given names', 'surname', 'name', 'full name',
  'age', 'sex', 'gender', 'relation', 'relationship', 'occupation',
  'birth place', 'birthplace', 'place of birth', 'where born', 'year',
]);
const looksLikeHeading = v => COLUMN_HEADINGS.has(
  String(v || '').toLowerCase().replace(/\(s\)/g, 's').replace(/[^a-z\s]/g, '').replace(/\s+/g, ' ').trim()
);

// POST /api/people/duplicates/dismiss — two people of the same name who really
// are two people. Sending dismissed:false puts the pair back in the list.
app.post('/api/people/duplicates/dismiss', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  const a = parseInt(req.body && req.body.person_a_id, 10);
  const b = parseInt(req.body && req.body.person_b_id, 10);
  const on = !(req.body && req.body.dismissed === false);
  if (!Number.isInteger(a) || !Number.isInteger(b) || a === b) {
    return res.status(400).json({ error: 'two different person ids are required' });
  }
  const lo = Math.min(a, b), hi = Math.max(a, b);
  const who = (req.session && (req.session.username || req.session.researchKey)) || null;
  try {
    if (!on) {
      await db.query(`DELETE FROM duplicate_dismissed WHERE person_a_id=$1 AND person_b_id=$2`,
        [lo, hi]);
      return res.json({ ok: true, dismissed: false });
    }
    await db.query(
      `INSERT INTO duplicate_dismissed (person_a_id, person_b_id, note, dismissed_by)
            VALUES ($1,$2,$3,$4)
       ON CONFLICT (person_a_id, person_b_id)
       DO UPDATE SET note=EXCLUDED.note, dismissed_by=EXCLUDED.dismissed_by, dismissed_at=NOW()`,
      [lo, hi, (req.body && req.body.note) || null, who]);
    res.json({ ok: true, dismissed: true });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// ── The archive ───────────────────────────────────────────────────────────────
// Things about the estate itself, which had nowhere to live: a person could hold
// photographs and documents, and a property could, but the place as a whole
// could not.
app.get('/api/archive', async (req, res) => {
  if (!db) return res.json([]);
  try {
    const r = await db.query(
      `SELECT id, title, description, url, filename, kind, dated, credit, source, created_at
         FROM archive_documents ORDER BY created_at DESC`);
    res.json(r.rows);
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/archive', requireContributor, (req, res) => {
  multer({ storage: multer.memoryStorage(), limits: { fileSize: 40 * 1024 * 1024 } })
    .single('file')(req, res, async (err) => {
    if (err) return res.status(400).json({ error: err.message });
    if (!db) return res.status(503).json({ error: 'DB not available' });
    if (!req.file) return res.status(400).json({ error: 'No file' });
    const title = (req.body.title || '').trim();
    if (!title) return res.status(400).json({ error: 'A title is required' });
    const stamped = `archive-${Date.now()}-${(req.file.originalname || 'file')
      .replace(/[^a-z0-9._-]/gi, '_')}`;
    let url;
    try { url = await uploadMedia(req.file.buffer, stamped, req.file.mimetype); }
    catch (e) { return res.status(500).json({ error: 'Upload failed: ' + e.message }); }
    const who = (req.session && (req.session.username || req.session.researchKey)) || null;
    try {
      const r = await db.query(
        `INSERT INTO archive_documents (title, description, url, filename, kind, dated,
                                        credit, source, added_by)
              VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) RETURNING *`,
        [title, req.body.description || null, url, req.file.originalname || null,
         req.body.kind || null, req.body.dated || null, req.body.credit || null,
         req.body.source || null, who]);
      res.json({ ok: true, document: r.rows[0] });
    } catch (e) { res.status(500).json({ error: e.message }); }
  });
});

app.patch('/api/archive/:id', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  const fields = ['title', 'description', 'kind', 'dated', 'credit', 'source'];
  const given = fields.filter(f => req.body[f] !== undefined);
  if (!given.length) return res.status(400).json({ error: 'nothing to change' });
  try {
    await db.query(
      `UPDATE archive_documents SET ${given.map((f, i) => `${f}=$${i + 2}`).join(', ')} WHERE id=$1`,
      [parseInt(req.params.id, 10), ...given.map(f => req.body[f] || null)]);
    res.json({ ok: true });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.delete('/api/archive/:id', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  try {
    await db.query(`DELETE FROM archive_documents WHERE id=$1`, [parseInt(req.params.id, 10)]);
    res.json({ ok: true });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// GET /api/people/duplicates — the same person imported twice. The 1911 and
// 1921 spreadsheets were loaded separately and name people differently: one
// holds "Helena Brownsword Dowson", the other "Helena Dowson". They match on
// surname and first forename with birth years within two, and crucially appear
// in no census year together — two records of one person, not two people.
app.get('/api/people/duplicates', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  try {
    const r = await db.query(`
      SELECT p.id, p.first_name, p.last_name, p.born_year, p.died_year, p.sex,
             p.wikipedia_url, p.photo_url, p.bio IS NOT NULL AS has_bio,
             ARRAY(SELECT DISTINCT c.census_year FROM census_entries c
                    WHERE c.person_id = p.id AND c.census_year IS NOT NULL
                    ORDER BY 1) AS years,
             (SELECT COUNT(*) FROM census_entries c WHERE c.person_id = p.id) AS entries,
             ARRAY(SELECT DISTINCT c.property_id FROM census_entries c
                    WHERE c.person_id = p.id AND c.property_id IS NOT NULL) AS props
        FROM people p
       WHERE COALESCE(TRIM(p.last_name), '') <> ''
         AND COALESCE(TRIM(p.first_name), '') <> ''`);

    const key = v => String(v || '').toLowerCase().replace(/[^a-z]/g, '');
    // An enumerator writes "Geo. Hy. Parr" where the record holds George Henry
    // Parr, and letter-for-letter those are two different men — which is how a
    // transcription made straight off the page came to enter eleven people the
    // record already had, none of them visible here. Expanding the short forms
    // first puts both spellings in the same bucket.
    const firstWord = v => expandForename(key(String(v || '').trim().split(/\s+/)[0]));
    // How common a name is changes what a coincidence means. Two Hanishes born
    // the same year are almost certainly one person; two Smiths may well be two.
    const surnameCount = new Map(), forenameCount = new Map();
    for (const p of r.rows) {
      const sn = key(p.last_name), fn = firstWord(p.first_name);
      surnameCount.set(sn, (surnameCount.get(sn) || 0) + 1);
      forenameCount.set(fn, (forenameCount.get(fn) || 0) + 1);
    }
    const buckets = new Map();
    for (const p of r.rows) {
      const k = key(p.last_name) + '|' + firstWord(p.first_name);
      if (!k.includes('|') || k.startsWith('|') || k.endsWith('|')) continue;
      if (!buckets.has(k)) buckets.set(k, []);
      buckets.get(k).push(p);
    }

    const dismissedRows = (await db.query(
      `SELECT person_a_id, person_b_id, note FROM duplicate_dismissed`)).rows;
    const dismissedKey = new Set(dismissedRows.map(d => `${d.person_a_id}:${d.person_b_id}`));
    const showDismissed = req.query.dismissed === '1';

    const pairs = [];
    for (const list of buckets.values()) {
      if (list.length < 2) continue;
      for (let i = 0; i < list.length; i++) {
        for (let j = i + 1; j < list.length; j++) {
          const a = list[i], b = list[j];
          if (!a.born_year || !b.born_year) continue;
          if (Math.abs(a.born_year - b.born_year) > 2) continue;
          const ya = new Set(a.years), yb = new Set(b.years);
          const overlap = [...ya].filter(y => yb.has(y));
          // Sharing a census year usually means two real people of one name. But
          // nobody is in two households in the same year, so an exact birth year
          // and no property in common is one person entered twice — which is how
          // Arthur Oscar Hanish came to be a boarder in two houses in 1921.
          const sn = key(a.last_name), fn = firstWord(a.first_name);
          const share = surnameCount.get(sn) || 1;
          const shareFore = forenameCount.get(fn) || 1;
          // A common name makes the coincidence ordinary. Two Smiths in one year
          // at two addresses is unremarkable; two Hanishes is not.
          const commonName = share >= 8 || (share >= 4 && shareFore >= 25);
          const sharedProp = a.props.some(x => b.props.includes(x));
          const sameYearTwice = overlap.length > 0
            && a.born_year === b.born_year
            && !sharedProp
            && !commonName;
          // The same household imported twice, from two transcriptions of one
          // page: one person entered as "Ada Jessop" and again as "Ada Mary
          // Jessop", same house, same year, same birth year. The rule here used
          // to skip exactly this — sharing a house and a year was read as proof
          // of two real people — which made a double-imported household the one
          // kind of duplicate the page could never see.
          // Deliberately not guarded by commonName. That guard is for the case
          // below, where two people of one name sit in different houses and a
          // common name makes the coincidence ordinary. Here they are in the
          // same house on the same night with the same birth year, and no
          // household holds two people of one forename and surname born the
          // same year — least of all a large family, which is exactly what a
          // common surname means. Fourteen Jessops is why the page could not
          // see the five Jessop duplicates.
          const doubleImport = overlap.length > 0
            && sharedProp
            && Math.abs(a.born_year - b.born_year) <= 1;
          if (overlap.length && !sameYearTwice && !doubleImport) continue;
          const reasons = [];
          if (sameYearTwice) {
            reasons.push(`in two households in ${overlap.join(' and ')} — nobody can be`);
          }
          if (doubleImport) {
            reasons.push(`both in the same house in ${overlap.join(' and ')} — one household entered twice`);
          }
          reasons.push(share === 1
            ? 'the only one of that surname'
            : `${share} people share the surname`);
          if (a.born_year === b.born_year) reasons.push('same birth year');
          else reasons.push(`birth years ${a.born_year} and ${b.born_year}`);
          if (sharedProp) reasons.push('same property');
          if (key(a.first_name) !== key(b.first_name)) reasons.push('one name fuller than the other');
          // Prefer keeping the record with more on it.
          const weight = p => (p.years.length * 4) + Number(p.entries)
            + (p.wikipedia_url ? 3 : 0) + (p.photo_url ? 3 : 0) + (p.has_bio ? 3 : 0)
            + (String(p.first_name).trim().split(/\s+/).length > 1 ? 1 : 0);
          const [keep, drop] = weight(a) >= weight(b) ? [a, b] : [b, a];
          const lo = Math.min(a.id, b.id), hi = Math.max(a.id, b.id);
          const isDismissed = dismissedKey.has(`${lo}:${hi}`);
          if (isDismissed && !showDismissed) continue;
          pairs.push({
            sameYearTwice, doubleImport, surnameShared: share, forenameShared: shareFore,
            commonName,
            dismissed: isDismissed,
            note: isDismissed
              ? (dismissedRows.find(d => d.person_a_id === lo && d.person_b_id === hi) || {}).note || null
              : null,
            suggestKeep: keep.id, suggestDrop: drop.id,
            sharedProperty: sharedProp, reasons,
            people: [a, b].map(p => ({
              id: p.id, name: [p.first_name, p.last_name].filter(Boolean).join(' '),
              born_year: p.born_year, died_year: p.died_year, sex: p.sex,
              years: p.years, entries: Number(p.entries), properties: p.props,
              wikipedia_url: p.wikipedia_url, has_photo: !!p.photo_url, has_bio: p.has_bio,
            })),
          });
        }
      }
    }
    pairs.sort((x, y) => (y.sameYearTwice - x.sameYearTwice)
                      || (y.sharedProperty - x.sharedProperty)
                      || (x.surnameShared - y.surnameShared)
                      || x.people[0].name.localeCompare(y.people[0].name));
    res.json({ total: pairs.length, dismissedCount: dismissedRows.length, pairs });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// GET /api/census/unfiled-groups — records filed against no property, gathered
// by the address they carry. 238 records turn out to be 22 distinct addresses,
// so this is 22 decisions rather than 238. Suggestions are offered, never
// applied: a house name in the text is a strong hint, a street alone is not.
const STREET_WORDS = { rd:'road', st:'street', dr:'drive', cres:'crescent', ave:'avenue',
  e:'east', w:'west', n:'north', s:'south', sq:'square', ter:'terrace', ln:'lane' };
const addrNorm = v => String(v || '').toLowerCase().replace(/[^a-z0-9 ]/g, ' ')
  .split(/\s+/).filter(Boolean).map(w => STREET_WORDS[w] || w).join(' ');

app.get('/api/census/unfiled-groups', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  try {
    const r = await db.query(`
      SELECT c.id, c.census_year, c.unresolved_address, c.relationship, c.person_id,
             p.first_name, p.last_name
        FROM census_entries c JOIN people p ON p.id = c.person_id
       WHERE c.property_id IS NULL
       ORDER BY c.id`);

    let props = [];
    try { props = JSON.parse(readAllPropsCached().body); } catch (e) { props = []; }
    if (!Array.isArray(props)) props = [];
    const suggest = (addr) => {
      const a = addrNorm(addr);
      if (!a) return [];
      const out = [];
      for (const pr of props) {
        const st = addrNorm(pr.street);
        const no = String(pr.no || '').trim();
        // Every name the house is known by, not just its current one. Kenmare
        // House is recorded in the census as Kenmore; without the former names
        // it could never be suggested.
        const names = [pr.name, pr.house_name, ...String(pr.prev_house_name || '').split('\n')]
          .map(addrNorm).filter(n => n && n.length > 3);
        let score = 0, why = [];
        const hit = names.find(n => a.includes(n));
        if (hit) {
          score += 10;
          why.push(addrNorm(pr.name) === hit || addrNorm(pr.house_name) === hit
                   ? 'house name' : 'former name');
        }
        if (st && a.includes(st)) { score += 4; why.push('street'); }
        // House codes like "PeD1" or "SR1" carry the number after the letters.
        const m = a.match(/^[a-z]{0,4}(\d+)\b/);
        if (m && no && m[1] === no) { score += 5; why.push('number'); }
        if (score >= 4) out.push({ id: pr.id, label: pr.address || pr.name || pr.street,
                                   street: pr.street, score, why: why.join(' + ') });
      }
      out.sort((x, y) => y.score - x.score || x.id - y.id);
      return out.slice(0, 6);
    };

    const byAddr = new Map();
    for (const e of r.rows) {
      const key = (e.unresolved_address || '').trim() || '\u0000none';
      if (!byAddr.has(key)) byAddr.set(key, []);
      byAddr.get(key).push(e);
    }
    const aside = new Map((await db.query(
      `SELECT entry_id, note, set_by FROM census_set_aside`)).rows
        .map(r => [r.entry_id, r]));

    const groups = [...byAddr.entries()].map(([addr, entries]) => {
      const s = addr === '\u0000none' ? [] : suggest(addr);
      // One address string can hold several households — the Dowsons and two
      // neighbours all arrived under "Felixstowe see 1911 Clumber rd W". A
      // house name in the text then evidences one of them, not all of them, so
      // a group carrying more than one household is never called confident.
      // Counted within each census year. One family recorded in 1901 and again
      // in 1911 has two heads in the group and is still one household — the
      // Jardines were flagged as "2 households" for exactly that reason, and
      // told not to file, when all twenty records are one family in two years.
      const perYear = new Map();
      for (const e of entries) {
        const y = e.census_year || 0;
        if (!perYear.has(y)) perYear.set(y, { heads: 0, wives: 0 });
        const t = perYear.get(y), rel = (e.relationship || '').trim();
        // Some imports put the schedule number in the relationship column, so a
        // household head arrives as a bare "1" rather than "Head". Three of the
        // six households under "Cavendish Crescent North" are marked that way,
        // and without this the group reported two households instead of six.
        if (/^head$/i.test(rel) || /^\d+$/.test(rel)) t.heads++;
        if (/^wife$/i.test(rel)) t.wives++;
      }
      const households = Math.max(1,
        ...[...perYear.values()].map(t => Math.max(t.heads, t.wives)));
      const strong = s.length && s[0].score >= 10
                     && (s.length === 1 || s[0].score > s[1].score)
                     && households === 1;
      const asideCount = entries.filter(e => aside.has(e.id)).length;
      return {
        address: addr === '\u0000none' ? null : addr,
        count: entries.length,
        households,
        asideCount,
        setAside: asideCount === entries.length && entries.length > 0,
        setAsideBy: (aside.get((entries.find(e => aside.has(e.id)) || {}).id) || {}).set_by || null,
        years: [...new Set(entries.map(e => e.census_year))].sort(),
        suggestions: s,
        confident: !!strong,
        entries: entries.map(e => ({
          id: e.id, person_id: e.person_id, year: e.census_year,
          name: [e.first_name, e.last_name].filter(Boolean).join(' '),
          relationship: e.relationship,
          setAside: aside.has(e.id),
        })),
      };
    }).sort((a, b) => b.count - a.count);

    res.json({ total: r.rows.length, groups });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// POST /api/census/crowding/confirm — this house really did hold that many.
// Sending confirmed:false takes it back into the list.
app.post('/api/census/crowding/confirm', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  const propertyId = parseInt(req.body && req.body.property_id, 10);
  const year = parseInt(req.body && req.body.census_year, 10);
  const on = !(req.body && req.body.confirmed === false);
  if (!Number.isInteger(propertyId) || !Number.isInteger(year)) {
    return res.status(400).json({ error: 'property_id and census_year are required' });
  }
  const who = (req.session && (req.session.username || req.session.researchKey)) || null;
  try {
    if (!on) {
      await db.query(`DELETE FROM crowding_reviewed WHERE property_id=$1 AND census_year=$2`,
        [propertyId, year]);
      return res.json({ ok: true, confirmed: false });
    }
    await db.query(
      `INSERT INTO crowding_reviewed (property_id, census_year, note, reviewed_by)
            VALUES ($1,$2,$3,$4)
       ON CONFLICT (property_id, census_year)
       DO UPDATE SET note=EXCLUDED.note, reviewed_by=EXCLUDED.reviewed_by, reviewed_at=NOW()`,
      [propertyId, year, (req.body && req.body.note) || null, who]);
    res.json({ ok: true, confirmed: true });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// POST /api/census/reassign — send each census record to the property named
// against it. One address holding several households is untangled a line at a
// time, which no single "move everyone" action can do.
// An address the census cannot resolve — no house name, no number on the
// return — is set aside rather than left in the queue. Nothing is moved or
// deleted; the records stay exactly where they are and stay searchable.
app.post('/api/census/unfiled-groups/set-aside', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  const ids = Array.isArray(req.body && req.body.entryIds)
    ? req.body.entryIds.map(n => parseInt(n, 10)).filter(Number.isInteger) : [];
  if (!ids.length) return res.status(400).json({ error: 'no records given' });
  if (ids.length > 2000) return res.status(400).json({ error: 'too many at once' });
  const on = !(req.body && req.body.on === false);
  const who = (await getResearchKey(req.session)) || null;
  try {
    if (!on) {
      await db.query(`DELETE FROM census_set_aside WHERE entry_id = ANY($1::int[])`, [ids]);
      return res.json({ ok: true, setAside: false, count: ids.length });
    }
    await db.query(
      `INSERT INTO census_set_aside (entry_id, note, set_by)
       SELECT id, $2, $3 FROM unnest($1::int[]) AS t(id)
       ON CONFLICT (entry_id) DO UPDATE SET note=EXCLUDED.note, set_by=EXCLUDED.set_by, set_at=NOW()`,
      [ids, (req.body && req.body.note) || null, who]);
    res.json({ ok: true, setAside: true, count: ids.length });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// Change the address an unfiled group sits under, or take it off. The label is
// only ever a guess from a transcription — "Felixstowe see 1911 Clumber Rd W" for
// a household nobody can place at Felixstowe — and a wrong one keeps suggesting a
// house. Only unfiled records are touched; a filed record has no label to change.
app.post('/api/census/unfiled-groups/relabel', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  const ids = Array.isArray(req.body && req.body.entryIds)
    ? req.body.entryIds.map(n => parseInt(n, 10)).filter(Number.isInteger) : [];
  if (!ids.length) return res.status(400).json({ error: 'no records given' });
  if (ids.length > 2000) return res.status(400).json({ error: 'too many at once' });
  const label = String((req.body && req.body.address) || '').trim() || null;
  try {
    const r = await db.query(
      `UPDATE census_entries SET unresolved_address = $2
        WHERE id = ANY($1::int[]) AND property_id IS NULL`, [ids, label]);
    res.json({ ok: true, changed: r.rowCount, address: label });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/census/reassign', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  const moves = Array.isArray(req.body && req.body.moves) ? req.body.moves : null;
  if (!moves || !moves.length) return res.status(400).json({ error: 'no moves given' });
  if (moves.length > 500) return res.status(400).json({ error: 'too many at once' });
  try {
    let filed = 0, unfiled = 0;
    for (const m of moves) {
      const entryId = parseInt(m && m.entryId, 10);
      if (!Number.isInteger(entryId)) continue;
      const raw = m.propertyId;
      const target = (raw === null || raw === undefined || raw === '') ? null : parseInt(raw, 10);
      if (target !== null && !Number.isInteger(target)) {
        return res.status(400).json({ error: `"${raw}" is not a property number` });
      }
      // Unfiling a household that came out of a misfiled address leaves it with
      // no address at all, which drops it into the "no address recorded" heap on
      // the unfiled page — the least useful place in the record. A move may
      // carry the address off the schedule instead, so the group arrives named.
      const addr = target === null && typeof m.address === 'string' && m.address.trim()
        ? m.address.trim() : null;
      await db.query(
        `UPDATE census_entries
            SET property_id = $1,
                unresolved_address = CASE
                  WHEN $1::int IS NOT NULL THEN NULL
                  WHEN $3::text IS NOT NULL THEN $3
                  ELSE unresolved_address END
          WHERE id = $2`, [target, entryId, addr]);
      if (target === null) unfiled++; else filed++;
      // Keep the resident link in step with where the record now sits.
      if (target !== null) {
        const person = await db.query(`SELECT person_id FROM census_entries WHERE id=$1`, [entryId]);
        const pid = person.rows[0] && person.rows[0].person_id;
        if (pid) {
          const dup = await db.query(
            `SELECT 1 FROM property_residents WHERE person_id=$1 AND property_id=$2`, [pid, target]);
          if (!dup.rows.length) {
            await db.query(`INSERT INTO property_residents (person_id, property_id) VALUES ($1,$2)`,
              [pid, target]);
          }
        }
      }
    }
    res.json({ ok: true, filed, unfiled });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// POST /api/admin/recover-source-column — a slipped column put "Married, Male"
// and the like into `source`, where the provenance should be. Both halves are
// real: the sex fills a blank on the person, the marital status moves to its own
// column. Only then is the source cleared, so nothing is thrown away.
const MARITAL = ['married', 'single', 'widowed', 'divorced', 'separated'];
const SEXWORD = { male: 'M', female: 'F', m: 'M', f: 'F' };
function readSlippedSource(v) {
  const parts = String(v || '').split(',').map(x => x.trim().toLowerCase()).filter(Boolean);
  if (!parts.length || parts.length > 2) return null;
  let marital = null, sex = null;
  for (const part of parts) {
    if (MARITAL.includes(part)) { if (marital) return null; marital = part; }
    else if (SEXWORD[part]) { if (sex) return null; sex = SEXWORD[part]; }
    else return null;                       // anything else means it is a real source
  }
  return (marital || sex) ? { marital, sex } : null;
}

app.post('/api/admin/recover-source-column', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  const dryRun = req.body && req.body.dryRun === true;
  try {
    const rows = (await db.query(`
      SELECT c.id, c.person_id, c.source, c.census_year, c.marital_status,
             p.first_name, p.last_name, p.sex
        FROM census_entries c JOIN people p ON p.id = c.person_id
       WHERE COALESCE(TRIM(c.source), '') <> ''
       ORDER BY c.id`)).rows;

    const work = [];
    for (const r of rows) {
      const got = readSlippedSource(r.source);
      if (!got) continue;
      work.push({
        id: r.id, person_id: r.person_id, year: r.census_year,
        name: [r.first_name, r.last_name].filter(Boolean).join(' '),
        was: r.source.trim(),
        setMarital: got.marital && !r.marital_status ? got.marital : null,
        setSex: got.sex && !r.sex ? got.sex : null,
      });
    }
    if (!dryRun) {
      for (const w of work) {
        if (w.setMarital) {
          await db.query(`UPDATE census_entries SET marital_status=$2 WHERE id=$1`,
            [w.id, w.setMarital]);
        }
        if (w.setSex) {
          await db.query(
            `UPDATE people SET sex=$2, sex_source='recovered from census source column'
              WHERE id=$1 AND sex IS NULL`, [w.person_id, w.setSex]);
        }
        await db.query(`UPDATE census_entries SET source=NULL WHERE id=$1`, [w.id]);
      }
    }
    res.json({
      ok: true, dryRun,
      entries: work.length,
      maritalRecovered: work.filter(w => w.setMarital).length,
      sexRecovered: work.filter(w => w.setSex).length,
      sample: work.slice(0, 15),
    });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// POST /api/admin/backfill-birthplaces — the census entries hold far more birth
// places than the person records do, the same shape as the occupations gap.
// Fills a blank born_place from that person's census entries; never overwrites,
// and never guesses when their entries disagree.
app.post('/api/admin/backfill-birthplaces', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  const dryRun = req.body && req.body.dryRun === true;
  try {
    const r = await db.query(`
      SELECT p.id, p.first_name, p.last_name,
             ARRAY_AGG(DISTINCT TRIM(c.birth_place)) AS places
        FROM people p
        JOIN census_entries c ON c.person_id = p.id
       WHERE COALESCE(TRIM(p.born_place), '') = ''
         AND COALESCE(TRIM(c.birth_place), '') <> ''
       GROUP BY p.id, p.first_name, p.last_name
       ORDER BY p.last_name, p.first_name`);

    const filled = [], conflicted = [];
    for (const row of r.rows) {
      const places = (row.places || []).filter(Boolean);
      const name = [row.first_name, row.last_name].filter(Boolean).join(' ');
      // Two spellings of one place is a conflict we should not resolve blind.
      if (places.length === 1) filled.push({ id: row.id, name, place: places[0] });
      else conflicted.push({ id: row.id, name, places });
    }
    if (!dryRun && filled.length) {
      for (const f of filled) {
        await db.query(`UPDATE people SET born_place=$2 WHERE id=$1
                         AND COALESCE(TRIM(born_place),'') = ''`, [f.id, f.place]);
      }
    }
    res.json({ ok: true, dryRun, filled: filled.length, conflicted: conflicted.length,
               sample: filled.slice(0, 12), conflicts: conflicted.slice(0, 12) });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// POST /api/admin/dedupe-resident-links — property_residents has no unique index
// on (person_id, property_id), so the same link can be written twice. Keeps the
// lowest id of each and removes the rest.
app.post('/api/admin/dedupe-resident-links', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  const dryRun = req.body && req.body.dryRun === true;
  try {
    const dupes = (await db.query(`
      SELECT r.person_id, r.property_id, COUNT(*) AS n,
             p.first_name, p.last_name
        FROM property_residents r JOIN people p ON p.id = r.person_id
       GROUP BY r.person_id, r.property_id, p.first_name, p.last_name
      HAVING COUNT(*) > 1
       ORDER BY COUNT(*) DESC`)).rows;
    const extra = dupes.reduce((n, d) => n + (Number(d.n) - 1), 0);
    if (!dryRun && dupes.length) {
      await db.query(`
        DELETE FROM property_residents a
         USING property_residents b
         WHERE a.person_id = b.person_id
           AND a.property_id = b.property_id
           AND a.id > b.id`);
    }
    res.json({ ok: true, dryRun, pairs: dupes.length, extraRows: extra,
      sample: dupes.slice(0, 12).map(d => ({
        person_id: d.person_id, property_id: d.property_id, copies: Number(d.n),
        name: [d.first_name, d.last_name].filter(Boolean).join(' '),
      })) });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// POST /api/admin/dedupe-census-rows — the wreckage of an import file run twice.
// A file that enters a household by house name leaves its people without a
// house, waiting on the unfiled page. Once somebody places them, a second run of
// the same file used to enter the household all over again, because it looked
// for a match under the house it could not find rather than under the person and
// the year. The importer no longer does that; this clears what it left behind.
// Only the houseless copy goes, and only where the same person already holds a
// record for that year with a house on it, so nothing still waiting to be placed
// is touched.
app.post('/api/admin/dedupe-census-rows', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  const dryRun = req.body && req.body.dryRun === true;
  try {
    const rows = (await db.query(`
      SELECT c.id, c.census_year, c.unresolved_address, c.person_id,
             p.first_name, p.last_name, MIN(f.property_id) AS filed_at
        FROM census_entries c
        JOIN people p ON p.id = c.person_id
        JOIN census_entries f ON f.person_id = c.person_id
                            AND f.census_year = c.census_year
                            AND f.property_id IS NOT NULL
       WHERE c.property_id IS NULL
       GROUP BY c.id, c.census_year, c.unresolved_address, c.person_id,
                p.first_name, p.last_name
       ORDER BY c.unresolved_address NULLS LAST, p.last_name, p.first_name`)).rows;
    if (!dryRun && rows.length) {
      await db.query(`DELETE FROM census_entries WHERE id = ANY($1::int[])`,
        [rows.map(r => r.id)]);
    }
    const houses = [...new Set(rows.map(r => r.unresolved_address || 'no address recorded'))];
    res.json({ ok: true, dryRun, rows: rows.length, houses: houses.length,
      sample: rows.slice(0, 20).map(r => ({
        entry_id: r.id, year: r.census_year,
        name: [r.first_name, r.last_name].filter(Boolean).join(' '),
        address: r.unresolved_address || 'no address recorded',
        filed_at: r.filed_at,
      })) });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// POST /api/admin/split-census-row — one census record that belongs to someone
// else of the same name. An import matching on a name alone can hang a servant
// on the daughter of the house: the same two words, forty years between them,
// and the record then holds one woman who was in two houses on the same night.
// This lifts the record onto a person of her own and takes with it what came
// off the same line of the return — the age, the birthplace, the occupation,
// and the link to the house. Where the wrong birthplace was written into the
// original's empty field by that same import, it goes back to empty.
app.post('/api/admin/split-census-row', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  const entryId = parseInt(req.body && req.body.entry_id, 10);
  const dryRun = req.body && req.body.dryRun === true;
  if (!entryId) return res.status(400).json({ error: 'A census record number is needed' });
  const client = await db.connect();
  try {
    await client.query('BEGIN');
    const q = await client.query(`
      SELECT c.*, p.first_name, p.last_name, p.sex,
             p.born_year AS person_born_year, p.born_place AS person_born_place
        FROM census_entries c JOIN people p ON p.id = c.person_id
       WHERE c.id = $1`, [entryId]);
    if (!q.rows.length) {
      await client.query('ROLLBACK');
      return res.status(404).json({ error: `No census record numbered ${entryId}` });
    }
    const row = q.rows[0];
    // The year this record says she was born, against the year recorded for the
    // person it is presently attached to. The gap is the reason to split.
    const impliedBorn = (row.age_at_census != null && row.census_year)
      ? row.census_year - Number(row.age_at_census) : null;
    // Only where the import wrote this record's birthplace into an empty field
    // on a person the record says was born years apart.
    const clearsBornPlace = !!(row.birth_place && row.person_born_place === row.birth_place
      && impliedBorn && row.person_born_year && Math.abs(impliedBorn - row.person_born_year) > 3);
    const plan = {
      entry_id: entryId, year: row.census_year, property_id: row.property_id,
      name: [row.first_name, row.last_name].filter(Boolean).join(' '),
      from_person: row.person_id, relationship: row.relationship || null,
      age: row.age_at_census, born_year: impliedBorn,
      born_place: row.birth_place || null, occupation: row.occupation_at_census || null,
      from_person_born_year: row.person_born_year, clears_born_place: clearsBornPlace,
    };
    if (dryRun) { await client.query('ROLLBACK'); return res.json({ ok: true, dryRun: true, plan }); }
    const ins = await client.query(
      `INSERT INTO people (first_name, last_name, sex, born_year, born_place)
       VALUES ($1,$2,$3,$4,$5) RETURNING id`,
      [row.first_name, row.last_name, row.sex || null, impliedBorn, row.birth_place || null]);
    const newId = ins.rows[0].id;
    await client.query('UPDATE census_entries SET person_id=$1 WHERE id=$2', [newId, entryId]);
    // The occupation the import wrote from this very line goes with it. The
    // census says "Lady's maid (domestic)" where the occupation reads "Lady's
    // maid", so the qualifier in brackets is set aside for the comparison.
    let movedOccupations = 0;
    if (row.occupation_at_census) {
      const bare = row.occupation_at_census.replace(/\s*\([^)]*\)\s*$/, '').trim();
      const o = await client.query(
        `UPDATE occupations SET person_id=$1
          WHERE person_id=$2 AND from_year=$3 AND to_year=$3
            AND LOWER(occupation) = LOWER($4) RETURNING id`,
        [newId, row.person_id, row.census_year, bare]);
      movedOccupations = o.rowCount;
    }
    if (clearsBornPlace) {
      await client.query('UPDATE people SET born_place=NULL WHERE id=$1', [row.person_id]);
    }
    // The link to the house moves too, but only when the person it is leaving
    // has no other record of being there — somebody may live in a house for
    // years and appear in it on a night that was never in doubt.
    let movedLinks = 0;
    if (row.property_id) {
      try {
        const l = await client.query(
          `UPDATE property_residents SET person_id=$1
            WHERE person_id=$2 AND property_id=$3
              AND NOT EXISTS (SELECT 1 FROM census_entries c
                               WHERE c.person_id=$2 AND c.property_id=$3 AND c.id<>$4)
            RETURNING id`, [newId, row.person_id, row.property_id, entryId]);
        movedLinks = l.rowCount;
      } catch (_) {}
    }
    await client.query('COMMIT');
    await logChange('person', newId, req, 'create', 'person', plan.name, null);
    res.json({ ok: true, dryRun: false, plan, new_person_id: newId, movedOccupations, movedLinks });
  } catch (e) { await client.query('ROLLBACK'); res.status(500).json({ error: e.message }); }
  finally { client.release(); }
});

// POST /api/admin/clean-occupations — values in the occupation field that are
// not occupations. A slipped column in an import leaves a sex or a relationship
// there; a spreadsheet's "none" placeholder leaves a dash. They are few, but
// "servant" and "wife" are plausible enough to survive a filter and skew the
// occupation counts, which is exactly what makes them worth clearing.
const NOT_AN_OCCUPATION = new Set([
  'male', 'female', 'm', 'f',
  'head', 'wife', 'husband', 'son', 'daughter', 'servant', 'boarder', 'lodger',
  'visitor', 'sister', 'brother', 'mother', 'father', 'niece', 'nephew',
  'sister-in-law', 'brother-in-law', 'cousin', 'grandson', 'granddaughter',
  'none', 'n/a', 'na', 'unknown', 'nil',
]);
const isNotAnOccupation = v => {
  const t = String(v == null ? '' : v).trim();
  if (!t) return false;                       // already empty; nothing to clear
  if (/^[-–—.]+$/.test(t)) return true;       // a dash standing in for "none"
  if (/^\d{1,4}$/.test(t)) return true;       // a bare number
  return NOT_AN_OCCUPATION.has(t.toLowerCase());
};

app.post('/api/admin/clean-occupations', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  const dryRun = req.body && req.body.dryRun === true;
  try {
    const ce = (await db.query(`
      SELECT c.id, c.census_year, c.occupation_at_census AS val,
             p.first_name, p.last_name, p.id AS person_id
        FROM census_entries c JOIN people p ON p.id = c.person_id
       WHERE COALESCE(TRIM(c.occupation_at_census), '') <> ''
       ORDER BY c.id`)).rows.filter(r => isNotAnOccupation(r.val));

    const occ = (await db.query(`
      SELECT o.id, o.occupation AS val, p.first_name, p.last_name, p.id AS person_id
        FROM occupations o JOIN people p ON p.id = o.person_id
       WHERE COALESCE(TRIM(o.occupation), '') <> ''
       ORDER BY o.id`)).rows.filter(r => isNotAnOccupation(r.val));

    if (!dryRun) {
      if (ce.length) {
        await db.query(`UPDATE census_entries SET occupation_at_census = NULL WHERE id = ANY($1)`,
          [ce.map(r => r.id)]);
      }
      if (occ.length) {
        await db.query(`DELETE FROM occupations WHERE id = ANY($1)`, [occ.map(r => r.id)]);
      }
    }
    const shape = r => ({
      value: String(r.val).trim(), person_id: r.person_id,
      name: [r.first_name, r.last_name].filter(Boolean).join(' '),
      year: r.census_year || null,
    });
    res.json({
      ok: true, dryRun,
      censusCleared: ce.length, peopleCleared: occ.length,
      census: ce.map(shape), people: occ.map(shape),
    });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// GET /api/census/crowding — property-years holding an improbable number of
// people. The Park's households run to a median of five; a house showing
// twenty-odd in one year is usually several households filed against one
// address rather than a genuinely enormous one. Distinct surnames is the
// stronger tell: one household is rarely more than two or three families.
app.get('/api/census/crowding', async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  const min = Math.max(parseInt(req.query.min, 10) || 12, 2);
  try {
    const r = await db.query(`
      WITH per AS (
        SELECT c.property_id, c.census_year,
               COUNT(*) AS people,
               COUNT(DISTINCT LOWER(TRIM(p.last_name))) FILTER (
                 WHERE COALESCE(TRIM(p.last_name),'') <> '') AS surnames
          FROM census_entries c
          JOIN people p ON p.id = c.person_id
         WHERE c.property_id IS NOT NULL
         GROUP BY c.property_id, c.census_year
      ),
      stats AS (
        SELECT property_id,
               PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY people) AS median_all,
               COUNT(*) AS years_recorded
          FROM per GROUP BY property_id
      )
      SELECT per.property_id, per.census_year, per.people, per.surnames,
             s.years_recorded,
             (SELECT JSON_AGG(JSON_BUILD_ARRAY(o.census_year, o.people) ORDER BY o.census_year)
                FROM per o WHERE o.property_id = per.property_id AND o.census_year <> per.census_year
             ) AS other_years
        FROM per JOIN stats s ON s.property_id = per.property_id
       WHERE per.people >= $1
       ORDER BY per.people DESC, per.surnames DESC`, [min]);

    const all = await db.query(`
      SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY n) AS median,
             PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY n) AS p95
        FROM (SELECT COUNT(*) AS n FROM census_entries
               WHERE property_id IS NOT NULL
               GROUP BY property_id, census_year) t`);

    const unfiled = await db.query(`
      SELECT census_year, COUNT(*) AS n FROM census_entries
       WHERE property_id IS NULL GROUP BY census_year ORDER BY census_year`);

    const okRows = (await db.query(
      `SELECT property_id, census_year, note, reviewed_by, reviewed_at
         FROM crowding_reviewed ORDER BY reviewed_at DESC NULLS LAST`)).rows;
    const okKey = new Set(okRows.map(o => `${o.property_id}:${o.census_year}`));
    const confirmed = req.query.confirmed === '1';

    res.json({
      threshold: min,
      confirmedCount: okRows.length,
      median: Number(all.rows[0] && all.rows[0].median) || null,
      p95: Number(all.rows[0] && all.rows[0].p95) || null,
      unfiled: unfiled.rows.map(u => ({ year: u.census_year, count: Number(u.n) })),
      // The most recent judgements, newest first and regardless of the size
      // threshold. Pressing "This is correct" on the wrong row is easy and was
      // impossible to undo once the row fell below the threshold — or once you
      // had forgotten which row it was.
      recentlyConfirmed: okRows.slice(0, 12).map(o => ({
        property_id: o.property_id, census_year: o.census_year,
        note: o.note || null, reviewed_by: o.reviewed_by || null,
        reviewed_at: o.reviewed_at || null,
      })),
      rows: r.rows
        .filter(x => confirmed || !okKey.has(`${x.property_id}:${x.census_year}`))
        .map(x => ({
          property_id: x.property_id, census_year: x.census_year,
          people: Number(x.people), surnames: Number(x.surnames),
          other_years: x.other_years || [],
          confirmed: okKey.has(`${x.property_id}:${x.census_year}`),
          note: (okRows.find(o => o.property_id === x.property_id
                                && o.census_year === x.census_year) || {}).note || null,
        })),
    });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// POST /api/admin/move-residents — a household filed against the wrong house.
// Moves census records from one property to another, and the resident links
// with them. Optionally limited to a census year, and optionally sweeping up
// the same people's unfiled records, which sit at no property at all and so
// would not otherwise be caught by a move "from" one.
app.post('/api/admin/move-residents', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  const dryRun = req.body && req.body.dryRun === true;
  const from = parseInt(req.body && req.body.from, 10);
  // A blank destination means unfile: send the records back to the unresolved
  // queue rather than to another house. That is the honest move when a
  // household plainly does not belong where it sits but the right address is
  // not yet known.
  const rawTo = req.body && req.body.to;
  const unfile = rawTo === null || rawTo === undefined || rawTo === '';
  const to = unfile ? null : parseInt(rawTo, 10);
  const year = req.body && req.body.year ? parseInt(req.body.year, 10) : null;
  const includeUnfiled = req.body && req.body.includeUnfiled === true;
  const only = Array.isArray(req.body && req.body.personIds) && req.body.personIds.length
    ? req.body.personIds.map(n => parseInt(n, 10)).filter(Number.isInteger) : null;
  if (!Number.isInteger(from) || (!unfile && !Number.isInteger(to))) {
    return res.status(400).json({ error: 'a from property id is required, and a to id unless unfiling' });
  }
  if (!unfile && from === to) return res.status(400).json({ error: 'from and to are the same property' });
  try {
    // Who is actually at the source, so an unfiled sweep cannot reach beyond them.
    const atSource = (await db.query(
      `SELECT DISTINCT person_id FROM census_entries
        WHERE property_id=$1 AND person_id IS NOT NULL
          ${year ? 'AND census_year=$2' : ''}`,
      year ? [from, year] : [from])).rows.map(r => r.person_id);
    const people = only ? atSource.filter(id => only.includes(id)) : atSource;
    if (!people.length) return res.json({ ok: true, dryRun, entries: [], links: 0, people: 0 });

    const entries = (await db.query(
      `SELECT c.id, c.census_year, c.property_id, p.first_name, p.last_name
         FROM census_entries c JOIN people p ON p.id = c.person_id
        WHERE c.person_id = ANY($1)
          AND ( c.property_id = $2 ${includeUnfiled ? 'OR c.property_id IS NULL' : ''} )
          ${year ? 'AND c.census_year = $3' : ''}
        ORDER BY p.last_name, p.first_name, c.census_year`,
      year ? [people, from, year] : [people, from])).rows;

    const linkRows = (await db.query(
      `SELECT person_id FROM property_residents WHERE property_id=$1 AND person_id = ANY($2)`,
      [from, people])).rows.map(r => r.person_id);

    if (!dryRun && entries.length) {
      // Unfiling keeps whatever address hint the record carries; filing clears it.
      await db.query(
        `UPDATE census_entries
            SET property_id=$1,
                unresolved_address = CASE WHEN $1::int IS NULL THEN unresolved_address ELSE NULL END
          WHERE id = ANY($2)`, [to, entries.map(e => e.id)]);
    }
    // Unfiling removes the resident link rather than pointing it somewhere new.
    if (!dryRun && unfile && linkRows.length) {
      await db.query(`DELETE FROM property_residents WHERE property_id=$1 AND person_id = ANY($2)`,
        [from, linkRows]);
    }
    if (!dryRun && !unfile && linkRows.length) {
      // The person may already be linked to the destination. property_residents
      // has no unique index on (person_id, property_id), so ON CONFLICT has
      // nothing to catch on and would happily write a second identical link —
      // the source of a duplicate the first time this ran. Test explicitly.
      await db.query(
        `INSERT INTO property_residents (person_id, property_id)
         SELECT pid, $2 FROM unnest($1::int[]) AS t(pid)
          WHERE NOT EXISTS (
            SELECT 1 FROM property_residents r
             WHERE r.person_id = t.pid AND r.property_id = $2)`,
        [linkRows, to]);
      await db.query(`DELETE FROM property_residents WHERE property_id=$1 AND person_id = ANY($2)`,
        [from, linkRows]);
    }
    res.json({
      ok: true, dryRun, from, to, unfile, year, people: people.length,
      links: linkRows.length,
      entries: entries.map(e => ({
        id: e.id, year: e.census_year,
        name: [e.first_name, e.last_name].filter(Boolean).join(' '),
        wasUnfiled: e.property_id === null,
      })),
    });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// GET /api/admin/stray-rows — people who are not people: header rows and blanks
// that survived an import. Read-only; deleting stays a deliberate click.
app.get('/api/admin/stray-rows', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  try {
    const r = await db.query(
      `SELECT p.id, p.first_name, p.last_name,
              (SELECT COUNT(*) FROM census_entries c WHERE c.person_id = p.id) AS census_entries
         FROM people p
        ORDER BY p.id`
    );
    const strays = r.rows.filter(p => {
      const fn = (p.first_name || '').trim(), ln = (p.last_name || '').trim();
      if (!fn && !ln) return true;
      return (!fn || looksLikeHeading(fn)) && (!ln || looksLikeHeading(ln));
    });
    res.json({ scanned: r.rows.length, strays });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// POST /api/census/import — bulk import from pasted census data
app.post('/api/census/import', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  try {
    const { property_id, census_year, rows } = req.body;
    if (!census_year || !rows || !rows.length) return res.status(400).json({ error: 'Missing required fields' });
    const results = [];
    for (const row of rows) {
      // Skip rows with no usable name (blanks, *MISSING*, sub-headers that slipped through)
      const fn = (row.first_name || '').trim();
      const ln = (row.last_name || '').trim();
      if (!fn && !ln) continue;
      if (/^\*.*\*$/.test(fn) || /^\*.*\*$/.test(ln)) continue; // e.g. *MISSING*
      // The spreadsheet's own header row, pasted in along with the data.
      if ((!fn || looksLikeHeading(fn)) && (!ln || looksLikeHeading(ln))) continue;
      let personId = row.person_id ? parseInt(row.person_id) : null;
      if (!personId) {
        // Try to match an existing person by name before creating a new one
        const existing = await db.query(
          `SELECT id FROM people WHERE LOWER(TRIM(first_name))=$1 AND LOWER(TRIM(last_name))=$2 LIMIT 1`,
          [fn.toLowerCase(), ln.toLowerCase()]
        );
        if (existing.rows.length > 0) {
          personId = existing.rows[0].id;
          // Backfill born_year / born_place if the existing record lacks them
          if (row.birth_year || row.birth_place) {
            await db.query(
              `UPDATE people SET
                born_year  = COALESCE(born_year,  $2),
                born_place = COALESCE(born_place, $3)
               WHERE id=$1`,
              [personId, row.birth_year || null, row.birth_place || null]
            );
          }
          results.push({ personId, created: false, matched: true, name: `${fn} ${ln}`.trim() });
        } else {
          // Create new person
          const pRes = await db.query(
            `INSERT INTO people (first_name, last_name, born_year, born_place) VALUES ($1,$2,$3,$4) RETURNING id`,
            [fn || null, ln || null, row.birth_year || null, row.birth_place || null]
          );
          personId = pRes.rows[0].id;
          results.push({ personId, created: true, name: `${fn} ${ln}`.trim() });
        }
      } else {
        results.push({ personId, created: false });
      }
      // Skip if an entry for this person+year already exists (prevents double-import)
      const dupCheck = await db.query(
        `SELECT id FROM census_entries WHERE person_id=$1 AND census_year=$2 LIMIT 1`,
        [personId, census_year]
      );
      if (dupCheck.rows.length === 0) {
        await db.query(
          `INSERT INTO census_entries (person_id, property_id, census_year, relationship, age_at_census, occupation_at_census, census_household_num, unresolved_address, birth_place)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)`,
          [personId, property_id || null, census_year, row.relationship || null,
           row.age ? parseInt(row.age) : null, row.occupation || null,
           row.census_household_num || null, row.unresolved_address || null,
           row.birth_place || null]
        );
      }
    }
    res.json({ ok: true, results });
    // Async geocode any new unique birth places (don't block the response)
    const newPlaces = [...new Set(rows.map(r => r.birth_place).filter(Boolean))];
    if (newPlaces.length) geocodePlacesBatch(newPlaces).catch(e => console.error('Batch geocode error:', e.message));
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// ── Census XLSX file import — removed ────────────────────────────────────────
// The spreadsheet upload was the only thing using the `xlsx` package, which
// carries a high-severity advisory (prototype pollution and ReDoS when parsing
// a crafted file) with no upstream fix. With no imports planned, the feature and
// the dependency are gone rather than carried.
//
// It parsed three sheet shapes — 1911 DAN, 1921hd, and a simple layout — with
// carry-forward across merged cells for 1911. To bring it back, restore from
// git (it was removed in this commit) and read it with a maintained library.
// The paste-based import at /api/census/import is untouched and still works.

// ── Birthplace admin ──────────────────────────────────────────────────────────
// GET /api/admin/unknown-places — birth places with no geocode result yet
app.get('/api/admin/unknown-places', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  try {
    const { rows } = await db.query(`
      SELECT
        TRIM(ce.birth_place) AS birth_place,
        COUNT(DISTINCT ce.person_id) AS cnt,
        JSON_AGG(DISTINCT p.first_name || ' ' || p.last_name ORDER BY 1) FILTER (WHERE p.id IS NOT NULL) AS examples,
        gc.status AS geocode_status
      FROM census_entries ce
      JOIN people p ON p.id = ce.person_id
      LEFT JOIN geocode_cache gc ON gc.place_text = TRIM(ce.birth_place)
      WHERE ce.birth_place IS NOT NULL AND TRIM(ce.birth_place) != ''
        AND (gc.place_text IS NULL OR gc.status = 'not_found')
      GROUP BY TRIM(ce.birth_place), gc.status
      ORDER BY cnt DESC, birth_place
    `);
    res.json(rows);
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// POST /api/admin/geocode-place — try to geocode a place (with optional corrected search text)
app.post('/api/admin/geocode-place', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  const { place_text, search_text } = req.body;
  if (!place_text) return res.status(400).json({ error: 'place_text required' });
  try {
    const result = await geocodePlace(place_text, search_text || place_text);
    if (result) {
      res.json({ ok: true, found: true, ...result });
    } else {
      res.json({ ok: true, found: false });
    }
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// DELETE /api/admin/geocode-place — remove a cache entry (to allow retry)
app.delete('/api/admin/geocode-place', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  const { place_text } = req.body;
  if (!place_text) return res.status(400).json({ error: 'place_text required' });
  try {
    await db.query('DELETE FROM geocode_cache WHERE place_text=$1', [place_text.trim()]);
    res.json({ ok: true });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// POST /api/admin/normalise-occupations — apply OCC_NORM_SERVER to census_entries + occupations
app.post('/api/admin/normalise-occupations', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  try {
    let totalUpdated = 0;
    for (const [raw, norm] of Object.entries(OCC_NORM_SERVER)) {
      if (raw === norm.toLowerCase().trim()) continue;
      const [r1, r2] = await Promise.all([
        db.query(`UPDATE census_entries SET occupation_at_census=$1 WHERE LOWER(TRIM(occupation_at_census))=$2`, [norm, raw]),
        db.query(`UPDATE occupations SET occupation=$1 WHERE LOWER(TRIM(occupation))=$2`, [norm, raw])
      ]);
      totalUpdated += (r1.rowCount || 0) + (r2.rowCount || 0);
    }
    res.json({ ok: true, updated: totalUpdated });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// GET /api/census-stats — coverage counts per year for the census landing page
app.get('/api/census-stats', async (req, res) => {
  if (!db) return res.json([]);
  try {
    const allPropsArr = JSON.parse(fs.readFileSync(ALL_PROPS_FILE, 'utf8'));
    const total = allPropsArr.length || 350;
    const [recordedRes, unoccupiedRes] = await Promise.all([
      db.query(`SELECT census_year, COUNT(DISTINCT property_id) AS cnt FROM census_entries WHERE property_id IS NOT NULL GROUP BY census_year`).catch(()=>({rows:[]})),
      db.query(`SELECT census_year, COUNT(*) AS cnt FROM census_unoccupied GROUP BY census_year`).catch(()=>({rows:[]}))
    ]);
    const recorded = {}, unoccupied = {};
    recordedRes.rows.forEach(r => { recorded[r.census_year] = parseInt(r.cnt); });
    unoccupiedRes.rows.forEach(r => { unoccupied[r.census_year] = parseInt(r.cnt); });
    const years = [1851,1861,1871,1881,1891,1901,1911,1921,1939];
    res.json(years.map(y => ({ year: y, recorded: recorded[y]||0, unoccupied: unoccupied[y]||0, total })));
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// GET /api/census-coverage/:year — all properties with their census status for that year
app.get('/api/census-coverage/:year', async (req, res) => {
  if (!db) return res.json([]);
  try {
    const year = parseInt(req.params.year);
    if (!year) return res.json([]);
    const props = JSON.parse(fs.readFileSync(ALL_PROPS_FILE, 'utf8'));
    const [recordedRes, unoccupiedRes, countsRes] = await Promise.all([
      db.query(`SELECT DISTINCT property_id FROM census_entries WHERE census_year=$1 AND property_id IS NOT NULL`, [year]).catch(()=>({rows:[]})),
      db.query(`SELECT property_id, notes FROM census_unoccupied WHERE census_year=$1`, [year]).catch(()=>({rows:[]})),
      db.query(`SELECT property_id, COUNT(DISTINCT person_id) AS cnt FROM census_entries WHERE census_year=$1 AND property_id IS NOT NULL GROUP BY property_id`, [year]).catch(()=>({rows:[]}))
    ]);
    const recordedSet = new Set(recordedRes.rows.map(r => r.property_id));
    const unoccupiedMap = {};
    unoccupiedRes.rows.forEach(r => { unoccupiedMap[r.property_id] = r.notes || ''; });
    const countsMap = {};
    countsRes.rows.forEach(r => { countsMap[r.property_id] = parseInt(r.cnt); });
    res.json((Array.isArray(props) ? props : []).map(p => ({
      id: p.id,
      address: (p.address||'Property '+p.id).replace(/:\s*([A-Z])/g,', $1').replace(/:\s*$/,''),
      status: recordedSet.has(p.id) ? 'recorded' : unoccupiedMap[p.id] !== undefined ? 'unoccupied' : 'none',
      people_count: countsMap[p.id] || 0,
      unoccupied_notes: unoccupiedMap[p.id] || null
    })));
  } catch(e) { console.error('census-coverage error:', e.message); res.status(500).json({ error: e.message }); }
});

// POST /api/census-unoccupied — mark a property as unoccupied for a census year
app.post('/api/census-unoccupied', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  try {
    const { property_id, census_year, notes } = req.body;
    await db.query(
      `INSERT INTO census_unoccupied (property_id, census_year, notes) VALUES ($1,$2,$3)
       ON CONFLICT (property_id, census_year) DO UPDATE SET notes=EXCLUDED.notes`,
      [property_id, census_year, notes||null]
    );
    res.json({ ok: true });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// GET /census page
app.get('/census', (req, res) => res.sendFile(path.join(__dirname,'public','census.html')));
app.get('/census/unresolved', (req, res) => res.sendFile(path.join(__dirname,'public','census-unresolved.html')));
app.get('/admin/birthplaces', (req, res) => res.sendFile(path.join(__dirname,'public','admin-birthplaces.html')));

// GET /api/recent-changes — for dashboard activity feed
app.get('/api/recent-changes', async (req, res) => {
  if (!db) return res.json([]);
  try {
    const mode = req.query.mode || 'recent'; // 'recent' or 'most-updated'
    let out;
    if (mode === 'most-updated') {
      const r = await db.query(`
        SELECT entity_type, entity_id, COUNT(*) AS update_count,
               MAX(created_at) AS last_update, MAX(username) AS username
        FROM change_log GROUP BY entity_type, entity_id
        ORDER BY update_count DESC LIMIT 30`);
      out = await Promise.all(r.rows.map(async row => {
        let label = row.entity_type + ' ' + row.entity_id;
        try {
          if (row.entity_type === 'person') {
            const p = await db.query('SELECT first_name, last_name, known_as FROM people WHERE id=$1', [row.entity_id]);
            if (p.rows[0]) { const x=p.rows[0]; label = x.known_as||(x.first_name+' '+x.last_name); }
          } else if (row.entity_type === 'property') {
            const prop = await loadProp(parseInt(row.entity_id));
            label = (prop && (prop.address || prop.name)) ? (prop.address||prop.name) : 'Property '+row.entity_id;
          }
        } catch(_) {}
        return { ...row, entity_label: label, update_count: parseInt(row.update_count) };
      }));
    } else {
      const r = await db.query(`
        SELECT cl.*, p.first_name, p.last_name, p.known_as
        FROM change_log cl
        LEFT JOIN people p ON cl.entity_type='person' AND p.id=cl.entity_id
        ORDER BY cl.created_at DESC LIMIT 40`);
      out = r.rows.map(row => {
        let label = row.entity_type;
        if (row.entity_type === 'person' && (row.first_name || row.last_name)) {
          label = row.known_as || ((row.first_name||'') + ' ' + (row.last_name||'')).trim();
        } else if (row.entity_type === 'property') {
          label = 'Property ' + row.entity_id;
        }
        return { ...row, entity_label: label };
      });
    }
    res.json(out);
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// GET /api/people-counts — returns {propId: count} for all properties that have people
app.get('/api/people-counts', async (req, res) => {
  if (!db) return res.json({});
  try {
    const r = await db.query(`
      SELECT ce.property_id, COUNT(DISTINCT ce.person_id) AS cnt
      FROM census_entries ce
      WHERE ce.property_id IS NOT NULL
      GROUP BY ce.property_id
    `);
    const out = {};
    r.rows.forEach(row => { out[row.property_id] = parseInt(row.cnt); });
    res.json(out);
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// ── Top residents by property count ──────────────────────────────────────────
app.get('/api/stats/top-residents', async (req, res) => {
  if (!db) return res.json([]);
  try {
    const r = await db.query(`
      SELECT p.id as person_id,
             p.first_name || ' ' || p.last_name as name,
             COUNT(DISTINCT ce.property_id) as prop_count,
             ARRAY_AGG(DISTINCT ce.property_id) FILTER (WHERE ce.property_id IS NOT NULL) as prop_ids
      FROM people p
      JOIN census_entries ce ON ce.person_id = p.id
      WHERE ce.property_id IS NOT NULL
      GROUP BY p.id, p.first_name, p.last_name
      HAVING COUNT(DISTINCT ce.property_id) > 0
      ORDER BY prop_count DESC, p.last_name
      LIMIT 30
    `);
    const rows = r.rows.map(row => ({
      ...row,
      prop_count: parseInt(row.prop_count),
      properties: (row.prop_ids || []).map(id => propName(id))
    }));
    res.json(rows);
  } catch(e) { res.json([]); }
});

// ── Admin: deduplicate relationships ─────────────────────────────────────────
app.post('/api/admin/deduplicate-relationships', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  try {
    const r = await db.query(`
      DELETE FROM people_relationships
      WHERE id IN (
        SELECT a.id FROM people_relationships a
        JOIN people_relationships b
          ON a.person_a_id=b.person_a_id
         AND a.person_b_id=b.person_b_id
         AND a.relationship=b.relationship
         AND a.id > b.id
      )
    `);
    res.json({ ok: true, deleted: r.rowCount });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// ── Delete a person entirely (admin only) ────────────────────────────────────
app.delete('/api/person/:id', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  const personId = parseInt(req.params.id);
  if (!personId) return res.status(400).json({ error: 'Invalid person id' });
  const client = await db.connect();
  try {
    await client.query('BEGIN');
    // Get name for audit log
    const who = await client.query('SELECT first_name,last_name FROM people WHERE id=$1', [personId]);
    if (!who.rows.length) { await client.query('ROLLBACK'); return res.status(404).json({ error: 'Person not found' }); }
    // Remove all related records
    await client.query('DELETE FROM census_entries        WHERE person_id=$1', [personId]);
    await client.query('DELETE FROM occupations           WHERE person_id=$1', [personId]);
    await client.query('DELETE FROM people_relationships  WHERE person_a_id=$1 OR person_b_id=$1', [personId]);
    await client.query('DELETE FROM people_places         WHERE person_id=$1', [personId]);
    await client.query('DELETE FROM person_media          WHERE person_id=$1', [personId]);
    await client.query('DELETE FROM person_links          WHERE person_id=$1', [personId]);
    await client.query('DELETE FROM bibliography          WHERE author_person_id=$1', [personId]);
    try { await client.query('DELETE FROM property_residents WHERE person_id=$1', [personId]); } catch(_) {}
    await client.query('DELETE FROM people WHERE id=$1', [personId]);
    await client.query('COMMIT');
    const name = `${who.rows[0].first_name} ${who.rows[0].last_name}`;
    await logChange('person', personId, req, 'delete', 'person', name, null);
    res.json({ ok: true, deleted: personId, name });
  } catch(e) { await client.query('ROLLBACK'); res.status(500).json({ error: e.message }); }
  finally { client.release(); }
});

// The short forms a census enumerator uses, against the names the record keeps.
// Only forms that are unambiguous in a Victorian return belong here: "Jas." is
// always James, but "Al." could be Albert or Alfred and is left alone.
const FORENAME_ABBR = {
  geo: 'george', chas: 'charles', wm: 'william', jno: 'john', jas: 'james',
  thos: 'thomas', fredk: 'frederick', edwd: 'edward', richd: 'richard',
  robt: 'robert', saml: 'samuel', benjn: 'benjamin', danl: 'daniel',
  josh: 'joseph', jos: 'joseph', elizth: 'elizabeth', eliz: 'elizabeth',
  margt: 'margaret', catharine: 'catherine', cathe: 'catherine',
  hy: 'henry', alexr: 'alexander', matw: 'matthew', andw: 'andrew',
  chris: 'christopher', nichs: 'nicholas', phil: 'philip', sarh: 'sarah',
};
const expandForename = w => FORENAME_ABBR[w] || w;

// The body of a merge, so the one-pair route and the bulk tool below run the
// same proven steps rather than two drifting copies of them. Caller owns the
// transaction.
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

  await client.query('DELETE FROM people WHERE id=$1', [deleteId]);
}

// POST /api/admin/merge-abbreviated-names — the same person entered twice
// because a transcription kept the enumerator's short forms. "Geo. Parr" beside
// George Parr, both born 1846, the new record holding one census year and the
// older one everything else. The two are paired only where the surname matches,
// the first forename matches once the short form is expanded, and the birth
// years are within two — and never where somebody has already said on the
// duplicates page that they are two different people. The fuller record is the
// one kept.
app.post('/api/admin/merge-abbreviated-names', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  const dryRun = req.body && req.body.dryRun === true;
  // Which records count as new. An import that has just run is the only thing
  // that makes these pairs, so the tool looks no further back than the first
  // person it created — everything older is the duplicates page's business.
  const sinceId = Number.isFinite(Number(req.body && req.body.since_id))
    && Number(req.body.since_id) > 0 ? Number(req.body.since_id) : 2900;
  try {
    const people = (await db.query(`
      SELECT p.id, p.first_name, p.last_name, p.born_year, p.bio IS NOT NULL AS has_bio,
             p.wikipedia_url, p.photo_url,
             (SELECT COUNT(*) FROM census_entries c WHERE c.person_id = p.id) AS entries,
             (SELECT COUNT(*) FROM occupations o WHERE o.person_id = p.id) AS occupations,
             (SELECT COUNT(*) FROM people_relationships r
               WHERE r.person_a_id = p.id OR r.person_b_id = p.id) AS relationships,
             ARRAY(SELECT DISTINCT c.census_year FROM census_entries c
                    WHERE c.person_id = p.id AND c.census_year IS NOT NULL ORDER BY 1) AS years
        FROM people p
       WHERE COALESCE(TRIM(p.first_name),'') <> '' AND COALESCE(TRIM(p.last_name),'') <> ''`)).rows;
    const dismissed = new Set((await db.query(
      `SELECT person_a_id, person_b_id FROM duplicate_dismissed`)).rows
      .map(d => `${d.person_a_id}:${d.person_b_id}`));

    const norm = v => String(v || '').toLowerCase().replace(/[^a-z]/g, '');
    const rawWords = v => String(v || '').trim().split(/\s+/).map(norm).filter(Boolean);
    const forenames = v => rawWords(v).map(expandForename);
    const buckets = new Map();
    for (const p of people) {
      const f = forenames(p.first_name);
      if (!f.length || !norm(p.last_name)) continue;
      const k = norm(p.last_name) + '|' + f[0];
      if (!buckets.has(k)) buckets.set(k, []);
      buckets.get(k).push(p);
    }
    // Two spellings of one name, or two people. Every forename must agree once
    // the short forms are expanded, treating a lone initial as standing for the
    // name beside it: "Catharine L." answers to Catherine Lucy. Anything that
    // disagrees on a name in the middle is two people and is left alone.
    const howAlike = (a, b) => {
      const fa = forenames(a), fb = forenames(b);
      if (!fa.length || !fb.length || fa[0] !== fb[0]) return null;
      for (let i = 0; i < Math.min(fa.length, fb.length); i++) {
        const x = fa[i], y = fb[i];
        if (x === y) continue;
        if (x.length === 1 && y.startsWith(x)) continue;
        if (y.length === 1 && x.startsWith(y)) continue;
        return null;
      }
      const same = rawWords(a).join(' ') === rawWords(b).join(' ');
      if (same) return 'the same spelling entered twice';
      if (fa.join(' ') === fb.join(' ')) return 'a short form written out';
      return 'an initial against the name it stands for';
    };
    // The fuller record is the one to keep — and fullness is what is actually
    // on it. An abbreviated name is not made fuller by having more words in it,
    // which is why the occupations, the bio and the relationships count and a
    // bare initial counts against.
    const weight = p => (p.years.length * 4) + Number(p.entries)
      + (Number(p.occupations) * 3) + (Number(p.relationships) * 2)
      + (p.wikipedia_url ? 3 : 0) + (p.photo_url ? 3 : 0) + (p.has_bio ? 3 : 0)
      + rawWords(p.first_name).reduce((n, w) => n + (w.length > 1 ? (expandForename(w) === w ? 2 : 1) : -1), 0);
    const pairs = [];
    const spoken = new Set();
    for (const list of buckets.values()) {
      if (list.length < 2) continue;
      for (let i = 0; i < list.length; i++) {
        for (let j = i + 1; j < list.length; j++) {
          const a = list[i], b = list[j];
          if (!a.born_year || !b.born_year) continue;
          // Ages on a census night are rounded, and a birth year worked back
          // from one is rounded with them; three years is as far as that
          // stretches before it is somebody else.
          if (Math.abs(a.born_year - b.born_year) > 3) continue;
          // Only pairs an import could have made. Two people who have both been
          // in the record for years and merely share a name are not this tool's
          // to judge — they belong on the duplicates page, where a person
          // decides. Elizabeth Phillips at two different houses is exactly the
          // pair that must not be swept up here.
          if (a.id < sinceId && b.id < sinceId) continue;
          const why = howAlike(a.first_name, b.first_name);
          if (!why) continue;
          const lo = Math.min(a.id, b.id), hi = Math.max(a.id, b.id);
          if (dismissed.has(`${lo}:${hi}`)) continue;
          if (spoken.has(a.id) || spoken.has(b.id)) continue; // one pair per person per run
          const [keep, drop] = weight(a) >= weight(b) ? [a, b] : [b, a];
          spoken.add(a.id); spoken.add(b.id);
          pairs.push({
            keep_id: keep.id, drop_id: drop.id,
            keep: [keep.first_name, keep.last_name].filter(Boolean).join(' '),
            drop: [drop.first_name, drop.last_name].filter(Boolean).join(' '),
            born: keep.born_year === drop.born_year ? keep.born_year
              : `${drop.born_year} and ${keep.born_year}`,
            keep_years: keep.years, drop_years: drop.years, why,
          });
        }
      }
    }
    pairs.sort((x, y) => x.keep.localeCompare(y.keep));
    if (dryRun) return res.json({ ok: true, dryRun, merged: 0, pairs });
    const client = await db.connect();
    let merged = 0;
    try {
      for (const p of pairs) {
        await client.query('BEGIN');
        await mergePeopleInto(client, p.keep_id, p.drop_id);
        await client.query('COMMIT');
        merged++;
        await logChange('person', p.keep_id, req, 'merge', 'person',
          `${p.drop} (#${p.drop_id})`, `${p.keep} (#${p.keep_id})`);
      }
    } catch (e) {
      await client.query('ROLLBACK');
      return res.status(500).json({ error: e.message, merged, pairs });
    } finally { client.release(); }
    res.json({ ok: true, dryRun, merged, pairs });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// ── Merge two people (contributors+): keep one, absorb all data from the other ──
app.post('/api/admin/merge-people', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  const { keep_id, delete_id } = req.body;
  if (!keep_id || !delete_id) return res.status(400).json({ error: 'keep_id and delete_id required' });
  const keepId = parseInt(keep_id), deleteId = parseInt(delete_id);
  if (keepId === deleteId) return res.status(400).json({ error: 'Cannot merge a person with themselves' });
  const client = await db.connect();
  try {
    await client.query('BEGIN');

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

    // Reassign all related records
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
    // property_residents (may not exist)
    try { await client.query('UPDATE property_residents SET person_id=$1 WHERE person_id=$2', [keepId, deleteId]); } catch(_) {}

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

    // Delete the absorbed person
    await client.query('DELETE FROM people WHERE id=$1', [deleteId]);

    await client.query('COMMIT');
    res.json({ ok: true, kept: keepId, deleted: deleteId });
  } catch(e) { await client.query('ROLLBACK'); res.status(500).json({ error: e.message }); }
  finally { client.release(); }
});

// ── User management (admin) ───────────────────────────────────────────────────
app.get('/api/admin/users', requireAdmin, async (req, res) => {
  if (!db) return res.json([]);
  try {
    const r = await db.query('SELECT id,email,first_name,last_name,role,approved,approved_by,created_at FROM users ORDER BY created_at DESC');
    res.json(r.rows);
  } catch(e) { res.status(500).json({ error: e.message }); }
});

app.patch('/api/admin/users/:id', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  const { role, approved } = req.body;
  const validRoles = ['viewer','contributor','admin'];
  if (role && !validRoles.includes(role)) return res.status(400).json({ error: 'Invalid role' });
  try {
    const sets = [], params = [parseInt(req.params.id)];
    if (role !== undefined) { params.push(role); sets.push(`role=$${params.length}`); }
    if (approved !== undefined) {
      params.push(approved);
      sets.push(`approved=$${params.length}`);
      if (approved) { params.push(req.session.username||'admin'); sets.push(`approved_by=$${params.length}`); }
    }
    if (!sets.length) return res.status(400).json({ error: 'Nothing to update' });
    await db.query(`UPDATE users SET ${sets.join(',')} WHERE id=$1`, params);
    await logChange('user', parseInt(req.params.id), req, 'update', role?'role':approved?'approved':'', null, role||String(approved));
    res.json({ ok: true });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

app.delete('/api/admin/users/:id', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  try {
    await db.query('DELETE FROM users WHERE id=$1', [parseInt(req.params.id)]);
    res.json({ ok: true });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// ── One-time occupation normalisation (admin only) ────────────────────────────
app.post('/api/admin/normalise-occupations', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  const merges = [
    { targets: ['servant','general servant','domestic servant','general domestic servant','household servant','house servant'], canonical: 'Domestic servant' },
    { targets: ['kitchenmaid','kitchen maid','kitchen-maid','scullery maid','scullery-maid'], canonical: 'Kitchenmaid' },
    { targets: ['nurse','hospital nurse','sick nurse','monthly nurse'], canonical: 'Nurse' },
  ];
  let total = 0;
  for (const { targets, canonical } of merges) {
    for (const t of targets) {
      const r = await db.query(`UPDATE occupations SET occupation=$1 WHERE LOWER(occupation)=LOWER($2)`, [canonical, t]);
      total += r.rowCount;
    }
  }
  res.json({ ok: true, updated: total });
});

// GET /api/seeded-properties — returns array of property IDs that have a seed file on disk
app.get('/api/seeded-properties', (req, res) => {
  const dataDir = path.join(__dirname, 'data');
  try {
    const ids = fs.readdirSync(dataDir)
      .map(f => f.match(/^seed-(\d+)-/))
      .filter(Boolean)
      .map(m => parseInt(m[1]));
    res.json(ids);
  } catch(e) { res.json([]); }
});

// GET /api/people/occupation/:occ — everyone with this occupation across all properties
app.get('/api/people/occupation/:occ', async (req, res) => {
  if (!db) return res.json([]);
  try {
    const r = await db.query(`
      SELECT p.id, p.first_name, p.last_name, p.known_as, p.born_year, p.died_year,
             o.occupation, o.from_year, o.to_year, o.employer,
             ARRAY_AGG(DISTINCT ce.property_id) FILTER (WHERE ce.property_id IS NOT NULL) AS property_ids,
             ARRAY_AGG(DISTINCT ce.census_year) FILTER (WHERE ce.census_year IS NOT NULL) AS census_years
      FROM people p
      JOIN occupations o ON o.person_id=p.id
      LEFT JOIN census_entries ce ON ce.person_id=p.id
      WHERE LOWER(o.occupation) LIKE LOWER($1)
      GROUP BY p.id, o.id ORDER BY p.last_name, p.first_name`,
      [`%${req.params.occ}%`]
    );
    res.json(r.rows);
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// GET /api/occupation-groups — returns list of group names and the raw occupation strings in each
const OCC_NORM_SERVER = {"domestic servant":"Domestic Servant","domestic servants":"Domestic Servant","domestic":"Domestic Servant","general domestic servant":"Domestic Servant","general domestic":"Domestic Servant","general servant":"Domestic Servant","general servant domestic":"Domestic Servant","general servant (domestic)":"Domestic Servant","general domestic service":"Domestic Servant","domestic service":"Domestic Servant","servant":"Domestic Servant","domestic - servant":"Domestic Servant","domestic serv":"Domestic Servant","general serv":"Domestic Servant","domestic occupation":"Domestic Servant","housemaid":"Housemaid","house maid":"Housemaid","housemaid domestic":"Housemaid","housemaid (domestic servant)":"Housemaid","housemaid domestic servant":"Housemaid","housemaid (dom)":"Housemaid","house maid domestic":"Housemaid","domestic housemaid":"Housemaid","under housemaid":"Under Housemaid","cook":"Cook","domestic cook":"Cook","cook domestic":"Cook","cook (dom)":"Cook","cook domestic servant":"Cook","cook domestic service":"Cook","coole":"Cook","cook general, private":"Cook","cook general":"Cook","parlourmaid":"Parlourmaid","parlour maid":"Parlourmaid","parlor maid":"Parlourmaid","parlormaid":"Parlourmaid","parlour maid domestic":"Parlourmaid","parlourmaid domestic":"Parlourmaid","house parlourmaid":"House Parlourmaid","house parlour maid":"House Parlourmaid","house parlour maid, private":"House Parlourmaid","house parlourmaid domestic service":"House Parlourmaid","kitchenmaid":"Kitchenmaid","kitchen maid":"Kitchenmaid","lady's maid":"Lady's Maid","ladies' maid":"Lady's Maid","ladies maid":"Lady's Maid","ladys maid":"Lady's Maid","housekeeper":"Housekeeper","house keeper":"Housekeeper","housekeeper domestic":"Housekeeper","house keeper domestic":"Housekeeper","housekeeper for above":"Housekeeper","housekeeper in charge":"Housekeeper","nursemaid":"Nursemaid","nurse maid":"Nursemaid","childs nurse":"Nursemaid","childrens nurse":"Nursemaid","nurse domestic":"Domestic Nurse","domestic nurse":"Domestic Nurse","nurse":"Nurse","sick nurse":"Sick Nurse","sick nurse (own means)":"Sick Nurse","hospital nurse":"Nurse","private nurse":"Nurse","nurse (certified)":"Nurse","nurse private":"Nurse","trained nurse":"Nurse","professional nurse":"Nurse","red cross nurse":"Red Cross Nurse","maternity nurse":"Maternity Nurse","solicitor":"Solicitor","solicitior":"Solicitor","knight solicitor":"Solicitor","lace manufacturer":"Lace Manufacturer","lace manufacturers":"Lace Manufacturer","lace manuf":"Lace Manufacturer","lace manu":"Lace Manufacturer","lace manufacturer (director)":"Lace Manufacturer","lace manufacturer (retired)":"Lace Manufacturer (Retired)","lace manuf (retired)":"Lace Manufacturer (Retired)","retired lace manufacturer":"Lace Manufacturer (Retired)","retired lace manufacture":"Lace Manufacturer (Retired)","retired lace manuf":"Lace Manufacturer (Retired)","lace dresser":"Lace Dresser","lace dresser and bleacher":"Lace Dresser and Bleacher","lace dresser and finisher":"Lace Dresser","lace dresser, dyer and bleacher":"Lace Dresser and Bleacher","lace merchant":"Lace Merchant","retired lace merchant":"Lace Merchant (Retired)","hosiery manufacturer":"Hosiery Manufacturer","hosiery manufactures director":"Hosiery Manufacturer","hosier; chairman and managing director":"Hosiery Manufacturer","hosier":"Hosier","hosiery and glove manufacturer":"Hosiery and Glove Manufacturer","hosiery and glove merchant":"Hosiery and Glove Manufacturer","manufacturer hosiery machinery":"Hosiery Machinery Manufacturer","manufacture textile machinery":"Textile Machinery Manufacturer","manu hosiery":"Hosiery Manufacturer","retired hosier":"Hosier (Retired)","retired hosiery manufacturer":"Hosiery Manufacturer (Retired)","knitted fabric manufacturer":"Hosiery Manufacturer","yarn agent":"Yarn Agent","yarn merchant":"Yarn Merchant","retired yarn merchant":"Yarn Merchant (Retired)","chairman yarn manufacturer":"Yarn Manufacturer","draper":"Draper","draper's clerk":"Draper's Clerk","linen and woollen draper":"Draper","architect":"Architect","civil engineer":"Civil Engineer","mechanical engineer":"Mechanical Engineer","mining engineer":"Mining Engineer","chief mechanical engineer":"Chief Mechanical Engineer","civil and mechanical engineer":"Civil and Mechanical Engineer","municipal engineer":"Municipal Engineer","steam engineer":"Steam Engineer","electrical engineer":"Electrical Engineer","consulting engineer":"Consulting Engineer","mech eng":"Mechanical Engineer","engineer (steam)":"Steam Engineer","architect + surveyor":"Architect and Surveyor","borough surveyor, nottingham":"Borough Surveyor","borough surveyor of nottingham":"Borough Surveyor","building surveyor":"Surveyor","estate agent and surveyor":"Estate Agent and Surveyor","surveyor & valuer":"Surveyor","private means":"Private Means","living on own means":"Private Means","living on means":"Private Means","independant":"Private Means","independent":"Private Means","independent means":"Private Means","indep means":"Private Means","funds derived from property":"Private Means","ground rent and fundholder":"Private Means","property holder":"Private Means","holding public funds":"Private Means","unpaid domestic duties":"Unpaid Domestic Duties","domestic duties":"Unpaid Domestic Duties","household duties":"Unpaid Domestic Duties","home duties":"Unpaid Domestic Duties","house duties":"Unpaid Domestic Duties","home duty":"Unpaid Domestic Duties","housewife":"Unpaid Domestic Duties","house wife":"Unpaid Domestic Duties","house work":"Unpaid Domestic Duties","housework":"Unpaid Domestic Duties","wife":"Unpaid Domestic Duties","at home":"Unpaid Domestic Duties","no occ":"No Occupation","no occu":"No Occupation","no occup":"No Occupation","no occupation":"No Occupation","not occupied for a living":"No Occupation","unemployed":"No Occupation","scholar":"Scholar","school":"Scholar","book keeper":"Book-keeper","bookeeper":"Book-keeper","clerk":"Clerk","retired":"Retired","coachman":"Coachman","coachman (domestic)":"Coachman","coachman domestic":"Coachman","groom - coachman":"Coachman","chauffeur":"Chauffeur","chaffeur":"Chauffeur","chauffer":"Chauffeur","chauffeur (private)":"Chauffeur","private chauffeur":"Chauffeur","gardener chauffeur":"Gardener/Chauffeur","auctioneer":"Auctioneer","auctioneer stationer":"Auctioneer","auctioneer & valuer":"Auctioneer and Valuer","auctioner & valuers":"Auctioneer and Valuer","teacher":"Teacher","head teacher":"Head Teacher","school master":"Schoolmaster","school mistress":"Schoolmistress","headmaster of nottm high school":"Headmaster","governess":"Governess","timber merchant":"Timber Merchant","grocer":"Grocer","grocer (retired)":"Grocer (Retired)","retired grocer":"Grocer (Retired)","grocer's clerk":"Grocer's Clerk","grocers clerk":"Grocer's Clerk","leather manufacturer":"Leather Manufacturer","leather manufacturers":"Leather Manufacturer","leather merchant":"Leather Merchant","maid":"Maid","maid domestic":"Maid","author (horror fiction)":"Author","author (fiction)":"Author","captain, 112th regiment, 9th sherwood foresters":"Captain","retired grocer":"Grocer (Retired)","grocer (retired)":"Grocer (Retired)"};
const OCC_GROUP_SERVER = {"Domestic Servant":"Domestic Service","Housemaid":"Domestic Service","Under Housemaid":"Domestic Service","Cook":"Domestic Service","Parlourmaid":"Domestic Service","House Parlourmaid":"Domestic Service","Kitchenmaid":"Domestic Service","Lady's Maid":"Domestic Service","Housekeeper":"Domestic Service","Domestic Nurse":"Domestic Service","Nursemaid":"Domestic Service","Maid":"Domestic Service","Butler":"Domestic Service","Groom":"Domestic Service","Coachman":"Domestic Service","Chauffeur":"Domestic Service","Gardener":"Domestic Service","Gardener/Chauffeur":"Domestic Service","Caretaker":"Domestic Service","Charwoman":"Domestic Service","Park Keeper":"Domestic Service","Houseman":"Domestic Service","Betweenmaid":"Domestic Service","Private Means":"Household / Private Means","Unpaid Domestic Duties":"Household / Private Means","Paid Domestic Duties":"Household / Private Means","No Occupation":"Household / Private Means","Invalid":"Household / Private Means","Child":"Household / Private Means","Scholar":"Student / Scholar","Student":"Student / Scholar","Retired":"Retired","Lace Manufacturer":"Lace Industry","Lace Manufacturer (Retired)":"Lace Industry","Lace Dresser":"Lace Industry","Lace Dresser and Bleacher":"Lace Industry","Lace Dresser (Retired)":"Lace Industry","Lace Bleacher":"Lace Industry","Lace Bleacher (Retired)":"Lace Industry","Lace Merchant":"Lace Industry","Lace Merchant (Retired)":"Lace Industry","Lace Dresser and Magistrate":"Lace Industry","Plain and Spot Net Manufacturer":"Lace Industry","Lace Machine Builder":"Lace Industry","Lace Warehouse Manager":"Lace Industry","Lace Manufacturer and Inventor":"Lace Industry","Hosiery Manufacturer":"Hosiery & Textiles","Hosiery Manufacturer (Retired)":"Hosiery & Textiles","Hosier":"Hosiery & Textiles","Hosier (Retired)":"Hosiery & Textiles","Hosiery and Glove Manufacturer":"Hosiery & Textiles","Hosiery Machinery Manufacturer":"Hosiery & Textiles","Textile Machinery Manufacturer":"Hosiery & Textiles","Yarn Agent":"Hosiery & Textiles","Yarn Merchant":"Hosiery & Textiles","Yarn Merchant (Retired)":"Hosiery & Textiles","Yarn Manufacturer":"Hosiery & Textiles","Cotton Doubler":"Hosiery & Textiles","Draper":"Hosiery & Textiles","Draper's Clerk":"Hosiery & Textiles","Bleacher":"Hosiery & Textiles","Solicitor":"Law","Barrister":"Law","Solicitor and Notary Public":"Law","Law Student":"Law","Law Clerk":"Law","Surgeon":"Medicine","Physician":"Medicine","Medical Officer":"Medicine","Medical Practitioner":"Medicine","Nurse":"Medicine","Sick Nurse":"Medicine","Red Cross Nurse":"Medicine","Maternity Nurse":"Medicine","Chemist / Pharmacist":"Medicine","Dental Surgeon":"Medicine","Masseuse":"Medicine","Architect":"Architecture & Engineering","Architect (Retired)":"Architecture & Engineering","Architect and Surveyor":"Architecture & Engineering","Civil Engineer":"Architecture & Engineering","Mechanical Engineer":"Architecture & Engineering","Mining Engineer":"Architecture & Engineering","Chief Mechanical Engineer":"Architecture & Engineering","Civil and Mechanical Engineer":"Architecture & Engineering","Municipal Engineer":"Architecture & Engineering","Steam Engineer":"Architecture & Engineering","Electrical Engineer":"Architecture & Engineering","Consulting Engineer":"Architecture & Engineering","Borough Surveyor":"Architecture & Engineering","Surveyor":"Architecture & Engineering","Estate Agent and Surveyor":"Architecture & Engineering","Magistrate":"Public Life & Civic","Justice of the Peace":"Public Life & Civic","Alderman":"Public Life & Civic","Sheriff of Nottingham":"Public Life & Civic","Sheriff of London":"Public Life & Civic","High Sheriff":"Public Life & Civic","Mayor of Nottingham":"Public Life & Civic","Lord Mayor of Nottingham":"Public Life & Civic","Lord Mayor of London":"Public Life & Civic","Town Councillor":"Public Life & Civic","County Councillor":"Public Life & Civic","Member of Parliament":"Public Life & Civic","Deputy-Lieutenant":"Public Life & Civic","Army Officer":"Military","Soldier":"Military","Captain":"Military","Lieutenant-Colonel":"Military","Teacher":"Education","Head Teacher":"Education","Schoolmaster":"Education","Schoolmistress":"Education","Headmaster":"Education","Governess":"Education","Professor":"Education","Librarian":"Education","Instructress in Wood Carving":"Education","Author":"Arts & Culture","Composer":"Arts & Culture","Conductor":"Arts & Culture","Violinist":"Arts & Culture","Organist":"Arts & Culture","Photographer":"Arts & Culture","Folklorist":"Arts & Culture","Journalist":"Arts & Culture","Cricketer":"Arts & Culture","Wood Carver":"Arts & Culture","Artist":"Arts & Culture","Singer":"Arts & Culture","Publisher":"Arts & Culture","Bank Manager":"Trade & Commerce","Bank Clerk":"Trade & Commerce","Stockbroker":"Trade & Commerce","Auctioneer":"Trade & Commerce","Auctioneer and Valuer":"Trade & Commerce","Grocer":"Trade & Commerce","Grocer (Retired)":"Trade & Commerce","Wholesale Grocer":"Trade & Commerce","Timber Merchant":"Trade & Commerce","Timber Merchant (Retired)":"Trade & Commerce","Leather Manufacturer":"Trade & Commerce","Leather Merchant":"Trade & Commerce","Furniture Manufacturer":"Trade & Commerce","Cabinet Maker":"Trade & Commerce","Commission Agent":"Trade & Commerce","Wine & Spirit Merchant":"Trade & Commerce","Cigar Manufacturer":"Trade & Commerce","Paper Maker":"Trade & Commerce","Manufacturer":"Trade & Commerce","Manager":"Trade & Commerce","Managing Director":"Trade & Commerce","Company Chairman":"Trade & Commerce","Director":"Trade & Commerce","Book-keeper":"Trade & Commerce","Clerk":"Trade & Commerce","Typist":"Trade & Commerce","Cashier":"Trade & Commerce","Warehouseman":"Trade & Commerce"};
const OCC_GROUPS_LIST = ["Domestic Service","Lace Industry","Hosiery & Textiles","Law","Medicine","Architecture & Engineering","Trade & Commerce","Public Life & Civic","Military","Education","Arts & Culture","Student / Scholar","Household / Private Means","Retired"];

function serverNorm(raw) { return OCC_NORM_SERVER[(raw||'').toLowerCase().trim()] || (raw||'').trim(); }
function serverOccGroup(raw) { const n = serverNorm(raw); return OCC_GROUP_SERVER[n] || null; }

app.get('/api/occupation-groups', (req, res) => {
  res.json(OCC_GROUPS_LIST);
});

// GET /api/people/by-group/:group — people whose any occupation belongs to this group
app.get('/api/people/by-group/:group', async (req, res) => {
  if (!db) return res.json([]);
  try {
    const group = req.params.group;
    // Collect all raw strings (lower-cased) that map to this group
    const matchSet = new Set();
    for (const [raw, norm] of Object.entries(OCC_NORM_SERVER)) {
      if (OCC_GROUP_SERVER[norm] === group) { matchSet.add(raw); matchSet.add(norm.toLowerCase()); }
    }
    for (const [norm, g] of Object.entries(OCC_GROUP_SERVER)) {
      if (g === group) matchSet.add(norm.toLowerCase());
    }
    const matchArr = Array.from(matchSet);
    if (!matchArr.length) return res.json([]);
    const r = await db.query(`
      SELECT DISTINCT p.id, p.first_name, p.last_name, p.known_as, p.title, p.postnominals,
             p.born_year, p.died_year, p.photo_url,
             (SELECT ARRAY_AGG(DISTINCT o.occupation) FROM occupations o WHERE o.person_id=p.id AND o.occupation IS NOT NULL) AS occupations,
             (SELECT ARRAY_AGG(DISTINCT pid) FROM (
               SELECT ce.property_id AS pid FROM census_entries ce WHERE ce.person_id=p.id AND ce.property_id IS NOT NULL
               UNION SELECT pr.property_id AS pid FROM property_residents pr WHERE pr.person_id=p.id
             ) all_props) AS property_ids
      FROM people p
      WHERE EXISTS (SELECT 1 FROM occupations o WHERE o.person_id=p.id AND LOWER(o.occupation)=ANY($1))
         OR EXISTS (SELECT 1 FROM census_entries ce WHERE ce.person_id=p.id AND LOWER(ce.occupation_at_census)=ANY($1))
      ORDER BY p.last_name, p.first_name`, [matchArr]);
    res.json(r.rows.map(row => ({ ...row, property_names: (row.property_ids||[]).map(id => propName(id)) })));
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// GET /api/significant-places — list all places
app.get('/api/significant-places', async (req, res) => {
  if (!db) return res.json([]);
  try {
    const r = await db.query(`
      SELECT sp.*,
             ARRAY_AGG(DISTINCT pp.person_id) FILTER (WHERE pp.person_id IS NOT NULL) AS person_ids
      FROM significant_places sp
      LEFT JOIN people_places pp ON pp.place_id=sp.id
      GROUP BY sp.id ORDER BY sp.name`);
    res.json(r.rows);
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// ── Admin: People write routes ────────────────────────────────────────────────

// ── Changelog helper ─────────────────────────────────────────────────────────
async function logChange(entityType, entityId, req, action, field, oldVal, newVal) {
  if (!db) return;
  const username = req.session?.username || req.session?.userId || 'unknown';
  try {
    await db.query(
      `INSERT INTO change_log (entity_type, entity_id, username, action, field, old_value, new_value) VALUES ($1,$2,$3,$4,$5,$6,$7)`,
      [entityType, entityId, username, action, field || null, oldVal != null ? String(oldVal) : null, newVal != null ? String(newVal) : null]
    );
  } catch(e) { /* non-critical */ }
}

// ── Person links API ──────────────────────────────────────────────────────────
app.get('/api/person/:id/links', async (req, res) => {
  if (!db) return res.json([]);
  try {
    const r = await db.query('SELECT * FROM person_links WHERE person_id=$1 ORDER BY created_at', [parseInt(req.params.id)]);
    res.json(r.rows);
  } catch(e) { res.json([]); }
});

app.post('/api/person/:id/links', requireContributor, async (req, res) => {
  // authorization handled by requireContributor in the route signature
  if (!db) return res.status(503).json({ error: 'No DB' });
  const { title, url, link_type, notes } = req.body;
  if (!title || !url) return res.status(400).json({ error: 'title and url required' });
  try {
    const username = req.session.username || req.session.userId || 'unknown';
    const r = await db.query(
      'INSERT INTO person_links (person_id, title, url, link_type, notes, created_by) VALUES ($1,$2,$3,$4,$5,$6) RETURNING *',
      [parseInt(req.params.id), title, url, link_type || 'website', notes || null, username]
    );
    await logChange('person', parseInt(req.params.id), req, 'add_link', 'links', null, `${title}: ${url}`);
    res.json({ ok: true, link: r.rows[0] });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

app.delete('/api/person/:personId/links/:linkId', requireContributor, async (req, res) => {
  // authorization handled by requireContributor in the route signature
  if (!db) return res.status(503).json({ error: 'No DB' });
  try {
    const r = await db.query('DELETE FROM person_links WHERE id=$1 AND person_id=$2 RETURNING title,url', [parseInt(req.params.linkId), parseInt(req.params.personId)]);
    if (r.rows[0]) await logChange('person', parseInt(req.params.personId), req, 'delete_link', 'links', `${r.rows[0].title}: ${r.rows[0].url}`, null);
    res.json({ ok: true });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// ── Changelog API ─────────────────────────────────────────────────────────────
app.get('/api/changelog', requireAdmin, async (req, res) => {
  if (!db) return res.json([]);
  try {
    const limit = parseInt(req.query.limit) || 100;
    const entityType = req.query.entity_type;
    const entityId = req.query.entity_id;
    let q = 'SELECT * FROM change_log';
    const params = [];
    const wheres = [];
    if (entityType) { params.push(entityType); wheres.push(`entity_type=$${params.length}`); }
    if (entityId) { params.push(parseInt(entityId)); wheres.push(`entity_id=$${params.length}`); }
    if (wheres.length) q += ' WHERE ' + wheres.join(' AND ');
    params.push(limit);
    q += ` ORDER BY created_at DESC LIMIT $${params.length}`;
    const r = await db.query(q, params);
    res.json(r.rows);
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// ── Person add relationship ───────────────────────────────────────────────────
// Helper: infer sibling + grandparent relationships when a parent/child link is added
async function inferFamilyRelationships(db, personId, otherId, relType) {
  const safeInsert = (aId, bId, rel) => {
    if (aId === bId) return Promise.resolve();
    return db.query(
      `INSERT INTO people_relationships (person_a_id, person_b_id, relationship) VALUES ($1,$2,$3) ON CONFLICT DO NOTHING`,
      [aId, bId, rel]
    );
  };
  // Normalise: who is the parent, who is the child?
  // Relationship types are stored as e.g. 'parent_of', 'child_of', 'sibling_of'
  let parentId, childId;
  if (relType === 'parent_of') { parentId = personId; childId = otherId; }       // personId is parent of otherId
  else if (relType === 'child_of') { parentId = otherId; childId = personId; }   // personId is child of otherId
  else return; // only infer for parent/child links

  // Existing children of parentId → siblings of childId
  const siblings = await db.query(
    `SELECT person_b_id AS sid FROM people_relationships WHERE person_a_id=$1 AND relationship='parent_of' AND person_b_id<>$2
     UNION
     SELECT person_a_id AS sid FROM people_relationships WHERE person_b_id=$1 AND relationship='child_of' AND person_a_id<>$2`,
    [parentId, childId]
  );
  for (const { sid } of siblings.rows) {
    await safeInsert(childId, sid, 'sibling_of');
    await safeInsert(sid, childId, 'sibling_of');
  }

  // Parents of parentId → grandparents of childId
  const grandparents = await db.query(
    `SELECT person_b_id AS gpid FROM people_relationships WHERE person_a_id=$1 AND relationship='child_of'
     UNION
     SELECT person_a_id AS gpid FROM people_relationships WHERE person_b_id=$1 AND relationship='parent_of'`,
    [parentId]
  );
  for (const { gpid } of grandparents.rows) {
    await safeInsert(childId, gpid, 'grandchild_of');
    await safeInsert(gpid, childId, 'grandparent_of');
  }
}

app.post('/api/person/:id/relationship', requireContributor, async (req, res) => {
  // authorization handled by requireContributor in the route signature
  if (!db) return res.status(503).json({ error: 'No DB' });
  const { other_person_id, relationship_type } = req.body;
  if (!other_person_id || !relationship_type) return res.status(400).json({ error: 'other_person_id and relationship_type required' });
  try {
    const r = await db.query(
      `INSERT INTO people_relationships (person_a_id, person_b_id, relationship) VALUES ($1,$2,$3)
       ON CONFLICT DO NOTHING RETURNING *`,
      [parseInt(req.params.id), parseInt(other_person_id), relationship_type]
    );
    await logChange('person', parseInt(req.params.id), req, 'add_relationship', 'relationships', null, `${relationship_type} with person ${other_person_id}`);
    // Auto-infer sibling and grandparent links
    await inferFamilyRelationships(db, parseInt(req.params.id), parseInt(other_person_id), relationship_type);
    res.json({ ok: true, relationship: r.rows[0] });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

app.delete('/api/person/:id/relationship/:relId', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  try {
    const relId = parseInt(req.params.relId);
    const personId = parseInt(req.params.id);
    // Verify this relationship involves the stated person (security check)
    const check = await db.query(
      'SELECT id FROM people_relationships WHERE id=$1 AND (person_a_id=$2 OR person_b_id=$2)',
      [relId, personId]
    );
    if (!check.rows.length) return res.status(404).json({ error: 'Relationship not found' });
    await db.query('DELETE FROM people_relationships WHERE id=$1', [relId]);
    await logChange('person', personId, req, 'delete_relationship', 'relationships', null, `Deleted relationship id ${relId}`);
    res.json({ ok: true });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// ── Person media gallery ──────────────────────────────────────────────────────
app.get('/api/person/:id/media', async (req, res) => {
  if (!db) return res.json([]);
  try {
    const r = await db.query('SELECT * FROM person_media WHERE person_id=$1 ORDER BY created_at', [parseInt(req.params.id)]);
    res.json(r.rows);
  } catch(e) { res.json([]); }
});

app.post('/api/person/:id/media', requireContributor, (req, res, next) => {
  // authorization handled by requireContributor in the route signature
  next();
}, (req, res) => {
  const personId = parseInt(req.params.id);
  // Held in memory, not written to the container's disk. Railway rebuilds the
  // container on every deploy, so anything saved under data/photos/ is gone the
  // next time the site ships — which is exactly what happened to the plaque
  // photographs. Portraits and videos already went to Cloudinary; this is the
  // one upload path that did not.
  multer({ storage: multer.memoryStorage(), limits: { fileSize: 10 * 1024 * 1024 } })
    .single('file')(req, res, async (err) => {
    if (err) return res.status(400).json({ error: err.message });
    if (!req.file) return res.status(400).json({ error: 'No file' });
    const stamped = `person-${personId}-media-${Date.now()}${path.extname(req.file.originalname)}`;
    let url;
    try {
      url = await uploadMedia(req.file.buffer, stamped, req.file.mimetype);
    } catch (e) {
      return res.status(500).json({ error: 'Upload failed: ' + e.message });
    }
    const caption = req.body.caption || '';
    const isDoc = /\.(pdf|doc|docx|txt)$/i.test(req.file.originalname);
    const media_type = isDoc ? 'document' : 'photo';
    try {
      if (db) {
        const r = await db.query(
          'INSERT INTO person_media (person_id, url, caption, media_type, filename) VALUES ($1,$2,$3,$4,$5) RETURNING *',
          [personId, url, caption, media_type, req.file.originalname]
        );
        res.json({ ok: true, media: r.rows[0] });
      } else {
        res.json({ ok: true, media: { url, caption, media_type, filename: req.file.originalname } });
      }
    } catch(e) { res.status(500).json({ error: e.message }); }
  });
});

app.delete('/api/person/:personId/media/:mediaId', requireAdmin, async (req, res) => {
  if (!db) return res.json({ ok: true });
  try {
    const r = await db.query('DELETE FROM person_media WHERE id=$1 AND person_id=$2 RETURNING url', [parseInt(req.params.mediaId), parseInt(req.params.personId)]);
    if (r.rows[0]) {
      try { fs.unlinkSync(path.join(__dirname, 'public', r.rows[0].url)); } catch(e) {}
    }
    res.json({ ok: true });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// Upload a video file for a person
app.post('/api/person/:id/media/video', requireContributor, (req, res) => {
  // authorization handled by requireContributor in the route signature
  const personId = parseInt(req.params.id);
  const chunks = [];
  let size = 0;
  req.on('data', c => { size += c.length; if (size > 200 * 1024 * 1024) req.destroy(new Error('File too large (max 200MB)')); else chunks.push(c); });
  req.on('end', async () => {
    try {
      const buf = Buffer.concat(chunks);
      if (buf.length < 100) return res.status(400).json({ error: 'Empty file' });
      const origName = (req.headers['x-filename'] || `video_${Date.now()}.mp4`).replace(/[^a-z0-9._-]/gi, '_');
      const filename = `person-${personId}_vid_${Date.now()}_${origName}`;
      const url = await uploadVideo(buf, filename);
      const caption = req.headers['x-caption'] || '';
      if (db) {
        const r = await db.query(
          'INSERT INTO person_media (person_id, url, caption, media_type, filename) VALUES ($1,$2,$3,$4,$5) RETURNING *',
          [personId, url, caption, 'video', origName]
        );
        res.json({ ok: true, media: r.rows[0] });
      } else {
        res.json({ ok: true, media: { url, caption, media_type: 'video', filename: origName } });
      }
    } catch(e) { res.status(500).json({ error: e.message }); }
  });
  req.on('error', e => res.status(500).json({ error: e.message }));
});

// ── Person photo upload (any logged-in user or admin) ────────────────────────
app.post('/api/person/:id/photo', requireContributor, (req, res, next) => {
  if (!req.session || (!req.session.isAdmin && !req.session.userId && !req.session.username)) {
    return res.status(401).json({ error: 'Login required' });
  }
  next();
}, (req, res) => {
  const personId = parseInt(req.params.id);
  multer({ storage: multer.memoryStorage(), limits: { fileSize: 5 * 1024 * 1024 } }).single('photo')(req, res, async (err) => {
    if (err) return res.status(400).json({ error: err.message });
    if (!req.file) return res.status(400).json({ error: 'No file' });
    try {
      const filename = `person-${personId}-${Date.now()}${path.extname(req.file.originalname||'.jpg')}`;
      const url = await uploadPhoto(req.file.buffer, filename, req.file.mimetype);
      if (db) await db.query('UPDATE people SET photo_url=$1 WHERE id=$2', [url, personId]).catch(()=>{});
      res.json({ ok: true, url });
    } catch(e) { res.status(500).json({ error: e.message }); }
  });
});

app.post('/api/person', requireContributor, async (req, res) => {
  // authorization handled by requireContributor in the route signature
  if (!db) return res.status(503).json({ error: 'DB not available' });
  try {
    const { first_name, last_name, known_as, born_date, born_year, born_place,
            died_date, died_year, died_place, bio, wikipedia_url, photo_url } = req.body;
    const r = await db.query(
      `INSERT INTO people (first_name,last_name,known_as,born_date,born_year,born_place,died_date,died_year,died_place,bio,wikipedia_url,photo_url)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12) RETURNING id`,
      [first_name,last_name,known_as,born_date,born_year,born_place,died_date,died_year,died_place,bio,wikipedia_url,photo_url]
    );
    res.json({ ok: true, id: r.rows[0].id });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

app.patch('/api/person/:id', requireContributor, async (req, res) => {
  // Allow admin OR logged-in users to edit
  // authorization handled by requireContributor in the route signature
  if (!db) return res.status(503).json({ error: 'DB not available' });
  try {
    const id = parseInt(req.params.id);
    const fields = req.body;
    const keys = Object.keys(fields).filter(k => ['first_name','last_name','known_as','maiden_name','title','postnominals','born_date','born_year','born_place','died_date','died_year','died_place','bio','wikipedia_url','photo_url','grave_location','grave_number','sex'].includes(k));
    if (!keys.length) return res.status(400).json({ error: 'No valid fields' });
    // Get old values for changelog
    // Setting sex here is an individual judgement — record that, so a later
    // forename pass leaves it alone.
    if (Object.prototype.hasOwnProperty.call(fields, 'sex')) {
      if (fields.sex !== 'M' && fields.sex !== 'F' && fields.sex !== null && fields.sex !== '') {
        return res.status(400).json({ error: "sex must be 'M', 'F' or empty" });
      }
      if (fields.sex === '') fields.sex = null;
      await db.query(
        `UPDATE people SET sex_source=$2 WHERE id=$1`,
        [id, fields.sex ? 'set on the person record by ' + (req.session.username || 'contributor') : null]);
    }
    const old = await db.query(`SELECT ${keys.join(',')} FROM people WHERE id=$1`, [id]);
    const sets = keys.map((k,i) => `${k}=$${i+2}`).join(',');
    await db.query(`UPDATE people SET ${sets} WHERE id=$1`, [id, ...keys.map(k=>fields[k])]);
    // Log each changed field
    for (const k of keys) {
      const oldVal = old.rows[0]?.[k];
      const newVal = fields[k];
      if (String(oldVal) !== String(newVal)) await logChange('person', id, req, 'edit', k, oldVal, newVal);
    }
    res.json({ ok: true });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/person/:id/occupation', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  try {
    const { occupation, from_year, to_year, employer, notes } = req.body;
    const r = await db.query(
      `INSERT INTO occupations (person_id,occupation,from_year,to_year,employer,notes) VALUES ($1,$2,$3,$4,$5,$6) RETURNING id`,
      [parseInt(req.params.id), occupation, from_year||null, to_year||null, employer||null, notes||null]
    );
    res.json({ ok: true, id: r.rows[0].id });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

app.delete('/api/occupation/:occId', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  try {
    const r = await db.query('DELETE FROM occupations WHERE id=$1 RETURNING id', [parseInt(req.params.occId)]);
    if (!r.rowCount) return res.status(404).json({ error: 'Occupation not found' });
    res.json({ ok: true });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/person/:id/census', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  try {
    const { property_id, address, census_year, relationship, age_at_census, occupation_at_census, source } = req.body;
    const r = await db.query(
      `INSERT INTO census_entries (person_id,property_id,address,census_year,relationship,age_at_census,occupation_at_census,source)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8) RETURNING id`,
      [parseInt(req.params.id), property_id||null, address||null, census_year, relationship||null, age_at_census||null, occupation_at_census||null, source||null]
    );
    res.json({ ok: true, id: r.rows[0].id });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

app.patch('/api/census-entry/:entryId', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  try {
    const { relationship, occupation_at_census, age_at_census, birth_place, census_year,
            property_id } = req.body;
    // Moving a record to another property. /api/census/resolve only ever fills a
    // blank — it carries "AND property_id IS NULL" — so a record filed against
    // the wrong house could not be moved at all. Sending property_id here does
    // it; sending null explicitly unfiles it, back to the unresolved queue.
    if (property_id !== undefined) {
      const target = property_id === null || property_id === '' ? null : parseInt(property_id, 10);
      if (target !== null && !Number.isInteger(target)) {
        return res.status(400).json({ error: 'property_id must be a number, or null to unfile' });
      }
      await db.query(`UPDATE census_entries SET property_id=$1,
                        unresolved_address = CASE WHEN $1::int IS NULL THEN unresolved_address ELSE NULL END
                      WHERE id=$2`,
        [target, parseInt(req.params.entryId)]);
    }
    await db.query(
      `UPDATE census_entries SET
        relationship = COALESCE($1, relationship),
        occupation_at_census = COALESCE($2, occupation_at_census),
        age_at_census = COALESCE($3, age_at_census),
        birth_place = COALESCE($4, birth_place),
        census_year = COALESCE($5, census_year)
       WHERE id = $6`,
      [relationship ?? null, occupation_at_census ?? null,
       age_at_census ? parseInt(age_at_census) : null,
       birth_place ?? null,
       census_year ? parseInt(census_year) : null,
       parseInt(req.params.entryId)]
    );
    res.json({ ok: true });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

app.delete('/api/census-entry/:entryId', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  try {
    const r = await db.query('DELETE FROM census_entries WHERE id=$1 RETURNING id', [parseInt(req.params.entryId)]);
    if (!r.rowCount) return res.status(404).json({ error: 'Entry not found' });
    res.json({ ok: true });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/significant-place', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  try {
    const { name, location, place_type, description, wikipedia_url, lat, lng } = req.body;
    const r = await db.query(
      `INSERT INTO significant_places (name,location,place_type,description,wikipedia_url,lat,lng) VALUES ($1,$2,$3,$4,$5,$6,$7) RETURNING id`,
      [name,location||null,place_type||null,description||null,wikipedia_url||null,lat||null,lng||null]
    );
    res.json({ ok: true, id: r.rows[0].id });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/person/:id/place', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  try {
    const { place_id, connection } = req.body;
    await db.query(`INSERT INTO people_places (person_id,place_id,connection) VALUES ($1,$2,$3)`,
      [parseInt(req.params.id), place_id, connection||null]);
    res.json({ ok: true });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/bibliography', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  try {
    const { author_person_id, title, year, publisher, notes, url, property_id } = req.body;
    const r = await db.query(
      `INSERT INTO bibliography (author_person_id,title,year,publisher,notes,url,property_id) VALUES ($1,$2,$3,$4,$5,$6,$7) RETURNING id`,
      [author_person_id||null,title,year||null,publisher||null,notes||null,url||null,property_id||null]
    );
    res.json({ ok: true, id: r.rows[0].id });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// ── Seed endpoint (admin) — load structured people data for a property ─────────
app.post('/api/seed/property/:propId/people', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  // req.body: { people: [...], places: [...], bibliography: [...] }
  // Each person: { first_name, last_name, known_as, born_*, died_*, bio, wikipedia_url,
  //               occupations: [{occupation,from_year,to_year,employer,notes}],
  //               census_entries: [{census_year,relationship,age_at_census,occupation_at_census,source}] }
  const client = await db.connect();
  try {
    await client.query('BEGIN');
    const propId = parseInt(req.params.propId);
    const { people: peopleData = [], places: placesData = [], bibliography: bibData = [] } = req.body;
    const idMap = {}; // name → db id

    // Upsert each person
    for (const p of peopleData) {
      // Check if person already exists by name match
      const existing = await client.query(
        `SELECT id FROM people WHERE LOWER(first_name)=LOWER($1) AND LOWER(last_name)=LOWER($2) LIMIT 1`,
        [p.first_name, p.last_name || '']
      );
      let personId;
      if (existing.rows[0]) {
        personId = existing.rows[0].id;
        await client.query(
          `UPDATE people SET known_as=COALESCE($2,known_as), born_date=COALESCE($3,born_date),
           born_year=COALESCE($4,born_year), born_place=COALESCE($5,born_place),
           died_date=COALESCE($6,died_date), died_year=COALESCE($7,died_year),
           died_place=COALESCE($8,died_place), bio=COALESCE($9,bio), wikipedia_url=COALESCE($10,wikipedia_url),
           updated_at=NOW() WHERE id=$1`,
          [personId, p.known_as||null, p.born_date||null, p.born_year||null, p.born_place||null,
           p.died_date||null, p.died_year||null, p.died_place||null, p.bio||null, p.wikipedia_url||null]
        );
      } else {
        const r = await client.query(
          `INSERT INTO people (first_name,last_name,known_as,born_date,born_year,born_place,died_date,died_year,died_place,bio,wikipedia_url)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11) RETURNING id`,
          [p.first_name,p.last_name||null,p.known_as||null,p.born_date||null,p.born_year||null,
           p.born_place||null,p.died_date||null,p.died_year||null,p.died_place||null,p.bio||null,p.wikipedia_url||null]
        );
        personId = r.rows[0].id;
      }
      idMap[`${p.first_name} ${p.last_name||''}`.trim()] = personId;

      // Upsert occupations
      for (const occ of (p.occupations || [])) {
        const eOcc = await client.query(
          `SELECT id FROM occupations WHERE person_id=$1 AND LOWER(occupation)=LOWER($2) LIMIT 1`,
          [personId, occ.occupation]
        );
        if (!eOcc.rows[0]) {
          await client.query(
            `INSERT INTO occupations (person_id,occupation,from_year,to_year,employer,notes) VALUES ($1,$2,$3,$4,$5,$6)`,
            [personId, occ.occupation, occ.from_year||null, occ.to_year||null, occ.employer||null, occ.notes||null]
          );
        }
      }

      // Upsert census entries — use ce.property_id if provided, otherwise fall back to the seed's propId
      for (const ce of (p.census_entries || [])) {
        const cePropId = ce.property_id || propId;
        const eCe = await client.query(
          `SELECT id FROM census_entries WHERE person_id=$1 AND property_id=$2 AND census_year=$3 LIMIT 1`,
          [personId, cePropId, ce.census_year]
        );
        if (!eCe.rows[0]) {
          await client.query(
            `INSERT INTO census_entries (person_id,property_id,census_year,relationship,age_at_census,occupation_at_census,source)
             VALUES ($1,$2,$3,$4,$5,$6,$7)`,
            [personId, cePropId, ce.census_year, ce.relationship||null, ce.age_at_census||null, ce.occupation_at_census||null, ce.source||null]
          );
        }
      }
    }

    // Wire up relationships now all IDs are known
    for (const p of peopleData) {
      const aId = idMap[`${p.first_name} ${p.last_name||''}`.trim()];
      if (!aId) continue;
      for (const rel of (p.relationships || [])) {
        const bId = idMap[rel.name];
        if (!bId) continue;
        await client.query(
          `INSERT INTO people_relationships (person_a_id,person_b_id,relationship,notes) VALUES ($1,$2,$3,$4) ON CONFLICT DO NOTHING`,
          [aId, bId, rel.type, rel.notes||null]
        );
      }
    }

    // Upsert significant places
    const placeIdMap = {};
    for (const pl of placesData) {
      const ePl = await client.query(`SELECT id FROM significant_places WHERE LOWER(name)=LOWER($1) LIMIT 1`, [pl.name]);
      let placeId;
      if (ePl.rows[0]) {
        placeId = ePl.rows[0].id;
      } else {
        const r = await client.query(
          `INSERT INTO significant_places (name,location,place_type,description,wikipedia_url,lat,lng) VALUES ($1,$2,$3,$4,$5,$6,$7) RETURNING id`,
          [pl.name,pl.location||null,pl.place_type||null,pl.description||null,pl.wikipedia_url||null,pl.lat||null,pl.lng||null]
        );
        placeId = r.rows[0].id;
      }
      placeIdMap[pl.name] = placeId;
      // Link to property
      const ePP = await client.query(`SELECT id FROM property_places WHERE property_id=$1 AND place_id=$2 LIMIT 1`, [propId, placeId]);
      if (!ePP.rows[0]) {
        await client.query(`INSERT INTO property_places (property_id,place_id,connection) VALUES ($1,$2,$3)`, [propId, placeId, pl.property_connection||null]);
      }
      // Link to people
      for (const pLink of (pl.person_connections || [])) {
        const pId = idMap[pLink.person];
        if (!pId) continue;
        const ePPL = await client.query(`SELECT id FROM people_places WHERE person_id=$1 AND place_id=$2 LIMIT 1`, [pId, placeId]);
        if (!ePPL.rows[0]) {
          await client.query(`INSERT INTO people_places (person_id,place_id,connection) VALUES ($1,$2,$3)`, [pId, placeId, pLink.connection||null]);
        }
      }
    }

    // Upsert bibliography
    for (const bk of bibData) {
      const authorId = bk.author_name ? idMap[bk.author_name] : null;
      const eBk = await client.query(`SELECT id FROM bibliography WHERE LOWER(title)=LOWER($1) AND COALESCE(author_person_id,0)=COALESCE($2,0) LIMIT 1`, [bk.title, authorId]);
      if (!eBk.rows[0]) {
        await client.query(
          `INSERT INTO bibliography (author_person_id,title,year,publisher,notes,url,property_id) VALUES ($1,$2,$3,$4,$5,$6,$7)`,
          [authorId,bk.title,bk.year||null,bk.publisher||null,bk.notes||null,bk.url||null,propId]
        );
      }
    }

    await client.query('COMMIT');
    res.json({ ok: true, ids: idMap });
  } catch(e) {
    await client.query('ROLLBACK');
    res.status(500).json({ error: e.message });
  } finally { client.release(); }
});

// ── Static ────────────────────────────────────────────────────────────────────
app.use(express.static(path.join(__dirname, 'public')));
app.get('/people', (req, res) => res.sendFile(path.join(__dirname, 'public', 'people.html')));
app.get('/dashboard', (req, res) => res.sendFile(path.join(__dirname, 'public', 'dashboard.html')));
app.get('/stats', (req, res) => res.sendFile(path.join(__dirname, 'public', 'stats.html')));
app.get('/my-contributions', (req, res) => res.sendFile(path.join(__dirname, 'public', 'my-contributions.html')));
app.get('/watchlist', (req, res) => res.sendFile(path.join(__dirname, 'public', 'watchlist.html')));
app.get('/admin/users', (req, res) => {
  // Serve the page — it checks auth itself via /api/admin/users fetch
  if (req.session && req.session.isAdmin) {
    return res.sendFile(path.join(__dirname, 'public', 'admin-users.html'));
  }
  // Not authenticated — redirect to map with login prompt
  res.redirect('/?login=1');
});
app.get('/family-tree', (req, res) => res.sendFile(path.join(__dirname, 'public', 'family-tree.html')));
app.get('/architects', (req, res) => res.sendFile(path.join(__dirname, 'public', 'architects.html')));
app.get('/significant', (req, res) => res.sendFile(path.join(__dirname, 'public', 'significant.html')));
app.get('/gazette-review', (req, res) => res.sendFile(path.join(__dirname, 'public', 'gazette-review.html')));
app.get('/name-sex', (req, res) => res.sendFile(path.join(__dirname, 'public', 'name-sex.html')));
app.get('/wikidata-review', (req, res) => res.sendFile(path.join(__dirname, 'public', 'wikidata-review.html')));
app.get('/crowding', (req, res) => res.sendFile(path.join(__dirname, 'public', 'crowding.html')));
app.get('/reassign', (req, res) => res.sendFile(path.join(__dirname, 'public', 'reassign.html')));
app.get('/unfiled', (req, res) => res.sendFile(path.join(__dirname, 'public', 'unfiled.html')));
app.get('/duplicates', (req, res) => res.sendFile(path.join(__dirname, 'public', 'duplicates.html')));
app.get('/archive', (req, res) => res.sendFile(path.join(__dirname, 'public', 'archive.html')));
app.get('/research', (req, res) => res.sendFile(path.join(__dirname, 'public', 'research.html')));
app.get('/join', (req, res) => res.sendFile(path.join(__dirname, 'public', 'join.html')));
app.get('/tasks', (req, res) => res.sendFile(path.join(__dirname, 'public', 'tasks.html')));
app.get('/osm', (req, res) => res.sendFile(path.join(__dirname, 'public', 'osm.html')));
app.get('/admin', (req, res) => res.sendFile(path.join(__dirname, 'public', 'admin.html')));
app.get('/listings', (req, res) => res.sendFile(path.join(__dirname, 'public', 'listings.html')));
app.get('/architects/:type/:id', (req, res) => res.sendFile(path.join(__dirname, 'public', 'architects.html')));
app.get('/architects/:id', (req, res) => res.sendFile(path.join(__dirname, 'public', 'architects.html')));

// ── The working list ──────────────────────────────────────────────────────────
// Written into data/tasks.json so a deploy carries it, ticked off in the site.
// Birth places the geocoder could not place, positioned by hand in
// data/geocode_manual.json so they show on the Origins map. Never overwrites a
// place the geocoder found, or one somebody placed by hand in the database. Rows
// from the file carry its name in corrected_from, so correcting the file
// corrects them.
async function seedGeocodeManual() {
  const SRC = 'data/geocode_manual.json';
  const file = path.join(__dirname, 'data', 'geocode_manual.json');
  if (!fs.existsSync(file)) return;
  let doc;
  try { doc = JSON.parse(fs.readFileSync(file, 'utf8')); }
  catch (e) { console.warn('geocode_manual.json is not valid JSON:', e.message); return; }
  let placed = 0, failed = 0, firstError = null;
  for (const p of (doc.places || [])) {
    const lat = Number(p.lat), lng = Number(p.lng);
    if (!p.place_text || !Number.isFinite(lat) || !Number.isFinite(lng)) continue;
    try {
      const r = await db.query(
        `INSERT INTO geocode_cache (place_text, lat, lng, formatted_address, status, corrected_from)
         VALUES ($1,$2,$3,$4,'manual',$5)
         ON CONFLICT (place_text) DO UPDATE
           SET lat=EXCLUDED.lat, lng=EXCLUDED.lng, formatted_address=EXCLUDED.formatted_address,
               status='manual', corrected_from=EXCLUDED.corrected_from, queried_at=NOW()
         WHERE geocode_cache.status NOT IN ('found','manual')
            OR (geocode_cache.corrected_from = EXCLUDED.corrected_from
                AND (geocode_cache.lat IS DISTINCT FROM EXCLUDED.lat
                     OR geocode_cache.lng IS DISTINCT FROM EXCLUDED.lng
                     OR geocode_cache.formatted_address IS DISTINCT FROM EXCLUDED.formatted_address))
         RETURNING place_text`,
        [p.place_text.trim(), lat, lng, p.label || null, SRC]);
      if (r.rows.length) placed++;
    } catch (e) { failed++; if (!firstError) firstError = `${p.place_text}: ${e.message}`; }
  }
  if (placed) console.log(`Geocode: ${placed} birth place(s) placed by hand from ${SRC}`);
  if (failed) console.warn(`Geocode: ${failed} place(s) from ${SRC} could not be saved — first: ${firstError}`);
}

async function seedTasks() {
  const file = path.join(__dirname, 'data', 'tasks.json');
  if (!fs.existsSync(file)) return;
  let doc;
  try { doc = JSON.parse(fs.readFileSync(file, 'utf8')); }
  catch (e) { console.warn('tasks.json is not valid JSON:', e.message); return; }
  let added = 0, refreshed = 0;
  for (const [i, t] of (doc.tasks || []).entries()) {
    if (!t.slug || !t.title) continue;
    try {
      const r = await db.query(
        `INSERT INTO tasks (slug, area, title, detail, size, link, sort_order, created_by)
         VALUES ($1,$2,$3,$4,$5,$6,$7,'seed') ON CONFLICT (slug) DO NOTHING RETURNING id`,
        [t.slug, t.area || null, t.title, t.detail || null, t.size || null, t.link || null, i]);
      if (r.rows.length) { added++; continue; }
      // Refresh the wording only while nobody has ticked or edited it.
      const upd = await db.query(
        `UPDATE tasks SET area=$2, title=$3, detail=$4, size=$5, link=$6, sort_order=$7
          WHERE slug=$1 AND done=FALSE AND edited_at IS NULL
            AND (area IS DISTINCT FROM $2 OR title IS DISTINCT FROM $3
                 OR detail IS DISTINCT FROM $4 OR size IS DISTINCT FROM $5
                 OR link IS DISTINCT FROM $6 OR sort_order IS DISTINCT FROM $7) RETURNING id`,
        [t.slug, t.area || null, t.title, t.detail || null, t.size || null, t.link || null, i]);
      if (upd.rows.length) refreshed++;
    } catch (e) { console.warn('task', t.slug, e.message); }
  }
  if (added || refreshed) console.log(`Tasks: ${added} added, ${refreshed} refreshed`);
}

app.get('/api/tasks', async (req, res) => {
  if (!db) return res.json({ tasks: [] });
  try {
    const r = await db.query(
      `SELECT id, slug, area, title, detail, size, link, done, done_by, done_at, created_by
         FROM tasks ORDER BY done, sort_order, id`);
    res.json({ tasks: r.rows });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/tasks', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  const title = String((req.body && req.body.title) || '').trim();
  if (!title) return res.status(400).json({ error: 'A task needs a title' });
  const who = (await getResearchKey(req.session)) || 'someone';
  try {
    const r = await db.query(
      `INSERT INTO tasks (area, title, detail, size, link, created_by, sort_order)
       VALUES ($1,$2,$3,$4,$5,$6,999) RETURNING id`,
      [req.body.area || null, title, (req.body.detail || '').trim() || null,
       req.body.size || null, (req.body.link || '').trim() || null, who]);
    res.json({ ok: true, id: r.rows[0].id });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.patch('/api/tasks/:id', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  const id = parseInt(req.params.id, 10);
  if (!Number.isInteger(id)) return res.status(400).json({ error: 'Not a task number' });
  const who = (await getResearchKey(req.session)) || 'someone';
  const b = req.body || {};
  try {
    if (b.done !== undefined) {
      await db.query(
        b.done ? `UPDATE tasks SET done=TRUE, done_by=$2, done_at=NOW() WHERE id=$1`
               : `UPDATE tasks SET done=FALSE, done_by=NULL, done_at=NULL WHERE id=$1`,
        b.done ? [id, who] : [id]);
    }
    const sets = [], vals = [id];
    for (const k of ['title', 'detail', 'area', 'size', 'link']) {
      if (b[k] !== undefined) { vals.push(String(b[k] || '').trim() || null); sets.push(`${k}=$${vals.length}`); }
    }
    if (sets.length) await db.query(`UPDATE tasks SET ${sets.join(', ')}, edited_at=NOW() WHERE id=$1`, vals);
    res.json({ ok: true });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.delete('/api/tasks/:id', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  try {
    await db.query(`DELETE FROM tasks WHERE id=$1`, [parseInt(req.params.id, 10)]);
    res.json({ ok: true });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// ── Research questions ────────────────────────────────────────────────────────
// The record has questions in it that no amount of reading will settle: which
// house a name belongs to, whether a building still stands, what a plaque says.
// They are written into data/research_questions.json so they arrive with a
// deploy, and a contributor claims one to say they are looking into it.
async function seedResearchQuestions() {
  const file = path.join(__dirname, 'data', 'research_questions.json');
  if (!fs.existsSync(file)) return;
  let doc;
  try { doc = JSON.parse(fs.readFileSync(file, 'utf8')); }
  catch (e) { console.warn('research_questions.json is not valid JSON:', e.message); return; }
  let added = 0, refreshed = 0;
  for (const q of (doc.questions || [])) {
    if (!q.slug || !q.title) continue;
    try {
      const r = await db.query(
        `INSERT INTO research_questions (slug, title, detail, kind, property_id, person_id, created_by)
         VALUES ($1,$2,$3,$4,$5,$6,'seed')
         ON CONFLICT (slug) DO NOTHING RETURNING id`,
        [q.slug, q.title, q.detail || null, q.kind || null,
         q.property_id || null, q.person_id || null]);
      if (r.rows.length) { added++; continue; }
      // Already there. Refresh the wording only while nobody has touched it by
      // hand — an edit or an answer in the site is worth more than the file.
      const upd = await db.query(
        `UPDATE research_questions
            SET title=$2, detail=$3, kind=$4, property_id=$5, person_id=$6
          WHERE slug=$1 AND edited_at IS NULL AND status='open'
            AND (title IS DISTINCT FROM $2 OR detail IS DISTINCT FROM $3
                 OR kind IS DISTINCT FROM $4 OR property_id IS DISTINCT FROM $5
                 OR person_id IS DISTINCT FROM $6) RETURNING id`,
        [q.slug, q.title, q.detail || null, q.kind || null,
         q.property_id || null, q.person_id || null]);
      if (upd.rows.length) refreshed++;
    } catch (e) { console.warn('research question', q.slug, e.message); }
  }
  if (added || refreshed) console.log(`Research questions: ${added} added, ${refreshed} refreshed`);
}

app.get('/api/research-questions', async (req, res) => {
  if (!db) return res.json({ questions: [] });
  try {
    const qs = await db.query(
      `SELECT id, slug, title, detail, kind, property_id, person_id, status,
              answer, answered_by, answered_at, created_by, created_at
         FROM research_questions
        ORDER BY (status = 'answered'), id`);
    const cl = await db.query(
      `SELECT question_id, username, note, started_at FROM research_claims ORDER BY started_at`);
    const by = {};
    for (const c of cl.rows) (by[c.question_id] = by[c.question_id] || []).push(c);
    res.json({ questions: qs.rows.map(q => ({ ...q, claims: by[q.id] || [] })) });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/research-questions', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  const title = String((req.body && req.body.title) || '').trim();
  if (!title) return res.status(400).json({ error: 'A question needs a title' });
  const who = (await getResearchKey(req.session)) || 'someone';
  try {
    const r = await db.query(
      `INSERT INTO research_questions (title, detail, kind, property_id, person_id, created_by)
       VALUES ($1,$2,$3,$4,$5,$6) RETURNING id`,
      [title, (req.body.detail || '').trim() || null, req.body.kind || null,
       parseInt(req.body.property_id, 10) || null, parseInt(req.body.person_id, 10) || null, who]);
    res.json({ ok: true, id: r.rows[0].id });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.patch('/api/research-questions/:id', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  const id = parseInt(req.params.id, 10);
  if (!Number.isInteger(id)) return res.status(400).json({ error: 'Not a question number' });
  const who = (await getResearchKey(req.session)) || 'someone';
  const b = req.body || {};
  try {
    if (b.answer !== undefined) {
      const answer = String(b.answer || '').trim();
      if (!answer) {
        // Reopening: the answer goes, the question comes back.
        await db.query(
          `UPDATE research_questions SET status='open', answer=NULL, answered_by=NULL,
                  answered_at=NULL WHERE id=$1`, [id]);
      } else {
        await db.query(
          `UPDATE research_questions SET status='answered', answer=$2, answered_by=$3,
                  answered_at=NOW() WHERE id=$1`, [id, answer, who]);
      }
    }
    const sets = [], vals = [id];
    for (const [k, col] of [['title','title'],['detail','detail'],['kind','kind']]) {
      if (b[k] !== undefined) { vals.push(String(b[k] || '').trim() || null); sets.push(`${col}=$${vals.length}`); }
    }
    if (sets.length) {
      // Mark it edited so the seed file stops rewriting it underneath them.
      await db.query(`UPDATE research_questions SET ${sets.join(', ')}, edited_at=NOW() WHERE id=$1`, vals);
    }
    res.json({ ok: true });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.delete('/api/research-questions/:id', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  try {
    await db.query(`DELETE FROM research_questions WHERE id=$1`, [parseInt(req.params.id, 10)]);
    res.json({ ok: true });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/research-questions/:id/claim', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  const who = await getResearchKey(req.session);
  if (!who) return res.status(401).json({ error: 'Login required' });
  try {
    await db.query(
      `INSERT INTO research_claims (question_id, username, note) VALUES ($1,$2,$3)
       ON CONFLICT (question_id, username) DO UPDATE SET note=EXCLUDED.note`,
      [parseInt(req.params.id, 10), who, (req.body && req.body.note || '').trim() || null]);
    res.json({ ok: true, username: who });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.delete('/api/research-questions/:id/claim', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  const who = await getResearchKey(req.session);
  if (!who) return res.status(401).json({ error: 'Login required' });
  try {
    await db.query(`DELETE FROM research_claims WHERE question_id=$1 AND username=$2`,
      [parseInt(req.params.id, 10), who]);
    res.json({ ok: true });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// ── Property research tracking ────────────────────────────────────────────────
app.get('/api/property-research', async (req, res) => {
  if (!db) return res.json({});
  try {
    const r = await db.query('SELECT property_id, username, started_at FROM property_research ORDER BY started_at');
    const out = {};
    r.rows.forEach(row => { if (!out[row.property_id]) out[row.property_id] = []; out[row.property_id].push(row.username); });
    res.json(out);
  } catch(e) { res.json({}); }
});
async function getResearchKey(session) {
  // Returns the display name to store/match in property_research table
  if (session.isAdmin) return 'admin';
  if (session.userId) {
    try {
      const u = await findUserById(session.userId);
      if (u) return ((u.first_name || '') + ' ' + (u.last_name || '')).trim() || u.email;
    } catch(e) {}
    return String(session.userId);
  }
  return null;
}

app.post('/api/property-research/:id', requireContributor, async (req, res) => {
  if (!req.session || (!req.session.isAdmin && !req.session.userId)) return res.status(401).json({ error: 'Login required' });
  if (!db) return res.status(503).json({ error: 'No DB' });
  const username = await getResearchKey(req.session);
  if (!username) return res.status(401).json({ error: 'Login required' });
  const propId = parseInt(req.params.id);
  try {
    await db.query('INSERT INTO property_research (property_id, username) VALUES ($1,$2) ON CONFLICT DO NOTHING', [propId, username]);
    res.json({ ok: true });
  } catch(e) { res.status(500).json({ error: e.message }); }
});
// Admin: wipe ALL research records (one-time cleanup)
app.delete('/api/property-research', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  try {
    const r = await db.query('DELETE FROM property_research');
    res.json({ ok: true, deleted: r.rowCount });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

app.delete('/api/property-research/:id', requireContributor, async (req, res) => {
  if (!req.session || (!req.session.isAdmin && !req.session.userId)) return res.status(401).json({ error: 'Login required' });
  if (!db) return res.status(503).json({ error: 'No DB' });
  const username = await getResearchKey(req.session);
  if (!username) return res.status(401).json({ error: 'Login required' });
  try {
    await db.query('DELETE FROM property_research WHERE property_id=$1 AND username=$2', [parseInt(req.params.id), username]);
    res.json({ ok: true });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// ── Architect Firms API ──────────────────────────────────────────────────────
app.get('/api/firms', async (req, res) => {
  const allProps = JSON.parse(fs.readFileSync(ALL_PROPS_FILE, 'utf8'));
  if (!db) {
    // Build from all_props.json only
    const firmMap = {};
    allProps.forEach(p => { if (p.architect) { const n=p.architect.trim(); if(!firmMap[n]) firmMap[n]={id:null,name:n,prop_count:0}; firmMap[n].prop_count++; } });
    return res.json(Object.values(firmMap).sort((a,b)=>b.prop_count-a.prop_count));
  }
  try {
    // Get DB firms
    const firms = await db.query('SELECT f.*, COUNT(DISTINCT fm.person_id) as member_count FROM architect_firms f LEFT JOIN firm_members fm ON fm.firm_id=f.id GROUP BY f.id ORDER BY f.name');
    // Count Park properties per firm from all_props
    const propCount = {};
    allProps.forEach(p => { if (p.architect) { const n=p.architect.trim(); propCount[n]=(propCount[n]||0)+1; } });
    const result = firms.rows.map(f => ({...f, prop_count: propCount[f.name]||0, member_count: parseInt(f.member_count)}));
    // Also include prop-only firms not in DB
    const dbNames = new Set(firms.rows.map(f=>f.name));
    const propOnly = Object.entries(propCount).filter(([n])=>!dbNames.has(n)).map(([name,cnt])=>({id:null,name,prop_count:cnt,member_count:0}));
    res.json([...result, ...propOnly].sort((a,b)=>b.prop_count-a.prop_count));
  } catch(e) { res.status(500).json({ error: e.message }); }
});

app.get('/api/firm/:id', async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  try {
    const firm = await db.query('SELECT * FROM architect_firms WHERE id=$1', [parseInt(req.params.id)]);
    if (!firm.rows[0]) return res.status(404).json({ error: 'Not found' });
    const members = await db.query(`SELECT fm.*, p.first_name, p.last_name, p.known_as, p.born_year, p.died_year
      FROM firm_members fm JOIN people p ON p.id=fm.person_id WHERE fm.firm_id=$1 ORDER BY fm.from_year`, [parseInt(req.params.id)]);
    res.json({ ...firm.rows[0], members: members.rows });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/firms', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  const { name, active_from, active_to, notes, wikipedia_url } = req.body;
  if (!name) return res.status(400).json({ error: 'name required' });
  try {
    const r = await db.query('INSERT INTO architect_firms (name,active_from,active_to,notes,wikipedia_url) VALUES ($1,$2,$3,$4,$5) RETURNING *',
      [name, active_from||null, active_to||null, notes||null, wikipedia_url||null]);
    res.json({ ok: true, firm: r.rows[0] });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

app.patch('/api/firm/:id', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  const { name, active_from, active_to, notes, wikipedia_url } = req.body;
  try {
    await db.query('UPDATE architect_firms SET name=COALESCE($2,name), active_from=$3, active_to=$4, notes=$5, wikipedia_url=$6 WHERE id=$1',
      [parseInt(req.params.id), name||null, active_from||null, active_to||null, notes||null, wikipedia_url||null]);
    res.json({ ok: true });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/firm/:id/members', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  const { person_id, role, from_year, to_year } = req.body;
  if (!person_id) return res.status(400).json({ error: 'person_id required' });
  try {
    await db.query('INSERT INTO firm_members (firm_id,person_id,role,from_year,to_year) VALUES ($1,$2,$3,$4,$5) ON CONFLICT DO NOTHING',
      [parseInt(req.params.id), parseInt(person_id), role||'Partner', from_year||null, to_year||null]);
    res.json({ ok: true });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

app.delete('/api/firm/:firmId/members/:personId', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  try {
    await db.query('DELETE FROM firm_members WHERE firm_id=$1 AND person_id=$2', [parseInt(req.params.firmId), parseInt(req.params.personId)]);
    res.json({ ok: true });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// Auto-create firms from all_props.json architect names
app.post('/api/admin/create-firms', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  try {
    const allProps = JSON.parse(fs.readFileSync(ALL_PROPS_FILE, 'utf8'));
    const names = [...new Set(allProps.map(p=>p.architect).filter(Boolean).map(n=>n.trim()))];
    let created = 0;
    for (const name of names) {
      const r = await db.query('INSERT INTO architect_firms (name) VALUES ($1) ON CONFLICT (name) DO NOTHING RETURNING id', [name]);
      if (r.rows[0]) created++;
    }
    res.json({ ok: true, created, total: names.length });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// ── Architect works API ───────────────────────────────────────────────────────
app.get('/api/architect-works/:personId', async (req, res) => {
  if (!db) return res.json([]);
  try {
    const r = await db.query('SELECT * FROM architect_works WHERE person_id=$1 ORDER BY year_start, name', [parseInt(req.params.personId)]);
    res.json(r.rows);
  } catch(e) { res.json([]); }
});

app.get('/api/architects', async (req, res) => {
  // Build from all_props.json architect fields
  const fromProps = {};
  try {
    const allProps = JSON.parse(fs.readFileSync(ALL_PROPS_FILE, 'utf8'));
    allProps.forEach(p => {
      if (p.architect) {
        const name = p.architect.trim();
        if (!fromProps[name]) fromProps[name] = { id: null, known_as: name, first_name: name, last_name: '', work_count: 0, source: 'props' };
        fromProps[name].work_count++;
      }
    });
  } catch(e) {}

  if (!db) return res.json(Object.values(fromProps).sort((a,b)=>b.work_count-a.work_count));

  try {
    const r = await db.query(`SELECT p.id, p.first_name, p.last_name, p.known_as, p.born_year, p.died_year,
      COUNT(w.id) as work_count FROM people p JOIN architect_works w ON w.person_id=p.id
      GROUP BY p.id ORDER BY p.last_name, p.first_name`);
    const dbArchs = r.rows.map(row => ({...row, work_count:parseInt(row.work_count), source:'db'}));
    const dbNames = new Set(dbArchs.map(a=>(a.known_as||(a.first_name+' '+a.last_name)).toLowerCase()));
    const propArchs = Object.values(fromProps).filter(a=>!dbNames.has(a.name&&a.name.toLowerCase()||a.known_as.toLowerCase())).sort((a,b)=>b.work_count-a.work_count);
    res.json([...dbArchs, ...propArchs]);
  } catch(e) {
    res.json(Object.values(fromProps).sort((a,b)=>b.work_count-a.work_count));
  }
});

app.post('/api/architect-works', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  const { person_id, name, location_text, address, city, year_start, year_end, notes, wikipedia_url, lat, lng, location_uncertain } = req.body;
  try {
    const r = await db.query(
      `INSERT INTO architect_works (person_id,name,location_text,address,city,year_start,year_end,notes,wikipedia_url,lat,lng,location_uncertain) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12) RETURNING *`,
      [person_id, name, location_text||null, address||null, city||'Nottingham', year_start||null, year_end||null, notes||null, wikipedia_url||null, lat||null, lng||null, location_uncertain||false]
    );
    res.json({ ok: true, work: r.rows[0] });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

app.patch('/api/architect-works/:id', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  const { lat, lng, location_uncertain, name, notes, address, year_start, year_end } = req.body;
  const updates = [];
  const vals = [parseInt(req.params.id)];
  const add = (col, val) => { if (val !== undefined) { vals.push(val); updates.push(`${col}=$${vals.length}`); } };
  add('lat', lat); add('lng', lng); add('location_uncertain', location_uncertain);
  add('name', name); add('notes', notes); add('address', address);
  add('year_start', year_start); add('year_end', year_end);
  if (!updates.length) return res.status(400).json({ error: 'Nothing to update' });
  try {
    await db.query(`UPDATE architect_works SET ${updates.join(',')} WHERE id=$1`, vals);
    res.json({ ok: true });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

app.delete('/api/architect-works/:id', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  try { await db.query('DELETE FROM architect_works WHERE id=$1', [parseInt(req.params.id)]); res.json({ ok: true }); }
  catch(e) { res.status(500).json({ error: e.message }); }
});

// ── People at a property ──────────────────────────────────────────────────────
app.get('/api/people-at-property/:id', async (req, res) => {
  if (!db) return res.json([]);
  try {
    const r = await db.query(`SELECT DISTINCT p.id, p.first_name, p.last_name, p.known_as
      FROM census_entries ce JOIN people p ON p.id=ce.person_id
      WHERE ce.property_id=$1`, [parseInt(req.params.id)]);
    res.json(r.rows);
  } catch(e) { res.json([]); }
});

// ── Debug: check what park houses returns server-side ─────────────────────────
// Public config — exposes only keys that are safe for the browser
app.get('/api/config', (req, res) => {
  res.json({ googleMapsKey: process.env.GOOGLE_MAPS_KEY || '' });
});

app.get('/api/test-fetch', (req, res) => {
  const http = require('http');
  const url = 'http://www.nottinghamparkhouses.co.uk/propertypagedetail.asp?infoId=130&linkid=130&pageId=130&id=101';
  http.get(url, { headers: { 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36' } }, (r) => {
    let data = '';
    r.on('data', c => data += c);
    r.on('end', () => {
      const startTag = data.indexOf('class="mainBody">');
      const contentStart = startTag + 'class="mainBody">'.length;
      const endTag = data.indexOf('</table>', contentStart);
      const raw = data.substring(contentStart, endTag);
      const text = raw.replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ').replace(/\s+/g, ' ').trim();
      res.send('LEN:'+text.length+' PREVIEW:'+text.substring(0,300));
    });
  }).on('error', e => res.send('ERR:'+e.message));
});

// ── Server-side scrape all descriptions from park houses website ──────────────
app.get('/api/scrape-all-descs', async (req, res) => {
  const http = require('http');
  const allPropsFile = path.join(__dirname, 'data', 'all_props.json');
  const props = JSON.parse(fs.readFileSync(allPropsFile, 'utf8'));
  const ids = props.map(p => p.id);

  function fetchDesc(id) {
    return new Promise((resolve) => {
      const url = `http://www.nottinghamparkhouses.co.uk/propertypagedetail.asp?infoId=${id}&linkid=${id}&pageId=${id}&id=101`;
      http.get(url, { headers: { 'User-Agent': 'Mozilla/5.0' } }, (r) => {
        let data = '';
        r.on('data', c => data += c);
        r.on('end', () => {
          // Find mainBody td start
          const startTag = data.indexOf('class="mainBody">');
          if (startTag === -1) return resolve({ id, desc: '' });
          const contentStart = startTag + 'class="mainBody">'.length;
          // Find the closing </table> tag after mainBody to capture full content
          const endTag = data.indexOf('</table>', contentStart);
          const raw = endTag === -1 ? data.substring(contentStart) : data.substring(contentStart, endTag);
          // Preserve newlines, strip only inline tags
          const text = raw.replace(/<br\s*\/?>/gi, '\n').replace(/<p[^>]*>/gi, '\n').replace(/<[^>]+>/g, '').replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/[ \t]+/g, ' ').trim();
          // Strip address header (everything up to first blank line)
          const desc = text.replace(/^[\s\S]*?\n\n+/, '').trim() || text;
          resolve({ id, desc });
        });
      }).on('error', () => resolve({ id, desc: '' }));
    });
  }

  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.write(`Scraping ${ids.length} properties...\n`);

  let updated = 0;
  for (let i = 0; i < ids.length; i += 10) {
    const batch = ids.slice(i, i + 10);
    const results = await Promise.all(batch.map(fetchDesc));
    results.forEach(({ id, desc }) => {
      if (desc) { const p = props.find(x => x.id === id); if (p) { p.desc = desc; updated++; } }
    });
    res.write(`Done ${Math.min(i + 10, ids.length)}/${ids.length}\n`);
  }

  fs.writeFileSync(allPropsFile, JSON.stringify(props, null, 2));
  res.end(`\nComplete! Updated ${updated} properties.\n`);
});

// ── Save scraped descriptions (local dev helper) ──────────────────────────────
app.options('/api/save-descs', (req, res) => {
  res.sendStatus(204);
});
// Admin only. This rewrites the description of every property in the shared data
// file, so it was previously an unauthenticated, cross-origin site defacement —
// and descriptions render as HTML, which made it stored XSS.
app.post('/api/save-descs', requireAdmin, express.json({limit: '10mb'}), (req, res) => {
  const descs = req.body;
  if (!descs || typeof descs !== 'object' || Array.isArray(descs)) {
    return res.status(400).json({ error: 'Expected an object of { propertyId: description }' });
  }
  const allPropsFile = path.join(__dirname, 'data', 'all_props.json');
  try {
    const props = JSON.parse(fs.readFileSync(allPropsFile, 'utf8'));
    let updated = 0;
    props.forEach(p => {
      const d = descs[p.id];
      if (typeof d === 'string') { p.desc = d; updated++; }
    });
    fs.writeFileSync(allPropsFile, JSON.stringify(props, null, 2));
    res.json({ ok: true, updated });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

dbInit().then(() => {
  app.listen(PORT, () => {
    console.log(`Park Houses running on port ${PORT}`);
    console.log(`Storage: ${db ? 'PostgreSQL' : 'JSON files (local)'}`);
    console.log(`Admin: ${ADMIN_USER} / (set ADMIN_USER + ADMIN_PASS env vars)`);
  });
});

// ── Sync all_props.json fields into property_overrides DB ────────────────────
// ── Sync all_props.json fields into property_data DB ────────────────────────
app.post('/api/admin/sync-props-to-db', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  try {
    const allProps = JSON.parse(fs.readFileSync(ALL_PROPS_FILE, 'utf8'));
    let updated = 0;
    for (const p of allProps) {
      const fields = {};
      if (p.desc) fields.desc = p.desc;
      if (p.history) fields.history = p.history;
      if (p.architect) fields.architect = p.architect;
      if (p.builder) fields.builder = p.builder;
      if (p.built_for) fields.built_for = p.built_for;
      if (p.converted) fields.converted = p.converted;
      if (p.prev_house_name) fields.prev_house_name = p.prev_house_name;
      if (p.listed_grade) fields.listedGrade = p.listed_grade;
      if (p.date_built) fields.built = p.date_built;
      if (p.listed) fields.listed = p.listed === 'Yes';
      if (!Object.keys(fields).length) continue;
      await saveProp(p.id, fields, 'sync');
      updated++;
    }
    res.json({ ok: true, updated });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// ── Find all images for a property page ──────────────────────────────────────
app.get('/api/admin/find-property-images/:id', requireAdmin, (req, res) => {
  const http = require('http');
  const id = parseInt(req.params.id);
  const url = `http://www.nottinghamparkhouses.co.uk/propertypagedetail.asp?infoId=${id}&linkid=${id}&pageId=${id}&id=101`;
  http.get(url, { headers: { 'User-Agent': 'Mozilla/5.0' } }, (r) => {
    let data = '';
    r.on('data', c => data += c);
    r.on('end', () => {
      // Extract all image/src references
      const imgs = [];
      const patterns = [
        /href=["']([^"']*\.(?:jpg|jpeg|png|gif|pdf))['"]/gi,
        /src=["']([^"']*\.(?:jpg|jpeg|png|gif))['"]/gi,
        /(imagesDB[^"'\s<>]*\.(?:jpg|jpeg|png|gif|pdf))/gi,
        /(PIC\d+[A-Za-z]?\.(?:jpg|jpeg|png|gif))/gi,
        /(PLN\d+[A-Za-z]?\.(?:jpg|jpeg|png|gif))/gi,
        /([A-Za-z0-9_-]+plan[A-Za-z0-9_-]*\.(?:jpg|jpeg|png|gif))/gi,
      ];
      patterns.forEach(p => {
        let m;
        while ((m = p.exec(data)) !== null) {
          let src = m[1];
          if (!src.startsWith('http')) {
            src = 'http://www.nottinghamparkhouses.co.uk/' + src.replace(/^\//, '').replace(/\\/g, '/');
          }
          if (!imgs.includes(src)) imgs.push(src);
        }
      });
      res.json({ id, images: imgs, total: imgs.length });
    });
  }).on('error', e => res.status(500).json({ error: e.message }));
});

// ── Scrape property images from Park Houses website ───────────────────────────
// Stores external URLs directly in the DB — no local disk storage needed,
// so images persist across Railway restarts/redeployments.
app.get('/api/admin/scrape-property-images', requireAdmin, async (req, res) => {
  const http = require('http');
  const allProps = JSON.parse(fs.readFileSync(ALL_PROPS_FILE, 'utf8'));
  const ids = req.query.id ? [parseInt(req.query.id)] : allProps.map(p => p.id);

  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.write(`Checking images for ${ids.length} properties...\n`);

  // Check if a URL returns a real image (status 200, size > 500 bytes)
  function checkUrl(url) {
    return new Promise(resolve => {
      http.get(url, { headers: { 'User-Agent': 'Mozilla/5.0' } }, r => {
        if (r.statusCode !== 200) { r.resume(); return resolve(false); }
        let len = 0;
        r.on('data', c => { len += c.length; if (len > 500) { r.destroy(); resolve(true); } });
        r.on('end', () => resolve(len > 500));
        r.on('close', () => {});
      }).on('error', () => resolve(false));
    });
  }

  let saved = 0;
  for (let i = 0; i < ids.length; i += 5) {
    const batch = ids.slice(i, i + 5);
    await Promise.all(batch.map(async id => {
      if (!db) return; // needs DB to persist
      const current = await loadProp(id);
      const photos = current.photos || [];
      const added = [];

      // Floor plan: /imagesdb/MAP{id}.jpg
      const planUrl = `http://www.nottinghamparkhouses.co.uk/imagesdb/MAP${id}.jpg`;
      if (!photos.find(p => p.url === planUrl) && await checkUrl(planUrl)) {
        photos.push({ url: planUrl, caption: 'Floor plan' });
        added.push('PLAN');
      }

      // Photos: /imagesDB/propertyimages/PIC{id}{suffix}.jpg
      for (const suffix of ['T', 'B', 'C', 'D', 'E']) {
        const imgUrl = `http://www.nottinghamparkhouses.co.uk/imagesDB/propertyimages/PIC${id}${suffix}.jpg`;
        const caption = suffix === 'T' ? 'Exterior' : suffix === 'B' ? 'Detail' : `View ${suffix}`;
        if (!photos.find(p => p.url === imgUrl) && await checkUrl(imgUrl)) {
          photos.push({ url: imgUrl, caption });
          added.push(suffix);
        }
      }

      if (added.length) {
        try {
          await saveProp(id, { photos }, 'image-scrape');
          saved += added.length;
          res.write(`✓ Property ${id}: ${added.join(', ')}\n`);
        } catch(e) {
          res.write(`✗ Property ${id} save failed: ${e.message}\n`);
        }
      }
    }));
    if (i % 50 === 0 && ids.length > 10) res.write(`Progress: ${Math.min(i+5, ids.length)}/${ids.length}\n`);
  }
  res.end(`\nDone! Saved ${saved} images across ${ids.length} properties.\n`);
});

// ── Origins API ───────────────────────────────────────────────────────────────
app.get('/api/origins', async (req, res) => {
  try {
    const { years, streets, houses, occupations } = req.query;
    const conditions = ['ce.birth_place IS NOT NULL', 'gc.lat IS NOT NULL'];
    const params = [];

    // Build property lookup from in-memory allProps JSON
    const allPropsData = JSON.parse(fs.readFileSync(ALL_PROPS_FILE, 'utf8'));
    const propMap = {};
    allPropsData.forEach(p => { propMap[p.id] = p; });

    if (years) {
      const yList = years.split(',').map(Number).filter(Boolean);
      if (yList.length) { conditions.push(`ce.census_year = ANY($${params.push(yList)})`); }
    }
    if (streets) {
      const sList = streets.split(',').map(s => s.trim()).filter(Boolean);
      if (sList.length) {
        const pidsByStreet = allPropsData
          .filter(p => p.street && sList.includes(p.street))
          .map(p => p.id);
        if (pidsByStreet.length) {
          conditions.push(`ce.property_id = ANY($${params.push(pidsByStreet)})`);
        } else {
          return res.json({ places: [], unknown: [] });
        }
      }
    }
    if (houses) {
      // houses param is comma-separated labels like "1 Park Drive,3 Park Drive"
      const hList = houses.split(',').map(s => s.trim()).filter(Boolean);
      if (hList.length) {
        const pidsByHouse = allPropsData
          .filter(p => {
            const label = [p.no, p.street].filter(Boolean).join(' ');
            return hList.includes(label);
          })
          .map(p => p.id);
        if (pidsByHouse.length) {
          conditions.push(`ce.property_id = ANY($${params.push(pidsByHouse)})`);
        } else {
          return res.json({ places: [], unknown: [] });
        }
      }
    }
    if (occupations) {
      const oList = occupations.split(',').map(s => s.trim().toLowerCase()).filter(Boolean);
      if (oList.length) {
        conditions.push(`(${oList.map((o) => `LOWER(ce.occupation_at_census) LIKE $${params.push('%'+o+'%')}`).join(' OR ')})`);
      }
    }

    const sql = `
      SELECT
        TRIM(ce.birth_place) AS birth_place,
        gc.lat, gc.lng, gc.formatted_address,
        ce.census_year,
        p.first_name, p.last_name,
        ce.occupation_at_census AS occupation,
        ce.relationship,
        ce.property_id,
        ce.unresolved_address
      FROM census_entries ce
      JOIN people p ON p.id = ce.person_id
      JOIN geocode_cache gc ON gc.place_text = TRIM(ce.birth_place) AND gc.status IN ('found','manual')
      WHERE ${conditions.join(' AND ')}
      ORDER BY birth_place, census_year
    `;

    const { rows } = await db.query(sql, params);

    // Group by place, enriching property info from in-memory propMap
    const places = {};
    for (const r of rows) {
      const key = r.birth_place;
      if (!places[key]) {
        places[key] = { birth_place: r.birth_place, lat: r.lat, lng: r.lng,
                        formatted_address: r.formatted_address, people: [] };
      }
      const prop = r.property_id ? propMap[r.property_id] : null;
      const street = prop ? (prop.street || '') : '';
      const house  = prop ? (prop.no ? `${prop.no} ${street}`.trim() : street) : (r.unresolved_address || '');
      places[key].people.push({
        name: `${r.first_name} ${r.last_name}`,
        year: r.census_year,
        occupation: r.occupation || '',
        relationship: r.relationship || '',
        street: street || r.unresolved_address || '',
        house: house || r.unresolved_address || ''
      });
    }

    // Also return places with no coords so UI can list them
    const { rows: unknown } = await db.query(`
      SELECT DISTINCT TRIM(ce.birth_place) AS birth_place, COUNT(*) AS cnt
      FROM census_entries ce
      WHERE ce.birth_place IS NOT NULL AND TRIM(ce.birth_place) != ''
        AND NOT EXISTS (SELECT 1 FROM geocode_cache gc WHERE gc.place_text = TRIM(ce.birth_place) AND gc.status IN ('found','manual'))
      GROUP BY TRIM(ce.birth_place)
      ORDER BY cnt DESC
    `);

    res.json({ places: Object.values(places), unknown });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: err.message });
  }
});

// Filter options for origins page
app.get('/api/origins/filters', async (req, res) => {
  try {
    const allPropsData = JSON.parse(fs.readFileSync(ALL_PROPS_FILE, 'utf8'));
    const propMap = {};
    allPropsData.forEach(p => { propMap[p.id] = p; });

    const streets = [...new Set(allPropsData.map(p => p.street).filter(Boolean))].sort();

    const [years, occupations, propRows] = await Promise.all([
      db.query(`SELECT DISTINCT census_year FROM census_entries WHERE birth_place IS NOT NULL ORDER BY census_year`),
      db.query(`SELECT DISTINCT occupation_at_census FROM census_entries WHERE occupation_at_census IS NOT NULL AND birth_place IS NOT NULL ORDER BY occupation_at_census`),
      db.query(`SELECT DISTINCT property_id FROM census_entries WHERE birth_place IS NOT NULL AND property_id IS NOT NULL`)
    ]);

    // Build house list: only properties that have birth_place data, sorted by label
    const houses = propRows.rows
      .map(r => {
        const p = propMap[r.property_id];
        if (!p) return null;
        return [p.no, p.street].filter(Boolean).join(' ');
      })
      .filter(Boolean)
      .sort();

    res.json({
      years: years.rows.map(r => r.census_year),
      streets,
      houses,
      occupations: occupations.rows.map(r => r.occupation_at_census)
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/origins', (req, res) => res.sendFile(path.join(__dirname, 'public', 'origins.html')));

// ── Catch-all: serve map page for any unmatched GET ───────────────────────────
// Express 5 uses path-to-regexp v8, where a bare '*' is no longer a valid path
// and a wildcard must be named. Resolved from the installed version so this
// keeps working either side of that upgrade.
const CATCH_ALL = require('express/package.json').version.startsWith('4') ? '*' : '/*splat';
app.get(CATCH_ALL, (req, res) => {
  // A request for a file that is not there is a missing file, not a page. Sending
  // the map back for it meant a lost photograph answered 200 with 159KB of HTML,
  // so the browser drew a broken-image icon and nothing anywhere said what had
  // happened. Anything under an asset directory, or carrying a file extension,
  // now says so plainly.
  if (/^\/api\//.test(req.path) || /^\/(data|uploads|assets)\//.test(req.path)
      || /\.[a-z0-9]{2,5}$/i.test(req.path)) {
    return res.status(404).json({ error: 'Not found: ' + req.path });
  }
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// ── Errors ───────────────────────────────────────────────────────────────────
// There was no error handler at all. Most routes catch their own failures, but
// two async ones do not, and Express 5 forwards a rejected promise here rather
// than leaving the request hanging as Express 4 does. Log it, and say something
// useful without leaking a stack trace to the browser in production.
app.use((err, req, res, next) => {
  console.error('[error]', req.method, req.originalUrl, '—', err && err.stack || err);
  if (res.headersSent) return next(err);
  res.status(err && err.status || 500).json({
    error: IS_PROD ? 'Something went wrong handling that request.' : String(err && err.message || err),
  });
});
