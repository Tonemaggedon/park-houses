// The worker that lets a phone be told something while the site is shut.
//
// It does one job and no caching at all, deliberately: the walk's worker caches,
// this one must not, because a worker that caches and a worker that pushes
// fighting over the same scope is how you end up serving last week's page.
self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));

self.addEventListener('push', event => {
  let d = {};
  try { d = event.data ? event.data.json() : {}; } catch (e) { d = { title: 'Nottingham Park Houses' }; }
  event.waitUntil(self.registration.showNotification(d.title || 'Nottingham Park Houses', {
    body: d.body || '',
    icon: '/apple-touch-icon.png',
    badge: '/favicon.svg',
    tag: d.kind || 'park',
    data: { url: d.url || '/me' }
  }));
});

// Tapping it should land you on the thing it was about, and should use a tab
// that is already open rather than piling up new ones.
self.addEventListener('notificationclick', event => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || '/me';
  event.waitUntil(clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
    for (const c of list) {
      if (c.url.includes(url) && 'focus' in c) return c.focus();
    }
    if (clients.openWindow) return clients.openWindow(url);
  }));
});
