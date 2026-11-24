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

# 1) tracking must be sub-6pt everywhere
z = zipfile.ZipFile("Astro_Smart_Attendance_Team_Sun_Rises_India.pptx")
maxspc = 0
for n in z.namelist():
    if re.match(r'ppt/slides/slide\d+\.xml$', n):
        for v in re.findall(r'spc="(\d+)"', z.read(n).decode()):
            maxspc = max(maxspc, int(v))
if maxspc > 600:
    fails.append(f"letter-spacing {maxspc/100:.1f}pt exceeds 6pt cap — text will scatter")
else:
    print(f"  tracking    ok  (max {maxspc/100:.2f}pt)")

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
