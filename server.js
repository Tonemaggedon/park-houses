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

// Ensure data dir + files exist
if (!fs.existsSync(path.join(__dirname, 'data'))) fs.mkdirSync(path.join(__dirname, 'data'));
if (!fs.existsSync(PHOTOS_DIR)) fs.mkdirSync(PHOTOS_DIR);
if (!fs.existsSync(COORDS_FILE)) fs.writeFileSync(COORDS_FILE, JSON.stringify({}));
if (!fs.existsSync(PROPS_FILE))  fs.writeFileSync(PROPS_FILE, JSON.stringify({}));

function loadProps() {
  try { return JSON.parse(fs.readFileSync(PROPS_FILE, 'utf8')); }
  catch (e) { return {}; }
}

function loadCoords() {
  try { return JSON.parse(fs.readFileSync(COORDS_FILE, 'utf8')); }
  catch (e) { return {}; }
}
function saveCoords(data) {
  fs.writeFileSync(COORDS_FILE, JSON.stringify(data, null, 2));
  autoCommit('Update dragged marker positions');
}
function saveProps(data) {
  fs.writeFileSync(PROPS_FILE, JSON.stringify(data, null, 2));
  autoCommit('Update property data');
}

// Auto-commit data files to git so Railway deploys always include latest positions/edits
function autoCommit(msg) {
  const { execSync } = require('child_process');
  try {
    execSync('git add data/coords_overrides.json data/property_overrides.json', { cwd: __dirname, stdio: 'ignore' });
    execSync(`git commit -m "${msg}" --allow-empty`, { cwd: __dirname, stdio: 'ignore' });
    // Push in background — don't block the request
    require('child_process').spawn('git', ['push'], { cwd: __dirname, stdio: 'ignore', detached: true }).unref();
  } catch(e) { /* git not available or nothing to commit — safe to ignore */ }
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
// Public: return all manual overrides (map applies these on load)
app.get('/api/coords', (req, res) => {
  res.json(loadCoords());
});

// Admin: save a single property's position
app.post('/api/coords/:id', requireAdmin, (req, res) => {
  const id = parseInt(req.params.id, 10);
  const { lat, lng } = req.body;
  if (!id || lat === undefined || lng === undefined) {
    return res.status(400).json({ error: 'id, lat, lng required' });
  }
  const coords = loadCoords();
  coords[id] = {
    lat: parseFloat(lat),
    lng: parseFloat(lng),
    placedBy: req.session.username,
    placedAt: new Date().toISOString()
  };
  saveCoords(coords);
  res.json({ ok: true, id, lat: coords[id].lat, lng: coords[id].lng });
});

// Admin: revert a property to auto-geocoded position
app.delete('/api/coords/:id', requireAdmin, (req, res) => {
  const id = parseInt(req.params.id, 10);
  const coords = loadCoords();
  delete coords[id];
  saveCoords(coords);
  res.json({ ok: true });
});

// Admin: download full coords JSON
app.get('/api/coords/export', requireAdmin, (req, res) => {
  res.setHeader('Content-Disposition', 'attachment; filename="park_coords_export.json"');
  res.setHeader('Content-Type', 'application/json');
  res.send(fs.readFileSync(COORDS_FILE));
});

// ── Property overrides API ────────────────────────────────────────────────────
// Public: get all overrides (map merges these over scraped defaults)
app.get('/api/properties', (req, res) => {
  res.json(loadProps());
});

// Public: get one property's overrides
app.get('/api/property/:id', (req, res) => {
  const id = parseInt(req.params.id, 10);
  const all = loadProps();
  res.json(all[id] || {});
});

// Admin: save/merge fields for a property
// Body: { desc, history, architect, style, built, listedGrade, residents, photos, notes }
app.post('/api/property/:id', requireAdmin, (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (!id) return res.status(400).json({ error: 'invalid id' });
  const all = loadProps();
  const current = all[id] || {};
  all[id] = {
    ...current,
    ...req.body,
    updatedBy: req.session.username,
    updatedAt: new Date().toISOString()
  };
  saveProps(all);
  res.json({ ok: true, data: all[id] });
});

// Admin: clear all overrides for a property
app.delete('/api/property/:id', requireAdmin, (req, res) => {
  const id = parseInt(req.params.id, 10);
  const all = loadProps();
  delete all[id];
  saveProps(all);
  res.json({ ok: true });
});

// ── Photo API ─────────────────────────────────────────────────────────────────
// Serve uploaded photos
app.use('/data/photos', express.static(PHOTOS_DIR));

// Admin: upload a photo for a property
app.post('/api/property/:id/photo', requireAdmin, (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (!id) return res.status(400).json({ error: 'invalid id' });

  // Handle multipart upload manually (avoid heavy multer dep)
  const chunks = [];
  req.on('data', c => chunks.push(c));
  req.on('end', () => {
    const buf = Buffer.concat(chunks);
    // Extract filename from Content-Disposition header
    const contentType = req.headers['content-type'] || '';
    const cd = req.headers['x-filename'] || `photo_${Date.now()}.jpg`;
    const filename = `${id}_${Date.now()}_${cd.replace(/[^a-z0-9._-]/gi, '_')}`;
    const filepath = path.join(PHOTOS_DIR, filename);
    fs.writeFileSync(filepath, buf);

    // Add URL to property overrides
    const all = loadProps();
    const current = all[id] || {};
    const photos = current.photos || [];
    const url = `/data/photos/${filename}`;
    photos.push({ url, caption: '', addedAt: new Date().toISOString() });
    all[id] = { ...current, photos, updatedBy: req.session.username, updatedAt: new Date().toISOString() };
    saveProps(all);
    res.json({ ok: true, url });
  });
  req.on('error', e => res.status(500).json({ error: e.message }));
});

// Admin: fetch photo from original site and save locally
app.post('/api/property/:id/fetch-photo', requireAdmin, (req, res) => {
  const http = require('http');
  const id = parseInt(req.params.id, 10);
  const { pageId, variant } = req.body; // variant: 'T' (thumb) or 'B' (big)
  const num = String(pageId || id).padStart(3, '0');
  const v = variant === 'B' ? 'B' : 'T';
  const url = `http://www.nottinghamparkhouses.co.uk/imagesDB/propertyimages/PIC${num}${v}.jpg`;

  http.get(url, { timeout: 10000 }, (upstream) => {
    if (upstream.statusCode !== 200) {
      return res.json({ ok: false, reason: `HTTP ${upstream.statusCode}` });
    }
    const chunks = [];
    upstream.on('data', c => chunks.push(c));
    upstream.on('end', () => {
      const buf = Buffer.concat(chunks);
      if (buf.length < 500) return res.json({ ok: false, reason: 'No image found' });
      const filename = `${id}_orig_${num}${v}.jpg`;
      fs.writeFileSync(path.join(PHOTOS_DIR, filename), buf);
      const photoUrl = `/data/photos/${filename}`;
      // Save to property overrides
      const all = loadProps();
      const current = all[id] || {};
      const photos = current.photos || [];
      if (!photos.find(p => p.url === photoUrl)) {
        photos.push({ url: photoUrl, caption: `Original site photo`, addedAt: new Date().toISOString() });
        all[id] = { ...current, photos, updatedBy: req.session.username, updatedAt: new Date().toISOString() };
        saveProps(all);
      }
      res.json({ ok: true, url: photoUrl });
    });
  }).on('error', e => res.json({ ok: false, reason: e.message }))
    .on('timeout', () => res.json({ ok: false, reason: 'timeout' }));
});

// Admin: delete a photo
app.delete('/api/property/:id/photo', requireAdmin, (req, res) => {
  const id = parseInt(req.params.id, 10);
  const { url } = req.body;
  const all = loadProps();
  const current = all[id] || {};
  current.photos = (current.photos || []).filter(p => p.url !== url);
  all[id] = { ...current, updatedBy: req.session.username, updatedAt: new Date().toISOString() };
  saveProps(all);
  // Try to delete file
  try { if (url.startsWith('/data/photos/')) fs.unlinkSync(path.join(PHOTOS_DIR, path.basename(url))); } catch(e) {}
  res.json({ ok: true });
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

app.listen(PORT, () => {
  console.log(`Park Houses running on port ${PORT}`);
  console.log(`Admin: ${ADMIN_USER} / (set ADMIN_USER + ADMIN_PASS env vars)`);
});
