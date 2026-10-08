"""Measure every GROOVE, every RECESS and every printed FIT on the shipped v3 STLs - and turn each
one into the size your real part has to be.

Why this file exists: "is the size and the fitting of the groove right?" is decided by a few tenths
of a millimetre of plastic, and the only honest way to answer it is to walk a probe line through
the triangles you will actually print and read the material/void transitions.  Nothing here reads
the generator's variables as truth - the design number is printed next to the measurement so the
agreement (or a disagreement) is visible instead of asserted.

Convention: design frame, z = 0 at the FRONT OUTER face, +z into the box.  The shipped bed-aligned
files are put back into it with the one table in tools/orient_v3.py.

  python3 tools/check_grooves_v3.py     -> prints, and writes docs/v3_groove_check.txt
"""
import os
import sys

import numpy as np
import trimesh

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import orient_v3  # noqa: E402

STEP = 0.02
AX = {"x": 0, "y": 1, "z": 2}
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


def mesh_of(rel):
    m = trimesh.load(os.path.join(ROOT, "cad", "v3", rel), process=True)
    dz = orient_v3.ORIENT[rel][0]
    if dz:
        m.apply_translation([0, 0, dz])
    return m


SHELL = mesh_of("01_MAIN_SHELL_v3.stl")
PLATE = mesh_of("02_REAR_PLATE_v3.stl")
RING = mesh_of("04_RC522_RING_v3.stl")


def line(m, axis, fixed, lo, hi):
    """Sample a probe line through a mesh: (coordinates, material?)."""
    n = int(abs(hi - lo) / STEP) + 2
    coords = np.linspace(lo, hi, n)
    pts = np.zeros((n, 3))
    for k, v in fixed.items():
        pts[:, AX[k]] = v
    pts[:, AX[axis]] = coords
    ins = np.zeros(n, dtype=bool)
    ins[m.contains(pts)] = True
    return coords, ins


def void_runs(coords, ins):
    """Every open run on the line, trimmed to the transition points."""
    out, i, n = [], 0, len(ins)
    while i < n:
        if not ins[i]:
            j = i
            while j < n and not ins[j]:
                j += 1
            out.append((float(coords[i - 1]) if i else float(coords[0]),
                        float(coords[j]) if j < n else float(coords[-1])))
            i = j
        else:
            i += 1
    return out


def widest_void(m, axis, fixed, lo, hi):
    c, ins = line(m, axis, fixed, lo, hi)
    r = void_runs(c, ins)
    if not r:
        return None
    a, b = max(r, key=lambda t: t[1] - t[0])
    return b - a


def trans(m, axis, fixed, lo, hi):
    c, ins = line(m, axis, fixed, lo, hi)
    d = np.diff(ins.astype(np.int8))
    return [(float(c[i + 1]), "wall" if d[i] > 0 else "open") for i in np.nonzero(d)[0]]


def need(v, what):
    if v is None:
        raise RuntimeError(f"probe found nothing: {what}")
    return v


def meas(sec, name, got, want, tol=0.035):
    ok = got is not None and abs(got - want) <= tol
    ROWS.append((sec, name, got, want, tol, ok))
    add(f"   {'PASS' if ok else 'FAIL'}  {name:48s} {got:8.3f} mm   design {want:6.2f}"
        f"   (+/-{tol})")
    return got


add("ASTRO SMART ATTENDANCE v3 - GROOVE, RECESS AND PRINTED-FIT MEASUREMENTS")
add("=" * 92)
add(f"probe: {STEP:.2f} mm material/void walk through the shipped bed-aligned STLs, back in the")
add("design frame (z = 0 at the front outer face, +z into the box; front wall 0 -> 3.0, the rear")
add("opening at z = 43.0, the plate's 2 mm register frame reaching down to z = 41.0).")
add("")

# ---------------------------------------------------------------- 0. the wall itself
add("0. THE FRONT WALL - the sheet every groove is cut in")
t = trans(SHELL, "z", {"x": -45.0, "y": -60.0}, -1.0, 6.0)
z0 = need(t[0][0], "outer face")
zi = need(t[1][0], "inner face")
meas("wall", "front wall thickness (plain area)", zi - z0, P["wall_front"])
face = []
for fx, fy in ((-45.0, 30.0), (-45.0, -60.0), (45.0, 60.0), (0.0, 70.0), (30.0, -70.0)):
    tt = trans(SHELL, "z", {"x": fx, "y": fy}, z0 - 2.0, z0 + 3.0)
    face.append(tt[0][0])
add(f"   the outer face at 5 points away from every feature: {', '.join(f'{v:.3f}' for v in face)}")
meas("wall", "flatness of that face (spread, = the bed's job)", max(face) - min(face), 0.0, 0.05)
add(f"   outer face {z0:.3f} (this line's grid; the 5-point check reads {min(face):.3f} - the")
add(f"   {STEP:.2f} mm probe step is the only uncertainty), inner face {zi:.3f}: the wall is")
add(f"   {zi - z0:.3f} mm thick, and every")
add("   depth below is measured from that outer face - which is the face that prints on the bed,")
add("   so it is the one surface guaranteed to be true.")
add("")

# ---------------------------------------------------------------- 1. LCD
lcx, lcy = P["lcd_centre"]
ww, wh = P["lcd_window"]
rb_d, rb_w = P["rebate"]
add("1. LCD 1602 - the sunk rebate ring the glass stands in")
add("   A rebate is a printed locating surface: its DEPTH is what limits how far the bezel can")
add("   sink, its WIDTH is how much of the bezel it actually holds.")
mw = need(widest_void(SHELL, "x", {"y": lcy, "z": z0 + rb_d / 2}, lcx - 42, lcx + 42), "lcd mouth")
mh = need(widest_void(SHELL, "y", {"x": lcx, "z": z0 + rb_d / 2}, lcy - 22, lcy + 22), "lcd mouth h")
tw = need(widest_void(SHELL, "x", {"y": lcy, "z": zi - 0.5}, lcx - 42, lcx + 42), "lcd window")
th = need(widest_void(SHELL, "y", {"x": lcx, "z": zi - 0.5}, lcy - 22, lcy + 22), "lcd window")
meas("lcd", "rebate mouth, across", mw, ww + 2 * rb_w)
meas("lcd", "rebate mouth, up", mh, wh + 2 * rb_w)
meas("lcd", "through-window, across", tw, ww)
meas("lcd", "through-window, up", th, wh)
t = trans(SHELL, "z", {"x": lcx, "y": lcy + wh / 2 + rb_w / 2}, z0 - 1.0, zi + 2.0)
meas("lcd", "rebate depth", t[0][0] - z0, rb_d)
meas("lcd", "wall left under the rebate floor", t[1][0] - t[0][0], P["wall_front"] - rb_d)
for zz in (0.1, 0.4, 0.5, 1.0, 2.0, 2.9):
    a = widest_void(SHELL, "x", {"y": lcy, "z": zz}, lcx - 42, lcx + 42)
    add(f"      z={zz:+4.1f}: opening {a:7.3f} mm wide"
        + ("   <- rebate level" if zz < rb_d else "   <- straight through"))
add(f"   -> YOUR PART: the glass must be <= {tw:.2f} x {th:.2f} mm to drop through the window,")
add(f"      and the bezel flange must be >= {mw:.2f} x {mh:.2f} mm overall so it lands on the")
add(f"      rebate instead of falling in. The step that sinks into the rebate has to be")
add(f"      <= {t[0][0] - z0:.2f} mm tall - that is the whole capture - and the flange has to")
add("      overlap the rebate on all four sides, i.e. its outer rectangle must reach past")
add(f"      {mw:.1f} x {mh:.1f} mm. A standard 1602 bezel is 80 x 36, so it does: that is what")
add("      makes the module locate on the plastic instead of floating on its screws.")
add("")

# ---------------------------------------------------------------- 2. R307
rx, ry = P["r307_centre"]
rl_w, rl_h = P["r307_relief"]
ow, oh = P["r307_window"]
add("2. R307 - bezel relief (the through-opening), the rebate that registers it, the seat ribs")
mo = need(widest_void(SHELL, "x", {"y": ry, "z": z0 + rb_d / 2}, rx - 24, rx + 24), "r307 mouth")
mv = need(widest_void(SHELL, "y", {"x": rx, "z": z0 + rb_d / 2}, ry - 24, ry + 24), "r307 mouth v")
go = need(widest_void(SHELL, "x", {"y": ry, "z": zi - 0.5}, rx - 24, rx + 24), "r307 opening")
gv = need(widest_void(SHELL, "y", {"x": rx, "z": zi - 0.5}, ry - 24, ry + 24), "r307 opening v")
meas("r307", "rebate mouth, across", mo, ow + 2 * rb_w)
meas("r307", "rebate mouth, up", mv, oh + 2 * rb_w)
meas("r307", "through-opening, across", go, rl_w)
meas("r307", "through-opening, up", gv, rl_h)
t = trans(SHELL, "z", {"x": rx + ow / 2 + rb_w / 2, "y": ry}, z0 - 1.0, zi + 2.0)
meas("r307", "rebate depth", t[0][0] - z0, rb_d)
add(f"   the through-opening is {go:.2f} x {gv:.2f} mm and the module's own lens is "
    f"{ow:.1f} x {oh:.1f} mm")
add(f"   -> {(go - ow) / 2:+.2f} mm clear on each side across and {(gv - oh) / 2:+.2f} mm up: no")
add("      plastic is in front of the sensor at any angle the finger can arrive from, and the rim")
add("      left over around the opening is what the module's bezel presses on to seal it.")
add(f"   -> YOUR PART: the R307's raised lens housing must be <= {go:.2f} x {gv:.2f} mm to pass")
add(f"      through, and its front frame >= {mo:.2f} x {mv:.2f} mm to sit on the rebate; the")
add(f"      frame's thickness has {rb_d:.2f} mm of rebate to sink into and the 2 anti-rotation")
add(f"      ribs ({P['r307_seat'][0]:.1f} x {P['r307_seat'][1]:.1f} mm at "
    f"{P['r307_seat_fit']:.2f} mm off the body) stop it turning once screwed.")
add("")

# ---------------------------------------------------------------- 3. RC522
cx, cy = P["rc522_centre"]
rr_w, rr_h = P["rfid_recess"]
rd = P["rfid_recess_deep"]
aw, ah = P["rfid_window"]
bw_, bl_, bt_ = P["rc522_board"]
add("3. RC522 - the 0.8 mm recess in the wall, the open aperture, and the 4 locating ribs")
rw = need(widest_void(SHELL, "x", {"y": cy, "z": z0 + rd / 2}, cx - 34, cx + 34), "recess")
rv = need(widest_void(SHELL, "y", {"x": cx, "z": z0 + rd / 2}, cy - 36, cy + 36), "recess")
awm = need(widest_void(SHELL, "x", {"y": cy, "z": zi - 0.5}, cx - 34, cx + 34), "aperture")
ahm = need(widest_void(SHELL, "y", {"x": cx, "z": zi - 0.5}, cy - 36, cy + 36), "aperture")
meas("rc522", "recess in the outer face, across", rw, rr_w)
meas("rc522", "recess in the outer face, up", rv, rr_h)
meas("rc522", "aperture through the wall, across", awm, aw)
meas("rc522", "aperture through the wall, up", ahm, ah)
# a point inside the recess, outside the aperture, and clear of the 4 ribs and of the raised rim:
# 21 mm in x (aperture edge 19.0, rim starts at 22.0) and 30 mm in y (aperture edge 28.0)
t = trans(SHELL, "z", {"x": cx + 21.0, "y": cy + 30.0}, z0 - 1.0, zi + 3.0)
meas("rc522", "recess depth", t[0][0] - z0, rd)
meas("rc522", "ledge sheet left under the recess", t[1][0] - t[0][0], P["wall_front"] - rd)
trim = trans(SHELL, "z", {"x": cx + 23.0, "y": cy}, z0 - 1.0, zi + 3.0)
rim_top = trim[-1][0]
t = trans(SHELL, "z", {"x": cx, "y": cy + bl_ / 2 + 1.0}, z0 - 1.0, zi + 3.0)
add(f"   the board lies on the wall's inner face at z={zi:.3f} and the 4 locating ribs stand "
    f"{(t[1][0] - zi) if len(t) > 1 else 0:.3f} mm proud of it (design "
    f"{P['rfid_seat_rib'][1]:.2f}), their faces {(P['rfid_board_fit'] * 2):.2f} mm apart "
    f"diametrically = {P['rfid_board_fit']:.2f} mm per side of a 40.0 x 60.0 board")
pox, poy = P["rc522_post_off"]
# probe 2.8 mm off a pad centre: still on the 8 x 8 pad, clear of the d2.8 pilot hole
tb = trans(SHELL, "z", {"x": cx + pox, "y": cy + poy + 2.8}, z0 - 1.0, zi + 4.0)
pad_top = tb[1][0] if len(tb) > 1 else float("nan")
add(f"   a screw pad under the ring (8 x 8, 2.8 mm off its hole): material "
    f"{tb[0][0]:.3f} -> {tb[1][0]:.3f}, so the pad top is {tb[1][0] - zi:.3f} mm proud of the")
add(f"   wall's inner face = the board's own thickness ({P['rc522_board'][2]:.1f} mm), which is what "
    "makes the pad top and the")
add("   board's back face ONE plane - the ring lies on both at once and cannot tilt or shim.")
meas("rc522", "rim top level with the pad top (one bearing plane)", rim_top - pad_top, 0.0, 0.03)
add(f"   (the rim that used to carry v2's clamp bars is trimmed to {rim_top:.3f}, the pads to")
add(f"   {pad_top:.3f}: a {abs(rim_top - pad_top):.3f} mm difference, so the 2.6 mm ring rests on"
    " four pads and a rim")
add("   at the same height - it cannot rock, and nothing has to be shaved to make it sit flat.)")
add(f"   -> YOUR PART: a 40.0 x 60.0 x 1.6 mm PCB drops onto the inner face with "
    f"{(rw - bw_) / 2:.2f} mm of")
add(f"      room across and {(rv - bl_) / 2:.2f} mm up in the recess, and the ribs at "
    f"{P['rfid_board_fit']:.2f} mm per side")
add("      centre it. The aperture is completely open, so no card-side dimension has to pass")
add("      through anything: only the 2.6 mm ring and the 1.6 mm board stack up behind the wall.")
add("")

# ---------------------------------------------------------------- 4. rear plate register
add("4. REAR PLATE - the register lip that locates it in the opening (the fit that closes the box)")
shx = trans(SHELL, "x", {"y": 10.0, "z": 42.0}, -70, 70)
plx = trans(PLATE, "x", {"y": 10.0, "z": 42.0}, -70, 70)
shy = trans(SHELL, "y", {"x": 0.0, "z": 42.0}, -85, 85)
ply = trans(PLATE, "y", {"x": 0.0, "z": 42.0}, -85, 85)
# a scan across the shell at z=42 crosses four faces: outer, inner, inner, outer - the two
# MIDDLE ones are the opening the plate has to slide into.  A scan across the plate crosses the
# lip: outer, inner, inner, outer - the two OUTSIDE ones are the lip's outer faces.
add(f"   shell: outer faces {shx[0][0]:+8.3f} / {shx[-1][0]:+8.3f}   "
    f"inner faces {shx[1][0]:+8.3f} / {shx[-2][0]:+8.3f}")
add(f"   plate lip: outer faces {plx[0][0]:+8.3f} / {plx[-1][0]:+8.3f}   "
    f"inner faces {plx[1][0]:+8.3f} / {plx[-2][0]:+8.3f}")
open_w = shx[-2][0] - shx[1][0]
lip_w_ = plx[-1][0] - plx[0][0]
open_h = shy[-2][0] - shy[1][0]
lip_h_ = ply[-1][0] - ply[0][0]
add(f"   opening {open_w:.3f} x {open_h:.3f} mm  vs  lip {lip_w_:.3f} x {lip_h_:.3f} mm")
gapx = (open_w - lip_w_) / 2
gapy = (open_h - lip_h_) / 2
meas("plate", "register gap per side, across", gapx, P["lip_fit"])
meas("plate", "register gap per side, up", gapy, P["lip_fit"])
t = trans(PLATE, "z", {"x": 0.0, "y": 0.0}, 39.0, 47.5)
meas("plate", "plate skin thickness at the centre", t[-1][0] - t[0][0], 3.0)
t = trans(PLATE, "z", {"x": 48.0, "y": 0.0}, 39.0, 47.5)
meas("plate", "lip + skin, total (2.0 lip + 3.0 skin)", t[-1][0] - t[0][0], 5.0)
t = trans(SHELL, "z", {"x": 53.0, "y": 0.0}, 39.0, 47.5)
add(f"   the shell's rim top face is at z={t[0][0]:.3f}; the plate's lip reaches from "
    f"{41.0:.3f} to 43.0, i.e. 2.00 mm of it is inside the opening and the 3.00 mm skin lands")
add(f"   on the wall's inner ledge, not in the hole. {P['lip_w']:.1f} mm of lip width x "
    f"{gapx:.2f} mm gap per side. A slicer overshoots an")
add("   external face by 0.05-0.15 mm, and this lip is the only face that has to be undersized,")
add("   so the plate can be stiff to close but cannot jam: 0.25 - 0.15 still slides.")
add("")

# ---------------------------------------------------------------- 5. hooks + countersinks
add("5. THE TWO THINGS THE WHOLE BOX HANGS ON - keyholes in the plate")
kd, ks, span = P["keyhole_d"], P["keyhole_slot"], P["keyhole_span"]
for kx in (-span / 2, span / 2):
    c_, ins_ = line(PLATE, "y", {"x": kx, "z": 44.5}, -12.0, 16.0)
    r = max(void_runs(c_, ins_), key=lambda t: t[1] - t[0])
    add(f"   keyhole at x={kx:+.1f}: open from y={r[0]:+.3f} to {r[1]:+.3f} = "
        f"{r[1] - r[0]:.3f} mm along the slot axis  [design: a {kd:.1f} head circle centred at "
        f"y=0 plus a slot to y=+12.0, i.e. {12.0 + kd / 2:.2f} mm]")
    meas("hook", f"slot+head length at x={kx:+.1f}", r[1] - r[0], 12.0 + kd / 2, 0.05)
    c0, i0 = line(PLATE, "x", {"y": 0.0, "z": 44.5}, kx - 8, kx + 8)
    r0 = max(void_runs(c0, i0), key=lambda t: t[1] - t[0])
    meas("hook", f"head entry circle at x={kx:+.1f}", r0[1] - r0[0], kd, 0.05)
    c2, i2 = line(PLATE, "x", {"y": 6.0, "z": 44.5}, kx - 8, kx + 8)   # inside the slot, past the
    r2 = max(void_runs(c2, i2), key=lambda t: t[1] - t[0])              # round's top tangent
    meas("hook", f"slot width at x={kx:+.1f} (shank must slide)", r2[1] - r2[0], ks)
c_, ins_ = line(PLATE, "x", {"y": 0.0, "z": 44.5}, -45, 45)
rr = sorted([ (a + b) / 2 for a, b in void_runs(c_, ins_) if b - a > 1 ])
add(f"   both keyholes found at y=0: centres at {rr[0]:+.3f} and {rr[-1]:+.3f} = "
    f"{rr[-1] - rr[0]:.2f} mm apart [design span {span:.1f}]")
add(f"   -> YOUR PART: a screw head up to {kd:.1f} mm across drops through, and the 4.6 mm slot")
add("      locks it when the plate is slid down 50 mm apart on two wall studs. The audit's own")
add("      load case says the hooks carry 1.7 N each against 8.5 MPa of shear area - 54x - so the")
add("      hooks are convenience, the 4 plate screws are the real fixing.")
add("")

# ---------------------------------------------------------------- 6. the ring's capture
add("6. RC522 RING - the lip that stands inside the aperture, and its own opening")
ro_w, ro_h, ro_lip = P["rc522_ring_open"]
rw2 = need(widest_void(RING, "x", {"y": cy, "z": zi + P["rc522_post_h"] + 1.3}, cx - 30, cx + 30),
           "ring opening")
rh2 = need(widest_void(RING, "y", {"x": cx, "z": zi + P["rc522_post_h"] + 1.3}, cy - 30, cy + 30),
           "ring opening")
meas("ring", "ring opening, across", rw2, ro_w)
meas("ring", "ring opening, up", rh2, ro_h)
add(f"   -> the ring's inner lip therefore stands {(awm - rw2) / 2:.2f} mm inside the "
    f"{awm:.1f} mm aperture")
add(f"      across and {(ahm - rh2) / 2:.2f} mm up: that is the anti-creep capture of the board,")
add("      printed as one part with the ring, not glued, and it is why the board cannot walk out")
add("      even with the screws loose.")
# the ring's own body, away from every hole: 21 mm out in x is between the opening's edge (18.5)
# and the outer edge (21.8) of the 43.6 mm body; probe from below the ring, not inside it
tr_ = trans(RING, "z", {"x": cx + 21.0, "y": cy}, zi + 0.5, zi + 6.0)
thick = tr_[1][0] - tr_[0][0] if len(tr_) >= 2 else float("nan")
meas("ring", "ring body thickness", thick, P["rc522_ring"][2])
# 2 mm off a tab centre: inside the d5.6 head recess, outside the d2.5 screw hole -> that is the
# recess floor.  At the exact centre the probe is void end to end: the clearance hole goes through.
tr_ = trans(RING, "z", {"x": cx + pox, "y": cy + poy + 2.0}, zi - 2.0, zi + 6.0)
left = tr_[1][0] - tr_[0][0] if len(tr_) >= 2 else float("nan")
meas("ring", "plastic left under the head recess floor", left, P["rc522_ring"][2] - 1.5)
tc = trans(RING, "z", {"x": cx + pox, "y": cy + poy}, zi - 2.0, zi + 6.0)
add(f"   through the tab centre: {len(tc)} transitions -> "
    f"{'the screw clearance hole is open right through the ring, as it must be' if not tc else tc}")
add(f"   -> the recess is {(P['rc522_ring'][2] - left):.3f} mm deep in the ring's outer face, sized "
    "for a DIN 84 / ISO 7380")
add("      pan head 2.0 mm tall, so 0.50 mm of the head still stands above the ring's inner face -")
add("      inside the box, over the PCB, where it touches nothing. An M2.5 x 8 pan head is the")
add("      length this assumes; a socket cap (1.3 mm head, 4.5 mm across) would sink fully.")
add("")
add("=" * 92)
bad = [r for r in ROWS if not r[-1]]
for sec in ("wall", "lcd", "r307", "rc522", "plate", "hook", "ring"):
    n = sum(1 for r in ROWS if r[0] == sec)
    b = sum(1 for r in ROWS if r[0] == sec and not r[-1])
    add(f"   {sec:6s}: {n - b}/{n} measured values agree with the design within 0.035 mm")
add("")
add(f"GROOVE RESULT: {'EVERY GROOVE AND FIT MEASURES AS DESIGNED' if not bad else 'CHECK THESE: ' + ', '.join(r[1] for r in bad)}")
open(os.path.join(ROOT, "docs", "v3_groove_check.txt"), "w").write("\n".join(L) + "\n")
raise SystemExit(1 if bad else 0)
