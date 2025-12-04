// A minimal service worker to meet the PWA requirement
self.addEventListener('install', (event) => {
    console.log('[Service Worker] Install');
    event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', (event) => {
    console.log('[Service Worker] Activate');
    event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
    // In a full PWA, you would add caching strategies here (Cache-First, Network-First)
    // For now, we just pass the request through.
    event.respondWith(fetch(event.request));
});