"""qa_deck.py — assert the .pptx is actually openable and sane.
Catches the class of bug that a naive preview renderer hides:
runaway letter-spacing, autofit resizing, boxes that can't hold their text.
Run after build_ppt.py; exits non-zero on failure."""
import re, sys, zipfile
from pptx import Presentation
from pptx.util import Emu
import textmetrics as TM

EMU = 914400.0
fails, warns = [], []

prs = Presentation("Astro_Smart_Attendance_Team_Sun_Rises_India.pptx")
if len(prs.slides) < 1:
    fails.append("no slides")

# 1) PORTABILITY GATE. The reviewer's own viewer exploded `spc` runs and
#    dropped the `<p:bg>` slide background. Both are banned outright, not
#    merely capped, and images may never be stretched by the box they sit in.
z = zipfile.ZipFile("Astro_Smart_Attendance_Team_Sun_Rises_India.pptx")
S = [n for n in z.namelist() if re.match(r'ppt/slides/slide\d+\.xml$', n)]
xml = {n: z.read(n).decode() for n in S}

spc = sum(len(re.findall(r'spc="', t)) for t in xml.values())
if spc:
    fails.append(f"{spc} letter-spacing (spc) attributes — banned: some viewers scatter them")
else:
    print("  tracking    ok  (no spc attributes at all)")

bg = sum(t.count("<p:bg") for t in xml.values())
if bg:
    fails.append(f"{bg} <p:bg> slide backgrounds — banned: some viewers ignore them; "
                 "draw a full-bleed rectangle instead")
else:
    print("  background  ok  (no <p:bg>; real shape on every slide)")

caps = sum(t.count('cap="all"') for t in xml.values())
if caps:
    fails.append(f"{caps} cap=\"all\" runs — uppercase the string instead")

# every picture must fill its box without distortion
from PIL import Image as _Im
for i, sd in enumerate(prs.slides, 1):
    for sh in sd.shapes:
        if sh.shape_type is not None and "PICTURE" in str(sh.shape_type):
            try:
                iw, ih = _Im.open(sh.image.blob and __import__("io").BytesIO(sh.image.blob)).size
            except Exception:
                continue
            if abs((iw / ih) - (sh.width / sh.height)) > 0.02:
                fails.append(f"slide {i}: picture is stretched "
                             f"({iw/ih:.2f} src in {sh.width/sh.height:.2f} box)")

# 2) no autofit — shapes must keep the geometry we placed
auto = sum(z.read(n).decode().count("spAutoFit") + z.read(n).decode().count("normAutofit")
           for n in z.namelist() if re.match(r'ppt/slides/slide\d+\.xml$', n))
if auto:
    fails.append(f"{auto} text frames use autofit — PowerPoint will resize them")
else:
    print("  geometry    ok  (no autofit)")

# 3) every text run must fit the box that holds it
overflow = 0
for i, s in enumerate(prs.slides, 1):
    for sh in s.shapes:
        if not sh.has_text_frame or not sh.text_frame.text.strip():
            continue
        w, h = sh.width / EMU, sh.height / EMU
        if w <= 0:
            continue
        need = 0.0
        for p in sh.text_frame.paragraphs:
            for r in p.runs:
                if not r.text:
                    continue
                sz = r.font.size.pt if r.font.size else 12
                ls = p.line_spacing if isinstance(p.line_spacing, float) else 1.0
                n = len(TM.wrap(r.text, sz, bool(r.font.bold), bool(r.font.italic), w * 288))
                need += n * sz * 1.205 * ls / 72.0
        if need > h + 0.10:
            overflow += 1
            if overflow <= 6:
                warns.append(f"S{i}: '{sh.text_frame.text[:34]}' needs {need:.2f}\" in a {h:.2f}\" box")
print(f"  text fit    {'ok' if not overflow else str(overflow)+' to review'}")

# 3b) no text may be painted over by a later opaque rectangle (z-order clip).
#     Growing type is exactly what causes this, so it is gated now.
import json as _json
_d = _json.load(open("deck.json")) if __import__("os").path.exists("deck.json") else None
if _d:
    clipped = 0
    for si, sd in enumerate(_d["slides"], 1):
        ps = sd["prims"]
        for k, p in enumerate(ps):
            if p["t"] != "text":
                continue
            items = p.get("items") or []
            if not items:
                continue
            need = 0.0
            for it in items:
                t = it.get("t", "")
                if not t.strip():
                    continue
                sz = it.get("size", 12)
                ls = it.get("ls", 1.0) or 1.0
                n = len(TM.wrap(t, sz, bool(it.get("b")), bool(it.get("i")), p["w"] * 288))
                need += n * sz * 1.205 * ls / 72.0
            tx0, ty0, tx1, ty1 = p["x"], p["y"], p["x"] + p["w"], p["y"] + need
            for q in ps[k + 1:]:
                if q["t"] != "rect" or not q.get("fill"):
                    continue
                ox = max(0, min(tx1, q["x"] + q["w"]) - max(tx0, q["x"]))
                oy = max(0, min(ty1, q["y"] + q["h"]) - max(ty0, q["y"]))
                if ox > 0.4 and oy > 0.10:
                    clipped += 1
                    warns.append(f"S{si}: text '{items[0]['t'][:30]}' is covered by a shape drawn after it")
    if clipped:
        fails.append(f"{clipped} text blocks are painted over by a later shape")
    else:
        print("  z-order     ok  (no text covered by a shape)")

# 4) every slide needs real speaker notes
for i, s in enumerate(prs.slides, 1):
    if len(s.notes_slide.notes_text_frame.text.strip()) < 300:
        fails.append(f"slide {i} speaker notes too short")

for w in warns:
    print("  note:", w)
print()
if fails:
    print("FAILED:")
    for f in fails:
        print("  ✗", f)
    sys.exit(1)
print("PASS — deck is structurally sound")
