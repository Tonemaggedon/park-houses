const express  = require('express');
const session  = require('express-session');
const path     = require('path');
const fs       = require('fs');

const app  = express();
const PORT = process.env.PORT || 3000;

// ── Config ────────────────────────────────────────────────────────────────────
const ADMIN_USER     = process.env.ADMIN_USER     || 'admin';
const ADMIN_PASS     = process.env.ADMIN_PASS     || 'parkhouses2024';
const SESSION_SECRET = process.env.SESSION_SECRET || 'ph-secret-change-in-prod';
const COORDS_FILE    = path.join(__dirname, 'data', 'coords_overrides.json');
const PROPS_FILE     = path.join(__dirname, 'data', 'property_overrides.json');
const PHOTOS_DIR     = path.join(__dirname, 'data', 'photos');

// Ensure data dir + files exist (used as fallback when no DB)
if (!fs.existsSync(path.join(__dirname, 'data'))) fs.mkdirSync(path.join(__dirname, 'data'));
if (!fs.existsSync(PHOTOS_DIR)) fs.mkdirSync(PHOTOS_DIR);
if (!fs.existsSync(COORDS_FILE)) fs.writeFileSync(COORDS_FILE, JSON.stringify({}));
if (!fs.existsSync(PROPS_FILE))  fs.writeFileSync(PROPS_FILE, JSON.stringify({}));

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
    `);
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

// ── Middleware ────────────────────────────────────────────────────────────────
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(session({
  secret: SESSION_SECRET,
  resave: false,
  saveUninitialized: false,
  cookie: { maxAge: 8 * 60 * 60 * 1000 } // 8 hours
}));

function requireAdmin(req, res, next) {
  if (req.session && req.session.isAdmin) return next();
  res.status(401).json({ error: 'Not authenticated' });
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

app.get('/api/me', (req, res) => {
  if (req.session && req.session.isAdmin) {
    res.json({ isAdmin: true, username: req.session.username });
  } else {
    res.json({ isAdmin: false });
  }
});

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
app.get('/api/all-props', (req, res) => {
  try { res.json(JSON.parse(fs.readFileSync(ALL_PROPS_FILE, 'utf8'))); }
  catch(e) { res.json([]); }
});

// ── Property overrides API ────────────────────────────────────────────────────
app.get('/api/properties', async (req, res) => {
  try { res.json(await loadProps()); } catch(e) { res.status(500).json({ error: e.message }); }
});

app.get('/api/property/:id', async (req, res) => {
  const id = parseInt(req.params.id, 10);
  try { res.json(await loadProp(id)); } catch(e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/property/:id', requireAdmin, async (req, res) => {
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
app.post('/api/property/:id/photo', requireAdmin, (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (!id) return res.status(400).json({ error: 'invalid id' });
  const chunks = [];
  req.on('data', c => chunks.push(c));
  req.on('end', async () => {
    try {
      const buf = Buffer.concat(chunks);
      const cd = req.headers['x-filename'] || `photo_${Date.now()}.jpg`;
      const filename = `${id}_${Date.now()}_${cd.replace(/[^a-z0-9._-]/gi, '_')}`;
      fs.writeFileSync(path.join(PHOTOS_DIR, filename), buf);
      const url = `/data/photos/${filename}`;
      const current = await loadProp(id);
      const photos = [...(current.photos || []), { url, caption: '', addedAt: new Date().toISOString() }];
      await saveProp(id, { ...current, photos }, req.session.username);
      res.json({ ok: true, url });
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
        const filename = `${id}_orig_${num}${v}.jpg`;
        fs.writeFileSync(path.join(PHOTOS_DIR, filename), buf);
        const photoUrl = `/data/photos/${filename}`;
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

// Admin: delete a photo
app.delete('/api/property/:id/photo', requireAdmin, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  const { url } = req.body;
  try {
    const current = await loadProp(id);
    current.photos = (current.photos || []).filter(p => p.url !== url);
    await saveProp(id, current, req.session.username);
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

// ── Static ────────────────────────────────────────────────────────────────────
app.use(express.static(path.join(__dirname, 'public')));
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

dbInit().then(() => {
  app.listen(PORT, () => {
    console.log(`Park Houses running on port ${PORT}`);
    console.log(`Storage: ${db ? 'PostgreSQL' : 'JSON files (local)'}`);
    console.log(`Admin: ${ADMIN_USER} / (set ADMIN_USER + ADMIN_PASS env vars)`);
  });
});
