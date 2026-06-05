#!/usr/bin/env node
/**
 * Upload downloaded property images to Cloudinary using an UNSIGNED preset
 * (no API secret required), then update Railway DB with the Cloudinary URLs.
 *
 * Setup:
 *   1. Cloudinary dashboard → Settings → Upload → Upload presets → Add upload preset
 *   2. Set Signing Mode: Unsigned, Preset name: park-houses → Save
 *
 * Run:
 *   CLOUDINARY_CLOUD_NAME=dmas6rksc node upload-to-cloudinary.js
 */

const fs    = require('fs');
const path  = require('path');
const https = require('https');

// ── Config ────────────────────────────────────────────────────────────────────
const CLOUD_NAME = process.env.CLOUDINARY_CLOUD_NAME || 'dmas6rksc'; // your cloud name
const PRESET     = 'park-houses'; // the unsigned preset name you created
const IMG_DIR    = path.join(__dirname, 'downloaded-images');
const ADMIN_PASS = 'parkhouses2024';

// ── Unsigned Cloudinary upload via multipart form ─────────────────────────────
const FormData = require('form-data');

function uploadToCloudinary(filePath, publicId) {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    form.append('file',         fs.createReadStream(filePath));
    form.append('upload_preset', PRESET);
    form.append('public_id',    `park-houses/${publicId}`);

    const headers = form.getHeaders();
    const req = https.request({
      hostname: 'api.cloudinary.com',
      path:     `/v1_1/${CLOUD_NAME}/image/upload`,
      method:   'POST',
      headers,
    }, res => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          if (json.secure_url) resolve(json.secure_url);
          else reject(new Error(json.error?.message || JSON.stringify(json)));
        } catch(e) { reject(new Error(data)); }
      });
    });
    req.on('error', reject);
    form.pipe(req);
  });
}

// ── Railway API helpers ───────────────────────────────────────────────────────
function apiRequest(urlPath, method, body, cookie) {
  return new Promise((resolve, reject) => {
    const data = body ? JSON.stringify(body) : null;
    const req  = https.request({
      hostname: 'park-houses-production.up.railway.app',
      path:     urlPath,
      method,
      headers: {
        'Content-Type': 'application/json',
        ...(data   ? { 'Content-Length': Buffer.byteLength(data) } : {}),
        ...(cookie ? { Cookie: cookie } : {}),
      },
    }, res => {
      let d = '';
      res.on('data', c => d += c);
      res.on('end', () => {
        try { resolve({ body: JSON.parse(d), headers: res.headers }); }
        catch(e) { resolve({ body: d, headers: res.headers }); }
      });
    });
    req.on('error', reject);
    if (data) req.write(data);
    req.end();
  });
}

async function login() {
  const r = await apiRequest('/api/login', 'POST', { username: 'admin', password: ADMIN_PASS });
  const c = r.headers['set-cookie'];
  if (!c) throw new Error('Login failed');
  return c.map(x => x.split(';')[0]).join('; ');
}

async function getPhotos(id, cookie) {
  const r = await apiRequest(`/api/property/${id}`, 'GET', null, cookie);
  return r.body.photos || [];
}

async function savePhotos(id, photos, cookie) {
  await apiRequest(`/api/property/${id}`, 'POST', { photos }, cookie);
}

function isTemporaryUrl(url) {
  return url.includes('nottinghamparkhouses.co.uk') || url.startsWith('/data/photos/');
}

// ── Main ──────────────────────────────────────────────────────────────────────
async function run() {
  // Group files by property ID
  const files  = fs.readdirSync(IMG_DIR).filter(f => /^prop-\d+-(T|B|plan)\.jpg$/.test(f));
  const byProp = {};
  for (const f of files) {
    const [, id, type] = f.match(/^prop-(\d+)-(T|B|plan)\.jpg$/);
    if (!byProp[id]) byProp[id] = [];
    byProp[id].push({ file: path.join(IMG_DIR, f), type });
  }
  const ids = Object.keys(byProp).sort((a, b) => parseInt(a) - parseInt(b));
  console.log(`Found ${files.length} files for ${ids.length} properties\n`);

  // Quick credential test
  console.log('Testing Cloudinary upload preset...');
  try {
    const testResult = await uploadToCloudinary(byProp[ids[0]][0].file, 'test-check');
    console.log(`✓ Working — test URL: ${testResult}\n`);
    // clean up test
    // (leave it — tiny file, harmless)
  } catch(e) {
    console.error(`✗ Upload failed: ${e.message}`);
    console.error('\nMake sure you created an UNSIGNED preset named "park-houses" in Cloudinary settings.');
    process.exit(1);
  }

  console.log('Logging in to Railway...');
  const cookie = await login();
  console.log('Logged in.\n');

  let uploaded = 0, skipped = 0, failed = 0;

  for (let i = 0; i < ids.length; i++) {
    const id    = ids[i];
    const items = byProp[id];
    process.stdout.write(`[${i+1}/${ids.length}] Property ${id}: `);

    let existing = [];
    try { existing = await getPhotos(id, cookie); } catch(e) {}
    const keepPhotos = existing.filter(p => !isTemporaryUrl(p.url));
    const newPhotos  = [...keepPhotos];
    const results    = [];

    for (const { file, type } of items) {
      const publicId = `prop-${id}-${type}`;

      if (keepPhotos.some(p => p.url.includes('cloudinary.com') && p.url.includes(publicId))) {
        skipped++; results.push(`${type}(done)`); continue;
      }

      try {
        const url     = await uploadToCloudinary(file, publicId);
        const caption = type === 'T' ? 'Exterior' : type === 'B' ? 'Detail' : 'Floor plan';
        newPhotos.push({ url, caption });
        uploaded++; results.push(type);
      } catch(e) {
        failed++; results.push(`${type}(ERR:${e.message.slice(0, 40)})`);
      }
    }

    try { await savePhotos(id, newPhotos, cookie); }
    catch(e) { results.push(`(DB err: ${e.message})`); }

    console.log(results.join(', '));
  }

  console.log(`\n✓ Complete. ${uploaded} uploaded, ${skipped} already done, ${failed} failed.`);
}

run().catch(e => { console.error('\nFatal:', e.message); process.exit(1); });
