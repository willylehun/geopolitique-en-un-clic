const CACHE = 'geo-clic-v26';
const CORE = [
  './',
  './index.html',
  './styles.css',
  './app.js',
  './countries.js',
  './manifest.webmanifest',
  './assets/splash-v26.jpg',
  './icons/icon-192.png'
];

self.addEventListener('install', event => {
  self.skipWaiting();
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    await Promise.allSettled(CORE.map(url => cache.add(url)));
  })());
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  const req = event.request;
  const url = new URL(req.url);

  if (req.mode === 'navigate' || url.pathname.includes('/data/')) {
    event.respondWith(
      fetch(req, { cache: 'no-store' })
        .then(response => {
          const copy = response.clone();
          caches.open(CACHE).then(cache => cache.put(req, copy)).catch(() => {});
          return response;
        })
        .catch(() => caches.match(req, { ignoreSearch: true }))
    );
    return;
  }

  event.respondWith(
    caches.match(req, { ignoreSearch: true })
      .then(cached => cached || fetch(req).then(response => {
        const copy = response.clone();
        caches.open(CACHE).then(cache => cache.put(req, copy)).catch(() => {});
        return response;
      }))
  );
});