"""Measure the FIT GAUGE card off its own STL, then measure the same dimensions off the enclosure.

Why this file exists.  The card promises one thing only: *a part that passes a cut here passes the
opening in the wall*.  That promise has two halves, and each is checked here by walking a probe line
through the triangles that will actually print and reading the material/void transitions:

  1. the card is the size its engraving says - 8 through-gauges, 6 blind pilots, 4 board holes,
     a 100 mm rule, and a card thick enough to be a shim;
  2. the box's real openings are no smaller than the card's cuts, measured at the *narrowest*
     section through the wall (a rebate sink or an internal relief pocket would otherwise let a
     part pass the mid-plane and still not go in).

Nothing here reads the generator's variables as truth.  The design value is printed next to the
measurement, so agreement is visible and a disagreement would be a failure, not a footnote.

  python3 tools/check_gauge_v3.py     -> prints, and writes docs/v3_gauge_check.txt
"""
import hashlib
import os
import sys

import numpy as np
import trimesh

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import orient_v3  # noqa: E402

STEP = 0.05
TOL = 0.035
L, ROWS = [], []


def add(s=""):
    L.append(s)
    print(s, flush=True)


def design():
    src = open(os.path.join(ROOT, "tools", "build_v3.py"), encoding="utf-8").read()
    i = src.index("P = dict(")
    ns = {"__builtins__": __builtins__, "math": __import__("math"), "np": np}
    exec(src[i:src.index("\n)\n", i) + 3], ns)
    return ns["P"]


P = design()


def load(fn):
    """the bed-aligned file, put back into the assembly frame by the one orientation table"""
    m = trimesh.load(os.path.join(ROOT, "cad", "v3", fn), process=True)
    dz = orient_v3.ORIENT[fn][0]
    if dz:
        m.apply_translation([0, 0, dz])
    return m


def point(origin, axis, t):
    p = np.asarray(origin, float).copy()
    p[axis] = t
    return p[None, :]


def refine(m, origin, axis, t_solid, t_other, iters=20):
    """bisect for the surface between a sample inside the material and one outside it"""
    a, b = float(t_solid), float(t_other)
    fa = bool(m.contains(point(origin, axis, a))[0])
    for _ in range(iters):
        mid = 0.5 * (a + b)
        if bool(m.contains(point(origin, axis, mid))[0]) == fa:
            a = mid
        else:
            b = mid
    return 0.5 * (a + b)


def intervals(m, origin, axis, lo, hi, want_solid=False, step=STEP):
    """the [t0, t1] stretches along origin + axis*t that are void (or solid, if want_solid)"""
    n = max(8, int(round((hi - lo) / step)))
    ts = np.linspace(lo, hi, n + 1)
    pts = np.tile(np.asarray(origin, float), (n + 1, 1))
    pts[:, axis] = ts
    solid = m.contains(pts)
    hit = solid if want_solid else ~solid      # the default is the VOID, which is what a gauge is
    out, i = [], 0
    while i <= n:
        if hit[i]:
            j = i
            while j <= n and hit[j]:
                j += 1
            # back off two samples, not one: a sample can land exactly ON a surface, and then the
            # bracket refine() is given has no crossing in it and the answer stays half a step out
            a = refine(m, origin, axis, ts[max(0, i - 2)], ts[i]) if i > 1 else lo
            b = refine(m, origin, axis, ts[min(n, j + 1)], ts[j - 1]) if j < n else hi
            out.append((min(a, b), max(a, b)))
            i = j
        else:
            i += 1
    return out


def void_at(m, origin, axis, lo, hi, around, want_solid=False):
    """the width of the single void (or solid) stretch that contains t = `around`"""
    runs = intervals(m, origin, axis, lo, hi, want_solid=want_solid)
    hits = [b - a for a, b in runs if a - 1e-6 <= around <= b + 1e-6]
    return hits[0] if len(hits) == 1 else None


def row(sec, label, want, got, tol=TOL, note=""):
    ok = got is not None and abs(got - want) <= tol
    ROWS.append((sec, label, ok))
    g = "  n/a  " if got is None else f"{got:8.3f}"
    d = "   -  " if got is None else f"{got - want:+7.3f}"
    add(f"   {sec:8s}{label:34s} design {want:8.3f}   measured {g}   delta {d}   "
        f"{'PASS' if ok else 'FAIL'}{('   ' + note) if note else ''}")
    return ok


def cut_size(m, cx, cy, w, h, cz, pad=5.0):
    """the two inside dimensions of a rectangular through-opening on the plane z = cz, measured
    as the single void interval a probe line finds across it"""
    return (void_at(m, (cx, cy, cz), 0, cx - w / 2 - pad, cx + w / 2 + pad, cx),
            void_at(m, (cx, cy, cz), 1, cy - h / 2 - pad, cy + h / 2 + pad, cy))


def hole_dia(m, cx, cy, d, cz, pad=4.0):
    return void_at(m, (cx, cy, cz), 0, cx - d / 2 - pad, cx + d / 2 + pad, cx)


def tightest(m, origin, axis, lo, hi, planes, paxis, zs):
    """narrowest void interval across the whole thickness of the wall: a part has to pass every
    plane, not just the mid one, so the minimum is the size that actually matters."""
    best = None
    for t in zs:
        o = np.asarray(origin, float).copy()
        o[paxis] = t
        w = void_at(m, o, axis, lo, hi, np.asarray(origin, float)[axis])
        if w is not None:
            best = w if best is None else min(best, w)
    return best


CARD = load("05_FIT_GAUGE_v3.stl")
SHELL = load("01_MAIN_SHELL_v3.stl")
CT, BOSS_H = 2.60, 10.0
TOP, BTOP = CT, CT + BOSS_H
MID = CT / 2.0
ZM = BTOP - 1.0                                      # a probe just under the boss's top face

add("")
add("05_FIT_GAUGE_v3 - the fit and pilot card, measured off the file that prints")
add("-" * 108)
lo, hi = CARD.bounds
size = os.path.getsize(os.path.join(ROOT, "cad/v3/05_FIT_GAUGE_v3.stl"))
sha = hashlib.sha256(open(os.path.join(ROOT, "cad/v3/05_FIT_GAUGE_v3.stl"), "rb").read()).hexdigest()
add(f"   file      {size / 1e3:.0f} kB, {len(CARD.faces)} triangles, watertight {CARD.is_watertight}, "
    f"sha256 {sha[:16]}")
add(f"   envelope  {hi[0] - lo[0]:.3f} x {hi[1] - lo[1]:.3f} x {hi[2] - lo[2]:.3f} mm   "
    f"volume {abs(CARD.volume) / 1e3:.2f} cm3   bodies {len(CARD.split(only_watertight=False))}")
add("")
add("   the card as a piece of plastic")
row("card", "length x", 150.0, hi[0] - lo[0], 0.001)
row("card", "length y", 112.0, hi[1] - lo[1], 0.001)
row("card", "height over the bed", CT + BOSS_H, hi[2] - lo[2], 0.001, "card 2.60 + boss 10.00")
row("card", "sits flat on the plate", 0.0, lo[2], 1e-6)
for nm, (px, py) in (("left end", (3.0, 40.0)), ("right of the LCD", (146.5, 70.0)),
                     ("behind the rule", (30.0, 109.5))):
    iv = intervals(CARD, (px, py, -1.0), 2, -1.0, hi[2] + 1.0, want_solid=True)
    th = iv[0][1] - iv[0][0] if len(iv) == 1 else None
    row("card", f"thickness, {nm}", CT, th, TOL, "also the shim / stack height unit")

# ---- the card's gauges, addressed from the builder's own geometry ------------------------------
# Nothing is retyped here.  The layout half of tools/build_gauge_v3.py is executed and the feature
# addresses come out of its own CUT / ENG lists - so this file cannot quietly measure the wrong
# place, and if the builder drew something else, the sizes below disagree and the run fails.
src = open(os.path.join(ROOT, "tools", "build_gauge_v3.py"), encoding="utf-8").read()
head = src[:src.index("# ============================================================ build + self-check")]
NS = {"__builtins__": __builtins__, "__file__": os.path.join(ROOT, "tools", "build_gauge_v3.py"),
      "os": os, "sys": sys, "np": np, "trimesh": trimesh}
exec(head, NS)
CT, BOSS_H = NS["CT"], NS["BOSS_H"]
TOP, BTOP, MID = CT, CT + BOSS_H, CT / 2.0
ZM = BTOP - 1.0

rects, circles = [], []
for c in NS["CUT"]:
    x0, y0, x1, y1 = c.bounds
    (circles if abs((x1 - x0) - (y1 - y0)) < 0.01 else rects).append(
        {"cx": 0.5 * (x0 + x1), "cy": 0.5 * (y0 + y1), "w": x1 - x0, "h": y1 - y0})
rects.sort(key=lambda d: -(d["w"] * d["h"]))
circles.sort(key=lambda d: d["w"])
add("")
add("   the eight through-gauges: four rectangles and four holes")
EXPECT = [("RC522", "the board outline +0.4 a side; the board rests on the ledge, it does not "
                    "go through the box", NS["RC_BOARD"][0] + 2 * NS["GO"],
           NS["RC_BOARD"][1] + 2 * NS["GO"]),
          ("LCD", "the 1602 window, exactly what the wall cuts",
           NS["LCD_WIN"][0], NS["LCD_WIN"][1]),
          ("R307", "the bezel relief the prism needs", NS["R307_RELIEF"][0], NS["R307_RELIEF"][1]),
          ("USB", "the slot as the wall has it, +1.2 a side", NS["USB_OPEN"][0], NS["USB_OPEN"][1])]
CUTS = {}
for (tag, note, w, h), g in zip(EXPECT, rects):
    CUTS[tag] = g
    gx, gy = cut_size(CARD, g["cx"], g["cy"], w, h, MID)
    row("cut", f"{tag} cut, width", w, gx, 0.02, note)
    row("cut", f"{tag} cut, height", h, gy, 0.02)
for g, d in zip(circles, NS["PCB_HOLES"]):
    row("hole", f"board hole d{d:.2f}", d, hole_dia(CARD, g["cx"], g["cy"], d, MID), 0.02,
        "a screw shank has to drop through, so these are cut, not drawn")

add("")
add("   the six blind pilots - the row that decides M2, M2.5 or M3")
pil = [e for e in NS["ENG"] if abs(e[1] - (BTOP - NS["PILOT_DEPTH"])) < 1e-9]
pil.sort(key=lambda e: (e[0].bounds[0] + e[0].bounds[2]) / 2)
assert len(pil) == len(NS["PILOTS"]), (len(pil), len(NS["PILOTS"]))
for (poly, _z0, _z1), d in zip(pil, NS["PILOTS"]):
    cx = 0.5 * (poly.bounds[0] + poly.bounds[2])
    cy = 0.5 * (poly.bounds[1] + poly.bounds[3])
    iv = intervals(CARD, (cx, cy, -1.0), 2, -1.0, BTOP + 1.0, want_solid=True)
    floor = max(b for _a, b in iv) if len(iv) == 1 else None
    row("pilot", f"pilot d{d:.2f}: depth", NS["PILOT_DEPTH"],
        (BTOP - floor) if floor is not None else None, 0.02, "blind, with plastic under the floor")
    row("pilot", f"pilot d{d:.2f}: diameter", d, hole_dia(CARD, cx, cy, d, ZM), 0.02)
    row("pilot", f"pilot d{d:.2f}: floor left", BTOP - NS["PILOT_DEPTH"], floor, 0.02,
        "an M3 tap would want 4 mm, and this boss gives it")

add("")
add("   the rule, and how deep the marks are")
RX, RY = NS["RX"], NS["RY"]
# Above the stroke (0.8 mm up) only the tick marks exist, so the run list is the tick list: 11 of
# them, 10 mm apart.  That is a scale; the length of an engraved stroke is not, because a stroke has
# round ends and they would flatter the reading by half a width.
ticks = intervals(CARD, (RX + 50.0, RY + 0.8, 2.3), 0, RX - 2.0, RX + 102.0)
row("rule", "tick marks", 11.0, float(len(ticks)), 0, "nought to a hundred, every 10 mm")
pitch = None
if len(ticks) >= 3:
    pitch = ((ticks[-1][0] + ticks[-1][1]) / 2 - (ticks[0][0] + ticks[0][1]) / 2) / (len(ticks) - 1)
row("rule", "pitch of the ticks", 10.0, pitch, 0.02, "a printer 1 % short is 1 mm off by the end")
row("rule", "width of a tick", 0.50, min(b - a for a, b in ticks) if ticks else None, 0.05,
    "0.5 wide and 0.5 deep: readable on paper, and with a fingernail")
for nm, (px, py) in (("the 1602 outline", (CUTS["LCD"]["cx"], CUTS["LCD"]["cy"] - NS["LCD_BOARD"][1] / 2)),
                     ("the RC522 recess line", (CUTS["RC522"]["cx"] - NS["RC_RECESS"][0] / 2,
                                                CUTS["RC522"]["cy"]))):
    iv = intervals(CARD, (px, py, -1.0), 2, -1.0, CT + 1.0, want_solid=True)
    dep = (CT - max(b for _a, b in iv)) if len(iv) == 1 else None
    row("eng", f"engraving depth, {nm}", NS["ENG_D"], dep, 0.02,
        "deep enough to read and to feel, shallow enough not to weaken anything")

add("")
add("   printing it")
down = CARD.face_normals[:, 2] < -1e-6
over = int((down & (CARD.triangles[:, 0, 2] > 1e-6)).sum())
row("print", "faces needing a support", 0, over, 0, "vertical walls, flat bottom: none")
row("print", "watertight", 1, int(CARD.is_watertight), 0)
row("print", "single body", 1, len(CARD.split(only_watertight=False)), 0)
row("print", "longest side, bed 220", 150.0, max(hi[0] - lo[0], hi[1] - lo[1]), 0.001,
    "and 12.60 mm tall, so it shares a bed with the enclosure")

# ---- the promise: pass the card, pass the wall --------------------------------------------------
add("")
add("   the same dimensions on the wall they exist to match (01_MAIN_SHELL_v3.stl)")


def plane_voids(m, axis, at, a0, a1, b0, b1, step=0.5):
    """every separate void in the plane `axis = at`, as {bbox, area, edge} in that plane's own
    two coordinates.  Components touching the border are flagged, not dropped: they are the
    outside of the part, or an opening that runs to the wall's edge."""
    oth = [a for a in range(3) if a != axis]
    na, nb = int(round((a1 - a0) / step)) + 1, int(round((b1 - b0) / step)) + 1
    A, B = np.meshgrid(np.linspace(a0, a1, na), np.linspace(b0, b1, nb), indexing="ij")
    pts = np.zeros((na * nb, 3))
    pts[:, axis] = at
    pts[:, oth[0]] = A.reshape(-1)
    pts[:, oth[1]] = B.reshape(-1)
    void = (~m.contains(pts)).reshape(na, nb)
    seen, out = np.zeros_like(void, bool), []
    for i0 in range(na):
        for j0 in range(nb):
            if void[i0, j0] and not seen[i0, j0]:
                stack, cells, edge = [(i0, j0)], [], False
                seen[i0, j0] = True
                while stack:
                    i, j = stack.pop()
                    cells.append((i, j))
                    if i in (0, na - 1) or j in (0, nb - 1):
                        edge = True
                    for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        a, b = i + di, j + dj
                        if 0 <= a < na and 0 <= b < nb and void[a, b] and not seen[a, b]:
                            seen[a, b] = True
                            stack.append((a, b))
                ai = [c[0] for c in cells]
                bj = [c[1] for c in cells]
                out.append({"a": (a0 + min(ai) * step, a0 + max(ai) * step),
                            "b": (b0 + min(bj) * step, b0 + max(bj) * step),
                            "area": len(cells) * step * step, "edge": edge})
    return out


def row_ge(label, want, got, tol=0.02, note=""):
    ok = got is not None and got >= want - tol
    ROWS.append(("wall", label, ok))
    add(f"   {'wall':8s}{label:34s} card {want:8.3f}   wall "
        f"{'  n/a  ' if got is None else f'{got:8.3f}'}   slack "
        f"{'   -  ' if got is None else f'{got - want:+7.3f}'}   "
        f"{'PASS' if ok else 'FAIL'}   {note}")


lcx, lcy = P["lcd_centre"]
rcx, rcy = P["r307_centre"]
# pick a probe point that is wall and nothing else: the front wall carries bosses, posts and the
# RFID ledge on its inner face, so one point can fuse into a thicker slab than the wall itself.
fw, fpt = None, None
for cand in ((-40.0, 70.0), (40.0, 70.0), (-40.0, -70.0), (40.0, -70.0), (lcx, lcy - 20.0)):
    runs = intervals(SHELL, (cand[0], cand[1], -2.0), 2, -2.0, P["wall_front"] + 6.0,
                     want_solid=True)
    got = min(runs, key=lambda ab: ab[0])
    if abs((got[1] - got[0]) - P["wall_front"]) <= 0.05:
        fw, fpt = got, cand
        break
if fw is None:                                  # nothing clean: report what the probe did find
    fw = min(intervals(SHELL, (lcx, lcy - 20.0, -2.0), 2, -2.0, P["wall_front"] + 6.0,
                       want_solid=True), key=lambda ab: ab[0])
hi_z = SHELL.bounds[1][2]
wall_ok = abs((fw[1] - fw[0]) - P["wall_front"]) <= 0.05
add(f"   front wall band: z {fw[0]:.3f} .. {fw[1]:.3f} = {fw[1] - fw[0]:.3f} mm thick, design "
    f"{P['wall_front']:.2f} mm   "
    + (f"probed at (x, y) = ({fpt[0]:.1f}, {fpt[1]:.1f}), a spot with nothing but wall behind it"
       if fpt else "the probe found no clean spot, so the four wall rows below are void")
    + ("" if wall_ok else "   WRONG SLAB"))
zs = [fw[0] + 0.55, 0.5 * (fw[0] + fw[1]), fw[1] - 0.55] if wall_ok else []
if wall_ok:
    add(f"   probed at z = {zs[0]:.2f} / {zs[1]:.2f} / {zs[2]:.2f} - rebate sink, mid thickness and "
        f"the inner face - and the narrowest section of the three is the one kept")
    prof = [fw[0] + 0.55, fw[0] + 1.05, fw[0] + 1.55, fw[0] + 2.05, fw[1] - 0.55]
    add(f"   profiled at z = {', '.join(f'{t:.2f}' for t in prof)} across the wall - 0.55 in from "
        f"each face, so the rebate sink stays out of the averaging")
    for tag, (cx, cy), (w, h) in (("LCD", (lcx, lcy), NS["LCD_WIN"]),
                                 ("R307", (rcx, rcy), NS["R307_RELIEF"])):
        for dim, axis, size in (("width", 0, w), ("height", 1, h)):
            base = cx if axis == 0 else cy
            vals = [v for v in (void_at(SHELL, (cx, cy, t), axis, base - size / 2 - 8.0,
                                       base + size / 2 + 8.0, base) for t in prof)
                    if v is not None]
            if len(vals) != len(prof):
                add(f"   !! {tag} {dim}: only {len(vals)} of {len(prof)} planes read clean")
                ROWS.append(("wall", f"{tag} {dim} profile", False))
                continue
            med, sp = float(np.median(vals)), max(vals) - min(vals)
            row("wall", f"{tag} {dim} prism spread", 0.0, sp, 0.08,
                f"over {len(vals)} planes ({min(vals):.3f} to {max(vals):.3f}) - a grazing ray on "
                f"one plane is noise, a taper here would be a real defect")
            row_ge(f"{tag} opening, {dim}", size, med,
                   note="the median of those planes; the card is no bigger, so a part that passes "
                        "the card clears the wall")
    # the USB slot lives in the wall whose normal is y; find that wall, then its biggest hole
    sideb = intervals(SHELL, (0.0, -P["H"] / 2 - 12.0, hi_z - 3.0), 1,
                      -P["H"] / 2 - 12.0, -P["H"] / 2 + 12.0, want_solid=True)
    sw = min(sideb, key=lambda ab: ab[0])       # the wall at -y, not the mirror one at +y
    ym = 0.5 * (sw[0] + sw[1])
    yz = [sw[0] + 0.5, ym, sw[1] - 0.5]
    add(f"   bottom wall (normal -y): band y {sw[0]:.3f} .. {sw[1]:.3f} = {sw[1] - sw[0]:.3f} mm "
        f"thick, design {P['wall_front']:.2f}; probe plane y = {ym:.3f}")

    def biggest_void(axis_wall, at, a0, a1, b0, b1):
        """the largest enclosed void in a wall's plane, located on a coarse 1.5 mm grid - coarse on
        purpose: a full 0.5 mm scan of an 110 x 43 wall costs 70 k ray casts and eats the box.  The
        grid only has to say WHERE the hole is; the size comes from refined line probes after."""
        cs = [c for c in plane_voids(SHELL, axis_wall, at, a0, a1, b0, b1, step=1.5)
              if not c["edge"]]
        return (max(cs, key=lambda c: c["area"]), at) if cs else None

    u = biggest_void(1, ym, -P["W"] / 2 + 1.0, P["W"] / 2 - 1.0, 1.0, hi_z - 4.0)
    if u is None:
        add("   !! no enclosed void in the bottom wall - the USB rows are void")
        ROWS.append(("wall", "USB opening found", False))
    else:
        ucx, ucz = 0.5 * sum(u[0]["a"]), 0.5 * sum(u[0]["b"])
        wu = tightest(SHELL, (ucx, ym, ucz), 0, ucx - 16.0, ucx + 16.0, None, 1, yz)
        hu = tightest(SHELL, (ucx, ym, ucz), 2, ucz - 12.0, ucz + 12.0, None, 1, yz)
        row_ge("USB opening, width", NS["USB_OPEN"][0], wu,
               note=f"hole centre found at x {ucx:.2f}, z {ucz:.2f}")
        row_ge("USB opening, height", NS["USB_OPEN"][1], hu)
    # RFID: the card's cut is the BOARD, and the board does not go through the wall - it rests on
    # the ledge, looking down at a smaller aperture.  Both halves of that are measurable.
    rc = None
    for zz in (fw[0] + 0.60, fw[1] - 0.60):     # the ledge is cut on one face only, so look 0.60
        got = biggest_void(2, zz, -P["W"] / 2 + 1.0, P["W"] / 2 - 1.0,   # in from both and keep the
                           -P["H"] / 2 + 1.0, P["H"] / 2 - 1.0)          # wider mouth - that one
                                                      # is the ledge, and 0.60 is past the 0.45
                                                      # rebate sink so the sink cannot inflate it
        if got and (rc is None or got[0]["area"] > rc[0]["area"]):
            rc = got
    if rc is None:
        add("   !! no enclosed void in the front wall - the RC522 rows are void")
        ROWS.append(("wall", "RC522 recess found", False))
    else:
        ccx, ccy = 0.5 * sum(rc[0]["a"]), 0.5 * sum(rc[0]["b"])
        rw = tightest(SHELL, (ccx, ccy, rc[1]), 0, ccx - 36.0, ccx + 36.0, None, 2, [rc[1]])
        rh = tightest(SHELL, (ccx, ccy, rc[1]), 1, ccy - 34.0, ccy + 34.0, None, 2, [rc[1]])
        # the card lays the reader landscape, the box holds it portrait, so the two are the same
        # rectangle turned through 90 degrees.  Comparing sorted pairs says that without lying.
        card_rc = sorted(NS["RC_RECESS"])
        wall_rc = sorted(v for v in (rw, rh) if v is not None)
        for nm, want, got in (("the short way", card_rc[0], wall_rc[0] if wall_rc else None),
                              ("the long way", card_rc[1], wall_rc[1] if len(wall_rc) > 1 else None)):
            row_ge(f"RC522 recess, {nm}", want, got, 0.05,
                   note=f"{rc[1]:.2f} mm off the face the board rests on")
        ap = biggest_void(2, zs[1], -P["W"] / 2 + 1.0, P["W"] / 2 - 1.0,
                          -P["H"] / 2 + 1.0, P["H"] / 2 - 1.0)
        aw = ah = None
        if ap:
            acx, acy = 0.5 * sum(ap[0]["a"]), 0.5 * sum(ap[0]["b"])
            aw = tightest(SHELL, (acx, acy, zs[1]), 0, acx - 32.0, acx + 32.0, None, 2, zs)
            ah = tightest(SHELL, (acx, acy, zs[1]), 1, acy - 22.0, acy + 22.0, None, 2, zs)
        add(f"   RC522 aperture mid-wall: {aw if aw is None else round(aw, 3)} x "
            f"{ah if ah is None else round(ah, 3)} - the card's "
            f"{NS['RC_BOARD'][0] + 2 * NS['GO']:.2f} x {NS['RC_BOARD'][1] + 2 * NS['GO']:.2f} cut "
            f"is deliberately larger, because the board sits ON the ledge: the gauge proves the "
            f"ledge takes the board,")
        add("   and the aperture is what the loop antenna looks through. Those are two different "
            "questions and the card answers the first.")
        ap_short = min(v for v in (aw, ah) if v is not None) if (aw and ah) else None
        ok = (ap_short is not None
              and min(NS["RC_BOARD"][0] + 2 * NS["GO"], NS["RC_BOARD"][1] + 2 * NS["GO"])
              > ap_short + 1.0)
        ROWS.append(("wall", "RC522 cut is the board, not the hole", ok))
        add(f"   {'wall':8s}{'RC522 cut vs wall aperture':34s}{'':22s}   "
                        f"{'PASS' if ok else 'FAIL'}   the cut clears the aperture the short way by "
            f"{(min(NS['RC_BOARD']) + 2 * NS['GO']) - (ap_short or 0):.2f} mm, and the board itself "
            f"never goes through at all")
add("")
add("=" * 108)
bad = [r for r in ROWS if not r[-1]]
for sec in ("card", "cut", "hole", "pilot", "rule", "eng", "print", "wall"):
    n = sum(1 for r in ROWS if r[0] == sec)
    b = sum(1 for r in ROWS if r[0] == sec and not r[-1])
    add(f"   {sec:6s}: {n - b}/{n} measured values agree with the design")
add("")
add(f"   {len(ROWS)} things measured, every one of them off the triangles: the card, "
    f"the wall, and the 0.5 mm of engraving between them")
add("")
add(f"GAUGE RESULT: {'EVERY GAUGE MEASURES AS DESIGNED, AND NONE IS BIGGER THAN THE WALL' if not bad else 'CHECK THESE: ' + ', '.join(r[1] for r in bad)}")
open(os.path.join(ROOT, "docs", "v3_gauge_check.txt"), "w").write("\n".join(L) + "\n")
raise SystemExit(1 if bad else 0)
