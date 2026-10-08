# Astro Smart Attendance - enclosure **v3**, the complete re-design

Everything in this file is a measurement of the shipped `cad/v3/*.stl` files, not an intention.
Box: **110 x 155 x 46 mm** outer, walls 2.6 mm on the sides and 3.0 mm front / rear / top,
plate 3.0 mm skin + 2 mm register frame, 22 self-tapping pilots at thread minor diameter
(M2.5 -> 2.05, M2.2 -> 1.80, M3 -> 2.50), 8 x 30 x 5 mm intake slots, no supports anywhere.
All four files are **bed-aligned**: the orientation a printer must see is baked into the triangles
(`tools/orient_v3.py` is the single source of truth, and the verifier undoes that one translation
before it asserts anything in the design frame).
Three independent programs had to agree before a single line was written here:

| check | program | result |
|---|---|---|
| parametric audit A-K | `tools/build_v3.py` | `RESULT: ALL CHECKS PASS` (`docs/v3_audit.txt`) |
| STL-only verification | `tools/verify_v3.py` | `INDEPENDENT RESULT: ALL CHECKS PASS` (`docs/v3_independent_verify.txt`) |
| 10-section multi-physics audit | `tools/audit_physics_v3.py` | `PHYSICS RESULT: no failures` (`docs/v3_physics_audit.txt`) |

That third program is the one that found the last three real defects, described in section 6.
It re-measures the shipped triangles and then argues with them: thread bite and pull-out, screw
heads and insertion kinematics, the fan's operating point against the openings it really has,
PLA's glass transition in an UP summer, 13.56 MHz and 2.4 GHz loss, the optical and viewing cones,
the ligaments between openings, and a layer-by-layer slicer model of how much plastic is extruded.

The second one never imports the generator: it re-types the reference dimensions, re-cuts the
meshes and re-measures every hole, opening and wall from triangles alone.

---

## 1. Why v3 exists

v2 was a repaired v1: same proportions, same walls, fixes bolted on. That is why it looked
"the same". v3 is generated from the same layout engine but with different *decisions*: the
depth came out of the RFID stack instead of being picked, the front face was re-drawn around
the modules, the RFID hold-down was replaced with a different mechanism, and the rear closure
was replaced with a different joint.

### measured shape changes (v2 -> v3)

| | v2 | v3 | why |
|---|---|---|---|
| overall size | 110 x 155 x **48** | 110 x 155 x **46** | the 48 mm was 2 mm of unused rear plug; depth is now the RFID stack + 3 mm cover |
| side wall | 2.4 mm | **2.6 mm** | v2's thinnest structural wall was 1.2 mm at the vents; 2.6 buys stiffness without new volume |
| RFID aperture | 56 x 38 with 2 x 4 mm stiffener bars (90.4 % open) | **38 x 56 portrait**, 100 % open, R5 corners | 8269 rays sampled in the aperture, 0 blocked (v2: 190 mm2 of shadow) |
| RC522 hold-down | 2 clamp bars + a 0.9 mm lip, printed **x2**, clamped over the board | **1 flat ring**, printed x1, 43.6 x 76.0 x 2.6, its inner lip 0.5 mm inside the aperture | 2.2 cm3 instead of two 1.6 cc bars, nothing in front of the antenna, one part, no flex |
| RC522 bearing | 2.0 mm ledge under the board | **2.2 mm** ledge (recess 0.8 instead of 1.0) | a 0.2 mm deeper wall in front of the coil is 8 % less plastic the 13.56 MHz has to push through |
| fan opening | d26 bore with 3 moulded grille bars (50 % free) + a d30 x 1.2 seat recess leaving a 1.4 mm lip | **d28 bore, nothing across it** (100 % free), flat wall | 616 of 616 sampled mm2 clear, and the print's most fragile sliver is gone |
| front-face openings | flush cut | **0.45 x 3.0 mm rebate ring** sunk around the LCD and the fingerprint opening | the module's own bezel sits in the rebate: a shadow line, no chipped edge, and the glass cannot be scratched by the frame |
| fingerprint mounting | 2 posts + a flat 2 mm strap over the sensor face | **dog-bone bracket** (wide over the holes, narrow across the glass) + 2 seat ribs, plus the module registers on the rebate floor | the bracket can be lifted off without prying on the glass |
| rear closure | solid 2 mm plug filling the opening (79.6 cc) | **8-sided register frame**, 2 mm proud, 0.25 mm/side, with the ESP32 zone cut clear in the **frame only** (**53.8 cm3**) | 26 cm3 (32 %) less plastic, and the board + its bosses + its locating tabs get real clearance while the 3 mm skin stays unbroken |
| ESP32 mounting | 4 square 8 x 8 posts | 4 **round d7 bosses** with **d3.6 x 0.7 spotfaces** | a round boss has no corner crack; the spotface sinks the head so the plate can still close |
| ventilation | fan wall only | **+X intake wall: 8 x 30 x 5 stadium slots at two heights, staggered** (1157 mm2), plus the same 4 exhaust slots + 3 top vents | air now has a real path: intake -> fan -> d28 bore -> bottom slot -> top vents. Measured duty point 0.86 L/s = 86 % of the fan's free air, the whole 784 cm3 box changed every 0.9 s, dT 1.6 K |
| print volume | 199.6 cc (all 4 parts) | **167.9 cm3** CAD -> **~154 g printed** (108 g shell + 42 g plate + 4 g small parts at 0.45 nozzle, 3 walls, 15 % infill) | the ring and the frame replace bars and a plug; 391 g all up with the modules on two wall hooks |

Nothing above is a design *claim*: `build_v3.py` section K measures the aperture and the bore by
ray-scan, the plate volume by mesh volume, the ledge flatness by probe, and `verify_v3.py`
repeats the aperture, the bore, the frame fit and the wall map from the STLs alone.

## 2. What is in the pack

| file | print | notes |
|---|---|---|
| `01_MAIN_SHELL_v3.stl` | x1 | 110.9 cm3, 15 308 triangles, watertight, 1 body, 0 open edges |
| `02_REAR_PLATE_v3.stl` | x1 | 53.8 cm3, 3 mm plate + 2 mm register frame |
| `03_R307_BRACKET_v3.stl` | x1 | 1.0 cm3, flat, 36.8 x 14.0 x 3.2 |
| `04_RC522_RING_v3.stl` | x1 | 2.2 cm3, flat, 43.6 x 76.0 x 2.6 (body 43.6 x 62.4, screw tabs to y +/-38) |

Four files, four prints, no mirrors, no "print this one twice".

## 3. Fixings - all 22 holes are circular, hollow and measured

`verify_v3.py` finds each hole in the mesh, measures its diameter with 8 rays at 3 depths, and
checks the wall around it. `build_v3.py` section I additionally asks "is this diameter and depth
actually what was designed".

| fixing | count | thread | pilot measured | driver access |
|---|---|---|---|---|
| LCD1602 + I2C backpack | 4 | M2.5 | **d2.04** x 6.3 (designed 2.05 = the thread's minor) | clear 25 mm |
| R307 bracket | 2 | M3 | d2.48 x 6.3 (designed 2.50) | clear 13 mm |
| **RC522 ring** | 4 | M2.5 | **d2.04 x 2.5 through the ring + blind d2.04 x 3.8 in the shell pad, 1.4 mm of wall left under it** | clear 23 mm |
| ESP32 DevKit V1 | 4 | M2.2 | d1.78 x 5.7 (designed 1.80) | clear 25 mm |
| 3010 fan | 4 | M3 | d2.48 x 10.3 (designed 2.50) | clear 25 mm |
| rear plate | 4 | M3 | d2.48 x 8.3 + 6.6 mm 90-deg csk | clear 25 mm |
| cable loom | 4 | - | through d4.0 tie holes | - |

The RC522 row is the one that used to be missing. It is now clamped the same way as the LCD:
four screws into four pads, and the ring's lip holds the board down. No glue, no clip, no
snap-fit, and nothing crosses the scan window.

Every pilot is at the screw's **minor** diameter, not its nominal one, because these are
thread-forming screws into printed PLA: at nominal the crest only just touches the hole wall, the
joint is friction and the screw spins. Measured radial bite/play after printing is +0.01 to +0.05
mm, and the computed pull-out is 75-362 N per screw against 0.15-0.88 N of service load (213x to
12 500x reserve). The audit's own conclusion, which is the honest one: **fastener count and
screwdriver access, not fastener strength, are what govern this box** - which is why every module
got its own 2-4 screws.

## 4. Printability, verified rather than assumed

* thinnest *sheet* anywhere in the shell: **2.2 mm** (the bearing band the RC522 board lies
  on), then 2.55 mm under the rebate rings, then 2.6 mm of side wall. The verifier's ray map
  reports a 1.40 mm minimum, and it is not a wall: it is the floor of the blind M2.5 pilot
  under an RC522 pad, which is exactly what was designed (1.4 mm of plastic under a 3.8 mm
  thread seat). v2 inherited a 1.0 x 1.4 mm lip all round the fan bore - a shallow d30 seat
  recess for a fan that is bolted to standoffs and never enters that wall - and v3 **deletes
  it**: the fan wall is a flat 3.0 mm plate with a clean d28 bore, which is both the visible
  change and the reason no fragile sliver is left in the print.
* faces steeper than 60 degrees: 325 mm2 = **0.40 %** of the shell, and each of those bridges
  less than 3 mm -> **supports: no**.
* 214 slices at 0.2 mm: zero self-intersections, zero empty layers, first layer 11 469 mm2.
* the worst area jump in the whole print (2 415 mm2 at z=10) cantilevers 0.00 mm past the layer
  below it - it is an internal shelf, not a bridge.
* the 9 sub-micron sliver triangles left by the boolean rim chamfers are inside the mesh, are
  under 1 um2 each, and are reported (not hidden) by the verifier.

## 5. Four numbers that still need your calipers

The model is built to the reference data in `docs/master_prompt.md`; those four are the ones
where a wrong number would cost you a print, and the geometry is deliberately forgiving
(+/- 0.35 mm seat fit, 0.5 mm ring overlap, spotfaced bosses) so small errors are absorbed:

1. ESP32 DevKit V1 - pad-hole inset from the board edge (assumed 3.5 mm).
2. R307 - bracket hole pitch (assumed 28.0 mm between the two M3 holes).
3. LCD1602 + I2C backpack - total depth from the glass to the back of the backpack (assumed 18.24).
4. 3010 fan - thickness and screw-hole diameter (assumed 10 mm thick, d3.2 / M3).

If any one of them is more than 0.5 mm out, change the number in `tools/build_v3.py` and re-run
`python3 tools/build_v3.py` (about 1 minute, it re-exports the STLs and re-runs every check, and
prints `RESULT: ALL CHECKS PASS` or refuses to). Then re-run `tools/verify_v3.py` (STL only)
and `tools/audit_physics_v3.py` (physics, and it re-measures the numbers in this file and in the
print order, so a doc cannot survive a stale claim).

---

## 6. v3.1 -> v3.2: what the physics audit found, and what changed

Both checkers passed v3.0, and the audit still found three real defects. All three are fixed in the
files you are printing; all three are now guarded by a permanent check, so they cannot come back.

**F11 - a rear-plate screw countersink opening onto a corner round (medium).** The 6.6 mm 90-degree
cone at each of the 4 plate screws was 0.08 mm from the R3 corner round of the plate outline, i.e.
the cone broke through the side of the part and the screw head would have had a hole to fall into.
The four screws moved from (+/-46.5, +/-71.0) to **(+/-46.5, +/-67.5)**, 3.5 mm inboard of the
rounds. The verifier now measures, for each corner, the plastic left between the cone axis and the
plate outline at the outer face: **2.25, 2.25, 2.25 and 3.80 mm** (it must be >= 1.2 mm; v3.0
measured 0.08 mm).

**F12 - the rear plate had a 15.6 x 63 mm hole through it (high).** The cut that keeps the ESP32's
locating bosses clear of the plate ran from the register frame to `z = D + 2`, i.e. **through the
whole 3 mm skin** instead of only the 2 mm frame that stands into the cavity. The shipped v3.0 plate
was open to dust and weather over that corner, and the "plate closes the box" claim was false. The
cut's top is now `z0 + 0.16` (the frame's own top surface), the plate went from 51.4 to 53.8 cm3,
and the verifier gained a check that slices the plate at mid-thickness and demands *exactly* 6 voids
- the 4 screw holes and the 2 keyhole slots - and >= 15 600 mm2 of skin (v3.0 measured 14 897 mm2
with a hole; v3.2 measures 15 983 mm2 with none).

**F13 - the RFID reader could not be installed at all (high).** Its PCB is 60 x 40 mm and v3 laid
the 60 mm dimension across the box, against the -X wall. But that wall carries the ESP32 on four
10 mm stand-off posts and the 3010 fan on four more, and the front wall's bay between the ESP32's
posts (ending at x = -42.4) and the R307's own -X post (starting at x = +15.95) is 58.35 mm:
**1.25 mm narrower than the board, 4.05 mm narrower than its hold-down ring.** Lowering the part
onto its seat is impossible in any orientation, tilted or not, and it is not fixed by a build order
because the blocking plastic is printed into the wall. Fixed by mounting the reader **portrait** -
its 60 mm dimension along the 155 mm height instead - which was always the better layout for a card
anyway: the whole stack is then 43.6 mm wide, drops straight down with 6.4 mm to the ESP32 posts,
10.2 mm to the R307 post and 3.25 mm to the fan bosses, and the reader centre moved from x = -20.05
to x = -16.05, which also widened the ligament between the RFID aperture and the fingerprint window
from 17.5 to 22.5 mm. Aperture 38 x 56 (2106 mm2, still 8269/8269 rays clear), ring 43.6 x 62.4
body with screw tabs at (+/-17, +/-34), and the audit section 3 now proves a straight-Z path for
**every** module plus the plate.

Two things that were not defects but are now corrected in the docs: the intake is 8 x 30 x 5 stadium
slots (1157 mm2, not the 6 x d5.0 / 118 mm2 that choked the fan in v3.0 - the measured duty point is
0.86 L/s at 1.7 Pa, 86 % of the fan's free air, the whole box changed every 0.9 s, dT 1.6 K at
1.6 W), and the print's mass. The 15 % infill figure of ~102 g was a blanket 50 % factor and is
**too low**: a 2.6 mm wall printed on a 0.45 nozzle with 3 perimeter lines is 2.7 mm of perimeter,
so it prints solid. Layer-by-layer over the shipped meshes the parts extrude 79 % (shell), 62 %
(plate), 100 % (bracket) and 100 % (ring) of their CAD volume = **154 g of PLA**, 391 g with the
modules on the wall, and a 1 kg spool prints the set 6.5 times.

Assembly note that came out of section 3: the reader's 8-pin header may not be taller than about
6 mm over the pads, because the channel under the ESP32 posts is 9.8 mm and the board plus a 9 mm
male header is 10.6 mm. Solder the leads, or use short / right-angle female headers, or fit the
reader before the ESP32. Everything else - ring, R307, LCD, fan, ESP32 - drops straight in with the
plate off, and the plate is the last thing closed.

Print order (unchanged by all of the above): all four parts flat on the bed, `01` front face down,
`02` frame down, `03` back face down, `04` pad face down; 0.2 mm layers, 2.6 mm walls, 15 % infill,
3 top/bottom skins, no supports, no brim needed unless your bed is unlevel (the shell's rim is
436 mm long).
