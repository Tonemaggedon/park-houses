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

// URLs to try for each property
function urlsForId(id) {
  return [
    {
      url: `http://www.nottinghamparkhouses.co.uk/imagesDB/propertyimages/PIC${id}T.jpg`,
      file: `prop-${id}-T.jpg`,
      label: 'exterior'
    },
    {
      url: `http://www.nottinghamparkhouses.co.uk/imagesDB/propertyimages/PIC${id}B.jpg`,
      file: `prop-${id}-B.jpg`,
      label: 'detail'
    },
    {
      url: `http://www.nottinghamparkhouses.co.uk/imagesdb/MAP${id}.jpg`,
      file: `prop-${id}-plan.jpg`,
      label: 'plan'
    },
  ];
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
    const id = ids[i];
    const entries = urlsForId(id);
    const results = [];

    for (const entry of entries) {
      const dest = path.join(OUT_DIR, entry.file);
      const result = await download(entry.url, dest);
      if (result === 'saved') { total++; results.push(entry.label); }
      if (result === 'skip')  { skipped++; results.push(`${entry.label}(cached)`); }
    }

    if (results.length) {
      process.stdout.write(`[${i+1}/${ids.length}] Property ${id}: ${results.join(', ')}\n`);
    }
  }

  console.log(`\nDone. ${total} new images saved, ${skipped} already existed.`);
  console.log(`Images are in: ${OUT_DIR}`);
}

run().catch(console.error);
