// PWA Service Worker for Ola Scooter Web App
const CACHE_NAME = 'ola-scooter-v1';
const ASSETS = [
  '/',
  '/login',
  '/dashboard',
  '/static/css/dashboard.css',
  '/static/js/dashboard.js',
  '/static/manifest.json',
  '/static/img/icon-192.svg',
  '/static/img/icon-512.svg'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (e) => {
  // Only handle static assets; dynamic API and SSE requests pass straight through to network
  if (e.request.url.includes('/api/') || e.request.url.includes('/events')) {
    return;
  }
  e.respondWith(
    caches.match(e.request).then((res) => res || fetch(e.request))
  );
});
