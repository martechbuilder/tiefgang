#!/usr/bin/env python3
"""Vertont ein Häppchen (oder den Vorspann) eines Tiefgang-Titels mit Chatterbox (MIT) und der Thorsten-Stimme (CC0).
  python tts.py --id <titel-id> --chapter <n|-1> --out datei.wav
Liest den Text aus data/<kat>.<hash>.js im Repo."""
import argparse, glob, json, re, sys, pathlib
ap = argparse.ArgumentParser()
ap.add_argument("--id", required=True); ap.add_argument("--chapter", type=int, required=True)
ap.add_argument("--out", required=True); ap.add_argument("--list", action="store_true"); ap.add_argument("--max-paras", type=int, default=0)
a = ap.parse_args()
ROOT = pathlib.Path(__file__).resolve().parents[2]

def find_book(bid):
    cat = bid.split("-")[0]
    for f in glob.glob(str(ROOT / "data" / f"{cat}.*.js")):
        raw = open(f, encoding="utf-8").read()
        for b in json.loads(raw[raw.index("(") + 1: raw.rindex(")")]):
            if b["id"] == bid:
                return b
    sys.exit(f"Titel {bid} nicht gefunden")

b = find_book(a.id)
if a.list:
    print(len(b["chapters"])); sys.exit(0)

# ---------- Text für die Aussprache aufbereiten ----------
from num2words import num2words
ABK = {"z. B.": "zum Beispiel", "z.B.": "zum Beispiel", "u. a.": "unter anderem", "d. h.": "das heißt", "bzw.": "beziehungsweise",
       "ca.": "circa", "etc.": "et cetera", "vgl.": "vergleiche", "Mio.": "Millionen", "Mrd.": "Milliarden", "Bio.": "Billionen",
       "Nr.": "Nummer", "Jh.": "Jahrhundert", "v. Chr.": "vor Christus", "n. Chr.": "nach Christus", "Prof.": "Professor", "Dr.": "Doktor",
       "§§": "Paragrafen", "§": "Paragraf", "Art.": "Artikel", "Abs.": "Absatz", "°C": " Grad Celsius", "km²": " Quadratkilometer",
       "m²": " Quadratmeter", "km": " Kilometer", "kg": " Kilogramm", "CO2": "C O 2", "%": " Prozent", "€": " Euro", "$": " Dollar"}
def jahr(n):
    n = int(n)
    if 1100 <= n <= 1999 and n % 100 != 0:
        return num2words(n // 100, lang="de") + "hundert " + num2words(n % 100, lang="de")
    if 2001 <= n <= 2099:
        return "zweitausend" + num2words(n % 100, lang="de")
    return num2words(n, lang="de")
def zahl(m):
    s = m.group(0)
    if re.fullmatch(r"\d{1,3}(\.\d{3})+", s): return num2words(int(s.replace(".", "")), lang="de")
    if "," in s:
        i, d = s.split(",", 1)
        return num2words(int(i), lang="de") + " Komma " + " ".join(num2words(int(c), lang="de") for c in d)
    if len(s) == 4: return jahr(s)
    return num2words(int(s), lang="de")
LEX = {"The New Yorker": "Se Nju Jorker", "New York": "Nju Jork", "Washington": "Woschington", "Buenos Aires": "Buenos Eires",
       "Ha'am": "Haam", "Trump": "Trammp", "Biden": "Beiden", "Obama": "Obama", "Reagan": "Rehgen", "Thatcher": "Thätscher",
       "Facebook": "Fäisbuck", "YouTube": "Jutjub", "Google": "Guhgel", "Twitter": "Twitter", "TikTok": "Tick Tock", "iPhone": "Ei Fohn",
       "Harvard": "Harwerd", "Stanford": "Stänferd", "Chicago": "Schikahgo", "Science": "Sei-ens", "Nature": "Neitscher",
       "Brexit": "Brexit", "Labour": "Lehber", "Tories": "Toris", "Silicon Valley": "Silikon Wälli", "Wall Street": "Wohl Striet"}
KEEP = {"NATO", "UNO", "UNESCO", "UNICEF", "OPEC", "NASA", "DAX", "BAföG", "AIDS", "LIDAR"}
def abk(m):
    w = m.group(0)
    if w in KEEP: return w
    return " ".join(w)
ROEM = {"II": "zwei", "III": "drei", "IV": "vier", "VI": "sechs", "VII": "sieben", "VIII": "acht", "IX": "neun", "XI": "elf", "XII": "zwölf", "XIII": "dreizehn", "XIV": "vierzehn", "XV": "fünfzehn", "XVI": "sechzehn"}
def norm(t):
    t = t.replace("**", "")
    t = re.sub(r"\b(" + "|".join(sorted(ROEM, key=len, reverse=True)) + r")\b(?=\s|[.,])", lambda m: ROEM[m.group(1)], t)
    for k, v in sorted(LEX.items(), key=lambda x: -len(x[0])):
        t = re.sub(r"(?<![\wäöüß])" + re.escape(k) + r"(?![\wäöüß])", v, t)
    t = re.sub(r"(?<![\wäöüßÄÖÜ])[A-ZÄÖÜ][A-ZÄÖÜa-z]?[A-ZÄÖÜ]{1,3}(?![\wäöüßÄÖÜ])", lambda m: abk(m) if sum(ch.isupper() for ch in m.group(0)) >= 2 else m.group(0), t)
    t = re.sub(r"(\d+)-(jährig|fach|mal|minütig|stündig|tägig|köpfig|prozentig)", r"\1\2", t)
    for k, v in sorted(ABK.items(), key=lambda x: -len(x[0])):
        t = t.replace(k, v)
    t = re.sub(r"(\d+)\.(?=\s+(Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember))",
               lambda m: num2words(int(m.group(1)), lang="de", to="ordinal") + "n", t)
    t = re.sub(r"(\d)\s*bis\s*(\d)", r"\1 bis \2", t)
    t = re.sub(r"\d{1,3}(?:\.\d{3})+|\d+,\d+|\d+", zahl, t)
    return re.sub(r"\s+", " ", t).strip()
def abschnitte(t, maxc=230, minc=50):
    """Sätze zu Sprechabschnitten von 50 bis 230 Zeichen bündeln (nie über Absatzgrenzen), damit die Satzmelodie trägt."""
    ss = []
    for s in re.split(r"(?<=[.!?…:;])\s+", t):
        s = s.strip()
        if not s: continue
        while len(s) > 300:  # überlange Sätze an Kommas teilen
            cut = s.rfind(", ", 120, 260)
            if cut < 0: break
            ss.append(s[:cut + 1]); s = s[cut + 2:]
        ss.append(s)
    out = []
    for s in ss:
        if out and (len(out[-1]) < minc or len(out[-1]) + len(s) + 1 <= maxc): out[-1] += " " + s
        else: out.append(s)
    if len(out) > 1 and len(out[-1]) < minc:
        last = out.pop(); out[-1] += " " + last
    return out

if a.chapter < 0:
    text = f"Tiefgang. {b['title']}. {b.get('subtitle','')}"
    paras = [text]
else:
    c = b["chapters"][a.chapter]
    paras = [c["h"] + "."] + [p for p in c["body"].split("\n\n") if p.strip()]
    if a.max_paras: paras = paras[:a.max_paras + 1]

# ---------- Sprechen ----------
import perth
if getattr(perth, "PerthImplicitWatermarker", None) is None:
    perth.PerthImplicitWatermarker = perth.DummyWatermarker
import numpy as np, torch, soundfile as sf, librosa
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
torch.manual_seed(7)
dev = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
m = ChatterboxMultilingualTTS.from_pretrained(device=dev)
REF = str(pathlib.Path(__file__).with_name("thorsten_ref.wav"))
SR = m.sr
def clean(w):
    """Gibt (audio, sprache_gefunden) zurück."""
    y = w.squeeze().detach().cpu().numpy().astype(np.float32)
    found = False
    y, _ = librosa.effects.trim(y, top_db=38, frame_length=1024, hop_length=256)  # Ruhe am Rand entfernen
    # Atmer und Rauschen am Rand: dort schneiden, wo die eigentliche Sprache beginnt bzw. endet
    hop = int(SR * 0.01); fr = librosa.feature.rms(y=y, frame_length=hop * 3, hop_length=hop)[0]
    if len(fr) > 20:
        # stimmhafte Abschnitte finden: Rauschen/Atmen ohne Stimme vor dem ersten und nach dem letzten Laut abschneiden
        f0, vf, _ = librosa.pyin(y, fmin=60, fmax=320, sr=SR, frame_length=2048, hop_length=hop)
        n = min(len(vf), len(fr))
        loud = fr[:n] > 0.15 * np.percentile(fr, 90)
        vi = np.where(vf[:n] & loud)[0]
        if len(vi) >= 8:
            found = True
            # Inseln: letzte stimmhafte Gruppe mit mindestens 80 ms, damit einzelne Fehlklassifikationen nicht zählen
            groups, start = [], vi[0]
            for i0, i1 in zip(vi[:-1], vi[1:]):
                if i1 - i0 > 3: groups.append((start, i0)); start = i1
            groups.append((start, vi[-1]))
            groups = [g for g in groups if g[1] - g[0] >= 8] or groups
            a0 = max(0, groups[0][0] * hop - int(SR * 0.12)); a1 = min(len(y), groups[-1][1] * hop + int(SR * 0.10))
            y = y[a0:a1]
        # lange Lücken im Inneren auf 0,35 s kürzen und laute stimmlose Stöße darin dämpfen
        fr = librosa.feature.rms(y=y, frame_length=hop * 3, hop_length=hop)[0]
    f = int(SR * 0.012)
    if len(y) > 4 * f:
        y[:f] *= np.linspace(0, 1, f); y[-f:] *= np.linspace(1, 0, f)  # weiche Ränder, keine Knackser
    rms = np.sqrt(np.mean(y ** 2)) + 1e-9
    return y * min(0.08 / rms, 4.0), found  # gleiche Lautheit je Abschnitt
stille = lambda s: np.zeros(int(SR * s), dtype=np.float32)
out = []
for pi, p in enumerate(paras):
    chunks = abschnitte(norm(p))
    for ci, c in enumerate(chunks):
        for versuch in range(3):  # Abschnitt ohne erkennbare Sprache (nur Rauschen) neu erzeugen
            w = m.generate(c, language_id="de", audio_prompt_path=REF, exaggeration=0.52, cfg_weight=0.35, temperature=0.68)
            yc, ok = clean(w)
            if ok: break
            print("Neuversuch wegen fehlender Sprache:", c[:60], flush=True)
        out.append(yc)
        if ci < len(chunks) - 1: out.append(stille(0.32))
    out.append(stille(1.05 if pi == 0 else 0.75))
y = np.concatenate(out)
y = y / max(1e-6, np.max(np.abs(y))) * 0.89
sf.write(a.out, y, SR)
print("ok", a.out, round(len(y) / SR, 1), "s")
