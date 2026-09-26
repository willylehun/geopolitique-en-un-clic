const CACHE = 'geo-clic-v22';
const ASSETS = [
  './',
  './index.html',
  './styles.css?v=22',
  './app.js?v=22',
  './countries.js?v=22',
  './manifest.webmanifest?v=22',
  './data/news.json',
  './data/election.json',
  './assets/logo.png?v=22',
  './icons/icon-192.png'
];

self.addEventListener('install', event => {
  self.skipWaiting();
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS)));
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  const freshAppAsset = url.pathname.endsWith('/index.html') || url.pathname.endsWith('/app.js') || url.pathname.endsWith('/styles.css') || url.pathname.endsWith('/countries.js') || url.pathname.endsWith('/') || url.pathname.includes('/data/');
  if (freshAppAsset) {
    event.respondWith(fetch(event.request, { cache: 'no-store' }).catch(() => caches.match(event.request,{ignoreSearch:true})));
    return;
  }
  event.respondWith(
    fetch(event.request)
      .then(response => {
        const copy = response.clone();
        caches.open(CACHE).then(cache => cache.put(event.request, copy));
        return response;
      })
      .catch(() => caches.match(event.request,{ignoreSearch:true}))
  );
});