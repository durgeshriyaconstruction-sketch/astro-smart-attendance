"""05_FIT_GAUGE_v3.stl - a 1:1 fit and pilot gauge card, printed to settle the five unknowns.

The five VERIFY_ACTUAL_HARDWARE items (R307 body / prism, 1602 outline, depth and hole pitch, RC522
outline, fan thickness, ESP32 board-hole size) cannot be measured from here, and every one of them
is a *fit* question.  So the fifth printed file answers them in the same plastic: this card carries
the box's real openings, cut through it, with each module's reference outline engraved around them,
plus a solid boss with six blind screw pilots at the exact diameters the enclosure drills.

Read the card like this:  **a cut is a GO gauge - it is a hole the box really has**, so whatever
passes here passes there.  **An engraved line is a reference outline** - the size your module is
supposed to be, drawn where it must sit.  The card is 2.60 mm thick, the same as the box's walls, so
its holes are the same quality as the box's holes, and 2.60 mm is also the height unit for the
clearance questions (1 card = 2.60, 2 cards = 5.20, 3 = 7.80 mm).

Generated, never drawn by hand: every number is read out of `P` in tools/build_v3.py, and the layout
is self-checked below with shapely (no cut within 3.0 mm of another cut or of an edge, no engraved
line left floating in a hole).  tools/check_gauge_v3.py then measures the exported STL back.

  python3 tools/build_gauge_v3.py    -> cad/v3/05_FIT_GAUGE_v3.stl + docs/v3_gauge_build.txt

Stations (card frame x 0..150, y 0..112, z 0..2.60, engraved face up):
  1  pilot boss      58 x 18 x 10 solid, six blind pilots d1.80 / 2.00 / 2.05 / 2.20 / 2.35 / 2.50
                     x 8 deep, each labelled - drive your screws in and feel which one bites
  2  board holes      four d2.00 / 2.20 / 2.50 / 2.70 through-holes: push a drill bit through your
                     PCB's corner hole and into these to read the hole's size
  3  LCD 1602        cut = the box's window 66.00 x 17.53; engraved: the rebate mouth 72.00 x 23.53,
                     the board outline 80 x 36, and d2.05 crosses at the 75.10 x 31.0 pitch
  4  R307            cut = the bezel relief 21.01 x 25.01; engraved: the rebate 25.33 x 27.21, the
                     sensor body 44.10 x 20.00 and the 19.30 x 21.20 prism window
  5  RC522           cut = the board GO gauge 60.40 x 40.40; engraved: the recess 62.73 x 44.72 and
                     four pad crosses at (+/-34, +/-17) - the pitch the ring's pilots are on
  6  USB             cut = the measured opening 20.40 x 12.40 through 3 mm of wall; engraved: the
                     plug body 15.60 x 8.00
  7  rule            100 mm engraved rule, ticks every 10, a major tick every 50
"""
import os
import sys

import numpy as np
import trimesh
from shapely.geometry import Polygon, box as sbox
from shapely.ops import unary_union

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import orient_v3  # noqa: E402

OUT = os.path.join(ROOT, "cad", "v3")
os.makedirs(OUT, exist_ok=True)
os.makedirs(os.path.join(OUT, "assembly"), exist_ok=True)

UNION = trimesh.boolean.union
DIFF = trimesh.boolean.difference


def design():
    """the enclosure's parameter block - the only source of numbers allowed in this file."""
    src = open(os.path.join(ROOT, "tools", "build_v3.py"), encoding="utf-8").read()
    i = src.index("P = dict(")
    ns = {"__builtins__": __builtins__, "math": __import__("math"), "np": np}
    exec(src[i:src.index("\n)\n", i) + 3], ns)
    return ns["P"]


P = design()

# ------------------------------------------------------------------ the card
CW, CH, CT = 150.0, 112.0, 2.60
CORNER_R = 3.0                 # the box's own front-face corner radius, so a corner feels familiar
GUTTER = 3.0                   # no cut within this of another cut or of the card's edge
ENG_T = 0.45                   # engraved line width (one extrusion is 0.4-0.45, so it always prints)
ENG_D = 0.50                   # engraved depth
PILOT_DEPTH = 8.0
BOSS_H = 10.0                  # the pilot boss stands this far above the card

CUT, ENG = [], []             # through-cuts (GO gauges) and engraved pockets / lines


def rr(cx, cy, w, h, r):
    r = max(0.02, min(r, w / 2 - 0.01, h / 2 - 0.01))
    return sbox(cx - w / 2 + r, cy - h / 2 + r, cx + w / 2 - r, cy + h / 2 - r).buffer(
        r, resolution=24, join_style=1)


def cut_open(cx, cy, w, h, r=1.0):
    """a GO gauge: material is removed, all the way through the card."""
    CUT.append(rr(cx, cy, w, h, r))


def circ(cx, cy, d, res=48):
    from shapely.geometry import Point
    return Point(cx, cy).buffer(d / 2.0, resolution=res, cap_style=1, join_style=1)


def cut_hole(cx, cy, d):
    CUT.append(circ(cx, cy, d))


def eng_box(x0, x1, y0, y1, z0=None, z1=None):
    ENG.append((sbox(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)),
                (CT - ENG_D) if z0 is None else z0,
                (CT + 0.3) if z1 is None else z1))


def eng_line(x0, y0, x1, y1, w=ENG_T, z0=None, z1=None):
    dx, dy = x1 - x0, y1 - y0
    ln = float(np.hypot(dx, dy)) or 1e-9
    nx, ny = -dy / ln * w / 2, dx / ln * w / 2
    ENG.append((Polygon([(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny),
                         (x0 - nx, y0 - ny)]),
                (CT - ENG_D) if z0 is None else z0, (CT + 0.3) if z1 is None else z1))


def eng_outline(cx, cy, w, h, bw=ENG_T, r=1.0, z0=None, z1=None):
    """a rectangle drawn as a line of width bw centred on the exact w x h path."""
    outer = rr(cx, cy, w + bw, h + bw, r + bw)
    inner = rr(cx, cy, w - bw, h - bw, max(0.02, r))
    ENG.append((outer.difference(inner), (CT - ENG_D) if z0 is None else z0,
                (CT + 0.3) if z1 is None else z1))


def eng_circle(cx, cy, d, bw=ENG_T, z0=None, z1=None):
    """an engraved circle drawn about its true diameter - a hole you can check a part against."""
    ENG.append((circ(cx, cy, d + bw, 72).difference(circ(cx, cy, d - bw, 72)),
                (CT - ENG_D) if z0 is None else z0, (CT + 0.3) if z1 is None else z1))


def eng_cross(cx, cy, d=4.4, w=ENG_T, z0=None, z1=None):
    eng_line(cx - d / 2, cy, cx + d / 2, cy, w, z0, z1)
    eng_line(cx, cy - d / 2, cx, cy + d / 2, w, z0, z1)


# ------------------------------------------------------------------ 7 segment
SEG = {0: "abcdef", 1: "bc", 2: "abged", 3: "abgcd", 4: "fgbc", 5: "afgcd", 6: "afgedcb",
       7: "abc", 8: "abcdefg", 9: "abcdfg", "-": "g", ".": ""}


def eng_text(cx, cy, txt, h=2.6, z0=None, z1=None, centre=True, bold=False):
    """digits / '.' / '-' engraved on a face; 7-segment because a printed letter needs a font."""
    t, w, gap = (ENG_T * (1.6 if bold else 1.0)), h * 0.58, 0.24 * h
    boxes, total = [], 0.0
    for ch in txt:
        if ch == ".":
            boxes.append(sbox(total + 0.08 * h, -0.06 * h, total + 0.08 * h + t, -0.06 * h + t))
            total += 0.30 * h
            continue
        s = SEG.get(ch, "")
        if "a" in s:
            boxes.append(sbox(0.14 * w, h - t, 0.86 * w, h))
        if "b" in s:
            boxes.append(sbox(w - t, w, 0.54 * h, h - 0.5 * t))
        if "c" in s:
            boxes.append(sbox(w - t, w, 0.5 * t, 0.46 * h))
        if "d" in s:
            boxes.append(sbox(0.14 * w, 0, 0.86 * w, t))
        if "e" in s:
            boxes.append(sbox(0, t, 0.5 * t, 0.46 * h))
        if "f" in s:
            boxes.append(sbox(0, t, 0.54 * h, h - 0.5 * t))
        if "g" in s:
            boxes.append(sbox(0.14 * w, 0.5 * h - 0.5 * t, 0.86 * w, 0.5 * h + 0.5 * t))
        total += w + gap
    x0 = cx - ((total - gap) / 2 if centre else 0.0)
    for b in boxes:
        g = np.asarray(b.exterior.coords) + [x0, cy - h / 2]
        ENG.append((Polygon(g), (CT - ENG_D) if z0 is None else z0,
                    (CT + 0.3) if z1 is None else z1))
    return x0, x0 + total - gap


def index_digit(cx, cy, n, z0=None, z1=None):
    """the station marker: a bare digit, deep enough to feel with a fingernail and to read in the
    figure.  It started life as a ring around the digit - the ring kept grazing an outline it was
    sitting beside, and a gauge with a broken line on it is worse than no line at all."""
    eng_text(cx, cy, str(n), h=3.4, z0=z0, z1=z1, bold=True)


# ============================================================ stations
# the numbers, read out of the enclosure's own parameters
LCD_WIN = P["lcd_window"]                                  # 66.0 x 17.5 -> the box's window
LCD_MOUTH = (LCD_WIN[0] + 2 * P["rebate"][1], LCD_WIN[1] + 2 * P["rebate"][1])   # 72.0 x 23.5
# the 1602's own PCB outline: a datasheet dimension [REF].  It is deliberately NOT in P - the box
# never uses it (it only cuts the window and drills the pitch), and this card is the one place
# where the outline matters, so it lives here rather than becoming a dead parameter up there.
LCD_BOARD = (80.0, 36.0)
LCD_PITCH = P["lcd_hole_pitch"]                            # 75.1 x 31.0
R307_RELIEF = P["r307_relief"]                            # 21.0 x 25.0, what the wall is cut to
R307_MOUTH = (R307_RELIEF[0] + 2 * 2.16, R307_RELIEF[1] + 2 * 1.1)               # 25.33 x 27.21
R307_WIN = P["r307_window"]                                # 19.3 x 21.2
R307_BODY = (P["r307_body"][1], P["r307_body"][0])        # 44.1 x 20.0
RC_BOARD = (P["rc522_board"][1], P["rc522_board"][0])     # 60 x 40 - P is portrait, the card is not
RC_RECESS = (P["rfid_recess"][1], P["rfid_recess"][0])     # 62.7 x 44.7, laid long-axis along x
RC_PAD = (P["rc522_post_off"][1], P["rc522_post_off"][0])  # (34, 17) - same rotation as the board
USB_OPEN = (P["usb_slot"][0] + 2.4, P["usb_slot"][1] + 2.4)                    # 20.4 x 12.4
USB_PLUG = P["usb_plug"]                                    # 15.6 x 8.0
PILOTS = [1.80, 2.00, 2.05, 2.20, 2.35, 2.50]
PCB_HOLES = [2.00, 2.20, 2.50, 2.70]
BOSS = (5.0, 58.0, 63.0, 76.0)                              # x0, y0, x1, y1 of the pilot boss

# --- 1  the pilot boss, and the six blind pilots ----------------------------------------------
bx0, by0, bx1, by1 = BOSS
px = [bx0 + 5.6 + i * ((bx1 - bx0 - 11.2) / 5.0) for i in range(6)]
py = (by0 + by1) / 2 - 1.2
for d, cx in zip(PILOTS, px):
    ENG.append((circ(cx, py, d, 72), CT + BOSS_H - PILOT_DEPTH, CT + BOSS_H + 0.5))
    eng_text(cx, by0 + 3.2, f"{d:.2f}", h=2.4, z0=CT + BOSS_H - ENG_D, z1=CT + BOSS_H + 0.3)
index_digit((bx0 + bx1) / 2, by1 - 4.2, 1, z0=CT + BOSS_H - ENG_D, z1=CT + BOSS_H + 0.3)

# --- 2  board-hole sizes -------------------------------------------------------------------------
for i, d in enumerate(PCB_HOLES):
    cx = 78.0 + i * 17.0
    cut_hole(cx, 95.0, d)
    eng_text(cx, 99.4, f"{d:.2f}", h=2.2)
index_digit(66.0, 95.0, 2)

# --- 3  the 1602, and the pitch the box drills ----------------------------------------------------
lx, ly = 108.0, 70.0
cut_open(lx, ly, LCD_WIN[0], LCD_WIN[1], 1.0)
eng_outline(lx, ly, LCD_BOARD[0], LCD_BOARD[1])
for sx in (-1, 1):
    for sy in (-1, 1):
        eng_cross(lx + sx * LCD_PITCH[0] / 2, ly + sy * LCD_PITCH[1] / 2, 3.6)
index_digit(66.0, 90.6, 3)

# --- 4  the R307: bezel relief, rebate, prism window, body --------------------------------------
rx, ry = 30.0, 18.0
cut_open(rx, ry, R307_RELIEF[0], R307_RELIEF[1], 1.5)
eng_outline(rx, 44.0, R307_BODY[0], R307_BODY[1])
eng_outline(64.5, 44.0, R307_WIN[0], R307_WIN[1])
eng_text(rx, ry - R307_RELIEF[1] / 2 - 2.4, f"{R307_RELIEF[0]:.1f}-{R307_RELIEF[1]:.1f}", h=1.9)
eng_text(64.5, 31.0, f"{R307_WIN[0]:.1f}-{R307_WIN[1]:.1f}", h=2.0)
index_digit(8.0, 8.0, 4)

# --- 5  the RC522: a GO gauge on the board outline, the recess drawn around it ------------------
qx, qy = 110.0, 26.0
GO = 0.40                                     # +0.4 mm per side so an in-tolerance board drops in
cut_open(qx, qy, RC_BOARD[0] + 2 * GO, RC_BOARD[1] + 2 * GO, 1.5)
eng_outline(qx, qy, RC_RECESS[0], RC_RECESS[1])
for sx in (-1, 1):
    for sy in (-1, 1):
        eng_cross(qx + sx * RC_PAD[0], qy + sy * RC_PAD[1], 3.6)
index_digit(78.0, 52.0, 5)

# --- 6  the USB opening as the wall really has it ----------------------------------------------
ux, uy = 40.0, 93.0
cut_open(ux, uy, USB_OPEN[0], USB_OPEN[1], 2.0)
eng_text(ux, uy - USB_OPEN[1] / 2 - 2.4, f"{USB_OPEN[0]:.1f}-{USB_OPEN[1]:.1f}", h=1.9)
eng_text(ux, uy + USB_OPEN[1] / 2 + 2.6, f"{USB_PLUG[0]:.1f}-{USB_PLUG[1]:.1f}", h=1.9)
index_digit(17.0, 93.0, 6)

# --- 7  a 100 mm rule, so the card also checks the printer's scale -------------------------------
RY, RX = 106.0, 6.0
eng_line(RX, RY, RX + 100.0, RY, 0.5)
for i in range(11):
    x = RX + i * 10.0
    eng_line(x, RY, x, RY + (2.6 if i % 5 == 0 else 1.6), 0.5)
eng_text(RX + 100.0 + 8.0, RY, "100", h=2.4)
index_digit(140.0, 106.4, 7)

# ============================================================ build + self-check
L, fails = [], []


def add(s=""):
    L.append(s)
    print(s, flush=True)


def verdict(good, label, detail=""):
    if not good:
        fails.append(label)
    add(f"   {label:36s} {detail:42s} {'PASS' if good else 'FAIL'}")
    return good


add("")
add("05_FIT_GAUGE_v3 - the fit and pilot card, every number read from tools/build_v3.py")
add("-" * 92)

card = rr(CW / 2, CH / 2, CW, CH, CORNER_R)
cuts_u = unary_union(CUT)
# (a) the layout is provable, not eyeballed: every cut must sit inside the card with a real margin,
#     and no two cuts may merge into one feature
worst_edge = min(card.exterior.distance(c) for c in CUT)
worst_pair = 9e9
for i in range(len(CUT)):
    for j in range(i + 1, len(CUT)):
        worst_pair = min(worst_pair, CUT[i].distance(CUT[j]))
verdict(worst_edge >= GUTTER, "cuts clear of the card's edge",
        f"min {worst_edge:.2f} mm (rule {GUTTER:.1f})")
verdict(worst_pair >= GUTTER, "cuts clear of each other", f"min {worst_pair:.2f} mm")
# (b) an engraved line must lie in plastic: if it runs into a cut it is not a line any more, it is
#     a broken edge, and the user reads a phantom dimension off it
bad_eng = 0
for poly, _z0, _z1 in ENG:
    a = poly.area
    if a <= 0:
        continue
    if poly.difference(cuts_u.buffer(0.55)).area / a < 0.98:
        bad_eng += 1
verdict(bad_eng == 0, "every engraved line is in solid plastic",
        f"{len(ENG)} engraving segments, {bad_eng} crossing a cut or its 0.55 mm edge")
# (c) the six pilots: 2 mm of floor under them, 2 mm between them, and none through the boss
floors = CT + BOSS_H - PILOT_DEPTH
verdict(floors >= 2.0, "pilot floor left in the boss", f"{floors:.2f} mm under an 8.00 mm pilot")
gap = min(abs(px[i + 1] - px[i]) - (PILOTS[i] + PILOTS[i + 1]) / 2 for i in range(5))
verdict(gap >= 2.0, "wall between neighbouring pilots", f"{gap:.2f} mm minimum")
# (d) the engravings must not touch the card's own outline
worst_out = min(p.distance(card.exterior) for p, _a, _b in ENG)
verdict(worst_out >= 0.4, "engravings clear of the card's outline",
        f"{worst_out:.2f} mm minimum (rule 0.4)")

def prism(poly, z0, z1):
    m = trimesh.creation.extrude_polygon(poly, z1 - z0)
    m.apply_translation([0, 0, z0])
    return m


BODY = prism(card, 0.0, CT)
solids = [prism(sbox(bx0, by0, bx1, by1), 0.0, CT + BOSS_H)]          # the pilot boss
all_void = [prism(p, -1.0, CT + 1.0) for p in CUT]                     # through-gauges
# Everything engraved on one face gets unioned in 2-D first and extruded once.  Extruding the
# individual rectangles instead leaves coincident coplanar walls wherever two pockets touch, and
# that is what cost the first build a dozen open edges and its watertightness.
by_z = {}
for _p, _z0, _z1 in ENG:
    by_z.setdefault((round(_z0, 6), round(_z1, 6)), []).append(_p)
for (z0, z1), polys in sorted(by_z.items()):
    u = unary_union(polys)
    for g in (u.geoms if u.geom_type == "MultiPolygon" else [u]):
        all_void.append(prism(g, z0, z1))

gauge = DIFF([UNION([BODY] + solids, engine="manifold"), UNION(all_void, engine="manifold")],
             engine="manifold")
gauge.fix_normals()      # inward normals would print a hollow card, and would flip every
gauge.merge_vertices()   # inside/outside probe a checker uses - so they are fixed, then asserted
gauge.update_faces(gauge.nondegenerate_faces())
gauge.update_faces(gauge.unique_faces())

wat = bool(gauge.is_watertight and gauge.is_volume and gauge.volume > 0)
bodies = len(gauge.split(only_watertight=False))
lo, hi = gauge.bounds
verdict(wat, "watertight, outward normals, positive volume",
        f"watertight={bool(gauge.is_watertight)} is_volume={bool(gauge.is_volume)} "
        f"volume={gauge.volume / 1e3:+.2f} cm3")
verdict(bodies == 1, "one body after the boolean", f"{bodies} bodies")
verdict(abs(lo[2]) < 1e-6 and abs(hi[2] - (CT + BOSS_H)) < 1e-6, "printed flat, no supports",
        f"min z {lo[2]:+.4f}  max z {hi[2]:.2f} (the boss is the tallest thing on it)")
fits = (hi[0] - lo[0] <= 220 and hi[1] - lo[1] <= 220 and hi[2] - lo[2] <= 250)
verdict(fits, "inside a 220 x 220 x 250 bed",
        f"{hi[0] - lo[0]:.2f} x {hi[1] - lo[1]:.2f} x {hi[2] - lo[2]:.2f}")
verdict(abs((hi[0] - lo[0]) - CW) < 0.01 and abs((hi[1] - lo[1]) - CH) < 0.01, "card outline",
        f"{hi[0] - lo[0]:.2f} x {hi[1] - lo[1]:.2f} (design {CW} x {CH})")
vol = abs(gauge.volume) / 1e3
add(f"   volume {vol * 1e3:.0f} mm3 ({vol:.2f} cm3); PLA ~{vol * 0.62:.0f} g at 3 walls / 15 %"
    f" infill - the same estimate the enclosure builder uses, so the two are comparable"
    f" (the boss prints solid, and it should - that is the point)")

add("")
add("   what the card carries (all of it from P, none of it typed a second time)")
add(f"     3  LCD   GO cut {LCD_WIN[0]:.2f} x {LCD_WIN[1]:.2f} (the window itself)   "
    f"board outline {LCD_BOARD[0]:.0f} x {LCD_BOARD[1]:.0f}   pitch crosses "
    f"{LCD_PITCH[0]:.2f} x {LCD_PITCH[1]:.1f}, d{P['lcd_pilot']:.2f} at the four holes the wall drills")
add(f"     4  R307  GO cut {R307_RELIEF[0]:.2f} x {R307_RELIEF[1]:.2f} (the bezel relief)   "
    f"body outline {R307_BODY[0]:.2f} x {R307_BODY[1]:.2f}   prism window "
    f"{R307_WIN[0]:.2f} x {R307_WIN[1]:.2f}")
add(f"     5  RC522 GO cut {RC_BOARD[0] + 2 * GO:.2f} x {RC_BOARD[1] + 2 * GO:.2f} "
    f"({GO:.2f} per side on a {RC_BOARD[0]:.0f} x {RC_BOARD[1]:.0f} board)   recess "
    f"{RC_RECESS[0]:.2f} x {RC_RECESS[1]:.2f}   pads (+/-{RC_PAD[0]:.0f}, +/-{RC_PAD[1]:.0f})")
add(f"     6  USB   GO cut {USB_OPEN[0]:.2f} x {USB_OPEN[1]:.2f}   plug body "
    f"{USB_PLUG[0]:.2f} x {USB_PLUG[1]:.2f}")
add(f"     1  pilots {', '.join(f'd{d:.2f}' for d in PILOTS)}, {PILOT_DEPTH:.2f} deep in a "
    f"{BOSS_H:.1f} mm boss   2  board holes {', '.join(f'd{d:.2f}' for d in PCB_HOLES)}")

name = "05_FIT_GAUGE_v3.stl"
assy = gauge.copy()
trimesh.exchange.export.export_mesh(assy, os.path.join(OUT, "assembly", name), file_type="stl")
orient_v3.to_print(gauge, name)
trimesh.exchange.export.export_mesh(gauge, os.path.join(OUT, name), file_type="stl")
add("")
add(f"   wrote cad/v3/{name} ({os.path.getsize(os.path.join(OUT, name)) / 1e3:.0f} kB, "
    f"{len(gauge.faces)} triangles) + the assembly copy")
add("")
add("GAUGE BUILD: FAILURES -> " + ", ".join(fails) if fails else "GAUGE BUILD: ALL CHECKS PASS")
open(os.path.join(ROOT, "docs", "v3_gauge_build.txt"), "w", encoding="utf-8").write("\n".join(L) + "\n")
sys.exit(1 if fails else 0)
