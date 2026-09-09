#!/usr/bin/env node
// Rebuilds data/wikidata_nottingham.json — the pool of Wikidata people the
// People page checks a resident against.
//
// Run it by hand when the snapshot looks thin:  node build-wikidata-snapshot.js
//
// The first version of this snapshot was generated once and never written down,
// so it could not be reproduced or refreshed, and it silently missed people who
// plainly qualified — Helena Brownsword Dowson among them. Hence this file.
//
// The query deliberately casts wider than "born in Nottingham". The Park's
// residents frequently were not: they moved into the estate as adults. So a
// person qualifies on birth, death, residence, workplace or burial.

const fs = require('fs');
const path = require('path');
const https = require('https');

const OUT = path.join(__dirname, 'data', 'wikidata_nottingham.json');
const UA = 'NottinghamParkHouses/1.0 (Park Conservation Trust historical record)';

// Nottingham, City of Nottingham, Nottinghamshire, and the historic county.
const PLACES = ['wd:Q41262', 'wd:Q21885994', 'wd:Q23106', 'wd:Q67535681'];
const BORN_FROM = 1750, BORN_TO = 1935;

const QUERY = `
SELECT DISTINCT ?p ?pLabel ?born ?died ?article
       (GROUP_CONCAT(DISTINCT ?occLabel; separator="|") AS ?occs)
       (GROUP_CONCAT(DISTINCT ?awdLabel; separator="|") AS ?awds)
WHERE {
  VALUES ?place { ${PLACES.join(' ')} }
  ?p wdt:P31 wd:Q5 .
  { ?p wdt:P19 ?place } UNION { ?p wdt:P20 ?place }
  UNION { ?p wdt:P551 ?place } UNION { ?p wdt:P937 ?place }
  UNION { ?p wdt:P119 ?place }
  ?p wdt:P569 ?dob .
  BIND(YEAR(?dob) AS ?born)
  FILTER(?born >= ${BORN_FROM} && ?born <= ${BORN_TO})
  OPTIONAL { ?p wdt:P570 ?dod . BIND(YEAR(?dod) AS ?died) }
  OPTIONAL { ?article schema:about ?p ; schema:isPartOf <https://en.wikipedia.org/> }
  OPTIONAL { ?p wdt:P106 ?occ . ?occ rdfs:label ?occLabel . FILTER(LANG(?occLabel)="en") }
  OPTIONAL { ?p wdt:P166 ?awd . ?awd rdfs:label ?awdLabel . FILTER(LANG(?awdLabel)="en") }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
}
GROUP BY ?p ?pLabel ?born ?died ?article`;

function sparql(query) {
  const body = 'query=' + encodeURIComponent(query);
  return new Promise((resolve, reject) => {
    const req = https.request({
      hostname: 'query.wikidata.org', path: '/sparql', method: 'POST',
      headers: {
        'User-Agent': UA,
        'Accept': 'application/sparql-results+json',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Content-Length': Buffer.byteLength(body),
      },
    }, res => {
      let d = '';
      res.on('data', c => d += c);
      res.on('end', () => {
        if (res.statusCode !== 200) {
          return reject(new Error(`Wikidata returned ${res.statusCode}: ${d.slice(0, 200)}`));
        }
        try { resolve(JSON.parse(d)); }
        catch (e) { reject(new Error('Unparseable response: ' + d.slice(0, 200))); }
      });
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

(async () => {
  console.log('Querying Wikidata — this takes up to a minute…');
  const data = await sparql(QUERY);
  const rows = data.results.bindings;

  const byQid = new Map();
  for (const r of rows) {
    const qid = r.p.value.replace(/.*\//, '');
    const name = r.pLabel.value;
    if (/^Q\d+$/.test(name)) continue;              // no English label; unusable for matching
    const split = v => (v && v.value ? v.value.split('|').filter(Boolean) : []);
    byQid.set(qid, {
      qid, name,
      born: r.born ? r.born.value : null,
      died: r.died ? r.died.value : null,
      occupations: split(r.occs),
      awards: split(r.awds),
      wikipedia: r.article ? decodeURI(r.article.value) : null,
      wikidata: `https://www.wikidata.org/wiki/${qid}`,
    });
  }

  const out = [...byQid.values()].sort((a, b) => a.name.localeCompare(b.name));

  let previous = [];
  try { previous = JSON.parse(fs.readFileSync(OUT, 'utf8')); } catch (e) {}
  const had = new Set(previous.map(p => p.qid));
  const added = out.filter(p => !had.has(p.qid));

  fs.writeFileSync(OUT, JSON.stringify(out, null, 2) + '\n');
  console.log(`Wrote ${out.length} people to ${path.relative(__dirname, OUT)} `
            + `(was ${previous.length}, ${added.length} new).`);
  if (added.length) {
    console.log('New, first 20:');
    for (const p of added.slice(0, 20)) console.log(`  ${p.qid}  ${p.name} (${p.born})`);
  }
})().catch(e => { console.error('Failed:', e.message); process.exit(1); });
