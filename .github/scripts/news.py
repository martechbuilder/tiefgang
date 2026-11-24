#!/usr/bin/env python3
"""Holt die wichtigsten Schlagzeilen per RSS und schreibt news.json (nur Titel, kurzer Anreißer, Link).
Gleicht jede Meldung per Schlagwort mit den Tiefgang-Titeln ab. Läuft in GitHub Actions, nur Standardbibliothek."""
import email.utils, html, json, re, sys, time, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

FEEDS = [  # (Quelle, URL, max. Meldungen, Filter auf Link)
    ("tagesschau", "https://www.tagesschau.de/index~rss2.xml", 8, None),
    ("Deutschlandfunk", "https://www.deutschlandfunk.de/nachrichten-100.rss", 6, None),
    ("DW", "https://rss.dw.com/rdf/rss-de-top", 5, None),
    ("netzpolitik.org", "https://netzpolitik.org/feed/", 4, None),
    ("Correctiv Faktencheck", "https://correctiv.org/feed/", 4, "/faktencheck/"),
    ("Spektrum", "https://www.spektrum.de/alias/rss/spektrum-de-rss-feed/996406", 4, None),
]
UA = "tiefgang-reader/1.0 (private RSS reader)"
STOP = set("""Warum Wenn Wie Was Wer Wo Die Der Das Den Dem Des Ein Eine Und Oder Aber Nicht Mehr Wird Werden Wurde Ist Sind
Wäre Hätte Gegen Über Unter Nach Seit Ohne Durch Alle Jeder Zwischen Zeit Jahr Jahre Jahrhundert Geschichte Welt Mensch Menschen
Leben Frage Fragen Idee Ideen Macht Staat Politik Deutschland Europa Bilanz Mythos Wahrheit Kritik Debatte Streit Ende Anfang
Neue Neuen Alte Große Großen Kleine Wirklich Richtig Falsch Zahlen Zahl Daten Studie Studien Forschung Wissen Denken
Deutschen Deutsche Berliner Gespräch Vergleich Entwicklung Rechte Alltag Zukunft Richter Vorwurf Forscher Millionen Million
Zustimmung Bürger Institutionen Behörden Webseite System Systeme Modell Gesellschaft Freiheit Gerechtigkeit Wirtschaft Arbeit
Triumph Erfolg Erfolgs Programm Programme Analyse Interview Nachricht Nachrichten Alltags Brille Brillen
Livestream Bericht Berichte Experten Mitglieder Probleme Problem Prozent Milliarden Woche Wochen Monate Mittwoch Dienstag
Mächte Kampf Krise Krisen Ordnung Revolution Verständlich Erklärt Grenzen Planeten Schritt Wahrheit Lehren Fehler""".split())
SKIP = {"waswaerewenn"}  # fiktive Szenarien nicht zu echten Nachrichten verlinken

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()

def clean(s, n=None):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    s = re.sub(r"\s+", " ", s).strip()
    if n and len(s) > n:
        s = s[:n].rsplit(" ", 1)[0] + " …"
    return s

def pdate(s):
    if not s:
        return None
    try:
        return email.utils.parsedate_to_datetime(s).astimezone(timezone.utc)
    except Exception:
        pass
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None

def items(xml):
    root = ET.fromstring(xml)
    for el in root.iter():
        tag = el.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        d = {}
        for c in el:
            t = c.tag.split("}")[-1]
            if t == "link":
                d["link"] = (c.text or "").strip() or c.get("href", "")
            elif t in ("title", "description", "summary", "pubDate", "date", "updated", "published"):
                d.setdefault(t, c.text or "")
        yield d

def keywords():
    """Typische Schlagwörter je Titel: Wörter aus Titel, Untertitel, Zusammenfassung und Kapitelüberschriften,
    die in höchstens 3 Titeln vorkommen. Gewichte: Nachname 3, Wort aus dem Titel 2, sonst 1."""
    try:
        raw = open("content.js", encoding="utf-8").read()
        data = json.loads(raw[raw.index("=") + 1: raw.index(";window.TG_FILES")])
    except Exception as e:
        print("content.js nicht lesbar:", e, file=sys.stderr)
        return []
    W = re.compile(r"[A-ZÄÖÜ][\wäöüß]{5,}")
    docs = []
    for b in data:
        if b["cat"] in SKIP:
            continue
        txt = " ".join([b.get("subtitle", ""), b.get("summary", "")] + b.get("ch", []))
        words = {w for w in W.findall(b.get("title", "") + " " + txt) if w not in STOP}
        docs.append((b, words, set(W.findall(b.get("title", "")))))
    df = {}
    for _, words, _ in docs:
        for w in words:
            df[w] = df.get(w, 0) + 1
    out = []
    for b, words, tw in docs:
        kw = {}
        for w in words:
            if df[w] <= 3 and (w in tw or len(w) >= 7):
                kw[w] = 2 if w in tw else 1
        p = b.get("person") or {}
        if p.get("name"):
            kw[p["name"].split()[-1]] = 3
        if kw:
            pats = {w: re.compile(r"(?<![\wäöüß])" + re.escape(w[:-1] if len(w) >= 7 else w) + r"[\wäöüß]{0,3}(?![\wäöüß])") for w in kw}
            out.append((b["id"], kw, pats))
    return out

def main():
    kws = keywords()
    seen, news = set(), []
    for src, url, n, filt in FEEDS:
        try:
            got = 0
            for d in items(fetch(url)):
                link = d.get("link", "")
                if not link or link in seen or (filt and filt not in link):
                    continue
                title = clean(d.get("title"))
                if not title or title.startswith("Livestream"):
                    continue
                dt = pdate(d.get("pubDate") or d.get("date") or d.get("published") or d.get("updated"))
                teaser = clean(d.get("description") or d.get("summary"), 220)
                text = title + " " + teaser
                rel = []
                for bid, kw, pats in kws:
                    hits, stems = [], set()
                    for w, rx in pats.items():
                        if w[:5] not in stems and rx.search(text):
                            hits.append(w); stems.add(w[:5])
                    score = sum(kw[w] for w in hits)
                    if score >= 3 or (score >= 2 and len(hits) >= 2):
                        rel.append((score, len(hits), bid))
                rel.sort(reverse=True)
                seen.add(link)
                news.append({"src": src, "title": title, "teaser": teaser, "link": link,
                             "t": int(dt.timestamp()) if dt else int(time.time()),
                             "rel": [r[2] for r in rel[:2]]})
                got += 1
                if got >= n:
                    break
        except Exception as e:
            print(f"{src}: {e}", file=sys.stderr)
    news.sort(key=lambda x: -x["t"])
    json.dump({"updated": int(time.time()), "items": news}, sys.stdout, ensure_ascii=False, separators=(",", ":"))

if __name__ == "__main__":
    main()
