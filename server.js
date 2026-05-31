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

// Ensure data dir + file exist
if (!fs.existsSync(path.join(__dirname, 'data'))) {
  fs.mkdirSync(path.join(__dirname, 'data'));
}
if (!fs.existsSync(COORDS_FILE)) {
  fs.writeFileSync(COORDS_FILE, JSON.stringify({}));
}

function loadCoords() {
  try { return JSON.parse(fs.readFileSync(COORDS_FILE, 'utf8')); }
  catch (e) { return {}; }
}
function saveCoords(data) {
  fs.writeFileSync(COORDS_FILE, JSON.stringify(data, null, 2));
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

// ── Static ────────────────────────────────────────────────────────────────────
app.use(express.static(path.join(__dirname, 'public')));
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`Park Houses running on port ${PORT}`);
  console.log(`Admin: ${ADMIN_USER} / (set ADMIN_USER + ADMIN_PASS env vars)`);
});
