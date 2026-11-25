#!/usr/bin/env python3
"""Vertont ein Häppchen (oder den Vorspann) eines Tiefgang-Titels mit Chatterbox (MIT) und der Thorsten-Stimme (CC0).
  python tts.py --id <titel-id> --chapter <n|-1> --out datei.wav
Liest den Text aus data/<kat>.<hash>.js im Repo."""
import argparse, glob, json, re, sys, pathlib
ap = argparse.ArgumentParser()
ap.add_argument("--id", required=True); ap.add_argument("--chapter", type=int, required=True)
ap.add_argument("--out", required=True); ap.add_argument("--list", action="store_true")
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
        return num2words(n // 100, lang="de") + "hundert" + num2words(n % 100, lang="de")
    return num2words(n, lang="de")
def zahl(m):
    s = m.group(0)
    if re.fullmatch(r"\d{1,3}(\.\d{3})+", s): return num2words(int(s.replace(".", "")), lang="de")
    if "," in s:
        i, d = s.split(",", 1)
        return num2words(int(i), lang="de") + " Komma " + " ".join(num2words(int(c), lang="de") for c in d)
    if len(s) == 4: return jahr(s)
    return num2words(int(s), lang="de")
def norm(t):
    t = t.replace("**", "")
    for k, v in sorted(ABK.items(), key=lambda x: -len(x[0])):
        t = t.replace(k, v)
    t = re.sub(r"(\d+)\.(?=\s+(Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember))",
               lambda m: num2words(int(m.group(1)), lang="de", to="ordinal") + "n", t)
    t = re.sub(r"(\d)\s*bis\s*(\d)", r"\1 bis \2", t)
    t = re.sub(r"\d{1,3}(?:\.\d{3})+|\d+,\d+|\d+", zahl, t)
    return re.sub(r"\s+", " ", t).strip()
def saetze(t):
    out = []
    for s in re.split(r"(?<=[.!?…:;])\s+", t):
        if len(s) > 280:
            out += [p.strip() for p in re.split(r"(?<=,)\s+", s) if p.strip()]
        elif s.strip():
            out.append(s.strip())
    merged = []
    for s in out:
        if merged and len(merged[-1]) + len(s) < 120: merged[-1] += " " + s
        else: merged.append(s)
    return merged

if a.chapter < 0:
    text = f"Tiefgang. {b['title']}. {b.get('subtitle','')}"
    paras = [text]
else:
    c = b["chapters"][a.chapter]
    paras = [c["h"] + "."] + [p for p in c["body"].split("\n\n") if p.strip()]

# ---------- Sprechen ----------
import perth
if getattr(perth, "PerthImplicitWatermarker", None) is None:
    perth.PerthImplicitWatermarker = perth.DummyWatermarker
import torch, torchaudio as ta
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
torch.manual_seed(7)
m = ChatterboxMultilingualTTS.from_pretrained(device="cuda" if torch.cuda.is_available() else "cpu")
REF = str(pathlib.Path(__file__).with_name("thorsten_ref.wav"))
parts = []
for pi, p in enumerate(paras):
    for s in saetze(norm(p)):
        w = m.generate(s, language_id="de", audio_prompt_path=REF, exaggeration=0.4, cfg_weight=0.35)
        parts += [w, torch.zeros(1, int(m.sr * 0.35))]
    parts.append(torch.zeros(1, int(m.sr * (0.9 if pi == 0 else 0.6))))
ta.save(a.out, torch.cat(parts, dim=1), m.sr)
print("ok", a.out)
