// The walk has to survive a dead spot. The page, its manifest and the last list
// of stops are kept so somebody halfway up Lenton Road does not lose the route
// when the signal goes. Everything else is network-first.
const CACHE = 'parkwalk-v1';
const SHELL = ['/walk', '/walk-manifest.json',
  'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks =>
    Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;                       // answers always go to the network
  const url = new URL(req.url);
  if (url.pathname.startsWith('/api/walk/stops')) {
    // Fresh when there is signal, the last good list when there is not.
    e.respondWith(fetch(req).then(r => {
      const copy = r.clone();
      caches.open(CACHE).then(c => c.put(req, copy));
      return r;
    }).catch(() => caches.match(req)));
    return;
  }
  if (SHELL.includes(url.pathname) || SHELL.includes(req.url)) {
    e.respondWith(caches.match(req).then(r => r || fetch(req)));
  }
});
