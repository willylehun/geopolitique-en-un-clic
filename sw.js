const CACHE='geo-clic-v35';
const CORE=[
  './',
  './index.html',
  './styles.css',
  './app.js',
  './countries.js',
  './manifest.webmanifest',
  './assets/splash-hd-v31.webp',
  './icons/icon-192.png'
];

self.addEventListener('install',event=>{
  self.skipWaiting();
  event.waitUntil((async()=>{
    const cache=await caches.open(CACHE);
    await Promise.allSettled(CORE.map(url=>cache.add(url)));
  })());
});

self.addEventListener('activate',event=>{
  event.waitUntil((async()=>{
    const keys=await caches.keys();
    await Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch',event=>{
  if(event.request.method!=='GET') return;

  const req=event.request;
  const url=new URL(req.url);

  // Never proxy or cache third-party requests.
  if(url.origin!==self.location.origin) return;

  if(req.mode==='navigate'||url.pathname.endsWith('/app.js')||url.pathname.endsWith('/countries.js')||url.pathname.endsWith('/styles.css')||url.pathname.includes('/data/')||url.pathname.includes('/api/')){
    event.respondWith(
      fetch(req,{cache:'no-store'})
        .catch(()=>caches.match(req,{ignoreSearch:true}))
    );
    return;
  }

  event.respondWith(
    caches.match(req,{ignoreSearch:true})
      .then(cached=>cached||fetch(req))
  );
});