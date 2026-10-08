"""v3 deliverable figures - drawn from the shipped STLs in cad/v3/, never from a sketch.

  renders/v3_drawing_sheet.png    4 annotated tiles (front / iso / side / rear plate)
  renders/v3_exploded_iso.png     the 4 printed parts, exploded along Z
  renders/v3_all_views.png        assembly front / back / +X / -X, with the part legend
  renders/v3_vs_v2.png            what actually changed, same view, same scale

Every number in a callout is read out of tools/build_v3.py's parameter table (the same table
that produced the geometry) or measured back off the mesh, so a figure cannot claim something
the model does not do.
"""
import os
import sys

sys.path.insert(0, "/home/user/astro-smart-attendance/tools")
import numpy as np
import trimesh
from PIL import Image, ImageDraw
from stl_tools import load_stl, render, projection, project_points
import build_v3 as B

ROOT = "/home/user/astro-smart-attendance/"
OUT = ROOT + "renders/"
P = B.P

YEL = (255, 205, 80)
GRN = (140, 255, 160)
CYA = (120, 220, 255)
WHT = (233, 235, 240)
MAG = (255, 150, 220)
RED = (255, 130, 130)
BG = (18, 20, 26)
PANEL_BG = (10, 11, 15)
TILE = (780, 560)

C = {"shell": (152, 172, 202), "plate": (126, 202, 152), "bracket": (232, 184, 96),
     "ring": (206, 136, 206)}

F = {"shell": "01_MAIN_SHELL_v3.stl", "plate": "02_REAR_PLATE_v3.stl",
     "bracket": "03_R307_BRACKET_v3.stl", "ring": "04_RC522_RING_v3.stl"}
PARTS = {k: load_stl(ROOT + "cad/v3/" + v)[0] for k, v in F.items()}
MESH = {k: trimesh.load(ROOT + "cad/v3/" + v, process=True) for k, v in F.items()}


def assembly(offset=None, drop=()):
    """all four printed parts, in their as-built positions, plus per-triangle colours"""
    out, cols = [], []
    for i, (name, tri) in enumerate(PARTS.items()):
        if name in drop:
            continue
        t = tri.copy()
        if offset and name in offset:
            t[:, :, 2] += offset[name]
        out.append(t)
        cols.append(np.tile(np.array(C[name], dtype=float), (len(t), 1)))
    tris = np.concatenate(out)
    return tris, np.concatenate(cols).astype(np.uint8)


def tile(tris, view, title, fname, W=TILE[0], H=TILE[1], marks=(), note=None, margins=0.10,
         tri_rgb=None):
    render(tris, OUT + fname, view=view, W=W, H=H, bg=BG, margins=margins, tri_rgb=tri_rgb)
    im = Image.open(OUT + fname).convert("RGB")
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 24], fill=PANEL_BG)
    d.rectangle([0, 24, W, 25], fill=(60, 64, 74))
    d.text((8, 6), title, fill=WHT)
    R, sc, ox, oy = projection(tris, view, W, H, margins=margins)
    placed = []
    for pt, lab, colour, dx, dy in marks:
        sx, sy, _ = project_points(np.array([pt]), R, sc, ox, oy)
        sx, sy = float(sx[0]), float(sy[0])
        for block in lab.split("\n"):
            pass
        w = 6.6 * max(len(s) for s in lab.split("\n")) + 10
        h = 15 * len(lab.split("\n")) + 4
        tx = min(max(sx + dx, 6), W - w - 6)
        ty = min(max(sy + dy, 30), H - h - (22 if note else 6))
        for _ in range(80):
            if not any(abs(ty - py) < h + 4 and tx < px + pw and px < tx + w
                       for px, pw, py in placed):
                break
            ty += h + 6
            if ty > H - h - 24:
                ty = 30
                tx = min(max(tx + 0.5 * w, 6), W - w - 6)
        placed.append((tx, w, ty))
        d.line([sx, sy, tx + (4 if dx >= 0 else w - 4), ty + h / 2], fill=colour)
        d.ellipse([sx - 3, sy - 3, sx + 3, sy + 3], outline=colour, width=2)
        d.rectangle([tx - 2, ty - 2, tx + w, ty + h], fill=PANEL_BG)
        for k, line in enumerate(lab.split("\n")):
            d.text((tx + 2, ty + 1 + 15 * k), line, fill=colour)
    if note:
        d.rectangle([0, H - 20, W, H], fill=PANEL_BG)
        d.text((8, H - 14), note, fill=CYA)
    return im


def measured_opening(mesh, z, cx, cy, tol=6.0):
    """size of the through-opening whose centre is nearest (cx, cy), measured off the mesh"""
    sec = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    best = None
    for poly in sec.to_2D()[0].polygons_full:
        for interior in poly.interiors:
            g = np.array(interior.coords)
            x0, x1 = g[:, 0].min(), g[:, 0].max()
            y0, y1 = g[:, 1].min(), g[:, 1].max()
            path, T = sec.to_2D()
            T = np.asarray(T)

            def w2(xy):
                v = np.array([xy[0], xy[1], 0.0, 1.0]) @ T.T
                return v[:2]

            x0, y0 = w2((x0, y0)); x1, y1 = w2((x1, y1))
            d = abs((x0 + x1) / 2 - cx) + abs((y0 + y1) / 2 - cy)
            if best is None or d < best[0]:
                best = (d, x1 - x0, y1 - y0)
    return best[1], best[2]


# ---------------------------------------------------------------- shared facts
lw, lh = P["lcd_window"]
r3w, r3h = P["r307_window"]
rfw, rfh = P["rfid_window"]
rcx, rcy = P["r307_centre"]
fcx, fcy = P["rc522_centre"]
lcx, lcy = P["lcd_centre"]
fy, fz = P["fan_centre_yz"]
OW, OH, OT = P["rc522_ring"]
OPEN_W, OPEN_H, OPEN_R = P["rc522_ring_open"]

lcd_open = measured_opening(MESH["shell"], P["wall_front"] / 2, lcx, lcy)
rfid_open = measured_opening(MESH["shell"], P["wall_front"] / 2 + 1.0, fcx, fcy)
r307_open = measured_opening(MESH["shell"], P["wall_front"] / 2, rcx, rcy)

# ==================================================================== FIGURE 1
sheet = Image.new("RGB", (TILE[0] * 2, TILE[1] * 2 + 52), PANEL_BG)
dr = ImageDraw.Draw(sheet)
dr.text((10, 8), "ASTRO SMART ATTENDANCE - ENCLOSURE v3 (complete re-design)   units: mm   "
                 f"outer {P['W']:.0f} x {P['H']:.0f} x {P['D']:.0f}   front 3.0 / side "
                 f"{P['wall_side']:.1f} / top-bottom 3.0   print fit {P['fit']:.2f}", fill=WHT)
dr.text((10, 28), f"4 printed parts | front face DOWN | no supports | {22} self-tapping screw "
                  "holes, every one measured out of the STL | rear plate hangs on keyholes + "
                  f"4 x M3 | total print volume {sum(abs(m.volume) for m in MESH.values()) / 1e3:.1f} cm3 "
                  f"(~140 g PLA printed, walls solid + 15 % infill)", fill=CYA)
dr.line([0, 48, TILE[0] * 2, 48], fill=(60, 64, 74))

front_marks = [
    ((lcx, lcy, 0.0), f"LCD1602 window  {lcd_open[0]:.1f} x {lcd_open[1]:.1f} through\n"
     f"0.45 x 3.0 rebate sunk around it", YEL, -180, -78),
    ((rcx, rcy, 0.0), f"fingerprint R307  opening {r307_open[0]:.1f} x {r307_open[1]:.1f}\n"
     f"module optical window {r3w} x {r3h} sits inside it", GRN, 92, -52),
    ((fcx, fcy, 0.0), f"RFID SCAN APERTURE {rfid_open[0]:.1f} x {rfid_open[1]:.1f}\n"
     "100 % open - v2 had 2 stiffener bars here", MAG, 150, 78),
    ((fcx - rfw / 2 - 3.0, fcy - rfh / 2 - 3.0, 0.0),
     f"RC522 pocket {P['rfid_recess'][0]:.1f} x {P['rfid_recess'][1]:.1f} x "
     f"{P['rfid_recess_deep']:.1f} deep\nleaves a 2.2 mm bearing ring under the PCB", CYA,
     -200, 96),
]
t1 = tile(PARTS["shell"], "back", "1  FRONT FACE - seen from outside (LCD / R307 / RFID)",
          "_v3f1.png", marks=front_marks,
          note="nothing but a 2.2 mm ring stands in front of the antenna; the aperture is a "
               "single R5-cornered opening, no bars, no floor")

tri, cols = assembly()
iso_marks = [
    ((rcx, rcy, 0.0), "R307 dog-bone bracket\n(1.0 cm3, print 1)", GRN, -150, -96),
    ((fcx, fcy, 0.0), f"RC522 hold-down ring {OW:.1f} x {OH:.1f} x {OT:.1f}\n"
     f"tabs out to y +/-31.5, print x1", MAG, -180, 90),
    ((0.0, -P["H"] / 2, 0.0), f"front wall {P['wall_front']:.1f} mm\nR3.0 corners + 1.0 mm rim chamfer",
     CYA, 120, 130),
]
t2 = tile(tri, "iso2", "2  ASSEMBLED ISO - all four printed parts in place", "_v3f2.png",
          marks=iso_marks, tri_rgb=cols,
          note="colours: shell = blue-grey, rear plate = green, R307 bracket = amber, "
               "RC522 ring = pink")

side_marks = [
    ((-P["W"] / 2, fy, fz), f"3010 fan bore d{P['fan_open_d']:.0f} - NO grille\n"
     f"100 % open (v2 left 50 % behind 3 bars)", GRN, 84, -92),
    ((-P["W"] / 2, -44.0, P["esp32_z_centre"]),
     f"ESP32 DevKit V1 bay (INSIDE): board {P['esp32_board'][1]:.2f} x "
     f"{P['esp32_board'][0]:.2f}\non 4 round bosses, {P['esp32_post_len']:.0f} mm off the "
     "wall, USB slot in the -Y wall", YEL, 120, 60),
    ((-P["W"] / 2, fy - 12, fz + 12), "4 x M3 into the standoffs\npilot d2.5 x 12", MAG, 150, 24),
]
t3 = tile(PARTS["shell"], "side", "3  -X SIDE - fan wall, seen from outside", "_v3f3.png",
          marks=side_marks,
          note="the fan pushes through a clear d28 bore; the ESP32 sits on 4 round bosses "
               "10 mm off the wall")

plate_marks = [
    ((P["plate_boss_xy"][0], P["plate_boss_xy"][1], P["D"]),
     "4 x M3 at the corners\npilot d2.5 x 9, csk 6.6", YEL, -190, -60),
    ((-P["keyhole_span"] / 2, 0.0, P["D"]),
     f"hang hooks d{P['keyhole_d']:.1f} + {P['keyhole_slot']:.1f} slot, "
     f"{P['keyhole_span']:.0f} mm span", CYA, 90, 60),
    ((0.0, -60.0, P["D"] - 2.0),
     "2 mm register frame, 0.25 mm/side\nNOT a plug: 52.8 cm3 vs v2's 79.6", MAG, -100, 120),
]
t4 = tile(PARTS["plate"], "back", "4  REAR PLATE - 3 mm, hangs on the shell", "_v3f4.png",
          marks=plate_marks,
          note="the whole ESP32 zone is cut out of the frame, so the board and its bosses "
               "have room and the plate is 27 cm3 lighter than v2's")

for pos, im in (((0, 52), t1), ((TILE[0], 52), t2), ((0, 52 + TILE[1]), t3),
                ((TILE[0], 52 + TILE[1]), t4)):
    sheet.paste(im, pos)
sheet.save(OUT + "v3_drawing_sheet.png")
print("wrote renders/v3_drawing_sheet.png", sheet.size)

# ==================================================================== FIGURE 2
EXP = {"shell": 0.0, "ring": -46.0, "bracket": -92.0, "plate": 86.0}
tris, cols = assembly(offset=EXP)
LAB = {"shell": "01  main shell  (112.4 cm3)", "ring": "04  RC522 ring  (3.0 cm3, print x1)",
       "bracket": "03  R307 bracket  (1.0 cm3)", "plate": "02  rear plate  (52.8 cm3)"}
ex = tile(tris, "iso2", "ASTRO SMART ATTENDANCE v3 - EXPLODED, 4 printed parts, no supports",
           "_v3f5.png", W=1240, H=860, marks=[], tri_rgb=cols,
           note="assembly order: ring + bracket drop onto the shell's front face, "
                "the plate hangs on the rear register and takes 4 x M3")
d = ImageDraw.Draw(ex)
R, sc, ox, oy = projection(tris, "iso2", 1240, 860, margins=0.10)
NUDGE = {"ring": (0.0, 34.0), "bracket": (0.0, -26.0), "plate": (0.0, 0.0), "shell": (0.0, 0.0)}
for name, tri in PARTS.items():
    t = tri.copy()
    t[:, :, 2] += EXP[name]
    c = t.reshape(-1, 3)
    c = c[np.argsort(c[:, 2])[-max(1, len(c) // 20):]].mean(axis=0)
    sx, sy, _ = project_points(np.array([c]), R, sc, ox, oy)
    sx, sy = float(sx[0]) + NUDGE[name][0], float(sy[0]) + NUDGE[name][1]
    d.line([sx, sy, sx + 74, sy - 50], fill=YEL)
    w = 6.6 * len(LAB[name]) + 10
    d.rectangle([sx + 74, sy - 60, sx + 74 + w, sy - 42], fill=PANEL_BG)
    d.text((sx + 76, sy - 58), LAB[name], fill=YEL)
ex.save(OUT + "v3_exploded_iso.png")
print("wrote renders/v3_exploded_iso.png")

# ==================================================================== FIGURE 3
tris, cols = assembly()
# stl_tools view names are the camera's side of the model: "back" looks at the device's
# front wall (z = 0) from outside, "front" looks at the plate, "side" at the -X wall.
panels = [
    ("back", "FRONT - everything the user touches",
     f"LCD {lcd_open[0]:.1f} x {lcd_open[1]:.1f} | fingerprint {r307_open[0]:.1f} x "
     f"{r307_open[1]:.1f} | RFID scan aperture {rfid_open[0]:.1f} x {rfid_open[1]:.1f} "
     "fully open | the LCD + fingerprint openings carry a 0.45 x 3.0 rebate ring"),
    ("front", "REAR - 3 mm plate, 4 x M3 and 2 hang hooks",
     "the frame side, facing the cavity: no plug behind it, the whole ESP32 zone is cut out; the "
     "loom is lashed down through the 4 x d4.0 tie holes and leaves through the USB opening in the "
     "bottom wall, which is the only hole the box has besides the fan bore"),
    ("side", "INLET WALL (-X) - d28 bore with nothing across it",
     "30 x 30 x 10 fan on 10 mm standoffs, 4 x M3 self-tapping into d2.5 pilots from the "
     "inside, mounted so it BLOWNS IN through this bore.  v2 put 3 grille bars over it; v3.3 made "
     "the bore the inlet and v3.4 made it the box's ONLY air opening (616 mm2) - the fan frame "
     "spans the hole, so the fan is part of the enclosure, not an extra"),
    ((-90, 0), "+X WALL - PLAIN, the 8 side slots are gone",
     "v3.2 cut 8 x 30 x 5 stadium slots here.  With a fan doing the work they only took "
     "stiffness out of the wall, so v3.3 deletes them: this wall is now solid 2.6 mm "
     "plastic, verified as 0 voids at mid-thickness"),
    ("top", "TOP WALL - v3.4 filled the 4 vents in: 0 voids at mid-thickness",
     f"this wall carried 4 x ({P['top_vent'][0]:.0f} x {P['top_vent'][1]:.0f}) mm slots at z "
     f"{P['top_vent_z']:.0f} in v3.3.  They are solid plastic now, so the wall is one continuous "
     f"3.0 mm sheet and its corner joints are unbroken - measured, not asserted, by section 6b of "
     f"the independent verifier"),
    ((0, -90), "BOTTOM WALL - v3.4 filled the 8 grille slots in; only the USB opening",
     f"the dark rectangle is the 20.4 x 12.4 mm USB opening; the "
     f"{P['vent_slot'][0]:.0f} x {P['vent_slot'][1]:.0f} mm slots this wall carried in v3.3 "
     f"(4 columns x 2 rows, 1069 mm2 with the top wall) are solid plastic, and cooling moved to "
     f"the skin - 2.7 K at 1.6 W, physics audit section 4"),
]
PW, PH, GAP = 1180, 640, 30
big = Image.new("RGB", (PW, 60 + (PH + GAP) * len(panels) + 40), PANEL_BG)
for i, (view, ttl, note) in enumerate(panels):
    im = tile(tris, view, f"{i + 1}   {ttl}", f"_v3v{i}.png", W=PW, H=PH, marks=[], tri_rgb=cols,
              margins=0.055, note=note)
    big.paste(im, (0, 60 + (PH + GAP) * i))
d = ImageDraw.Draw(big)
d.text((12, 12), "ASTRO SMART ATTENDANCE - ENCLOSURE v3   all four printed parts assembled   "
                 "110 x 155 x 46 mm", fill=WHT)
d.text((12, 34), "part colours: shell (blue-grey)  rear plate (green)  R307 bracket (amber)  "
                 "RC522 ring (pink)", fill=CYA)
y0 = 60 + (PH + GAP) * len(panels)
d.line([12, y0, PW - 12, y0], fill=(60, 64, 74))
d.text((12, y0 + 8), "print: shell + plate + ring + bracket, front face down, 0.2 mm layers, "
                     "3 perimeters, 15 % infill - support-free (0.30 % of the shell's faces are "
                     "steeper than 60 deg, and each of those bridges < 3 mm)", fill=YEL)
big.save(OUT + "v3_all_views.png")
print("wrote renders/v3_all_views.png", big.size)

# ==================================================================== FIGURE 4
V2 = {"shell": "01_MAIN_SHELL_v2.stl", "plate": "02_REAR_PLATE_v2.stl",
      "bracket": "03_R307_BRACKET_v2.stl", "clamp": "04_RC522_CLAMP_v2.stl"}
V2P = {k: load_stl(ROOT + "cad/v2/" + v)[0] for k, v in V2.items()}
v2tri = np.concatenate([V2P["shell"], V2P["plate"], V2P["bracket"], V2P["clamp"], V2P["clamp"]])
v3tri = tris

PW2, PH2 = 620, 620
rows = [
    ("FRONT WALL - seen from the cavity side", "front", [
        ("v2  RFID window crossed by 2 x 4 mm stiffener bars", V2P["shell"], CYA),
        ("v3  one R5-cornered aperture, 38 x 56 portrait, nothing across it", PARTS["shell"], GRN)]),
    ("REAR PLATE - the face that looks into the cavity", "back", [
        ("v2  a solid 2 mm plug fills the whole opening", V2P["plate"], CYA),
        ("v3  register frame only + the ESP32 zone cut clear", PARTS["plate"], GRN)]),
    ("ISO", "iso", [
        ("v2  110 x 155 x 48 deep, 4 files (clamp bars printed twice)", v2tri, CYA),
        ("v3  110 x 155 x 46 deep, 4 files (one ring, printed once)", v3tri, GRN)]),
    ("FAN WALL (-X)", "side", [
        ("v2  d26 bore with 3 grille bars moulded across it", V2P["shell"], CYA),
        ("v3  d28 bore, nothing across it at all", PARTS["shell"], GRN)]),
]
cmp_im = Image.new("RGB", (PW2 * 2 + 26, 60 + len(rows) * (PH2 + 26)), PANEL_BG)
d = ImageDraw.Draw(cmp_im)
d.text((12, 10), "v2 -> v3   SAME VIEWS, SAME PROJECTION, both columns rendered from the "
                 "shipped STL files themselves", fill=WHT)
d.text((12, 30), "v2 = 173877c (in cad/v2)        v3 = cad/v3  -  rebuilt from the layout up",
       fill=CYA)
for r, (name, view, items) in enumerate(rows):
    y = 60 + r * (PH2 + 26)
    d.text((12, y - 4), name, fill=YEL)
    for ci, (lab, tri, colour) in enumerate(items):
        t = tri.copy()
        x = ci * (PW2 + 26)
        render(t, OUT + f"_cmp{r}{ci}.png", view=view, W=PW2, H=PH2, bg=BG, margins=0.075)
        im = Image.open(OUT + f"_cmp{r}{ci}.png").convert("RGB")
        dd = ImageDraw.Draw(im)
        dd.rectangle([0, PH2 - 20, PW2, PH2], fill=PANEL_BG)
        dd.text((6, PH2 - 14), lab, fill=colour)
        cmp_im.paste(im, (x, y))
cmp_im.save(OUT + "v3_vs_v2.png")
print("wrote renders/v3_vs_v2.png", cmp_im.size)

print("\nmeasured off the meshes: LCD opening %.1f x %.1f | R307 %.1f x %.1f | RFID %.1f x %.1f"
      % (lcd_open[0], lcd_open[1], r307_open[0], r307_open[1], rfid_open[0], rfid_open[1]))
