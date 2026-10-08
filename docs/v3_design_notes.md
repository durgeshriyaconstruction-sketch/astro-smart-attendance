# Astro Smart Attendance - enclosure **v3**, the complete re-design

Everything in this file is a measurement of the shipped `cad/v3/*.stl` files, not an intention.
Two independent programs had to agree before a single line was written here:

| check | program | result |
|---|---|---|
| parametric audit A-K | `tools/build_v3.py` | `RESULT: ALL CHECKS PASS` (`docs/v3_audit.txt`) |
| STL-only verification | `tools/verify_v3.py` | `INDEPENDENT RESULT: ALL CHECKS PASS` (`docs/v3_independent_verify.txt`) |

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
| RFID aperture | 56 x 38 with 2 x 4 mm stiffener bars (90.4 % open) | 56 x 38, **100 % open**, R5 corners | 8269 rays sampled in the aperture, 0 blocked (v2: 190 mm2 of shadow) |
| RC522 hold-down | 2 clamp bars + a 0.9 mm lip, printed **x2**, clamped over the board | **1 flat ring**, printed x1, its inner lip 0.5 mm inside the aperture | 3.0 cm3 instead of 2 x 1.58 cm3 of bars, nothing in front of the antenna, one part, no flex |
| RC522 bearing | 2.0 mm ledge under the board | **2.2 mm** ledge (recess 0.8 instead of 1.0) | a 0.2 mm deeper wall in front of the coil is 8 % less plastic the 13.56 MHz has to push through |
| fan opening | d26 bore with 3 moulded grille bars (50 % free) + a d30 x 1.2 seat recess leaving a 1.4 mm lip | **d28 bore, nothing across it** (100 % free), flat wall | 616 of 616 sampled mm2 clear, and the print's most fragile sliver is gone |
| front-face openings | flush cut | **0.45 x 3.0 mm rebate ring** sunk around the LCD and the fingerprint opening | the module's own bezel sits in the rebate: a shadow line, no chipped edge, and the glass cannot be scratched by the frame |
| fingerprint mounting | 2 posts + a flat 2 mm strap over the sensor face | **dog-bone bracket** (wide over the holes, narrow across the glass) + 2 seat ribs, plus the module registers on the rebate floor | the bracket can be lifted off without prying on the glass |
| rear closure | solid 2 mm plug filling the opening (79.6 cm3) | **8-sided register frame**, 2 mm proud, 0.25 mm/side, with the whole ESP32 zone cut clear (**52.8 cm3**) | 27 cm3 (34 %) less plastic, and the board + its bosses + its locating tabs get real clearance |
| ESP32 mounting | 4 square 8 x 8 posts | 4 **round d7 bosses** with **d3.6 x 0.7 spotfaces** | a round boss has no corner crack; the spotface sinks the head so the plate can still close |
| ventilation | fan wall only | **+X intake wall: 6 x d5.0 holes at two heights, staggered**, plus the same 4 exhaust slots + 3 top vents | air now has a path: intake -> fan -> d28 bore -> bottom slot -> top vents, and no hole breaks an ESP32 boss |
| print volume | 199.6 cm3 (all 4 parts) | **169.2 cm3** -> ~105 g PLA at 15 % | the ring and the frame replace bars and a plug |

Nothing above is a design *claim*: `build_v3.py` section K measures the aperture and the bore by
ray-scan, the plate volume by mesh volume, the ledge flatness by probe, and `verify_v3.py`
repeats the aperture, the bore, the frame fit and the wall map from the STLs alone.

## 2. What is in the pack

| file | print | notes |
|---|---|---|
| `01_MAIN_SHELL_v3.stl` | x1 | 112.4 cm3, 14 834 triangles, watertight, 1 body, 0 open edges |
| `02_REAR_PLATE_v3.stl` | x1 | 52.8 cm3, 3 mm plate + 2 mm register frame |
| `03_R307_BRACKET_v3.stl` | x1 | 1.0 cm3, flat, 36.8 x 14.0 x 3.2 |
| `04_RC522_RING_v3.stl` | x1 | 3.0 cm3, flat, 62.4 x 63.0 x 2.6 (tabs to y +/-31.5) |

Four files, four prints, no mirrors, no "print this one twice".

## 3. Fixings - all 22 holes are circular, hollow and measured

`verify_v3.py` finds each hole in the mesh, measures its diameter with 8 rays at 3 depths, and
checks the wall around it. `build_v3.py` section I additionally asks "is this diameter and depth
actually what was designed".

| fixing | count | thread | pilot measured | driver access |
|---|---|---|---|---|
| LCD1602 + I2C backpack | 4 | M2.5 | d2.50 x 8.5 | clear 25 mm |
| R307 bracket | 2 | M3 | d2.50 x 8.0 | clear 13 mm |
| **RC522 ring** | 4 | M2.5 | **d2.20 x 3.8 in the ring + blind d2.2 x 3.8 in the shell, 1.4 mm of wall left under it** | clear 23 mm |
| ESP32 DevKit V1 | 4 | M2.2 | d2.20 x 7.0 | clear 25 mm |
| 3010 fan | 4 | M3 | d2.50 x 12.0 | clear 25 mm |
| rear plate | 4 | M3 | d2.50 x 9.0 + 6.6 mm 90-deg csk | clear 25 mm |
| cable loom | 4 | - | through d4.0 tie holes | - |

The RC522 row is the one that used to be missing. It is now clamped the same way as the LCD:
four screws into four pads, and the ring's lip holds the board down. No glue, no clip, no
snap-fit, and nothing crosses the scan window.

## 4. Printability, verified rather than assumed

* thinnest *sheet* anywhere in the shell: **2.2 mm** (the bearing band the RC522 board lies
  on), then 2.55 mm under the rebate rings, then 2.6 mm of side wall. The verifier's ray map
  reports a 1.40 mm minimum, and it is not a wall: it is the floor of the blind M2.5 pilot
  under an RC522 pad, which is exactly what was designed (1.4 mm of plastic under a 3.8 mm
  thread seat). v2 inherited a 1.0 x 1.4 mm lip all round the fan bore - a shallow d30 seat
  recess for a fan that is bolted to standoffs and never enters that wall - and v3 **deletes
  it**: the fan wall is a flat 3.0 mm plate with a clean d28 bore, which is both the visible
  change and the reason no fragile sliver is left in the print.
* faces steeper than 60 degrees: 329 mm2 = **0.41 %** of the shell, and each of those bridges
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
prints `RESULT: ALL CHECKS PASS` or refuses to). Then re-run `tools/verify_v3.py`.
