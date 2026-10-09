// The walk has to survive a dead spot halfway up Lenton Road - but it must not
// survive a deploy.
//
// **Version one cached /walk and then served it from the cache for ever.** Shell
// paths were answered cache-first with no revalidation and the cache name never
// changed, so once somebody had opened the walk they kept that exact page no
// matter what was published afterwards. A. Hagues had the enumerator's round and
// none of the three walks added after it, which is precisely the page he had
// loaded on the day the cache was filled.
//
// So: **network first for anything that changes, cache only as the fallback.**
// The page is fresh whenever there is any signal at all, and the last good copy
// is there when there is none. Only the Leaflet files are cache-first, because
// their URLs carry a version number and never change under you.
const CACHE = 'parkwalk-v3';
const LIB = [
  'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js'
];
const PAGE = ['/walk', '/walk-manifest.json'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE)
    .then(c => Promise.allSettled([...LIB, ...PAGE].map(u => c.add(u))))
    .then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

// Fresh if we can get it, the last good copy if we cannot.
function networkFirst(req) {
  return fetch(req).then(r => {
    if (r && r.ok) { const copy = r.clone(); caches.open(CACHE).then(c => c.put(req, copy)); }
    return r;
  }).catch(() => caches.match(req).then(r => r || Response.error()));
}

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;              // answers and photographs always go out
  const url = new URL(req.url);

  if (LIB.includes(req.url)) {
    e.respondWith(caches.match(req).then(r => r || fetch(req)));
    return;
  }
  // The page itself, its manifest, and the stops - everything that can change.
  if (PAGE.includes(url.pathname) || url.pathname.startsWith('/api/walk/')) {
    e.respondWith(networkFirst(req));
  }
});
