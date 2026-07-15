const express  = require('express');
const session  = require('express-session');
const path     = require('path');
const fs       = require('fs');
const bcrypt   = require('bcrypt');
const multer   = require('multer');

const app  = express();
const PORT = process.env.PORT || 3000;

// ── Global CORS (dev) ─────────────────────────────────────────────────────────
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Content-Type,Authorization');
  res.header('Access-Control-Allow-Private-Network', 'true');
  if (req.method === 'OPTIONS') return res.sendStatus(204);
  next();
});

// ── Config ────────────────────────────────────────────────────────────────────
const ADMIN_USER     = process.env.ADMIN_USER     || 'admin';
const ADMIN_PASS     = process.env.ADMIN_PASS     || 'parkhouses2024';
const SESSION_SECRET = process.env.SESSION_SECRET || 'ph-secret-change-in-prod';
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
// Upload a video buffer to Cloudinary using a SIGNED upload (required for video — unsigned presets only allow images)
async function uploadVideo(buf, filename) {
  const cloudName = process.env.CLOUDINARY_CLOUD_NAME;
  const apiKey    = process.env.CLOUDINARY_API_KEY;
  const apiSecret = process.env.CLOUDINARY_API_SECRET;
  if (!cloudName || !apiKey || !apiSecret) {
    // Fallback: local disk (ephemeral on Railway)
    const dest = path.join(PHOTOS_DIR, filename);
    fs.writeFileSync(dest, buf);
    return `/data/photos/${filename}`;
  }
  const ext = filename.split('.').pop().toLowerCase();
  const mimeByExt = {
    mp4:'video/mp4', mov:'video/quicktime', avi:'video/x-msvideo',
    mkv:'video/x-matroska', webm:'video/webm', m4v:'video/mp4',
    wmv:'video/x-ms-wmv', ogv:'video/ogg'
  };
  const mimeType = mimeByExt[ext] || 'video/mp4';
  const safeFilename = filename.replace(/[^a-z0-9._-]/gi, '_');

  // Build signed upload: signature = SHA1(sorted_params + api_secret)
  const crypto = require('crypto');
  const timestamp = Math.floor(Date.now() / 1000);
  const sigStr = `timestamp=${timestamp}${apiSecret}`;
  const signature = crypto.createHash('sha1').update(sigStr).digest('hex');

  return new Promise((resolve, reject) => {
    const https = require('https');
    const boundary = '----ParkHousesVideoBoundary' + Date.now().toString(16);
    const parts = [
      `--${boundary}\r\nContent-Disposition: form-data; name="api_key"\r\n\r\n${apiKey}`,
      `--${boundary}\r\nContent-Disposition: form-data; name="timestamp"\r\n\r\n${timestamp}`,
      `--${boundary}\r\nContent-Disposition: form-data; name="signature"\r\n\r\n${signature}`,
    ];
    const prelude = Buffer.from(parts.join('\r\n') + '\r\n');
    const fileHeader = Buffer.from(
      `--${boundary}\r\nContent-Disposition: form-data; name="file"; filename="${safeFilename}"\r\nContent-Type: ${mimeType}\r\n\r\n`
    );
    const epilogue = Buffer.from(`\r\n--${boundary}--\r\n`);
    const body = Buffer.concat([prelude, fileHeader, buf, epilogue]);
    const req = https.request({
      hostname: 'api.cloudinary.com',
      path: `/v1_1/${cloudName}/video/upload`,
      method: 'POST',
      headers: { 'Content-Type': `multipart/form-data; boundary=${boundary}`, 'Content-Length': body.length },
      timeout: 300000, // 5 min timeout for large video files
    }, resp => {
      let data = '';
      resp.on('data', c => data += c);
      resp.on('end', () => {
        try {
          const json = JSON.parse(data);
          if (json.secure_url) resolve(json.secure_url);
          else reject(new Error(json.error?.message || `Cloudinary error: ${data.slice(0,200)}`));
        } catch(e) { reject(new Error(`Parse error: ${data.slice(0,200)}`)); }
      });
    });
    req.on('error', reject);
    req.on('timeout', () => { req.destroy(); reject(new Error('Upload timed out')); });
    // Write in chunks to avoid memory/backpressure issues with large files
    const CHUNK = 64 * 1024;
    for (let i = 0; i < body.length; i += CHUNK) {
      req.write(body.slice(i, i + CHUNK));
    }
    req.end();
  });
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

app.use(session({
  secret: SESSION_SECRET,
  resave: false,
  saveUninitialized: false,
  store: new PgStore(),
  cookie: { maxAge: 7 * 24 * 60 * 60 * 1000 } // 7 days
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
  if (username === ADMIN_USER && password === ADMIN_PASS) {
    req.session.isAdmin = true;
    req.session.username = username;
    res.json({ ok: true });
  } else {
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
  if (!email || !password)
    return res.status(400).json({ error: 'email and password required' });
  try {
    const user = await findUserByEmail(email);
    if (!user) return res.status(401).json({ error: 'Invalid email or password' });
    const ok = await bcrypt.compare(password, user.password_hash);
    if (!ok) return res.status(401).json({ error: 'Invalid email or password' });
    if (!user.approved) return res.status(403).json({ error: 'Your account is awaiting admin approval' });
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
    propNameMap[p.id] = addr || `Property ${p.id}`;
  });
} catch(e) { /* file may not exist in some envs */ }

function propName(id) { return propNameMap[id] || `Property ${id}`; }

app.get('/api/all-props', (req, res) => {
  try { res.json(JSON.parse(fs.readFileSync(ALL_PROPS_FILE, 'utf8'))); }
  catch(e) { res.json([]); }
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

    res.json({
      properties: { total: totalProps, withDesc: propsWithDesc, withPeople: propsWithPeople, withPhotos: propsWithPhotos },
      people: { total: totalPeople, occupations: totalOccupations },
      jobs: { byCensusYear: jobsByCensusYear, topJobs: topJobsList }
    });
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
app.delete('/api/property/:id/photo', async (req, res) => {
  if (!req.session.isAdmin && !req.session.userId) return res.status(401).json({ error: 'Login required' });
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
  if (!req.session.userId && !req.session.isAdmin) return res.status(401).json({ error: 'Login required' });
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
  if (!req.session.userId && !req.session.isAdmin) return res.status(401).json({ error: 'Must be logged in' });
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
      SELECT p.id, p.first_name, p.last_name, p.known_as,
             p.born_year, p.born_place, p.died_year, p.died_place,
             p.wikipedia_url, p.photo_url,
             (SELECT ARRAY_AGG(DISTINCT o.occupation) FROM occupations o WHERE o.person_id=p.id AND o.occupation IS NOT NULL) AS occupations,
             (SELECT ARRAY_AGG(DISTINCT ce.property_id) FROM census_entries ce WHERE ce.person_id=p.id AND ce.property_id IS NOT NULL) AS property_ids,
             (SELECT ARRAY_AGG(DISTINCT ce.census_year) FROM census_entries ce WHERE ce.person_id=p.id AND ce.census_year IS NOT NULL) AS census_years
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
      wheres.push(`EXISTS (SELECT 1 FROM census_entries cx WHERE cx.person_id=p.id AND cx.property_id=$${params.length})`);
    }
    if (q) {
      params.push(`%${q.toLowerCase()}%`);
      wheres.push(`(LOWER(p.first_name) LIKE $${params.length} OR LOWER(p.last_name) LIKE $${params.length} OR LOWER(p.known_as) LIKE $${params.length})`);
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
    const r = await db.query(`SELECT DISTINCT LOWER(occupation) as occupation, COUNT(*) as count
                               FROM occupations GROUP BY LOWER(occupation) ORDER BY count DESC`);
    res.json(r.rows);
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// GET /api/census/:year — all people recorded at a census year, optionally ?property=
app.get('/api/census/:year', async (req, res) => {
  if (!db) return res.json([]);
  try {
    const year = parseInt(req.params.year);
    const propId = req.query.property ? parseInt(req.query.property) : null;
    let query = `SELECT ce.*, p.first_name, p.last_name, p.known_as, p.wikipedia_url
                 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                 WHERE ce.census_year=$1`;
    const params = [year];
    if (propId) { params.push(propId); query += ` AND ce.property_id=$${params.length}`; }
    query += ' ORDER BY ce.property_id, ce.relationship';
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

// DELETE /api/property/:propId/residents/:residentId
app.delete('/api/property/:propId/residents/:residentId', requireContributor, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  try {
    await db.query('DELETE FROM property_residents WHERE id=$1 AND property_id=$2', [parseInt(req.params.residentId), parseInt(req.params.propId)]);
    res.json({ ok: true });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// GET /api/census-stats — coverage counts per year for the census landing page
app.get('/api/census-stats', async (req, res) => {
  if (!db) return res.json([]);
  try {
    const props = await loadProps();
    const total = Array.isArray(props) ? props.length : 350;
    const [recordedRes, unoccupiedRes] = await Promise.all([
      db.query(`SELECT census_year, COUNT(DISTINCT property_id) AS cnt FROM census_entries WHERE property_id IS NOT NULL GROUP BY census_year`),
      db.query(`SELECT census_year, COUNT(*) AS cnt FROM census_unoccupied GROUP BY census_year`)
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
    const props = await loadProps();
    const [recordedRes, unoccupiedRes, countsRes] = await Promise.all([
      db.query(`SELECT DISTINCT property_id FROM census_entries WHERE census_year=$1 AND property_id IS NOT NULL`, [year]),
      db.query(`SELECT property_id, notes FROM census_unoccupied WHERE census_year=$1`, [year]),
      db.query(`SELECT property_id, COUNT(DISTINCT person_id) AS cnt FROM census_entries WHERE census_year=$1 AND property_id IS NOT NULL GROUP BY property_id`, [year])
    ]);
    const recordedSet = new Set(recordedRes.rows.map(r => r.property_id));
    const unoccupiedMap = {};
    unoccupiedRes.rows.forEach(r => { unoccupiedMap[r.property_id] = r.notes || ''; });
    const countsMap = {};
    countsRes.rows.forEach(r => { countsMap[r.property_id] = parseInt(r.cnt); });
    res.json(props.map(p => ({
      id: p.id,
      address: (p.address||'Property '+p.id).replace(/:\s*([A-Z])/g,', $1').replace(/:\s*$/,''),
      status: recordedSet.has(p.id) ? 'recorded' : unoccupiedMap[p.id] !== undefined ? 'unoccupied' : 'none',
      people_count: countsMap[p.id] || 0,
      unoccupied_notes: unoccupiedMap[p.id] || null
    })));
  } catch(e) { res.status(500).json({ error: e.message }); }
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

// ── Admin: merge two people (keep target, reassign all data from source) ──────
app.post('/api/admin/merge-people', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'No DB' });
  const { keep_id, delete_id } = req.body;
  if (!keep_id || !delete_id) return res.status(400).json({ error: 'keep_id and delete_id required' });
  const keepId = parseInt(keep_id), deleteId = parseInt(delete_id);
  const client = await db.connect();
  try {
    await client.query('BEGIN');
    // Reassign census entries
    await client.query('UPDATE census_entries SET person_id=$1 WHERE person_id=$2', [keepId, deleteId]);
    // Reassign occupations
    await client.query('UPDATE occupations SET person_id=$1 WHERE person_id=$2', [keepId, deleteId]);
    // Reassign relationships — delete any that would conflict first, then update
    await client.query(`DELETE FROM people_relationships WHERE person_a_id=$2 AND (person_b_id, relationship) IN (SELECT person_b_id, relationship FROM people_relationships WHERE person_a_id=$1)`, [keepId, deleteId]);
    await client.query(`DELETE FROM people_relationships WHERE person_b_id=$2 AND (person_a_id, relationship) IN (SELECT person_a_id, relationship FROM people_relationships WHERE person_b_id=$1)`, [keepId, deleteId]);
    await client.query('UPDATE people_relationships SET person_a_id=$1 WHERE person_a_id=$2', [keepId, deleteId]);
    await client.query('UPDATE people_relationships SET person_b_id=$1 WHERE person_b_id=$2', [keepId, deleteId]);
    // Remove self-referential relationships created by merge
    await client.query('DELETE FROM people_relationships WHERE person_a_id=person_b_id');
    // Remove person_media
    await client.query('UPDATE person_media SET person_id=$1 WHERE person_id=$2', [keepId, deleteId]);
    // Remove person_links
    await client.query('UPDATE person_links SET person_id=$1 WHERE person_id=$2', [keepId, deleteId]);
    // Delete the duplicate person
    await client.query('DELETE FROM people WHERE id=$1', [deleteId]);
    // Deduplicate relationships again after merge
    await client.query(`DELETE FROM people_relationships WHERE id IN (
      SELECT a.id FROM people_relationships a
      JOIN people_relationships b ON a.person_a_id=b.person_a_id AND a.person_b_id=b.person_b_id AND a.relationship=b.relationship AND a.id > b.id
    )`);
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

app.post('/api/person/:id/links', async (req, res) => {
  if (!req.session || (!req.session.isAdmin && !req.session.userId && !req.session.username)) return res.status(401).json({ error: 'Login required' });
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

app.delete('/api/person/:personId/links/:linkId', async (req, res) => {
  if (!req.session || (!req.session.isAdmin && !req.session.userId && !req.session.username)) return res.status(401).json({ error: 'Login required' });
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
app.post('/api/person/:id/relationship', async (req, res) => {
  if (!req.session || (!req.session.isAdmin && !req.session.userId && !req.session.username)) return res.status(401).json({ error: 'Login required' });
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
    res.json({ ok: true, relationship: r.rows[0] });
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

app.post('/api/person/:id/media', (req, res, next) => {
  if (!req.session || (!req.session.isAdmin && !req.session.userId && !req.session.username)) return res.status(401).json({ error: 'Login required' });
  next();
}, (req, res) => {
  const personId = parseInt(req.params.id);
  const storage = multer.diskStorage({
    destination: PHOTOS_DIR,
    filename: (req, file, cb) => cb(null, `person-${personId}-media-${Date.now()}${path.extname(file.originalname)}`)
  });
  multer({ storage, limits: { fileSize: 10 * 1024 * 1024 } }).single('file')(req, res, async (err) => {
    if (err) return res.status(400).json({ error: err.message });
    if (!req.file) return res.status(400).json({ error: 'No file' });
    const url = `/data/photos/${req.file.filename}`;
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
app.post('/api/person/:id/media/video', (req, res) => {
  if (!req.session || (!req.session.isAdmin && !req.session.userId && !req.session.username)) return res.status(401).json({ error: 'Login required' });
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
app.post('/api/person/:id/photo', (req, res, next) => {
  if (!req.session || (!req.session.isAdmin && !req.session.userId && !req.session.username)) {
    return res.status(401).json({ error: 'Login required' });
  }
  next();
}, (req, res) => {
  const personId = parseInt(req.params.id);
  const storage = multer.diskStorage({
    destination: PROFILE_DIR,
    filename: (req, file, cb) => cb(null, `person-${personId}-${Date.now()}${path.extname(file.originalname)}`)
  });
  multer({ storage, limits: { fileSize: 5 * 1024 * 1024 } }).single('photo')(req, res, async (err) => {
    if (err) return res.status(400).json({ error: err.message });
    if (!req.file) return res.status(400).json({ error: 'No file' });
    const url = `/data/photos/profiles/${req.file.filename}`;
    if (db) {
      try {
        await db.query('UPDATE people SET photo_url=$1 WHERE id=$2', [url, personId]);
      } catch(e) { /* continue even if DB update fails */ }
    }
    res.json({ ok: true, url });
  });
});

app.post('/api/person', async (req, res) => {
  if (!req.session || (!req.session.isAdmin && !req.session.userId && !req.session.username)) return res.status(401).json({ error: 'Login required' });
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

app.patch('/api/person/:id', async (req, res) => {
  // Allow admin OR logged-in users to edit
  if (!req.session || (!req.session.isAdmin && !req.session.userId && !req.session.username)) return res.status(401).json({ error: 'Login required' });
  if (!db) return res.status(503).json({ error: 'DB not available' });
  try {
    const id = parseInt(req.params.id);
    const fields = req.body;
    const keys = Object.keys(fields).filter(k => ['first_name','last_name','known_as','born_date','born_year','born_place','died_date','died_year','died_place','bio','wikipedia_url','photo_url','grave_location','grave_number'].includes(k));
    if (!keys.length) return res.status(400).json({ error: 'No valid fields' });
    // Get old values for changelog
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

app.post('/api/person/:id/occupation', requireAdmin, async (req, res) => {
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

app.post('/api/person/:id/census', requireAdmin, async (req, res) => {
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

app.post('/api/person/:id/relationship', requireAdmin, async (req, res) => {
  if (!db) return res.status(503).json({ error: 'DB not available' });
  try {
    const { related_person_id, relationship, notes } = req.body;
    await db.query(
      `INSERT INTO people_relationships (person_a_id,person_b_id,relationship,notes) VALUES ($1,$2,$3,$4) ON CONFLICT DO NOTHING`,
      [parseInt(req.params.id), related_person_id, relationship, notes||null]
    );
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
app.get('/architects/:type/:id', (req, res) => res.sendFile(path.join(__dirname, 'public', 'architects.html')));
app.get('/architects/:id', (req, res) => res.sendFile(path.join(__dirname, 'public', 'architects.html')));

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

app.post('/api/property-research/:id', async (req, res) => {
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

app.delete('/api/property-research/:id', async (req, res) => {
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
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'POST');
  res.header('Access-Control-Allow-Headers', 'Content-Type');
  res.sendStatus(204);
});
app.post('/api/save-descs', (req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Headers', 'Content-Type');
  next();
}, express.json({limit: '10mb'}), (req, res) => {
  const descs = req.body;
  const allPropsFile = path.join(__dirname, 'data', 'all_props.json');
  try {
    const props = JSON.parse(fs.readFileSync(allPropsFile, 'utf8'));
    let updated = 0;
    props.forEach(p => {
      if (descs[p.id]) { p.desc = descs[p.id]; updated++; }
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

// ── Catch-all: serve map page for any unmatched GET ───────────────────────────
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});
