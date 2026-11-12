"""Build presentation views of the Astro Smart Attendance enclosure."""
import sys
sys.path.insert(0, "/home/user/astro-smart-attendance/tools")
import numpy as np
from PIL import Image, ImageDraw
from stl_tools import load_stl, render, projection, project_points, compute_normals

G = "/home/user/astro-smart-attendance/cad/"
OUT = "/home/user/astro-smart-attendance/renders/"
FILES = ["01_MAIN_SHELL.stl", "02_DETACHABLE_WALL_PLATE.stl",
         "03_R307_RETENTION.stl", "04_RC522_RETENTION.stl", "05_ESP32_RETENTION.stl"]

parts = {f: load_stl(G + f)[0] for f in FILES}


def translate(tri, d):
    return tri + np.array(d, dtype=np.float64)


# ------------------------------------------------------------------ 1. front view
W, H = 760, 1000
tri = parts["01_MAIN_SHELL.stl"]
render(tri, OUT + "_tmp_front.png", view="back", W=W, H=H, margins=0.10)
im = Image.open(OUT + "_tmp_front.png").convert("RGB")
d = ImageDraw.Draw(im)
R, scale, ox, oy = projection(tri, "back", W, H, margins=0.10)

notes = [
    # (x0,x1,y0,y1, z, text)
    (-32.6, 32.5, 44.5, 59.4, 0.0, "LCD1602 window  65.1 x 14.9 mm (through)"),
    (26.3, 45.6, -34.7, -13.5, 0.0, "square opening  19.3 x 21.2 mm (through)"),
    (-51.4, 11.3, -46.4, -1.7, 1.5, "recessed panel  62.7 x 44.7 mm, 1.5 mm deep"),
]
for (x0, x1, y0, y1, z, txt) in notes:
    pts = np.array([[x0, y0, z], [x1, y0, z], [x1, y1, z], [x0, y1, z]])
    sx, sy, _ = project_points(pts, R, scale, ox, oy)
    box = [sx.min(), sy.min(), sx.max(), sy.max()]
    d.rectangle(box, outline=(255, 210, 90), width=2)
    ty = box[1] - 34 if box[1] > 40 else box[3] + 8
    d.rectangle([box[0] - 2, ty - 2, box[0] + 12 * len(txt) * 0.62, ty + 16], fill=(12, 13, 17))
    d.text((box[0], ty), txt, fill=(255, 210, 90))
d.text((10, H - 24), "FRONT (device face)  -  outer shell 110 x 155 x 48 mm", fill=(190, 195, 205))
im.save(OUT + "shell_front_annotated.png")

# ------------------------------------------------------------------ 2. exploded iso
exp = {
    "01_MAIN_SHELL.stl": (0, 0, 0),
    "02_DETACHABLE_WALL_PLATE.stl": (0, 0, 70),
    "03_R307_RETENTION.stl": (0, 0, 55),
    "04_RC522_RETENTION.stl": (0, 0, 45),
    "05_ESP32_RETENTION.stl": (0, 0, 50),
}
allp = np.concatenate([translate(parts[f], exp[f]) for f in FILES])
render(allp, OUT + "exploded_iso.png", view="iso2", W=1100, H=780)

# ------------------------------------------------------------------ 3. section (right half cut away)
tri = parts["01_MAIN_SHELL.stl"]
cen = tri.mean(axis=1)
half = tri[cen[:, 0] <= 0.0]
section = np.concatenate([half,
                          translate(parts["03_R307_RETENTION.stl"], (0, 0, 0)),
                          translate(parts["04_RC522_RETENTION.stl"], (0, 0, 0)),
                          translate(parts["05_ESP32_RETENTION.stl"], (0, 0, 0))])
render(section, OUT + "section_iso.png", view=(-140, 30), W=1000, H=760)

print("done")
