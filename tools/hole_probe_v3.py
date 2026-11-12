#!/usr/bin/env python3
"""
hole_probe_v3.py - measure, off the shipped STLs, the void behind every fastener.

For each of the 22 screw holes the box actually has, this casts three rays along the hole axis into
the printed part(s) that own it:

    on-axis      -> the first surface met down the hole = the bottom of a blind pilot, or nothing at
                    all, which means the hole is a through-hole (a defect worth knowing about)
    offset       -> the face next to the hole = the surface a screw head bears on
    from outside -> the outer skin behind the hole, so `behind` says how much plastic is left and
                    proves a "blind" pilot is not a leak

Everything the .blend builder and the print order claim about screw LENGTH is derived from these
numbers, so a length that cannot seat is caught here instead of in the print.

`measure()` returns the table; run as a script to print it.  Exit 1 if a documented screw length
does not fit the hole the printer makes.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import numpy as np                                # noqa: E402
import trimesh                                    # noqa: E402
import orient_v3                                  # noqa: E402
import build_v3 as B                              # noqa: E402

P = B.P
PACK = ["01_MAIN_SHELL_v3.stl", "02_REAR_PLATE_v3.stl", "03_R307_BRACKET_v3.stl",
        "04_RC522_RING_v3.stl"]
BIG = 300.0


def load_parts():
    out = {}
    for f in PACK:
        m = trimesh.load(os.path.join(ROOT, "cad", "v3", f), process=False)
        out[f[:2]] = orient_v3.to_assembly(m, f)
    return out


# label, owner keys, axis, insertion origin sign, pilot dia, the length the print order recommends,
# the unprinted stack the shank crosses on its way in, and what the hole is drilled through first
# `toward` is the point the offset probe aims at, so the surface it finds is the boss or pad next to
# this hole rather than the edge of a dog-bone or a rear rim 20 mm away.  `stack` is the unprinted
# material the shank crosses before it reaches the printed hole (the LCD's and the ESP32's 1.6 mm PCB,
# nothing for the R307 (the bracket is printed, so its own 3.2 mm is already inside the void
# the probe measures), and for the fan the thickness of its own frame at the hole -
# measured on YOUR fan, 2.5 for thin tabs or 10.0 if the holes go through the frame).
JOINTS = [
    ("LCD1602", ("01",), "z", 2.05, 8.0, 1.6, P["lcd_centre"]),
    ("R307 bracket", ("01", "03"), "z", 2.50, 8.0, 0.0, P["r307_centre"]),
    ("RC522 ring", ("01", "04"), "z", 2.05, 4.0, 0.0, P["rc522_centre"]),
    ("rear plate", ("01", "02"), "z", 2.50, 10.0, 0.0, (0.0, 0.0)),
    ("fan 3010", ("01",), "x", 2.50, 12.0, 2.5, tuple(reversed(P["fan_centre_yz"]))),
    ("ESP32 boss", ("01",), "x", 1.80, 8.0, 1.6,
     (P["esp32_usb_edge"] + P["esp32_board"][1] / 2, P["esp32_z_centre"])),
]


def centres(key):
    if key == "LCD1602":
        return [(P["lcd_centre"][0] + sx * P["lcd_hole_pitch"][0] / 2,
                 P["lcd_centre"][1] + sy * P["lcd_hole_pitch"][1] / 2)
                for sx in (-1, 1) for sy in (-1, 1)]
    if key == "R307 bracket":
        return [(P["r307_centre"][0] + off, P["r307_centre"][1]) for off in P["r307_bracket_holes"]]
    if key == "RC522 ring":
        return [(P["rc522_centre"][0] + sx * P["rc522_post_off"][0],
                 P["rc522_centre"][1] + sy * P["rc522_post_off"][1])
                for sx in (-1, 1) for sy in (-1, 1)]
    if key == "rear plate":
        return [(sx * P["plate_boss_xy"][0], sy * P["plate_boss_xy"][1])
                for sx in (-1, 1) for sy in (-1, 1)]
    if key == "fan 3010":
        fy, fz = P["fan_centre_yz"]
        return [(fy + sy * P["fan_pitch"] / 2, fz + sz * P["fan_pitch"] / 2)
                for sy in (-1, 1) for sz in (-1, 1)]
    if key == "ESP32 boss":
        ebl, ebw, ins = P["esp32_board"][1], P["esp32_board"][0], P["esp32_inset"]
        ey0, ezc = P["esp32_usb_edge"], P["esp32_z_centre"]
        return [(ey0 + (ins if a == 0 else ebl - ins), ezc + b * (ebw / 2 - ins))
                for a in (0, 1) for b in (-1, 1)]
    raise KeyError(key)


def _hits(mesh, origin, direction, ai):
    loc, _idx, _r = mesh.ray.intersects_location(
        np.array([origin], dtype=np.float64), np.array([direction], dtype=np.float64),
        multiple_hits=True)
    if len(loc) == 0:
        return []
    vals = sorted([float(c) for c in loc[:, ai]])
    return vals if direction[ai] > 0 else list(reversed(vals))   # nearest to the origin first


def first_hit(mesh, origin, direction):
    """the coordinate of the first surface a ray from `origin` along `direction` meets, or None if
    it escapes - which is how a through-hole is told from a blind pilot.  Ray-based on purpose:
    `mesh.contains` on an STL whose shells are not consistently wound gives wrong answers."""
    ai = 2 if abs(direction[2]) > 0.5 else 0
    h = _hits(mesh, origin, direction, ai)
    return h[0] if h else None


def measure(parts=None):
    """-> list of dicts, one per joint, with the measured void depth and the fit verdict"""
    parts = parts or load_parts()
    rows = []
    for label, owners, axis, pdia, slen, stack, toward in JOINTS:
        mesh = trimesh.util.concatenate([parts[k] for k in owners])
        bb = mesh.bounds
        ai = 2 if axis == "z" else 0
        ins = (0.0, 0.0, -1.0) if axis == "z" else (-1.0, 0.0, 0.0)
        out_d = tuple(-c for c in ins)
        per = []
        for (u, v) in centres(label):
            off = pdia / 2 + 1.5
            if toward is not None:
                # the offset is applied to x for z-axis holes and to z for x-axis holes
                ref, cur = (toward[0], u) if axis == "z" else (toward[1], v)
                off = abs(off) * (1.0 if (ref - cur) >= 0 else -1.0)
            if axis == "z":
                o_in = (u, v, bb[1][2] + 1.0)
                o_off = (u + off, v, bb[1][2] + 1.0)
                o_out = (u, v, bb[0][2] - BIG)
            else:
                o_in = (0.0, u, v)                       # from inside the cavity toward the -X wall
                o_off = (0.0, u, v + (abs(off) if toward is not None else off))
                o_out = (bb[0][0] - BIG, u, v)
            h_ax = _hits(mesh, o_in, ins, ai)
            h_sf = _hits(mesh, o_off, ins, ai)
            h_ot = _hits(mesh, o_out, out_d, ai)
            per.append(dict(bearing=h_sf[0] if h_sf else None,
                            hole_end=h_ax[0] if h_ax else None,
                            outer=h_ot[0] if h_ot else None,
                            n_axis=len(h_ax)))
        bear = [p["bearing"] for p in per if p["bearing"] is not None]
        end = [p["hole_end"] for p in per if p["hole_end"] is not None]
        void = [abs(p["bearing"] - p["hole_end"]) for p in per
                if p["bearing"] is not None and p["hole_end"] is not None]
        behind = [abs(p["hole_end"] - p["outer"]) for p in per
                  if p["hole_end"] is not None and p["outer"] is not None]
        through = [i for i, p in enumerate(per) if p["hole_end"] is None]
        vmax = min(void) if void else None
        room = (vmax if vmax is not None else 0.0) + stack + 0.4
        rows.append(dict(label=label, owners=owners, axis=axis, n=len(per), pilot=pdia,
                         screw=slen, stack=stack, bearing=min(bear) if bear else None,
                         bearing_max=max(bear) if bear else None,
                         hole_end=min(end) if end else None, void=vmax, void_max=max(void) if void else None,
                         behind=min(behind) if behind else None, through=through,
                         room=room, fits=(vmax is not None and slen <= room)))
    return rows


def main():
    rows = measure()
    print("HOLES AND SCREW LENGTHS, MEASURED OFF THE SHIPPED STLs")
    print("=" * 96)
    print(f"{'joint':<14} {'n':>2} {'ax':>3}  bearing face      hole end       void     behind   "
          f"screw   room  verdict")
    print("-" * 96)
    bad = []
    for r in rows:
        bf = f"{r['bearing']:6.2f}..{r['bearing_max']:<6.2f}" if r["bearing"] is not None else "  -  "
        he = f"{r['hole_end']:8.2f}" if r["hole_end"] is not None else "  escapes"
        vo = f"{r['void']:6.2f}" + (f"..{r['void_max']:<5.2f}" if r["void_max"] and
                                    abs(r["void_max"] - r["void"]) > 0.05 else "")
        bd = f"{r['behind']:6.2f}" if r["behind"] is not None else "  -  "
        v = "FITS" if r["fits"] else f"TOO LONG by {r['screw'] - r['room']:.2f}"
        if not r["fits"]:
            bad.append(r)
        print(f"{r['label']:<14} {r['n']:>2} {r['axis']:>3}  {bf:>16} {he:>10} {vo:>11} {bd:>7} "
              f"  {r['screw']:4.1f} {r['room']:5.2f}  {v}")
    print("")
    print("bearing face  z (or x) of the plastic a screw head bears on, from the mesh")
    print("hole end      where the void stops; 'escapes' means the hole is a THROUGH-hole")
    print("void          depth of that void; behind = plastic between the void end and the outside")
    print("room          void + the unprinted stack the shank crosses + 0.4 mm of tip chamfer")
    print("")
    for r in bad:
        print(f"   FIX  {r['label']}: the print order recommends {r['screw']:.1f} mm but the hole only"
              f" takes {r['room']:.1f} mm -> use M{r['pilot'] + 0.45:.1f} x {int(r['room'])}")
    if not bad:
        print("   every recommended screw length seats in the hole the printer makes")
    print("")
    print("HOLE PROBE: " + ("ALL CHECKS PASS" if not bad else f"{len(bad)} LENGTH(S) DO NOT SEAT"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
