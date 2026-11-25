const CACHE = "tiefgang-202611251101";
const CORE = ["./", "./index.html", "./content.js", "./manifest.json",
  "./icons/icon-nacht-180.png", "./icons/icon-glas-180.png", "./icons/icon-hell-180.png", "./icons/icon-getoent-180.png",
  "./icons/preview-nacht.svg", "./icons/preview-glas.svg", "./icons/preview-hell.svg", "./icons/preview-getoent.svg"];
const ART = ["biologie","debatten","denken","digital","eu","geschichte","klima","koepfe","patriarchat","philosophie","physik","politik",
  "populismus","psychologie","schluesselpaper","sozialismus","streitfragen","technologie","waswaerewenn","weltall","werkzeugkasten","wirtschaft"]
  .map(c => "./art/" + c + ".jpg");
const DATA = ["./data/biologie.f83599b8dc.js", "./data/debatten.c7c4f9a862.js", "./data/denken.59115affa4.js", "./data/digital.1cd0f626b9.js", "./data/eu.ad64f71e20.js", "./data/geschichte.2f7d490d3d.js", "./data/klima.02ba95d605.js", "./data/koepfe.43be37b747.js", "./data/patriarchat.bd6dd6a393.js", "./data/philosophie.6e3ccb2008.js", "./data/physik.29bbcaa889.js", "./data/politik.8efd292423.js", "./data/populismus.1a0387ba50.js", "./data/psychologie.a9f84593a3.js", "./data/schluesselpaper.7445b3f8aa.js", "./data/sozialismus.f0da0c539b.js", "./data/streitfragen.1202c0cd67.js", "./data/technologie.35fb360bfa.js", "./data/waswaerewenn.d8e45b40f1.js", "./data/weltall.e0795e7f15.js", "./data/werkzeugkasten.560456831e.js", "./data/wirtschaft.930224097c.js"];

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
