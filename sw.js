importScripts("./build-meta.js");

const CACHE_PREFIX = "shaoyang-quiz-";
const CACHE_NAME = `${CACHE_PREFIX}${globalThis.SHAOYANG_BUILD?.id || "development"}`;
const NETWORK_TIMEOUT_MS = 4500;
const CORE_ASSETS = [
  "./",
  "./index.html",
  "./style.css",
  "./build-meta.js",
  "./app.js",
  "./question-media.js",
  "./questions.js",
  "./manifest.webmanifest",
  "./icon-192.png",
  "./icon-512.png",
  "./icon.svg",
  "./notes.html"
];

self.addEventListener("install", (event) => {
  const freshRequests = CORE_ASSETS.map((url) => new Request(url, {cache: "reload"}));
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(freshRequests)));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key.startsWith(CACHE_PREFIX) && key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("message", (event) => {
  if (event.data === "SKIP_WAITING") self.skipWaiting();
});

async function fetchWithTimeout(request) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), NETWORK_TIMEOUT_MS);
  try {
    return await fetch(request, {signal: controller.signal, cache: "no-cache"});
  } finally {
    clearTimeout(timer);
  }
}

async function readFallback(request) {
  try {
    const cache = await caches.open(CACHE_NAME);
    const direct = await cache.match(request, {ignoreSearch: request.mode === "navigate"});
    if (direct) return direct;
    if (request.mode === "navigate") {
      const pathname = new URL(request.url).pathname;
      return await cache.match(pathname.endsWith("/notes.html") ? "./notes.html" : "./index.html", {ignoreSearch: true});
    }
  } catch {}
  return null;
}

async function cacheResponse(request, response) {
  if (!response || !response.ok) return;
  try {
    const cache = await caches.open(CACHE_NAME);
    await cache.put(request, response.clone());
  } catch {}
}

async function networkFirst(request) {
  try {
    const response = await fetchWithTimeout(request);
    await cacheResponse(request, response);
    return response;
  } catch {
    return (await readFallback(request)) || Response.error();
  }
}

async function cacheFirst(request) {
  const cached = await readFallback(request);
  if (cached) return cached;
  const response = await fetch(request);
  await cacheResponse(request, response);
  return response;
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin || url.pathname.includes("/api/")) return;

  const isCritical = request.mode === "navigate" || /\/(questions\.js|notes\.html|app\.js)$/.test(url.pathname);
  const isMedia = request.destination === "image";
  event.respondWith(isCritical ? networkFirst(request) : isMedia ? cacheFirst(request) : networkFirst(request));
});
