// The build injects the exact immutable assets and a cache name derived from the bundle.
const assets = __SAATHI_ASSETS__;
const cacheName = __SAATHI_CACHE__;
self.addEventListener("install", event => {
  event.waitUntil(caches.open(cacheName).then(cache => cache.addAll(assets)));
});
self.addEventListener("activate", event => {
  event.waitUntil(caches.keys().then(names => Promise.all(names
    .filter(name => name.startsWith("saathi-shell-") && name !== cacheName)
    .map(name => caches.delete(name)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", event => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || url.origin !== self.location.origin || url.pathname.startsWith("/api/")) return;
  if (event.request.mode === "navigate") {
    event.respondWith(fetch(event.request).catch(() => caches.open(cacheName).then(cache => cache.match("/index.html"))));
  } else if (assets.includes(url.pathname)) {
    event.respondWith(caches.open(cacheName).then(async cache => (await cache.match(url.pathname)) || fetch(event.request)));
  }
});
