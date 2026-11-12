"""Detect openings (holes) in each principal face of a part.

Rasterises all triangles lying on the outermost plane of each of the 6 principal
faces, then finds uncovered connected regions inside the face outline.
"""
import sys
sys.path.insert(0, "/home/user/astro-smart-attendance/tools")
import numpy as np
from PIL import Image, ImageDraw
from stl_tools import load_stl, compute_normals

RES = 0.1  # mm per pixel


def face_mask(tri, axis, sign, plane_tol=0.15, pad=1.0):
    """mask + extent of the outermost planar face perpendicular to `axis`."""
    n = compute_normals(tri)
    amp = np.abs(n[:, axis])
    sel = (amp > 0.999) & (np.sign(n[:, axis]) == sign)
    if sel.sum() == 0:
        return None
    t = tri[sel]
    coords = t[:, :, axis]
    # outermost plane among selected
    plane = coords.mean(axis=1)
    outer = plane.max() if sign > 0 else plane.min()
    keep = np.abs(plane - outer) < plane_tol
    t = t[keep]
    if len(t) == 0:
        return None
    others = [i for i in range(3) if i != axis]
    pts = t.reshape(-1, 3)[:, others]
    lo = pts.min(axis=0) - pad
    hi = pts.max(axis=0) + pad
    W = int(np.ceil((hi[0] - lo[0]) / RES)) + 1
    H = int(np.ceil((hi[1] - lo[1]) / RES)) + 1
    img = Image.new("1", (W, H), 1)
    d = ImageDraw.Draw(img)
    for f in t:
        p = f[:, others]
        poly = [((p[k, 0] - lo[0]) / RES, (p[k, 1] - lo[1]) / RES) for k in range(3)]
        d.polygon(poly, fill=0)
    m = np.array(img, dtype=bool)  # True = uncovered
    return dict(mask=m, lo=lo, hi=hi, plane=outer, outer_axis=axis, others=others)


def components(mask):
    """simple 4-connected labelling"""
    H, W = mask.shape
    lab = np.zeros((H, W), np.int32)
    cur = 0
    stack = []
    for y in range(H):
        for x in range(W):
            if mask[y, x] and lab[y, x] == 0:
                cur += 1
                stack = [(y, x)]
                lab[y, x] = cur
                while stack:
                    cy, cx = stack.pop()
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < H and 0 <= nx < W and mask[ny, nx] and lab[ny, nx] == 0:
                            lab[ny, nx] = cur
                            stack.append((ny, nx))
    return lab, cur


def report(path):
    tri, _ = load_stl(path)
    print(f"\n=== {path}")
    verts = tri.reshape(-1, 3)
    print("  overall bbox:", verts.min(axis=0).round(2), "->", verts.max(axis=0).round(2))
    for axis in range(3):
        for sign in (1, -1):
            f = face_mask(tri, axis, sign)
            if f is None:
                continue
            lab, n = components(f["mask"])
            others = f["others"]
            an = "XYZ"
            print(f"  --- face {'+' if sign>0 else '-'}{an[axis]}  (plane {an[axis]}={f['plane']:.2f})  extent "
                  f"{f['lo'][0]:.1f}..{f['hi'][0]:.1f} x {f['lo'][1]:.1f}..{f['hi'][1]:.1f} "
                  f"({an[others[0]]} x {an[others[1]]})")
            for c in range(1, n + 1):
                ys, xs = np.nonzero(lab == c)
                area = len(ys) * RES * RES
                x0 = xs.min() * RES + f["lo"][0]
                x1 = xs.max() * RES + f["lo"][0]
                y0 = ys.min() * RES + f["lo"][1]
                y1 = ys.max() * RES + f["lo"][1]
                touches_border = (xs.min() == 0 or ys.min() == 0 or
                                  xs.max() == f["mask"].shape[1] - 1 or
                                  ys.max() == f["mask"].shape[0] - 1)
                if area < 0.05:
                    continue
                kind = "EDGE(open boundary)" if touches_border else "HOLE"
                print(f"      {kind:20s} {an[others[0]]} {x0:8.2f}..{x1:8.2f}  {an[others[1]]} {y0:8.2f}..{y1:8.2f}"
                      f"  size {(x1-x0):6.2f} x {(y1-y0):6.2f} mm  area {area/100:6.2f} cm^2")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        report(p)
