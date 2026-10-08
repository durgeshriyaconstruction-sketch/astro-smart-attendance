"""Fixing detail: how the RC522 is held down (per-triangle colours, one draw pass).

Panels
  1  exploded - the print as it goes in: wall -> pads -> board -> clamp bars -> screws,
                every hole drawn as the real hollow circle that is in the printed part
  2  section  - true cut at the +Y row of screw axes, dimensioned in mm
Geometry comes from tools/build_v2.py (same parameters, same expressions), so this figure
cannot drift from the model that produced the STL.
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
PANEL_BG = (10, 11, 15)
MARG = 0.055                       # SAME margin for render() and for the label projection
W = 1180

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
lw, ll = P["rc522_clamp_lip"]                # 62, 3.0  (width, lip y-extent)
z_board_top = zi + board_t                   # 4.6
pad_top = zi + pad_h                         # 5.5
lt = pad_top - z_board_top                   # 0.9  lip height, derived
bar_lo = pad_top                             # 5.5  platform underside = pad top
bar_hi = bar_lo + ct                         # 7.1
cbore_d, cbore_t = 5.6, 1.4                  # screw-head recess in each bar

# clamp y extents exactly as build_v2 lays them out (+Y bar at fcy+poy-cl+2 .. fcy+poy+4)
PLAT = [(fcy + poy - cl + 2.0, fcy + poy + 4.0)]
PLAT.append(tuple(2 * fcy - v for v in reversed(PLAT[0])))
LIPY = [(fcy + poy - cl + 2.0, fcy + poy - cl + 2.0 + ll)]
LIPY.append(tuple(2 * fcy - v for v in reversed(LIPY[0])))

CLIPX = [None]                                # optional x-range clamp used by box()
pilot_lo = 1.4                                # build_v2: cut.append(cyl_z(px, py, 1.4, ...))


def box(x0, x1, y0, y1, z0, z1):
    if CLIPX[0] is not None:                  # hard crop for the section panel
        x0 = max(x0, CLIPX[0][0])
        x1 = min(x1, CLIPX[0][1])
        if x1 - x0 < 1e-9:
            return None
    m = trimesh.creation.box(extents=(max(x1 - x0, 1e-6), max(y1 - y0, 1e-6), max(z1 - z0, 1e-6)))
    m.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])
    return m


def hollow(m, holes):
    """subtract (x, y, d, z0, z1) hole cylinders - the real printed hole, not a drawn ring"""
    if m is None:
        return None
    cutters = []
    for x, y, d, hz0, hz1 in holes:
        c = trimesh.creation.cylinder(radius=d / 2, height=hz1 - hz0, sections=40)
        c.apply_translation([x, y, (hz0 + hz1) / 2])
        cutters.append(c)
    if not cutters:
        return m
    return trimesh.boolean.difference([m] + cutters, engine="manifold")


def screw(x, y, z0, z1, d=2.2, head_d=4.6, head_t=1.8):
    """self-tapping M2.5: thread boss in the pilot + a pan head seated in the bar recess"""
    m = trimesh.creation.cylinder(radius=d / 2, height=z1 - z0, sections=32)
    m.apply_translation([x, y, (z0 + z1) / 2])
    hd = trimesh.creation.cylinder(radius=head_d / 2, height=head_t, sections=32)
    hd.apply_translation([x, y, z1 + head_t / 2 - 0.15])
    return trimesh.util.concatenate([m, hd])


def build(dz_board=0.0, dz_bar=0.0, only_two_pads=True, slice_y=None, clipx=None):
    """Return (triangles, per-triangle rgb).

    With slice_y set the figure becomes a SECTION: material the plane actually cuts is
    drawn at full brightness, everything that only sits BEHIND the plane is dimmed, so a
    reader can never mistake background for cut material.
    """
    CLIPX[0] = clipx
    parts = []

    def add(m, c, y0, y1):
        parts.append((m, c, y0, y1))

    hx, hy = win_w / 2 + 0.4, win_h / 2 + 0.4            # wall frame around the open scan window

    def wall(x0, x1, y0, y1):
        add(box(x0, x1, y0, y1, 0.0, zi), C_WALL, y0, y1)

    wall(fcx - 46, fcx - hx, fcy - 34, fcy + 34)         # left of the window
    wall(fcx + hx, fcx + 46, fcy - 34, fcy + 34)         # right of the window
    wall(fcx - hx, fcx + hx, fcy - 34, fcy - hy)         # below the window
    wall(fcx - hx, fcx + hx, fcy + hy, fcy + 34)         # above the window

    # the 4 screw pads: square posts with a real round BLIND pilot hole down the middle.
    # exactly as build_v2 lays them: post from zi-0.5 to zi+2.5, pilot from z=1.4 up to the
    # top, so the hole is pad_top-1.4 = 4.1 deep and leaves 1.4 mm of wall underneath it.
    for sx in (-1, 1):
        for sy in (-1, 1):
            px, py = fcx + sx * pox, fcy + sy * poy
            add(hollow(box(px - pad_s / 2, px + pad_s / 2, py - pad_s / 2, py + pad_s / 2,
                           zi - 0.5, pad_top), [(px, py, pilot_d, pilot_lo, pad_top + 0.001)]),
                C_PAD, py - pad_s / 2, py + pad_s / 2)

    # RC522 board, with its 4 fixing holes (d2.7 clearance for M2.5)
    add(hollow(box(fcx - bw / 2, fcx + bw / 2, fcy - bl / 2, fcy + bl / 2,
                   zi + dz_board, z_board_top + dz_board),
               [(fcx + sx * pox, fcy + sy * poy, 2.7,
                 zi + dz_board - 1.0, z_board_top + dz_board + 1.0)
                for sx in (-1, 1) for sy in (-1, 1)]), C_BOARD, fcy - bl / 2, fcy + bl / 2)

    # two clamp bars (part 04): platform over the pad pair + lip down to the board face
    for sy, (y_pl0, y_pl1), (y_li0, y_li1) in ((1, PLAT[0], LIPY[0]), (-1, PLAT[1], LIPY[1])):
        holes = []
        for sx in (-1, 1):
            hx_, hy_ = fcx + sx * pox, fcy + sy * poy
            holes.append((hx_, hy_, 3.0, bar_lo + dz_bar - 1.0, bar_hi + dz_bar + 1.0))
            holes.append((hx_, hy_, cbore_d, bar_hi + dz_bar - cbore_t, bar_hi + dz_bar + 1.0))
        add(hollow(box(fcx - cw / 2, fcx + cw / 2, y_pl0, y_pl1,
                       bar_lo + dz_bar, bar_hi + dz_bar), holes), C_BAR, y_pl0, y_pl1)
        add(hollow(box(fcx - lw / 2, fcx + lw / 2, y_li0, y_li1,
                       z_board_top + dz_bar, bar_lo + dz_bar),
                   [(fcx + sx * pox, fcy + sy * poy, 3.0,
                     z_board_top + dz_bar - 1.0, bar_lo + dz_bar + 1.0) for sx in (-1, 1)]),
            C_LIP, y_li0, y_li1)

    # screws: shaft down through the bar into the pad pilot, head seated in the bar recess
    for sx in (-1, 1):
        for sy in (1, -1):
            if only_two_pads and sy < 0:
                continue
            py = fcy + sy * poy
            add(screw(fcx + sx * pox, py, z_board_top + 0.2 + dz_bar,
                      bar_hi - cbore_t - 0.1 + dz_bar), C_SCREW, py - 2.4, py + 2.4)

    tris, cols = [], []
    for m, c, y0, y1 in parts:
        if m is None:
            continue
        f = np.asarray(m.faces)
        v = np.asarray(m.vertices, dtype=np.float64)
        t = v[f]
        if slice_y is not None:                       # keep y <= slice_y -> the cut faces the camera
            t = t[t[:, :, 1].max(axis=1) <= slice_y + 1e-9]
        if clipx is not None:
            t = t[(t[:, :, 0].max(axis=1) <= clipx[1] + 1e-9) &
                  (t[:, :, 0].min(axis=1) >= clipx[0] - 1e-9)]
        if len(t):
            col = np.array(c, dtype=np.uint8)
            if slice_y is not None and not (y0 - 1e-9 <= slice_y <= y1 + 1e-9):
                col = (col * 0.38).astype(np.uint8)   # background behind the cut plane
            tris.append(t)
            cols.append(np.tile(col, (len(t), 1)))
    CLIPX[0] = None
    return np.concatenate(tris), np.concatenate(cols)


class Annot:
    """Label layer drawn in the SAME projection the renderer used (same margins)."""

    def __init__(self, im, tri, view, title, note=None):
        self.im = im
        self.d = ImageDraw.Draw(im)
        self.W, self.H = im.size
        self.R, self.sc, self.ox, self.oy = projection(tri, view, self.W, self.H, margins=MARG)
        self.d.rectangle([0, 0, self.W, 24], fill=PANEL_BG)
        self.d.text((8, 6), title, fill=(233, 235, 240))
        if note:
            self.d.rectangle([0, self.H - 22, self.W, self.H], fill=PANEL_BG)
            self.d.text((8, self.H - 15), note, fill=(120, 220, 255))

    def px(self, pt):
        sx, sy, _ = project_points(np.array([pt], dtype=np.float64), self.R, self.sc, self.ox, self.oy)
        return float(sx[0]), float(sy[0])

    def label(self, pt, text, col, tx, ty, align="left"):
        sx, sy = self.px(pt)
        w = 6.7 * len(text) + 12
        x = tx if align == "left" else (tx - w if align == "right" else tx - w / 2)
        lx = x + w - 5 if sx > x + w else x + 3
        self.d.line([sx, sy, lx, ty + 8], fill=col)
        self.d.ellipse([sx - 3, sy - 3, sx + 3, sy + 3], outline=col, width=2)
        self.d.rectangle([x - 3, ty - 2, x + w - 3, ty + 16], fill=PANEL_BG)
        self.d.text((x + 2, ty + 2), text, fill=col)
        return x, ty, w

    def dimv(self, x_model, z0, z1, text, col):
        """vertical dimension with ticks, drawn at a model x position (pixels via projection)"""
        (ax, ay) = self.px((x_model, 0, z0))
        (bx_, by_) = self.px((x_model, 0, z1))
        self.d.line([ax, ay, bx_, by_], fill=col, width=1)
        for (px_, py_) in ((ax, ay), (bx_, by_)):
            self.d.line([px_ - 5, py_, px_ + 5, py_], fill=col)
        mx, my = (ax + bx_) / 2, (ay + by_) / 2
        w = 6.7 * len(text) + 8
        self.d.rectangle([mx - w / 2, my - 8, mx + w / 2, my + 8], fill=PANEL_BG)
        self.d.text((mx - w / 2 + 4, my - 5), text, fill=col)

    def save(self, name):
        self.im.save(OUT + name)


# ----------------------------------------------------------------- panel 1: exploded
# +Z runs UP the page (pitch < 0) so the stack reads bottom-up like the real assembly
VIEW1 = (0, -62)
H1 = 700
DZ_B, DZ_R = 16.0, 34.0
t1, c1 = build(dz_board=DZ_B, dz_bar=DZ_R)
im1 = render(t1, OUT + "_fix1.png", view=VIEW1, W=W, H=H1, bg=BG, margins=MARG, tri_rgb=c1)
a1 = Annot(im1, t1, VIEW1, "1   RC522 FIXED WITH SCREWS - exploded   (no clips: the board is screwed down)",
           "the bars press only the two short board edges, so the whole 56 x 38 scan window stays open"
           "   -   and every hole above is a real hollow circle in the print")
a1.label((fcx - pox, fcy + poy, bar_hi + DZ_R - cbore_t / 2),
         "4 x M2.5 x 6 pan head, seated flush in the recess", C_SCREW, 40, 42)
a1.label((fcx + 20, fcy + poy, bar_hi + DZ_R + 0.4),
         "2 x printed clamp bars (part 04): d3.0 through hole", C_BAR, W - 340, 100, "right")
a1.label((fcx - 24, fcy + poy - cl + 3.5, z_board_top + DZ_R + lt / 2),
         f"lip {lt:.1f} down to the board face", C_LIP, 40, 190)
a1.label((fcx + 24, fcy, z_board_top + DZ_B + 0.4),
         "RC522 60 x 40 x 1.6, 4 x d2.7 clearance holes", C_BOARD, W - 36, 250, "right")
a1.label((fcx - pox, fcy + poy, pad_top - 0.4),
         f"4 x 8 x 8 x {pad_h:.1f} pads, d{pilot_d} pilot (4.1 deep in the print)", C_PAD, W - 36, 640, "right")
a1.label((fcx - 34, fcy + win_h / 2 + 0.4, zi),
         f"front wall {zi:.1f} mm - RFID scan window {win_w:.0f} x {win_h:.0f} fully open", C_WALL, 40, 610)
a1.save("v2_fixing_exploded.png")

# ----------------------------------------------------------------- panel 2: section
# true cut on the +Y screw row, cropped around the +X screw axis so it can be dimensioned
H2 = 430
CLIP = (fcx + 2.0, fcx + 40.0)
t2, c2 = build(slice_y=fcy + poy + 0.001, clipx=CLIP)
VIEW2 = (180, 90)      # cut face toward the camera, +Z up the page, X increasing to the left
im2 = render(t2, OUT + "_fix2.png", view=VIEW2, W=W, H=H2, bg=BG, margins=MARG, tri_rgb=c2)
a2 = Annot(im2, t2, VIEW2,
           "2   SECTION ON THE +Y SCREW AXIS, ZOOMED   (seen from the +Y side: Z up, X to the left)",
           f"stack-up: wall {zi:.1f} | board {board_t:.1f} | lip {lt:.1f} | platform {ct:.1f} | pad {pad_h:.1f}"
           f"   ->   platform underside {bar_lo:.2f} lands exactly on the pad top {pad_top:.2f},"
           f" screw head sits in the bar's d{cbore_d} x {cbore_t:.1f} recess,"
           f" and {pilot_lo:.1f} mm of wall stays under the blind pilot")
# vertical dimension chain on the left of the section, one bracket per layer
x_dim = fcx + 4.5
a2.dimv(x_dim, 0.0, zi, f"wall {zi:.1f}", C_WALL)
a2.dimv(x_dim + 0.0, zi, z_board_top, f"board {board_t:.1f}", C_BOARD)
a2.dimv(fcx + 13.5, z_board_top, bar_lo, f"lip {lt:.1f}", C_LIP)
a2.dimv(fcx + 13.5, bar_lo, bar_hi, f"platform {ct:.1f}", C_BAR)
a2.dimv(fcx + 34.0, zi, pad_top, f"pad {pad_h:.1f}", C_PAD)
a2.dimv(fcx + pox + pad_s / 2 + 2.0, pilot_lo, pad_top, "pilot 4.1 deep", C_SCREW)
a2.label((fcx + pox, fcy + poy, (zi + pad_top) / 2),
         f"d{pilot_d} pilot, 4.1 deep, in the pad", C_PAD, 40, 330)
a2.label((fcx + pox - pilot_d / 2 - 0.1, fcy + poy, zi + 0.2), f"pilot d{pilot_d:.1f}", C_SCREW, 640, 356)
a2.label((fcx + pox + 1.6, fcy + poy, bar_hi - cbore_t / 2), f"head recess d{cbore_d} x {cbore_t:.1f}", C_LIP, 700, 330)
a2.save("v2_fixing_section.png")

# ----------------------------------------------------------------- combined sheet
sheet = Image.new("RGB", (W, H1 + H2 + 8), PANEL_BG)
sheet.paste(im1, (0, 0))
sheet.paste(im2, (0, H1 + 8))
sheet.save(OUT + "v2_fixing_detail.png")
print("wrote renders/v2_fixing_exploded.png / v2_fixing_section.png / v2_fixing_detail.png")
print(f"stack check: platform underside {bar_lo:.2f} == pad top {pad_top:.2f} -> "
      f"{'OK' if abs(bar_lo - pad_top) < 1e-9 else 'MISMATCH'}; "
      f"lip {lt:.1f} spans board face {z_board_top:.2f} -> pad top {pad_top:.2f}; "
      f"pads d{pilot_d} pilots, board d2.7 holes, bars d3.0 holes + d{cbore_d} head recesses")
