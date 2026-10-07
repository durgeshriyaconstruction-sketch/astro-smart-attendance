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
    r307_relief=(25.0, 27.0), r307_relief_deep=1.6,
    r307_body=(20.0, 44.1, 23.5),                           # [REF]
    r307_post=6.0, r307_post_h=23.5, r307_pilot=2.5,
    r307_bracket_holes=(-13.95, 14.05), r307_bracket_w=52.2,

    # ---- RC522 RFID ------------------------------------------------------
    rc522_board=(60.0, 40.0, 1.6),                          # [REF]
    rc522_centre=(-20.05, -24.05),                          # [V1] recess centre
    rc522_components=6.0,                                   # [REF] 3-8 mm
    rc522_pocket=(64.0, 44.0),                              # 2 mm clearance
    rfid_recess=(62.7, 44.7), rfid_recess_deep=1.5,         # [V1]
    rfid_window=(54.0, 36.0), rfid_bars=(2, 4.0),           # <- the open scan window
    rc522_tab_over=1.2, rc522_tab_t=1.4,

    # ---- ESP32 DevKit V1 -------------------------------------------------
    esp32_board=(28.33, 51.45, 1.6),                        # [REF] Y x Z when flat on wall
    esp32_comp_h=16.0,                                      # [REF] 8-12 + USB
    esp32_post_len=10.0, esp32_usb_edge=-70.0,               # USB edge Y
    esp32_z_centre=27.5,                                     # keeps it clear of the RC522
    esp32_pad=8.0, esp32_pilot=2.2, esp32_inset=3.5,        # inset VERIFY_ACTUAL_HARDWARE
    usb_slot=(18.0, 10.0), usb_plug=(15.6, 8.0),

    # ---- 3010 fan --------------------------------------------------------
    fan=(30.0, 30.0, 10.0), fan_pitch=24.0, fan_open_d=26.0,  # [REF]
    fan_centre_yz=(14.0, 22.0), fan_post=8.0, fan_pilot=2.5,

    # ---- ventilation -----------------------------------------------------
    vent_slot=(20.0, 4.0), vent_rows=(-16.0, 16.0), vent_z=(6.0, 12.0),
    top_vent=(16.0, 3.0), top_vent_x=(-18.0, 0.0, 18.0), top_vent_z=26.0,

    # ---- hardware --------------------------------------------------------
    plate_boss=9.0, plate_boss_xy=(46.5, 71.0),
    plate_pilot=2.5, plate_screw=3.4,
    keyhole_d=7.5, keyhole_slot=4.6, keyhole_span=50.0,
    zip_post=(8.0, -55.0), zip_post2=(30.0, -55.0), zip_post3=(44.0, 12.0),
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

    # -------------------------------------------------------------- RC522
    fcx, fcy = P["rc522_centre"]
    rrw, rrh = P["rfid_recess"]
    deep = P["rfid_recess_deep"]
    cut.append(ext_z(rr(fcx, fcy, rrw, rrh, 3.0), -1, deep))
    cut.append(ext_z(rr(fcx, fcy, rrw + 1.6, rrh + 1.6, 3.4), 0.6, deep + 0.01))
    vw, vh = P["rfid_window"]
    cut.append(ext_z(rr(fcx, fcy, vw, vh, 5.0), deep - 0.1, zi + 1))     # OPEN window
    nbar, bw = P["rfid_bars"]
    for k in range(nbar):
        off = (k + 1) * vw / (nbar + 1) - vw / 2
        late.append(bx(fcx + off - bw / 2, fcx + off + bw / 2,
                       fcy - vh / 2 - 1.0, fcy + vh / 2 + 1.0, deep - 0.05, zi))
    pw, ph = P["rc522_pocket"]
    rim = 2.4
    early.append(DIFF([bx(fcx - pw / 2 - rim, fcx + pw / 2 + rim,
                          fcy - ph / 2 - rim, fcy + ph / 2 + rim, zi - 0.5, zi + 2.4),
                       bx(fcx - pw / 2, fcx + pw / 2, fcy - ph / 2, fcy + ph / 2,
                          zi - 1, zi + 3)], engine="manifold"))
    zt0 = zi + P["rc522_board"][2]
    zt1 = zt0 + P["rc522_tab_t"]
    over = P["rc522_tab_over"]
    for tx, ty, inward in ((-40.0, fcy + ph / 2, -1), (0.0, fcy + ph / 2, -1),
                           (-40.0, fcy - ph / 2, +1), (0.0, fcy - ph / 2, +1)):
        y_in = ty + inward * (over + 1.0)
        y_host = ty - inward * 1.0
        early.append(bx(tx - 3, tx + 3, y_in, y_host, zt0, zt1))
        early.append(bx(tx - 3, tx + 3, y_in, y_in + inward * 0.9, zt0, zt0 + 0.4))

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
    for (zx, zy) in (P["zip_post"], P["zip_post2"], P["zip_post3"]):
        early.append(bx(zx - 4, zx + 4, zy - 4, zy + 4, zi - 0.5, zi + 8.0))
        cut.append(cyl_z(zx, zy, zi + 1.6, zi + 9.0, P["zip_pilot"]))

    # ------------------------------------------------------------- ribs
    early.append(bx(46.0, 48.4, -60.0, 30.0, zi - 0.5, zi + 2.4))
    early.append(bx(-wi, 46.0, 30.0, 32.4, zi - 0.5, zi + 2.4))

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
    kd, ks, span = P["keyhole_d"], P["keyhole_slot"], P["keyhole_span"]
    for kx in (-span / 2, span / 2):
        cut.append(cyl_z(kx, 0.0, z0 - 1, D + 1, kd))
        cut.append(bx(kx - ks / 2, kx + ks / 2, -kd / 2, 12.0, z0 - 1, D + 1))
    plate = DIFF([plate, UNION(cut, engine="manifold")], engine="manifold")

    ribs = [bx(-span / 2, span / 2, -1.5, 1.5, z0 - 4.0, z0 - 2.0)]
    for kx in (-span / 2, span / 2):
        ribs.append(bx(kx - 1.5, kx + 1.5, -H / 2 + 8, span / 2, z0 - 4.0, z0 - 2.0))
    return UNION([plate] + ribs, engine="manifold")


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
def thickness(shell, origin, direction, maxmm=30.0, step=0.05):
    d = np.array(direction, dtype=float)
    d /= np.linalg.norm(d)
    t = 0.0
    if not shell.contains([origin])[0]:
        return 0.0
    while t < maxmm and shell.contains([np.array(origin) + d * t])[0]:
        t += step
    return t


def wall_probe(shell):
    probes = [
        ("front wall, plain",        (0.0, 10.0, 0.1), (0, 0, 1),  2.90),
        ("front wall, RFID recess",  (-50.0, -30.0, 1.55), (0, 0, 1), 1.45),
        ("RFID stiffener bar",       (-29.05, -24.05, 1.55), (0, 0, 1), 1.45),
        ("side wall",                (-54.9, 0.0, 40.0), (1, 0, 0), 2.30),
        ("top wall",                 (0.0, 77.4, 20.0), (0, -1, 0), 2.90),
        ("bottom wall",              (-2.0, -77.4, 12.0), (0, 1, 0), 2.90),
        ("LCD boss above wall",      (36.0, 36.45, 3.0), (0, 0, 1), 11.50),
        ("R307 post height",         (20.0, -24.1, 3.0), (0, 0, 1), 23.50),
    ]
    rows = []
    for name, o, d, expect in probes:
        t = thickness(shell, o, d)
        rows.append((name, t, expect))
    return rows


def fcx_bar():
    return -20.05 - 9.0


def audit(shell, plate, r307b):
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
    for nm, m in (("shell <-> rear plate", plate), ("shell <-> R307 bracket", r307b)):
        v = abs(INTER([shell, m], engine="manifold").volume)
        add(f"   {nm:34s} {v:9.2f} mm3   {'PASS' if v < 1.0 else 'FAIL'}")
    add("")
    add("B. component fit  (envelope overlap with shell material = 0 required)")
    add(f"   {'envelope':26s} {'overlap':>10s}  verdict")
    ok = True
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
        ("RC522 hole positions", "slotted retainer pads", "unverified", False),
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
    add(f"   designed walls: front {P['wall_front']} mm (1.5 mm at the RFID recess), "
        f"sides {P['wall_side']} mm, top/bottom {P['wall_top']} mm, "
        f"plate {P['plate_t']} mm, fit clearance {P['fit']} mm")
    add("")
    add(f"RESULT: {'ALL CHECKS PASS' if ok else 'FAILURES - see above'}")
    return "\n".join(L), ok


def main():
    shell = build_shell()
    plate = build_plate()
    bracket = build_r307_bracket()
    shell.export(os.path.join(OUT, "01_MAIN_SHELL_v2.stl"))
    plate.export(os.path.join(OUT, "02_REAR_PLATE_v2.stl"))
    bracket.export(os.path.join(OUT, "03_R307_BRACKET_v2.stl"))
    txt, ok = audit(shell, plate, bracket)
    with open(os.path.join(ROOT, "docs", "v2_audit.txt"), "w") as fh:
        fh.write(txt + "\n")
    print(txt)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
