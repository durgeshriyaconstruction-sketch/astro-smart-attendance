"""Before / after of the RFID area: v1 closed pocket floor vs v2 open scan window.

Renders both shells in the same front-face view and marks the RC522 footprint, so the
difference the user asked for (an RFID area the reader can actually scan through) is
visible at a glance.
"""
import sys
sys.path.insert(0, "/home/user/astro-smart-attendance/tools")
import numpy as np
from PIL import Image, ImageDraw
from stl_tools import load_stl, render, projection, project_points
import build_v2 as B

ROOT = "/home/user/astro-smart-attendance/"
OUT = ROOT + "renders/"
BG = (18, 20, 26)
W, H = 660, 800
P = B.P

v1 = load_stl(ROOT + "cad/01_MAIN_SHELL.stl")[0]
v2 = load_stl(ROOT + "cad/v2/01_MAIN_SHELL_v2.stl")[0]

fx, fy = P["rc522_centre"]
rw, rh = P["rfid_recess"]
marks = [((fx - rw / 2, fy - rh / 2, 0.2), "RC522 antenna footprint 60 x 40"),
         ((fx, fy, 0.2), "what the reader has to see through")]

sheet = Image.new("RGB", (W * 2 + 12, H + 60), (10, 11, 15))
d0 = ImageDraw.Draw(sheet)
d0.text((10, 8), "RFID AREA - BEFORE / AFTER REVISION", fill=(233, 235, 240))
d0.text((10, 27), "v1: pocket floor at z = 3 mm closes the recess - the 13.56 MHz field is shielded. "
                  "v2: 54 x 36 mm window cut through the 3 mm wall, only 2 x 4 mm stiffener bars remain.",
        fill=(120, 220, 255))

for i, (tri, title, note) in enumerate((
        (v1, "BEFORE  v1  - closed 62.7 x 44.7 pocket", (255, 120, 120)),
        (v2, "AFTER   v2  - 54 x 36 open scan window", (140, 255, 160)))):
    render(tri, OUT + "_c.png", view="front", W=W, H=H, bg=BG)
    im = Image.open(OUT + "_c.png").convert("RGB")
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 24], fill=(10, 11, 15))
    d.text((8, 6), title, fill=note)
    R, sc, ox, oy = projection(tri, "front", W, H, margins=0.08)

    def PX(p):
        sx, sy, _ = project_points(np.array([p]), R, sc, ox, oy)
        return float(sx[0]), float(sy[0])

    for pt, lab in marks:
        sx, sy = PX(pt)
        d.ellipse([sx - 4, sy - 4, sx + 4, sy + 4], outline=(255, 205, 80), width=2)
    # rectangle around the recess footprint, drawn from its corner marks
    a = PX((fx - rw / 2, fy - rh / 2, 0.2))
    b = PX((fx + rw / 2, fy + rh / 2, 0.2))
    d.rectangle([min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])],
                outline=(255, 205, 80), width=1)
    d.rectangle([0, H - 22, W, H], fill=(10, 11, 15))
    d.text((8, H - 15), lab if i == 0 else
           "open window + 2 x 4 mm bars = 300 mm2 of free aperture over the antenna coil",
           fill=(233, 235, 240))
    sheet.paste(im, (i * (W + 12), 54))

sheet.save(OUT + "rfid_before_after.png")
print("wrote renders/rfid_before_after.png")
