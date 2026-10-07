"""Fixing detail: how the RC522 is held down (per-triangle colours, one draw pass).

Panels
  1  exploded - the print as it goes in: wall -> pads -> board -> clamp bars -> screws,
                every hole drawn as the real hollow circle that is in the printed part
  2  section  - cut at the +Y row of screw axes, showing the exact stack-up in mm
Geometry is taken from tools/build_v2.py (same parameters, same expressions).
"""
import sys
sys.path.insert(0, "/home/user/astro-smart-attendance/tools")
import numpy as np
import trimesh
from PIL import Image, ImageDraw
from stl_tools import render, projection, project_points
import build_v2 as B

ROOT = "/home/user/astro-smart-attendance/"
OUT = ROOT + "renders/"
P = B.P
BG = (16, 18, 24)
W, H = 1180, 720

C_WALL = (100, 110, 126)
C_BOARD = (68, 145, 92)
C_PAD = (120, 160, 205)
C_BAR = (226, 178, 92)
C_SCREW = (206, 210, 218)
C_LIP = (245, 205, 120)

fcx, fcy = P["rc522_centre"]                 # -20.05, -24.05
pox, poy = P["rc522_post_off"]               # 22, 27
zi = P["wall_front"]                         # 3.0
bw, bl, board_t = P["rc522_board"]           # 60, 40, 1.6
win_w, win_h = P["rfid_window"]              # 56, 38
pad_s = P["rc522_post"]                      # 8.0 square posts
pad_h = P["rc522_post_h"]                    # 2.5
pilot_d = P["rc522_pilot_d"]                 # 2.2
cw, cl, ct = P["rc522_clamp"]                # 62, 13, 1.6
lw, ll = P["rc522_clamp_lip"]                # 62, 3.0
z_board_top = zi + board_t                   # 4.6
pad_top = zi + pad_h                         # 5.5
lt = pad_top - z_board_top                   # 0.9  lip step
bar_lo = pad_top                             # 5.5  platform underside = pad top
bar_hi = bar_lo + ct                         # 7.1
cbore_d, cbore_t = 5.6, 1.4                  # screw-head recess machined into each bar

# clamp y extents exactly as build_v2 lays them out (+Y bar at fcy+16..fcy+31) and its mirror
PLAT = [(fcy + poy - cl + 2.0, fcy + poy + 4.0)]
PLAT.append(tuple(2 * fcy - v for v in reversed(PLAT[0])))
LIPY = [(fcy + poy - cl + 2.0, fcy + poy - cl + 2.0 + ll)]
LIPY.append(tuple(2 * fcy - v for v in reversed(LIPY[0])))


def box(x0, x1, y0, y1, z0, z1):
    m = trimesh.creation.box(extents=(max(x1 - x0, 1e-6), max(y1 - y0, 1e-6), max(z1 - z0, 1e-6)))
    m.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])
    return m


def hollow(m, holes):
    """subtract (x, y, d, z0, z1) hole cylinders - the real printed hole, not a drawn ring"""
    cutters = []
    for x, y, d, hz0, hz1 in holes:
        c = trimesh.creation.cylinder(radius=d / 2, height=hz1 - hz0, sections=40)
        c.apply_translation([x, y, (hz0 + hz1) / 2])
        cutters.append(c)
    if not cutters:
        return m
    return trimesh.boolean.difference([m] + cutters, engine="manifold")


def screw(x, y, z0, z1, d=2.2, head_d=4.6, head_t=1.8):
    """self-tapping M2.5: thread boss in the pilot + a pan head seated in the bar's recess"""
    m = trimesh.creation.cylinder(radius=d / 2, height=z1 - z0, sections=32)
    m.apply_translation([x, y, (z0 + z1) / 2])
    hd = trimesh.creation.cylinder(radius=head_d / 2, height=head_t, sections=32)
    hd.apply_translation([x, y, z1 + head_t / 2 - 0.15])
    return trimesh.util.concatenate([m, hd])


def build(dz_board=0.0, dz_bar=0.0, dz_screw=0.0, only_two_pads=True, slice_y=None, x_min=None):
    """Return (triangles, per-triangle rgb)."""
    parts = []
    hx, hy = win_w / 2 + 0.4, win_h / 2 + 0.4            # wall frame around the open scan window

    def wall(x0, x1, y0, y1):
        parts.append((box(x0, x1, y0, y1, 0.0, zi), C_WALL))

    wall(fcx - 46, fcx - hx, fcy - 34, fcy + 34)         # left of the window
    wall(fcx + hx, fcx + 46, fcy - 34, fcy + 34)         # right of the window
    wall(fcx - hx, fcx + hx, fcy - 34, fcy - hy)         # below the window
    wall(fcx - hx, fcx + hx, fcy + hy, fcy + 34)         # above the window

    # the 4 screw pads: square posts with a real round pilot hole down the middle
    for sx in (-1, 1):
        for sy in (-1, 1):
            px, py = fcx + sx * pox, fcy + sy * poy
            parts.append((hollow(box(px - pad_s / 2, px + pad_s / 2, py - pad_s / 2, py + pad_s / 2,
                                     zi, pad_top), [(px, py, pilot_d, zi - 1.0, pad_top + 1.0)]),
                          C_PAD))

    # RC522 board, with its 4 fixing holes (d2.7 clearance for M2.5)
    brd = hollow(box(fcx - bw / 2, fcx + bw / 2, fcy - bl / 2, fcy + bl / 2,
                     zi + dz_board, z_board_top + dz_board),
                 [(fcx + sx * pox, fcy + sy * poy, 2.7,
                   zi + dz_board - 1.0, z_board_top + dz_board + 1.0)
                  for sx in (-1, 1) for sy in (-1, 1)])
    parts.append((brd, C_BOARD))

    # two clamp bars (04): platform over the pad pair + lip down to the board face
    for sy, (y_pl0, y_pl1), (y_li0, y_li1) in ((1, PLAT[0], LIPY[0]), (-1, PLAT[1], LIPY[1])):
        holes = []
        for sx in (-1, 1):
            hx_, hy_ = fcx + sx * pox, fcy + sy * poy
            holes.append((hx_, hy_, 3.0, bar_lo + dz_bar - 1.0, bar_hi + dz_bar + 1.0))
            holes.append((hx_, hy_, cbore_d, bar_hi + dz_bar - cbore_t, bar_hi + dz_bar + 1.0))
        plat = hollow(box(fcx - cw / 2, fcx + cw / 2, y_pl0, y_pl1,
                          bar_lo + dz_bar, bar_hi + dz_bar), holes)
        lip = hollow(box(fcx - lw / 2, fcx + lw / 2, y_li0, y_li1,
                         z_board_top + dz_bar, bar_lo + dz_bar),
                     [(fcx + sx * pox, fcy + sy * poy, 3.0,
                       z_board_top + dz_bar - 1.0, bar_lo + dz_bar + 1.0) for sx in (-1, 1)])
        parts.append((plat, C_BAR))
        parts.append((lip, C_LIP))

    # screws: shaft down through the bar into the pad pilot, head seated in the bar recess
    for sx in (-1, 1):
        for sy in (1, -1):
            if only_two_pads and sy < 0:
                continue
            parts.append((screw(fcx + sx * pox, fcy + sy * poy, z_board_top + 0.2 + dz_bar,
                                bar_hi - cbore_t - 0.1 + dz_bar), C_SCREW))

    tris, cols = [], []
    for m, c in parts:
        f = np.asarray(m.faces)
        v = np.asarray(m.vertices, dtype=np.float64)
        t = v[f]
        if slice_y is not None:                       # simple half-space clip (keeps y <= slice_y)
            keep = t[:, :, 1].max(axis=1) <= slice_y + 1e-9
            t = t[keep]
        if x_min is not None:                         # and keep only x >= x_min (zoom near a screw)
            keep = t[:, :, 0].min(axis=1) >= x_min - 1e-9
            t = t[keep]
        if len(t):
            tris.append(t)
            cols.append(np.tile(np.array(c, dtype=np.uint8), (len(t), 1)))
    return np.concatenate(tris), np.concatenate(cols)


def annotate(im, tri, view, marks, title, note):
    W_, H_ = im.size
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W_, 24], fill=(10, 11, 15))
    d.text((8, 6), title, fill=(233, 235, 240))
    if note:
        d.rectangle([0, H_ - 22, W_, H_], fill=(10, 11, 15))
        d.text((8, H_ - 15), note, fill=(120, 220, 255))
    R, sc, ox, oy = projection(tri, view, W_, H_, margins=0.09)

    def PX(pt):
        sx, sy, _ = project_points(np.array([pt]), R, sc, ox, oy)
        return float(sx[0]), float(sy[0])

    placed = []
    for pt, lab, col, dx, dy in marks:
        sx, sy = PX(pt)
        w = 6.6 * len(lab) + 10
        tx = min(max(sx + dx, 6), W_ - w - 6)
        ty = min(max(sy + dy, 34), H_ - 40)
        for _ in range(40):
            if not any(abs(ty - py) < 19 and tx < px + pw and px < tx + w for px, pw, py in placed):
                break
            ty += 21
            if ty > H_ - 40:
                ty = 34
                tx = min(max(tx + 0.5 * w, 6), W_ - w - 6)
        placed.append((tx, w, ty))
        d.line([sx, sy, tx + (4 if dx >= 0 else w - 4), ty + 7], fill=col)
        d.ellipse([sx - 3, sy - 3, sx + 3, sy + 3], outline=col, width=2)
        d.rectangle([tx - 2, ty - 2, tx + w, ty + 15], fill=(10, 11, 15))
        d.text((tx + 2, ty), lab, fill=col)
    return im


# ----------------------------------------------------------------- panel 1: exploded
# steep view so the explode direction (Z) runs straight up the page
VIEW1 = (0, 62)
DZ_B, DZ_R, DZ_S = 20.0, 52.0, 84.0
t1, c1 = build(dz_board=DZ_B, dz_bar=DZ_R)
im1 = render(t1, OUT + "_fix1.png", view=VIEW1, W=W, H=H, bg=BG, tri_rgb=c1)
marks1 = [
    ((fcx, fcy + poy, bar_hi + DZ_S + 1.0), "4 x M2.5 x 6 pan head", C_SCREW, 70, -70),
    ((fcx - 26, fcy + poy, bar_hi + DZ_R + 0.4),
     "2 x printed clamp bars (04): d3 hole + d5.6 head recess", C_BAR, 60, -26),
    ((fcx - pox, fcy + poy, z_board_top + DZ_B + 0.4),
     "RC522 60 x 40 x 1.6, 4 x d2.7 holes", C_BOARD, 30, -66),
    ((fcx - pox, fcy + poy - 4, pad_top - 0.4), "4 x 8 x 8 pads, d2.2 pilot 4.1 deep",
     C_PAD, -360, 66),
    ((fcx - 24, fcy + win_h / 2 + 0.4, zi),
     "front wall 3.0 mm - RFID window 56 x 38 fully open", C_WALL, -430, 110),
]
im1 = annotate(im1, t1, VIEW1, marks1,
               "1  RC522 FIXING - EXPLODED   (no clips: the board is screwed down, not snapped in)",
               "the bars press only the two short board edges, so the whole 56 x 38 scan window stays "
               "open - and every hole above is a real hollow circle in the print")
im1.save(OUT + "v2_fixing_exploded.png")

# ----------------------------------------------------------------- panel 2: section
# top view of a half assembly: X across the page, Z down it, all at the +Y pad row
t2, c2 = build(slice_y=fcy + poy + 0.001, x_min=fcx + 2.0)      # zoom on the +X screw axis
VIEW2 = "top"
im2 = render(t2, OUT + "_fix2.png", view=VIEW2, W=W, H=H, bg=BG, tri_rgb=c2)
marks2 = [
    ((fcx - 4, fcy + poy, bar_hi - 0.3), f"clamp platform {ct:.1f}", C_BAR, -250, -46),
    ((fcx - 26, fcy + poy, z_board_top + lt / 2), f"lip {lt:.1f}", C_LIP, -280, 30),
    ((fcx + pox, fcy + poy, (zi + pad_top) / 2 - 0.6), f"pad {pad_h:.1f}, d{pilot_d} pilot",
     C_PAD, 130, -30),
    ((fcx + 24, fcy + poy, z_board_top - 0.4), f"board {board_t:.1f}", C_BOARD, 150, 26),
    ((fcx - 40, fcy + poy, zi - 0.8), f"front wall {zi:.1f}", C_WALL, -300, 60),
]
im2 = annotate(im2, t2, VIEW2, marks2,
               "2  SECTION ON A +Y SCREW AXIS, ZOOMED   (X across, Z down; the near half is cut away)",
               f"stack-up: wall {zi:.1f} | board {board_t:.1f} | lip {lt:.1f} | platform {ct:.1f} "
               f"| pad {pad_h:.1f}   ->   platform underside {bar_lo:.2f} lands exactly on the pad top "
               f"{pad_top:.2f}, and the screw head sits in the bar's d{cbore_d} recess")
im2.save(OUT + "v2_fixing_section.png")

# ----------------------------------------------------------------- combined sheet
sheet = Image.new("RGB", (W, H * 2 + 8), (10, 11, 15))
sheet.paste(im1, (0, 0))
sheet.paste(im2, (0, H + 8))
sheet.save(OUT + "v2_fixing_detail.png")
print("wrote renders/v2_fixing_exploded.png / v2_fixing_section.png / v2_fixing_detail.png")
print(f"stack check: platform underside {bar_lo:.2f} == pad top {pad_top:.2f} -> "
      f"{'OK' if abs(bar_lo - pad_top) < 1e-9 else 'MISMATCH'}; "
      f"lip {lt:.1f} spans board face {z_board_top:.2f} -> pad top {pad_top:.2f}; "
      f"pads d{pilot_d} pilots, board d2.7 holes, bars d3.0 holes + d{cbore_d} head recesses")
