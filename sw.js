const CACHE = "tiefgang-202611252044";
const CORE = ["./", "./index.html", "./content.js", "./manifest.json",
  "./icons/icon-nacht-180.png", "./icons/icon-glas-180.png", "./icons/icon-hell-180.png", "./icons/icon-getoent-180.png",
  "./icons/preview-nacht.svg", "./icons/preview-glas.svg", "./icons/preview-hell.svg", "./icons/preview-getoent.svg"];
const ART = ["biologie","debatten","denken","digital","eu","geschichte","klima","koepfe","patriarchat","philosophie","physik","politik",
  "populismus","psychologie","schluesselpaper","sozialismus","streitfragen","technologie","waswaerewenn","weltall","werkzeugkasten","wirtschaft"]
  .map(c => "./art/" + c + ".jpg");
const DATA = ["./data/biologie.cb20dc9c0b.js", "./data/debatten.4125f83be0.js", "./data/denken.6c8fca25b7.js", "./data/digital.7cd03f4d00.js", "./data/eu.b10fcc7fd2.js", "./data/geschichte.3609121187.js", "./data/klima.dd018ba70d.js", "./data/koepfe.944a7a4040.js", "./data/patriarchat.fba38d18e6.js", "./data/philosophie.8b93f5d8fa.js", "./data/physik.ccb12dd492.js", "./data/politik.79f0dae89d.js", "./data/populismus.a317d2ce6b.js", "./data/psychologie.890f2a4f99.js", "./data/schluesselpaper.58161b3632.js", "./data/sozialismus.0ee9f14ef0.js", "./data/streitfragen.cd0ad75e93.js", "./data/technologie.d02f473889.js", "./data/waswaerewenn.7dd9c35dbe.js", "./data/weltall.752d2c4aa0.js", "./data/werkzeugkasten.e6dbc3643a.js", "./data/wirtschaft.33810ac84b.js", "./data/glossar.dae75c988b.js"];

self.addEventListener("install", e => {
  e.waitUntil((async () => {
    const c = await caches.open(CACHE);
    await c.addAll(CORE);
    // Textdateien tragen einen Hash im Namen: unveränderte aus dem alten Cache übernehmen, nur neue laden
    for (const u of DATA) {
      const hit = await caches.match(u);
      if (hit) await c.put(u, hit);
      else { try { const r = await fetch(u); if (r.ok) await c.put(u, r); } catch (_) {} }
    }
    try { await c.addAll(ART); } catch (_) {}
    await self.skipWaiting();
  })());
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
  // Nachrichten: immer frisch aus dem Netz, offline der letzte Stand
  if (new URL(req.url).pathname.endsWith("/news.json")) {
    e.respondWith(fetch(req, { cache: "no-store" }).then(res => putCache(req, res)).catch(() => caches.match(req, { ignoreSearch: true })));
    return;
  }
  // Inhalte, Bilder, Icons: sofort aus dem Cache, im Hintergrund aktualisieren
  e.respondWith(caches.match(req, { ignoreSearch: true }).then(hit => {
    const net = fetch(req).then(res => putCache(req, res)).catch(() => hit);
    return hit || net;
  }));
});
