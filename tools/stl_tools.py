"""Minimal STL reader + analysis + software renderer (no external deps beyond numpy/PIL).

Usage:
  python3 stl_tools.py info  <file.stl> [...]
  python3 stl_tools.py render <file.stl> <out.png> [--view|--top|--front|--side|--all]
"""
import struct
import sys
import math

import numpy as np
from PIL import Image, ImageDraw


# ---------------------------------------------------------------- loading
def load_stl(path):
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:5].lower() == b"solid" and b"facet" in data[:512]:
        return _load_ascii(data)
    return _load_binary(data)


def _load_binary(data):
    n = struct.unpack("<I", data[80:84])[0]
    expect = 84 + n * 50
    if len(data) < expect:
        raise ValueError(f"binary STL truncated: {len(data)} < {expect}")
    rec = np.frombuffer(data, dtype=np.uint8, count=n * 50, offset=84).reshape(n, 50)
    tri = rec[:, 12:48].copy().view("<f4").reshape(n, 3, 3).astype(np.float64)
    normals = rec[:, 0:12].copy().view("<f4").reshape(n, 3).astype(np.float64)
    return tri, normals


def _load_ascii(data):
    tris = []
    cur = []
    for line in data.decode("utf-8", "ignore").splitlines():
        parts = line.split()
        if len(parts) == 4 and parts[0] == "vertex":
            cur.append([float(x) for x in parts[1:]])
            if len(cur) == 3:
                tris.append(cur)
                cur = []
    tri = np.array(tris, dtype=np.float64)
    n = compute_normals(tri)
    return tri, n


def compute_normals(tri):
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    ln[ln == 0] = 1
    return n / ln


# ---------------------------------------------------------------- analysis
def analyse(tri):
    verts = tri.reshape(-1, 3)
    lo = verts.min(axis=0)
    hi = verts.max(axis=0)
    size = hi - lo
    # unique vertex count (rounded to 1e-4 mm)
    key = np.round(verts, 4)
    uniq, inverse = np.unique(key, axis=0, return_inverse=True)
    faces = inverse.reshape(-1, 3)
    # area + signed volume
    a = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    area = np.linalg.norm(a, axis=1).sum() / 2.0
    vol = np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6.0
    # watertight-ish check: every edge used exactly twice
    edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    edges = np.sort(edges, axis=1)
    _, counts = np.unique(edges, axis=0, return_counts=True)
    bad = int((counts != 2).sum())
    # flat-plate detection: how much volume of the bbox is used
    return dict(tris=len(tri), verts=len(uniq), size=size, lo=lo, hi=hi,
                area=area, volume=abs(vol), open_edges=bad)


def bbox_table(lo, hi, size):
    names = "XYZ"
    out = []
    for i in range(3):
        out.append(f"  {names[i]}: {lo[i]:9.2f} .. {hi[i]:9.2f}   ({size[i]:7.2f} mm)")
    return "\n".join(out)


# ---------------------------------------------------------------- render
def _rot_matrix(view):
    if view == "iso":
        yaw, pitch = math.radians(35), math.radians(28)
    elif view == "iso2":
        yaw, pitch = math.radians(-140), math.radians(25)
    elif view == "front":
        yaw, pitch = math.radians(0), math.radians(0)
    elif view == "side":
        yaw, pitch = math.radians(90), math.radians(0)
    elif view == "top":
        yaw, pitch = math.radians(0), math.radians(90)
    elif view == "back":          # look at the +Z face from outside
        yaw, pitch = math.radians(180), math.radians(0)
    elif view == "front2":        # look at the -Z (device front) face
        yaw, pitch = math.radians(180), math.radians(0)
    elif isinstance(view, tuple):
        yaw, pitch = math.radians(view[0]), math.radians(view[1])
    else:
        yaw, pitch = math.radians(0), math.radians(0)
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    return rx @ ry


def projection(tri, view, W, H, margins=0.06):
    """returns (R, sx, sy, depth, scale, ox, oy, lo, hi) for a given view"""
    R = _rot_matrix(view)
    pts = tri.reshape(-1, 3) @ R.T
    lo = pts.min(axis=0)
    hi = pts.max(axis=0)
    span = np.where(hi - lo < 1e-9, 1.0, hi - lo)
    scale = min(W * (1 - 2 * margins) / span[0], H * (1 - 2 * margins) / span[1])
    ox = W / 2 - (lo[0] + hi[0]) / 2 * scale
    oy = H / 2 + (lo[1] + hi[1]) / 2 * scale
    return R, scale, ox, oy


def project_points(pts, R, scale, ox, oy):
    q = np.asarray(pts, dtype=np.float64).reshape(-1, 3) @ R.T
    return q[:, 0] * scale + ox, oy - q[:, 1] * scale, q[:, 2]


def render(tri, out_png, view="iso", W=1000, H=750, bg=(24, 26, 32),
           colors=((150, 200, 235),), wire=False, margins=0.06, tri_rgb=None,
           label=None):
    """Painter's algorithm z-buffer-free triangle rasteriser with simple shading."""
    R = _rot_matrix(view)
    pts = tri.reshape(-1, 3) @ R.T
    x, y, z = pts[:, 0].reshape(-1, 3), pts[:, 1].reshape(-1, 3), pts[:, 2].reshape(-1, 3)
    lo = pts.min(axis=0)
    hi = pts.max(axis=0)
    span = np.where(hi - lo < 1e-9, 1.0, hi - lo)
    scale = min(W * (1 - 2 * margins) / span[0], H * (1 - 2 * margins) / span[1])
    ox = W / 2 - (lo[0] + hi[0]) / 2 * scale
    oy = H / 2 + (lo[1] + hi[1]) / 2 * scale
    sx = x * scale + ox
    sy = oy - y * scale

    img = np.zeros((H, W, 3), dtype=np.uint8)
    img[:, :] = bg
    zbuf = np.full((H, W), -1e18)

    # camera looks along -Z of rotated space; depth = z of rotated point (bigger = closer)
    nrm = compute_normals(tri) @ R.T  # view-space normals
    shade_dir = np.array([-0.35, 0.55, 0.75])
    shade_dir = shade_dir / np.linalg.norm(shade_dir)
    lam = np.abs(nrm @ shade_dir)
    lam = 0.22 + 0.78 * lam

    order = np.argsort(((z[:, 0] + z[:, 1] + z[:, 2]) / 3.0))
    if tri_rgb is not None:
        assert len(tri_rgb) == len(tri), "tri_rgb must have one RGB per triangle"
        col_for = None
    elif len(colors) == 1:
        col_for = np.zeros(len(tri), dtype=int)
    else:
        # colour by face normal cluster -> very rough material-part guess
        col_for = (np.abs(nrm[:, 2]) < 0.5).astype(int) % len(colors)

    for i in order:
        px = sx[i]
        py = sy[i]
        pz = z[i]
        x0 = max(int(np.floor(px.min())), 0)
        x1 = min(int(np.ceil(px.max())), W - 1)
        y0 = max(int(np.floor(py.min())), 0)
        y1 = min(int(np.ceil(py.max())), H - 1)
        if x1 < x0 or y1 < y0:
            continue
        ax, ay = px[0], py[0]
        bx, by = px[1], py[1]
        cx, cy = px[2], py[2]
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-12:
            continue
        xs = np.arange(x0, x1 + 1) + 0.5
        ys = np.arange(y0, y1 + 1) + 0.5
        gx, gy = np.meshgrid(xs, ys)
        l1 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den
        l2 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den
        l3 = 1.0 - l1 - l2
        m = (l1 >= -1e-9) & (l2 >= -1e-9) & (l3 >= -1e-9)
        if not m.any():
            continue
        depth = l1 * pz[0] + l2 * pz[1] + l3 * pz[2]
        sub_z = zbuf[y0:y1 + 1, x0:x1 + 1]
        upd = m & (depth > sub_z + 1e-9)
        if not upd.any():
            continue
        sub_z[upd] = depth[upd]
        base = (np.asarray(tri_rgb[i], dtype=np.float64) if tri_rgb is not None
                else np.array(colors[col_for[i]], dtype=np.float64))
        c = np.clip(base * lam[i], 0, 255).astype(np.uint8)
        sub_img = img[y0:y1 + 1, x0:x1 + 1]
        sub_img[upd] = c
        if wire:
            # edge overlay
            pass

    im = Image.fromarray(img)
    d = ImageDraw.Draw(im)
    lab = label if label is not None else (
        f"{view}   bbox {hi[0]-lo[0]:.1f} x {hi[1]-lo[1]:.1f} x {hi[2]-lo[2]:.1f} mm")
    d.rectangle([0, 0, W, 22], fill=(12, 13, 17))
    d.text((8, 6), lab, fill=(200, 200, 210))
    im.save(out_png)
    return im


def contact_sheet(paths, out_png, view="iso", cols=3, tile=(500, 380)):
    ims = []
    for p in paths:
        tri, _ = load_stl(p)
        tmp = "/tmp/_tile.png"
        render(tri, tmp, view=view, W=tile[0], H=tile[1])
        im = Image.open(tmp).convert("RGB")
        d = ImageDraw.Draw(im)
        name = p.split("/")[-1].replace(".stl", "")
        d.rectangle([0, tile[1] - 20, tile[0], tile[1]], fill=(12, 13, 17))
        d.text((8, tile[1] - 15), name, fill=(255, 220, 140))
        ims.append(im)
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile[0], rows * tile[1]), (24, 26, 32))
    for i, im in enumerate(ims):
        sheet.paste(im, ((i % cols) * tile[0], (i // cols) * tile[1]))
    sheet.save(out_png)
    return sheet


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "info":
        for path in sys.argv[2:]:
            tri, _ = load_stl(path)
            st = analyse(tri)
            print(f"\n=== {path}")
            print(f"  triangles: {st['tris']}   unique vertices: {st['verts']}")
            print(bbox_table(st["lo"], st["hi"], st["size"]))
            print(f"  surface area: {st['area']:.1f} mm^2   closed volume: {st['volume']/1000:.2f} cm^3")
    elif cmd == "render":
        path, out = sys.argv[2], sys.argv[3]
        view = sys.argv[4] if len(sys.argv) > 4 else "iso"
        tri, _ = load_stl(path)
        render(tri, out, view=view)
        print("wrote", out)
    else:
        raise SystemExit(f"unknown cmd {cmd}")
