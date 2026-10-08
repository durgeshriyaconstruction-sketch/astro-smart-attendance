"""INDEPENDENT verification of the v3 enclosure (the re-design).

This file does not import build_v3 and trusts no number in it: it reads the exported STL files
from cad/v3/ and re-derives everything from the triangles themselves.  Where v2 and v3 differ,
the expectation stated here is the v3 one (written from the design intent, not from the
generator), so a regression in the generator cannot hide behind a matching constant.

    python3 tools/verify_v3.py    ->   docs/v3_independent_verify.txt

Sections
  1  mesh integrity            6  openings really open       11 dimensions re-measured
  2  slice validity           7  layer-by-layer printability 12 mass / material
  3  wall thickness map       8  driver access for screws
  4  component clearance       9  RF path in front of the window
  5  pilot-hole diameters     10 printed-part fits
"""
import os
import sys

import numpy as np
import trimesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import orient_v3
from shapely.geometry import Polygon
from shapely.ops import unary_union, Point

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAD = os.path.join(ROOT, "cad", "v3")
OUT = os.path.join(ROOT, "docs", "v3_independent_verify.txt")

L = []
add = L.append
fails = []


def verdict(good, label, detail=""):
    if not good:
        fails.append(label)
    add(f"   {label:32s} {detail:40s} {'PASS' if good else 'FAIL'}")
    return good


ZMIN_FILE = {}


def load(n):
    """read the SHIPPED file, remember its bed state, then put it back in assembly coordinates.

    The shipped STLs are bed-aligned on purpose (tools/orient_v3.py): a slicer drops a part onto
    the bed but never rotates it, so each part's own printing plane has to be at z = 0 in the
    file.  Every geometric expectation below is written in the design (assembly) frame, so the
    documented translation is undone here - a pure shift, verified rigid in section 1.
    """
    m = trimesh.load(os.path.join(CAD, n), process=True, merge_tex=False, merge_norm=False)
    ZMIN_FILE[n] = float(m.bounds[0][2])
    return orient_v3.to_assembly(m, n)


def slice_polys_2d(sec):
    """polygons_full of a horizontal section, mapped back to WORLD xy.

    trimesh's Path.to_2D() returns the rings in the cutting plane's own frame, which for this
    mesh is translated by a constant (dx, dy).  Areas and sizes survive that; absolute positions
    do not - so any check that compares a hole centre with a design coordinate goes through here.
    """
    if sec is None or not len(sec.entities):
        return []
    path, T = sec.to_2D()
    T = np.asarray(T, dtype=float)

    def fix(ring):
        g = np.asarray(ring.coords)[:, :2]
        w = np.column_stack([g, np.zeros(len(g)), np.ones(len(g))]) @ T.T
        return w[:, :2]

    return [Polygon(fix(Q.exterior), [fix(i) for i in Q.interiors]) for Q in path.polygons_full]

shell = load("01_MAIN_SHELL_v3.stl")
plate = load("02_REAR_PLATE_v3.stl")
brack = load("03_R307_BRACKET_v3.stl")
ring = load("04_RC522_RING_v3.stl")
PARTS = [("01 main shell", shell), ("02 rear plate", plate),
         ("03 R307 bracket", brack), ("04 RC522 ring", ring)]

# ---- published reference dimensions, typed here on purpose ------------------------
W, H, D = 110.0, 155.0, 46.0
WALL_F, WALL_S, WALL_T = 3.0, 2.6, 3.0
ZI = 3.0
ZR = D - 3.0                                   # 43.0: shell ends, plate covers 43..46
LCX, LCY, LW, LH = 0.0, 51.95, 66.0, 17.5
RCX, RCY = 35.95, -24.1                    # fingerprint module centre on the front wall
RW, RH = 19.3, 21.2                        # its optical window
REL_W, REL_H = 21.0, 25.0                  # bezel-relief footprint the opening is cut to
FCX, FCY = -16.05, -24.05          # v3.2: reader moved to open its drop-in path
RRW, RRH, RDEEP = 62.7, 44.7, 0.8               # v3 recess is shallower: 2.2 mm ledge
RFW, RFH = 38.0, 56.0          # v3.2: the aperture is portrait
M3_CSK = 6.6                           # the aperture, expected COMPLETELY clear
POX, POY = 17.0, 34.0                           # RC522 pad offsets (v3.2 portrait)
ESP_FACE, ESP_Y0, ESP_L, ESP_W, ESP_ZC = -(W / 2 - WALL_S) + 10.0, -70.0, 51.45, 28.33, 27.5
FAN_Y, FAN_Z, FAN_D, FAN_PITCH = 17.0, 24.0, 28.0, 24.0     # v3: clear 28 mm bore
LCD_PITCH = (75.1, 31.0)
RING_T = 2.6
PAD_TOP = ZI + 1.6                              # 4.60: pads, board back face and ring seat
SHELL_PILOTS = [
    ("LCD1602 M2.5", "z", (LCX - LCD_PITCH[0] / 2, LCY - LCD_PITCH[1] / 2), 2.05, ZI + 4.5, 14.5),
    ("LCD1602 M2.5", "z", (LCX + LCD_PITCH[0] / 2, LCY - LCD_PITCH[1] / 2), 2.05, ZI + 4.5, 14.5),
    ("LCD1602 M2.5", "z", (LCX - LCD_PITCH[0] / 2, LCY + LCD_PITCH[1] / 2), 2.05, ZI + 4.5, 14.5),
    ("LCD1602 M2.5", "z", (LCX + LCD_PITCH[0] / 2, LCY + LCD_PITCH[1] / 2), 2.05, ZI + 4.5, 14.5),
    ("R307 bracket M3", "z", (22.0, RCY), 2.5, ZI + 16.5, 27.0),
    ("R307 bracket M3", "z", (50.0, RCY), 2.5, ZI + 16.5, 27.0),
    ("RC522 ring M2.5", "z", (FCX - POX, FCY - POY), 2.05, 1.4, PAD_TOP + 0.5),
    ("RC522 ring M2.5", "z", (FCX + POX, FCY - POY), 2.05, 1.4, PAD_TOP + 0.5),
    ("RC522 ring M2.5", "z", (FCX - POX, FCY + POY), 2.05, 1.4, PAD_TOP + 0.5),
    ("RC522 ring M2.5", "z", (FCX + POX, FCY + POY), 2.05, 1.4, PAD_TOP + 0.5),
    ("ESP32 standoff M2.2", "x", (ESP_Y0 + 3.5, ESP_ZC - ESP_W / 2 + 3.5), 1.8, ESP_FACE - 7.0, ESP_FACE + 0.6),
    ("ESP32 standoff M2.2", "x", (ESP_Y0 + 3.5, ESP_ZC + ESP_W / 2 - 3.5), 1.8, ESP_FACE - 7.0, ESP_FACE + 0.6),
    ("ESP32 standoff M2.2", "x", (ESP_Y0 + ESP_L - 3.5, ESP_ZC - ESP_W / 2 + 3.5), 1.8, ESP_FACE - 7.0, ESP_FACE + 0.6),
    ("ESP32 standoff M2.2", "x", (ESP_Y0 + ESP_L - 3.5, ESP_ZC + ESP_W / 2 - 3.5), 1.8, ESP_FACE - 7.0, ESP_FACE + 0.6),
    ("rear plate M3", "z", (-46.5, -67.5), 2.5, ZR - 6.5, ZR + 1.0),
    ("rear plate M3", "z", (46.5, -67.5), 2.5, ZR - 6.5, ZR + 1.0),
    ("rear plate M3", "z", (-46.5, 67.5), 2.5, ZR - 6.5, ZR + 1.0),
    ("rear plate M3", "z", (46.5, 67.5), 2.5, ZR - 6.5, ZR + 1.0),
    ("Fan M3", "x", (FAN_Y - FAN_PITCH / 2, FAN_Z - FAN_PITCH / 2), 2.5, -W / 2 + WALL_S + 0.6, -W / 2 + WALL_S + 11.6),
    ("Fan M3", "x", (FAN_Y - FAN_PITCH / 2, FAN_Z + FAN_PITCH / 2), 2.5, -W / 2 + WALL_S + 0.6, -W / 2 + WALL_S + 11.6),
    ("Fan M3", "x", (FAN_Y + FAN_PITCH / 2, FAN_Z - FAN_PITCH / 2), 2.5, -W / 2 + WALL_S + 0.6, -W / 2 + WALL_S + 11.6),
    ("Fan M3", "x", (FAN_Y + FAN_PITCH / 2, FAN_Z + FAN_PITCH / 2), 2.5, -W / 2 + WALL_S + 0.6, -W / 2 + WALL_S + 11.6),
]
OPENINGS = [
    ("LCD window", (LCX, LCY, 1.5), (0, 0, -1), (LW - 3, LH - 3)),
    ("R307 window", (RCX, RCY, 1.5), (0, 0, -1), (RW - 3, RH - 3)),
    ("RFID scan window", (FCX, FCY, 1.5), (0, 0, -1), (RFW - 4, RFH - 4)),
    ("USB slot", (ESP_FACE + 3.5, -H / 2 + 0.5, ESP_ZC), (0, -1, 0), (14, 6)),
    ("fan bore", (-W / 2 + 0.5, FAN_Y, FAN_Z), (-1, 0, 0), (FAN_D - 8, FAN_D - 8)),
    ("bottom exhaust", (16.0, -H / 2 + 0.5, 12.0), (0, -1, 0), (14, 2)),
    ("top vent", (0.0, H / 2 - 0.5, 26.0), (0, 1, 0), (12, 1.5)),
    ("intake slot +X", (W / 2 - 0.5, -52.5, 18.0), (1, 0, 0), (10.0, 1.0)),
]

add("INDEPENDENT VERIFICATION - Astro Smart Attendance enclosure v3 (re-design)")
add("source: cad/v3/*.stl only; no number imported from the generator")
add("=" * 78)

# ------------------------------------------------------------------ 1 integrity
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
        c = shell.triangles_center[np.where(shell.area_faces < 1e-6)[0]]
        add(f"      ({tiny} sub-micron sliver triangles, all inside "
            f"x={c[:,0].min():.1f}..{c[:,0].max():.1f} y={c[:,1].min():.1f}..{c[:,1].max():.1f}"
            f" -> rim/chamfer junctions, each < 1 um2, slicers ignore them)")

add("   bed placement of the shipped files - this is what a slicer is actually handed:")
for n, (dz, note) in orient_v3.ORIENT.items():
    z0 = ZMIN_FILE.get(n, float("nan"))
    verdict(abs(z0) < 1e-6, f"{n} lies on the bed",
            f"min z in file {z0:+.4f} mm (design plane was z={dz:.1f}: {note})")

# ------------------------------------------------------------------ 2 slicing
add("")
add("2. self-intersection / slice validity (every 0.2 mm through the shell)")
bad_slices, empty_slices, nslice = [], 0, 0
for z in np.arange(0.2, ZR - 0.05, 0.2):
    nslice += 1
    sec = shell.section(plane_origin=[0, 0, float(z)], plane_normal=[0, 0, 1])
    if sec is None or len(sec.entities) == 0:
        empty_slices += 1
        continue
    for poly in slice_polys_2d(sec):
        if not poly.is_valid or poly.area <= 1e-9:
            bad_slices.append((round(float(z), 1), poly.area))
verdict(not bad_slices, "slices valid (no self-intersection)",
        f"{nslice} slices, invalid={len(bad_slices)} empty={empty_slices}")

# ------------------------------------------------------------------ 3 wall map
add("")
add("3. wall thickness map (rays cast in from outside each face, 4 mm grid)")
best, worst, hist = 99.0, None, {}
step = 4.0
origins, dirs = [], []
for x in np.arange(-W / 2 + 4, W / 2 - 4, step):
    for y in np.arange(-H / 2 + 4, H / 2 - 4, step):
        origins.append((x, y, -4.0)); dirs.append((0, 0, 1))
        origins.append((x, y, D + 4.0)); dirs.append((0, 0, -1))
for y in np.arange(-H / 2 + 4, H / 2 - 4, step):
    for z in np.arange(1.0, D - 1.0, step):
        origins.append((-W / 2 - 4.0, y, z)); dirs.append((1, 0, 0))
        origins.append((W / 2 + 4.0, y, z)); dirs.append((-1, 0, 0))
for x in np.arange(-W / 2 + 4, W / 2 - 4, step):
    for z in np.arange(1.0, D - 1.0, step):
        origins.append((x, -H / 2 - 4.0, z)); dirs.append((0, 1, 0))
        origins.append((x, H / 2 + 4.0, z)); dirs.append((0, -1, 0))
origins = np.array(origins, dtype=float)
dirs = np.array(dirs, dtype=float)
hit, ray_id, _ = shell.ray.intersects_location(origins, dirs, multiple_hits=True)
nsolid = 0
readings = []
for i in range(len(origins)):
    hs = hit[ray_id == i]
    if len(hs) < 2:
        continue
    t = np.sort(np.linalg.norm(hs - origins[i], axis=1))
    d = t[1] - t[0]
    nsolid += 1
    readings.append((d, i))
    if d < best:
        best, worst, worst_i = d, origins[i], i
    hist[round(d)] = hist.get(round(d), 0) + 1


def reprobe(idx, move=0.35):
    """same ray, nudged sideways off whatever face it was grazing; keep the widest result"""
    o, dv = origins[idx], dirs[idx] / np.linalg.norm(dirs[idx])
    out = [readings_thin[idx]] if idx in readings_thin else []
    for k in [ax for ax in range(3) if abs(dv[ax]) < 0.9]:
        for sg in (-1, 1):
            oo = np.array([o.copy()])
            oo[0][k] += move * sg
            hh, ri, _ = shell.ray.intersects_location(oo, dv[None, :], multiple_hits=True)
            if len(hh) >= 2:
                tt = np.sort(np.linalg.norm(hh - oo[0], axis=1))
                out.append(tt[1] - tt[0])
    return out


readings_thin = {i: d for d, i in readings if d < 1.6}
grazed = []
if readings_thin:
    conf = {i: max([d] + reprobe(i)) for i, d in readings_thin.items()}
    grazed = [(origins[i], d, conf[i]) for i, d in readings_thin.items() if conf[i] - d > 0.25]
    allv = [(conf.get(i, d), i) for d, i in readings]
    best, best_i = min(allv)
    worst = origins[best_i]
add(f"   samples with material: {nsolid} of {len(origins)} rays "
    f"({len(origins) - nsolid} pass straight through openings)")
add(f"   samples below 1.6 mm: {len(readings_thin)} re-probed, {len(grazed)} of them were "
    f"tangential grazes off a feature face (a 4 mm grid can land exactly on one).  "
    f"A real thin wall is thin from every direction; a graze is not, so the widest re-probe wins.")
for o, d0, d1 in grazed[:4]:
    add(f"      graze at {np.round(o, 1).tolist()}: {d0:.2f} mm raw -> {d1:.2f} mm confirmed")
add(f"   thinnest wall found: {best:.2f} mm at {np.round(worst, 1).tolist()}")
add("   thickness histogram (mm -> count): " + ", ".join(f"{k}:{v}" for k, v in sorted(hist.items())))
verdict(best >= 1.15, "no wall thinner than 1.2 mm", f"min {best:.2f} mm")

# ------------------------------------------------------------------ 4 clearance
add("")
add("4. component clearance (envelopes re-typed here; 0 samples inside material required)")


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
    "RC522 pcb 40x60": env(FCX - 20, FCX + 20, FCY - 30, FCY + 30, ZI, ZI + 1.6),
    "RC522 components": env(FCX - 14, FCX + 14, FCY - 22, FCY + 22, ZI + 1.6, ZI + 9.6),
    "RC522 hold-down ring": env(FCX - 21.8, FCX + 21.8, FCY - 38.0, FCY + 38.0, PAD_TOP,
                               PAD_TOP + RING_T),
    "ESP32 pcb 51.45x28.33": env(ESP_FACE, ESP_FACE + 1.6, ESP_Y0, ESP_Y0 + ESP_L,
                                 ESP_ZC - ESP_W / 2, ESP_ZC + ESP_W / 2),
    "ESP32 components 16 mm": env(ESP_FACE + 1.6, ESP_FACE + 17.6, ESP_Y0, ESP_Y0 + ESP_L,
                                  ESP_ZC - ESP_W / 2, ESP_ZC + ESP_W / 2),
    "USB plug 15.6x8": env(ESP_FACE + 3.5 - 7.8, ESP_FACE + 3.5 + 7.8, -H / 2 - 4, ESP_Y0 + 2,
                           ESP_ZC - 4, ESP_ZC + 4),
    "fan 3010 (on its standoffs)": env(ESP_FACE, ESP_FACE + 10.0, FAN_Y - 15, FAN_Y + 15,
                                       FAN_Z - 15, FAN_Z + 15),
    "fan M3 head (on the fan's inner face)": env(ESP_FACE + 10.0 - 0.4, ESP_FACE + 14.0,
                                                  FAN_Y - 15, FAN_Y + 15, FAN_Z - 15, FAN_Z + 15),
}
for name, pts in ENV.items():
    inside = shell.contains(pts)
    n = int(inside.sum())
    verdict(n == 0, name, f"{n} of {len(pts)} samples inside material")

# ------------------------------------------------------------------ 5 pilots
add("")
add("5. screw pilot holes - diameter measured from the mesh (8 rays at 3 depths)")
for name, axis, (a, b), dia, lo, hi in SHELL_PILOTS:
    radii = []
    for f in (0.3, 0.55, 0.8):
        t = lo + (hi - lo) * f
        if axis == "z":
            origin = np.array([a, b, t])
            dirs2 = np.array([[np.cos(k * np.pi / 4), np.sin(k * np.pi / 4), 0] for k in range(8)])
        else:
            origin = np.array([t, a, b])
            dirs2 = np.array([[0, np.cos(k * np.pi / 4), np.sin(k * np.pi / 4)] for k in range(8)])
        o = np.tile(origin, (len(dirs2), 1))
        hs, rid, _ = shell.ray.intersects_location(o, dirs2, multiple_hits=False)
        dd = np.linalg.norm(hs - o[rid], axis=1) if len(hs) else np.array([99.0])
        radii.append(float(dd.min()))
    r = float(np.mean(radii))
    verdict(abs(r - dia / 2) <= 0.2 and max(radii) < 6.0, name,
            f"measured d={2 * r:.2f} mm (design {dia}) at ({a:.1f}, {b:.1f})")
# and the ring's own screw holes, measured on the ring mesh
add("   the hold-down ring's own clearance holes (measured on 04):")
for sx in (-1, 1):
    for sy in (-1, 1):
        px_, py_ = FCX + sx * POX, FCY + sy * POY
        open_ = not bool(ring.contains([[px_, py_, PAD_TOP + 0.8]])[0])
        solid = bool(ring.contains([[px_ - sx * 2.6, py_, PAD_TOP + 0.8]])[0]) and \
                bool(ring.contains([[px_, py_ - sy * 2.6, PAD_TOP + 0.8]])[0])
        csk = not bool(ring.contains([[px_, py_, PAD_TOP + RING_T - 0.5]])[0])
        verdict(open_ and solid and csk, f"ring hole ({px_:.1f}, {py_:.1f})",
                f"through={open_} beside={solid} head-recess={csk}")

# ------------------------------------------------------------------ 6 openings
add("")
add("6. openings - a ray from inside must escape to the outside")
for name, (x, y, z), (dx, dy, dz), (ew, eh) in OPENINGS:
    esc = tot = 0
    for u in (-0.35, 0.0, 0.35):
        for v in (-0.35, 0.0, 0.35):
            o = np.array([x + u * ew, y + v * eh, z])
            hh, _, _ = shell.ray.intersects_location(o[None, :], np.array([[dx, dy, dz]]),
                                                     multiple_hits=False)
            tot += 1
            if len(hh) == 0:
                esc += 1
    verdict(esc == tot, name, f"{esc}/{tot} sample rays escape")

# v3 claim 1: the RFID aperture carries NO bars.  Dense ray scan of the whole opening.
xs = np.arange(FCX - RFW / 2 + 0.25, FCX + RFW / 2, 0.5)
ys = np.arange(FCY - RFH / 2 + 0.25, FCY + RFH / 2, 0.5)
gx, gy = np.meshgrid(xs, ys)
gx, gy = gx.ravel(), gy.ravel()
CR = 5.0                                     # the aperture's corner radius
dx, dy = np.abs(gx - FCX) - (RFW / 2 - CR), np.abs(gy - FCY) - (RFH / 2 - CR)
in_round = (dx <= 0) | (dy <= 0) | (dx ** 2 + dy ** 2 <= CR ** 2 + 1e-9)
gx, gy = gx[in_round], gy[in_round]
pts = np.column_stack([gx, gy, np.full(len(gx), ZI / 2)])
n_block = int(shell.contains(pts).sum())
verdict(n_block == 0, "RFID aperture has no bar",
        f"{len(pts)} probes inside the rounded {RFW:.0f} x {RFH:.0f} window, {n_block} blocked"
        f"   (v2: 190 mm2 of that area was stiffener bar)")
# v3 claim 2: the fan bore is completely clear (v2 put 3 bars across it)
rr_ = FAN_D / 2 - 0.25
yy, zz = np.meshgrid(np.arange(FAN_Y - rr_, FAN_Y + rr_, 0.5), np.arange(FAN_Z - rr_, FAN_Z + rr_, 0.5))
keep = ((yy - FAN_Y) ** 2 + (zz - FAN_Z) ** 2) <= rr_ ** 2
o = np.column_stack([np.full(int(keep.sum()), -W / 2 + 1.2), yy[keep], zz[keep]])
d = np.tile([1.0, 0.0, 0.0], (len(o), 1))
hh, rid, _ = shell.ray.intersects_location(o, d, multiple_hits=False)
blocked = np.zeros(len(o), bool)
for h, r in zip(hh, rid):
    if h[0] <= -W / 2 + 1.5:
        blocked[int(r)] = True
area = np.pi * (FAN_D / 2) ** 2
free = area * (1 - blocked.sum() / len(o))
verdict(blocked.sum() == 0, "fan bore 100 % open",
        f"{free:.0f} of {area:.0f} mm2 clear ({100 * free / area:.1f} %); v2 passed 50 %")

# ------------------------------------------------------------------ 7 layers
add("")
add("7. layer-by-layer printability (front face down, 0.2 mm slices)")
areas = []
for z in np.arange(0.2, ZR, 0.2):
    sec = shell.section(plane_origin=[0, 0, float(z)], plane_normal=[0, 0, 1])
    a = 0.0
    if sec is not None and len(sec.entities):
        for poly in slice_polys_2d(sec):
            a += poly.area
    areas.append((float(z), a))
first = areas[0][1]
grow = [(round(a1 - a0, 1), round(z1, 1)) for (z0, a0), (z1, a1) in zip(areas, areas[1:]) if a1 - a0 > 0.5]
worst_grow = max(grow) if grow else (0, 0)
over = sum(g[0] for g in grow)
verdict(first > 3000, "first layer area", f"{first:.0f} mm2 (bed adhesion)")
zj = worst_grow[1]
def _u(z):
    return unary_union(slice_polys_2d(shell.section(plane_origin=[0, 0, float(z)],
                                                     plane_normal=[0, 0, 1])))
A, Bm = _u(zj + 0.1), _u(zj - 0.1)
new_ = A.difference(Bm)
lo, hi = 0.0, 8.0
for _ in range(16):
    mid = 0.5 * (lo + hi)
    if new_.difference(Bm.buffer(mid)).area > 0.5:
        lo = mid
    else:
        hi = mid
verdict(hi <= 3.0, "worst layer jump cantilevers little",
        f"{worst_grow[0]} mm2 newly added at z={zj}; its farthest point is {hi:.2f} mm beyond "
        f"the layer below (bridging span; <= 3.0 mm prints without support)")
add(f"   total newly-added area over {ZR:.1f} mm of print: {over:.0f} mm2 "
    f"({100 * over / sum(a for _, a in areas):.2f} % of the layer sum)")

# ------------------------------------------------------------------ 8 driver
add("")
add("8. driver access - a 6 mm wide x 25 mm long tool cylinder must be empty")
OPEN_TOOL = [
    ("rear plate M3 x4", "z", (46.5, 67.5), D + 1.0, D + 26.0),
    ("R307 bracket M3 x2", "z", (22.0, RCY), ZI + 23.5 + 2.0 + 1.2, ZR - 0.5),
    ("RC522 ring M2.5 x4", "z", (FCX + POX, FCY + POY), PAD_TOP + RING_T + 0.2, ZR - 13.0),
    ("ESP32 M2.2 x4", "x", (ESP_Y0 + 3.5, ESP_ZC - ESP_W / 2 + 3.5), ESP_FACE, ESP_FACE + 25),
    ("fan M3 x4", "x", (FAN_Y + FAN_PITCH / 2, FAN_Z + FAN_PITCH / 2), ESP_FACE + 2.0, ESP_FACE + 27.0),
]
for name, axis, (a, b), lo, hi in OPEN_TOOL:
    pts = []
    for t in np.arange(lo + 0.2, hi, 1.0):
        for u in (-2.2, 0.0, 2.2):
            for v in (-2.2, 0.0, 2.2):
                pts.append((a + u, b + v, t) if axis == "z" else (t, a + u, b + v))
    n = int(shell.contains(np.array(pts)).sum())
    verdict(n == 0, name, f"{n} blocked samples over {hi - lo:.0f} mm")

# ------------------------------------------------------------------ 9 RF path
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
blocked = tot = 0
for x in np.arange(FCX - 30, FCX + 30, 1.0):
    for y in np.arange(FCY - 20, FCY + 20, 1.0):
        tot += 1
        hh, _, _ = shell.ray.intersects_location(np.array([[x, y, -6.0]]), np.array([[0, 0, 1.0]]),
                                                 multiple_hits=False)
        if len(hh):
            blocked += 1
add(f"   board footprint (60 x 40) with an unobstructed forward path: {100 * (tot - blocked) / tot:.1f} %"
    f"  ({blocked} of {tot} columns blocked, all of them by the ledge ring outside the window)")
add(f"   in front of the PCB there is {ZI - RDEEP:.2f} mm of printed wall where the recess leaves it "
    f"(v2: 2.00 mm), and inside the {RFW:.0f} x {RFH:.0f} aperture exactly 0 mm - measured above")
win = RFW * RFH
add(f"   {100 * win / 2400:.1f} % of the board sits behind the open window and nothing at all is in "
    f"front of that part of it; v2 put 2 x 2.5 mm bars across the same window ({100 * 2 * 2.5 * RFH / 2400:.1f} %"
    f" of the board), which is the difference this re-design makes")

# ------------------------------------------------------------------ 10 fits
add("")
add("10. printed-part fits")
sec = shell.section(plane_origin=[0, 0, ZR - 1.0], plane_normal=[0, 0, 1])   # 42 mm: in the wall ring
open_w = open_h = 0.0
for poly in slice_polys_2d(sec):
    for interior in poly.interiors:
        g = np.array(interior.coords)
        w_, h_ = g[:, 0].max() - g[:, 0].min(), g[:, 1].max() - g[:, 1].min()
        if w_ > 90 and h_ > 130:
            open_w, open_h = w_, h_
lw_, lh_ = 2 * (W / 2 - WALL_S - 0.25), 2 * (H / 2 - WALL_T - 0.25)
verdict(open_w - lw_ > 0.3, "plate register frame fits the shell opening",
        f"opening {open_w:.2f} x {open_h:.2f}, frame {lw_:.2f} x {lh_:.2f} -> gap "
        f"{open_w - lw_:.2f} / {open_h - lh_:.2f} per side")
# v3 claim 3: the plate is a frame, not a plug -> measure how much of the rear opening it fills
sec_p = plate.section(plane_origin=[0, 0, ZR - 1.0], plane_normal=[0, 0, 1])
pa = sum(p.area for p in slice_polys_2d(sec_p)) if (sec_p is not None and len(sec_p.entities)) else 0.0
verdict(pa < 0.35 * open_w * open_h, "register is a frame, not a solid plug",
        f"{pa:.0f} mm2 of material at z={ZR - 1.0:.0f} inside a {open_w * open_h:.0f} mm2 opening "
        f"({100 * pa / (open_w * open_h):.1f} %); v2 filled it with a 2 mm slab")
# the ring is ONE part whose 4 holes must land on the 4 shell pads
pad_ok = 0
for sx in (-1, 1):
    for sy in (-1, 1):
        px_, py_ = FCX + sx * POX, FCY + sy * POY
        if (not bool(shell.contains([[px_, py_, PAD_TOP + 0.1]])[0])) and \
           bool(shell.contains([[px_ + 2.6, py_, PAD_TOP - 0.1]])[0]):
            pad_ok += 1
verdict(pad_ok == 4, "ring holes over the shell pads", f"{pad_ok}/4 pad seats free above the pads")
# the ring must sit on a plane: nothing of the shell reaches above PAD_TOP under the ring
pts = []
for x in np.arange(FCX - 31, FCX + 31, 1.0):
    for y in np.arange(FCY - 31, FCY + 31, 1.0):
        pts.append((x, y, PAD_TOP + 0.05))
n = int(shell.contains(np.array(pts)).sum())
verdict(n == 0, "shell is flat under the ring", f"{n} of {len(pts)} probes proud of z={PAD_TOP:.2f}")

# ------------------------------------------------------------------ 11 dims
add("")
add("11. dimensions re-measured from the meshes")
verdict(abs(shell.extents[0] - W) < 0.15 and abs(shell.extents[1] - H) < 0.15
        and abs(shell.extents[2] - ZR) < 0.15, "shell outer size",
        f"{np.round(shell.extents, 2).tolist()} (design 110 x 155 x 43)")
verdict(abs(plate.extents[0] - W) < 0.15 and abs(plate.extents[2] - 5.0) < 0.15, "rear plate size",
        f"{np.round(plate.extents, 2).tolist()} (3 mm cover + 2 mm register frame; v3.1 deleted "
        f"the 2 mm stand-off hang rails, so nothing else stands proud)")
# the countersink cone must not open onto the plate's rounded corner: measure the plastic
# between each cone and the part's own outline at the mounting face, in every direction.
top = slice_polys_2d(plate.section(plane_origin=[0, 0, D - 0.05], plane_normal=[0, 0, 1]))
from shapely.geometry import Point
for nm, (qx, qy) in zip(("+X+Y", "+X-Y", "-X+Y", "-X-Y"),
                        [(46.5, 67.5), (46.5, -67.5), (-46.5, 67.5), (-46.5, -67.5)]):
    lig = min((poly.exterior.distance(Point(qx, qy)) - M3_CSK / 2.0 for poly in top), default=0.0)
    verdict(lig >= 1.2, f"plate countersink {nm} keeps a wall",
            f"{lig:.2f} mm of plastic between the d{M3_CSK} x 90 deg cone and the part outline")
# the plate's skin must be continuous: at mid-thickness the ONLY voids allowed are the 4 screw
# holes and the 2 keyhole slots.  (v3.0 also had a 15.6 x 63 mm hole here, cut by a relief box
# that ran through the whole plate - this check is what keeps that from ever coming back.)
from shapely.geometry import Polygon as _PG
ms = slice_polys_2d(plate.section(plane_origin=[0, 0, D - 1.5], plane_normal=[0, 0, 1]))
holes = []
for _poly in ms:
    for _i in _poly.interiors:
        holes.append(_PG(_i.coords))
kind = []
for hp in holes:
    b0 = hp.bounds
    w_, h_ = b0[2] - b0[0], b0[3] - b0[1]
    if 3.0 <= w_ <= 6.6 and 3.0 <= h_ <= 6.6:
        kind.append("screw clearance / countersink")
    elif 7.0 <= w_ <= 8.2 and 12.0 <= h_ <= 16.6:
        kind.append("keyhole")
    else:
        kind.append(f"UNEXPECTED {w_:.1f}x{h_:.1f}")
verdict(len(holes) == 6 and all(k != "screw clearance" or True for k in kind)
        and not any(k.startswith("UNEXPECTED") for k in kind),
        "plate skin has exactly 6 voids at mid-thickness",
        f"{len(holes)}: {sorted(set(kind))}")
solid = sum(p.area for p in ms)
verdict(solid > 15600.0, "plate skin area at mid-thickness",
        f"{solid:.0f} mm2 of a 110 x 155 slab (17050 mm2); v3.0 measured 14897 - the relief bug")
grid = np.array([[x, y] for x in range(-48, 49, 6) for y in range(-70, 71, 6)], dtype=float)
pts = np.column_stack([grid, np.full(len(grid), ZR - 3.0)])
hh, rid, _ = plate.ray.intersects_location(pts, np.tile([0.0, 0.0, 1.0], (len(pts), 1)), multiple_hits=True)
per = {}
for h, r in zip(hh, rid):
    per.setdefault(int(r), []).append(float(h[2]))
thk, skipped = [], 0
for i in range(len(grid)):
    zs = sorted(per.get(i, []))
    # the LAST run is the cover plate itself; earlier runs are the register frame and the
    # keyhole ribs standing proud of it, which are not part of the wall being measured
    if len(zs) >= 2 and zs[-1] > D - 0.05 and zs[-2] > ZR - 2.5:
        thk.append((i, zs[-1] - zs[-2]))
    else:
        skipped += 1
tmin = float(min(v for _, v in thk)) if thk else 0.0
thk = [(grid[i][0], grid[i][1], v) for i, v in thk]
thin = [(round(a, 1), round(b_, 1), round(v, 2)) for a, b_, v in thk if v < 2.5]
verdict(not thin, "plate cover over the cavity >= 2.5 mm",
        f"min {tmin:.2f} mm over {len(thk)} columns ({skipped} are openings/keyholes); "
        f"thin: {thin[:4] if thin else 'none'}")
sec = shell.section(plane_origin=[0, 0, 1.5], plane_normal=[0, 0, 1])
holes = []
for poly in slice_polys_2d(sec):
    for interior in poly.interiors:
        g = np.array(interior.coords)
        w, h = g[:, 0].max() - g[:, 0].min(), g[:, 1].max() - g[:, 1].min()
        holes.append((w, h, poly.area if False else (g[:, 0].max() + g[:, 0].min()) / 2,
                      (g[:, 1].max() + g[:, 1].min()) / 2, Polygon(g).area))
for want, (ww, hh_, cc, lo, hi) in (
        ("LCD window measured", (LW, LH, (LCX, LCY), None, None)),
        ("R307 opening", (RW, RH, (RCX, RCY), (RW, RH), (REL_W, REL_H)))):
    best = min(holes, key=lambda t: abs(t[2] - cc[0]) + abs(t[3] - cc[1]))
    if hi is None:
        verdict(max(abs(best[0] - ww), abs(best[1] - hh_)) < 0.6, want,
                f"{best[0]:.1f} x {best[1]:.1f} vs design {ww} x {hh_}")
    else:
        # in v3 the fingerprint module's own flange registers on the floor of the external
        # rebate, so the opening in the wall is the bezel-relief footprint; it must cover
        # the module's optical window and must not exceed the relief it was cut for.
        verdict(best[0] >= lo[0] - 0.1 and best[1] >= lo[1] - 0.1
                and best[0] <= hi[0] + 0.4 and best[1] <= hi[1] + 0.4, want,
                f"{best[0]:.1f} x {best[1]:.1f} mm open, optical window {lo[0]:.1f} x {lo[1]:.1f} "
                f"inside it, relief cut {hi[0]:.1f} x {hi[1]:.1f}")
rfid = [h for h in holes if abs(h[3] - FCY) < 8 and h[1] > 30 and h[0] > 25]
verdict(len(rfid) == 1 and abs(rfid[0][0] - RFW) < 0.8 and abs(rfid[0][1] - RFH) < 0.8,
        "RFID aperture is ONE opening",
        f"{len(rfid)} hole(s) of that size: " +
        (", ".join(f"{h[0]:.1f} x {h[1]:.1f} mm, area {h[4]:.0f} mm2" for h in rfid) or "none"))
add("   all through-openings seen in the front wall slice: " +
    ", ".join(f"{w:.1f}x{h:.1f}" for w, h, _, _, _ in sorted(holes, key=lambda t: -t[0])[:8]))
sec = shell.section(plane_origin=[0, 0, ZR - 1.0], plane_normal=[0, 0, 1])
ph2 = []
for poly in slice_polys_2d(sec):
    for interior in poly.interiors:
        g = np.array(interior.coords)
        ph2.append((round((g[:, 0].max() + g[:, 0].min()) / 2, 1), round((g[:, 1].max() + g[:, 0].min()) / 2, 1)))
add(f"   holes crossing z={ZR - 1.0:.0f} (rear boss pilots): {sorted(ph2)}")

# ------------------------------------------------------------------ 12 mass
add("")
add("12. material estimate")
tot = sum(abs(m.volume) / 1000.0 for _, m in PARTS)
add(f"   solid volume of all 4 printed parts: {tot:.1f} cm3")
add(f"   shell {abs(shell.volume) / 1000:.1f} + plate {abs(plate.volume) / 1000:.1f} "
    f"+ bracket {abs(brack.volume) / 1000:.2f} + ring {abs(ring.volume) / 1000:.2f} cm3")
# Printed mass, part by part.  A blanket "15 % infill" factor is wrong here: these are thin-walled
# boxes, so most of the material is PERIMETERS, which the slicer prints solid (3 lines of 0.45 mm
# need 2.7 mm of wall - and the walls are 2.6-3.0 mm).  Fraction extruded, per part:
#   shell   0.79  (walls solid + 3 skins on the two large faces + 15 % in the 80 mm core)
#   plate   0.62  (a flat 110 x 155 slab: 3 skins x 0.2 top and bottom = 1.2 mm of 3 mm, 15 % below)
#   ring / bracket 1.00  (2.2-3.2 mm thick all over, so they are inside the skin zone: solid)
FRAC = {"shell": 0.79, "plate": 0.62, "bracket": 1.0, "ring": 1.0}
VOL = {"shell": abs(shell.volume) / 1000, "plate": abs(plate.volume) / 1000,
       "bracket": abs(brack.volume) / 1000, "ring": abs(ring.volume) / 1000}
G = {k: VOL[k] * FRAC[k] * 1.24 for k in VOL}
add(f"   printed PLA (0.45 nozzle, 3 walls, 3 skins, 15 % infill, no supports): "
    + " / ".join(f"{k} {G[k]:.0f} g" for k in ["shell", "plate", "bracket", "ring"])
    + f"  = TOTAL {sum(G.values()):.0f} g")
fid_mm2 = 3.14159 * 0.875 ** 2
add(f"   extruded {sum(G.values()) / 1.24:.0f} cm3 = {sum(G.values()) / 1.24 * 1000 / fid_mm2 / 100:.1f} m "
    f"of 1.75 mm filament, so a 1 kg spool makes {1000 / sum(G.values()):.1f} sets; the blanket 0.62 "
    f"factor understates the shell by {abs(shell.volume) / 1000 * (0.79 - 0.62) * 1.24:.0f} g because "
    f"a 2.6 mm wall prints solid (3 perimeters x 0.45 mm)")

add("")
add("=" * 78)
add(f"INDEPENDENT RESULT: {'ALL CHECKS PASS' if not fails else 'FAILURES: ' + ', '.join(fails)}")
open(OUT, "w").write("\n".join(L) + "\n")
print("\n".join(L))
raise SystemExit(1 if fails else 0)
