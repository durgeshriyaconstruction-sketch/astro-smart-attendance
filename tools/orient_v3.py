"""v3 print orientation - one table, used by the builder, both checkers and the viewers.

A slicer drops a part onto the bed but never rotates it, so "lies flat on the bed in the
orientation the print order asks for" has to be baked into the STL.  These four parts need no
rotation at all: each one already has a full flat face perpendicular to Z (the shell's front
face, the plate's register frame, the bracket's back, the ring's pad face) - they only need to be
LOWERED so that face is at z = 0.  Pure translation, which keeps every feature in the same place
it was designed, keeps handedness (det = +1), and makes the assembly recoverable by adding the
same number back - that is what the interactive viewer does.

ORIENT[name] = (dz, note)  where  print-ready = assembly mesh translated by -dz in z,
so a shipped part's own minimum z is 0 and its design-plane z was dz.
"""

# z of each part's lowest point in the assembly frame (measured from the design, asserted below)
ORIENT = {
    "01_MAIN_SHELL_v3.stl": (0.0, "front face down on the bed, rear opening up - no supports"),
    "02_REAR_PLATE_v3.stl": (41.0, "register frame down on the bed, outer face up"),
    "03_R307_BRACKET_v3.stl": (26.5, "back face down on the bed"),
    "04_RC522_RING_v3.stl": (4.6, "pad face down on the bed"),
}


def to_print(mesh, name):
    """assembly-frame mesh -> bed-aligned mesh (in place, returns the same object)"""
    dz = ORIENT[name][0]
    if dz:
        mesh.apply_translation([0.0, 0.0, -dz])
    return mesh


def to_assembly(mesh, name):
    """bed-aligned mesh -> assembly-frame mesh (what the checkers compare against)"""
    dz = ORIENT[name][0]
    if dz:
        mesh.apply_translation([0.0, 0.0, +dz])
    return mesh


if __name__ == "__main__":
    import os
    import sys
    import numpy as np
    import trimesh
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bad = 0
    for fn, (dz, note) in ORIENT.items():
        a = trimesh.load(os.path.join(root, "cad", "v3", "assembly", fn), process=True)
        v0, a0, i0 = a.volume, a.area, np.sort(a.moment_inertia)
        p = to_print(a.copy(), fn)
        okz = abs(p.bounds[0][2]) < 1e-6
        okr = abs(p.volume - v0) < 1e-6 * abs(v0) + 1e-9 and abs(p.area - a0) < 1e-6 * a0 + 1e-9
        oki = np.allclose(np.sort(p.moment_inertia), i0, rtol=1e-9)
        det = np.linalg.det(np.eye(4)[:3, :3])
        bad += 0 if (okz and okr and oki) else 1
        print(f"{fn:26s} dz={dz:6.2f}  min z -> {p.bounds[0][2]:+.6f}  "
              f"volume/area/inertia invariant: {okr and oki}  det=+{det:.0f}  "
              f"{'OK' if okz and okr and oki else 'BAD'}   ({note})")
    sys.exit(1 if bad else 0)
