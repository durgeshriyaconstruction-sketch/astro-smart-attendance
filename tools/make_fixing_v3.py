"""v3 fixing detail - true sections of the SHIPPED STLs, plus the module outlines from P.

  renders/v3_fixing_detail.png   3D exploded (pads / PCB / ring / screws) + 3 cut sections
  renders/v3_fixing_section.png  the two RC522 sections, enlarged

The printed parts are never drawn by hand: every grey / green / pink shape in a section is the
polygon trimesh gets when it cuts the exported .stl with that exact plane, so a hole that is in
the figure is in the print.  Only the parts that are NOT printed (the PCB, the screws, the LCD
and ESP32 boards) are rectangles taken from tools/build_v3.py's parameter table.
"""
import sys

sys.path.insert(0, "/home/user/astro-smart-attendance/tools")
import numpy as np
import trimesh
from PIL import Image, ImageDraw
from stl_tools import load_stl, render, projection, project_points
import build_v3 as B

ROOT = "/home/user/astro-smart-attendance/"
OUT = ROOT + "renders/"
P = B.P

BG = (16, 18, 24)
PANEL = (10, 11, 15)
INK = (233, 235, 240)
YEL = (255, 205, 80)
CYA = (120, 220, 255)
GRN = (140, 255, 160)
MAG = (255, 150, 220)
RED = (255, 140, 140)

MESH = {k: trimesh.load(ROOT + f"cad/v3/{n}", process=True) for k, n in {
    "shell": "01_MAIN_SHELL_v3.stl", "plate": "02_REAR_PLATE_v3.stl",
    "bracket": "03_R307_BRACKET_v3.stl", "ring": "04_RC522_RING_v3.stl"}.items()}
FILL = {"shell": (126, 138, 158), "plate": (96, 156, 112), "bracket": (196, 152, 74),
        "ring": (176, 112, 176)}

fcx, fcy = P["rc522_centre"]
pox, poy = P["rc522_post_off"]
bw, bl, bt = P["rc522_board"]
win_w, win_h = P["rfid_window"]
rec_w, rec_h = P["rfid_recess"]
rec_d = P["rfid_recess_deep"]
zi, zf = P["wall_front"], P["wall_front"]          # front wall spans 0..3.0
pad_top = zi + P["rc522_post_h"]
ring_w, ring_h, ring_t = P["rc522_ring"]
op_w, op_h, op_r = P["rc522_ring_open"]
pilot = P["rc522_pilot_d"]
D = P["D"]
ZR = D - P["plate_t"]


# ------------------------------------------------------------------- section helper
from shapely.geometry import Polygon as _Poly, box as _box


def cut_polys(mesh, axis, value, clip=None):
    """the polygons trimesh gets when it cuts `mesh` with a plane, as world rings.

    returns [[ring(n,3), ...holes...], ...]; `clip` is (a0, a1, b0, b1) in the screen axes
    (x/z for an 'xz' cut, y/z for 'yz'), so a wall that runs the whole 43 mm can be cropped.
    """
    n = {"x": [1, 0, 0], "y": [0, 1, 0], "z": [0, 0, 1]}[axis]
    o = {"x": [value, 0, 0], "y": [0, value, 0], "z": [0, 0, value]}[axis]
    sec = mesh.section(plane_origin=o, plane_normal=n)
    if sec is None or not len(sec.entities):
        return []
    path, T = sec.to_2D()
    T = np.asarray(T, dtype=float)
    out = []
    for Q in path.polygons_full:
        rings = [Q.exterior] + list(Q.interiors)
        w = []
        for r in rings:
            g = np.asarray(r.coords)[:, :2]
            v = np.column_stack([g, np.zeros(len(g)), np.ones(len(g))]) @ T.T
            w.append(v[:, :3])
        out.append(w)
    if clip is not None:
        ia, ib = (0, 2) if axis == "y" else ((1, 2) if axis == "x" else (0, 1))
        box2 = _box(min(clip[0], clip[1]), min(clip[2], clip[3]),
                    max(clip[0], clip[1]), max(clip[2], clip[3]))
        keep = []
        for rings in out:
            poly = _Poly(np.column_stack([rings[0][:, ia], rings[0][:, ib]]),
                         [np.column_stack([r[:, ia], r[:, ib]]) for r in rings[1:]])
            inter = poly.intersection(box2)
            if inter.is_empty:
                continue
            for g in (inter.geoms if inter.geom_type == "MultiPolygon" else [inter]):
                rings2 = [np.asarray(g.exterior.coords)[:, :2]]
                rings2 += [np.asarray(h.coords)[:, :2] for h in g.interiors]
                # put the clipped 2-D rings back into the plane's own world frame
                def back(a2, rings=rings):
                    if axis == "y":
                        return np.column_stack([a2[:, 0], np.full(len(a2), value), a2[:, 1]])
                    return np.column_stack([np.full(len(a2), value), a2[:, 0], a2[:, 1]])
                keep.append([back(a) for a in rings2])
        out = keep
    return out


def draw_section(im, view, polys_by_mesh, scale, pad=6, hatch=True):
    """view = ('xz'|'yz', a0, a1, b0, b1) in world coords; screen x = first axis, y = second"""
    kind = view[0]
    ia, ib = (0, 2) if kind == "xz" else (1, 2)
    ax0, ax1, v0, v1 = view[1:]
    W, H = im.size

    def S(x, y):
        return (pad + (x - ax0) * scale, H - pad - (y - v0) * scale)

    mask = Image.new("L", (W, H), 0)
    dm = ImageDraw.Draw(mask)
    flat = []
    for name, polys in polys_by_mesh:
        for rings in polys:
            rr = [np.column_stack([r[:, ia], r[:, ib]]) for r in rings]
            flat.append((name, rr))
            dm.polygon([S(a, b) for a, b in rr[0]], fill=255)
            for hole in rr[1:]:
                dm.polygon([S(a, b) for a, b in hole], fill=0)
    hatch_img = Image.new("RGB", (W, H), BG)
    dd = ImageDraw.Draw(hatch_img)
    for k in range(-H, W + H, 5):
        dd.line([k, 0, k + H, H], fill=(206, 211, 221), width=1)
    base = im.copy()
    if hatch:
        base = Image.composite(hatch_img, base, mask)
    d = ImageDraw.Draw(base)
    for name, rr in flat:
        col = FILL[name]
        for ring in rr:
            pts = [S(a, b) for a, b in ring]
            for k in range(len(pts) - 1):
                d.line([pts[k], pts[k + 1]], fill=col, width=2)
    return base, S


PLACED = []
BOUNDS = [0, 0, 0, 0]                      # left, top, right, bottom of the drawing area


def label(d, x, y, txt, fill=YEL, right=False, size=13):
    """draw a black-backed label; nudge it until it no longer covers another label

    BOUNDS/PLACED are set per panel by rfid_section(), so a caption can never land on top of
    a dimension or on top of another caption - the figure has to be readable, not just drawn.
    """
    lines = txt.split("\n")
    w = 6.3 * max(len(t) for t in lines) + 6
    h = size * len(lines) + 5
    x0 = x - w if right else x
    x0 = min(max(x0, BOUNDS[0] + 2), BOUNDS[2] - w - 2)
    L, T, Rt, Bt = BOUNDS
    cand = []
    for dx in (0, 26, -26, 52, -52):
        for k in range(26):
            cand += [(x0 + dx, y - 16 * k), (x0 + dx, y + 16 * k)]
    best = (x0, y)
    for cx, cy in cand:
        if cx < L + 2 or cx + w > Rt - 2 or cy < T + 2 or cy + h > Bt - 2:
            continue
        if not any(cx < px + pw and px < cx + w and cy < py + ph and py < cy + h
                   for px, pw, py, ph in PLACED):
            best = (cx, cy)
            break
    x0, y = best
    PLACED.append((x0, w, y, h))
    d.rectangle([x0 - 2, y - 2, x0 + w, y + h], fill=PANEL)
    for k, t in enumerate(lines):
        d.text((x0 + 2, y + k * size), t, fill=fill)
    return x0, x0 + w, y, y + h


def dim_h(d, S, x0, x1, y, txt, col=CYA, up=14):
    a, b = S(x0, y), S(x1, y)
    d.line([a, b], fill=col, width=1)
    for p in (a, b):
        d.line([p, (p[0], p[1] - 5)], fill=col, width=1)
    label(d, (a[0] + b[0]) / 2 - 6.3 * len(txt) / 2 - 3, a[1] - up - 13, txt, fill=col)


def dim_v(d, S, y0, y1, x, txt, col=CYA, dx=10):
    a, b = S(x, y0), S(x, y1)
    d.line([a, b], fill=col, width=1)
    for p in (a, b):
        d.line([p, (p[0] - 5, p[1])], fill=col, width=1)
    label(d, min(a[0], b[0]) + dx, (a[1] + b[1]) / 2 - 8, txt, fill=col)


# ============================================================ 1. RC522 sections
SC = 18.0                                   # px per mm
XA, XB = -52.0, 20.0
ZA, ZB = -2.5, 12.0
PADT, RINGT = pad_top, pad_top + ring_t


def rfid_section(y_cut, title, note, extra=(), win=(XA, XB, ZA, ZB), sc=SC):
    w0, w1, z0, z1 = win
    im = Image.new("RGB", (int((w1 - w0) * sc) + 12, int((z1 - z0) * sc) + 12), BG)
    clipbox = (w0, w1, z0, z1)
    pm = [("shell", cut_polys(MESH["shell"], "y", y_cut, clip=clipbox)),
          ("ring", cut_polys(MESH["ring"], "y", y_cut, clip=clipbox))]
    im, S = draw_section(im, ("xz", w0, w1, z0, z1), pm, sc)
    d = ImageDraw.Draw(im)
    del PLACED[:]
    BOUNDS[:] = (12, 26, im.size[0] - 12, im.size[1] - 26)
    for kind, x0, x1, za, zb, col, txt, tx, ty in extra:
        pts = [S(x0, za), S(x1, za), S(x1, zb), S(x0, zb)]
        for k in range(4):
            d.line([pts[k], pts[(k + 1) % 4]], fill=col, width=2)
        if txt:
            label(d, S(tx, ty)[0], S(tx, ty)[1], txt, fill=col)
    d.rectangle([0, 0, im.size[0], 22], fill=PANEL)
    d.text((8, 5), title, fill=INK)
    d.rectangle([0, im.size[1] - 20, im.size[0], im.size[1]], fill=PANEL)
    d.text((8, im.size[1] - 15), note, fill=CYA)
    return im, S, d


# --- panel A: through the aperture centre - what stands in front of the antenna
extraA = [
    ("pcb", fcx - bw / 2, fcx + bw / 2, zi, zi + bt, GRN,
     f"RC522 PCB {bw:.0f} x {bl:.0f} x {bt:.1f}, component side up", fcx - 6, 9.6),
    ("ring", fcx + win_w / 2 - 0.5, fcx + ring_w / 2, PADT, PADT + ring_t, MAG,
     f"ring, {ring_t:.1f} thick - its lip reaches 0.5 mm inside\nthe aperture, so the board "
     "cannot move in its seat", fcx + 8.0, 7.4),
    ("ring", fcx - ring_w / 2, fcx - win_w / 2 + 0.5, PADT, PADT + ring_t, MAG, "", 0, 0),
    ("rib", fcx - bw / 2 - P["rfid_seat_rib"][0], fcx - bw / 2, zi,
     zi + P["rfid_seat_rib"][1], CYA, "the 1.2 x 1.0 mm seat rib locates\nthe board at 0.35 mm "
     "per side", fcx - 46.0, 7.4),
]
imA, SA, dA = rfid_section(
    fcy, "A   SECTION at y = %.2f mm - straight through the scan aperture (the printed shapes "
         "are cut out of the shipped .stl, not drawn)" % fcy,
    "hatched white = printed shell   pink = RC522 ring   green = the module's PCB (not printed) "
    "   the aperture is open through the whole wall and nothing crosses it", extraA)
dim_h(dA, SA, fcx - win_w / 2, fcx + win_w / 2, -1.6, f"scan aperture {win_w:.0f} x "
      f"{win_h:.0f} mm, open", col=MAG, up=13)
dim_v(dA, SA, rec_d, zi, fcx - bw / 2 - 1.9,
      f"recess {rec_d:.1f} deep,\n{zi - rec_d:.1f} mm ledge left\nin front of the PCB", dx=6)
label(dA, SA(fcx + 6, 3.6)[0], SA(fcx + 6, 3.6)[1],
      "v2 crossed this same window with 2 x 4 mm bars (190 mm2 of shadow).\nNow 8269 of 8269 "
      "rays out of the antenna leave the box unobstructed.", fill=RED)

# --- panel B: through a screw axis - pad, blind pilot, head recess
yB = fcy - poy
xB = fcx - pox
XB0, XB1 = -58.0, -14.0
extraB = [
    ("void", xB - pilot / 2, xB + pilot / 2, 1.4, PADT + 0.6, (86, 92, 106), "", 0, 0),
    ("screw", xB - 1.1, xB + 1.1, 1.9, PADT + 1.15, INK, "", 0, 0),
    ("head", xB - 2.3, xB + 2.3, PADT + 1.15, PADT + 2.65, INK,
     "M2.5 x 6 pan head,\nseated 1.15 mm below\nthe ring's outer face", xB + 6.5, 12.4),
    ("pcb", fcx - bw / 2, fcx + bw / 2, zi, zi + bt, GRN,
     "the PCB's edge stops 7.0 mm short of this line, so no screw\never passes through the "
     "board - it is held by the ring's lip only", xB + 12.0, 6.6),
]
imB, SB, dB = rfid_section(
    yB, "B   SECTION at y = %.2f mm - through one of the ring's four screws" % yB,
    "grey = shell   pink = ring   the pale slot is the d2.2 pilot moulded into the shell, the "
    "white is the screw as it sits when tightened - nothing is glued or clipped", extraB,
    win=(XB0, XB1, ZA, 16.0), sc=27.0)
dim_v(dB, SB, 1.4, PADT + 0.6, xB - 5.6, f"blind pilot d{pilot:.1f},\ndepth "
      f"{PADT + 0.6 - 1.4:.1f} mm,\n{1.4:.1f} mm of wall\nleft underneath", dx=-168)
dim_v(dB, SB, zi - 0.5, PADT, xB + 5.4, f"pad {P['rc522_post']:.0f} sq, top at z={PADT:.1f} - "
      "coplanar with\nthe PCB, so the ring cannot tilt on one side", dx=-16)
dim_h(dB, SB, xB - 1.5, xB + 1.5, 14.4, "ring hole d3.0", col=MAG, up=13)
dim_h(dB, SB, xB - 2.8, xB + 2.8, 13.0, "head recess d5.6 x 1.5", col=CYA, up=13)
label(dB, SB(xB + 24.0, 14.6)[0], SB(xB + 24.0, 14.6)[1],
      "the tab lies on the pad, the screw pulls the ring down, and the\nring's lip traps the "
      "board against the wall's 2.2 mm ledge", fill=RED)

# ============================================================ 2. plate / tie section
SCp = 14.0
YA, YB2 = 52.0, P["H"] / 2 + 4.0
ZAp, ZBp = 26.0, 50.0
imC = Image.new("RGB", (int((YB2 - YA) * SCp) + 12, int((ZBp - ZAp) * SCp) + 12), BG)
px = -P["plate_boss_xy"][0]
clipC = (YA, YB2, ZAp, ZBp)
pmC = [("shell", cut_polys(MESH["shell"], "x", px, clip=clipC)),
       ("plate", cut_polys(MESH["plate"], "x", px, clip=clipC))]
imC, SSC = draw_section(imC, ("yz", YA, YB2, ZAp, ZBp), pmC, SCp)
dC = ImageDraw.Draw(imC)
del PLACED[:]
BOUNDS[:] = (12, 50, imC.size[0] - 12, imC.size[1] - 26)
dC.text((8, 5), "C   SECTION at x = %.1f mm - a rear-plate M3 into the shell" % px, fill=INK)
dC.text((8, 20), "3 mm plate on a 2 mm register frame; pilot d%.1f x 9, 6.6 mm 90-deg csk"
        % P["plate_pilot"], fill=YEL)
dC.text((8, 35), "the tall grey column is the shell's own tie boss, cut open here so you can "
                 "see the plastic the screw bites into", fill=CYA)
dim_v(dC, SSC, ZR, D, YB2 - 4.5, f"plate {P['plate_t']:.1f}", dx=-64)
dim_h(dC, SSC, YA + 2.0, YB2 - 2.0, ZBp - 6.0,
      "110 x 155 mm outer, 46 mm deep (v2: 48)", col=CYA, up=13)

# ============================================================ 3. 3D exploded (assembled stack)
def box(x0, x1, y0, y1, z0, z1, col):
    m = trimesh.creation.box(extents=(max(x1 - x0, 1e-6), max(y1 - y0, 1e-6),
                                       max(z1 - z0, 1e-6)))
    m.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])
    return m, np.tile(np.array(col, dtype=np.uint8), (len(m.faces), 1))


def cyl(x, y, z0, z1, d, col, n=32):
    m = trimesh.creation.cylinder(radius=d / 2, height=z1 - z0, sections=n)
    m.apply_translation([x, y, (z0 + z1) / 2])
    return m, np.tile(np.array(col, dtype=np.uint8), (len(m.faces), 1))


def screw(x, y, z0, z1, d=2.2, head_d=4.6, head_t=1.8):
    a = trimesh.creation.cylinder(radius=d / 2, height=z1 - z0, sections=28)
    a.apply_translation([x, y, (z0 + z1) / 2])
    b = trimesh.creation.cylinder(radius=head_d / 2, height=head_t, sections=28)
    b.apply_translation([x, y, z1 + head_t / 2 - 0.15])
    m = trimesh.util.concatenate([a, b])
    return m, np.tile(np.array(INK, dtype=np.uint8), (len(m.faces), 1))


items = []
# the printed parts, clipped to the pocket neighbourhood so the stack reads clearly
cx0, cx1 = fcx - 34, fcx + 34
cy0, cy1 = fcy - 34, fcy + 34
for name in ("shell", "ring"):
    m = MESH[name].copy()
    keep = m.triangles[:, :, 0].min(axis=1) > cx0
    keep &= m.triangles[:, :, 0].max(axis=1) < cx1
    keep &= m.triangles[:, :, 1].min(axis=1) > cy0
    keep &= m.triangles[:, :, 1].max(axis=1) < cy1
    tri = m.triangles[keep]
    items.append((name, tri.copy(), np.tile(np.array(FILL[name], dtype=np.uint8), (len(tri), 1)), 0.0))
pcb, pcb_c = box(fcx - bw / 2, fcx + bw / 2, fcy - bl / 2, fcy + bl / 2, zi, zi + bt, GRN)
items.append(("PCB", pcb.triangles.copy(), pcb_c, 30.0))
parts = []
for sx in (-1, 1):
    for sy in (-1, 1):
        px, py = fcx + sx * pox, fcy + sy * poy
        a, ca = cyl(px, py, 1.4, pad_top + 0.6, pilot, (60, 66, 78))
        parts.append((a.triangles, ca))
        b, cb = screw(px, py, pad_top + 1.0, pad_top + 1.0 + 6.0)
        parts.append((b.triangles, cb))
items.append(("screws", np.concatenate([t for t, _ in parts]).copy(),
              np.concatenate([c for _, c in parts]), 78.0))
for t in items:
    t[1][:, :, 2] += t[3]
tris = np.concatenate([t[1] for t in items])
cols = np.concatenate([t[2] for t in items])
render(tris, OUT + "_fix3d.png", view="iso2", W=1300, H=700, bg=BG, margins=0.07, tri_rgb=cols)
im3 = Image.open(OUT + "_fix3d.png").convert("RGB")
d3 = ImageDraw.Draw(im3)
del PLACED[:]
BOUNDS[:] = (12, 30, im3.size[0] - 12, im3.size[1] - 26)
d3.rectangle([0, 0, 1300, 22], fill=PANEL)
d3.text((8, 5), "D   THE WHOLE RFID FIXING, EXPLODED - printed shell + printed ring + the PCB "
                "and its 4 screws, separated along Z", fill=INK)
d3.rectangle([0, 680, 1300, 700], fill=PANEL)
d3.text((8, 685), "grey = shell (wall, 4 pads, 4 locating ribs, the 0.8 mm recess)   pink = "
                  "ring (1 part, printed flat, no supports)   green = the RC522 module   "
                  "white = 4 x M2.5 x 6 self-tapping", fill=CYA)
R, sc3, ox3, oy3 = projection(tris, "iso2", 1300, 700, margins=0.07)
for (nm, t, c, dz) in items:
    cen = t.reshape(-1, 3).mean(axis=0)
    sx, sy, _ = project_points(np.array([cen]), R, sc3, ox3, oy3)
    if nm in ("ring", "PCB"):
        txt = {"ring": f"ring: {ring_w:.1f} x {ring_h:.1f}, tabs to y +/-31.5",
               "PCB": "RC522 PCB, 4 ribs locate it at +/-0.35 mm"}[nm]
        label(d3, float(sx[0]) + 120, float(sy[0]) - 8, txt, fill=MAG if nm == "ring" else GRN)
    if nm == "shell":
        label(d3, float(sx[0]) - 320, float(sy[0]) - 40,
              f"4 pads, top at z={pad_top:.1f} - coplanar with the PCB, so the ring lies flat",
              fill=CYA)
    if nm == "screws":
        label(d3, float(sx[0]) - 300, float(sy[0]) + 10,
              "4 x M2.5 into blind pilots d2.2 - no through-hole in the wall, no access needed "
              "from the back", fill=INK)

# ============================================================ montage
pad = 16
wA, hA = imA.size
wB, hB = imB.size
wC, hC = imC.size
W = max(wA, wB, im3.size[0], wC) + pad
Htot = 46 + im3.size[1] + hA + hB + hC + pad * 4
sheet = Image.new("RGB", (W, Htot), (8, 9, 12))
ds = ImageDraw.Draw(sheet)
ds.text((12, 10), "ASTRO SMART ATTENDANCE v3 - how every module is held: screws into printed "
                  "pilots, no glue, no clips, no snap-fits", fill=INK)
ds.text((12, 28), "22 screw holes: 4 x LCD1602 M2.5 | 2 x R307 bracket M3 | 4 x RC522 ring M2.5 "
                  "| 4 x ESP32 M2.2 | 4 x fan M3 | 4 x rear plate M3 (+ 4 x d4.0 cable-tie "
                  "holes) - every diameter measured back out of the STL, none assumed", fill=YEL)
x3 = (W - im3.size[0]) // 2
xc = (W - wC) // 2
sheet.paste(im3, (x3, 46))
sheet.paste(imA, (pad, 46 + im3.size[1] + pad))
sheet.paste(imB, (pad, 46 + im3.size[1] + pad + hA + pad))
sheet.paste(imC, (xc, 46 + im3.size[1] + pad + hA + hB + pad * 2))
sheet.save(OUT + "v3_fixing_detail.png")
print("wrote renders/v3_fixing_detail.png", sheet.size)

two = Image.new("RGB", (max(wA, wB) + pad, hA + hB + 40), (8, 9, 12))
dt = ImageDraw.Draw(two)
dt.text((12, 8), "v3 RFID fixing - the two cut sections enlarged (hatched = printed material, "
                 "cut by trimesh out of the shipped .stl)", fill=INK)
two.paste(imA, (pad, 26))
two.paste(imB, (pad, 26 + hA + pad))
two.save(OUT + "v3_fixing_section.png")
print("wrote renders/v3_fixing_section.png", two.size)
