const CACHE = "tiefgang-202611240933";
const CORE = ["./", "./index.html", "./content.js", "./manifest.json",
  "./icons/icon-nacht-180.png", "./icons/icon-glas-180.png", "./icons/icon-hell-180.png", "./icons/icon-getoent-180.png",
  "./icons/preview-nacht.svg", "./icons/preview-glas.svg", "./icons/preview-hell.svg", "./icons/preview-getoent.svg"];
const ART = ["biologie","debatten","denken","digital","eu","geschichte","klima","patriarchat","philosophie","physik","politik",
  "populismus","psychologie","sozialismus","streitfragen","technologie","waswaerewenn","weltall","werkzeugkasten","wirtschaft"]
  .map(c => "./art/" + c + ".jpg");

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(CORE).then(() => c.addAll(ART).catch(() => {}))).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

function putCache(req, res) { if (res && res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); } return res; }

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET" || new URL(req.url).origin !== location.origin) return;
  // Seite: Netz mit 3 s Timeout, sonst Cache (neue Version kommt beim nächsten Start)
  if (req.mode === "navigate") {
    e.respondWith(new Promise(resolve => {
      let done = false;
      const fallback = () => caches.match(req).then(h => h || caches.match("./index.html")).then(h => { if (!done && h) { done = true; resolve(h); } });
      const t = setTimeout(fallback, 3000);
      fetch(req).then(res => { clearTimeout(t); putCache(req, res); if (!done) { done = true; resolve(res); } })
        .catch(() => { clearTimeout(t); fallback(); });
    }));
    return;
  }
  // Inhalte, Bilder, Icons: sofort aus dem Cache, im Hintergrund aktualisieren
  e.respondWith(caches.match(req, { ignoreSearch: true }).then(hit => {
    const net = fetch(req).then(res => putCache(req, res)).catch(() => hit);
    return hit || net;
  }));
});
