#!/usr/bin/env node
// Usage: node seed.js <site-url> <admin-email> <admin-password> <property-id> <seed-file>
// Example: node seed.js https://park-houses.up.railway.app admin@example.com mypassword 25 data/seed-9-cavendish.json

const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');

const [,, siteUrl, email, password, propertyId, seedFile] = process.argv;

if (!siteUrl || !email || !password || !propertyId || !seedFile) {
  console.error('Usage: node seed.js <site-url> <admin-email> <admin-password> <property-id> <seed-file>');
  process.exit(1);
}

const data = JSON.parse(fs.readFileSync(path.resolve(seedFile), 'utf8'));
const base = siteUrl.replace(/\/$/, '');
const isHttps = base.startsWith('https');
const lib = isHttps ? https : http;

function request(method, path, body, cookie) {
  return new Promise((resolve, reject) => {
    const url = new URL(base + path);
    const bodyStr = body ? JSON.stringify(body) : null;
    const opts = {
      hostname: url.hostname,
      port: url.port || (isHttps ? 443 : 80),
      path: url.pathname + url.search,
      method,
      headers: {
        'Content-Type': 'application/json',
        ...(bodyStr ? { 'Content-Length': Buffer.byteLength(bodyStr) } : {}),
        ...(cookie ? { Cookie: cookie } : {}),
      },
    };
    const req = lib.request(opts, res => {
      let raw = '';
      res.on('data', d => raw += d);
      res.on('end', () => {
        try { resolve({ status: res.statusCode, headers: res.headers, body: JSON.parse(raw) }); }
        catch { resolve({ status: res.statusCode, headers: res.headers, body: raw }); }
      });
    });
    req.on('error', reject);
    if (bodyStr) req.write(bodyStr);
    req.end();
  });
}

async function main() {
  // 1. Login
  console.log('Logging in as', email, '…');
  const loginRes = await request('POST', '/api/login', { username: email, password });
  if (loginRes.status !== 200) {
    console.error('Login failed:', loginRes.body);
    process.exit(1);
  }
  const cookie = loginRes.headers['set-cookie']?.[0]?.split(';')[0];
  if (!cookie) { console.error('No session cookie returned'); process.exit(1); }
  console.log('✓ Logged in');

  // 2. Seed
  console.log(`Seeding property ${propertyId} with ${data.people?.length || 0} people…`);
  const seedRes = await request('POST', `/api/seed/property/${propertyId}/people`, data, cookie);
  if (seedRes.status !== 200) {
    console.error('Seed failed:', seedRes.body);
    process.exit(1);
  }
  const result = seedRes.body;
  console.log('✓ Seed complete');
  if (result.inserted) {
    console.log(`  People inserted: ${result.inserted.people}`);
    console.log(`  Occupations: ${result.inserted.occupations}`);
    console.log(`  Census entries: ${result.inserted.census_entries}`);
    console.log(`  Relationships: ${result.inserted.relationships}`);
    console.log(`  Places: ${result.inserted.places}`);
    console.log(`  Bibliography: ${result.inserted.bibliography}`);
  }
  if (result.people) {
    console.log('\nPeople IDs:');
    for (const [name, id] of Object.entries(result.people)) {
      console.log(`  ${name} → #${id}`);
    }
  }
}

main().catch(e => { console.error(e); process.exit(1); });
