# Astro Smart Attendance - enclosure **v3**, the complete re-design

Everything in this file is a measurement of the shipped `cad/v3/*.stl` files, not an intention.
Box: **110 x 155 x 46 mm** outer, walls 2.6 mm on the sides and 3.0 mm front / rear / top,
plate 3.0 mm skin + 2 mm register frame, 22 self-tapping pilots at thread minor diameter
(M2.5 -> 2.05, M2.2 -> 1.80, M3 -> 2.50), plain side walls, and since v3.4 one hole: the d28 fan
bore is the **only air opening** on the box - the twelve grille slots v3.3 cut were filled in by
request - no supports anywhere.
All four files are **bed-aligned**: the orientation a printer must see is baked into the triangles
(`tools/orient_v3.py` is the single source of truth, and the verifier undoes that one translation
before it asserts anything in the design frame).
Four independent programs had to agree before a single line was written here:

| check | program | result |
|---|---|---|
| parametric audit A-K | `tools/build_v3.py` | `RESULT: ALL CHECKS PASS` (`docs/v3_audit.txt`) |
| STL-only verification | `tools/verify_v3.py` | `INDEPENDENT RESULT: ALL CHECKS PASS` (`docs/v3_independent_verify.txt`) |
| 10-section multi-physics audit | `tools/audit_physics_v3.py` | `PHYSICS RESULT: no failures` (`docs/v3_physics_audit.txt`) |
| groove + printed-fit walk | `tools/check_grooves_v3.py` | `EVERY GROOVE AND FIT MEASURES AS DESIGNED` - 34 values, each probed at 0.02 mm through the shipped STLs (`docs/v3_groove_check.txt`) |

That third program is the one that found the last three real defects, described in section 6.
It re-measures the shipped triangles and then argues with them: thread bite and pull-out, screw
heads and insertion kinematics, the fan's operating point against the openings it really has,
PLA's glass transition in an UP summer, 13.56 MHz and 2.4 GHz loss, the optical and viewing cones,
the ligaments between openings, and a layer-by-layer slicer model of how much plastic is extruded.

The second one never imports the generator: it re-types the reference dimensions, re-cuts the
meshes and re-measures every hole, opening and wall from triangles alone. The fourth one is the
answer to "is the size and the fitting of the groove 100 %": it does not check the *design*, it
walks a probe line through each rebate, recess, lip and hole in the file you print and prints the
number the plastic actually offers - mouth 72.00 x 23.53 for the LCD, depth 0.438, through-window
66.00 x 17.53; R307 opening 21.01 x 25.01 around a 19.3 x 21.2 lens; RC522 recess 44.73 x 62.72
x 0.798 deep leaving a 2.197 mm ledge, aperture 38.01 x 56.00; register lip 104.305 x 148.503 in
a 104.785 x 148.982 opening = 0.240 mm per side; keyhole 7.531 x 4.614 at 50.01 span; ring
opening 37.008 x 55.002 so its lip stands 0.50 mm inside the aperture; ring body 2.611 with 1.097
left under the 1.503 head recess; and the ring's four pads and its rim level to 0.001 mm. Every
one of those agrees with the intent within 0.035 mm, which is the probe's own 0.02 mm quantisation
plus rounding - i.e. the plastic is where it was told to be.

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
| ventilation | fan wall only, everything else choked | **v3.4: one opening, the one that moves air.** The d28 fan bore in the -X wall is the only air hole on the box (615 mm2, fan blows IN) and the bottom wall keeps just the USB opening; v3.3's 8-slot bottom + 4-slot top grilles (1069 mm2, 1.74x the bore) are solid plastic. See sections 7 and 9 | air has a real path, the walls are not perforated for nothing, and nothing on the box is an opening without a duty |
| print volume | 199.6 cc (all 4 parts) | **172.2 cm3** CAD -> **159 g printed** (114 g shell + 42 g plate + 4 g small parts at 0.45 nozzle, 3 walls, 15 % infill) | the ring and the frame replace bars and a plug; 396 g all up with the modules on two wall hooks |

Nothing above is a design *claim*: `build_v3.py` section K measures the aperture and the bore by
ray-scan, the plate volume by mesh volume, the ledge flatness by probe, and `verify_v3.py`
repeats the aperture, the bore, the frame fit and the wall map from the STLs alone.

## 2. What is in the pack

| file | print | notes |
|---|---|---|
| `01_MAIN_SHELL_v3.stl` | x1 | 115.2 cm3, 11 108 triangles, watertight, 1 body, 0 open edges |
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
* faces steeper than 60 degrees: 244 mm2 = **0.30 %** of the shell (v3.3 measured 296 mm2 =
  0.36 % - filling the grilles in removed 52 mm2 of slot rims), and each of those bridges less
  than 3 mm -> **supports: no**.
* 214 slices at 0.2 mm: zero self-intersections, zero empty layers, first layer 11 469 mm2 (the
  footprint did not change - the shell's outline is the same 110 x 155 mm front face).
* the worst area jump in the whole print is 794 mm2 of new wall at z=0.6 and it cantilevers
  0.20 mm past the layer below (v3.3's worst was 2 415 mm2 at z=10 with a 0.00 mm cantilever);
  2 634 mm2 is added over the whole 43.0 mm of print, 0.47 % of the layer sum.
* the 10 sub-micron sliver triangles left by the boolean rim chamfers are inside the mesh, are
  under 1 um2 each, and are reported (not hidden) by the verifier.

## 5. The four numbers that used to need your calipers  *(all four closed 2026-10-08 -> section 10)*

These were the ones where a wrong number would cost a print, and the geometry is deliberately
forgiving (+/- 0.35 mm seat fit, 0.5 mm ring overlap, spotfaced bosses) so small errors are
absorbed.  Every line below is now checked against published vendor data instead of against your
drawer - what each one turned out to be:

1. ESP32 DevKit V1 - pad-hole inset from the board edge: 3.5 mm, still the modelled value, and
   corroborated by the closest published drawing in the family (wESP32 puts its 3.0 mm pad holes
   3.5 mm from the edge).  DOIT's own hole *diameter* is the one number that stays unpublished
   (2.5 mm reported by owners, 3.0 mm on that drawing): it decides M2.2 vs M2 and nothing else.
2. R307 - bracket hole pitch: there is no such pitch.  The module has no mounting holes; the stock
   kits clamp it with a bracket and two long screws, so the 28.0 mm between our posts is a choice
   we made to clear the antenna end and the corner posts, and it cannot be wrong.
3. LCD1602 + I2C backpack depth: 13.2 / 18.24 / 20.0 mm depending on whose backpack - the pocket
   reserves 24.0 behind the glass, so the deepest one on sale fits with 4 mm to spare.
4. 3010 fan - thickness and hole size: 30 x 30 x 10 with a 24 +/- 0.3 mm pattern and four 3 mm
   holes, exactly as modelled; the +/- 0.3 is taken up by the M3 shank inside the lug hole.

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

Two things that were not defects but are now corrected in the docs: the air path, and the print's
mass.  The air path went through two changes: v3.1/v3.2 opened 8 x 30 x 5 mm stadium slots in the
+X wall (1157 mm2) because the 6 x d5.0 / 118 mm2 of v3.0 choked the fan; then **v3.3 deleted those
side slots** and moved the inlet into the fan's own bore (see the v3.3 section below). The 15 % infill figure of ~102 g was a blanket 50 % factor and is
**too low**: a 2.6 mm wall printed on a 0.45 nozzle with 3 perimeter lines is 2.7 mm of perimeter,
so it prints solid. Layer-by-layer over the shipped meshes the parts extrude 79 % (shell), 62 %
(plate), 100 % (bracket) and 100 % (ring) of their CAD volume = **159 g of PLA**, 396 g with the
modules on the wall, and a 1 kg spool prints the set 6.3 times (53.0 m of 1.75 mm filament).
(`verify_v3`'s typed per-part fractions put the same print at 158 g - 0.6 % apart, both quoted
rather than smoothed, because the two are different samplings of one model.)  Those
those are the v3.4 figures; the grilles v3.3 left in the bottom and top walls were worth 3.2 cc of
plastic and 3 g of it.

Assembly note that came out of section 3: the reader's 8-pin header may not be taller than about
6 mm over the pads, because the channel under the ESP32 posts is 9.8 mm and the board plus a 9 mm
male header is 10.6 mm. Solder the leads, or use short / right-angle female headers, or fit the
reader before the ESP32. Everything else - ring, R307, LCD, fan, ESP32 - drops straight in with the
plate off, and the plate is the last thing closed.

Print order (unchanged by all of the above): all four parts flat on the bed, `01` front face down,
`02` frame down, `03` back face down, `04` pad face down; 0.2 mm layers, 2.6 mm walls, 15 % infill,
3 top/bottom skins, no supports, no brim needed unless your bed is unlevel (the shell's rim is
436 mm long).

---

## 7. v3.2 -> v3.3: the fan does the work, so the side grooves went away  *(v3.3, superseded below)*

Asked for directly: *"remove the right side many grooves - for that I have fan"*.  The eight stadium
slots in the +X wall went, and that wall is solid 2.6 mm plastic - the independent checker
slices it at mid-thickness and finds **0 voids**, still true in v3.4.  A fan still has to move air
through *something*, so the duty moved instead of disappearing, and the numbers below are what the
v3.3 STLs measured - the history of where the openings were, with v3.4's change in section 9:

| | v3.2 | v3.3 (then v3.4, section 9) |
|---|---|---|
| inlet | 8 x 30 x 5 mm slots in the +X wall, 1157 mm2 | the **d28 fan bore itself** in the -X wall: 615 mm2, measured 615 of 616 clear |
| fan direction | blowing OUT (exhaust) | **blowing IN** - the arrows moulded on the fan's frame point at the box |
| outlet | 4 x (20 x 4) bottom + 3 x (16 x 3) top, 452 mm2 | **8 x (21 x 4.5) bottom + 4 x (21 x 4) top = 1069 mm2**, 1.74x the bore - all twelve of those slots are filled in now |
| right (+X) wall | perforated over 4 of its 6 rows of features | plain; nothing to sand, nothing to crack, and the ESP32 bosses keep their full wall behind them |

The rule as it stood then was from the master prompt - the passive set must stay **>= 1.5x the fan
bore** - and it is that rule, not the geometry, that v3.4 replaces with a different one (section 9).
Everything else about the path was deliberate, and stays true of the walls as they now stand:

* bottom grille (v3.3, now solid): 21.00 x 4.50 mm slots in 4 columns (+/-12.5, +/-37.5) at 2 heights (z 7.0 and 15.0),
  every corner rounded r1.6 (r1.2 in the top wall) so there is no corner to start a crack - which
  also means each one measures 92.3 mm2 of free area, not the 94.5 mm2 of a sharp rectangle;
* top grille: 21.00 x 4.00 mm, 4 slots at z 26, i.e. the warmest air above the board level;
* 3.50 mm of plastic between the two rows, 4.00 mm between the columns - never thinner than the
  3.0 mm wall they are cut in;
* the lowest slot edge sat 1.75 mm clear of the front wall's inner face, and 4.6 mm clear of the
  20.4 x 12.4 mm USB opening in the same wall - that opening is the one thing left in it;
* pressurising the box rather than evacuating it is the better direction for this unit: it pushes air
  out through the RFID aperture and the LCD rebate, which is what keeps dust from being sucked in
  around the R307 prism.

Two options were rejected with numbers, not taste.  Sealing the +X wall and leaving v3.2's grilles
would have dropped the passive set to 452 mm2 = 0.73x the bore: the fan would have run close to its
own choke point and the box would have been a negative-pressure dust collector.  The first v3.3 cut
- rows of 5 mm slots at z 7 and 14.5 - failed the audit outright:
`web between neighbouring bottom grille openings  2.50 mm minimum  FAIL`, a ligament thinner than
the wall around it.  Dropping the slot height to 4.5 and opening the rows to 7 / 15 gave 3.50 mm of
web, and widening the slots 18 -> 21 mm at a 25 mm pitch (still 4.00 mm between neighbours) paid the
area back with interest: 985 mm2 -> 1069 mm2 of outlet.

Duty point against the fan's straight line, as section 4 of the physics audit measured it **on the
v3.3 mesh**: A_eff 533 mm2 -> 0.84 L/s at 1.9 Pa, 84 % of the fan's free air, the whole 784 cm3 box
changed every 0.9 s, dT 1.6 K at 1.6 W.  That was the same duty point v3.2 measured (0.86 L/s) with
a wall full of holes in it, reached with the passive openings alone and no perforation in the side
wall; the bottom grille was 8 x 21 x 4.5 mm and the top 4 x 21 x 4 mm, which is where the
1069 mm2 came from.  With the grilles filled in the flow is smaller and the box is no cooler - that
is section 9's measurement, not this one.
Nothing in this section is load-bearing on the geometry switch alone: setting `P["side_intake"] = True`
in `tools/build_v3.py` puts v3.2's perforated wall back in one rebuild, `P["grilles"] = True` puts
v3.3's twelve slots back, and the build's self-test changes its checks to match either way.  Those
flags exist so these decisions can be reversed without archaeology; they are not hidden second
designs - the shipped model is the one with `side_intake=False, grilles=False`.


## 8. The fifth print: `05_FIT_GAUGE_v3.stl`, a card that answers the five open questions  *(kept in the repo, out of the pack from v3.5)*

Section 5 left five numbers owned by your hardware rather than by any datasheet I could read from
here - which pilot your boss actually bites, what size the hole in your PCB really is, whether the
1602 window and its 75.1 x 31.0 pitch are your module, whether the R307's bezel clears a 21 x 25
relief, and whether the RC522 board and its pads sit where the ledge is.  Those are all *size*
questions, so they do not need a box to answer them: they need a printed thing of known size.  The
card is that thing - 150 x 112 x 2.60 mm, print-flat, 40 minutes, and every number on it read out
of `tools/build_v3.py` at build time rather than typed a second time.

Two conventions, and only two, because a gauge that mixes them is unreadable:

* **a cut is a GO gauge.**  The card is 2.60 thick and the hole in it is the hole in the wall, to
  the micron, so anything that drops through the cut fits the box.  A pass here is a pass there;
  that is the whole promise, and `tools/check_gauge_v3.py` measures it rather than asserting it.
* **an engraved line is a reference outline** - the board, the pitch, the prism window, the ledge -
  0.50 mm deep, to be read with calipers or felt with a fingernail.

Seven stations: six blind pilots (d1.80 / 2.00 / 2.05 / 2.20 / 2.35 / 2.50 at 8.00 deep, each
leaving 4.60 mm of solid boss under it), four through-board-holes (d2.00 to d2.70), the 1602 window
and its pitch crosses, the R307 relief plus the prism window and body outline, the RC522 board at
+0.40 a side with its ledge and four pads, the USB opening as the wall has it, and a 100 mm rule
ticked every 10 mm so a printer that shrinks the whole set is found out first.  The card's own
thickness is also the shim unit: 2.60 mm, the height of one wall, so stacking two says 5.20.

What it cannot do, said plainly: it cannot tell you how *tall* a module is, or whether an LCD's
contrast survives a 1.6 mm shelf.  Those are the box's own geometry and they are measured in
`docs/v3_groove_check.txt`.  The card settles the sizes; the box still has to be test-fitted.

Three real defects were caught building it, which is what a self-check is for:

* the first boolean produced 12 open edges.  Cause: thirty engraved pockets extruded as separate
  prisms with coplanar walls touching each other.  Fixed by unioning every pocket that shares a
  plane in 2-D and extruding once - which also dropped the file from 32 958 to 16 208 triangles.
* `is_watertight` said True while the normals pointed *inward*.  A slicer handed that STL may print
  the card hollow.  Fixed with `fix_normals()` in the builder, and the build now refuses to write a
  file unless `is_watertight and is_volume and volume > 0` (`GAUGE BUILD: ALL CHECKS PASS`).
* the first checker reported `watertight=False` for a part that was fine, because its probe asked
  "how many void stretches are in this window" instead of "which stretch contains the centre".  A
  probe line that crosses the far side of the part on its way to the window edge is not a second
  void.  The rule now used everywhere: the interval that contains the probe centre, refined by
  bisection - and it must back off *two* samples, not one, because a sample can land exactly on a
  surface (that is where a d1.80 pilot read 1.750 for one run: half a step on each side).

The wall comparison is deliberately not a min-of-three-planes statistic any more.  Profiling the
front wall at five planes showed a 0.05 mm disagreement on one plane - a grazing ray on a vertex,
not a taper - so the checker now reports the spread as its own row (`LCD width is a clean prism`,
0.000 to 0.050 mm) and compares the *median* against the card, requiring the card never to be the
bigger of the two.  That row can still fail, and fails if a wall ever does taper.

The card is registered everywhere a part has to be: `tools/orient_v3.py` (`0.0`, printed flat,
engraved face up), the pack's STL list, its figure list, the offline viewer, and the print order -
where it is step 0, before the shell, which is the entire point of it.


## 9. v3.3 -> v3.4: one hole, not twelve - the grilles are gone

Asked for directly, pointing at the hollows in the side of the box: *"remove all unnecessary ... no
need for those hollows, only let that DC fan one - not more, and last check"*.  So every grille slot
was filled in.  The bottom wall loses its 8 x (21 x 4.5) grille and keeps **only the USB opening**
(20.4 x 12.4 mm, a cable hole, never an air one); the top wall loses its 4 x (21 x 4) grille and has
no opening left at all; the +X wall was already plain in v3.3 and still is.  What is on the box now:

| wall (measured at mid-thickness off the shipped STL) | v3.3 | v3.4 |
|---|---|---|
| bottom (-Y) | 8 slots + USB, 9 voids | **1 void**: the 20.40 x 12.40 mm USB opening |
| top (+Y) | 4 slots, 4 voids | **0 voids** |
| right (+X) | 0 voids | 0 voids |
| left (-X) | d28 bore, 615 mm2 | **d28 bore, 615 mm2 - the only air opening** |

That inventory is not a claim in a document, it is `tools/verify_v3.py` section 6b, run on the STL
and nothing else, and it also fires 9 sample rays at each of the twelve old slot centres and both
ends of every slot (36 probes, 324 rays) which all have to be *blocked*: a slot that came back would
let them through.  `tools/make_grille_map_v3.py` draws the same four sections and exits non-zero
unless the counts are 1 / 0 / 0 / 1.

**What the change costs, measured rather than argued.**  The openings were the *flow* path; the heat
mostly leaves through the *skin*, and the skin did not change.  Section 4 of the physics audit now
computes both:

* passive: 1.6 W (ESP32 in TX bursts + RC522 + the fan's own draw) over 0.0585 m2 of PLA at
  h = 10 W/m2.K -> **dT = 2.7 K** above ambient; at h = 5 (a closed cabinet, no air movement) 5.5 K;
* through-flow: the fan has only the bore in front of it and the plate's register seam to get out
    of, 509 mm of frame x 0.25 mm of clearance = 127 mm2 *[this one row is an ASSUMPTION about your
  print, and the audit records it as a note, never as a gate]* -> A_eff 125 mm2 -> **0.25 L/s at
  12.2 Pa**, 25 % of the fan's free air, the 784 cm3 box changed every 3.2 s, dT 5.4 K;
* the two paths are in parallel, so the box settles at **dT = 1.8 K**.  v3.3 measured 1.6 K with
  1069 mm2 of grille open, so closing all twelve slots is worth **0.2 K**: the through-flow fell
  from 0.84 L/s to 0.25 L/s, 30 % of what it was, because a d28 bore was always what limited a
  3.6 m3/h blower - but the skin never noticed, and that is the whole reason the trade was open
  to make.  12.2 Pa is high up a small blower's pressure curve, which is what a fan facing a
  narrow gap does; it costs a little noise, not cooling.

The trade is therefore real but small, and two things about it are worth knowing before the print is
sanded off the bed:

* the fan is now part of the enclosure, not an accessory.  The d28 bore is the biggest hole on the
  box; a 30 x 30 frame spans it with 1 mm of plastic all round, so with the fan screwed in there is
  no opening a finger can follow, but a shell used *without* the fan has a 28 mm hole in its side.
* what the fan still does inside a sealed box is stir: it breaks the boundary layer off the LCD and
  the R307 prism and holds the enclosure slightly above room pressure, which is what keeps dust from
  being pulled in around the scanner.  It is a demister that also cools, and it should keep running
  from the ESP32's own supply.

Nothing else moved.  Filling twelve slots in added 3.2 cc of plastic to the shell (112.0 cc -> **115.2 cm3**),
11 108 triangles where v3.3 had 14 426 (3 318 fewer, because the slot outlines and their corner arcs
are gone), and it *reduced* the fragile geometry: overhang area 296 mm2 -> **244 mm2** (0.30 % of the
shell), still no supports, first layer 11 469 mm2.  The four box parts are now **172.2 cm3 CAD ->
159 g of PLA**, 396 g with the modules on two wall hooks, 53.0 m of filament, 6.3 sets on a 1 kg
spool.  `02_REAR_PLATE_v3.stl`, `03_R307_BRACKET_v3.stl` and `04_RC522_RING_v3.stl` are byte-identical
to v3.3 - only the shell was rebuilt - and so is `05_FIT_GAUGE_v3.stl`, which the user still prints
first because none of this changes a pilot diameter.

Reversible in one line, like every other aesthetic decision on this model: `P["grilles"] = True` in
`tools/build_v3.py` brings all twelve slots back, and the builder's self-checks, section 6b of the
verifier and the opening map all switch their expectations with the flag rather than being edited to
match.


---

## 10. v3.4 → v3.5: the pack is four files, and the open sizes were closed from vendor data

Asked for the exact sizes and a final screw list — and not willing to print a gauge or measure
anything — the only honest way to answer was to go and look.  Every module in this box was checked
against published outlines on 2026-10-08.  **Nothing in the geometry moved**, and that is the result
rather than a shrug: the model was built from the same numbers the vendors publish, so the audit, the
verifier and the four STLs you already have still refer to these exact bytes.

| part | what the vendor data says | what the box has | verdict |
|---|---|---|---|
| R307 | 44.1 × 20 × 23.5 body, 19 × 21 window — makerselectronics, robokits and the Grow/NEWTECH manual all publish the same numbers | `r307_body=(20.0, 44.1, 23.5)`, window 19.3 × 21.2, relief 21.0 × 25.0 in a 25.3 × 27.2 rebate | **exact**, 0.3–0.6 mm clear around the glass, 0.35 seat fit |
| R307 mounting | the module has no mounting holes at all: the four Phillips screws on its back close the housing, and the stock kits (ArduGeek, sensorembedded, Grow) clamp it with a bracket plus two long M3 | a printed dog-bone bracket over the housing, 2 × M3 × 10 into ⌀2.5 × 8.0 posts | **the same method as the kit**, so the 28.0 mm pitch is our bracket's and not a tolerance to match |
| 1602 + I2C | 80 × 36 outline; depth 13.2 (displaymodule.com, slim), 18.24 (addicore), 20.0 (einstronic); 72 × 25 of bezel, 64.5 × 16.2 of visible text | window 66.0 × 17.5, rebate 72.0 × 23.5 × 0.45, cavity reserved to `zi+24.0` | **every depth sold fits with ≥4 mm to spare**, and the audit's envelope check proved the pocket collides with nothing |
| RC522 | 60 × 40, 1.6 PCB, header ≤ 6 mm | 62.7 × 44.7 × 2.9 recess, 1.0 shelf, 4 ribs, the ring clamps the edges | **fits any brand of that size**; the board's own hole pitch is deliberately unused |
| 3010 fan | 30 × 30 × 10, "mounting dimensions 24 ± 0.3 mm", "4 holes 3 mm"; 5 V parts flow 1.9–2.5 CFM | `fan=(30,30,10)`, `fan_pitch=24.0`, ⌀3.2 lugs, ⌀28 bore, flow modelled 3.6 m³/h | **exact**; the modelled flow is inside the published 3.2–4.2 m³/h band and the audit runs the low end |
| ESP32 DevKit V1 | 51.45 × 28.33 (espboards.dev draws it to that outline), 52 × 28 × **14** with headers (einstronic); pad holes ⌀2.5 reported by owners, ⌀3.0 on the wESP32 drawing with 3.5 inset | `esp32_board=(28.33, 51.45, 1.6)`, `esp32_comp_h=16.0`, inset 3.5, M2.2 into ⌀1.8 | outline **exact**, height **2 mm over the real stack**, pad-hole diameter still unpublished — it decides M2.2 vs M2 and nothing else |

Two near-misses that turned out to be fine.  The ESP32's real 14 mm stack looked like it needed
`esp32_comp_h` raised from 12: it was already 16.0, and the audit proves the plate still closes over it.
And the fan's ±0.3 mm pattern tolerance is absorbed by the M3 shank having 0.1 mm per side inside the
lug hole — which is precisely why the wall holes are ⌀2.5 pilots rather than threads cut to 24.0.

**Screws, final.**  Same table as the print order's SCREWS section, which the audit measured hole by
hole (22 of them):

| where | screw | into | evidence |
|---|---|---|---|
| rear plate | 4 × M3 × 10 | ⌀2.48 × 9.0 blind pilots; plate holes ⌀3.4 clearance; 90° countersink ⌀6.40 | pull-out 291 N each vs 0.59 N of load |
| LCD1602 | 4 × M2.5 × 12 | ⌀2.05 × 8.5 | the pilot is the thread's minor ⌀2.06, so it bites |
| RC522 ring | 4 × M2.5 × 8 | ⌀2.05 (2.5 through the ring + 3.8 blind in the pad) | × 6 works too; heads sink in the ring's ⌀5.6 × 1.5 recesses |
| R307 bracket | 2 × M3 × 10 | ⌀2.50 × 8.0 | and the stock R307 kit ships the same length |
| fan | 4 × M3 × 12 (12–14) | ⌀2.50 × 12.0 | a 3010 usually ships **two** screws — you need four, pan head, not countersunk |
| ESP32 | 4 × M2.2 × 8 | ⌀1.80 × 5.7 | **M2.2 only** at the antenna end; M2 × 8 self-tapping is the fallback (it clears a 2.5 mm board hole and bites the same pilot); **not M2.5**, which may not pass that hole; never M3 |

M2.2 × 8 is the only line a Mirzapur hardware shop might not stock — it is a precision size, sold
online in packs.  M2 × 8 from any M2 kit is the substitute.  Everything else here is loose-change
stock.

And the fifth file is gone from the pack: `tools/build_gauge_v3.py`, `tools/check_gauge_v3.py`,
`tools/make_gauge_figure_v3.py`, `cad/v3/05_FIT_GAUGE_v3.stl`, `docs/v3_gauge_build.txt`,
`docs/v3_gauge_check.txt` and `renders/v3_fit_gauge.png` all stay in the repo and still run, and none
of them ships any more — `tools/make_pack_v3.py` lists four STLs.  If a vendor number ever turns out to
be a lie about *your* module, `python3 tools/build_gauge_v3.py` prints the card again in 20 seconds of
slicing time and the pack takes the line back.
