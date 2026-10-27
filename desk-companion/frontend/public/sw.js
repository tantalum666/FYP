const SHELL_CACHE = "desk-shell-v1";
const SHELL_FILES = [
  "/index.html",
  "/manifest.webmanifest",
  "/manifest-device.webmanifest",
  "/pwa.js",
  "/icon-192.png",
  "/icon-512.png",
];

function deskFetchPlan(href, method) {
  let url;
  try {
    url = new URL(href, self.location.origin);
  } catch (error) {
    return "network";
  }
  if (method !== "GET" || url.origin !== self.location.origin) return "network";
  if (url.pathname === "/api" || url.pathname.startsWith("/api/")) return "network";
  if (url.pathname === "/" || url.pathname === "/index.html") return "navigation";
  if (url.pathname.startsWith("/assets/") || SHELL_FILES.includes(url.pathname)) return "shell";
  return "network";
}

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(SHELL_CACHE).then((cache) => cache.addAll(SHELL_FILES)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((key) => key !== SHELL_CACHE).map((key) => caches.delete(key))),
      )
      .then(() => self.clients.claim()),
  );
});

async function shellResponse(request) {
  const cache = await caches.open(SHELL_CACHE);
  const cached = await cache.match(request);
  try {
    const response = await fetch(request);
    if (response && response.ok && response.type === "basic") await cache.put(request, response.clone());
    return response;
  } catch (error) {
    return cached || Response.error();
  }
}

self.addEventListener("fetch", (event) => {
  const plan = deskFetchPlan(event.request.url, event.request.method);
  if (plan === "network") return;
  if (plan === "navigation") {
    event.respondWith(fetch(event.request).catch(() => caches.match("/index.html")));
    return;
  }
  event.respondWith(shellResponse(event.request));
});
