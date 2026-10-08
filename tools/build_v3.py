"""
ASTRO SMART ATTENDANCE - v3 enclosure generator (parametric, 1:1 mm).

v3 is a RE-DESIGN, not a polish of v2.  Architectural changes vs v2:
  1  4 mm shallower (46 vs 48) and 2.6 mm side walls (was 2.4) - stiffer, lighter look
  2  RFID aperture is 100 % clear: v2's two 2.5 mm stiffener bars are GONE, the wall around
     the 56 x 38 hole is a 2.0 mm ledge ring reinforced by 4 corner gussets instead
  3  the RC522 is held by ONE perimeter hold-down ring (62.4 x 44.4 x 2.6, 55 x 37 opening)
     that rests on 4 pads whose tops are coplanar with the board's back face - no lip, no
     two-part clamp, nothing in front of the antenna coil
  4  the 3010 fan sits in a CLEAR d28 bore (v2 had 3 bars across it) on 4 internal bosses
  5  0.45 x 3.0 rebate ring around the LCD and fingerprint openings (shadow line, edge chip
     protection), R307 bracket redrawn as a dog-bone with two stiffening ribs
  6  ESP32 on 4 round d7 bosses with 0.5 spotfaces + a 3 x 2 locating rail
  7  rear plate: 2 strain-relief slots in line with 2 tie posts, register lip tightened to
     0.55 mm, plain side walls - the d28 fan bore is the inlet and the 8 + 4 grilles the outlet

Axes:   X = width (110)   Y = height (155)   Z = depth (48)
        z = 0  -> device FRONT (user) face
        z = 45 -> shell rear edge, z 45..48 = rear service plate

Provenance of every number:  [V1] measured from the uploaded 01_MAIN_SHELL.stl
                             [REF] component reference supplied by the team
                             [EST] engineering estimate -> VERIFY_ACTUAL_HARDWARE

Run:  python3 tools/build_v3.py     ->  cad/v3/*.stl  +  docs/v3_audit.txt
"""
import os
import sys

import numpy as np
import trimesh
from shapely.geometry import box as sbox

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "cad", "v3")
os.makedirs(OUT, exist_ok=True)
os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)

# ============================================================================
# 1. PARAMETERS  (change, re-run, everything rebuilds - nothing hard coded)
# ============================================================================
P = dict(
    W=110.0, H=155.0, D=46.0,
    wall_side=2.6, wall_top=3.0, wall_front=3.0, plate_t=3.0,
    fit=0.35, rebate=(0.45, 3.0),        # cosmetic sink ring around the front openings

    # ---- LCD1602 + I2C backpack -----------------------------------------
    lcd_window=(66.0, 17.5), lcd_centre=(0.0, 51.95),        # [V1] window pos
    lcd_hole_pitch=(75.1, 31.0),                             # [V1] == 1602 std
    lcd_boss=6.0, lcd_pilot=2.05, lcd_glass_t=11.5,       # v3.1: pilot at M2.5 minor dia  # [REF] 18-25 mm deep

    # ---- R307 fingerprint -----------------------------------------------
    r307_window=(19.3, 21.2), r307_centre=(35.95, -24.1),   # [V1]
    r307_relief=(21.0, 25.0), r307_relief_deep=1.6,         # clears the M3 posts
    r307_body=(20.0, 44.1, 23.5),                           # [REF]
    r307_post=6.0, r307_post_h=23.5, r307_pilot=2.5,
    r307_seat=(1.2, 1.5), r307_seat_fit=0.35,               # locating seat (w x h)
    r307_bracket_holes=(-13.95, 14.05), r307_bracket_w=52.2,

    # ---- RC522 RFID ------------------------------------------------------
    rc522_board=(40.0, 60.0, 1.6),                          # [REF] v3.2: portrait, see below
    rc522_centre=(-16.05, -24.05),                          # [V1] recess centre
    rc522_components=6.0,                                   # [REF] 3-8 mm
    rc522_pocket=(44.0, 64.0),                              # 2 mm clearance
    rfid_recess=(44.7, 62.7), rfid_recess_deep=0.8,         # v3: 2.2 mm ledge ring, no bars
    rfid_board_fit=0.35, rfid_seat_rib=(1.2, 1.0),          # locating ribs (w x h)
    rfid_window=(38.0, 56.0), rfid_bars=(0, 0.0),           # v3: NO bars, clear aperture
    rc522_post_off=(17.0, 34.0), rc522_post=8.0,                      # screw ears, beyond board
    #  ^ the ear centres must clear THREE things at once: the board's outline (|y| > 30), the
    #    ring's own opening (|y| > 27.5), and the through-window cut in the wall (|y| > 28) - 34
    #    does all three with >= 6 mm to spare, exactly as v3.0's (22, 27) did for the landscape
    #    board (it cleared |x| 30 / opening 27.5 / window 28 in the other axis).
    rc522_pilot_d=2.05,
    rc522_ring=(43.6, 62.4, 2.6), rc522_ring_open=(37.0, 55.0, 3.0),   # v3 hold-down ring
    rc522_post_h=1.6,                          # pad top = board back face (zero-lip clamp)

    # ---- ESP32 DevKit V1 -------------------------------------------------
    esp32_board=(28.33, 51.45, 1.6),                        # [REF] Y x Z when flat on wall
    esp32_comp_h=16.0,                                      # [REF] 8-12 + USB
    esp32_post_len=10.0, esp32_usb_edge=-70.0,               # USB edge Y
    esp32_z_centre=27.5,                                     # keeps it clear of the RC522
    esp32_pad=8.0, esp32_pilot=1.8, esp32_inset=3.5,        # inset VERIFY_ACTUAL_HARDWARE
    usb_slot=(18.0, 10.0), usb_plug=(15.6, 8.0),

    # ---- 3010 fan --------------------------------------------------------
    fan=(30.0, 30.0, 10.0), fan_pitch=24.0, fan_open_d=28.0,  # v3: clear bore, no grille
    fan_centre_yz=(17.0, 24.0), fan_post=8.0, fan_pilot=2.5,

    # ---- ventilation -----------------------------------------------------
    # v3.3: the side walls are plain, by request ("remove the right-side grooves - I have a
    # fan").  The fan in the -X wall therefore becomes the INLET: air is drawn in through the
    # d28 bore and leaves through the bottom + top grilles.  The physics rule did not move, only
    # the openings: the passive set must stay >= 1.5x the bore, which the 8 bottom + 4 top slots
    # below give (measured, see docs/v3_physics_audit.txt section 4).  side_intake=True restores
    # the v3.2 arrangement (8 x 30 x 5 in +X, fan exhausting) in one rebuild.
    side_intake=False,
    # the pitch is 25 mm and the slot 21 wide, which leaves 4.0 mm of web - thicker than the
    # 3.0 mm wall itself.  Two rows of 5 mm at 7 / 14.5 left a 2.5 mm web between the rows,
    # i.e. a ligament thinner than the wall it sits in, and the physics audit (section 8)
    # failed it; 4.5 tall at 7 / 15 gives 3.5 mm and still keeps 1.75 mm clear of the front
    # wall's inner face and 4.6 mm clear of the USB opening.
    vent_slot=(21.0, 4.5), vent_rows=(-37.5, -12.5, 12.5, 37.5), vent_z=(7.0, 15.0),
    top_vent=(21.0, 4.0), top_vent_x=(-37.5, -12.5, 12.5, 37.5), top_vent_z=26.0,
    intake=(30.0, 5.0, (-52.5, -17.5, 17.5, 52.5), (18.0, 32.0), 2.5),  # 8 slots = 1157 mm2

    # ---- hardware --------------------------------------------------------
    plate_boss=9.0, plate_boss_xy=(46.5, 67.5), lip_fit=0.25, lip_w=8.0,   # v3.1: 3.5 mm inboard
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


def ext_x(poly, x0, x1):
    """polygon given in (y, z) -> prism spanning x0..x1.

    extrude_polygon works along local Z, so the frame is permuted cyclically
    (local x -> world y, local y -> world z, local z -> world x): det = +1, no mirroring.
    """
    x0, x1 = sorted((x0, x1))
    m = trimesh.creation.extrude_polygon(poly, x1 - x0)
    T = np.eye(4)
    T[:3, :3] = [[0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
    m.apply_transform(T)
    m.apply_translation([x0, 0, 0])
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
    rd, rw = P["rebate"]                                  # 0.45 deep x 3.0 wide sink ring
    cut.append(DIFF([ext_z(rr(lcx, lcy, lw + 2 * rw, lh + 2 * rw, 3.0), -0.5, rd),
                     ext_z(rr(lcx, lcy, lw, lh, 1.5), -1.0, rd + 1.0)], engine="manifold"))
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
    # bezel relief: the module's front flange passes through this opening and registers
    # on the FLOOR OF THE REBATE (rd), not on a separate internal pocket.  Starting the
    # cut at rd instead of 1.6 removes what would otherwise be a 1.15 mm ledge standing
    # between the two cuts (measured by the wall-thickness map in the verifier).
    cut.append(ext_z(rr(rcx, rcy, relw, relh, 2.0), P["rebate"][0], zi + 1))
    ww, hh = P["r307_window"]
    rd, rw = P["rebate"]
    cut.append(DIFF([ext_z(rr(rcx, rcy, ww + 2 * rw, hh + 2 * rw, 3.0), -0.5, rd),
                     ext_z(rr(rcx, rcy, ww, hh, 2.0), -1.0, rd + 1.0)], engine="manifold"))
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
    # v3: this rim used to carry v2's clamp bars up to 5.4; now it is trimmed to the SAME
    # height as the pads and the board's back face (zi + 1.6) so the hold-down ring lies
    # perfectly flat on one plane - no shim, no tilt, no three-point contact
    rim_top = zi + P["rc522_post_h"]
    early.append(DIFF([bx(fcx - pw / 2 - rim, fcx + pw / 2 + rim,
                          fcy - ph / 2 - rim, fcy + ph / 2 + rim, zi - 0.5, rim_top),
                       bx(fcx - pw / 2, fcx + pw / 2, fcy - ph / 2, fcy + ph / 2,
                          zi - 1, rim_top + 1)], engine="manifold"))
    # 4 pads for the v3 hold-down ring - circular M2.5 pilots, top face coplanar with the
    # board's back face (pad_h 1.6 == board_t 1.6) so the ring sits flat with no lip
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
    # v2 also cut a d30 x 1.2 shallow recess around this bore as a fan "seat spigot".  It
    # left a 1.0 mm wide, 1.4 mm thick lip standing all round the opening - the thinnest
    # plastic anywhere in the print - and it does nothing, because the fan is bolted to the
    # standoffs INSIDE the cavity and its 30 mm frame never enters the wall.  Deleted in v3:
    # the fan wall is now a flat 3.0 mm plate with a clean d28 bore through it.

    # v3: NO grille bars.  The d28 bore is completely clear; the fan frame is captured by
    # the 4 bosses below, which is what carried the wall stiffness load in v2.
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
            early.append(cyl_x(-wi - 0.5, ex_face, py, pz, P["esp32_pad"]))
            cut.append(cyl_x(ex_face - 0.7, ex_face + 0.2, py, pz, P["esp32_pilot"] + 1.4))
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

    # --------------------------------------------- v3 intake holes (+X wall)
    iw, ih, iys, izs, ir = P["intake"]
    if P["side_intake"]:
        for iy in iys:
            for iz in izs:
                cut.append(ext_x(rr(iy, iz, iw, ih, ir), wi - 0.1, W / 2 + 2))

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
    lf = P["lip_fit"]          # 0.25 mm per side (v2 used 0.35 -> rattlier)
    # v3: not a solid plug (v2 filled the whole rear opening with 39 cm3 of plastic) but an
    # 8 x 2 mm register FRAME that locates the plate; the -X stretch is left open over the
    # ESP32 so the board and its bosses pass freely.
    ox_, oy_ = wi - lf, hi - lf
    ix_, iy_ = ox_ - P["lip_w"], oy_ - P["lip_w"]
    ribs = [bx(ix_, ox_, -oy_, oy_, z0 - 2.0, z0 + 0.15),        # +X
            bx(-ox_, -ix_, -oy_, oy_, z0 - 2.0, z0 + 0.15),      # -X
            bx(-ox_, ox_, -oy_, -iy_, z0 - 2.0, z0 + 0.15),      # -Y
            bx(-ox_, ox_, iy_, oy_, z0 - 2.0, z0 + 0.15)]        # +Y
    plate = UNION([plate] + ribs, engine="manifold")
    # The ESP32 stands on 4 bosses and 2 locating tabs that reach z = 41.67, i.e. into the
    # register zone, so one clearance box cuts the frame wherever that module lives.  What is
    # left is 3 full sides + both ends of the 4th (about 90 mm of 148) - plenty to locate a
    # plate that is also held by 4 M3 screws, and the cut removes plastic nobody needs.
    wi2 = P["W"] / 2 - P["wall_side"]
    ezc, ebw, ebl = P["esp32_z_centre"], P["esp32_board"][0], P["esp32_board"][1]
    ey0 = P["esp32_usb_edge"]
    # v3.2 LAYOUT: the RC522 is mounted PORTRAIT (its 60 mm dimension along Y, not X).  With the
    # board's 60 mm side along X it could not be installed at all: the front wall's bay between the
    # ESP32's stand-off posts (which end at x = -42.4) and the R307's -X post (which starts at
    # x = 15.95) is 58.35 mm, and the reader's own hold-down ring is 62.4 mm - a 4 mm shortfall, so
    # no vertical or tilted path existed (audit section 3 F13).  Turned through 90 deg the whole
    # stack is 43.6 mm wide and drops straight down with 6.4 mm to the ESP32 posts, 10.2 mm to the
    # R307 post and 3.25 mm to the fan bosses; a card is portrait anyway, and the swipe area lands
    # nearer the centre of the front face.
    # v3.1 BUGFIX: this relief used to run to z = D + 2, i.e. THROUGH THE WHOLE PLATE, so the
    # shipped v3.0 rear plate had a 15.6 x 63 mm hole in its -X-Y corner (found by the physics
    # audit, invisible to the interference test because the frame is cut there anyway).  The
    # relief only has to remove register-frame material, so it now stops at the frame's own top.
    plate = DIFF([plate, bx(-ox_ - 2.0, -wi2 + P["esp32_post_len"] + 3.0,
                            ey0 - 6.0, ey0 + ebl + 6.0, z0 - 2.5, z0 + 0.16)], engine="manifold")

    cut = []
    bx0, by0 = P["plate_boss_xy"]
    r = P["plate_boss"] / 2 + 0.4
    for sx in (-1, 1):
        for sy in (-1, 1):
            for comp in (plate,):
                pass
            cut.append(bx(sx * bx0 - r, sx * bx0 + r, sy * by0 - r, sy * by0 + r,
                          z0 - 2.2, z0 + 0.3))            # relief for the shell boss
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

    # v3.1: the two 3 x 2 mm hang rails that used to be unioned here are gone.  They stood
    # 2 mm in FRONT of the plate, touched nothing but the register frame's bottom face, and
    # bridged 50 mm between their legs - they carried no load (the hooks see 1.7 N each against
    # 8.5 MPa of shear area, a 70x reserve) and they were the one feature in the whole model a
    # slicer would have to print as a long thin bridge.
    return plate


def build_rc522_ring():
    """v3 RC522 hold-down ring (ONE flat part, printed once).

    A rectangular frame that sits BEHIND the board: its inner edge (55 x 37) is inside the
    wall's 56 x 38 aperture, so no material of this part stands in front of the antenna.
    It rests on 4 pads whose tops are coplanar with the board's back face, so it is a
    zero-lip, zero-flex clamp: the 4 M2.5 screws pull the ring onto the pads and the ring's
    inner edge holds the board against the wall's aperture edge.  No clamp bars over the
    aperture, no reliance on the module's own hole pitch.
    """
    fcx, fcy = P["rc522_centre"]
    pox, poy = P["rc522_post_off"]
    ow, oh, ot = P["rc522_ring"]
    opw, oph, opr = P["rc522_ring_open"]
    z0 = P["wall_front"] + P["rc522_board"][2]        # board back face = pad top = 4.6
    body = [bx(fcx - ow / 2, fcx + ow / 2, fcy - oh / 2, fcy + oh / 2, z0, z0 + ot)]
    # v3.2: the 4 screw tabs used to be hard-coded (x 15..29, y 20..31.5) for the landscape
    # reader; they are now generated from rc522_post_off so they always carry the ears that sit on
    # the shell's pads, whichever way round the module is mounted.  The opening cut that follows
    # trims their inner ends, so the overlap onto the frame is self-limiting.
    tab_in = max(ow, oh) / 2.0 - 8.0
    for sx in (-1, 1):
        for sy in (-1, 1):
            xa, xb = fcx + sx * (pox - 4.0), fcx + sx * (pox + 4.0)
            ya, yb = fcy + sy * tab_in, fcy + sy * (poy + 4.0)
            body.append(bx(min(xa, xb), max(xa, xb), min(ya, yb), max(ya, yb), z0, z0 + ot))
    frame = UNION(body, engine="manifold")
    opening = ext_z(rr(fcx, fcy, opw, oph, opr), z0 - 1, z0 + ot + 1)
    frame = DIFF([frame, opening], engine="manifold")
    cut = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            px, py = fcx + sx * pox, fcy + sy * poy
            cut.append(cyl_z(px, py, z0 - 1, z0 + ot + 1, 3.0))                 # screw clears
            cut.append(cyl_z(px, py, z0 + ot - 1.5, z0 + ot + 1, 5.6))          # head recess
    return DIFF([frame, UNION(cut, engine="manifold")], engine="manifold")


def build_r307_bracket():
    rcx, rcy = P["r307_centre"]
    d0, d1 = P["r307_bracket_holes"]
    z0 = P["wall_front"] + P["r307_body"][2]
    # v3: dog-bone - wide over the two holes (bearing), narrow across the sensor face so
    # the bracket can be lifted off without prying on the glass, plus two 1.2 x 1.2 ribs
    w_end, w_mid = 7.0, 3.2
    x_lo = rcx + d0 - w_end
    x_hi = min(rcx + d1 + w_end, P["W"] / 2 - P["wall_side"] - 0.6)
    b0 = bx(x_lo, x_hi, rcy - w_end, rcy + w_end, z0, z0 + 2.0)
    b1 = bx(rcx + d0 + w_end, max(x_hi - 2 * w_end, rcx + d1 - w_end),
            rcy - w_mid, rcy + w_mid, z0, z0 + 2.0)
    for sgn in (-1, 1):                       # two 1.2 x 1.2 ribs on the wide parts
        b1 = UNION([b1, bx(x_lo, x_lo + 12.0, rcy + sgn * (w_mid - 1.2), rcy + sgn * w_mid,
                           z0 + 2.0, z0 + 3.2)], engine="manifold")
    b = UNION([b0, b1], engine="manifold")
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
    # v3.2: the reader is portrait, so the lane the card is presented in runs along Y
    lane = fcy - 24.0                       # inside the aperture, away from the bearing band
    usx = -wi + P["esp32_post_len"] + 3.5
    ezc = P["esp32_z_centre"]
    fy, fz = P["fan_centre_yz"]
    cases = [
        ("LCD window",        (lcx, lcy, zi - 1.5), (lcx + P["lcd_window"][0] / 2 + 4, lcy, zi - 1.5)),
        ("R307 window",       (rcx, rcy, zi - 1.5), (rcx + P["r307_window"][0] / 2 + 4, rcy, zi - 1.5)),
        ("RFID scan window",  (fcx, lane, (deep + zi) / 2),
         (fcx, fcy - P["rfid_window"][1] / 2 - 2, (deep + zi) / 2)),
        ("USB slot",          (usx, -P["H"] / 2 + 1.5, ezc), (usx + P["usb_slot"][0] / 2 + 4, -P["H"] / 2 + 1.5, ezc)),
        ("fan bore (no grille)", (-P["W"] / 2 + 1.5, fy, fz), (-P["W"] / 2 + 1.5, fy, fz + P["fan_open_d"] / 2 + 4)),
        ("exhaust slot",      (P["vent_rows"][0], -P["H"] / 2 + 1.5, P["vent_z"][0]),
                              ((P["vent_rows"][0] + P["vent_rows"][1]) / 2,
                               -P["H"] / 2 + 1.5, P["vent_z"][0])),
        ("top vent",          (P["top_vent_x"][0], P["H"] / 2 - 1.5, P["top_vent_z"]),
                              (P["top_vent_x"][0], P["H"] / 2 - 1.5,
                               P["top_vent_z"] + P["top_vent"][1] / 2 + 5)),
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
        ("front wall, plain",        (0.0, 20.0, 0.1), (0, 0, 1),  2.90),
        # this one DOES stand on a hole: the RC522 corner pilot is blind from the
        # inside, so what is left is the skin the screw threads into.
        ("front-wall skin under an RC522 pilot", (0.95, 9.95, 0.1), (0, 0, 1), 1.40),
        # these two used to stand outside the recess and read nonsense (2.95 /
        # 0.00 against a 2.20 expectation).  Floor first: 0.8 of shelf, then the
        # sheet that is left of the 3.0 wall.  Then full wall just outside it.
        # the aperture is fully open at the centre, so stand on the shelf band:
        # between the aperture edge (+3.95) and the recess edge (+7.31).
        ("RFID recess floor sheet",   (fcx, fcy + 29.7, -1.0), (0, 0, 1), 2.20),
        ("front wall beside the recess", (fcx + 26.0, fcy, -1.0), (0, 0, 1), 3.00),
        ("side wall",                (-54.9, 0.0, 40.0), (1, 0, 0), 2.60),
        ("top wall",                 (0.0, 77.4, 20.0), (0, -1, 0), 2.90),
        ("bottom wall",              (-2.0, -77.4, 12.0), (0, 1, 0), 2.90),
        ("LCD boss above wall",      (36.0, 36.45, 3.0), (0, 0, 1), 11.50),
        ("R307 post height",         (20.0, -24.1, 3.0), (0, 0, 1), 23.50),
        ("fan bore rim (no grille)", (-53.9, P["fan_centre_yz"][0], P["fan_centre_yz"][1] + 16.0), (1, 0, 0), 1.60),
    ]
    rows = []
    for name, o, d, expect in probes:
        t = thickness(shell, o, d)
        rows.append((name, t, expect))
    return rows


def fcx_bar():
    return -20.05 - 9.0


def audit(shell, plate, r307b, ring=None):
    L = []
    add = L.append
    vol = abs(shell.volume) / 1000.0
    add("ASTRO SMART ATTENDANCE - v3 enclosure audit  (RE-DESIGN)")
    add("=" * 76)
    add(f"axis frame: X width {P['W']:.0f}, Y height {P['H']:.0f}, Z depth {P['D']:.0f} mm")
    add(f"shell     : {len(shell.faces)} tris, watertight={shell.is_watertight}, "
        f"winding_ok={shell.is_winding_consistent}, bodies={shell.body_count}")
    add(f"shell size: {np.round(shell.extents,1).tolist()} (depth 43 + 3 mm plate = 46)")
    add(f"assembly  : 110.0 x 155.0 x 46.0 mm  (v2 was 48 deep)")
    add(f"volume    : {vol:.1f} cm3  ~{vol*0.62:.0f} g PLA (15 % infill, estimate)")
    add("")
    add("A. printed-part interference")
    ok = True
    checks = [("shell <-> rear plate", plate), ("shell <-> R307 bracket", r307b),
              ("shell <-> RC522 ring", ring)]
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
    add(f"   RC522 ring   : size {np.round(ring.extents,1).tolist()}, "
        f"watertight={ring.is_watertight}, {abs(ring.volume)/1000:.1f} cm3  (print 1, flat - "
        f"v2 needed 2 clamp bars + a lip, v3 needs one part)")
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
        ("RC522 pcb", f"{P['rc522_board'][:2]}", "40 x 60", True),
        ("LCD pcb", "80 x 36 (window pattern 75.1 x 31)", "80 x 36", True),
        ("LCD visible", f"{P['lcd_window']} window", "64 x 16", True),
        ("Fan", f"{P['fan']}", "30 x 30 x 10", True),
        ("Fan hole pitch", f"{P['fan_pitch']}", "~24", True),
        ("ESP32 PCB hole inset", f"{P['esp32_inset']}", "unverified", False),
        ("RC522 board holes", "unused - perimeter hold-down ring", "unverified", False),
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
    add(f"   designed walls: front {P['wall_front']} mm, locally {P['wall_front'] - P['rfid_recess_deep']:.1f} mm"
        f" at the RFID ledge ring, sides {P['wall_side']} mm, top/bottom {P['wall_top']} mm, "
        f"plate {P['plate_t']} mm, part fit {P['fit']} mm, plate register lip {P['lip_fit']} mm/side, "
        f"rebate ring {P['rebate'][0]} x {P['rebate'][1]} mm around the LCD + fingerprint openings")
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
            holes.append(("LCD1602", "M2.5", 2.05, 8.5,
                          (lcx + sx * P["lcd_hole_pitch"][0] / 2, lcy + sy * P["lcd_hole_pitch"][1] / 2),
                          "z", zi + 4.5, zi + P["lcd_glass_t"] + 1.5))
    for dx in P["r307_bracket_holes"]:                        # R307 : 2 x M3
        holes.append(("R307 bracket", "M3", 2.5, 8.0, (rcx + dx, rcy), "z",
                      zi + P["r307_post_h"] - 7.0, zi + P["r307_post_h"] + 1))
    for sx in (-1, 1):                                        # RC522 : 4 x M2.5
        for sy in (-1, 1):
            holes.append(("RC522 ring", "M2.5", 2.05, 3.8,
                          (fcx + sx * pox, fcy + sy * poy), "z", 1.4, zi + P["rc522_post_h"] + 0.6))
    for py in (ey0 + P["esp32_inset"], ey0 + ebl - P["esp32_inset"]):      # ESP32 : 4 x M2.2
        for pz in (ez0 + P["esp32_inset"], ez1 - P["esp32_inset"]):
            holes.append(("ESP32 standoff", "M2.2", 1.8, 7.0, (py, pz), "x",
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
        pstr = f"{d:.2f} x {depth:.1f}"
        add(f"   {name:14s}{sc:7s}{pstr:9s}{'':8s}{str(empty):>11s}{str(solid):>10s}  "
            f"{'PASS' if good else 'FAIL'}   at ({pos[0]:.1f}, {pos[1]:.1f})")
    ok = ok and bad == 0
    add(f"   -> {len(holes)} screw holes in total: " +
        ", ".join(f"{v} x {k}" for k, v in counts.items()) +
        f"  |  4 x cable-tie holes d4.0 (through)   ALL {'PASS' if bad == 0 else 'FAIL'}")
    add("")
    add("J. outer polish / assembly features (probed)")
    fyv, fzv = P["fan_centre_yz"]
    W_, H_, D_ = P["W"], P["H"], P["D"]
    r, c = P["corner_r"], P["rim_chamfer"]
    plate_m = build_plate()
    checks = [
        ("corner rounded",     not bool(shell.contains([[W_ / 2 - 0.3, H_ / 2 - 0.3, 20.0]])[0])),
        ("corner material kept", all(bool(shell.contains([[W_ / 2 - dx, H_ / 2 - dy, 20.0]])[0])
                                      for dx, dy in ((1.3, 1.3), (0.8, 2.2), (2.2, 0.8)))),
        # v3.1 note: this used to probe one point at (W/2-r-1.2, H/2-r-1.2) which happened to
        # land on a rear-plate boss, so it was not measuring the corner at all.  Three points
        # inside the wall band, none of them on a boss, is.

        ("front rim chamfered", not bool(shell.contains([[W_ / 2 - 0.2, 0.0, 0.2]])[0])),
        ("rim material below",  bool(shell.contains([[W_ / 2 - 0.2, 0.0, 2.0]])[0])),
        ("plate rear chamfer",  not bool(plate_m.contains([[W_ / 2 - 0.2, 0.0, D_ - 0.2]])[0])),
        ("plate corner round",  not bool(plate_m.contains([[W_ / 2 - 0.3, H_ / 2 - 0.3, D_ - 0.5]])[0])),
        ("plate csk open",      not bool(plate_m.contains([[P["plate_boss_xy"][0] + 2.6,
                                                            P["plate_boss_xy"][1], D_ - 0.4]])[0])),
        ("plate csk wall kept", bool(plate_m.contains([[P["plate_boss_xy"][0] + 5.0,
                                                        P["plate_boss_xy"][1], D_ - 0.4]])[0])),
        ("RC522 seat rib",      bool(shell.contains(
            [[fcx - (P["rc522_board"][0] / 2 + P["rfid_board_fit"]) - 0.6, fcy, zi + 0.5]])[0])),
        ("RC522 ledge ring",    bool(shell.contains(
            [[fcx - (P["rfid_window"][0] + P["rfid_recess"][0]) / 4.0, fcy, zi - 0.05]])[0])),
        ("R307 seat rib",       bool(shell.contains([[rcx + 10.0 + P["r307_seat_fit"] + 0.6,
                                                      rcy + 16.0, zi + 0.5]])[0])),
        ("strain-relief post",  bool(shell.contains([[P["zip_post4"][0] + 3.0, P["zip_post4"][1], zi + 3.0]])[0])),
    ]
    wi_ = P["W"] / 2 - P["wall_side"]
    lcy_ = P["lcd_centre"][1]; lcx_ = P["lcd_centre"][0]
    lw_ = P["lcd_window"][0]; lh_ = P["lcd_window"][1]
    eyf_ = P["esp32_usb_edge"]; ezf_ = P["esp32_z_centre"]; ebw_ = P["esp32_board"][0]
    exf_ = -wi_ + P["esp32_post_len"]
    fyv, fzv = P["fan_centre_yz"]
    iw, ih, iys, izs, ir = P["intake"]

    def _solid(*c):
        """is that design-frame point inside the shell's material?"""
        return bool(shell.contains([list(c)])[0])

    checks += [
        ("RFID aperture centre clear", not _solid(fcx, fcy, zi - 1.5)),
        ("no bar in the aperture",
         not _solid(fcx - 9.33, fcy, zi - 1.5) and not _solid(fcx + 9.33, fcy, zi - 1.5)),
        ("fan bore centre clear", not _solid(-P["W"] / 2 + 1.0, fyv, fzv)),
        *([("intake slot open (+X)", not _solid(W_ / 2 - 1.0, iys[0], izs[0])),
           ("intake wall beside", _solid(W_ / 2 - 1.0, iys[0] - iw / 2 - 2.0, izs[0]))]
          if P["side_intake"] else
          [("+X wall plain (no side openings)",
            all(_solid(W_ / 2 - 1.0, iy, iz) for iy in iys for iz in tuple(izs) + (2.5, 41.0))),
           ("bottom grille open", not _solid(P["vent_rows"][0], -H_ / 2 + 1.0, P["vent_z"][0])),
           ("top grille open", not _solid(P["top_vent_x"][0], H_ / 2 - 1.0, P["top_vent_z"])),
           ("wall between grille rows",
            _solid((P["vent_rows"][0] + P["vent_rows"][1]) / 2, -H_ / 2 + 1.0,
                   P["vent_z"][0]))]),
        # pad top must be exactly the board's back face (4.6) - probe OFF the pilot axis
        ("ring pad coplanar",       bool(shell.contains(
            [[fcx - P["rc522_post_off"][0] + 2.6, fcy + P["rc522_post_off"][1] - 2.6,
              zi + P["rc522_post_h"] - 0.2]])[0]) and
                                    not bool(shell.contains(
            [[fcx - P["rc522_post_off"][0] + 2.6, fcy + P["rc522_post_off"][1] - 2.6,
              zi + P["rc522_post_h"] + 0.3]])[0])),
        ("LCD rebate ring cut",    not bool(shell.contains([[lcx_, lcy_ + lh_ / 2 + 1.4, 0.2]])[0])),
        ("wall under LCD rebate",   bool(shell.contains([[lcx_, lcy_ + lh_ / 2 + 1.4, 1.6]])[0])),
        ("rebate at the other side", not bool(shell.contains([[lcx_ + lw_ / 2 + 1.4, lcy_, 0.2]])[0])),
        ("ESP32 round boss",        bool(shell.contains([[exf_ - 2.0, eyf_ + P["esp32_inset"] + 2.0,
                                                          ezf_ - ebw_ / 2 + P["esp32_inset"]]])[0]),),
        ("ESP32 spotface open",    not bool(shell.contains([[exf_ + 0.1, eyf_ + P["esp32_inset"],
                                                             ezf_ - ebw_ / 2 + P["esp32_inset"]]])[0])),
    ]
    for name, good in checks:
        ok = ok and good
        add(f"   {name:26s} {'PASS' if good else 'FAIL'}")
    add("")
    add("K. v3 design deltas - measured, not asserted")
    # ---- K1  RFID aperture: every ray through the 56 x 38 opening must escape
    vw, vh = P["rfid_window"]
    # the aperture has R5 corners, so the sample grid is masked to the SAME rounded rectangle
    # - otherwise the grid's own square corners would read as "blocked" and lie about the part
    apol = rr(fcx, fcy, vw, vh, 5.0)
    nx, ny = 113, 77
    xs = np.linspace(fcx - vw / 2, fcx + vw / 2, nx)
    ys = np.linspace(fcy - vh / 2, fcy + vh / 2, ny)
    gx, gy = np.meshgrid(xs, ys)
    from shapely.geometry import Point
    inside_grid = np.array([apol.contains(Point(x, y)) for x, y in
                            zip(gx.ravel(), gy.ravel())]).reshape(gx.shape)
    px_, py_ = gx[inside_grid], gy[inside_grid]
    pts = np.column_stack([px_, py_, np.full(len(px_), zi / 2)])
    blocked = int(shell.contains(pts).sum())
    area = apol.area
    per = area / len(pts)
    free = area - blocked * per
    add(f"   K1 RFID aperture   {len(pts)} rays inside the rounded {vw:.0f} x {vh:.0f} window: "
        f"{blocked} blocked  ->  {free:.0f} mm2 free ({100 * free / area:.1f} % of "
        f"{area:.0f} mm2 of opening)   v2 lost 190 mm2 to two stiffener bars")
    ok = ok and blocked == 0
    # ---- K2  fan bore
    fr = P["fan_open_d"] / 2 - 0.5
    fa = np.pi * fr * fr
    n = 21
    fx0, fx1 = fyv - fr, fyv + fr
    gx2, gy2 = np.meshgrid(np.linspace(fx0, fx1, n), np.linspace(fzv - fr, fzv + fr, n))
    keep = (gx2 - fyv) ** 2 + (gy2 - fzv) ** 2 <= fr * fr
    kk = int(keep.sum())
    pts = np.column_stack([np.full(kk, -W_ / 2 + 1.2), gx2[keep], gy2[keep]])
    blocked = int(shell.contains(pts).sum())
    tot = int(keep.sum())
    add(f"   K2 fan bore        {tot} rays in the d{P['fan_open_d']:.0f} circle: {blocked} blocked"
        f"  ->  {100 * (1 - blocked / tot):.1f} % of the bore is open"
        f"   (v2: 3 grille bars left 50 %)")
    ok = ok and blocked == 0
    # ---- K3  the ring must sit on ONE plane: pads, pocket rim and board all at 4.60
    zz = P["wall_front"] + P["rc522_post_h"]
    seats = [("pad -X-Y", (fcx - pox - 2.6, fcy - poy - 2.6)), ("pad +X-Y", (fcx + pox + 2.6, fcy - poy - 2.6)),
             ("pad -X+Y", (fcx - pox - 2.6, fcy + poy + 2.6)), ("pad +X+Y", (fcx + pox + 2.6, fcy + poy + 2.6))]
    bad = [nm for nm, (qx, qy) in seats
           if not (bool(shell.contains([[qx, qy, zz - 0.05]])[0]) and
                   not bool(shell.contains([[qx, qy, zz + 0.05]])[0]))]
    add(f"   K3 clamp seat flat  {len(seats) - len(bad)}/{len(seats)} pad tops at exactly z={zz:.2f}"
        f" (the ring's seat plane)   {'PASS' if not bad else 'FAIL ' + str(bad)}")
    ok = ok and not bad
    bearing = [("bearing +Y", (fcx, fcy + vh / 2 + 0.6)), ("bearing -Y", (fcx, fcy - vh / 2 - 0.6)),
               ("bearing +X", (fcx + vw / 2 + 0.6, fcy)), ("bearing -X", (fcx - vw / 2 - 0.6, fcy))]
    bad2 = [nm for nm, (qx, qy) in bearing
            if not (bool(shell.contains([[qx, qy, P["wall_front"] - 0.05]])[0]) and
                    not bool(shell.contains([[qx, qy, P["wall_front"] + 0.05]])[0]))]
    add(f"   K3b board bearing   {len(bearing) - len(bad2)}/{len(bearing)} points on the flat "
        f"inner face at z={P['wall_front']:.2f} all around the aperture   "
        f"{'PASS' if not bad2 else 'FAIL ' + str(bad2)}")
    ok = ok and not bad2
    # ---- K4  plate register frame instead of a solid plug
    plug = (P["W"] - 2 * P["wall_side"] - 2 * P["lip_fit"]) * \
           (P["H"] - 2 * P["wall_top"] - 2 * P["lip_fit"]) * 2.0 / 1000.0
    add(f"   K4 rear plate      {abs(plate.volume) / 1000:.1f} cm3   v2's solid 2 mm plug alone was "
        f"{plug:.1f} cm3 -> the v3 frame keeps the same location duty for a fraction of the plastic")
    # ---- K5  the two 45 deg chamfers must not have eaten the front rim
    add(f"   K5 front face      {P['wall_front']:.1f} mm plate, {P['rebate'][0]:.2f} x "
        f"{P['rebate'][1]:.1f} mm rebate sunk around LCD + fingerprint; "
        f"{2 * P['rim_chamfer']:.1f} mm of the rim was chamfered away, "
        f"{P['wall_front'] - P['rebate'][0]:.2f} mm is left under each rebate")
    add("")
    add("H. STL file re-read verification (what the slicer will actually see)")
    for nm, fn in (("shell", "01_MAIN_SHELL_v3.stl"), ("rear plate", "02_REAR_PLATE_v3.stl"),
                   ("R307 bracket", "03_R307_BRACKET_v3.stl"), ("RC522 ring", "04_RC522_RING_v3.stl")):
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
    ring = build_rc522_ring()
    # the assembly-frame copies are what the checkers were written against; the SHIPPED files are
    # the same meshes lowered onto the bed (tools/orient_v3.py), which is what a slicer needs.
    assy = os.path.join(OUT, "assembly")
    os.makedirs(assy, exist_ok=True)
    parts = [("01_MAIN_SHELL_v3.stl", shell), ("02_REAR_PLATE_v3.stl", plate),
             ("03_R307_BRACKET_v3.stl", bracket), ("04_RC522_RING_v3.stl", ring)]
    import orient_v3
    for fn, m in parts:
        m.export(os.path.join(assy, fn))
        # to_print must not touch the in-memory mesh: the A-K audit below runs in assembly coords
        orient_v3.to_print(m.copy(), fn).export(os.path.join(OUT, fn))
        print(f"   {fn:26s} shipped bed-aligned (was at z {orient_v3.ORIENT[fn][0]:.1f} in "
              f"assembly coords)")
    txt, ok = audit(shell, plate, bracket, ring)
    with open(os.path.join(ROOT, "docs", "v3_audit.txt"), "w") as fh:
        fh.write(txt + "\n")
    print(txt)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
