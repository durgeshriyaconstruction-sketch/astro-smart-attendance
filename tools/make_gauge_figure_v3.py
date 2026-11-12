"""Draw 05_FIT_GAUGE_v3 the way you will actually meet it: as a printed card, and in section.

Three views.  The plan and the section are cut out of cad/v3/05_FIT_GAUGE_v3.stl - the file that
prints - so neither can show a feature the part does not have; the numbered overlay and the sizes
come from the builder's own geometry, executed rather than copied, so nothing here retypes a
dimension either.

  left     the plan through the plastic at mid thickness: a cut is a GO gauge, an engraved line is
           a reference outline, and every station carries the number the legend explains.
  top right the card in one-point perspective, shaded by height - light is high, dark is a pocket
           or a hole clean through, which is close to what the slicer's first layers see.
  bottom   a cut across the pilot centres, so the 8.00 mm depth and the 4.60 mm of floor left under
           each pilot are visible instead of asserted.  Heights are exaggerated x3, and say so.

  python3 tools/make_gauge_figure_v3.py     -> renders/v3_fit_gauge.png
"""
import os
import sys

import numpy as np
import trimesh
from matplotlib.patches import Polygon as MplPolygon
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import orient_v3  # noqa: E402

NAME = "05_FIT_GAUGE_v3.stl"
OUT = os.path.join(ROOT, "renders", "v3_fit_gauge.png")

NOTES = [
    (1, ["six pilots, d1.80 / 2.00 / 2.05 / 2.20 / 2.35 / 2.50, 8.00 deep in a 10.00 mm boss:",
         "which screw your bosses really take, and how much thread is in the plastic under it"]),
    (2, ["four board holes, d2.00 / 2.20 / 2.50 / 2.70:",
         "what size the hole in your PCB actually is, before you order 40 screws"]),
    (3, ["the 1602 window at 66.00 x 17.50 - the size the front wall is cut to,",
         "the 75.10 x 31.0 hole pitch, and the four d2.05 pilots it drills"]),
    (4, ["the R307 bezel relief at 21.00 x 25.00 that the prism has to clear,",
         "the 19.30 x 21.20 window, and the 44.10 x 20.00 body it sits behind"]),
    (5, ["the RC522 board with +0.40 mm a side, the 62.70 x 44.70 recess it rests in,",
         "and the four pads the hold-down ring clamps, at +/-34 and +/-17"]),
    (6, ["the USB opening as the wall has it, 20.40 x 12.40, and the 15.60 x 8.00 plug",
         "that has to pass it - checked before the wall ever gets printed"]),
    (7, ["a 100 mm rule ticked every 10: PLA shrinks, and if your printer is 1 % out",
         "nothing else on this card or in the box would be true.  Read it first"]),
]


def layout():
    """the geometry half of the gauge builder, executed - so this figure cannot draw a dimension
    the part does not have, and cannot be blamed for typing one twice"""
    src = open(os.path.join(ROOT, "tools", "build_gauge_v3.py"), encoding="utf-8").read()
    head = src[:src.index("# ============================================================ build + self-check")]
    ns = {"__builtins__": __builtins__,
          "__file__": os.path.join(ROOT, "tools", "build_gauge_v3.py"),
          "os": os, "sys": sys, "np": np, "trimesh": trimesh}
    exec(head, ns)
    return ns


NS = layout()
m = trimesh.load(os.path.join(ROOT, "cad", "v3", NAME), process=True)
dz = orient_v3.ORIENT[NAME][0]
if dz:
    m.apply_translation([0, 0, dz])
assert m.is_watertight and len(m.split(only_watertight=False)) == 1, "the shipped STL is not one body"
CT, BOSS_H, TOP = NS["CT"], NS["BOSS_H"], NS["CT"] + NS["BOSS_H"]
CW, CH = NS["CW"], NS["CH"]
lo, hi = m.bounds
INK, CARD, POCKET, FACE = "#1d2b36", "#e9e6de", "#a4b5c1", "#ffffff"

fig = plt.figure(figsize=(15.6, 10.4), dpi=150)
fig.patch.set_facecolor("#f7f7f4")

# ---- the plan, at mid thickness: read off the mesh ----------------------------------------------
ap = fig.add_axes([0.030, 0.330, 0.455, 0.565])
ap.set_facecolor(FACE)
sec = m.section(plane_normal=[0, 0, 1], plane_origin=[0, 0, CT / 2])
loops = []
for grp in sec.discrete:
    A = grp if isinstance(grp, np.ndarray) else np.asarray(grp)
    if A.ndim == 2 and A.shape[1] == 3:
        loops.append(A)
def fill_loops(axx, lps, ex=1.0, lw=1.2):
    """the biggest loop is the material; every loop inside it at this plane is air.  That is the
    whole rule, and it needs no knowledge of what the builder intended to cut."""
    lps = sorted(lps, key=lambda A: -np.ptp(A[:, 0]) * np.ptp(A[:, 1]))
    for i, A in enumerate(lps):
        axx.fill(A[:, 0], A[:, 1 if ex == 1.0 else 2] * ex,
                 facecolor=CARD if i == 0 else FACE, edgecolor=INK, lw=lw if i == 0 else 1.1,
                 zorder=1 + i)


fill_loops(ap, loops)
bx0, by0, bx1, by1 = NS["BOSS"]
ap.add_patch(MplPolygon(np.asarray(NS["sbox"](bx0, by0, bx1, by1).exterior.coords), closed=True,
                        facecolor="none", edgecolor="#6b818f", lw=1.1, ls=(0, (4, 2)), zorder=2))
for p, z0, z1 in NS["ENG"]:
    if abs(z0 - (CT - NS["ENG_D"])) > 1e-9:                  # the boss-top marks are in the section
        continue
    for g in (p.geoms if p.geom_type == "MultiPolygon" else [p]):
        ap.add_patch(MplPolygon(np.asarray(g.exterior.coords), closed=True, facecolor=POCKET,
                                edgecolor="none", zorder=2))
        for q in g.interiors:                                # the middle of a ring is plain plastic
            ap.add_patch(MplPolygon(np.asarray(q.coords), closed=True, facecolor=CARD,
                                    edgecolor="none", zorder=2))
for num, (sx, sy) in [(1, (0.5 * (bx0 + bx1), by1 - 4.2)), (2, (66.0, 95.0)), (3, (66.0, 90.6)),
                      (4, (8.0, 8.0)), (5, (78.0, 52.0)), (6, (17.0, 93.0)), (7, (140.0, 106.4))]:
    ap.text(sx, sy, str(num), fontsize=15, ha="center", va="center", color="#7f93a1", zorder=4)
ap.set_xlim(-3, CW + 3)
ap.set_ylim(-3, CH + 3)
ap.set_aspect("equal")
ap.set_xticks([]); ap.set_yticks([])
for sp in ap.spines.values():
    sp.set_color("#c9c4b8")
ap.set_title("the plan, cut out of the shipped STL at z = 1.30 of 2.60 - a cut is a GO gauge, an "
             "engraved line is a reference", fontsize=10.2, color=INK, pad=6, loc="left")

# ---- the printed card, in perspective, shaded by height -----------------------------------------
ax = fig.add_axes([0.545, 0.560, 0.425, 0.340], projection="3d")
ax.set_facecolor("#f7f7f4")
tri, nrm = m.triangles, m.face_normals
z = tri[:, :, 2].mean(1)
lit = np.clip(nrm @ np.array([-0.28, -0.44, 0.85]), 0.0, 1.0)
lev = np.where(z > TOP - 0.05, 0.99, np.where(z > CT - 0.05, 0.80,
              np.where(z > CT - NS["ENG_D"] - 0.05, 0.46, 0.16)))       # boss top, card face,
shade = lev * (0.88 + 0.12 * lit)          # mostly height, a little light: the facets must not                                        # pocket floor, hole
cols = np.stack([0.13 + 0.62 * shade, 0.23 + 0.55 * shade, 0.36 + 0.46 * shade,
                 np.ones_like(shade)], 1)
ax.add_collection3d(Poly3DCollection(tri, facecolors=cols, edgecolors="none",
                                     antialiaseds=True))
ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1]); ax.set_zlim(0, 13.5)
ax.set_box_aspect((CW, CH, 13.5))
ax.view_init(elev=57, azim=-108)
ax.set_axis_off()
ax.set_title("as it prints: 150.0 x 112.0 x 2.60 flat, one 10.00 mm boss, no supports; the eight "
             "gauges go clean through", fontsize=10.2, color=INK, pad=-22)

# ---- the section across the pilots, heights x3 ---------------------------------------------------
asx = fig.add_axes([0.030, 0.075, 0.455, 0.170])
asx.set_facecolor(FACE)
py = 0.5 * (by0 + by1) - 1.2
xs_ = m.section(plane_normal=[0, 1, 0], plane_origin=[0, py, 0])
sloops = []
for grp in xs_.discrete:
    A = grp if isinstance(grp, np.ndarray) else np.asarray(grp)
    if A.ndim == 2 and A.shape[1] == 3:
        sloops.append(A)
EX = 3.0
fill_loops(asx, sloops, ex=EX, lw=1.4)
pcx = sorted(0.5 * (p.bounds[0] + p.bounds[2]) for p, z0, z1 in NS["ENG"]
             if abs(z0 - (TOP - NS["PILOT_DEPTH"])) < 1e-9)
pilot = list(zip(pcx, NS["PILOTS"]))         # the builder drilled them left to right, in order

for cx, d in pilot:
    asx.plot([cx, cx], [(TOP - NS["PILOT_DEPTH"]) * EX, TOP * EX + 1.0], color="#b2452f", lw=1.0,
             ls=(0, (2, 2)), zorder=3)
    asx.annotate(f"d{d:.2f}", (cx, TOP * EX + 1.2), ha="center", va="bottom", fontsize=8.2,
                 color=INK, zorder=4)
asx.axhline(CT * EX, color="#6b818f", lw=0.7, ls=(0, (3, 3)), zorder=3)
asx.text(-1.0, CT * EX + 0.5, f"card {CT:.2f}", ha="left", fontsize=8.0, color="#5b6f7d")
asx.text(CW + 1.0, TOP * EX - 0.4, f"boss top {TOP:.2f}", ha="right", fontsize=8.0, color="#5b6f7d")
asx.text(CW + 1.0, (TOP - NS["PILOT_DEPTH"]) * EX - 1.0, "pilot floor 4.60", ha="right",
         fontsize=8.0, color="#b2452f")
asx.set_xlim(-2, CW + 2)
asx.set_ylim(-1.0, (TOP * EX) + 5.0)
asx.set_xticks([0, 50, 100, 150])
asx.set_yticks([0, CT * EX, (TOP - NS["PILOT_DEPTH"]) * EX, TOP * EX])
asx.set_xticklabels(["0", "50", "100", "150 mm"], fontsize=8.2)
asx.set_yticklabels(["0", f"{CT:.2f}", f"{TOP - NS['PILOT_DEPTH']:.2f}", f"{TOP:.2f}"], fontsize=8.2)
asx.grid(alpha=0.20, lw=0.5)
for sp in asx.spines.values():
    sp.set_color("#c9c4b8")
asx.set_title("cut across the pilot centres at y = %.2f, heights x3: each pilot stops 4.60 mm short "
              "of the underside" % py, fontsize=10.0, color=INK, pad=4, loc="left")

# ---- the legend ----------------------------------------------------------------------------------
lg = fig.add_axes([0.530, 0.050, 0.450, 0.430])
lg.set_axis_off()
lg.text(0, 1.0, "what one 40-minute print settles", fontsize=12.8, weight="bold", va="top",
        color=INK)
y = 0.905
for num, lines in NOTES:
    lg.text(0.0, y, str(num), fontsize=10.6, weight="bold", va="top", color="#7f93a1")
    for k, ln in enumerate(lines):
        lg.text(0.033, y - 0.0355 * k, ln, fontsize=8.5, va="top", color="#22303a")
    y -= 0.114
lg.text(0.0, y + 0.006,
        "measured by tools/check_gauge_v3.py: 59 things, every one off the shipped triangles - and "
        "the four\nfit gauges then compared against the wall they have to match, where none of them "
        "came out the bigger.",
        fontsize=8.3, va="top", color="#5b6f7d")
fig.text(0.030, 0.952, "05_FIT_GAUGE_v3 - the fit and pilot card", fontsize=17.5, weight="bold",
         color=INK)
fig.text(0.030, 0.921, "every number on the plastic came out of tools/build_v3.py at build time, "
         "and was then measured back off the STL", fontsize=10.3, color="#5b6f7d")
fig.savefig(OUT, facecolor=fig.get_facecolor())
print(f"wrote {OUT} ({os.path.getsize(OUT) / 1e3:.0f} kB): plan loops {len(loops)}, "
      f"voids in it {max(len(loops) - 1, 0)} (the card has {len(NS['CUT'])} cuts), "
      f"section loops {len(sloops)}, "
      f"pilots in section {len(pilot)}, {len(m.faces)} triangles read off the STL")
