#!/usr/bin/env node
/**
 * Download all Park Houses property images to ./downloaded-images/
 * Run: node download-images.js
 *
 * Downloads for each property:
 *   - PIC{id}T.jpg  (exterior photo)
 *   - PIC{id}B.jpg  (detail photo)
 *   - MAP{id}.jpg   (floor plan)
 */

const http  = require('http');
const https = require('https');
const fs    = require('fs');
const path  = require('path');

const OUT_DIR = path.join(__dirname, 'downloaded-images');
if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR);

const allProps = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'all_props.json'), 'utf8'));
const ids = allProps.map(p => p.id);

// Build a list of candidate URLs for each image type.
// For ids < 100, try the zero-padded form first (PIC001T), then unpadded (PIC1T).
function candidatesForId(id) {
  const pad = String(id).padStart(3, '0');
  const raw = String(id);
  const picForms = pad === raw ? [raw] : [pad, raw]; // e.g. ['001','1'] for id=1
  const mapForms = pad === raw ? [raw] : [pad, raw];

  return {
    T:    picForms.map(p => `http://www.nottinghamparkhouses.co.uk/imagesDB/propertyimages/PIC${p}T.jpg`),
    B:    picForms.map(p => `http://www.nottinghamparkhouses.co.uk/imagesDB/propertyimages/PIC${p}B.jpg`),
    plan: mapForms.map(p => `http://www.nottinghamparkhouses.co.uk/imagesdb/MAP${p}.jpg`),
  };
}

function download(url, dest) {
  return new Promise(resolve => {
    if (fs.existsSync(dest)) return resolve('skip'); // already downloaded
    const lib = url.startsWith('https') ? https : http;
    const file = fs.createWriteStream(dest + '.tmp');
    lib.get(url, { headers: { 'User-Agent': 'Mozilla/5.0' } }, r => {
      if (r.statusCode !== 200) {
        r.resume();
        file.close();
        fs.unlink(dest + '.tmp', () => {});
        return resolve('miss');
      }
      r.pipe(file);
      file.on('finish', () => {
        file.close(() => {
          const stat = fs.statSync(dest + '.tmp');
          if (stat.size < 500) {
            fs.unlink(dest + '.tmp', () => {});
            return resolve('miss');
          }
          fs.renameSync(dest + '.tmp', dest);
          resolve('saved');
        });
      });
    }).on('error', () => {
      file.close();
      fs.unlink(dest + '.tmp', () => {});
      resolve('miss');
    });
  });
}

async function run() {
  let total = 0, skipped = 0;
  console.log(`Downloading images for ${ids.length} properties into ./downloaded-images/\n`);

  for (let i = 0; i < ids.length; i++) {
    const id         = ids[i];
    const candidates = candidatesForId(id);
    const results    = [];

    for (const [type, urls] of Object.entries(candidates)) {
      const file  = `prop-${id}-${type}.jpg`;
      const dest  = path.join(OUT_DIR, file);
      let outcome = 'miss';

      for (const url of urls) {
        outcome = await download(url, dest);
        if (outcome === 'saved' || outcome === 'skip') break; // got it
      }

      if (outcome === 'saved') { total++;   results.push(type); }
      if (outcome === 'skip')  { skipped++; results.push(`${type}(cached)`); }
    }

    if (results.length) {
      process.stdout.write(`[${i+1}/${ids.length}] Property ${id}: ${results.join(', ')}\n`);
    }
  }

  console.log(`\nDone. ${total} new images saved, ${skipped} already existed.`);
  console.log(`Images are in: ${OUT_DIR}`);
}

run().catch(console.error);
