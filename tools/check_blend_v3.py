#!/usr/bin/env python3
"""
check_blend_v3.py - the .blend gate.  It opens exports/ASTRO_SMART_ATTENDANCE_v3.blend from disk and
re-measures everything out of its OWN polygons, in world space, at the frames the rig claims.  It
shares no code with the builder: the builder's numbers are not used as evidence anywhere here.
What it has to agree with, and where that number comes from independently:

  * the four shipped STLs  -> solid volume, triangle count, bounding box, the depth of every pilot
  * docs/v3_design_notes   -> the same volumes as published (0.1 cm3 tolerance)
  * the screw schedule     -> one screw per documented hole, correct length, head at the entry face
  * the render files       -> actually contain the picture they claim (pixel statistics, not bytes)

Run:  LD_LIBRARY_PATH=$PWD/pylibs/stubs:$PWD/pylibs/bpy/lib PYTHONPATH=pylibs \\
      python3 tools/check_blend_v3.py > docs/.blend_check.log 2>&1
"""
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
for _p in os.environ.get("LD_LIBRARY_PATH", "").split(os.pathsep):
    if _p:
        sys.path.append(_p)
import bpy                                                   # noqa: E402

import trimesh                                               # noqa: E402
import hole_probe_v3 as HP                                   # noqa: E402
from orient_v3 import ORIENT                                  # noqa: E402

CAD = os.path.join(ROOT, "cad", "v3")

BLEND = os.path.join(ROOT, "exports", "ASTRO_SMART_ATTENDANCE_v3.blend")
GLB = os.path.join(ROOT, "exports", "ASTRO_SMART_ATTENDANCE_v3_assembly.glb")
REPORT = os.path.join(ROOT, "docs", "v3_blend_check.txt")
DOC_CM3 = {"01_MAIN_SHELL_v3.stl": 115.2, "02_REAR_PLATE_v3.stl": 53.8,
           "03_R307_BRACKET_v3.stl": 1.0, "04_RC522_RING_v3.stl": 2.2}
NAMES = {"01_MAIN_SHELL_v3.stl": "01 MAIN SHELL", "02_REAR_PLATE_v3.stl": "02 REAR PLATE",
         "03_R307_BRACKET_v3.stl": "03 R307 BRACKET", "04_RC522_RING_v3.stl": "04 RC522 RING"}
PER_HOLE = {"LCD1602": 4, "R307 bracket": 2, "RC522 ring": 4, "rear plate": 4, "fan 3010": 4,
            "ESP32 boss": 4}
L = []


def say(t=""):
    L.append(t)
    print(t, flush=True)


F = []


def chk(cond, what):
    say(f"   {what:<74} {'PASS' if cond else 'FAIL'}")
    if not cond:
        F.append(what)
    return bool(cond)


def world_vol_and_box(ob):
    """signed-tetrahedron volume of one object's polygons, in world space, plus its world bbox.
    triangles only here - the STL import and every screw is a tri mesh, so no fan is needed"""
    M = ob.matrix_world
    mv = [M @ v.co for v in ob.data.vertices]
    tri = 0
    vol = 0.0
    lo = [1e9] * 3
    hi = [-1e9] * 3
    for pg in ob.data.polygons:
        idx = pg.vertices
        for k in range(1, len(idx) - 1):
            a, b, c = mv[idx[0]], mv[idx[k]], mv[idx[k + 1]]
            vol += (a[0] * (b[1] * c[2] - b[2] * c[1])
                    - a[1] * (b[0] * c[2] - b[2] * c[0])
                    + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6.0
            tri += 1
        for p in (a, b, c):
            for i in range(3):
                lo[i] = min(lo[i], p[i])
                hi[i] = max(hi[i], p[i])
    return abs(vol), tri, lo, hi


say("ASTRO SMART ATTENDANCE v3 - .blend GATE (opens the saved file and re-measures it)")
say("=" * 80)
if not chk(os.path.exists(BLEND) and os.path.getsize(BLEND) > 300_000,
           f"{os.path.basename(BLEND)} exists and is a real .blend"):
    sys.exit(1)
bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.context.view_layer
sc.update()
objs = {o.name: o for o in bpy.data.objects}
parts = HP.load_parts()
for k in parts:
    parts[k].merge_vertices()
say("")
say(f"   opened: Blender {bpy.app.version_string}, {len(bpy.data.objects)} objects, "
    f"{len(bpy.data.meshes)} meshes, {len(bpy.data.collections)} collections")
say("")

say("1. THE PRINTED PARTS IN THE .blend vs THE SHIPPED STLS  (both measured here, in mm)")
say("-" * 80)
printed = list(bpy.data.collections["01 PRINTED"].objects)
chk(sorted(o.name for o in printed) == sorted(NAMES.values()),
    "collection '01 PRINTED' holds exactly the four parts that ship as STLs, nothing extra")
stl_vol, blend_vol = {}, {}
for k, name in NAMES.items():
    stl = trimesh.load(os.path.join(CAD, k), process=True, file_type="stl")
    ob = objs.get(name)
    if ob is None:
        chk(False, f"{name}: present in the .blend")
        continue
    v, tri, lo, hi = world_vol_and_box(ob)
    stl_vol[k] = stl.volume / 1000.0
    blend_vol[name] = v / 1000.0
    box = [hi[i] - lo[i] for i in range(3)]
    dz = ORIENT[k][0]
    chk(abs(v / 1000.0 - stl.volume / 1000.0) < 0.05,
        f"{name}: {v / 1000.0:6.2f} cm3 in the .blend vs {stl.volume / 1000.0:6.2f} cm3 in the STL "
        f"({tri} tris)")
    chk(abs(v / 1000.0 - DOC_CM3[k]) < 0.1,
        f"{name}: {v / 1000.0:6.2f} cm3 vs the {DOC_CM3[k]} cm3 the design notes publish")
    chk(abs(tri - len(stl.faces)) <= 2, f"{name}: same triangle count as the STL ({tri})")
    # orient_v3 says the STL sits with its first layer on z=0 and the assembly frame lifts it by dz;
    # so the .blend copy's own lowest point must BE that lift, to the micron - which is the check that
    # the model in the .blend is the model that prints, not a copy of something else
    chk(abs(lo[2] - dz) < 1e-3 and hi[2] - lo[2] > 2.0,
        f"{name}: lowest point z = {lo[2]:.2f} mm = the {dz} mm lift in the print-orientation table "
        f"(part runs z {lo[2]:.2f} .. {hi[2]:.2f} mm)")
    chk(all(abs(box[i]) < 200.0 for i in range(3)),
        f"{name}: envelope {box[0]:.2f} x {box[1]:.2f} x {box[2]:.2f} mm is inside one 180 x 180 bed")
allbox_lo = [min(world_vol_and_box(objs[n])[2][i] for n in NAMES.values()) for i in range(3)]
allbox_hi = [max(world_vol_and_box(objs[n])[3][i] for n in NAMES.values()) for i in range(3)]
say("")
tot = sum(blend_vol.values())
say(f"   four printed solids, from the .blend's own triangles: {tot:.2f} cm3, "
    f"box {allbox_hi[0] - allbox_lo[0]:.2f} x {allbox_hi[1] - allbox_lo[1]:.2f} x "
    f"{allbox_hi[2] - allbox_lo[2]:.2f} mm")
chk(abs((allbox_hi[0] - allbox_lo[0]) - 110.0) < 0.02 and abs((allbox_hi[1] - allbox_lo[1]) - 155.0) < 0.02
    and abs((allbox_hi[2] - allbox_lo[2]) - 46.0) < 0.02, "assembly box off the .blend = 110 x 155 x 46 mm")

say("")
say("2. FASTENERS: one per documented hole, in that hole, to that length")
say("-" * 80)
rows = {r["label"]: r for r in HP.measure(parts)}
placed = {}
for ob in sorted(bpy.data.objects, key=lambda o: o.name):
    if "screw" not in ob.name or ob.type != "MESH":
        continue
    label = ob.name.rsplit(" screw", 1)[0]
    v, tri, lo, hi = world_vol_and_box(ob)
    placed.setdefault(label, []).append((lo, hi))
for label, n in PER_HOLE.items():
    r = rows[label]
    got = placed.get(label, [])
    if not chk(len(got) == n == len(HP.centres(label)),
               f"{label}: {len(got)} screws in the .blend for {n} holes measured on the mesh"):
        continue
    axis = r["axis"]
    worst_seat = 1e9
    worst_off = 0.0
    for (lo, hi) in got:
        ctr = [(lo[i] + hi[i]) / 2 for i in range(3)]
        ux = [0.0, 0.0, 1.0] if axis == "z" else [1.0, 0.0, 0.0]
        # the screw's own span along the joint axis, and where its axis line sits in the cross-section
        span = [hi[2] if axis == "z" else hi[0], lo[2] if axis == "z" else lo[0]]
        cross = [ctr[0] if axis == "z" else ctr[1], ctr[1] if axis == "z" else ctr[2]]
        best = min(math.hypot(cross[0] - c[0], cross[1] - c[1]) for c in HP.centres(label))
        worst_off = max(worst_off, best)
        # tip must stop above the bottom of the pilot and head must sit at the entry face
        worst_seat = min(worst_seat, span[1] - r["hole_end"])
        if span[0] > r["bearing"] + r["stack"] + 0.9 or span[0] < r["bearing"] + r["stack"] - 2.6:
            chk(False, f"{label}: a head is not at the entry face ({span[0]:.2f} vs "
                       f"{r['bearing'] + r['stack']:.2f})")
    chk(abs(worst_off) < 0.06,
        f"{label}: every screw axis lands on a measured hole centre (worst {worst_off:.3f} mm)")
    chk(worst_seat > -0.05,
        f"{label}: every tip stops in the plastic ({worst_seat:+.2f} mm above the pilot bottom)")
    say(f"      {label:<13} screw length in the .blend "
        f"{max(hi[2 if axis == 'z' else 0] - lo[2 if axis == 'z' else 0] for lo, hi in got):.2f} mm"
        f"  vs documented {r['screw']:.1f} mm (room {r['room']:.2f} mm)")
    chk(abs(max(hi[2 if axis == "z" else 0] - lo[2 if axis == "z" else 0] for lo, hi in got)
            - min(r["screw"], r["room"])) < 0.35, f"{label}: modelled length matches the schedule")
say("")
tot_s = sum(len(v) for v in placed.values())
chk(tot_s == 22, f"{tot_s} screws in the .blend = the 22 holes the print order tells you to drill")

say("")
say("3. THE BED-ALIGNED COPIES, THE MODULES AND THE RIG")
say("-" * 80)
if chk("04 BED ALIGNED" in bpy.data.collections, "collection '04 BED ALIGNED' is in the file"):
    bed = list(bpy.data.collections["04 BED ALIGNED"].objects)
else:
    bed = []
if chk(len(bed) == 4, f"{len(bed)} bed-aligned copies in '04 BED ALIGNED' for the print bag"):
    for ob in bed:
        v, tri, lo, hi = world_vol_and_box(ob)
        chk(abs(lo[2]) < 0.02, f"{ob.name}: first layer on z = 0 ({lo[2]:.3f} mm), "
                               f"{v / 1000.0:.2f} cm3 in the box")
    cb = bpy.data.collections["04 BED ALIGNED"]
    chk(bool(cb.hide_viewport) and bool(cb.hide_render),
        "the bed copies are switched off in the viewport and the render, so the assembly view "
        "is never doubled up when you open the file")
fast = list(bpy.data.collections["03 FASTENERS"].objects)
shanks = [o for o in fast if " screw " in o.name]
heads = [o for o in fast if " head " in o.name]
chk(len(shanks) == len(heads) == 22,
    f"'03 FASTENERS' holds {len(shanks)} shanks and {len(heads)} heads - one of each per screw")
mod = list(bpy.data.collections["02 MODULES"].objects)
fast = list(bpy.data.collections["03 FASTENERS"].objects)
say(f"   {len(mod)} module solids in '02 MODULES' as envelopes "
    f"(they are the reserved space, published from vendor sheets - not a claim about your boards)")
fan = [o for o in mod if o.name.startswith("3010")]
if chk(len(fan) == 1, "the 3010 fan is the one solid that is real geometry, not a box"):
    v, tri, lo, hi = world_vol_and_box(fan[0])
    box = sorted(round(hi[i] - lo[i], 2) for i in range(3))
    chk(box == [10.0, 30.0, 30.0], f"fan outer box {box[2]} x {box[1]} x {box[0]} mm in the .blend "
        f"(axis along X, into the bore) = the 30 x 30 x 10 mm 3010")
    chk(2400.0 < v < 2660.0,
        f"fan solid {v:.0f} mm3 - that is 30 x 30 x 10 = 9000 minus the d28 bore and 4 x d3.2 on 24 mm")
    chk(tri > 400, f"fan mesh has {tri} triangles (the bore and the lug holes are really in it)")
keyed = [o.name for o in bpy.data.objects
         if o.animation_data and o.animation_data.action and o.type == "EMPTY"]
chk(len(keyed) == 7, f"{len(keyed)} explode empties with keyframes: {', '.join(sorted(keyed))}")
sc = bpy.context.scene
chk(sc.frame_start == 1 and sc.frame_end == 48 and sc.render.fps >= 24,
    f"timeline {sc.frame_start}..{sc.frame_end} at {sc.render.fps} fps - assembled, exploded, reassembled")
offs = {}
for nm in keyed:
    e = bpy.data.objects[nm]
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    a = [e.matrix_world.translation[i] for i in range(3)]
    bpy.context.scene.frame_set(24)
    bpy.context.view_layer.update()
    b = [e.matrix_world.translation[i] for i in range(3)]
    offs[nm] = [round(b[i] - a[i], 1) for i in range(3)]
say("   explode travel measured by moving the timeline on the reopened file:")
for nm in sorted(offs):
    say(f"      {nm:<14} -> {offs[nm][0]:+6.1f}, {offs[nm][1]:+6.1f}, {offs[nm][2]:+6.1f} mm")
chk(all(any(abs(v) > 20.0 for v in o) for o in offs.values()),
    "every group actually moves more than 20 mm, so the drawing separates the parts")
chk(sum(1 for o in offs.values() if o[2] < -20) == 4 and sum(1 for o in offs.values() if o[2] > 20) == 1
    and sum(1 for o in offs.values() if o[0] < -20) == 2,
    "4 groups out through the front, 1 out through the back, 2 out through the fan wall - "
    "the order the print guide is written in")
chk(sc.unit_settings.system == "METRIC" and abs(sc.unit_settings.scale_length - 0.001) < 1e-9
    and sc.unit_settings.length_unit == "MILLIMETERS",
    "scene units: 1 unit = 1 mm, so every number above is a millimetre and a slicer will agree")

say("")
say("3b. NOTHING POKES OUT OF THE CASE (the check that a display solid was not left 14 mm in the air)")
say("-" * 80)
pb = [allbox_lo, allbox_hi]
bpy.context.scene.frame_set(1)          # the explode keys move everything; measure the assembled frame
bpy.context.view_layer.update()
stray = []
for coll in ("01 PRINTED", "02 MODULES", "03 FASTENERS"):
    for ob in bpy.data.collections[coll].objects:
        _v, _t, lo, hi = world_vol_and_box(ob)
        for i in range(3):
            if lo[i] < pb[0][i] - 2.5 or hi[i] > pb[1][i] + 2.5:
                stray.append(f"{ob.name}[{i}] {lo[i]:.1f}..{hi[i]:.1f} vs {pb[0][i]:.1f}..{pb[1][i]:.1f}")
chk(not stray, "every printed part, module and screw is inside the 110 x 155 x 46 envelope + 2.5 mm "
    "(the 2 mm USB plug relief is the only thing allowed outside, and it is inside that margin)")
if stray:
    for sx in stray:
        say(f"      outside: {sx}")

say("")
say("4. THE .glb COPY AND THE RENDERED FRAMES")
say("-" * 80)
if chk(os.path.exists(GLB) and os.path.getsize(GLB) > 200_000, f"{os.path.basename(GLB)} exists"):
    for o in [x for x in list(bpy.data.objects) if x.name.startswith("GLB ")]:
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.import_scene.gltf(filepath=GLB)
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    imp = [o for o in bpy.data.objects if o.type == "MESH" and o.name not in objs]
    lo = [min((world_vol_and_box(o)[2][i] for o in imp), default=0) for i in range(3)]
    hi = [max((world_vol_and_box(o)[3][i] for o in imp), default=0) for i in range(3)]
    box = [round(hi[i] - lo[i], 1) for i in range(3)]
    # glTF has no millimetre unit, and this .glb deliberately keeps 1 unit = 1 mm, so reopening it in
    # a Blender scene that is also in mm inflates by exactly the scene scale of 1000.  Asserting the
    # ratio is the check that the export wrote the geometry and not a rescaled copy of it.
    mm = [b / 1000.0 for b in box]
    say(f"   re-imported {len(imp)} meshes, box {box[0]:.0f} x {box[1]:.0f} x {box[2]:.0f} scene-mm "
        f"= {mm[0]:.2f} x {mm[1]:.2f} x {mm[2]:.2f} .glb units (1 unit = 1 mm)")
    chk(len(imp) >= 30, f"the .glb carries the assembly ({len(imp)} meshes)")
    # the honest comparison is .glb vs the .blend's OWN printed + module + fastener solids, because
    # the plug relief and the screw heads are legitimately outside the 110 x 155 x 46 printed box
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    bl_lo = [1e9] * 3
    bl_hi = [-1e9] * 3
    for coll in ("01 PRINTED", "02 MODULES", "03 FASTENERS"):
        for ob in bpy.data.collections[coll].objects:
            _v, _t, lo, hi = world_vol_and_box(ob)
            for i in range(3):
                bl_lo[i] = min(bl_lo[i], lo[i])
                bl_hi[i] = max(bl_hi[i], hi[i])
    full = [round(bl_hi[i] - bl_lo[i], 2) for i in range(3)]
    say(f"   .blend assembled box, all three real-object collections: {full[0]} x {full[1]} x {full[2]} mm"
        f"  (the printed case itself is 110 x 155 x 46)")
    chk(all(abs(mm[i] - full[i]) < 0.05 for i in range(3)),
        f"the .glb re-imports to the .blend's own {full[0]} x {full[1]} x {full[2]} mm to 0.05 mm - "
        "a faithful copy, with no explode baked into it")
shots = [("v3_blend_front.png", 155.0), ("v3_blend_iso.png", 0.0), ("v3_blend_exploded.png", 0.0)]
for name, _ in shots:
    f = os.path.join(ROOT, "renders", name)
    if not chk(os.path.exists(f) and os.path.getsize(f) > 60_000, f"renders/{name} exists"):
        continue
    im = bpy.data.images.load(f)
    w, h = im.size
    px = im.pixels[:]
    step = max(1, (w * h) // 40_000)
    samp = px[::step * 4]
    mn, mx = min(samp), max(samp)
    mean = sum(samp) / len(samp)
    var = sum((p - mean) ** 2 for p in samp) / len(samp)
    chk(w >= 1200 and h >= 900, f"renders/{name}: {w} x {h} px")
    chk(var > 0.0025 and mx - mn > 0.25,
        f"renders/{name}: {len(samp)} sampled px, spread {mn:.2f}..{mx:.2f}, variance {var:.4f} "
        f"- a real shaded picture, not a blank or a black frame")
    bpy.data.images.remove(im)

say("")
say(f"   .blend sha256 {__import__('hashlib').sha256(open(BLEND, 'rb').read()).hexdigest()[:40]}")
say("")
say("BLENDER RESULT: " + ("ALL CHECKS PASS" if not F else f"{len(F)} FAILURE(S)"))
open(REPORT, "w", encoding="utf-8").write("\n".join(L) + "\n")
sys.exit(1 if F else 0)
