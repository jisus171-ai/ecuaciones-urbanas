const CACHE_NAME = "ecuaciones-urbanas-v10";

const STATIC_ASSETS = [
  "/",
  "/static/manifest.json",
  "/static/icon-192.png",
  "/static/icon-512.png"
];

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys
          .filter(key => key !== CACHE_NAME)
          .map(key => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener("fetch", event => {
  const request = event.request;

  if (request.method !== "GET") {
    return;
  }

  event.respondWith(
    fetch(request).catch(() => {
      return caches.match(request);
    })
  );
});
