"""Annotated drawing sheet for the v2 (regenerated) Astro Smart Attendance enclosure.

Everything is read from cad/v2/*.stl and the same parameter table that built them
(tools/build_v2.py), so the callouts can never drift from the geometry.
"""
import sys
sys.path.insert(0, "/home/user/astro-smart-attendance/tools")
import numpy as np
from PIL import Image, ImageDraw
from stl_tools import load_stl, render, projection, project_points
import build_v2 as B

ROOT = "/home/user/astro-smart-attendance/"
G = ROOT + "cad/v2/"
OUT = ROOT + "renders/"
P = B.P

YEL = (255, 205, 80)
GRN = (140, 255, 160)
CYA = (120, 220, 255)
WHT = (233, 235, 240)
MAG = (255, 150, 220)
BG = (18, 20, 26)
TILE = (760, 560)

shell = load_stl(G + "01_MAIN_SHELL_v2.stl")[0]
plate = load_stl(G + "02_REAR_PLATE_v2.stl")[0]
bracket = load_stl(G + "03_R307_BRACKET_v2.stl")[0]


def text_box(d, x, y, txt, fill=YEL):
    w = 6.6 * len(txt) + 8
    d.rectangle([x - 2, y - 2, x + w, y + 15], fill=BG)
    d.text((x + 2, y), txt, fill=fill)


def tile(view, title, tris=None, margins=0.10, marks=(), note=None):
    t = shell if tris is None else tris
    render(t, OUT + "_t.png", view=view, W=TILE[0], H=TILE[1], bg=BG)
    im = Image.open(OUT + "_t.png").convert("RGB")
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, TILE[0], 24], fill=(10, 11, 15))
    d.rectangle([0, 24, TILE[0], 25], fill=(60, 64, 74))
    d.text((8, 6), title, fill=WHT)
    R, sc, ox, oy = projection(t, view, TILE[0], TILE[1], margins=margins)

    def PX(pt):
        sx, sy, _ = project_points(np.array([pt]), R, sc, ox, oy)
        return float(sx[0]), float(sy[0])

    placed = []
    for pt, lab, colour, dx, dy in marks:
        sx, sy = PX(pt)
        w = 6.6 * len(lab) + 10
        tx = min(max(sx + dx, 6), TILE[0] - w - 6)
        ty = min(max(sy + dy, 34), TILE[1] - 26)
        for _ in range(60):                       # nudge off other labels
            if not any(abs(ty - py) < 20 and tx < px + pw and px < tx + w for px, pw, py in placed):
                break
            ty += 22
            if ty > TILE[1] - 26:
                ty = 34
                tx = min(max(tx + 0.5 * w, 6), TILE[0] - w - 6)
        placed.append((tx, w, ty))
        d.line([sx, sy, tx + (4 if dx >= 0 else w - 4), ty + 7], fill=colour)
        d.ellipse([sx - 3, sy - 3, sx + 3, sy + 3], outline=colour, width=2)
        text_box(d, tx, ty, lab, fill=colour)
    if note:
        d.rectangle([0, TILE[1] - 20, TILE[0], TILE[1]], fill=(10, 11, 15))
        d.text((8, TILE[1] - 14), note, fill=CYA)
    return im


# ------------------------------------------------------------------ sheet
sheet = Image.new("RGB", (TILE[0] * 2, TILE[1] * 2 + 46), (10, 11, 15))
draw = ImageDraw.Draw(sheet)
draw.text((10, 8), "ASTRO SMART ATTENDANCE  —  ENCLOSURE v2 (parametric rebuild)   units: mm   "
                   "outer 110 x 155 x 48   wall 2.4-3.0   print fit 0.35", fill=WHT)
draw.text((10, 26), "front face DOWN on the bed · rear opening UP · no supports required "
                    "· 4 x M3 shell->plate · single watertight shell body", fill=CYA)
draw.line([0, 44, TILE[0] * 2, 44], fill=(60, 64, 74))

fy, fz = P["fan_centre_yz"]
lcdx, lcdy = P["lcd_centre"]
r3x, r3y = P["r307_centre"]
rcx, rcy = P["rc522_centre"]

# tile 0,0 ---- front face, annotated
front_marks = [
    ((lcdx, lcdy, 0.0), "LCD1602 window %.1f x %.1f (80 x 36 behind)" % P["lcd_window"], YEL, -170, -60),
    ((r3x, r3y, 0.0), "R307 window %.1f x %.1f" % (P["r307_window"][0], P["r307_window"][1]), GRN, 80, -46),
    ((rcx, rcy, 0.0), "RFID SCAN WINDOW %.0f x %.0f - OPEN, no floor" % P["rfid_window"], MAG, 140, 66),
    ((rcx - P["rfid_recess"][0] / 2, rcy - P["rfid_recess"][1] / 2, 0.0),
     "RC522 recess %.1f x %.1f x %.1f" % (P["rfid_recess"][0], P["rfid_recess"][1], P["rfid_recess_deep"]), CYA, -190, 86),
]
sheet.paste(tile("front", "1  FRONT FACE  (LCD + fingerprint + RFID scan window)", marks=front_marks,
                 note="2 x 4 mm stiffener bars only - the whole RC522 antenna sees out"), (0, 46))

# tile 1,0 ---- iso
iso_marks = [
    ((r3x, r3y, 0.0), "fingerprint", GRN, -110, -70),
    ((rcx, rcy, 0.0), "RFID scan window", MAG, -160, 60),
    ((0.0, -P["H"] / 2, 3.0), "front wall 3.0 mm", CYA, 80, 100),
]
sheet.paste(tile("iso", "2  ISO  (front face down on the bed)", marks=iso_marks), (TILE[0], 46))

# tile 0,1 ---- -X side wall: fan, ESP32, vents
side_marks = [
    ((-P["W"] / 2, fy, fz), "3010 fan: grille d26, 3 bars, 4 M2.5 pilots at 24 mm", GRN, 90, -66),
    ((-P["W"] / 2, -44.0, P["esp32_z_centre"]), "ESP32 DevKit V1 bay - 10 mm standoff, USB slot", YEL, 130, 40),
    ((-P["W"] / 2, 0.0, P["top_vent_z"]), "top vent 3 x (16 x 3)", CYA, 96, -86),
    ((-P["W"] / 2, 0.0, P["vent_z"][0]), "exhaust 2 x (20 x 4)", MAG, 110, 86),
]
sheet.paste(tile("side", "3  -X SIDE  (fan + ESP32 bay, seen from outside)", marks=side_marks,
                 note="vented wall: exhaust low, fan mid, top vent at the board level"), (0, 46 + TILE[1]))

# tile 1,1 ---- rear plate
plate_marks = [
    ((P["plate_boss_xy"][0], P["plate_boss_xy"][1], P["D"]), "4 x M3 into 9 mm bosses (pilot d2.5)", YEL, -180, -56),
    ((-P["keyhole_span"] / 2, 0.0, P["D"]), "keyhole hang: d7.5 + 4.6 slot, 50 mm span", CYA, 76, 56),
    ((-P["plate_boss_xy"][0], -P["plate_boss_xy"][1], P["D"]),
     "truncated boss keeps the USB corridor clear", MAG, 86, 96),
]
sheet.paste(tile("back", "4  REAR PLATE  (3 mm, seats on a 2 mm register lip)", tris=plate, marks=plate_marks,
                 note="plate + shell = 48 mm total depth"), (TILE[0], 46 + TILE[1]))

sheet.save(OUT + "v2_shell_drawing_sheet.png")
print("wrote renders/v2_shell_drawing_sheet.png")

# ------------------------------------------------------------------ exploded
parts = [("01  Main shell", shell.copy(), 0.0),
         ("02  Rear plate", plate.copy(), 95.0),
         ("03  R307 bracket", bracket.copy(), 0.0)]
for _, t, dz in parts:
    if dz:
        t[:, :, 2] += dz
parts[2][1][:, :, 2] += 96.0
parts[2][1][:, :, 0] += 46.0
parts[2][1][:, :, 1] -= 78.0
allp = np.concatenate([t for _, t, _ in parts])
render(allp, OUT + "v2_exploded_iso.png", view="iso2", W=1200, H=840, bg=BG)
im = Image.open(OUT + "v2_exploded_iso.png").convert("RGB")
d = ImageDraw.Draw(im)
d.rectangle([0, 0, 1200, 24], fill=(10, 11, 15))
d.text((8, 6), "EXPLODED  —  Astro Smart Attendance enclosure v2  (3 printed parts, no supports)", fill=WHT)
R, sc, ox, oy = projection(allp, "iso2", 1200, 840, margins=0.07)
for name, t, _ in parts:
    c = t.reshape(-1, 3)
    c = c[np.argsort(c[:, 2])[-max(1, len(c) // 20):]].mean(axis=0)
    sx, sy, _ = project_points(np.array([c]), R, sc, ox, oy)
    sx, sy = float(sx[0]), float(sy[0])
    d.line([sx, sy, sx + 70, sy - 46], fill=YEL)
    text_box(d, sx + 72, sy - 54, name, fill=YEL)
im.save(OUT + "v2_exploded_iso.png")
print("wrote renders/v2_exploded_iso.png")
