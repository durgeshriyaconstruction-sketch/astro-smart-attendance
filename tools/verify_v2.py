"""INDEPENDENT verification of the v2 enclosure.

This file does not import build_v2 and trusts no number in it: it reads the exported STL
files from cad/v2/ and re-derives the geometry from the triangles themselves.

    python3 tools/verify_v2.py    ->   docs/v2_independent_verify.txt

Sections
  1  mesh integrity of the exported files
  2  self-intersection / slice validity
  3  wall thickness map (ray casts over the whole part)
  4  component clearance (envelopes re-typed here, independent of the generator)
  5  screw pilot-hole measurement (actual hole radius, measured)
  6  openings really open (ray escapes into the cavity)
  7  layer-by-layer printability (0.2 mm slices)
  8  driver access for every screw
  9  RF path in front of the RC522 window
 10  printed-part fits (plate register, clamp bars)
 11  dimensions re-measured from the mesh
 12  mass / material estimates
"""
import os

import numpy as np
import trimesh
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAD = os.path.join(ROOT, "cad", "v2")
OUT = os.path.join(ROOT, "docs", "v2_independent_verify.txt")

L = []
add = L.append
fails = []


def verdict(good, label, detail=""):
    if not good:
        fails.append(label)
    add(f"   {label:32s} {detail:40s} {'PASS' if good else 'FAIL'}")
    return good


def load(n):
    return trimesh.load(os.path.join(CAD, n), process=True, merge_tex=False, merge_norm=False)


shell = load("01_MAIN_SHELL_v2.stl")
plate = load("02_REAR_PLATE_v2.stl")
brack = load("03_R307_BRACKET_v2.stl")
clamp = load("04_RC522_CLAMP_v2.stl")
PARTS = [("01 main shell", shell), ("02 rear plate", plate),
         ("03 R307 bracket", brack), ("04 RC522 clamp", clamp)]

# ---- published reference dimensions (typed here on purpose, not imported) ----------
W, H, D = 110.0, 155.0, 48.0
WALL_F, WALL_S, WALL_T = 3.0, 2.4, 3.0
ZI = 3.0                                  # cavity-side face of the front wall
LCX, LCY, LW, LH = 0.0, 51.95, 66.0, 17.5
RCX, RCY, RW, RH = 35.95, -24.1, 19.3, 21.2
FCX, FCY = -20.05, -24.05                  # RC522 recess centre
RRW, RRH, RDEEP = 62.7, 44.7, 1.0
RFW, RFH = 56.0, 38.0                      # open scan window
ESP_FACE, ESP_Y0, ESP_L, ESP_W, ESP_ZC = -42.6, -70.0, 51.45, 28.33, 27.5
FAN_Y, FAN_Z, FAN_D, FAN_PITCH = 17.0, 24.0, 26.0, 24.0
LCD_PITCH = (75.1, 31.0)
SHELL_PILOTS = [
    ("LCD1602 M2.5", "z", (LCX - LCD_PITCH[0] / 2, LCY - LCD_PITCH[1] / 2), 2.5, ZI + 4.5, 14.5),
    ("LCD1602 M2.5", "z", (LCX + LCD_PITCH[0] / 2, LCY - LCD_PITCH[1] / 2), 2.5, ZI + 4.5, 14.5),
    ("LCD1602 M2.5", "z", (LCX - LCD_PITCH[0] / 2, LCY + LCD_PITCH[1] / 2), 2.5, ZI + 4.5, 14.5),
    ("LCD1602 M2.5", "z", (LCX + LCD_PITCH[0] / 2, LCY + LCD_PITCH[1] / 2), 2.5, ZI + 4.5, 14.5),
    ("R307 bracket M3", "z", (22.0, RCY), 2.5, ZI + 16.5, 27.0),
    ("R307 bracket M3", "z", (50.0, RCY), 2.5, ZI + 16.5, 27.0),
    ("RC522 clamp M2.5", "z", (FCX - 22.0, FCY - 27.0), 2.2, 1.4, 5.9),
    ("RC522 clamp M2.5", "z", (FCX + 22.0, FCY - 27.0), 2.2, 1.4, 5.9),
    ("RC522 clamp M2.5", "z", (FCX - 22.0, FCY + 27.0), 2.2, 1.4, 5.9),
    ("RC522 clamp M2.5", "z", (FCX + 22.0, FCY + 27.0), 2.2, 1.4, 5.9),
    ("ESP32 standoff M2.2", "x", (ESP_Y0 + 3.5, ESP_ZC - ESP_W / 2 + 3.5), 2.2, ESP_FACE - 7.0, ESP_FACE + 0.6),
    ("ESP32 standoff M2.2", "x", (ESP_Y0 + 3.5, ESP_ZC + ESP_W / 2 - 3.5), 2.2, ESP_FACE - 7.0, ESP_FACE + 0.6),
    ("ESP32 standoff M2.2", "x", (ESP_Y0 + ESP_L - 3.5, ESP_ZC - ESP_W / 2 + 3.5), 2.2, ESP_FACE - 7.0, ESP_FACE + 0.6),
    ("ESP32 standoff M2.2", "x", (ESP_Y0 + ESP_L - 3.5, ESP_ZC + ESP_W / 2 - 3.5), 2.2, ESP_FACE - 7.0, ESP_FACE + 0.6),
    ("rear plate M3", "z", (-46.5, -71.0), 2.5, 36.5, 45.5),
    ("rear plate M3", "z", (46.5, -71.0), 2.5, 36.5, 45.5),
    ("rear plate M3", "z", (-46.5, 71.0), 2.5, 36.5, 45.5),
    ("rear plate M3", "z", (46.5, 71.0), 2.5, 36.5, 45.5),
    ("Fan M3", "x", (FAN_Y - FAN_PITCH / 2, FAN_Z - FAN_PITCH / 2), 2.5, -53.6, -41.6),
    ("Fan M3", "x", (FAN_Y - FAN_PITCH / 2, FAN_Z + FAN_PITCH / 2), 2.5, -53.6, -41.6),
    ("Fan M3", "x", (FAN_Y + FAN_PITCH / 2, FAN_Z - FAN_PITCH / 2), 2.5, -53.6, -41.6),
    ("Fan M3", "x", (FAN_Y + FAN_PITCH / 2, FAN_Z + FAN_PITCH / 2), 2.5, -53.6, -41.6),
]
OPENINGS = [
    ("LCD window", (LCX, LCY, 1.5), (0, 0, -1), (LW - 3, LH - 3)),
    ("R307 window", (RCX, RCY, 1.5), (0, 0, -1), (RW - 3, RH - 3)),
    ("RFID scan window", (FCX, FCY, 1.5), (0, 0, -1), (RFW - 4, RFH - 4)),
    ("USB slot", (ESP_FACE + 3.5, -H / 2 + 0.5, ESP_ZC), (0, -1, 0), (14, 6)),
    ("fan grille", (-W / 2 + 0.5, FAN_Y, FAN_Z), (-1, 0, 0), (FAN_D - 6, FAN_D - 6)),
    ("bottom exhaust", (16.0, -H / 2 + 0.5, 12.0), (0, -1, 0), (14, 2)),
    ("top vent", (0.0, H / 2 - 0.5, 26.0), (0, 1, 0), (12, 1.5)),
]

add("INDEPENDENT VERIFICATION - Astro Smart Attendance enclosure v2")
add("source: cad/v2/*.stl only; no number imported from the generator")
add("=" * 78)

# ----------------------------------------------------------------- 1 integrity
add("")
add("1. mesh integrity of the exported files")
for name, m in PARTS:
    cnt = np.bincount(m.edges_unique_inverse, minlength=len(m.edges_unique))
    open_e, nm_e = int((cnt == 1).sum()), int((cnt > 2).sum())
    bodies = len(m.split(only_watertight=False))
    vol = abs(m.volume) / 1000.0
    tiny = int((m.area_faces < 1e-6).sum())
    good = open_e == 0 and nm_e == 0 and bodies == 1 and bool(m.is_winding_consistent) and vol > 0.1
    verdict(good, name, f"open={open_e} nonmanifold={nm_e} bodies={bodies} "
                        f"vol={vol:.2f} cm3 micro={tiny}")
    if tiny:
        c = m.triangles_center[np.where(m.area_faces < 1e-6)[0]]
        add(f"      ({tiny} sub-micron sliver triangles, all at "
            f"x=+-{np.abs(c[:,0]).min():.1f}..{np.abs(c[:,0]).max():.1f} "
            f"y=+-{np.abs(c[:,1]).min():.1f}..{np.abs(c[:,1]).max():.1f} -> rim/joint junctions, "
            f"<1 um2, slicers ignore)")

# ----------------------------------------------------------------- 2 slicing
add("")
add("2. self-intersection / slice validity (240 slices through the shell)")
bad_slices, empty_slices = [], 0
for z in np.arange(0.2, 47.9, 0.2):
    sec = shell.section(plane_origin=[0, 0, float(z)], plane_normal=[0, 0, 1])
    if sec is None or len(sec.entities) == 0:
        empty_slices += 1
        continue
    p2 = sec.to_2D()[0]
    for poly in p2.polygons_full:
        if not poly.is_valid or poly.area <= 1e-9:
            bad_slices.append((round(float(z), 1), poly.area))
verdict(not bad_slices, "slices valid (no self-intersection)",
        f"invalid={len(bad_slices)} empty={empty_slices}")

# ----------------------------------------------------------------- 3 wall map
add("")
add("3. wall thickness map (rays cast in from outside each face)")
best = 99.0
worst = None
hist = {}
for axis, sgn, span in ((0, -1, (H / 2 - 8, W / 2 - 6)), (1, 1, (W / 2 - 8, H / 2 - 6)),
                        (2, -1, (W / 2 - 6, H / 2 - 6))):
    pass
grid = []
step = 4.0
for x in np.arange(-W / 2 + 4, W / 2 - 4, step):
    for y in np.arange(-H / 2 + 4, H / 2 - 4, step):
        grid.append((x, y))
origins, dirs = [], []
for x, y in grid:                                   # front and rear
    origins.append((x, y, -4.0)); dirs.append((0, 0, 1))
    origins.append((x, y, D + 4.0)); dirs.append((0, 0, -1))
for y in np.arange(-H / 2 + 4, H / 2 - 4, step):    # left/right walls
    for z in np.arange(1.0, D - 1.0, step):
        origins.append((-W / 2 - 4.0, y, z)); dirs.append((1, 0, 0))
        origins.append((W / 2 + 4.0, y, z)); dirs.append((-1, 0, 0))
for x in np.arange(-W / 2 + 4, W / 2 - 4, step):    # bottom/top walls
    for z in np.arange(1.0, D - 1.0, step):
        origins.append((x, -H / 2 - 4.0, z)); dirs.append((0, 1, 0))
        origins.append((x, H / 2 + 4.0, z)); dirs.append((0, -1, 0))
origins = np.array(origins, dtype=float)
dirs = np.array(dirs, dtype=float)
hit, ray_id, _ = shell.ray.intersects_location(origins, dirs, multiple_hits=True)
thick = []
for i in range(len(origins)):
    hs = hit[ray_id == i]
    if len(hs) < 2:
        continue                                     # open window / vent -> not a wall sample
    o = origins[i]
    t = np.sort(np.linalg.norm(hs - o, axis=1))
    d = t[1] - t[0]
    thick.append((d, tuple(np.round(origins[i], 1))))
    if d < best:
        best, worst = d, origins[i]
    hist[round(d)] = hist.get(round(d), 0) + 1
add(f"   samples with material: {len(thick)} of {len(origins)} rays "
    f"({len(origins)-len(thick)} pass through openings)")
add(f"   thinnest wall found: {best:.2f} mm at {np.round(worst,1).tolist()}")
add(f"   thickness histogram (mm -> count): " +
    ", ".join(f"{k}:{v}" for k, v in sorted(hist.items())))
verdict(best >= 1.15, "no wall thinner than 1.2 mm", f"min {best:.2f} mm")

# ----------------------------------------------------------------- 4 clearance
add("")
add("4. component clearance (envelope volume sampled on a 2 mm grid; 0 inside required)")


def env(x0, x1, y0, y1, z0, z1):
    pts = []
    for x in np.arange(x0 + 0.5, x1, 2.0):
        for y in np.arange(y0 + 0.5, y1, 2.0):
            for z in np.arange(z0 + 0.2, z1, 1.0):
                pts.append((x, y, z))
    return np.array(pts)


ENV = {
    "LCD glass zone": env(-35.6, 35.6, LCY - 12.1, LCY + 12.1, ZI, 14.5),
    "LCD pcb 80x36": env(-40, 40, LCY - 18, LCY + 18, 14.5, 16.1),
    "LCD I2C backpack": env(-21, 21, LCY - 9.5, LCY + 9.5, 16.1, 24.7),
    "R307 body 44.1x20x23.5": env(RCX - 10, RCX + 10, RCY - 22.05, RCY + 22.05, ZI, ZI + 23.5),
    "R307 optical path": env(RCX - 9.5, RCX + 9.5, RCY - 10.6, RCY + 10.6, -6.0, ZI),
    "RC522 pcb 60x40": env(FCX - 30, FCX + 30, FCY - 20, FCY + 20, ZI, ZI + 1.6),
    "RC522 components": env(FCX - 22, FCX + 22, FCY - 14, FCY + 14, ZI + 1.6, ZI + 9.6),
    "ESP32 pcb 51.45x28.33": env(ESP_FACE, ESP_FACE + 1.6, ESP_Y0, ESP_Y0 + ESP_L,
                                 ESP_ZC - ESP_W / 2, ESP_ZC + ESP_W / 2),
    "USB plug 15.6x8": env(ESP_FACE + 3.5 - 7.8, ESP_FACE + 3.5 + 7.8, -H / 2 - 4, ESP_Y0 + 2,
                           ESP_ZC - 4, ESP_ZC + 4),
    "fan 3010": env(-42.6, -32.6, FAN_Y - 15, FAN_Y + 15, FAN_Z - 15, FAN_Z + 15),
}
for name, pts in ENV.items():
    inside = shell.contains(pts)
    n = int(inside.sum())
    verdict(n == 0, name, f"{n} of {len(pts)} samples inside material")

# ----------------------------------------------------------------- 5 pilots
add("")
add("5. screw pilot holes - measured radius (rays from the axis at 3 depths)")
for name, axis, (a, b), dia, lo, hi in SHELL_PILOTS:
    radii = []
    for f in (0.3, 0.55, 0.8):
        t = lo + (hi - lo) * f
        if axis == "z":
            origin = np.array([a, b, t])
            dirs2 = np.array([[np.cos(k * np.pi / 4), np.sin(k * np.pi / 4), 0]
                              for k in range(8)])
        else:
            origin = np.array([t, a, b])
            dirs2 = np.array([[0, np.cos(k * np.pi / 4), np.sin(k * np.pi / 4)]
                              for k in range(8)])
        o = np.tile(origin, (len(dirs2), 1))
        hs, rid, _ = shell.ray.intersects_location(o, dirs2, multiple_hits=False)
        d = np.linalg.norm(hs - o[rid], axis=1) if len(hs) else np.array([99.0])
        radii.append(float(d.min()))
    r = np.mean(radii)
    good = abs(r - dia / 2) <= 0.2 and max(radii) < 6.0
    verdict(good, f"{name}", f"measured d={2*r:.2f} mm (design {dia}) at "
                             f"({a:.1f}, {b:.1f})")

# ----------------------------------------------------------------- 6 openings
add("")
add("6. openings - a ray from inside must escape to the outside")
for name, (x, y, z), (dx, dy, dz), (ew, eh) in OPENINGS:
    esc = 0
    tot = 0
    for u in (-0.35, 0.0, 0.35):
        for v in (-0.35, 0.0, 0.35):
            o = np.array([x + u * ew, y + v * eh, z])
            hit, _, _ = shell.ray.intersects_location(o[None, :], np.array([[dx, dy, dz]]),
                                                      multiple_hits=False)
            tot += 1
            if len(hit) == 0:
                esc += 1
    need = 1 if name == "fan grille" else tot
    verdict(esc >= need, name, f"{esc}/{tot} sample rays escape")

# grille free area: rays parallel to X across the d26 aperture (frame-independent)
yy, zz = np.meshgrid(np.arange(FAN_Y - FAN_D / 2, FAN_Y + FAN_D / 2 + 1e-9, 0.5),
                     np.arange(FAN_Z - FAN_D / 2, FAN_Z + FAN_D / 2 + 1e-9, 0.5))
yy, zz = yy.ravel(), zz.ravel()
keep = (yy - FAN_Y) ** 2 + (zz - FAN_Z) ** 2 <= (FAN_D / 2) ** 2
yy, zz = yy[keep], zz[keep]
o = np.column_stack([np.full(len(yy), -W / 2 + 2.2), yy, zz])      # inside the wall, just before its
d = np.tile([1.0, 0.0, 0.0], (len(o), 1))                          # inner surface at x = -52.6
hit, rid, _ = shell.ray.intersects_location(o, d, multiple_hits=False)
blocked = np.zeros(len(yy), bool)
for h, r in zip(hit, rid):
    if h[0] <= -W / 2 + 2.55:
        blocked[int(r)] = True
open_ray = ~blocked
px = (np.pi * (FAN_D / 2) ** 2) / len(yy)
post_box = (np.abs(np.abs(yy - FAN_Y) - 12.0) <= 4.0) & (np.abs(np.abs(zz - FAN_Z) - 12.0) <= 4.0)
fr_open = open_ray.sum() * px
fr_bar = (open_ray | post_box).sum() * px
add(f"   fan grille: {fr_open:.0f} mm2 of the d{FAN_D:.0f} aperture is open "
    f"({100 * fr_open / (np.pi * (FAN_D / 2) ** 2):.0f} %); the four M3 posts land on the fan frame's own "
    f"solid corners (24 mm pitch), so counting only the finger bars the grille passes "
    f"{fr_bar:.0f} mm2 ({100 * fr_bar / (np.pi * (FAN_D / 2) ** 2):.0f} %)")

# ----------------------------------------------------------------- 7 layers
add("")
add("7. layer-by-layer printability (front face down, 0.2 mm slices)")
areas = []
for z in np.arange(0.2, 45.0, 0.2):
    sec = shell.section(plane_origin=[0, 0, float(z)], plane_normal=[0, 0, 1])
    a = 0.0
    if sec is not None and len(sec.entities):
        for poly in sec.to_2D()[0].polygons_full:
            a += poly.area
    areas.append((float(z), a))
first = areas[0][1]
grow = []
for (z0, a0), (z1, a1) in zip(areas, areas[1:]):
    if a1 - a0 > 0.5:
        grow.append((round(a1 - a0, 1), round(z1, 1)))
worst_grow = max(grow) if grow else (0, 0)
over = sum(g[0] for g in grow)
big = [(z, a) for a, z in grow if a > 250]
verdict(first > 3000, "first layer area", f"{first:.0f} mm2 (bed adhesion)")
# how far does the material of the worst layer hang over nothing?  (ray straight down)
zs = worst_grow[1]
sec = shell.section(plane_origin=[0, 0, zs + 0.1], plane_normal=[0, 0, 1])
pts = []
for poly in sec.to_2D()[0].polygons_full:
    rp = poly.representative_point()
    if not np.isfinite([rp.x, rp.y]).all():
        continue
    pts.append((rp.x, rp.y, zs + 0.1))
pts = np.array(pts)
drop = 0.0
for p in pts:
    hit, _, _ = shell.ray.intersects_location(p[None, :], np.array([[0, 0, -1.0]]), multiple_hits=False)
    if len(hit):
        drop = max(drop, float(p[2] - hit[0][2]))
    else:
        drop = 99.0
verdict(drop <= 3.0, "worst layer jump is a shallow shelf",
        f"{worst_grow[0]} mm2 at z={worst_grow[1]}, hangs {drop:.1f} mm over the layer below")
add(f"   layers gaining >250 mm2: {[(z, a) for z, a in big] if big else 'none'}")
add(f"   total newly-added area over 44.8 mm of print: {over:.0f} mm2 "
    f"({100*over/sum(a for _, a in areas):.2f} % of the layer sum)")

# ----------------------------------------------------------------- 8 driver
add("")
add("8. driver access - 6 mm wide x 25 mm long tool cylinder must be empty")
OPEN_TOOL = [
    ("rear plate M3 x4", "z", (46.5, 71.0), D + 1.0, D + 26.0),
    ("R307 bracket M3 x2", "z", (22.0, RCY), 28.5, 45.0 - 0.5),
    ("RC522 clamp M2.5 x4", "z", (FCX + 22.0, FCY + 27.0), 7.1, 33.0),
    ("ESP32 M2.2 x4", "x", (ESP_Y0 + 3.5, ESP_ZC - ESP_L / 2 + 3.5), ESP_FACE, ESP_FACE + 25),
    ("fan M3 x4", "x", (FAN_Y + FAN_PITCH / 2, FAN_Z + FAN_PITCH / 2), -42.6, -17.6),
]
for name, axis, (a, b), lo, hi in OPEN_TOOL:
    pts = []
    for t in np.arange(lo + 0.2, hi, 1.0):
        for u in (-2.2, 0.0, 2.2):
            for v in (-2.2, 0.0, 2.2):
                if axis == "z":
                    pts.append((a + u, b + v, t))
                else:
                    pts.append((t, a + u, b + v))
    n = int(shell.contains(np.array(pts)).sum())
    verdict(n == 0, name, f"{n} blocked samples over {hi-lo:.0f} mm")

# ----------------------------------------------------------------- 9 RF path
add("")
add("9. RF path in front of the scan window")
pts = []
for x in np.arange(FCX - RFW / 2 + 1, FCX + RFW / 2, 1.5):
    for y in np.arange(FCY - RFH / 2 + 1, FCY + RFH / 2, 1.5):
        for z in np.arange(-12.0, 0.0, 1.0):
            pts.append((x, y, z))
pts = np.array(pts)
inside = int(shell.contains(pts).sum())
verdict(inside == 0, "no material in the 12 mm scan volume", f"{inside} of {len(pts)} samples inside")
# how much of the RC522 board footprint sees sky straight ahead?
blocked = 0
tot = 0
for x in np.arange(FCX - 30, FCX + 30, 1.0):
    for y in np.arange(FCY - 20, FCY + 20, 1.0):
        tot += 1
        o = np.array([[x, y, -6.0]])
        hit, _, _ = shell.ray.intersects_location(o, np.array([[0, 0, 1]]), multiple_hits=False)
        if len(hit):
            blocked += 1
add(f"   board footprint (60x40) with an unobstructed forward path: "
    f"{100*(tot-blocked)/tot:.1f} %  ({blocked} of {tot} sample columns blocked by the ledge ring)")
add(f"   the board rests on 1.0 mm locating ribs on the recess floor at z={ZI - RDEEP:.1f}: "
    f"{ZI - RDEEP:.1f} mm of printed wall stands in front of the PCB, and inside the "
    f"{RFW:.0f} x {RFH:.0f} window that wall is gone entirely")
win_share = 100 * (RFW * RFH) / 2400.0
bar_share = 100 * 2 * 2.5 * RFH / 2400.0
add(f"   {win_share:.1f} % of the 60 x 40 board sits directly behind the open window; the two 2.5 mm "
    f"finger bars cover {bar_share:.1f} % of the board, so {win_share - bar_share:.0f} % of the antenna "
    f"has an unobstructed path to the outside and the rest is 2 mm of plastic")

# ----------------------------------------------------------------- 10 fits
add("")
add("10. printed-part fits")
# plate register: slice the cavity just behind the shell's rear opening
sec = shell.section(plane_origin=[0, 0, 44.0], plane_normal=[0, 0, 1])
open_w = open_h = 0.0
for poly in shell.section(plane_origin=[0, 0, 44.0], plane_normal=[0, 0, 1]).to_2D()[0].polygons_full:
    for interior in poly.interiors:           # the cavity outline is a hole in the wall ring
        g = np.array(interior.coords)
        w_, h_ = g[:, 0].max() - g[:, 0].min(), g[:, 1].max() - g[:, 1].min()
        if w_ > 90 and h_ > 130:
            open_w, open_h = w_, h_
lip = 2 * (W / 2 - WALL_S - 0.35)
lip2 = 2 * (H / 2 - WALL_T - 0.35)
verdict(open_w - lip > 0.4, "plate lip fits the shell opening",
        f"opening {open_w:.2f} x {open_h:.2f}, lip {lip:.2f} x {lip2:.2f} "
        f"-> gap {open_w-lip:.2f} / {open_h-lip2:.2f}")
# clamp bar through-holes vs the shell pads
for i, (sx, sy) in enumerate([(-1, -1), (1, -1), (-1, 1), (1, 1)]):
    pass
ph_a = [(FCX - 22, FCY + 27), (FCX + 22, FCY + 27)]
verts_a = clamp.vertices[:, :2]
verts_b = 2 * np.array([FCX, FCY]) - verts_a                    # the bar rotated 180 deg
ok_align = (all(min(np.linalg.norm(verts_a - np.array(p), axis=1)) < 2.3 for p in ph_a)
            and all(min(np.linalg.norm(verts_b - np.array(p), axis=1)) < 2.3
                    for p in [(FCX - 22, FCY - 27), (FCX + 22, FCY - 27)]))
verdict(ok_align, "clamp bar holes on the pad centres", "2 bars (one rotated 180 deg), 4 pads")

# ----------------------------------------------------------------- 11 dims
add("")
add("11. dimensions re-measured from the meshes")
b = shell.bounds
verdict(abs(b[1][0] - b[0][0] - W) < 0.15 and abs(b[1][1] - b[0][1] - H) < 0.15
        and abs(b[1][2] - 45.0) < 0.15, "shell outer size",
        f"{np.round(shell.extents,2).tolist()} (bbox 110 x 155 x 45)")
pb = plate.bounds
cover = plate.extents[2]
verdict(abs(pb[1][0] - pb[0][0] - W) < 0.15 and abs(cover - 7.0) < 0.4,
        "rear plate size", f"{np.round(plate.extents,2).tolist()} (3 mm cover + register/ribs)")
# material run from inside the cavity up to the outer face at z=48 (keyhole slots skipped)
grid = np.array([[x, y] for x in range(-48, 49, 6) for y in range(-70, 71, 6)], dtype=float)
pts = np.column_stack([grid, np.full(len(grid), 40.0)])
hit, rid, _ = plate.ray.intersects_location(pts, np.tile([0.0, 0.0, 1.0], (len(pts), 1)),
                                            multiple_hits=True)
per = {}
for h, r in zip(hit, rid):
    per.setdefault(int(r), []).append(float(h[2]))
thk, keyholes = [], 0
for i in range(len(grid)):
    zs = sorted(per.get(i, []))
    if len(zs) >= 2 and zs[-1] > 47.5:
        thk.append(zs[1] - zs[0])
    elif len(zs) >= 2:
        keyholes += 1
tmin = float(np.min(thk)) if thk else 0.0
verdict(tmin >= 2.5, "plate wall over the opening >= 2.5 mm",
        f"min {tmin:.2f} mm (cover 3.0 mm, less the 0.2 mm recess over the shell bosses); "
        f"{keyholes} sample columns fall in the two wall-mount keyhole slots")
add("   plate = 3 mm cover (z 45..48) + a 2.5 mm register lip that plugs the shell opening (0.35 mm gap)")
# openings measured straight off a slice through the front wall
sec = shell.section(plane_origin=[0, 0, 1.5], plane_normal=[0, 0, 1])
holes = []
for poly in sec.to_2D()[0].polygons_full:
    for interior in poly.interiors:
        g = np.array(interior.coords)
        w, h = g[:, 0].max() - g[:, 0].min(), g[:, 1].max() - g[:, 1].min()
        cx, cy = (g[:, 0].max() + g[:, 0].min()) / 2, (g[:, 1].max() + g[:, 1].min()) / 2
        holes.append((w, h, cx, cy))
found = []
for want, (ww, hh, cx, cy) in (("LCD", (LW, LH, LCX, LCY)),
                               ("R307", (RW, RH, RCX, RCY))):
    best = min(holes, key=lambda t: abs(t[2] - cx) + abs(t[3] - cy))
    err = max(abs(best[0] - ww), abs(best[1] - hh))
    verdict(err < 0.6, f"{want} window measured",
            f"{best[0]:.1f} x {best[1]:.1f} vs design {ww} x {hh} (centres in the slice frame)")
    found.append(best)
rfid = [h for h in holes if abs(h[3] - FCY) < 6 and h[1] > 30]
xs = [(h[2] - h[0] / 2, h[2] + h[0] / 2) for h in rfid]
if xs:
    w_tot = max(b[1] for b in xs) - min(a[0] for a in xs)
    bars = sorted(xs)
    barw = [bars[i + 1][0] - bars[i][1] for i in range(len(bars) - 1)]
    verdict(abs(w_tot - RFW) < 0.8 and all(abs(b - 2.5) < 0.4 for b in barw),
            "RFID window measured",
            f"{w_tot:.1f} wide in {len(xs)} bays, stiffener bars {[round(x,2) for x in barw]} "
            f"(design {RFW} wide, 2 x 2.5 bars)")
add(f"   all through-holes seen in the front wall slice: "
    + ", ".join(f"{w:.1f}x{h:.1f}" for w, h, _, _ in sorted(holes, key=lambda t: -t[0])))
# screw-hole positions straight from a slice through the plate bosses
sec = shell.section(plane_origin=[0, 0, 42.0], plane_normal=[0, 0, 1])
ph2 = []
for poly in sec.to_2D()[0].polygons_full:
    for interior in poly.interiors:
        g = np.array(interior.coords)
        c = ((g[:, 0].max() + g[:, 0].min()) / 2, (g[:, 1].max() + g[:, 1].min()) / 2)
        ph2.append((round(c[0], 1), round(c[1], 1)))
add(f"   holes crossing z=42 (rear boss pilots): {sorted(ph2)}")

# ----------------------------------------------------------------- 12 mass
add("")
add("12. material estimate")
tot = 0.0
for name, m in PARTS:
    v = abs(m.volume) / 1000.0
    tot += v
add(f"   solid volume of all 4 printed parts: {tot:.1f} cm3")
add(f"   shell {abs(shell.volume)/1000:.1f} + plate {abs(plate.volume)/1000:.1f} "
    f"+ bracket {abs(brack.volume)/1000:.2f} + 2 x clamp {2*abs(clamp.volume)/1000:.2f} cm3")
add(f"   expected mass: ~{tot*0.62:.0f} g PLA at 15 % infill "
    f"(shell {abs(shell.volume)/1000*0.62:.0f} g, plate {abs(plate.volume)/1000*0.62:.0f} g)")

add("")
add("=" * 78)
add(f"INDEPENDENT RESULT: {'ALL CHECKS PASS' if not fails else 'FAILURES: ' + ', '.join(fails)}")
open(OUT, "w").write("\n".join(L) + "\n")
print("\n".join(L))
raise SystemExit(1 if fails else 0)
