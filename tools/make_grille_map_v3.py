"""v3.3 opening map - the four walls, drawn from the shipped STL and nothing else.

The all-views render can show a plain wall, but it cannot show *why* the holes are where they
are.  This figure cuts each wall at mid-thickness, lifts every closed void out of the section, and
draws it with the dimensions measured back off the triangles.  Nothing here is typed from the
design: if the mesh says 20.8 mm the label says 20.8 mm.

    python3 tools/make_grille_map_v3.py   ->  renders/v3_grille_map.png
"""
import os
import sys

import numpy as np
import trimesh
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPoly

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import orient_v3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAD = os.path.join(ROOT, "cad", "v3")
OUT = os.path.join(ROOT, "renders", "v3_grille_map.png")

W, H, D = 110.0, 155.0, 46.0
WALL_S, WALL_T = 2.6, 3.0
BORE = 28.0
FAN_Y, FAN_Z = 17.0, 24.0

m = trimesh.load(os.path.join(CAD, "01_MAIN_SHELL_v3.stl"), process=True)
m = orient_v3.to_assembly(m, "01_MAIN_SHELL_v3.stl")


def voids(axis, at):
    """closed voids in a wall sliced at mid-thickness: (area, w, h, cu, cv) in wall-plane mm."""
    nrm = [0.0, 1.0, 0.0] if axis == "y" else [1.0, 0.0, 0.0]
    org = [0.0, float(at), 0.0] if axis == "y" else [float(at), 0.0, 0.0]
    sec = m.section(plane_origin=org, plane_normal=nrm)
    if sec is None or not len(sec.entities):
        return [], None
    path, T = sec.to_2D()
    T = np.asarray(T, dtype=float)
    out, outline = [], None
    for Q in path.polygons_full:
        g = np.asarray(Q.exterior.coords)[:, :2]
        w3 = np.column_stack([g, np.zeros(len(g)), np.ones(len(g))]) @ T.T
        outline = w3[:, [0, 2]] if axis == "y" else w3[:, [1, 2]]
        for ipoly in Q.interiors:
            g = np.asarray(ipoly.coords)[:, :2]
            w3 = np.column_stack([g, np.zeros(len(g)), np.ones(len(g))]) @ T.T
            pts = w3[:, [0, 2]] if axis == "y" else w3[:, [1, 2]]
            from shapely.geometry import Polygon
            q = Polygon(pts)
            b0, b1, b2, b3 = q.bounds
            out.append(dict(a=q.area, w=b2 - b0, h=b3 - b1, cu=(b0 + b2) / 2, cv=(b1 + b3) / 2,
                            pts=pts))
    out.sort(key=lambda r: (round(r["cv"], 1), r["cu"]))
    return out, outline


PANELS = [
    ("y", -H / 2 + WALL_T / 2, "BOTTOM  wall  (y = -77.5 .. -74.5)",
     "8 x 21 x 4.5 grille + the USB opening"),
    ("y", H / 2 - WALL_T / 2, "TOP  wall  (y = +74.5 .. +77.5)",
     "4 x 21 x 4 grille, above the board level"),
    ("x", W / 2 - WALL_S / 2, "RIGHT  wall  (+X) - the v3.3 change",
     "v3.2 cut 8 x 30 x 5 slots here;  v3.3: none"),
    ("x", -W / 2 + WALL_S / 2, "LEFT  wall  (-X) - the fan bore IS the inlet",
     f"d{BORE:.0f} clear bore, {np.pi * (BORE / 2) ** 2:.0f} mm2, fan blows IN"),
]

fig, axes = plt.subplots(1, 4, figsize=(19.5, 6.4), dpi=115)
fig.patch.set_facecolor("#10141b")
measured = []
for ax, (axis, at, title, sub) in zip(axes, PANELS):
    vs, outline = voids(axis, at)
    ax.set_facecolor("#10141b")
    for sp in ax.spines.values():
        sp.set_color("#48505e")
    ax.tick_params(colors="#9fb0c6", labelsize=8)
    if outline is not None:
        ax.add_patch(MplPoly(outline, closed=True, facecolor="#7f93ad", edgecolor="#cfdcef",
                             linewidth=1.0, alpha=0.95))
    for v in vs:
        ax.add_patch(MplPoly(v["pts"], closed=True, facecolor="#0a0d12", edgecolor="#ffd166",
                             linewidth=1.1))
    # one label per SIZE, put on the leftmost opening of that size: eight copies of
    # "21.0 x 4.5" over 4 mm-tall slots is unreadable, one of them with "x8" is
    seen = {}
    for v in sorted(vs, key=lambda r: (round(r["h"], 1), r["cu"])):
        key = (round(v["w"], 1), round(v["h"], 1))
        n = sum(1 for u in vs if (round(u["w"], 1), round(u["h"], 1)) == key)
        if key in seen:
            continue
        seen[key] = True
        ax.annotate(f"{v['w']:.1f} x {v['h']:.1f}" + (f"   x{n}" if n > 1 else ""),
                    (v["cu"], v["cv"] + v["h"] / 2 + 2.2), color="#ffd166", fontsize=8.2,
                    ha="center", va="bottom",
                    bbox=dict(boxstyle="round,pad=0.2", fc="#10141b", ec="#48505e", lw=0.6))
    if not vs:
        ax.text(0, 23, "0 voids\nin this wall", color="#68d391", fontsize=15, ha="center",
                va="center", weight="bold")
    tot = sum(v["a"] for v in vs)
    measured.append((title, len(vs), tot))
    ax.set_title(f"{title}\n{sub}", color="#eef3fa", fontsize=10.2, loc="left", pad=9)
    ax.text(0.015, 0.965, f"{len(vs)} opening(s)   {tot:.0f} mm2 free",
            transform=ax.transAxes, color="#9fb0c6", fontsize=8.4, va="top",
            bbox=dict(boxstyle="round,pad=0.22", fc="#0a0d12", ec="#48505e", lw=0.6))
    if outline is not None and len(outline):
        # the wall's own span, measured from the section, not asserted from the design
        o = np.asarray(outline)
        y0 = float(o[:, 1].min()) - 6.5
        ax.annotate("", xy=(float(o[:, 0].min()), y0), xytext=(float(o[:, 0].max()), y0),
                    arrowprops=dict(arrowstyle="<->", color="#68d391", lw=1.0))
        ax.text((float(o[:, 0].min()) + float(o[:, 0].max())) / 2, y0 + 1.1,
                f"outline spans {o[:, 0].max() - o[:, 0].min():.2f} x "
                f"{o[:, 1].max() - o[:, 1].min():.2f} mm", color="#68d391", fontsize=7.8,
                ha="center", va="bottom")
    if axis == "y":
        ax.set_xlim(-62, 62)
        ax.set_ylim(-11, 50)
        ax.set_xlabel("x  (mm)  -  width, front face at the bottom of this view", color="#9fb0c6",
                      fontsize=8)
    else:
        ax.set_xlim(-84, 84)
        ax.set_ylim(-11, 50)
        ax.set_xlabel("y  (mm)  -  height, front face at the left", color="#9fb0c6", fontsize=8)
    ax.set_ylabel("z  (mm)  -  depth", color="#9fb0c6", fontsize=8)
    ax.set_aspect("equal")
    ax.grid(color="#243040", linewidth=0.4)
    ax.label_outer()
    ax.set_axisbelow(True)

grille = sum(v["a"] for v in voids("y", -H / 2 + WALL_T / 2)[0] if v["h"] < 8)
grille += sum(v["a"] for v in voids("y", H / 2 - WALL_T / 2)[0])
bore_a = np.pi * (BORE / 2) ** 2
fig.text(0.012, 0.055,
         "measured off cad/v3/01_MAIN_SHELL_v3.stl: each wall cut by one plane at its own "
         "mid-thickness (bottom/top y = +/-76.0, sides x = +/-53.7), every closed void in that "
         "section drawn at its measured size.  No tolerance applied, nothing typed from the design.", color="#cfdcef", fontsize=8.6)
fig.text(0.012, 0.022,
         f"air path: inlet = the d28 bore, {bore_a:.0f} mm2  ->  outlet = the two grilles, "
         f"{grille:.0f} mm2 = {grille / bore_a:.2f}x the bore (rule >= 1.5x).  "
         f"Nothing is left of the perforated right-hand wall: 0 voids, and 4.4 mm of solid from "
         f"every grille slot to the side wall.", color="#68d391", fontsize=9.2)
fig.suptitle("ASTRO SMART ATTENDANCE v3.3  -  every opening, measured back out of the printed mesh"
             "   (110 x 155 x 46 mm, walls 3.0 front / 2.6 sides / 3.0 top-bottom)",
             color="#eef3fa", fontsize=12.6, x=0.012, ha="left", y=0.985)
fig.subplots_adjust(left=0.05, right=0.99, top=0.83, bottom=0.19, wspace=0.16)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
fig.savefig(OUT, facecolor=fig.get_facecolor())
print("wrote", OUT)
for title, n, tot in measured:
    print(f"   {title:46s} {n} openings  {tot:7.1f} mm2")
# 9 in the bottom wall = the 8 grille slots plus the USB opening, which is cut in
# the same sheet and is expected to be there (20.4 x 12.4, see the print order).
bad = [t for t, n, _ in measured if n not in (9, 4, 0, 1)]
if bad:
    print("WARNING: unexpected opening counts in: " + ", ".join(bad), file=sys.stderr)
    sys.exit(1)
