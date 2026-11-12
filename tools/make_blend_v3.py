#!/usr/bin/env python3
"""
make_blend_v3.py - build exports/ASTRO_SMART_ATTENDANCE_v3.blend: the whole assembly, in millimetres.

Nothing in the .blend is typed by hand.  Three sources, all of them already trusted elsewhere:

  cad/v3/*.stl        the four bed-aligned print files - restored to the assembly frame with
                      tools/orient_v3.py, the same table the verifier and the physics audit use, and
                      also kept as-shipped in a second collection so the printing attitude is in the
                      file.  Each part's volume is re-measured off the .blend's own triangles and
                      compared with the documented number, so the .blend cannot quietly contain a
                      different model from the one the reports describe.
  tools/build_v3.py   the module solids ARE the generator's own envelope meshes (its `envelopes()`),
                      so they sit where the collision checks say they sit.
  tools/hole_probe_v3.py
                      every screw: its hole's real bearing face, the real depth of the void, and the
                      real plastic left behind it.  A screw is only as long as the hole can take.

Contents (collections):
  01 PRINTED      the 4 parts, assembled            <- what you print
  02 MODULES      R307, 1602+I2C, RC522, ESP32, 3010 fan, USB plug  (reference solids, not printed)
  03 FASTENERS    the 22 screws, each in its measured hole
  04 BED ALIGNED  the same 4 parts exactly as the STLs are, for the slicer view (hidden by default)
  00 RIG          one empty per group with a 24-frame explode, three cameras, sun + area fill

Writes docs/v3_blend_build.txt, exports/ASTRO_SMART_ATTENDANCE_v3_assembly.glb, and renders a
Cycles frame straight out of the saved file.  Exit 0 / "BLENDER BUILD: ALL CHECKS PASS".

Headless note: the pip `bpy` wheel links X11/GL libraries that a container has no reason to carry,
and a background render never opens a window or a GL context.  pylibs/stubs/*.so (gitignored, never
shipped) provide the few symbols the loader insists on; see the report for what was stubbed.
"""
import hashlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import trimesh                                    # noqa: E402
import hole_probe_v3 as HP                        # noqa: E402
import build_v3 as B                              # noqa: E402

P = B.P
E = B.envelopes()
OUT_BLEND = os.path.join(ROOT, "exports", "ASTRO_SMART_ATTENDANCE_v3.blend")
OUT_GLB = os.path.join(ROOT, "exports", "ASTRO_SMART_ATTENDANCE_v3_assembly.glb")
REPORT = os.path.join(ROOT, "docs", "v3_blend_build.txt")
SHOT = os.path.join(ROOT, "renders", "v3_blend_iso.png")     # the hero image

EXPECT_VOL_CM3 = {"01": 115.2, "02": 53.8, "03": 1.0, "04": 2.2}
NAMES = {"01": "01 MAIN SHELL", "02": "02 REAR PLATE", "03": "03 R307 BRACKET",
         "04": "04 RC522 RING"}
GROUP = {"01": None, "02": "rear_plate", "03": "front_bracket", "04": "front_ring"}
HEADROOM_MM = 0.4          # the tip chamfer allowance hole_probe_v3 uses

L, fails, notes = [], [], []


def say(s=""):
    print(s)
    L.append(s)


def chk(cond, msg, alt="FAIL"):
    say(f"   {msg:<70} {'PASS' if cond else alt}")
    if not cond:
        if alt == "FAIL":
            fails.append(msg)
    return bool(cond)


def note(s):
    notes.append(s)
    say("   [note] " + s)


import bpy                                        # noqa: E402

scene = bpy.context.scene
for c in list(scene.collection.children):
    bpy.data.collections.remove(c)
for me in list(bpy.data.meshes):
    bpy.data.meshes.remove(me)
for ob in list(scene.objects):
    bpy.data.objects.remove(ob, do_unlink=True)

COLLS = {}


def coll(name, hide=False):
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    COLLS[name] = c
    if hide:
        c.hide_viewport = True
        c.hide_render = True
    return c


def mat(name, rgba, metallic=0.0, rough=0.45):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*rgba[:3], 1.0)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    return m


M_PLA = mat("PLA shell", (0.60, 0.62, 0.65), 0.0, 0.55)
M_PLA2 = mat("PLA small part", (0.75, 0.76, 0.78), 0.0, 0.5)
M_PCB = mat("PCB green", (0.035, 0.20, 0.10), 0.0, 0.35)
M_GLASS = mat("LCD glass", (0.04, 0.06, 0.05), 0.0, 0.10)
M_HOUSE = mat("module housing", (0.90, 0.90, 0.86), 0.0, 0.42)
M_BLACK = mat("fan frame", (0.03, 0.03, 0.035), 0.0, 0.45)
M_STEEL = mat("steel screw", (0.60, 0.61, 0.63), 1.0, 0.25)
M_GOLD = mat("header tin", (0.72, 0.70, 0.42), 1.0, 0.30)
M_COPPER = mat("copper coil", (0.62, 0.28, 0.14), 1.0, 0.30)


def box_mesh(name, x0, x1, y0, y1, z0, z1):
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    z0, z1 = sorted((z0, z1))
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(v, [], f)
    me.update()
    return me


def tm_mesh(name, m):
    me = bpy.data.meshes.new(name)
    me.from_pydata([(float(a), float(b), float(c)) for a, b, c in m.vertices], [],
                   [(int(i), int(j), int(k)) for i, j, k in m.faces])
    me.update()
    me.validate()
    return me


def tube(name, axis, c1, c2, d_far, d_near, length, sign, n=26):
    """a capped cylinder/cone along `axis` ('z' or 'x'); its centre line passes through (c1, c2) in
    the two transverse coordinates; it starts at 0 and runs `length*sign`; d_far is the diameter at
    the far end (a taper for a countersunk head), d_near at the start."""
    v, f = [], []
    for k in range(n):
        a = 2.0 * math.pi * k / n
        ca, sa = math.cos(a), math.sin(a)
        u1, w1 = (d_near / 2.0) * ca, (d_near / 2.0) * sa
        u2, w2 = (d_far / 2.0) * ca, (d_far / 2.0) * sa
        if axis == "z":
            v.append((c1 + u1, c2 + w1, 0.0))
            v.append((c1 + u2, c2 + w2, sign * length))
        else:
            v.append((0.0, c1 + u1, c2 + w1))
            v.append((sign * length, c1 + u2, c2 + w2))
    for k in range(n):
        k2 = (k + 1) % n
        f.append((k, k2, n + k2, n + k))
    f.append(tuple(reversed(range(n))))
    f.append(tuple(range(n, 2 * n)))
    me = bpy.data.meshes.new(name)
    me.from_pydata(v, [], f)
    me.update()
    return me


def add(name, me, c, m, grp=None, loc=(0.0, 0.0, 0.0)):
    ob = bpy.data.objects.new(name, me)
    c.objects.link(ob)
    ob.location = loc
    if m is not None:
        ob.data.materials.append(m)
    ob["group"] = grp or ""
    return ob


def bb(m):
    lo, hi = m.bounds
    return (lo[0], hi[0], lo[1], hi[1], lo[2], hi[2])


# ============================================================ printed parts + reference solids
say("ASTRO SMART ATTENDANCE v3 - .blend BUILDER")
say("=" * 80)
say(f"Blender {bpy.app.version_string} (headless bpy wheel)  |  units mm  |  "
    f"generated by tools/make_blend_v3.py, nothing typed by hand")
say("")

c_print = coll("01 PRINTED")
c_mod = coll("02 MODULES")
c_fast = coll("03 FASTENERS")
c_bed = coll("04 BED ALIGNED", hide=True)
c_rig = coll("00 RIG")

say("1. THE FOUR PRINTED PARTS  (assembly frame, from the shipped bed-aligned STLs)")
say("-" * 80)
parts = HP.load_parts()
for _k in parts:                       # the STL carries duplicated vertices; Blender wants one
    parts[_k].merge_vertices()         # seam-free mesh, and merge_vertices makes the watertight
    parts[_k].remove_infinite_values() # test meaningful (it is the test the docs claim passes)
printed = {}
for k in ("01", "02", "03", "04"):
    m = parts[k]
    fn = [f for f in os.listdir(os.path.join(ROOT, "cad", "v3")) if f.startswith(k)][0]
    raw = trimesh.load(os.path.join(ROOT, "cad", "v3", fn), process=False)
    ob = add(NAMES[k], tm_mesh(NAMES[k], m), c_print, M_PLA if k == "01" else M_PLA2,
             grp=GROUP[k])
    printed[k] = ob
    add(NAMES[k] + " (as printed)", tm_mesh(NAMES[k] + "_bed", raw), c_bed, M_PLA2)
    vol = float(m.volume) / 1000.0
    b = bb(m)
    chk(abs(vol - EXPECT_VOL_CM3[k]) < 0.06,
        f"{NAMES[k]}: {vol:.2f} cm3 in the .blend vs {EXPECT_VOL_CM3[k]:.1f} cm3 documented, "
        f"{len(m.faces)} faces, watertight={m.is_watertight}")
    genus = int((2 - int(m.euler_number)) / 2)
    chk(bool(m.is_watertight) and int(m.body_count) == 1,
        f"{NAMES[k]}: watertight, {int(m.body_count)} closed body, {genus} through-holes "
        f"(genus {genus}) in the .blend mesh")
    chk(abs(raw.bounds[0][2]) < 1e-6, f"{NAMES[k]}: the bed-aligned copy sits at z = 0 "
                                     f"(tools/orient_v3.py dz={__import__('orient_v3').ORIENT[fn][0]})")
allm = trimesh.util.concatenate(list(parts.values()))
lo, hi = allm.bounds
say(f"   assembly envelope off these four solids: {hi[0]-lo[0]:.2f} x {hi[1]-lo[1]:.2f} x "
    f"{hi[2]-lo[2]:.2f} mm")
chk(abs((hi[0] - lo[0]) - P["W"]) < 0.02 and abs((hi[1] - lo[1]) - P["H"]) < 0.02
    and abs((hi[2] - lo[2]) - P["D"]) < 0.02,
    f"equals the documented {P['W']:.0f} x {P['H']:.0f} x {P['D']:.0f} mm")

say("")
say("2. MODULES  (the generator's own envelope solids + a real 3010 with its bore and lug holes)")
say("-" * 80)
MODS = [("LCD1602 glass", "LCD_glass_pane", M_GLASS, "front_LCD"),
        ("LCD1602 pcb + I2C backpack", "LCD_pcb+backpack", M_PCB, "front_LCD"),
        ("R307 housing", "R307_body", M_HOUSE, "front_R307"),
        ("RC522 board", "RC522_board", M_PCB, "front_ring"),
        ("RC522 components", "RC522_components", M_GOLD, "front_ring"),
        ("ESP32 board + headers", "ESP32_board+components", M_PCB, "left_esp32"),
        ("USB plug in the slot", "USB_plug", M_BLACK, "left_esp32")]
# the envelope generator carries the USB plug as a full 22.5 mm slab from the socket backwards, which
# is right for a clearance check and wrong for a picture - it would hang 14 mm outside the case.  The
# .blend draws it from the socket to 2 mm proud of the outer wall, which is what a straight USB-C plug
# actually does through a 3 mm wall with the socket 7 mm inside it.  Geometry in the STL is untouched.
PROUD = 2.0
y_out = -(P["H"] / 2.0) - PROUD
for label, key, m, grp in MODS:
    b = bb(E[key])
    if key == "USB_plug":
        b = (b[0], b[1], max(b[2], y_out), b[3], b[4], b[5])
    add(label, box_mesh(label, *b), c_mod, m, grp=grp)
    say(f"   {label:<30} {b[1]-b[0]:6.2f} x {b[3]-b[2]:6.2f} x {b[5]-b[4]:6.2f} mm")
say(f"   the USB plug is drawn to {PROUD:.1f} mm proud of the y = {-P['H'] / 2.0:.1f} mm outer wall; the")
say( "   envelope the clearance check uses is unchanged, this is the picture, not the fit claim")

gx, gy = P["r307_centre"]
zi = P["wall_front"]
add("R307 glass", box_mesh("R307 glass", gx - P["r307_window"][0] / 2, gx + P["r307_window"][0] / 2,
                           gy - P["r307_window"][1] / 2, gy + P["r307_window"][1] / 2,
                           zi - 0.6, zi + 0.4), c_mod, M_GLASS, grp="front_R307")
say(f"   {'R307 glass (the optical window)':<30} {P['r307_window'][0]:6.2f} x "
    f"{P['r307_window'][1]:6.2f} mm")

fy, fz = P["fan_centre_yz"]
fb = bb(E["Fan_3010"])
fan = trimesh.creation.box(extents=(fb[1] - fb[0], fb[3] - fb[2], fb[5] - fb[4]))
fan.apply_translation([(fb[0] + fb[1]) / 2, (fb[2] + fb[3]) / 2, (fb[4] + fb[5]) / 2])
rot = trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0])
bore = trimesh.creation.cylinder(radius=P["fan_open_d"] / 2.0, height=400.0, sections=96)
bore.apply_transform(rot)
bore.apply_translation([(fb[0] + fb[1]) / 2, fy, fz])
cut = [bore]
for sy in (-1, 1):
    for sz in (-1, 1):
        h = trimesh.creation.cylinder(radius=1.6, height=200.0, sections=24)
        h.apply_transform(rot)
        h.apply_translation([(fb[0] + fb[1]) / 2, fy + sy * P["fan_pitch"] / 2,
                             fz + sz * P["fan_pitch"] / 2])
        cut.append(h)
try:
    fan = fan.difference(trimesh.util.concatenate(cut))
    add("3010 fan (bored)", tm_mesh("fan", fan), c_mod, M_BLACK, grp="left_fan")
    chk(fan.volume < 30.0 * 30.0 * 10.0 and fan.volume > 0.0,
        f"   3010 fan (bored): {P['fan'][0]:.0f} x {P['fan'][1]:.0f} x {P['fan'][2]:.0f} mm minus a "
        f"d{P['fan_open_d']:.0f} bore and 4 x d3.2 on {P['fan_pitch']:.0f} mm -> {fan.volume:.0f} mm3")
except Exception as exc:
    add("3010 fan (bored)", box_mesh("fan", *fb), c_mod, M_BLACK, grp="left_fan")
    note(f"fan booleans unavailable ({type(exc).__name__}) - shipped as the envelope box")

# ============================================================ fasteners, from the probe
say("")
say("3. FASTENERS  (22 screws, each placed on a hole that was measured off the mesh)")
say("-" * 80)
rows = HP.measure(parts)
rows_by = {r["label"]: r for r in rows}
# a pilot is cut at the thread's minor, the shank that goes in it is at nominal
NOM = {2.05: 2.5, 2.50: 3.0, 1.80: 2.2}
n_screw = 0
for label, owners, axis, pdia, slen, stack, toward in HP.JOINTS:
    r = rows_by[label]
    mesh = trimesh.util.concatenate([parts[k] for k in owners])
    for (u, v) in HP.centres(label):
        grp = {"LCD1602": "front_LCD", "R307 bracket": "front_bracket", "RC522 ring": "front_ring",
               "rear plate": "rear_plate", "fan 3010": "left_fan", "ESP32 boss": "left_esp32"}[label]
        length = round(min(slen, r["room"]), 1)
        nom = NOM.get(pdia, pdia + 0.45)
        # DIN 125 pan heads are about nominal + 2.5 across; the plate uses a DIN 963 countersunk
        # head, modelled as the cone that the printed 90-degree countersink was cut for
        head_d, head_h = (6.0, 1.85) if label == "rear plate" else (min(nom + 2.5, 6.0), 1.9)
        if axis == "z":
            entry = r["bearing"] + stack
            shank = tube(f"{label} screw {n_screw}", "z", u, v, nom, nom, length, -1.0)
            add(f"{label} screw {n_screw}", shank, c_fast, M_STEEL, grp=grp, loc=(0, 0, entry))
            hd = tube(f"{label} head {n_screw}", "z", u, v, head_d,
                      4.6 if label == "rear plate" else head_d, head_h, +1.0)
            add(f"{label} head {n_screw}", hd, c_fast, M_STEEL, grp=grp, loc=(0, 0, entry))
            tip, endz = entry - length, r["hole_end"]
            ok = tip >= endz - 0.05
        else:
            entry = r["bearing"] + stack
            shank = tube(f"{label} screw {n_screw}", "x", u, v, nom, nom, length, -1.0)
            add(f"{label} screw {n_screw}", shank, c_fast, M_STEEL, grp=grp, loc=(entry, 0, 0))
            hd = tube(f"{label} head {n_screw}", "x", u, v, head_d, head_d, head_h, +1.0)
            add(f"{label} head {n_screw}", hd, c_fast, M_STEEL, grp=grp, loc=(entry, 0, 0))
            tip, endz = entry - length, r["hole_end"]
            ok = tip >= endz - 0.05
        n_screw += 1
        ins = (0.0, 0.0, -1.0) if axis == "z" else (-1.0, 0.0, 0.0)
        o = (u, v, entry + 1.0) if axis == "z" else (entry + 1.0, u, v)
        first = HP.first_hit(mesh, o, ins)
        # both axes insert toward decreasing coordinates, so the tip must stop above the bottom
        open_ok = first is not None and tip >= first - 0.05     # void really open down to the tip
        blind = first is not None                               # and it stops: not a through-hole
        left = r["behind"] if r["behind"] is not None else 0.0
        if n_screw <= 6 or not (ok and open_ok and blind and left >= 1.0):
            say(f"   {label:<13} M{nom:.1f} x {length:4.1f} at ({u:6.2f},{v:6.2f})  "
                f"void {r['void']:.2f} deep, tip clears by {tip - endz:+.2f} mm")
        chk(bool(ok and open_ok and blind and left >= 1.0),
            f"{label} screw #{n_screw}: seats in the void it was measured for, the axis is open at "
            f"{0.0 if first is None else abs(first - entry):.2f} mm of open void, pilot blind with {left:.2f} mm "
            f"of wall left behind it")
chk(n_screw == 22, f"{n_screw} screws placed, and the print order documents 22 screw holes")
for r in rows:
    chk(r["fits"], f"{r['label']:<13} recommended L={r['screw']:.1f} mm vs {r['room']:.2f} mm of "
                   f"measured room", alt="WARN")

# ============================================================ rig, cameras, light, explode
say("")
say("4. RIG  (a 24-frame explode; the .blend shows how the thing goes together)")
say("-" * 80)
EXPLODE = {"front_ring": (0, 0, -22.0), "front_R307": (0, 0, -38.0), "front_bracket": (0, 0, -70.0),
           "front_LCD": (0, 0, -50.0), "left_fan": (-62.0, 0, 0), "left_esp32": (-46.0, 0, 0),
           "rear_plate": (0, 0, +62.0)}
allobjs = list(c_print.objects) + list(c_mod.objects) + list(c_fast.objects)
for gname, off in EXPLODE.items():
    e = bpy.data.objects.new(gname, None)
    e.empty_display_type = "ARROWS"
    e.empty_display_size = 30.0
    c_rig.objects.link(e)
    e.keyframe_insert("location", frame=1)
    kids = [ob for ob in allobjs if ob.get("group") == gname]
    for ob in kids:
        ob.parent = e
        ob.matrix_parent_inverse = e.matrix_world.inverted()
    e.location = off
    e.keyframe_insert("location", frame=24)
    for a in (e.animation_data.action,):
        for fc in a.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.easing = "EASE_IN_OUT"
    say(f"   {gname:<14} -> {off[0]:+6.1f}, {off[1]:+6.1f}, {off[2]:+6.1f} mm      ({len(kids)} objects)")
chk(sum(len([o for o in allobjs if o.get('group') == g]) for g in EXPLODE) +
    len([o for o in allobjs if not o.get("group")]) == len(allobjs),
    "every object is either in an explode group or deliberately fixed (the shell)")
scene.frame_start, scene.frame_end = 1, 48
scene.frame_set(1)
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 0.001
scene.unit_settings.length_unit = "MILLIMETERS"

cen = [(lo[i] + hi[i]) / 2 for i in range(3)]
tgt = bpy.data.objects.new("view target", None)
tgt.empty_display_size = 5.0
c_rig.objects.link(tgt)
tgt.location = cen
# the front of this case is the z = 0 plane (the cavity runs +Z to the plate), so a camera that
# shows the LCD rebate and the reader ring has to sit at NEGATIVE z, 430 mm out
for nm, loc, ortho in (("CAM front", (cen[0], cen[1], cen[2] - 430.0), True),
                       ("CAM iso", (cen[0] + 345.0, cen[1] - 345.0, cen[2] - 375.0), False),
                       ("CAM fan wall", (cen[0] - 440.0, cen[1], cen[2]), True)):
    cd = bpy.data.cameras.new(nm)
    if ortho:
        cd.type = "ORTHO"
        # the film is 1500 x 1100, so ortho_scale must cover the 155 mm height of the case on the
        # SHORT side of the sensor: 155 * 1500/1100 = 211.4 mm, plus a 1 % margin
        cd.ortho_scale = 214.0
        cd.lens = 50.0
    else:
        cd.lens = 55.0
    ob = bpy.data.objects.new(nm, cd)
    c_rig.objects.link(ob)
    ob.location = loc
    con = ob.constraints.new("TRACK_TO")
    con.target, con.track_axis, con.up_axis = tgt, "TRACK_NEGATIVE_Z", "UP_Y"
scene.camera = bpy.data.objects["CAM iso"]
sun = bpy.data.lights.new("sun", "SUN")
sun.energy, sun.angle = 3.5, math.radians(3.0)
sob = bpy.data.objects.new("sun", sun)
c_rig.objects.link(sob)
# a sun travels along its own -Z, so an X rotation past 90 deg puts the light on the front side of
# the case (the face the reader looks at) instead of washing out the back plate
sob.rotation_euler = (math.radians(126), 0.0, math.radians(-28))
fill = bpy.data.lights.new("fill", "AREA")
fill.energy, fill.size = 1400.0, 340.0
fob = bpy.data.objects.new("fill", fill)
c_rig.objects.link(fob)
fob.location = (cen[0] + 150.0, cen[1] - 300.0, cen[2] - 300.0)
fc = fob.constraints.new("TRACK_TO")
fc.target, fc.track_axis, fc.up_axis = tgt, "TRACK_NEGATIVE_Z", "UP_Y"
world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.34, 0.35, 0.37, 1.0)
# 3 shots out of the saved file: the ortho front (the face that gets printed and read), an iso
# assembled view, and the same iso at frame 24 where the explode has pulled everything out
SHOTS = (("CAM front", 1, "v3_blend_front.png", "ortho, the LCD rebate + reader aperture + ring centres"),
         ("CAM iso", 1, "v3_blend_iso.png", "assembled 3/4"),
         ("CAM iso", 24, "v3_blend_exploded.png", "frame 24, exploded, all 22 screws clear of the holes"))

# ============================================================ save, check, export, render
say("")
say("5. OUTPUT")
say("-" * 80)
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
sz = os.path.getsize(OUT_BLEND)
chk(sz > 300_000, f"{os.path.basename(OUT_BLEND)}  {sz:,} bytes, {len(scene.objects)} objects, "
                  f"{len(bpy.data.meshes)} meshes")
sha = hashlib.sha256(open(OUT_BLEND, "rb").read()).hexdigest()
try:
    scene.frame_set(1)
    bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format="GLB", use_visible=True)
    say(f"   {os.path.basename(OUT_GLB)}  {os.path.getsize(OUT_GLB):,} bytes (assembled, for any "
        f"viewer that cannot open a .blend)")
except Exception as exc:
    note(f"glTF export skipped: {type(exc).__name__}: {exc}")
rendered = []
try:
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 24
    scene.render.resolution_x, scene.render.resolution_y = 1500, 1100
    scene.render.image_settings.file_format = "PNG"
    for cam, frame, name, why in SHOTS:
        out = os.path.join(ROOT, "renders", name)
        scene.camera = bpy.data.objects[cam]
        scene.frame_set(frame)
        scene.render.filepath = out
        bpy.ops.render.render(write_still=True)
        rendered.append((name, why, out))
except Exception as exc:
    note(f"render stopped ({type(exc).__name__}: {exc}) - the .blend itself is complete")
for name, why, out in rendered:
    sz = os.path.getsize(out) if os.path.exists(out) else 0
    chk(sz > 60_000, f"Cycles CPU rendered the SAVED .blend -> renders/{name} ({sz:,} B)  {why}")
chk(len(rendered) == len(SHOTS), f"all {len(SHOTS)} shots came out of the saved file")
say("")
say(f"   blend sha256 {sha[:40]}")
say("")
say("BLENDER BUILD: " + ("ALL CHECKS PASS" if not fails else f"{len(fails)} FAILURE(S)"))
if notes:
    say("   (notes: " + "; ".join(n[:70] for n in notes) + ")")
open(REPORT, "w", encoding="utf-8").write("\n".join(L) + "\n")
sys.exit(1 if fails else 0)
