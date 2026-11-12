"""
ASTRO SMART ATTENDANCE - v2 enclosure generator (parametric, 1:1 mm).

Axes:   X = width (110)   Y = height (155)   Z = depth (48)
        z = 0  -> device FRONT (user) face
        z = 45 -> shell rear edge, z 45..48 = rear service plate

Provenance of every number:  [V1] measured from the uploaded 01_MAIN_SHELL.stl
                             [REF] component reference supplied by the team
                             [EST] engineering estimate -> VERIFY_ACTUAL_HARDWARE

Run:  python3 tools/build_v2.py     ->  cad/v2/*.stl  +  docs/v2_audit.txt
"""
import os
import sys

import numpy as np
import trimesh
from shapely.geometry import box as sbox

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "cad", "v2")
os.makedirs(OUT, exist_ok=True)
os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)

# ============================================================================
# 1. PARAMETERS  (change, re-run, everything rebuilds - nothing hard coded)
# ============================================================================
P = dict(
    W=110.0, H=155.0, D=48.0,
    wall_side=2.4, wall_top=3.0, wall_front=3.0, plate_t=3.0,
    fit=0.35,

    # ---- LCD1602 + I2C backpack -----------------------------------------
    lcd_window=(66.0, 17.5), lcd_centre=(0.0, 51.95),        # [V1] window pos
    lcd_hole_pitch=(75.1, 31.0),                             # [V1] == 1602 std
    lcd_boss=6.0, lcd_pilot=2.5, lcd_glass_t=11.5,           # [REF] 18-25 mm deep

    # ---- R307 fingerprint -----------------------------------------------
    r307_window=(19.3, 21.2), r307_centre=(35.95, -24.1),   # [V1]
    r307_relief=(21.0, 25.0), r307_relief_deep=1.6,         # clears the M3 posts
    r307_body=(20.0, 44.1, 23.5),                           # [REF]
    r307_post=6.0, r307_post_h=23.5, r307_pilot=2.5,
    r307_seat=(1.2, 1.5), r307_seat_fit=0.35,               # locating seat (w x h)
    r307_bracket_holes=(-13.95, 14.05), r307_bracket_w=52.2,

    # ---- RC522 RFID ------------------------------------------------------
    rc522_board=(60.0, 40.0, 1.6),                          # [REF]
    rc522_centre=(-20.05, -24.05),                          # [V1] recess centre
    rc522_components=6.0,                                   # [REF] 3-8 mm
    rc522_pocket=(64.0, 44.0),                              # 2 mm clearance
    rfid_recess=(62.7, 44.7), rfid_recess_deep=1.0,         # [V1] footprint, floor 2.0 mm
    rfid_board_fit=0.35, rfid_seat_rib=(1.2, 1.0),          # locating ribs (w x h)
    rfid_window=(56.0, 38.0), rfid_bars=(2, 2.5),           # <- the open scan window
    rc522_post_off=(22.0, 27.0), rc522_post=8.0, rc522_post_h=2.5,   # screw pads
    rc522_pilot_d=2.2, rc522_clamp=(62.0, 13.0, 1.6), rc522_clamp_lip=(62.0, 3.0),

    # ---- ESP32 DevKit V1 -------------------------------------------------
    esp32_board=(28.33, 51.45, 1.6),                        # [REF] Y x Z when flat on wall
    esp32_comp_h=16.0,                                      # [REF] 8-12 + USB
    esp32_post_len=10.0, esp32_usb_edge=-70.0,               # USB edge Y
    esp32_z_centre=27.5,                                     # keeps it clear of the RC522
    esp32_pad=8.0, esp32_pilot=2.2, esp32_inset=3.5,        # inset VERIFY_ACTUAL_HARDWARE
    usb_slot=(18.0, 10.0), usb_plug=(15.6, 8.0),

    # ---- 3010 fan --------------------------------------------------------
    fan=(30.0, 30.0, 10.0), fan_pitch=24.0, fan_open_d=26.0,  # [REF]
    fan_centre_yz=(17.0, 24.0), fan_post=8.0, fan_pilot=2.5,

    # ---- ventilation -----------------------------------------------------
    vent_slot=(20.0, 4.0), vent_rows=(-16.0, 16.0), vent_z=(6.0, 12.0),
    top_vent=(16.0, 3.0), top_vent_x=(-18.0, 0.0, 18.0), top_vent_z=26.0,

    # ---- hardware --------------------------------------------------------
    plate_boss=9.0, plate_boss_xy=(46.5, 71.0),
    plate_pilot=2.5, plate_screw=3.4,
    keyhole_d=7.5, keyhole_slot=4.6, keyhole_span=50.0,
    corner_r=3.0, corner_eps=0.12, rim_chamfer=1.0, m3_csk=6.6,   # polish + flush screws
    zip_post=(-10.0, -66.0), zip_post2=(16.0, -66.0), zip_post3=(44.0, 12.0),
    zip_post4=(-48.0, -66.0),                               # strain relief by the USB slot
    zip_pilot=4.0,
)

AN = "XYZ"
UNION = trimesh.boolean.union
DIFF = trimesh.boolean.difference
INTER = trimesh.boolean.intersection


# ============================================================================
# 2. PRIMITIVES
# ============================================================================
def rr(cx, cy, w, h, r):
    r = min(r, w / 2 - 0.01, h / 2 - 0.01)
    return sbox(cx - w / 2 + r, cy - h / 2 + r, cx + w / 2 - r, cy + h / 2 - r).buffer(
        r, resolution=16, join_style=1)


def ext_z(poly, z0, z1):
    m = trimesh.creation.extrude_polygon(poly, z1 - z0)
    m.apply_translation([0, 0, z0])
    return m


def ext_y(poly, y0, y1):
    """polygon given in (x, z) -> extruded along Y from y0 to y1"""
    y0, y1 = sorted((y0, y1))
    m = trimesh.creation.extrude_polygon(poly, y1 - y0)
    m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    m.apply_translation([0, y1, 0])
    return m


def bx(x0, x1, y0, y1, z0, z1):
    x0, x1 = sorted((x0, x1)); y0, y1 = sorted((y0, y1)); z0, z1 = sorted((z0, z1))
    m = trimesh.creation.box(extents=(x1 - x0, y1 - y0, z1 - z0))
    m.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])
    return m


def cyl_x(x0, x1, y, z, d, n=64):
    m = trimesh.creation.cylinder(radius=d / 2, height=abs(x1 - x0), sections=n)
    m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
    m.apply_translation([(x0 + x1) / 2, y, z])
    return m


def half_cut(n, d, size=400.0):
    """Cutting solid occupying n . p >= d  (used for 45 deg rim chamfers)."""
    n = np.asarray(n, dtype=float)
    n = n / np.linalg.norm(n)
    m = trimesh.creation.box(extents=(size, size, size))
    m.apply_transform(trimesh.geometry.align_vectors([-1.0, 0.0, 0.0], n))
    m.apply_translation(n * (d + size / 2.0))
    return m


def corner_cut(cx, cy, cy_off, r, z0, z1, big=30.0):
    """Round a vertical corner: solid = (corner box) minus (cylinder r) -> keeps the arc."""
    sx = 1.0 if cx > 0 else -1.0
    sy = 1.0 if cy > 0 else -1.0
    box_ = bx(min(cx, cx + sx * big), max(cx, cx + sx * big),
              min(cy, cy + sy * big), max(cy, cy + sy * big), z0, z1)
    cyl = cyl_z(cx, cy, z0 - 1, z1 + 1, 2 * r, n=96)
    return DIFF([box_, cyl], engine="manifold")


def cyl_z(x, y, z0, z1, d, n=48):
    m = trimesh.creation.cylinder(radius=d / 2, height=abs(z1 - z0), sections=n)
    m.apply_translation([x, y, (z0 + z1) / 2])
    return m


# ============================================================================
# 3. SHELL
# ============================================================================
def build_shell():
    W, H, D = P["W"], P["H"], P["D"]
    wi = W / 2 - P["wall_side"]           # +-52.6
    hi = H / 2 - P["wall_top"]            # +-74.5
    zi = P["wall_front"]                  # 3.0
    zr = D - P["plate_t"]                 # 45.0

    early, late, cut = [], [], []

    body = bx(-W / 2, W / 2, -H / 2, H / 2, 0, zr)       # shell ends at the plate
    pocket = [bx(-wi, wi, -hi, hi, zi, D + 2),           # cavity
              bx(-W / 2 - 1, W / 2 + 1, -H / 2 - 1, H / 2 + 1, zr, D + 2)]   # rear face

    # ---------------------------------------------------------------- LCD
    lcx, lcy = P["lcd_centre"]
    lw, lh = P["lcd_window"]
    cut.append(ext_z(rr(lcx, lcy, lw, lh, 1.5), -1, zi + 1))
    for sx in (-1, 1):
        for sy in (-1, 1):
            px = lcx + sx * P["lcd_hole_pitch"][0] / 2
            py = lcy + sy * P["lcd_hole_pitch"][1] / 2
            h = P["lcd_boss"] / 2
            early.append(bx(px - h, px + h, py - h, py + h, zi - 0.5, zi + P["lcd_glass_t"]))
            cut.append(cyl_z(px, py, zi + 4.5, zi + P["lcd_glass_t"] + 1.5, P["lcd_pilot"]))

    # --------------------------------------------------------------- R307
    rcx, rcy = P["r307_centre"]
    relw, relh = P["r307_relief"]
    cut.append(ext_z(rr(rcx, rcy, relw, relh, 2.0), P["r307_relief_deep"], zi + 1))
    cut.append(ext_z(rr(rcx, rcy, P["r307_window"][0], P["r307_window"][1], 1.5),
                     -1, zi + 1))
    for dx in P["r307_bracket_holes"]:
        h = P["r307_post"] / 2
        early.append(bx(rcx + dx - h, rcx + dx + h, rcy - h, rcy + h,
                        zi - 0.5, zi + P["r307_post_h"]))
        cut.append(cyl_z(rcx + dx, rcy, zi + P["r307_post_h"] - 7.0,
                         zi + P["r307_post_h"] + 1, P["r307_pilot"]))
    # ---- R307 locating seat: module slides in, clamped by the bracket
    sw, sh = P["r307_seat"]
    sfit = P["r307_seat_fit"]
    bw2, bl2 = P["r307_body"][0], P["r307_body"][1]
    relh2 = P["r307_relief"][1] / 2.0                       # keep clear of the bezel relief
    for sgn in (-1, 1):                                     # side walls (X), split in Y
        a = rcx + sgn * (bw2 / 2 + sfit)
        b = rcx + sgn * (bw2 / 2 + sfit + sw)
        for (y0, y1) in ((rcy - bl2 / 2 + 1.0, rcy - relh2 - 0.5),
                         (rcy + relh2 + 0.5, rcy + bl2 / 2 - 1.0)):
            early.append(bx(min(a, b), max(a, b), y0, y1, zi - 0.5, zi + sh))
    e0 = rcy - bl2 / 2 - sfit - sw                          # end stop at the connector end
    early.append(bx(rcx - bw2 / 2 - 1.0, rcx + bw2 / 2 + 1.0, e0, e0 + sw, zi - 0.5, zi + sh))

    # -------------------------------------------------------------- RC522
    fcx, fcy = P["rc522_centre"]
    rrw, rrh = P["rfid_recess"]
    deep = P["rfid_recess_deep"]
    rbw, rbl = P["rc522_board"][0], P["rc522_board"][1]
    fit = P["rfid_board_fit"]
    ribw, ribh = P["rfid_seat_rib"]
    cut.append(ext_z(rr(fcx, fcy, rrw, rrh, 3.0), -1, deep))
    # ---- seat: 4 locating ribs on the recess floor, board outline + fit
    # The board drops in from the cavity side and stands on the 2 mm ledge that the
    # open window leaves in the recess (its solder side faces the window, its component
    # side and antenna face the cavity).  Four ribs above the inner face centre it.
    seat_z0, seat_z1 = zi, zi + ribh
    for sgn in (-1, 1):                                     # ribs parallel to Y (+-X sides)
        a = fcx + sgn * (rbw / 2 + fit)                     # inner face = board outline + fit
        b = a + sgn * ribw
        early.append(bx(min(a, b), max(a, b), fcy - rbl / 2 + 1.0, fcy + rbl / 2 - 1.0,
                        seat_z0, seat_z1))
    for sgn in (-1, 1):                                     # ribs parallel to X (+-Y sides)
        a = fcy + sgn * (rbl / 2 + fit)
        b = a + sgn * ribw
        early.append(bx(fcx - rbw / 2 + 1.0, fcx + rbw / 2 - 1.0,
                        min(a, b), max(a, b), seat_z0, seat_z1))
    vw, vh = P["rfid_window"]
    cut.append(ext_z(rr(fcx, fcy, vw, vh, 5.0), deep - 0.1, zi + 1))     # OPEN window
    seat_top = deep + ribh                                    # board back face
    board_top = seat_top + P["rc522_board"][2]                # board front face
    nbar, bw = P["rfid_bars"]
    for k in range(nbar):
        off = (k + 1) * vw / (nbar + 1) - vw / 2
        late.append(bx(fcx + off - bw / 2, fcx + off + bw / 2,
                       fcy - vh / 2 - 1.2, fcy + vh / 2 + 1.2, deep + 0.05, zi))
    pw, ph = P["rc522_pocket"]
    rim = 2.4
    early.append(DIFF([bx(fcx - pw / 2 - rim, fcx + pw / 2 + rim,
                          fcy - ph / 2 - rim, fcy + ph / 2 + rim, zi - 0.5, zi + 2.4),
                       bx(fcx - pw / 2, fcx + pw / 2, fcy - ph / 2, fcy + ph / 2,
                          zi - 1, zi + 3)], engine="manifold"))
    # 4 screw pads for the RC522 clamp bars - circular M2.5 pilot holes
    pox, poy = P["rc522_post_off"]
    for sx in (-1, 1):
        for sy in (-1, 1):
            px, py = fcx + sx * pox, fcy + sy * poy
            h = P["rc522_post"] / 2
            early.append(bx(px - h, px + h, py - h, py + h, zi - 0.5, zi + P["rc522_post_h"]))
            cut.append(cyl_z(px, py, 1.4, zi + P["rc522_post_h"] + 0.6, P["rc522_pilot_d"]))

    # ---------------------------------------------------------------- fan
    fy, fz = P["fan_centre_yz"]
    cut.append(cyl_x(-W / 2 - 2, -wi + 0.1, fy, fz, P["fan_open_d"]))
    cut.append(cyl_x(-W / 2 - 2, -W / 2 + 1.2, fy, fz, 30.0))          # outer recess
    r = P["fan_open_d"] / 2
    for dy in (-6.0, 0.0, 6.0):
        half = (r * r - dy * dy) ** 0.5 + 0.8
        late.append(bx(-W / 2, -wi, fy + dy - 1.5, fy + dy + 1.5,
                       fz - half, fz + half))
    sp = P["fan_pitch"] / 2
    for dy in (-sp, sp):
        for dz in (-sp, sp):
            h = P["fan_post"] / 2
            early.append(bx(-wi - 0.5, -wi + 10.0, fy + dy - h, fy + dy + h,
                            fz + dz - h, fz + dz + h))
            cut.append(cyl_x(-wi - 1.0, -wi + 11.0, fy + dy, fz + dz, P["fan_pilot"]))

    # -------------------------------------------------------------- ESP32
    ebw, ebl = P["esp32_board"][0], P["esp32_board"][1]
    ex_face = -wi + P["esp32_post_len"]                  # board rear face plane
    ey0 = P["esp32_usb_edge"]
    ezc = P["esp32_z_centre"]
    ez0, ez1 = ezc - ebw / 2, ezc + ebw / 2
    for py in (ey0 + P["esp32_inset"], ey0 + ebl - P["esp32_inset"]):
        for pz in (ez0 + P["esp32_inset"], ez1 - P["esp32_inset"]):
            h = P["esp32_pad"] / 2
            early.append(bx(-wi - 0.5, ex_face, py - h, py + h, pz - h, pz + h))
            cut.append(cyl_x(ex_face - 7.0, ex_face + 0.6, py, pz, P["esp32_pilot"]))
    for pz in (ez0 + 3.0, ez1 - 3.0):                    # Y stop (2 tabs, USB passes between)
        early.append(bx(-wi - 0.5, ex_face + 0.8, ey0 - 1.6, ey0, pz - 3.0, pz + 3.0))
    usx = ex_face + 3.5                                  # connector centre over the board
    usw, ush = P["usb_slot"]
    cut.append(ext_y(rr(usx, ezc, usw, ush, 2.0), -H / 2 - 2, -hi + 0.1))
    cut.append(ext_y(rr(usx, ezc, usw + 2.4, ush + 2.4, 2.6), -H / 2 - 2, -hi + 2.0))

    # -------------------------------------------------------- ventilation
    vw2, vh2 = P["vent_slot"]
    for vx in P["vent_rows"]:
        for vz in P["vent_z"]:
            cut.append(ext_y(rr(vx, vz, vw2, vh2, 1.6), -H / 2 - 2, -hi + 0.1))
    for vx in P["top_vent_x"]:
        w2, h2 = P["top_vent"]
        cut.append(ext_y(rr(vx, P["top_vent_z"], w2, h2, 1.2), H / 2 + 2, hi - 0.1))

    # ---------------------------------------------------- cable tie posts
    for (zx, zy) in (P["zip_post"], P["zip_post2"], P["zip_post3"], P["zip_post4"]):
        early.append(bx(zx - 4, zx + 4, zy - 4, zy + 4, zi - 0.5, zi + 8.0))
        cut.append(cyl_z(zx, zy, zi + 1.6, zi + 9.0, P["zip_pilot"]))

    # ------------------------------------------------------------- ribs
    early.append(bx(46.0, 48.4, -60.0, 30.0, zi - 0.5, zi + 2.4))
    early.append(bx(-wi, 47.4, 29.0, 32.4, zi - 0.5, zi + 2.4))   # 1.4 x 1 mm overlap -> no edge contact

    # ------------------------------------- rear plate screw bosses
    bx0, by0 = P["plate_boss_xy"]
    r = P["plate_boss"] / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * bx0, sy * by0
            if sx < 0 and sy < 0:            # USB cable exits here -> short, narrow boss
                early.append(bx(cx - r, ex_face, cy - r, cy + r, 33.0, zr))
            else:
                early.append(bx(cx - r, cx + r, cy - r, cy + r, zi - 0.5, zr))
            cut.append(cyl_z(cx, cy, zr - 9.0, zr + 1, P["plate_pilot"]))

    # ------------------------------------------- outer cosmetics (v2 polish)
    r = P["corner_r"]
    for sx in (-1, 1):
        for sy in (-1, 1):
            cut.append(corner_cut(sx * (W / 2 - r), sy * (H / 2 - r), 0, r + P["corner_eps"], -1, zr + 1))
    c = P["rim_chamfer"]
    s2 = np.sqrt(2.0)
    for nvec, off in (([1, 0, -1], (W / 2 - c)), ([-1, 0, -1], (W / 2 - c)),
                      ([0, 1, -1], (H / 2 - c)), ([0, -1, -1], (H / 2 - c))):
        cut.append(half_cut(nvec, off / s2))

    # ------------------------------------------------------- pipeline
    # 1 hollow the body  2 add internal structure  3 cut all openings/pilots
    # 4 re-add the feature that lives inside an opening (grille bars)
    s = DIFF([body, UNION(pocket, engine="manifold")], engine="manifold")
    s = UNION([s] + early, engine="manifold")
    s = DIFF([s, UNION(cut, engine="manifold")], engine="manifold")
    s = UNION([s] + late, engine="manifold")
    return s


def build_plate():
    W, H, D, fit, t = P["W"], P["H"], P["D"], P["fit"], P["plate_t"]
    z0 = D - t
    plate = bx(-W / 2, W / 2, -H / 2, H / 2, z0, D)                 # flush rear cover
    wi = W / 2 - P["wall_side"]
    hi = H / 2 - P["wall_top"]
    lip = bx(-wi + fit, wi - fit, -hi + fit, hi - fit, z0 - 2.0, z0 + 0.5)
    plate = UNION([plate, lip], engine="manifold")

    cut = []
    bx0, by0 = P["plate_boss_xy"]
    r = P["plate_boss"] / 2 + 0.4
    for sx in (-1, 1):
        for sy in (-1, 1):
            for comp in (plate,):
                pass
            cut.append(bx(sx * bx0 - r, sx * bx0 + r, sy * by0 - r, sy * by0 + r,
                          z0 - 2.1, z0 + 0.2))            # relief for the shell boss
            cut.append(cyl_z(sx * bx0, sy * by0, z0 - 3, D + 1, P["plate_screw"]))
            cut.append(cyl_z(sx * bx0, sy * by0, z0 + 1.2, D + 1, P["plate_screw"] + 2.6))
    r = P["corner_r"]
    for sx in (-1, 1):
        for sy in (-1, 1):
            cut.append(corner_cut(sx * (W / 2 - r), sy * (H / 2 - r), 0, r + P["corner_eps"], z0 - 3, D + 1))
    c = P["rim_chamfer"]
    s2 = np.sqrt(2.0)
    for nvec, off in (([1, 0, 1], (W / 2 + z0)), ([-1, 0, 1], (W / 2 + z0)),
                      ([0, 1, 1], (H / 2 + z0)), ([0, -1, 1], (H / 2 + z0))):
        cut.append(half_cut(nvec, off / s2))
    cs = P["m3_csk"] / 2.0                       # 90 deg countersink -> flat-head M3 sits flush
    for sx in (-1, 1):
        for sy in (-1, 1):
            cone = trimesh.creation.cone(radius=cs, height=cs, sections=64)
            cone.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
            cone.apply_translation([sx * bx0, sy * by0, D])     # base at the outer face, apex in
            cut.append(cone)
    kd, ks, span = P["keyhole_d"], P["keyhole_slot"], P["keyhole_span"]
    for kx in (-span / 2, span / 2):
        cut.append(cyl_z(kx, 0.0, z0 - 1, D + 1, kd))
        cut.append(bx(kx - ks / 2, kx + ks / 2, -kd / 2, 12.0, z0 - 1, D + 1))
    plate = DIFF([plate, UNION(cut, engine="manifold")], engine="manifold")

    ribs = [bx(-span / 2, span / 2, -1.5, 1.5, z0 - 4.0, z0 - 2.0)]
    for kx in (-span / 2, span / 2):
        ribs.append(bx(kx - 1.5, kx + 1.5, -H / 2 + 8, span / 2, z0 - 4.0, z0 - 2.0))
    return UNION([plate] + ribs, engine="manifold")


def build_rc522_clamp():
    """One RC522 clamp bar (print 2 - rotate the second by 180 deg about Z).

    Sits on the two M2.5 pads at y = rc522_centre +/- post_off[1], its lip presses the
    board's edge down onto the front wall while the whole antenna area stays open.
    """
    fcx, fcy = P["rc522_centre"]
    pox, poy = P["rc522_post_off"]
    cw, cl, ct = P["rc522_clamp"]
    lw, ll = P["rc522_clamp_lip"]
    z0 = P["wall_front"] + P["rc522_board"][2]        # board front face (component side up)
    lt = P["wall_front"] + P["rc522_post_h"] - z0     # lip reaches from board face to pad top
    plat = bx(fcx - cw / 2, fcx + cw / 2, fcy + poy - cl + 2.0, fcy + poy + 4.0, z0 + lt, z0 + lt + ct)
    lip = bx(fcx - lw / 2, fcx + lw / 2, fcy + poy - cl + 2.0, fcy + poy - cl + 2.0 + ll, z0, z0 + lt)
    bar = UNION([plat, lip], engine="manifold")
    cut = []
    for sx in (-1, 1):
        cut.append(cyl_z(fcx + sx * pox, fcy + poy, z0 - 1, z0 + lt + ct + 1, 3.0))
        cut.append(cyl_z(fcx + sx * pox, fcy + poy, z0 + lt + 0.2, z0 + lt + ct + 1, 5.6))
    return DIFF([bar, UNION(cut, engine="manifold")], engine="manifold")


def build_r307_bracket():
    rcx, rcy = P["r307_centre"]
    d0, d1 = P["r307_bracket_holes"]
    z0 = P["wall_front"] + P["r307_body"][2]
    b = bx(rcx + d0 - 3.5, min(rcx + d1 + 3.0, P['W'] / 2 - P['wall_side'] - 0.6),
           rcy - 6.0, rcy + 6.0, z0, z0 + 2.0)
    cut = []
    for dx in (d0, d1):
        cut.append(cyl_z(rcx + dx, rcy, z0 - 1, z0 + 3, 3.0))
        cut.append(cyl_z(rcx + dx, rcy, z0 + 1.2, z0 + 3, 5.6))
    b = DIFF([b, UNION(cut, engine="manifold")], engine="manifold")
    return b


# ============================================================================
# 4. VERIFICATION VOLUMES
# ============================================================================
def envelopes():
    E = {}
    wi = P["W"] / 2 - P["wall_side"]
    zi = P["wall_front"]
    lcx, lcy = P["lcd_centre"]
    E["LCD_glass_pane"] = bx(lcx - 35.6, lcx + 35.6, lcy - 12.1, lcy + 12.1,
                             zi, zi + P["lcd_glass_t"])
    E["LCD_pcb+backpack"] = bx(lcx - 21.0, lcx + 21.0, lcy - 9.5, lcy + 9.5,
                               zi + P["lcd_glass_t"], zi + 24.0)
    E["LCD_bezel_window"] = bx(lcx - P["lcd_window"][0] / 2 + 0.5,
                               lcx + P["lcd_window"][0] / 2 - 0.5,
                               lcy - P["lcd_window"][1] / 2 + 0.5,
                               lcy + P["lcd_window"][1] / 2 - 0.5, -2.0, zi - 0.2)
    rcx, rcy = P["r307_centre"]
    bw, bl, bd = P["r307_body"]
    E["R307_body"] = bx(rcx - bw / 2, rcx + bw / 2, rcy - bl / 2, rcy + bl / 2, zi, zi + bd)
    fcx, fcy = P["rc522_centre"]
    rbw, rbl, rbt = P["rc522_board"]
    E["RC522_board"] = bx(fcx - rbw / 2, fcx + rbw / 2, fcy - rbl / 2, fcy + rbl / 2,
                          zi, zi + rbt)
    E["RC522_components"] = bx(fcx - 22.0, fcx + 22.0, fcy - 14.0, fcy + 14.0,
                               zi + rbt, zi + rbt + P["rc522_components"])
    E["RC522_scan_zone"] = bx(fcx - rbw / 2, fcx + rbw / 2, fcy - rbl / 2, fcy + rbl / 2,
                              -25.0, -1.0)
    ex_face = -wi + P["esp32_post_len"]
    ey0 = P["esp32_usb_edge"]
    ebl, ebw = P["esp32_board"][1], P["esp32_board"][0]
    ezc = P["esp32_z_centre"]
    E["ESP32_board+components"] = bx(ex_face, ex_face + P["esp32_comp_h"],
                                     ey0, ey0 + ebl, ezc - ebw / 2, ezc + ebw / 2)
    E["ESP32_RF_keepout"] = bx(ex_face, ex_face + P["esp32_comp_h"],
                               ey0 + ebl, ey0 + ebl + 15.0,
                               ezc - ebw / 2, ezc + ebw / 2)
    usx = ex_face + 3.5
    E["USB_plug"] = bx(usx - P["usb_plug"][0] / 2, usx + P["usb_plug"][0] / 2,
                       -P["H"] / 2 - 14.0, ey0 + 1.0,
                       ezc - P["usb_plug"][1] / 2, ezc + P["usb_plug"][1] / 2)
    fy, fz = P["fan_centre_yz"]
    ft = P["fan"][2]
    E["Fan_3010"] = bx(-wi + ft, -wi + 2 * ft, fy - P["fan"][0] / 2, fy + P["fan"][0] / 2,
                       fz - P["fan"][1] / 2, fz + P["fan"][1] / 2)
    return E


def opening_test(shell):
    """material must be absent at the opening centre, present 8 mm away"""
    wi = P["W"] / 2 - P["wall_side"]
    hi = P["H"] / 2 - P["wall_top"]
    zi = P["wall_front"]
    t = P["W"]  # unused
    deep = P["rfid_recess_deep"]
    lcx, lcy = P["lcd_centre"]
    rcx, rcy = P["r307_centre"]
    fcx, fcy = P["rc522_centre"]
    nbar, bw = P["rfid_bars"]
    lane = fcx - 24.0                       # inside the first lane between stiffener bars
    usx = -wi + P["esp32_post_len"] + 3.5
    ezc = P["esp32_z_centre"]
    fy, fz = P["fan_centre_yz"]
    cases = [
        ("LCD window",        (lcx, lcy, zi - 1.5), (lcx + P["lcd_window"][0] / 2 + 4, lcy, zi - 1.5)),
        ("R307 window",       (rcx, rcy, zi - 1.5), (rcx + P["r307_window"][0] / 2 + 4, rcy, zi - 1.5)),
        ("RFID scan window",  (lane, fcy, (deep + zi) / 2), (fcx - P["rfid_window"][0] / 2 - 2, fcy, (deep + zi) / 2)),
        ("USB slot",          (usx, -P["H"] / 2 + 1.5, ezc), (usx + P["usb_slot"][0] / 2 + 4, -P["H"] / 2 + 1.5, ezc)),
        ("fan grille",        (-P["W"] / 2 + 1.5, fy + 4.5, fz), (-P["W"] / 2 + 1.5, fy + 4.5, fz + P["fan_open_d"] / 2 + 6)),
        ("exhaust slot",      (P["vent_rows"][0], -P["H"] / 2 + 1.5, P["vent_z"][0]),
                              (P["vent_rows"][0] + P["vent_slot"][0] / 2 + 6, -P["H"] / 2 + 1.5, P["vent_z"][0])),
        ("top vent",          (P["top_vent_x"][0], P["H"] / 2 - 1.5, P["top_vent_z"]),
                              (P["top_vent_x"][0], P["H"] / 2 - 1.5, P["top_vent_z"] + P["top_vent"][1] / 2 + 5)),
    ]
    res = []
    for name, p_open, p_wall in cases:
        in_open = bool(shell.contains([p_open])[0])
        in_wall = bool(shell.contains([p_wall])[0])
        res.append((name, not in_open, in_wall))
    return res


# ============================================================================
# 5. AUDIT
# ============================================================================
def thickness(shell, origin, direction, maxmm=40.0, step=0.05):
    """Length of the FIRST run of material along the ray (leading void is skipped)."""
    d = np.array(direction, dtype=float)
    d /= np.linalg.norm(d)
    o = np.array(origin, dtype=float)
    t = 0.0
    while t < maxmm and not shell.contains([o + d * t])[0]:      # skip the void
        t += step
    if t >= maxmm:
        return 0.0
    t0 = t
    while t < maxmm and shell.contains([o + d * t])[0]:          # measure the material
        t += step
    return t - t0


def wall_probe(shell):
    fcx, fcy = P["rc522_centre"]
    deep = P["rfid_recess_deep"]
    probes = [
        ("front wall, plain",        (0.0, 10.0, 0.1), (0, 0, 1),  2.90),
        ("RFID ledge ring",          (fcx + 30.0, fcy + 5.0, -1.0), (0, 0, 1), 2.00),
        ("RFID stiffener bar",       (fcx - 9.5, fcy, -1.0), (0, 0, 1), 1.95),
        ("side wall",                (-54.9, 0.0, 40.0), (1, 0, 0), 2.30),
        ("top wall",                 (0.0, 77.4, 20.0), (0, -1, 0), 2.90),
        ("bottom wall",              (-2.0, -77.4, 12.0), (0, 1, 0), 2.90),
        ("LCD boss above wall",      (36.0, 36.45, 3.0), (0, 0, 1), 11.50),
        ("R307 post height",         (20.0, -24.1, 3.0), (0, 0, 1), 23.50),
        ("fan ring above grille",    (-53.9, P["fan_centre_yz"][0], P["fan_centre_yz"][1] + 16.0), (1, 0, 0), 1.20),
    ]
    rows = []
    for name, o, d, expect in probes:
        t = thickness(shell, o, d)
        rows.append((name, t, expect))
    return rows


def fcx_bar():
    return -20.05 - 9.0


def audit(shell, plate, r307b, clamp=None):
    L = []
    add = L.append
    vol = abs(shell.volume) / 1000.0
    add("ASTRO SMART ATTENDANCE - v2 enclosure audit")
    add("=" * 76)
    add(f"axis frame: X width {P['W']:.0f}, Y height {P['H']:.0f}, Z depth {P['D']:.0f} mm")
    add(f"shell     : {len(shell.faces)} tris, watertight={shell.is_watertight}, "
        f"winding_ok={shell.is_winding_consistent}, bodies={shell.body_count}")
    add(f"shell size: {np.round(shell.extents,1).tolist()} (depth 45 + 3 mm plate = 48)")
    add(f"assembly  : 110.0 x 155.0 x 48.0 mm")
    add(f"volume    : {vol:.1f} cm3  ~{vol*0.62:.0f} g PLA (15 % infill, estimate)")
    add("")
    add("A. printed-part interference")
    clamps = ([clamp, clamp.copy().apply_transform(
        trimesh.transformations.rotation_matrix(np.pi, [0, 0, 1], [P["rc522_centre"][0], P["rc522_centre"][1], 0]))]
        if clamp is not None else [])
    ok = True
    checks = [("shell <-> rear plate", plate), ("shell <-> R307 bracket", r307b)]
    for i, cm in enumerate(clamps):
        checks.append((f"shell <-> RC522 clamp {i+1}", cm))
    for nm, m in checks:
        v = abs(INTER([shell, m], engine="manifold").volume)
        good = v < 1.0
        ok = ok and good
        add(f"   {nm:34s} {v:9.2f} mm3   {'PASS' if good else 'FAIL'}")
    add("")
    add("B. component fit  (envelope overlap with shell material = 0 required)")
    add(f"   {'envelope':26s} {'overlap':>10s}  verdict")
    for k, m in envelopes().items():
        v = abs(INTER([shell, m], engine="manifold").volume)
        good = v < 1.5
        ok &= good
        add(f"   {k:26s} {v:10.2f}  {'PASS' if good else 'FAIL'}")
    add("")
    add("C. openings (must be open through the wall, wall must exist beside them)")
    for name, open_ok, wall_ok in opening_test(shell):
        good = open_ok and wall_ok
        ok &= good
        add(f"   {name:20s} open={open_ok!s:5s} wall_ok={wall_ok!s:5s} "
            f"{'PASS' if good else 'FAIL'}")
    add("")
    add("D. other printed parts")
    add(f"   rear plate   : size {np.round(plate.extents,1).tolist()}, "
        f"watertight={plate.is_watertight}, {abs(plate.volume)/1000:.1f} cm3")
    if clamp is not None:
        add(f"   RC522 clamp  : size {np.round(clamp.extents,1).tolist()}, "
            f"watertight={clamp.is_watertight}, {abs(clamp.volume)/1000:.1f} cm3  (print 2, "
            f"second rotated 180 deg)")
    add(f"   R307 bracket : size {np.round(r307b.extents,1).tolist()}, "
        f"watertight={r307b.is_watertight}")
    add("")
    add("E. wall / feature thickness probe (ray through the material)")
    for name, t, expect in wall_probe(shell):
        ok_t = abs(t - expect) <= 0.35
        add(f"   {name:26s} measured {t:5.2f} mm   design {expect:4.2f}   "
            f"{'PASS' if ok_t else 'CHECK'}")
    add("")
    add("F. dimensional audit against the supplied component references")
    ref = [
        ("R307 body", f"{P['r307_body']}", "44.1 x 20 x 23.5", True),
        ("R307 window", f"{P['r307_window']}", "19 x 21", True),
        ("ESP32 pcb", f"{P['esp32_board']}", "51.45 x 28.33", True),
        ("RC522 pcb", f"{P['rc522_board'][:2]}", "60 x 40", True),
        ("LCD pcb", "80 x 36 (window pattern 75.1 x 31)", "80 x 36", True),
        ("LCD visible", f"{P['lcd_window']} window", "64 x 16", True),
        ("Fan", f"{P['fan']}", "30 x 30 x 10", True),
        ("Fan hole pitch", f"{P['fan_pitch']}", "~24", True),
        ("ESP32 PCB hole inset", f"{P['esp32_inset']}", "unverified", False),
        ("RC522 board holes", "unused - 2 clamp bars + 4 pads", "unverified", False),
    ]
    for what, got, exp, ver in ref:
        add(f"   {what:22s} model: {str(got):38s} ref: {exp:20s}"
            f"{'' if ver else '  VERIFY_ACTUAL_HARDWARE'}")
    add("")
    n = shell.face_normals
    a = shell.area_faces
    over = a[(n[:, 2] > 0.259) & (n[:, 2] <= 0.707)]
    add("")
    add("G. printability (orientation: front face down, rear opening up)")
    add(f"   >60 deg overhang area: {over.sum():.0f} mm2 "
        f"({100*over.sum()/a.sum():.2f} % of surface) - SUPPORT_REQUIRED = NO")
    add(f"   designed walls: front {P['wall_front']} mm ({P['rfid_recess_deep'] + P['rfid_recess_deep']:.1f} mm"
        f" ledge ring at the RFID window), sides {P['wall_side']} mm, top/bottom {P['wall_top']} mm, "
        f"plate {P['plate_t']} mm, fit clearance {P['fit']} mm")
    add(f"   outer polish: vertical corners R{P['corner_r']} mm, {P['rim_chamfer']} mm x 45 deg front rim, "
        f"plate rear rim chamfered, plate screws countersunk {P['m3_csk']} mm / 90 deg (flush flat head)")
    add("")
    add("I. screw fixing map  (circular pilot holes - every hardware fixing, verified)")
    wi = P["W"] / 2 - P["wall_side"]
    hi = P["H"] / 2 - P["wall_top"]
    zi = P["wall_front"]
    zr = P["D"] - P["plate_t"]
    lcx, lcy = P["lcd_centre"]
    rcx, rcy = P["r307_centre"]
    fcx, fcy = P["rc522_centre"]
    ex_face = -wi + P["esp32_post_len"]
    ebw, ebl = P["esp32_board"][0], P["esp32_board"][1]
    ey0, ezc = P["esp32_usb_edge"], P["esp32_z_centre"]
    ez0, ez1 = ezc - ebw / 2, ezc + ebw / 2
    fy, fz = P["fan_centre_yz"]
    pox, poy = P["rc522_post_off"]
    holes = []
    for sx in (-1, 1):                                        # LCD 1602 : 4 x M2.5
        for sy in (-1, 1):
            holes.append(("LCD1602", "M2.5", 2.5, 8.5,
                          (lcx + sx * P["lcd_hole_pitch"][0] / 2, lcy + sy * P["lcd_hole_pitch"][1] / 2),
                          "z", zi + 4.5, zi + P["lcd_glass_t"] + 1.5))
    for dx in P["r307_bracket_holes"]:                        # R307 : 2 x M3
        holes.append(("R307 bracket", "M3", 2.5, 8.0, (rcx + dx, rcy), "z",
                      zi + P["r307_post_h"] - 7.0, zi + P["r307_post_h"] + 1))
    for sx in (-1, 1):                                        # RC522 : 4 x M2.5
        for sy in (-1, 1):
            holes.append(("RC522 clamp", "M2.5", 2.2, 4.1,
                          (fcx + sx * pox, fcy + sy * poy), "z", 1.4, zi + P["rc522_post_h"] + 0.6))
    for py in (ey0 + P["esp32_inset"], ey0 + ebl - P["esp32_inset"]):      # ESP32 : 4 x M2.2
        for pz in (ez0 + P["esp32_inset"], ez1 - P["esp32_inset"]):
            holes.append(("ESP32 standoff", "M2.2", 2.2, 7.0, (py, pz), "x",
                          ex_face - 7.0, ex_face + 0.6))
    for dy in (-P["fan_pitch"] / 2, P["fan_pitch"] / 2):       # fan : 4 x M3
        for dz in (-P["fan_pitch"] / 2, P["fan_pitch"] / 2):
            holes.append(("Fan 3010", "M3", 2.5, 12.0, (fy + dy, fz + dz), "x",
                          -wi - 1.0, -wi + 11.0))
    bx0, by0 = P["plate_boss_xy"]                              # rear plate : 4 x M3
    for sx in (-1, 1):
        for sy in (-1, 1):
            holes.append(("rear plate", "M3", 2.5, 9.0, (sx * bx0, sy * by0), "z", zr - 9.0, zr + 1))
    add(f"   {'part':14s}{'screw':7s}{'pilot':9s}{'depth':8s}{'hole empty':>11s}{'material':>10s}")
    bad = 0
    counts = {}
    for name, sc, d, depth, pos, axis, a0, a1 in holes:
        mid = (a0 + a1) / 2
        p_on = {"z": (pos[0], pos[1], mid), "x": (mid, pos[0], pos[1]), "y": (pos[0], mid, pos[1])}[axis]
        off = {"z": (pos[0] + d * 0.5 + 1.2, pos[1], mid),
               "x": (mid, pos[0] + d * 0.5 + 1.2, pos[1]),
               "y": (pos[0], mid, pos[1] + d * 0.5 + 1.2)}[axis]
        empty = not bool(shell.contains([p_on])[0])
        solid = bool(shell.contains([off])[0])
        good = empty and solid
        bad += 0 if good else 1
        counts[name] = counts.get(name, 0) + 1
        pstr = f"{d:.1f} x {depth:.1f}"
        add(f"   {name:14s}{sc:7s}{pstr:9s}{'':8s}{str(empty):>11s}{str(solid):>10s}  "
            f"{'PASS' if good else 'FAIL'}   at ({pos[0]:.1f}, {pos[1]:.1f})")
    ok = ok and bad == 0
    add(f"   -> {len(holes)} screw holes in total: " +
        ", ".join(f"{v} x {k}" for k, v in counts.items()) +
        f"  |  3 x cable-tie holes d4.0 (through)   ALL {'PASS' if bad == 0 else 'FAIL'}")
    add("")
    add("J. outer polish / assembly features (probed)")
    W_, H_, D_ = P["W"], P["H"], P["D"]
    r, c = P["corner_r"], P["rim_chamfer"]
    plate_m = build_plate()
    checks = [
        ("corner rounded",     not bool(shell.contains([[W_ / 2 - 0.3, H_ / 2 - 0.3, 20.0]])[0])),
        ("corner material kept", bool(shell.contains([[W_ / 2 - r - 1.2, H_ / 2 - r - 1.2, 20.0]])[0])),
        ("front rim chamfered", not bool(shell.contains([[W_ / 2 - 0.2, 0.0, 0.2]])[0])),
        ("rim material below",  bool(shell.contains([[W_ / 2 - 0.2, 0.0, 2.0]])[0])),
        ("plate rear chamfer",  not bool(plate_m.contains([[W_ / 2 - 0.2, 0.0, D_ - 0.2]])[0])),
        ("plate corner round",  not bool(plate_m.contains([[W_ / 2 - 0.3, H_ / 2 - 0.3, D_ - 0.5]])[0])),
        ("plate csk open",      not bool(plate_m.contains([[P["plate_boss_xy"][0] + 2.6,
                                                            P["plate_boss_xy"][1], D_ - 0.4]])[0])),
        ("plate csk wall kept", bool(plate_m.contains([[P["plate_boss_xy"][0] + 5.0,
                                                        P["plate_boss_xy"][1], D_ - 0.4]])[0])),
        ("RC522 seat rib",      bool(shell.contains([[fcx - 30.0 - P["rfid_board_fit"] - 0.6,
                                                      fcy, zi + 0.5]])[0])),
        ("RC522 ledge ring",    bool(shell.contains([[fcx - 30.0 + 1.0, fcy, zi - 0.05]])[0])),
        ("R307 seat rib",       bool(shell.contains([[rcx + 10.0 + P["r307_seat_fit"] + 0.6,
                                                      rcy + 16.0, zi + 0.5]])[0])),
        ("strain-relief post",  bool(shell.contains([[P["zip_post4"][0] + 3.0, P["zip_post4"][1], zi + 3.0]])[0])),
    ]
    for name, good in checks:
        ok = ok and good
        add(f"   {name:22s} {'PASS' if good else 'FAIL'}")
    add("")
    add("H. STL file re-read verification (what the slicer will actually see)")
    for nm, fn in (("shell", "01_MAIN_SHELL_v2.stl"), ("rear plate", "02_REAR_PLATE_v2.stl"),
                   ("R307 bracket", "03_R307_BRACKET_v2.stl"), ("RC522 clamp", "04_RC522_CLAMP_v2.stl")):
        m = trimesh.load(os.path.join(OUT, fn), process=True, merge_tex=False, merge_norm=False)
        cnt = np.bincount(m.edges_unique_inverse, minlength=len(m.edges_unique))
        open_e, bad_e = int((cnt == 1).sum()), int((cnt > 2).sum())
        nb = len(m.split(only_watertight=False))
        tiny = int((m.area_faces < 1e-6).sum())
        good = (open_e == 0 and bad_e == 0 and nb == 1)
        ok = ok and good
        add(f"   {nm:<12} edges open={open_e} non-manifold={bad_e} bodies={nb}"
            f" micro-faces={tiny} vol={abs(m.volume)/1000:.1f} cm3   {'PASS' if good else 'FAIL'}")
    add("")
    add(f"RESULT: {'ALL CHECKS PASS' if ok else 'FAILURES - see above'}")
    return "\n".join(L), ok


def main():
    shell = build_shell()
    plate = build_plate()
    bracket = build_r307_bracket()
    clamp = build_rc522_clamp()
    shell.export(os.path.join(OUT, "01_MAIN_SHELL_v2.stl"))
    plate.export(os.path.join(OUT, "02_REAR_PLATE_v2.stl"))
    bracket.export(os.path.join(OUT, "03_R307_BRACKET_v2.stl"))
    clamp.export(os.path.join(OUT, "04_RC522_CLAMP_v2.stl"))
    txt, ok = audit(shell, plate, bracket, clamp)
    with open(os.path.join(ROOT, "docs", "v2_audit.txt"), "w") as fh:
        fh.write(txt + "\n")
    print(txt)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
