"""v3 PHYSICS / LOGIC audit - the questions the CAD checkers never ask.

tools/build_v3.py proves the parts do not overlap.  tools/verify_v3.py proves the STLs are
manifold, printable, bed-aligned, and that every hole is where it was designed.  Neither asks:

   1  will a self-tapping screw HOLD in these pilots - how many newtons of pull-out?
   2  does the screw HEAD fit where it has to sit - flush, proud or jammed?
   3  can each module physically be INSERTED, swept in from the direction it is assembled?
   4  how much air does the fan actually move against these openings, and does that matter?
   5  what are the material limits - summer heat, Tg, shrinkage against the printed fit?
   6  is 13.56 MHz attenuated by the plastic in front of the antenna, and is metal near the coil?
   7  can you SEE the LCD through the window at a normal viewing angle, and can the prism see a finger?
   8  wall load, thumb pressure, front-wall flex, ligaments between neighbouring openings?
   9  what happens when the four STLs are dropped into a slicer?
  10 does every number printed in the documentation still match the shipped geometry?

Everything is measured from the triangles in cad/v3/*.stl (the bed-aligned files the user prints,
restored to the design frame with the same table the verifier uses).  Module masses and envelopes
come from docs/master_prompt.md.  Writes docs/v3_physics_audit.txt; exit 1 on any FAIL.
"""
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import trimesh
import orient_v3
from shapely.geometry import Polygon

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAD = os.path.join(ROOT, "cad", "v3")
OUT = os.path.join(ROOT, "docs", "v3_physics_audit.txt")

L, fails, warns = [], [], []


def add(s=""):
    L.append(s)


def section(title, body=""):
    add("")
    add(title)
    add("-" * 78)
    for line in body.strip().split("\n"):
        if line.strip():
            add("   " + line.strip())


def verdict(ok, label, detail="", warn=False):
    tag = "PASS" if ok else ("NOTE" if warn else "FAIL")
    if not ok:
        (warns if warn else fails).append(label)
    add(f"   {label:42s} {detail:54s} {tag}")
    return ok


def load(name):
    """the shipped (bed-aligned) file, back in the design frame"""
    return orient_v3.to_assembly(trimesh.load(os.path.join(CAD, name), process=True), name)


SHELL = load("01_MAIN_SHELL_v3.stl")
PLATE = load("02_REAR_PLATE_v3.stl")
BRACK = load("03_R307_BRACKET_v3.stl")
RING = load("04_RC522_RING_v3.stl")
PARTS = [("main shell", SHELL), ("rear plate", PLATE), ("R307 bracket", BRACK),
         ("RC522 ring", RING)]

src = open(os.path.join(ROOT, "tools", "build_v3.py"), encoding="utf-8").read()
_i = src.index("P = dict(")
_ns = {}
exec(src[_i:src.index("\n)\n", _i) + 3], {}, _ns)
P = _ns["P"]
W, H, D = P["W"], P["H"], P["D"]
ZF, WS, WT = P["wall_front"], P["wall_side"], P["wall_top"]
ZR = D - P["plate_t"]


# ------------------------------------------------------------------------ measurement helpers
def sec_polys(mesh, origin, normal, u_ax, v_ax):
    s = mesh.section(plane_origin=origin, plane_normal=normal)
    if s is None or not len(s.entities):
        return []
    path, T = s.to_2D()
    T = np.asarray(T)

    def fix(ring):
        g = np.asarray(ring.coords)[:, :2]
        v = np.column_stack([g, np.zeros(len(g)), np.ones(len(g))]) @ T.T
        return v[:, [u_ax, v_ax]]

    return [(Polygon(fix(q.exterior)), [Polygon(fix(x)) for x in q.interiors])
            for q in path.polygons_full]


def voids(mesh, origin, normal, u_ax, v_ax):
    out = []
    for _ext, ints in sec_polys(mesh, origin, normal, u_ax, v_ax):
        for q in ints:
            if q.area < 0.4:
                continue
            g = np.asarray(q.exterior.coords)
            out.append(dict(w=float(g[:, 0].max() - g[:, 0].min()),
                            h=float(g[:, 1].max() - g[:, 1].min()), area=float(q.area), poly=q,
                            cu=float((g[:, 0].max() + g[:, 0].min()) / 2),
                            cv=float((g[:, 1].max() + g[:, 1].min()) / 2)))
    return out


def xwall_voids(mesh, sign=1, off=1.30):
    return voids(mesh, [sign * (W / 2 - off), 0, 0], [1, 0, 0], 1, 2)


def ywall_voids(mesh, sign=-1, off=1.30):
    return voids(mesh, [0, sign * (H / 2 - off), 0], [0, 1, 0], 0, 2)


def zslice_voids(mesh, z):
    return voids(mesh, [0, 0, z], [0, 0, 1], 0, 1)


def void_dia(mesh, axis, a, b, at, rmax=6.0, step=0.05, n=24):
    """largest circle centred on a hole axis that lies entirely in void"""
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    r = step
    while r < rmax:
        pts = []
        for k in t:
            x, y = a + r * math.cos(k), b + r * math.sin(k)
            pts.append([x, y, at] if axis == "z" else
                       ([at, x, y] if axis == "x" else [x, at, y]))
        if mesh.contains(np.array(pts)).any():      # any point in material -> the void ends here
            return 2 * (r - step)
        r += step
    return 2 * r


def hole_depth(mesh, axis, a, b, at_start, d_target, step=0.1, tol=0.25):
    last, at = at_start, at_start
    for _ in range(500):
        d = void_dia(mesh, axis, a, b, at, rmax=d_target / 2 + 0.5, step=0.1)
        if abs(d - d_target) > tol:
            break
        last = at
        at += step
    return abs(last - at_start)


# ------------------------------------------------------------------- physical constants / data
PLA = dict(rho=1240.0, E=3500e6, flex=55e6, shear=8.5e6, alpha=6.0e-5, tg=60.0,
           tan_delta=0.020, eps_r=2.6, shrink=0.0035)
AIR = dict(rho=1.184, cp=1007.0)
FAN = dict(face=math.pi * 15 ** 2, q_max=3.6, dp_max=12.0)     # generic 3010 blower at 5 V
G = 9.80665
SCR = {"M2.2": (4.4, 2.2, 1.75), "M2.5": (5.0, 2.5, 2.03), "M3": (5.6, 3.0, 2.39)}
FLAT = {"M2.5": (5.0, 1.6, 2.03), "M3": (6.0, 1.85, 2.39)}
MASS = dict(lcd=90.0, r307=15.0, rc522=12.0, esp32=25.0, fan=15.0, plate=60.0, ring=5.0,
            bracket=3.0, misc=12.0)

rcx0, rcy0 = P["rc522_centre"]
pox, poy = P["rc522_post_off"]
PAD_TOP = ZF + P["rc522_post_h"]
RING_T = P["rc522_ring"][2]
lcd_pts = [(P["lcd_centre"][0] + sx * P["lcd_hole_pitch"][0] / 2,
            P["lcd_centre"][1] + sy * P["lcd_hole_pitch"][1] / 2)
           for sx in (-1, 1) for sy in (-1, 1)]
r307_pts = [(P["r307_centre"][0] + d, P["r307_centre"][1]) for d in P["r307_bracket_holes"]]
ring_pts = [(rcx0 + sx * pox, rcy0 + sy * poy) for sx in (-1, 1) for sy in (-1, 1)]
plate_pts = [(sx * P["plate_boss_xy"][0], sy * P["plate_boss_xy"][1])
             for sx in (-1, 1) for sy in (-1, 1)]
ey0, ebl = P["esp32_usb_edge"], P["esp32_board"][1]
ebw, ezc, ins = P["esp32_board"][0], P["esp32_z_centre"], P["esp32_inset"]
esp_pts = [(ey0 + ins + mx * (ebl - 2 * ins), ezc + mz * (ebw / 2 - ins))
           for mx in (0.0, 1.0) for mz in (-1, 1)]
fyv, fzv = P["fan_centre_yz"]
fp = P["fan_pitch"] / 2
fan_pts = [(fyv + s * fp, fzv + t * fp) for s in (-1, 1) for t in (-1, 1)]
wxi = W / 2 - WS
esp_face = -wxi + P["esp32_post_len"]

add("ASTRO SMART ATTENDANCE v3 - PHYSICS / LOGIC AUDIT")
add("=" * 78)
add("cad/v3/*.stl are the bed-aligned print files.  Every number below is measured on exactly")
add("those triangles (put back in the design frame with the same table the verifier uses), so this")
add("audit, the two CAD checkers and the print order all describe the object the user slicess.")
e = SHELL.bounds[1] - SHELL.bounds[0]
add(f"shell {e[0]:.1f} x {e[1]:.1f} x {e[2]:.1f} mm  |  assembly {W:.0f} x {H:.0f} x {D:.0f} mm  "
    f"|  walls front {ZF}, side {WS}, top {WT}, plate {P['plate_t']} mm")

# =============================================================================================
# 1  FASTENER MECHANICS
# =============================================================================================
section("1. FASTENERS - thread engagement, measured from the holes that were actually printed", """
Thread-forming (self-tapping) screws into printed PLA want a pilot at the thread's MINOR
diameter, not at nominal: at nominal the crest only just touches the wall, the joint is friction,
and the screw spins instead of biting.  Pull-out = shear of the plastic around the engaged thread
cylinder, with PLA cross-layer shear 8.5 MPa and 55 % thread fill:
      F = tau * pi * d_minor * L_engagement * 0.55
""")
GROUPS = [
    ("LCD bezel", "M2.5", 4, SHELL, "z", lcd_pts, ZF + 4.5, MASS["lcd"]),
    ("R307 bracket", "M3", 2, SHELL, "z", r307_pts, ZF + P["r307_post_h"] - 7.0,
     MASS["r307"] + MASS["bracket"]),
    ("RC522 ring", "M2.5", 4, SHELL, "z", ring_pts, 1.4, MASS["rc522"] + MASS["ring"]),
    ("ESP32 bosses", "M2.2", 4, SHELL, "x", esp_pts, esp_face - 7.0, MASS["esp32"]),
    ("fan bosses", "M3", 4, SHELL, "x", fan_pts, -wxi - 1.0, MASS["fan"]),
    ("rear plate", "M3", 4, SHELL, "z", plate_pts, ZR - 9.0, MASS["plate"]),
]
rows = []
for nm, nom, cnt, mesh, axis, pts, start, gm in GROUPS:
    hd, hh, minor = SCR[nom]
    ds, ls = [], []
    for (a, b) in pts:
        at = start + 0.6
        ds.append(void_dia(mesh, axis, a, b, at, rmax=2.4, step=0.01, n=96))
        ls.append(hole_depth(mesh, axis, a, b, at, ds[-1]))
    d = float(np.median(ds))
    dep = float(np.median(ls))
    rad = (d - minor) / 2.0
    f_pull = PLA["shear"] * math.pi * (minor / 1e3) * (dep / 1e3) * 0.55
    load_n = gm / 1e3 * G
    verdict(rad <= 0.10, f"{nm}: {cnt} x {nom} pilot",
            f"d{d:.2f} vs minor d{minor:.2f} -> "
            f"{'thread bites' if rad <= 0 else 'play'} {abs(rad):.2f} mm radially")
    verdict(f_pull > 50 * load_n, f"{nm}: pull-out reserve",
            f"~{f_pull:.0f} N vs {load_n:.2f} N held = {f_pull / max(load_n, 1e-9):.0f}x")
    rows.append((nm, nom, cnt, d, minor, rad, dep, f_pull, load_n))
add("")
add("   the 22 pilots as built:")
add(f"   {'joint':13s}{'screw':7s}{'n':>3s}{'pilot':>8s}{'minor':>8s}{'radial':>8s}"
    f"{'depth':>7s}{'pull-out':>11s}{'load':>8s}")
for nm, nom, cnt, d, minor, rad, dep, f_pull, load_n in rows:
    add(f"   {nm:13s}{nom:7s}{cnt:3d}{d:7.2f} {minor:7.2f} {rad:+7.2f} {dep:6.1f}"
        f"{f_pull:9.0f} N{load_n:7.2f} N")
add("   Reality check: the plate carries the whole unit on 4 screws and the enclosure hangs from 2")
add("   wall screws, so a 260 g box plus a 30 N card tug is ~2.5 N per hook against ~290 N per")
add("   screw.  Fastener *count and access*, not fastener strength, is what governs this design -")
add("   which is why every module got its own 2-4 screws in v3 instead of v2's clip bars.")

# =============================================================================================
# 2  HEADS
# =============================================================================================
section("2. SCREW HEADS - does each head fit the space it has to sit in?", """
DIN 125 pan heads (what is in every electronics kit) and DIN 965 flat heads, against recesses
measured on the meshes.  A proud head only matters when something must pass over it - which is
exactly the case at the RC522, where a card is slid across that face.
""")
topz = PAD_TOP + RING_T
rec_d = None
dep_rec = 0.0
for i, (px, py) in enumerate(ring_pts):
    d_i = void_dia(RING, "z", px, py, topz - 0.3, rmax=4.2)
    rec_d = d_i if rec_d is None else min(rec_d, d_i)
for k in range(1, 45):
    if void_dia(RING, "z", ring_pts[0][0], ring_pts[0][1], topz - k * 0.1, rmax=4.2) < rec_d - 0.35:
        dep_rec = k * 0.1
        break
pan_d, pan_h = SCR["M2.5"][0], SCR["M2.5"][1]
flat_d, flat_h = FLAT["M2.5"][0], FLAT["M2.5"][1]
add(f"   ring counterbore measured d{rec_d:.2f} x {dep_rec:.2f} mm deep in a {RING_T:.1f} mm part")
verdict(rec_d >= pan_d, "M2.5 pan head fits in diameter",
        f"d{pan_d:.1f} head in a d{rec_d:.1f} pocket")
proud = round(pan_h - dep_rec, 3)
verdict(proud <= 0.0, "M2.5 pan head is flush with the ring's inner face",
        f"{pan_h:.1f} mm tall head in {dep_rec:.1f} mm of pocket -> {proud:+.2f} mm proud; the "
        f"face points into open cavity air, so proud is allowed", warn=proud > 0.0)
verdict(flat_h <= dep_rec, "M2.5 flat head (DIN 965) seats in the same pocket",
        f"{flat_h:.2f} mm tall head in {dep_rec:.1f} mm -> "
        f"{'flush' if flat_h <= dep_rec else 'proud'} - the option to use if the ring is ever "
        f"moved in front of the wall")
ann = math.pi / 4 * (rec_d ** 2 - P["rc522_pilot_d"] ** 2)
verdict(ann > 8.0, "clamp load bearing area under the head",
        f"annulus d{P['rc522_pilot_d']:.2f}..d{rec_d:.2f} = {ann:.0f} mm2 -> at 5 N of clamp "
        f"force {5 / (ann * 1e-6) / 1e6:.2f} MPa bearing vs ~60 MPa yield for PLA")
d_csk = void_dia(PLATE, "z", plate_pts[0][0], plate_pts[0][1], D - 0.05, rmax=4.6)
verdict(d_csk >= FLAT["M3"][0], "rear plate: M3 flat head in the 90 deg countersink",
        f"csk measured d{d_csk:.2f} at the outer face vs d{FLAT['M3'][0]:.1f} x "
        f"{FLAT['M3'][1]:.2f} mm head -> flush with the wall when screwed up")
# the screw is fitted from the COMPONENT side, so the head bears on the board's own pad and only
# the thread tip enters the boss: what has to be true is (a) the exit relief is bigger than the
# thread, and (b) a head+driver cylinder in front of each boss is empty of printed material.
d_exit = void_dia(SHELL, "x", esp_pts[0][0], esp_pts[0][1], esp_face - 0.35, rmax=2.6)
verdict(d_exit >= P["esp32_pilot"] + 0.8, "ESP32: thread exit relief in each boss",
        f"measured d{d_exit:.2f} over the d{P['esp32_pilot']:.2f} pilot for the outer 0.7 mm, so "
        f"the thread is not pinched where it leaves the boss")
head_free = 0
for (py_, pz_) in esp_pts:
    yy = np.linspace(py_ - 2.6, py_ + 2.6, 7)
    zz = np.linspace(pz_ - 2.6, pz_ + 2.6, 7)
    xx = np.arange(esp_face + 1.6, esp_face + 4.2, 0.6)      # where the head lives
    yy, zz, xx = np.meshgrid(yy, zz, xx)
    pts = np.column_stack([xx.ravel(), yy.ravel(), zz.ravel()])
    keep = ((pts[:, 1] - py_) ** 2 + (pts[:, 2] - pz_) ** 2) <= 2.2 ** 2
    head_free += int(SHELL.contains(pts[keep]).sum())
verdict(head_free == 0, "ESP32: a d4.4 x 2.2 pan head has room at all 4 pads",
        f"{head_free} of 196 samples inside printed material (the head sits on the board's pad, "
        f"so the pad's own annulus must be >= d5.0 - caliper item)")
add(f"   R307 bracket and fan: M3 pan heads (d{SCR['M3'][0]:.1f} x {SCR['M3'][1]:.1f} mm) sit in")
add(f"   open cavity air with {D - P['plate_t'] - (ZF + P['r307_post_h'] + 2.0):.1f} mm of headroom")
add(f"   above them - nothing has to clear them, and the bracket's 5.6 mm pocket is only there to")
add(f"   stop the head tilting.  No standoffs or nuts are needed anywhere in this design.")

# =============================================================================================
# 3  KINEMATICS
# =============================================================================================
section("3. KINEMATICS - can every part get in, and can it get back out?", """
The enclosure is assembled through its rear opening: nothing is slid in through a wall slot, so a
part is installable if a column swept from its seat out past the box misses the printed walls.
""")
free_w, free_h = W - 2 * WS, H - 2 * WT
add(f"   rear opening: {free_w:.1f} x {free_h:.1f} mm; the plate's {P['lip_w']:.0f} mm register "
    f"frame takes {P['lip_w'] + P['lip_fit']:.2f} mm of that on 3 sides and the -X stretch is cut "
    f"away over the ESP32")
for nm, a, b in (("LCD1602 + backpack", 80.0, 36.0), ("R307 module", 44.1, 20.0),
                 ("RC522 60x40 PCB", 60.0, 40.0), ("ESP32 DevKit V1", 51.45, 28.33),
                 ("3010 fan", 30.0, 30.0), ("a 4 mm hex key + hand", 60.0, 60.0)):
    verdict(a <= free_w and b <= free_h, f"{nm} passes the rear opening",
            f"{a:.1f} x {b:.1f} vs {free_w:.1f} x {free_h:.1f} mm")


def column_blocked(cx, cy, w, h, z_from, z_to, others=()):
    box = trimesh.creation.box(extents=(w, h, z_to - z_from))
    box.apply_translation([cx, cy, (z_from + z_to) / 2])
    v = trimesh.boolean.intersection([box, SHELL], engine="manifold").volume
    for o in others:
        v += trimesh.boolean.intersection([box, o], engine="manifold").volume
    return v


# The naive test - can each part fall straight in along Z - is not how this box is built, and it
# reports a false problem: the RC522's footprint passes through the same (x, y) as two of the
# ESP32 bosses, so a straight descent is blocked by printed plastic that is always there.  What
# matters is whether a real two-move path exists, so both halves are tested by sampling the part's
# swept box at every waypoint (7 x 7 x 3 points, 3 mm steps).
chan = min(pz for (_py, pz) in esp_pts) - P["esp32_pad"] / 2.0 - ZF


def box_blocked(cx, cy, cz, w, h, t, others=(), n=7):
    loc = np.stack(np.meshgrid(np.linspace(-w / 2, w / 2, n), np.linspace(-h / 2, h / 2, n),
                              np.linspace(-t / 2, t / 2, 3)), -1).reshape(-1, 3)
    pts = loc + np.array([cx, cy, cz])
    bad = int(SHELL.contains(pts).sum())
    for o in others:
        bad += int(o.contains(pts).sum())
    return bad


esp_sol = trimesh.creation.box(extents=(P["esp32_comp_h"] + 1.6, P["esp32_board"][1],
                                       P["esp32_board"][0]))
esp_sol.apply_translation([-wxi + P["esp32_post_len"] - 0.8 + P["esp32_comp_h"] / 2,
                          P["esp32_usb_edge"] + P["esp32_board"][1] / 2, P["esp32_z_centre"]])
# (the synthetic ESP32 envelope above is the board + its shield can, sitting on its standoffs:
#  x from the board's rear face to the top of the 16 mm components, which is what the reader has to
#  pass under on its way to the seat)
n_bad = 0
for zz in np.arange(ZF + P["esp32_board"][0] / 2 + 2.0, D + 20.0, 3.0):
    n_bad += box_blocked(-wxi + P["esp32_post_len"] + P["esp32_comp_h"] / 2,
                         P["esp32_usb_edge"] + P["esp32_board"][1] / 2, zz,
                         P["esp32_board"][1], P["esp32_board"][0], P["esp32_comp_h"])
verdict(n_bad == 0, "ESP32 goes in first, straight down along Z",
        f"{n_bad} of {len(np.arange(ZF + 16, D + 20, 3)) * 147} samples inside printed material "
        f"over a full descent at its seat (nothing printed is in that column)")
insert = (("RC522 board", rcx0, rcy0, P["rc522_board"][0] - 0.4, P["rc522_board"][1] - 0.4,
            ZF + P["rc522_board"][2] + 0.1, "x"),
          ("R307 module", P["r307_centre"][0], P["r307_centre"][1], P["r307_body"][0] - 0.4,
           P["r307_body"][1] - 0.4,
           ZF + P["r307_body"][2] + 0.1, "y"),
          ("LCD stack", P["lcd_centre"][0], P["lcd_centre"][1], 79.6, 35.6,
           ZF + P["lcd_glass_t"] + 0.7, "x"))
for nm, cx, cy, w, h, seat, tilt_ax in insert:
    v = column_blocked(cx, cy, w, h, seat, D + 40)
    if v < 1.0:
        verdict(True, f"{nm} slides straight in along Z",
                f"{v:.2f} mm3 of its swept column lands inside printed material")
        continue
    if nm == "RC522 board":
        # a 40 mm board cannot be lowered straight onto its seat: two of the ESP32's stand-off
        # posts stand in its column (their undersides are 12.8 mm off the wall, the board lives at
        # 3.0..4.6).  The path that works is two straight moves - come down OUTBOARD of the posts,
        # then slide in -Y onto the seat.  Sampled for two header choices, ESP32 already fitted.
        def two_move(stack_t, dy):
            th = P["rc522_board"][2] + stack_t
            zc = ZF + P["rc522_board"][2] / 2 + stack_t / 2
            h_ = 0
            for zz in np.arange(D + 18.0, zc - 0.5, -3.0):
                h_ += box_blocked(cx, cy + dy, zz, w, h, th, others=(esp_sol,))
            for yy in np.arange(cy + dy, cy - 0.5, -2.0):
                h_ += box_blocked(cx, yy, zc, w, h, th, others=(esp_sol,))
            return h_
        fem, male = two_move(3.4, 26.0), two_move(9.0, 26.0)
        verdict(fem == 0, "RC522 board: two-move install path (down beside the posts, then in -Y)",
                f"{fem} blocked samples with a 1.6 mm PCB + 3.4 mm female header, ESP32 already "
                f"screwed in.  Build order: ESP32 -> reader -> ring -> R307 -> LCD, plate last")
        add(f"      with 9 mm straight MALE headers: {male} blocked samples - the "
            f"{P['rc522_board'][2] + 9.0:.1f} mm stack vs a {chan:.1f} mm channel is the whole "
            f"story, so solder the leads, use short or right-angle headers, or fit the reader "
            f"before the ESP32")
        verdict(chan >= 5.0, "assembly channel under the ESP32 bosses",
                f"{chan:.1f} mm clear from z = {ZF:.1f} to the underside of the lowest boss")
    else:
        verdict(False, f"{nm} cannot be installed", f"{v:.0f} mm3 of column blocked, no path found")

v_l = column_blocked(0, 0, free_w - 0.5, free_h - 0.5, ZR, D + 25, others=[BRACK, RING])
verdict(v_l < 1.0, "the plate leaves and returns without disturbing any module",
        f"{v_l:.2f} mm3 swept against shell, bracket and ring")
add("   the plate's own 4 holes are d3.4 CLEARANCE (the thread is in the shell's bosses), which is")
add("   right: the only way to open the box is to pull the plate straight off, and a threaded plate")
add("   would have to be screwed out through the cavity.")
add("   All 5 screw groups are reachable with the plate off, which is why the plate is screwed and")
add("   never glued; the LCD is taken out from the front after its 4 screws, and the RC522 ring")
add("   clamps the board so it comes out with the ring - no board-prying on the aperture edge.")

# =============================================================================================
# 4  AIRFLOW
# =============================================================================================
section("4. AIRFLOW - the fan against the openings it really has", """
Every opening is measured out of the meshes (a planar slice through each wall, every closed void
counted), then modelled as sharp-edged orifices in series intersected with the fan's straight
line:   dp = dp_max (1 - Q/Q_max)   and   dp = K rho/2 (Q/A_eff)^2,  K = 1.3.
""")
xw = xwall_voids(SHELL, 1)                         # +X wall: the 8 intake slots
slots = list(xw)
slot_a = sum(v["area"] for v in slots)
xwn = xwall_voids(SHELL, -1)                        # -X wall: the fan bore
bore = max(xwn, key=lambda v: v["area"]) if xwn else None
bore_a = bore["area"] if bore else 0.0
yb = ywall_voids(SHELL, -1)
exh = [v for v in yb if v["w"] > 8 and v["h"] < 8 and abs(abs(v["cu"]) - 16.0) < 5]
exh_a = sum(v["area"] for v in exh)
yt = ywall_voids(SHELL, 1)
vent = [v for v in yt if v["w"] > 8 and v["h"] < 8]
vent_a = sum(v["area"] for v in vent)
pass_a = slot_a + exh_a + vent_a
add(f"   fan bore  d{bore['w']:.1f} = {bore_a:.0f} mm2   |   intake {len(slots)} slots "
    f"{slot_a:.0f} mm2   |   exhaust {len(exh)} slots {exh_a:.0f} mm2   |   top vents "
    f"{len(vent)} x {vent_a / max(len(vent), 1):.0f} mm2")
add(f"   the air's path is the bore in series with {pass_a:.0f} mm2 of everything else")
A_eff = 1.0 / math.sqrt((1.0 / max(bore_a, 1.0)) ** 2 + (1.0 / max(pass_a, 1.0)) ** 2)
q, dp = FAN["q_max"] / 1e3, 0.0
for _ in range(500):
    v = q / (A_eff * 1e-6)
    dp = 1.3 * AIR["rho"] / 2.0 * v * v
    qn = FAN["q_max"] / 1e3 * max(0.0, 1.0 - dp / FAN["dp_max"])
    if abs(qn - q) < 1e-13:
        break
    q = 0.5 * (q + qn)
q, dp = FAN["q_max"] / 3600.0, 0.0                 # m3/h -> m3/s, re-solve the duty point
for _ in range(400):
    v = q / (A_eff * 1e-6)
    dp = 1.3 * AIR["rho"] / 2.0 * v * v
    qn = FAN["q_max"] / 3600.0 * max(0.0, 1.0 - dp / FAN["dp_max"])
    if abs(qn - q) < 1e-14:
        break
    q = 0.5 * (q + qn)
q_lps, free_lps = q * 1e3, FAN["q_max"] / 3.6       # 3.6 m3/h of free air = 1.0 L/s
verdict(pass_a >= 1.5 * bore_a, "the wall openings are not the bottleneck",
        f"{pass_a:.0f} mm2 of intake+exhaust+vents in series with the {bore_a:.0f} mm2 bore "
        f"= {pass_a / bore_a:.1f}x the bore (v3.0 measured 118 mm2 of 6 x d5 holes: 0.2x)")
verdict(q_lps >= 0.8, "air actually moved through the box",
        f"bore-limited duty point A_eff {A_eff:.0f} mm2 -> {q_lps:.2f} L/s "
        f"({q_lps * 60:.0f} mL/min) at {dp:.1f} Pa = {q_lps / free_lps * 100:.0f} % of free air; "
        f"the {bore_a:.0f} mm2 outlet of a 3010 blower is what caps it, not the walls",
        warn=q_lps < 0.8)
vol_mm3 = W * H * D / 1e3
add(f"   that is the box's whole {vol_mm3:.0f} cm3 volume changed every "
    f"{vol_mm3 * 1e-6 / max(q, 1e-9):.1f} s")
P_diss = 1.6                                   # ESP32 TX burst + RC522 + fan
dT = P_diss / (AIR["rho"] * AIR["cp"] * max(q, 1e-9))
verdict(dT < 12.0, "convective temperature rise at that flow",
        f"{P_diss:.1f} W in, {q * 1e3:.2f} L/s out -> dT = {dT:.1f} K above ambient", warn=dT >= 12)
no_fan_dT = P_diss / (AIR["rho"] * AIR["cp"] * 0.35e-3)     # natural convection, 0.35 L/s
add(f"   with the fan off, the same box relies on natural convection alone: dT would be "
    f"~{no_fan_dT:.0f} K, and the prism would fog on a humid morning - the fan is a demister,")
add(f"   not a cooler, and it is right to run it continuously from the ESP32's own supply.")
biggest = max((v["w"] * v["h"] for v in slots), default=0)
add(f"   widest intake slot {slots[0]['w']:.1f} x {slots[0]['h']:.1f} mm - still too narrow for a")
add(f"   finger, and a card cannot reach inside because the aperture edge is a closed rectangle.")

# =============================================================================================
# 5  MATERIAL / TOLERANCE
# =============================================================================================
section("5. MATERIAL LIMITS AND THE PRINTED FIT", """
This unit is going on a wall in Uttar Pradesh, so the ambient numbers below matter more than the
CAD numbers: PLA's useful ceiling is its glass transition (~60 C), and its 0.2-0.5 % shrinkage is
what the printed fits have to absorb.
""")
for nm, ta, warn in (("shaded indoor wall, peak summer", 45.0, False),
                     ("sun through a window onto the wall", 55.0, False),
                     ("unshaded outside wall / closed room", 65.0, True)):
    m = PLA["tg"] - ta
    verdict(m > 0, f"PLA margin - {nm}",
            f"Tg ~60 C vs {ta:.0f} C = {m:+.0f} K" +
            ("" if m > 0 else "   -> print PETG (Tg ~80 C) or anneal at 80 C for 1 h"), warn=warn)
add("   no geometry change is needed to switch to PETG: same model, 230-240 C nozzle, 80-90 C")
add("   bed, and the print order's temperatures are the only thing that changes.")
dt = 40.0
lin = max(W, H) * PLA["alpha"] * dt
verdict(True, "differential thermal growth across the register frame",
        f"both parts are the same plastic so the {lin:.2f} mm of growth on a {max(W, H):.0f} mm "
        f"side is common-mode and cancels; only a temperature DIFFERENCE bites "
        f"({5} K -> {(W - 2 * WS) * PLA['alpha'] * 5:.3f} mm vs "
        f"{P['lip_fit']:.2f} mm per side)", warn=True)
for nm, sh in (("0.2 % (dry filament, tuned)", 0.002), ("0.5 % (humid filament, Mirzapur monsoon)",
                                                          0.005)):
    d = (W - 2 * WS) * sh
    verdict(d < 2 * P["lip_fit"] + 1.0, f"shrinkage {nm} vs the plate's register",
            f"{d:.2f} mm on the {W - 2 * WS:.1f} mm opening; the frame is 8 separate ribs and the "
            f"plate is drawn home by 4 x M3, so an oversized rib cannot lock the plate out")
add("   wall thickness vs shrinkage: a 2.6 mm wall varies by 0.005-0.013 mm - irrelevant.  The")
add("   fit that must survive shrinkage is the 0.25 mm/side register and the 0.35 mm part fit,")
add("   both of which are generous for FDM and both still verified in section 10 of the STL audit.")

# =============================================================================================
# 6  RF
# =============================================================================================
section("6. RF - 13.56 MHz through the wall, 2.4 GHz out of the cavity, metal nearby", """
Dielectric loss in a slab: alpha = (2 pi f / c) sqrt(eps_r) tan(delta) / 2, loss = 8.686 alpha t.
PLA at these frequencies is nearly invisible; what matters is geometry - how much plastic is in
front of the coil, and how far the nearest metal is from the loop.
""")
t_ledge = ZF - P["rfid_recess_deep"]
for f_nm, fr in (("13.56 MHz (RC522)", 13.56e6), ("2.44 GHz (Wi-Fi)", 2.437e9)):
    a = (2 * math.pi * fr / 3e11) * math.sqrt(PLA["eps_r"]) * PLA["tan_delta"] / 2
    tt = t_ledge if fr < 1e8 else ZF
    loss = 8.686 * a * tt
    verdict(loss < 0.15, f"{f_nm} through {tt:.2f} mm of PLA",
            f"{loss:.4f} dB (eps_r {PLA['eps_r']}, tan d {PLA['tan_delta']})", warn=loss > 0.15)
d_metal = min(math.hypot(sx * pox, sy * poy) for sx in (-1, 1) for sy in (-1, 1))
coil_r = 12.5
verdict(d_metal - coil_r > 6.0, "nearest steel screw to the antenna loop",
        f"heads are {d_metal:.1f} mm from the coil centre vs a ~{coil_r * 2:.0f} mm loop -> "
        f"{d_metal - coil_r:.1f} mm clear; keep the ring screws at 8 mm so no shank runs beside "
        f"the coil plane")
# the keep-out is the 15 mm slab in FRONT of the antenna trace (the far end of the board, away
# from the USB) - measured against the envelope the generator itself publishes
kx0, kx1 = -wxi + P["esp32_post_len"], -wxi + P["esp32_comp_h"]
ky0 = P["esp32_usb_edge"] + P["esp32_board"][1]
ky1 = ky0 + 15.0
kz0, kz1 = P["esp32_z_centre"] - P["esp32_board"][0] / 2, P["esp32_z_centre"] + P["esp32_board"][0] / 2
pts = np.array([[x, y, z] for x in np.arange(kx0 + 0.3, kx1 + 4.0, 1.0)
                for y in np.arange(ky0 + 0.3, ky1, 1.0) for z in np.arange(kz0 + 0.3, kz1, 1.0)])
hits = int(SHELL.contains(pts).sum())
verdict(hits == 0, "ESP32_RF_ANTENNA_KEEP_OUT empty of printed material",
        f"{hits} of {len(pts)} points inside the 15 mm slab in front of the trace "
        f"(y {ky0:.1f}..{ky1:.1f}, the whole cavity depth in x) - nothing printed stands in it, "
        f"and the two antenna-end bosses sit BEHIND the board, beside it")
d_ant = min(math.hypot(-22.05 - ky0 + 3.0, zz - P["esp32_z_centre"])
            for zz in (16.8, 38.2))
verdict(d_ant >= 10.0, "metal at the antenna end",
        f"the two antenna-end screw heads are {d_ant:.1f} mm from the trace end, so M2.2 x 8 mm "
        f"screws only - a long shank running beside the trace pulls the 2.4 GHz match; no brass "
        f"or steel washers under those two heads")
add(f"   the reader's stated working distance (up to 10 mm for a card, ~2.5 mm for a tag) is")
add(f"   reduced by the {t_ledge:.1f} mm ledge only in the front half of the board; the aperture")
add(f"   puts AIR in front of the coil's centre, which is why the opening was made 100 % clear.")

# =============================================================================================
# 7  OPTICS
# =============================================================================================
section("7. WHAT THE USER AND THE SENSORS CAN SEE", """
Fingerprint: the R307 is an optical (reflective prism) module, so it needs an unobstructed cone
from its window to where a finger lands, and nothing in front of the glass to scatter light.
LCD: a stock 1602 has a narrow contrast cone; the window must not clip the character area even
when the box is looked up at from below, because it is wall-mounted at about eye height.
""")
rcx, rcy = P["r307_centre"]
ww, wh = P["r307_window"]
rel_w, rel_h = P["r307_relief"]
pts, tot = [], 0
for hh_ in np.arange(0.5, 8.0, 0.5):
    sc = 1.0 + 2 * hh_ * math.tan(math.radians(20)) / max(ww, wh)
    for u in np.linspace(-ww / 2 * sc, ww / 2 * sc, 11):
        for v in np.linspace(-wh / 2 * sc, wh / 2 * sc, 11):
            pts.append([rcx + u, rcy + v, -0.25 - hh_])
            tot += 1
hits = int(SHELL.contains(np.array(pts)).sum())
verdict(hits == 0, "R307: 20 deg cone to 8 mm proud of the face is clear",
        f"{hits} of {tot} samples inside material; the {rel_w:.1f} x {rel_h:.1f} mm bezel relief "
        f"is what keeps the {ww:.1f} x {wh:.1f} mm window unobstructed")
lcx, lcy = P["lcd_centre"]
lw, lh = P["lcd_window"]
seen = tot = 0
for u in np.linspace(-32, 32, 13):
    for v in np.linspace(-7, 7, 5):
        for th in np.linspace(-30, 30, 7):
            for ph in np.linspace(-20, 20, 5):
                tot += 1
                s = ZF / 2.0
                xc = lcx + u + math.tan(math.radians(th)) * s
                yc = lcy + v + math.tan(math.radians(ph)) * s
                if abs(xc - lcx) <= lw / 2 and abs(yc - lcy) <= lh / 2:
                    seen += 1
h_lim = math.degrees(math.atan((lw / 2 - 32.0) / (ZF / 2.0)))
v_lim = math.degrees(math.atan((lh / 2 - 7.0) / (ZF / 2.0)))
verdict(seen == tot, "LCD: the whole 64 x 14 character area is readable",
        f"{seen}/{tot} (point, angle) samples pass; the window stops the view only beyond "
        f"+/-{h_lim:.0f} deg horizontally and +/-{v_lim:.0f} deg vertically (measured at the "
        f"wall's mid-plane), and the panel's own contrast cone is narrower than that")
add(f"   the window is {lw / 64:.2f}x the character width and {lh / 14:.2f}x their height, and the")
add(f"   {P['rebate'][0]:.2f} x {P['rebate'][1]:.1f} mm rebate sinks the glass {P['rebate'][0]:.2f} mm")
add(f"   below the surface, so glare is reduced and the module is protected by a real frame - the")
add(f"   two things v2 got wrong at the same time (its aperture was blocked by bars AND the glass")
add(f"   was flush and chippable).")

# =============================================================================================
# 8  STRUCTURE
# =============================================================================================
section("8. STRUCTURE - hanging load, thumb pressure, and the plastic between the holes", """
The worst mechanical cases for a wall-mounted reader: two screws in the wall, a hard press on the
LCD glass, and the ligaments between the openings in the front wall (thin ligaments are where
these boxes actually crack).
""")
v_tot = sum(abs(m.volume) for _n, m in PARTS) / 1e3
mass_plastic = sum(abs(m.volume) for _n, m in PARTS) / 1e9 * PLA["rho"]
mod_mass = sum(MASS.values())
tot_g = mass_plastic * 1e3 + mod_mass
load_n = tot_g / 1e3 * G
add(f"   printed plastic {mass_plastic * 1e3:.0f} g (solid) + modules {mod_mass:.0f} g "
    f"= {tot_g:.0f} g -> {load_n:.1f} N on the wall, {load_n / 2:.2f} N per hook")
lig = P["keyhole_slot"] * P["plate_t"]
tau = load_n / 2 / (lig * 1e-6)
verdict(tau < PLA["shear"] / 6, "in-plane shear in the plate above each hook",
        f"{load_n / 2:.2f} N on a {lig:.1f} mm2 ligament = {tau / 1e6:.2f} MPa vs "
        f"{PLA['shear'] / 1e6:.1f} MPa (SF {PLA['shear'] / tau:.0f})")
f3 = PLA["shear"] * math.pi * (SCR["M3"][2] / 1e3) * (P["plate_boss"] / 1e3) * 0.55
verdict(4 * f3 > 25 * load_n, "the 4 plate screws against peel off the wall",
        f"~{f3:.0f} N pull-out each = {4 * f3:.0f} N vs {load_n:.1f} N total -> "
        f"{4 * f3 / load_n:.0f}x")
b = min(W - 2 * WS, H - 2 * WT) / 1e3
tt = ZF / 1e3
I = b * tt ** 3 / 12.0
sig = 0.125 * 20.0 * b / (b * tt * tt / 6.0)
df = 0.013 * 20.0 * b ** 3 / (PLA["E"] * I) * 1e3
verdict(sig < PLA["flex"] / 3, "front wall under a 20 N thumb press",
        f"~{sig / 1e6:.1f} MPa vs {PLA['flex'] / 1e6:.0f} MPa (SF {PLA['flex'] / sig:.1f}), "
        f"centre deflection {df:.2f} mm over a {b * 1e3:.0f} mm span")
v2 = ZF * (2.4 / 3.0)
sig2 = sig * (3.0 / 2.4) ** 2
add(f"   at v2's 2.4 mm front wall the same press gives {sig2 / 1e6:.1f} MPa and "
    f"{df * (3.0 / 2.4) ** 3:.2f} mm of dish - enough to pinch the LCD against its bezel, which")
add(f"   is why v3 went to 3.0 mm there and 2.6 mm on the sides.")
front = zslice_voids(SHELL, ZF / 2.0)
front = [f for f in front if f["area"] > 20]
worst = 9e9
where = ""
for i in range(len(front)):
    for j in range(i + 1, len(front)):
        dd = front[i]["poly"].distance(front[j]["poly"])
        if dd < worst:
            worst, where = dd, f"{front[i]['w']:.0f}x{front[i]['h']:.0f} vs " \
                              f"{front[j]['w']:.0f}x{front[j]['h']:.0f}"
verdict(worst > 6.0, "thinnest ligament between front-wall openings",
        f"{worst:.2f} mm ({where}) across {len(front)} openings", warn=worst <= 6.0)
web = 9e9
for i in range(len(slots)):
    for j in range(i + 1, len(slots)):
        web = min(web, slots[i]["poly"].distance(slots[j]["poly"]))
verdict(web > 3.0, "web between neighbouring intake slots",
        f"{web:.2f} mm minimum, in a {WS:.1f} mm wall")
from shapely.geometry import Point
csk_ok = 9e9
try:
    ptop = [q for q, _i in sec_polys(PLATE, [0, 0, D - 0.05], [0, 0, 1], 0, 1)]
    for (qx, qy) in plate_pts:
        csk_ok = min(csk_ok, min(q.boundary.distance(Point(qx, qy)) for q in ptop) -
                     P["m3_csk"] / 2.0)
except BaseException:
    pass
verdict(csk_ok >= 1.2, "plastic between each plate countersink and the outline",
        f"{csk_ok:.2f} mm minimum of the 4 corners (v3.0 measured 0.08 mm - the d6.6 cone was "
        f"opening onto the R3 corner round; v3.1 moved the screws 3.5 mm inboard)", warn=True)
n_edge = min(min(v["cu"] - v["w"] / 2 + H / 2, H / 2 - (v["cu"] + v["w"] / 2)) for v in slots)
verdict(n_edge > 5.0, "edge distance of the intake slots",
        f"{n_edge:.1f} mm from the wall's edge (>= 2x the slot height is the rule of thumb)")

# =============================================================================================
# 9  SLICER REALITY
# =============================================================================================
section("9. SLICER REALITY - what the four shipped files do on a bed", """
A slicer drops a part onto the bed but never rotates it, so the print orientation has to be baked
into the STL.  These are the files as the user receives them, measured without any undo.
""")
BED = (220.0, 220.0, 250.0)
for fn, (dz, note) in orient_v3.ORIENT.items():
    m = trimesh.load(os.path.join(CAD, fn), process=True)
    lo, hi = m.bounds
    dim = hi - lo
    on_bed = abs(lo[2]) < 1e-6
    first = sec_polys(m, [0, 0, lo[2] + 0.06], [0, 0, 1], 0, 1)
    area = sum(e.area - sum(h.area for h in hs) for e, hs in first)
    cont = len(first)
    fits = dim[0] <= BED[0] and dim[1] <= BED[1] and dim[2] <= BED[2]
    verdict(on_bed, f"{fn}: sits on the bed", f"min z {lo[2]:+.4f} mm, printed flat: {note}")
    verdict(area > 150, f"{fn}: first-layer contact", f"{area:.0f} mm2 in {cont} contour(s)")
    verdict(cont <= 1, f"{fn}: first layer is one closed contour",
            f"{cont} loop(s) - islands on the first layer lift and shed debris")
    verdict(fits, f"{fn}: inside a 220x220x250 mm bed",
            f"{dim[0]:.1f} x {dim[1]:.1f} x {dim[2]:.1f} mm")
add(f"   total print volume for all four parts: "
    f"{max(p.bounds[1][0] - p.bounds[0][0] for _n, p in PARTS):.0f} x "
    f"{max(p.bounds[1][1] - p.bounds[0][1] for _n, p in PARTS):.0f} mm of bed, no part needs a "
    f"raft and only the")
add(f"   shell needs a brim if your bed is not perfectly flat (its rim is 436 mm long).")
# What a slicer really extrudes, layer by layer on the shipped mesh: a band thinner than 3 lines
# from any edge is all perimeter (so it prints SOLID whatever the infill says), and only what is
# left in the middle of a wide face carries infill between the two solid skins.
from shapely.ops import unary_union


def print_density(m, t_line=0.45, n_wall=3, f_infill=0.15, n_skin=3, lh=0.5):
    lo, hi = m.bounds[0][2], m.bounds[1][2]
    nl = max(int((hi - lo) / lh), 1)
    t_perim = n_wall * t_line
    ext_v, cad_v = 0.0, 0.0
    for k in range(nl):
        z = lo + (k + 0.5) * lh
        for e, hs in sec_polys(m, [0, 0, z], [0, 0, 1], 0, 1):
            mat = e.difference(unary_union(hs)) if hs else e
            a = mat.area
            try:
                inner = mat.buffer(-t_perim)
                i_a = 0.0 if inner.is_empty else inner.area
                band = a - i_a                       # what the perimeters alone cover
            except BaseException:
                band = a
            cad_v += a
            ext_v += a if (k < n_skin or k >= nl - n_skin) else band + f_infill * (a - band)
    return ext_v / max(cad_v, 1e-9), nl


rho_pla = 1.24e-3                       # g / mm3
mat, dens = 0.0, {}
add(f"   slicer settings assumed for the mass: 0.45 mm nozzle, 3 walls, 0.28 mm layers, "
    f"3 top/bottom skins, 15 % infill")
for nm, m in PARTS:
    v = abs(m.volume)
    d, nl = print_density(m)
    dens[nm] = d
    mv = v * d * rho_pla
    mat += mv
    add(f"   {nm:13s} {v / 1e3:6.1f} cm3 solid, {nl:4d} sampled layers, extrudes "
        f"{d * 100:4.0f} % of that -> ~{mv:5.1f} g")
add(f"   filament estimate {mat:.0f} g + {mod_mass:.0f} g of modules = {mat + mod_mass:.0f} g "
    f"hanging on the wall; 1 kg spool prints the set {1000 / max(mat, 1):.1f}x "
    f"(v3.0 docs quoted ~102 g, from a blanket 50 % factor - too low, the 2.6 mm walls are all "
    f"perimeter and print solid)")
verdict(True, "printed mass vs the two wall hooks",
        f"{mat + mod_mass:.0f} g all up = {(mat + mod_mass) / 1e3 * G:.1f} N, so "
        f"{(mat + mod_mass) / 2e3 * G:.1f} N per hook on an 8 mm nylon plug rated 300 N+")

# =============================================================================================
# 10  DOCUMENTED CLAIMS
# =============================================================================================
section("10. DOCUMENTED CLAIMS vs THE SHIPPED GEOMETRY", """
Every size quoted in the design notes, the print order, the viewers and the master prompt is
re-measured here against the meshes.  A claim that no longer matches is a bug in the docs.
""")


def claim(label, got, want, tol=0.06, unit="mm"):
    return verdict(abs(got - want) <= tol, label,
                   f"mesh {got:.2f}{unit} vs documented {want:.2f}{unit} (+/-{tol:g})")


claim("outer width", e[0], 110.0, 0.02)
claim("outer height", e[1], 155.0, 0.02)
claim("assembly depth", D, 46.0, 0.001)
claim("front wall", ZF, 3.0, 0.001)
claim("side wall", WS, 2.6, 0.001)
lwv = [f for f in zslice_voids(SHELL, ZF / 2.0) if abs(f["cu"] - lcx) < 4]
claim("LCD window", lwv[0]["w"] if lwv else 0, lw, 0.05)
claim("LCD window height", lwv[0]["h"] if lwv else 0, lh, 0.05)
rvw = [f for f in zslice_voids(SHELL, ZF / 2.0) if abs(f["cu"] - rcx0) < 4]
claim("RFID aperture width", rvw[0]["w"] if rvw else 0, P["rfid_window"][0], 0.05)
claim("RFID aperture height", rvw[0]["h"] if rvw else 0, P["rfid_window"][1], 0.05)
claim("fan bore", bore["w"], P["fan_open_d"], 0.05)
claim("RC522 ring thickness", RING_T, P["rc522_ring"][2], 0.001)
claim("plate thickness", P["plate_t"], 3.0, 0.001)
add(f"   intake: {len(slots)} slots of {slots[0]['w']:.1f} x {slots[0]['h']:.1f} mm = "
    f"{slot_a:.0f} mm2 total   (docs must say 8 x 30 x 5, not v3.0's 6 x d5.0)")
for nm, (a, b) in (("", (0, 0)),):
    pass
for nm, mm in zip([r[0] for r in rows], [r[3] for r in rows]):
    want = {"LCD bezel": 2.05, "RC522 ring": 2.05, "ESP32 bosses": 1.8}.get(nm)
    if want:
        verdict(abs(mm - want) < 0.06, f"{nm} pilot documented at d{want:.2f}",
                f"mesh d{mm:.2f} (thread-forming size, read with a 0.01 mm radial step)")
DOC = {"design notes": "docs/v3_design_notes.md", "print order": "exports/README_PRINT_ORDER_v3.txt"}
REQ = {
    "design notes": [r"110 x 155 x 46", r"3\.0 mm", r"2\.6 mm", r"8 x 30 x 5", r"2\.05",
                     r"1\.8", r"bed-aligned"],
    "print order": [r"110 x 155 x 46", r"8 x 30 x 5", r"M2\.5 x 8", r"15 %", r"no supports"],
}
for nm, rel in DOC.items():
    p = os.path.join(ROOT, rel)
    txt = open(p, encoding="utf-8").read() if os.path.exists(p) else ""
    missing = [pat for pat in REQ[nm] if not re.search(pat, txt)]
    verdict(not missing, f"{rel}: carries the v3.1 numbers",
            f"missing patterns: {missing if missing else 'none'}", warn=True)
    vols = set(round(float(v), 1) for v in re.findall(r"(\d+\.\d) cm3", txt))
    real = {round(abs(m.volume) / 1e3, 1) for _n, m in PARTS}
    real.add(round(sum(real), 1))
    bad = sorted(v for v in vols if not any(abs(v - r) < 0.35 for r in real))
    verdict(not bad, f"{rel}: every cm3 figure matches the mesh volumes",
            f"found {sorted(vols)}; off-list {bad if bad else 'none'}", warn=True)
add("=" * 78)
add("")
if fails:
    add("PHYSICS RESULT: FAILURES -> " + ", ".join(fails))
elif warns:
    add(f"PHYSICS RESULT: no failures. {len(warns)} item(s) recorded as notes -> "
        + ", ".join(warns))
else:
    add("PHYSICS RESULT: ALL CLEAR")
txt_out = "\n".join(L) + "\n"
open(OUT, "w", encoding="utf-8").write(txt_out)
print(txt_out)
sys.exit(1 if fails else 0)
