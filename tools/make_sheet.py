"""Annotated drawing sheet for the Astro Smart Attendance main shell (STL 1)."""
import sys
sys.path.insert(0, "/home/user/astro-smart-attendance/tools")
import numpy as np
from PIL import Image, ImageDraw
from stl_tools import load_stl, render, projection, project_points

G = "/home/user/astro-smart-attendance/cad/"
OUT = "/home/user/astro-smart-attendance/renders/"
SHELL = G + "01_MAIN_SHELL.stl"

YEL = (255, 205, 80)
CYA = (120, 220, 255)
WHT = (233, 235, 240)
BG = (18, 20, 26)
TILE = (700, 520)

tri = load_stl(SHELL)[0]


def text_box(d, x, y, txt, fill=YEL):
    w = 6.6 * len(txt) + 8
    d.rectangle([x - 2, y - 2, x + w, y + 15], fill=BG)
    d.text((x + 2, y), txt, fill=fill)


def tile(view, title, tris=None, margins=0.10):
    t = tri if tris is None else tris
    render(t, OUT + "_t.png", view=view, W=TILE[0], H=TILE[1], bg=BG)
    im = Image.open(OUT + "_t.png").convert("RGB")
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, TILE[0], 24], fill=(10, 11, 15))
    d.rectangle([0, 24, TILE[0], 25], fill=(60, 64, 74))
    d.text((8, 6), title, fill=WHT)
    R, sc, ox, oy = projection(t, view, TILE[0], TILE[1], margins=margins)

    def P(x, y, z):
        sx, sy, _ = project_points(np.array([[x, y, z]]), R, sc, ox, oy)
        return float(sx[0]), float(sy[0])

    return im, d, P


def box(d, a, b, txt, fill=YEL, dy=-18):
    bx = [min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])]
    d.rectangle(bx, outline=fill, width=2)
    ty = bx[1] + dy
    if ty < 30:
        ty = bx[3] + 4
    text_box(d, bx[0], ty, txt, fill=fill)


def dim(d, a, b, txt, fill=CYA):
    d.line([a[0], a[1], b[0], b[1]], fill=fill, width=1)
    d.line([a[0] - 4, a[1], a[0] + 4, a[1]], fill=fill)
    d.line([b[0] - 4, b[1], b[0] + 4, b[1]], fill=fill)
    text_box(d, (a[0] + b[0]) / 2 - 3.3 * len(txt), (a[1] + b[1]) / 2 - 7, txt, fill=fill)


sheet = Image.new("RGB", (2 * TILE[0], 2 * TILE[1]), BG)

# ------------------------------------------------------------------ A front
im, d, P = tile("back", "A.  FRONT (device face)   —   110 x 155 x 48 mm overall")
box(d, P(-32.6, 44.5, 0), P(32.5, 59.4, 0), "LCD1602 window  65.1 x 14.9  (through)")
box(d, P(26.3, -34.7, 0), P(45.6, -13.5, 0), "reader opening  19.3 x 21.2  (through)", dy=22)
box(d, P(-51.4, -46.4, 0), P(11.3, -1.7, 0), "recessed pocket  62.7 x 44.7,  1.5 deep")
dim(d, P(-55, -77.5, 0), P(55, -77.5, 0), "110")
sheet.paste(im, (0, 0))

# ------------------------------------------------------------------ B left wall
im, d, P = tile("side", "B.  LEFT WALL  (x = -55)   —   4 cooling vents")
box(d, P(-55, -3.4, 11.1), P(-55, 23.4, 22.9), "4 vents  2.8 x 11.8  (through wall)")
dim(d, P(-55, -77.5, 0), P(-55, -77.5, 48), "48")
sheet.paste(im, (TILE[0], 0))

# ------------------------------------------------------------------ C rear
im, d, P = tile("front", "C.  REAR  (z = 48, closed by part 02)   —   module access")
box(d, P(26.3, -34.7, 0), P(45.6, -13.5, 0), "module opening 19.3 x 21.2 (through)", dy=22)
box(d, P(-32.6, 44.5, 0), P(32.5, 59.4, 0), "LCD rear window  (same through-slot)")
d.text((10, TILE[1] - 20), "3 mm rim all round, 4 x 3 mm standoffs inside", fill=CYA)
sheet.paste(im, (0, TILE[1]))

# ------------------------------------------------------------------ D interior
inner = tri[tri.mean(axis=1)[:, 2] >= 3.0]
im, d, P = tile("back", "D.  INTERIOR  (front wall & LCD floor removed)", tris=inner)
for (px, py, txt) in [(-37.55, 36.45, "LCD boss"), (-37.55, 67.45, "LCD boss"),
                      (37.55, 36.45, "LCD boss"), (37.55, 67.45, "LCD boss")]:
    p = P(px, py, 8.3)
    d.ellipse([p[0] - 5, p[1] - 5, p[0] + 5, p[1] + 5], outline=CYA, width=2)
text_box(d, 60, 60, "4 LCD bosses  z = 3..11,  1.5 mm pilot", fill=CYA)
for (px, py, txt) in [(22.4, -24.0, "pilot"), (49.4, -24.0, "pilot")]:
    p = P(px, py, 8.3)
    d.ellipse([p[0] - 5, p[1] - 5, p[0] + 5, p[1] + 5], outline=YEL, width=2)
text_box(d, TILE[0] - 250, TILE[1] - 90, "2 x 1.5 mm pilot (R307)", fill=YEL)
p = P(12.0, -7.0, 5.5)
d.ellipse([p[0] - 5, p[1] - 5, p[0] + 5, p[1] + 5], outline=(140, 255, 160), width=2)
text_box(d, 60, TILE[1] - 60, "1.5 mm pilot (RC522) + 3 x 3 mm standoffs at the rear", fill=(140, 255, 160))
sheet.paste(im, (TILE[0], TILE[1]))

sheet.save(OUT + "shell_drawing_sheet.png")
print("wrote shell_drawing_sheet.png")

# ------------------------------------------------------------------ exploded with labels
FILES = ["01_MAIN_SHELL.stl", "02_DETACHABLE_WALL_PLATE.stl", "03_R307_RETENTION.stl",
         "04_RC522_RETENTION.stl", "05_ESP32_RETENTION.stl"]
ZOFF = {"01_MAIN_SHELL.stl": 0, "02_DETACHABLE_WALL_PLATE.stl": 95,
        "03_R307_RETENTION.stl": 60, "04_RC522_RETENTION.stl": 32, "05_ESP32_RETENTION.stl": 78}
parts = []
for f in FILES:
    t = load_stl(G + f)[0].copy()
    t[:, :, 2] += ZOFF[f]
    parts.append((f, t))
allp = np.concatenate([t for _, t in parts])
render(allp, OUT + "exploded_iso.png", view="iso", W=1200, H=820, bg=BG)
im = Image.open(OUT + "exploded_iso.png").convert("RGB")
d = ImageDraw.Draw(im)
d.rectangle([0, 0, 1200, 24], fill=(10, 11, 15))
d.text((8, 6), "EXPLODED ASSEMBLY  —  Astro Smart Attendance enclosure v1", fill=WHT)
R, sc, ox, oy = projection(allp, "iso", 1200, 820, margins=0.06)
labels = {"01_MAIN_SHELL.stl": "01  Main shell", "02_DETACHABLE_WALL_PLATE.stl": "02  Detachable wall plate",
          "03_R307_RETENTION.stl": "03  R307 retention", "04_RC522_RETENTION.stl": "04  RC522 retention",
          "05_ESP32_RETENTION.stl": "05  ESP32 retention"}
for f, t in parts:
    c = t.reshape(-1, 3)
    c = c[np.argsort(c[:, 2])[-max(1, len(c) // 20):]].mean(axis=0)
    sx, sy, _ = project_points(np.array([c]), R, sc, ox, oy)
    sx, sy = float(sx[0]), float(sy[0])
    d.line([sx, sy, sx + 70, sy - 46], fill=YEL)
    text_box(d, sx + 72, sy - 54, labels[f], fill=YEL)
im.save(OUT + "exploded_iso.png")
print("wrote exploded_iso.png")
