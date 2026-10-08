ASTRO SMART ATTENDANCE - ENCLOSURE v3  (complete re-design, parametric rebuild)
outer 110 x 155 x 46 mm | 4 printed parts | no supports | 22 screw holes, every module screwed down
==============================================================================

WHAT THIS IS
  v3 is not a re-tuned v2. The depth came out of the RFID stack instead of being picked, the
  front face was re-drawn around the three modules with a sunk rebate ring, the RFID hold-down
  was replaced by one flat ring, the rear closure was replaced by a register frame, the fan
  grille and its 1.4 mm seat lip were deleted, and a fresh intake wall was cut. See
  docs/v3_design_notes.md for the measured before/after (19 table rows, all measured off the
  shipped STLs). Both checkers have to say PASS before this file is regenerated:
    python3 tools/build_v3.py     ->  RESULT: ALL CHECKS PASS        (docs/v3_audit.txt)
    python3 tools/verify_v3.py    ->  INDEPENDENT RESULT: ALL CHECKS PASS
                                      (docs/v3_independent_verify.txt - STL-only, re-typed dims)
    python3 tools/audit_physics_v3.py -> PHYSICS RESULT: no failures
    python3 tools/check_grooves_v3.py  ->  EVERY GROOVE AND FIT MEASURES AS DESIGNED
                                      (docs/v3_groove_check.txt - 34 numbers, each walked at
                                       0.02 mm through the print files: every rebate, recess,
                                       register lip, keyhole and ring opening, as printed)
                                      (docs/v3_physics_audit.txt - fasteners, airflow, RF, optics,
                                       PLA limits, insertion kinematics, slicer reality, and a
                                       re-measurement of every number written in this file)

PRINT  (PLA or PETG, 0.2 mm layers, 3 perimeters, 15-20 % infill, NO supports)
  1. 01_MAIN_SHELL_v3.stl      x1   front face DOWN on the bed, rear opening UP
  2. 02_REAR_PLATE_v3.stl      x1   flat, register frame UP (the frame is 2 mm proud)
  3. 04_RC522_RING_v3.stl      x1   flat  (this replaces v2's two clamp bars: one part now)
  4. 03_R307_BRACKET_v3.stl    x1   flat
  material: 167.9 cm3 of solid model -> **154 g printed PLA** at 15 % infill, 0.45 nozzle, 3
  walls (shell 110.9 cm3 / 108 g, plate 53.8 / 42 g, ring 2.2 / 2.7 g, bracket 1.0 / 1.2 g).
  That is a layer-by-layer slicer model, not a flat "15 %" factor: a 2.6 mm wall needs 3 lines of
  0.45 = 2.7 mm, so the walls print SOLID and only the plate's faces and the big bosses carry
  infill. 1 kg spool = 6.5 sets. With the modules in it the box weighs 391 g on two wall hooks.
  (v3.0 quoted ~102 g from a blanket 50 % factor - too low, corrected here and in the notes.)
  Thinnest sheet anywhere: 2.2 mm (the bearing band the RC522 lies on). Faces steeper than 60 deg:
  0.40 % of the shell (325 mm2), every one bridging under 3 mm -> supports off. First layer
  11 469 mm2, one closed contour on all four parts, no island to lift.

SCREWS  (every fixing is a real circular self-tapping pilot; each one was found in the mesh,
         its diameter measured with 8 rays, and the wall around it checked - 22 holes)
  4 x M3 x 10     rear plate     -> 9 mm bosses, 6.6 mm 90-deg countersunk from outside
                                    (pilot d2.5 x 9.0)
  4 x M2.5 x 12   LCD1602+I2C    -> 6 x 6 bosses, glass sits on the wall's 1.6 mm shelf
                                    (pilot d2.05 x 8.5 - the thread's minor, so it bites)
  2 x M3 x 10     R307 bracket   -> the dog-bone bracket onto 2 posts   (pilot d2.5 x 8.0)
  4 x M2.5 x 8    RC522 ring     -> 4 x 8 x 8 pads at (+/-17, +/-34) from the reader centre,
                                    heads sunk in the ring's own d5.6 x 1.5 recesses. Use x 6 if
                                    you like, x 8 reaches the blind pilot comfortably: pilot
                                    d2.05 x 2.5 through the ring + blind d2.05 x 3.8 in the shell
                                    pad, 1.4 mm of wall left under it - no through-hole.
  4 x M3 x 12     fan 3010       -> 4 standoffs, 24 mm pitch            (pilot d2.5 x 12.0)
                                    (v2's list said M3 x 20; that bottoms out - the pilot is
                                    12 deep and the fan's lug 2.5 mm, so use M3 x 12-14)
  4 x M2.2 x 8    ESP32 DevKit   -> 4 round d8 bosses with d3.2 x 0.7 exit reliefs so the plate
                                    still closes over the heads (pilot d1.8 x 5.7). M2.2 x 8 ONLY
                                    at the antenna end: the heads are 10.7 mm from the trace and a
                                    long shank beside it pulls the 2.4 GHz match. No steel or brass
                                    washers under those two heads.
  4 x cable ties  through the d4.0 holes in the 4 strain-relief posts

ASSEMBLY ORDER
  1. LCD1602 with its I2C backpack: drop it into the 66 x 17.5 window from INSIDE so the glass
     stands proud in the 0.45 deep rebate, then 4 x M2.5 into the corner bosses. The backpack
     has 24 mm of room and the rebate hides the bezel step.
  2. R307: slide the module into the 21 x 25 opening from inside - its own bezel shoulder
     registers on the floor of the 0.45 rebate, and the two 1.2 x 1.5 seat ribs stop it
     rotating. Then the dog-bone bracket over the sensor's two flanges, 2 x M3. The narrow
     middle of the bracket spans the glass so you can undo it without prying on the window.
  3. RC522: the board goes in PORTRAIT (its 40 mm dimension across the box, 60 mm up the box).
     Lay it on the 2.2 mm bearing band inside the 44.7 x 62.7 x 0.8 recess; the four 1.2 x 1.0
     seat ribs locate it at 0.35 mm per side. The 38 x 56 aperture under it is completely open -
     nothing crosses it, which is the whole point of v3, and it drops straight down onto its seat
     with 6.4 mm to clear to the ESP32 stand-offs. Put the ring on the board's front face, its
     4 tabs onto the 4 pads, and 4 x M2.5 x 8 into the blind pilots. The ring's inner lip stands
     0.5 mm inside the aperture, so the board cannot creep; the heads sit 1.15 mm below the ring's
     outer face, so the rear plate clears it.
     One hardware rule: the 8-pin header must not stand more than ~6 mm proud of the PCB on the
     pad side, because the channel under the ESP32's posts is 9.8 mm and a 1.6 mm board plus a
     9 mm male header is 10.6 mm. Solder the leads, or use short / right-angle female headers, or
     fit the reader before the ESP32. (v3.0 laid this board landscape, and it could not be
     installed at all: the bay between the ESP32 post ends and the R307's post is 58.35 mm and the
     board needed 60. See docs/v3_design_notes.md section 6, defect F13.)
  4. ESP32 DevKit V1: 4 x M2.2 into the round bosses on the -X wall, USB edge toward the
     18 x 10 slot in the -Y wall. The board has 0.5 mm of clearance to the front wall and the
     antenna end keeps its full keep-out box (verified: 0 of 27 000 samples inside material).
  5. 3010 fan: 4 x M3 x 12 into the standoffs on the -X wall. The d28 bore (615 mm2) has no
     grille, so the fan moves the air straight out; 8 x 30 x 5 stadium slots in the opposite wall
     feed it (1157 mm2, 1.9x the bore). Measured against the fan's own curve that is 0.86 L/s at
     1.7 Pa - 86 % of its free air, the whole 784 cm3 box changed every 0.9 s, 1.6 K below the
     no-flow rise. It is a demister, not a cooler: run it continuously off the ESP32's supply.
  6. Loom: cable ties through the 4 x d4.0 holes, USB / DC leads out through the bottom-wall
     exhaust slot (4 x 20 x 4) - nothing hangs in front of the fan (checked: 0 blocked rays).
  7. Close with the rear plate: the 2 mm register frame goes INTO the opening (0.25 mm per
     side, printed fit), 4 x M3 flat heads flush in the countersinks. Hang it on the wall with
     the two keyhole hooks (d7.5 + 4.6 slot, 50 mm span) - the plate carries 4 screws, so the
     hooks are not structural.

BEFORE YOU PRINT - MEASURE YOUR OWN PARTS (docs/master_prompt.md section 23)
  - ESP32 DevKit V1 pad-hole inset from the board edge (assumed 3.5 mm)
  - R307 bracket hole pitch (assumed 28.0 mm) and the module's front-bezel size
  - LCD + I2C backpack total depth (assumed 18.24 mm)
  - fan thickness and its hole diameter (assumed 10 mm thick, d3.2 / M3)
  The RC522's own hole pitch is deliberately NOT used by this design - the ring holds the
  board by its edges, so a 60 x 40 board of any brand fits. The four ribs, the 0.5 mm ring
  overlap and the spotfaced bosses absorb +/- 0.5 mm of error in the other numbers.

  The pack is bed-aligned on purpose: a slicer translates a part onto the bed but never rotates
  it, so "print it flat" had to be baked into the triangles, not written as advice.

  If a measurement is off by more than that: edit the number in tools/build_v3.py and re-run
  it - it re-exports all four STLs and re-runs every one of the A-K checks (interference,
  component fit, openings, printability, the 22-hole pilot census, the v2/v3 deltas) and
  either prints RESULT: ALL CHECKS PASS or refuses. Then re-run tools/verify_v3.py, which
  repeats the important measurements from the STL files alone, and tools/audit_physics_v3.py,
  which asks the questions geometry alone cannot answer (can it be assembled, does it breathe,
  does the thread bite, does the plastic stay flat at 60 C) and then re-measures every number in
  this file so the pack cannot drift from the model.

FILES IN THIS PACK
  01..04 *.stl                     the four prints
  v3_audit.txt                     the generator's own A-K checks, with the numbers
  v3_independent_verify.txt        the STL-only check (12 sections, 4-12 mm probes)
  v3_physics_audit.txt             the third gate: fasteners, airflow, RF, optics, kinematics,
                                   PLA limits, slicer reality - and a re-measurement of this file
  v3_groove_check.txt              the fourth gate: measured size of every groove and the fit of
                                   every mating part, so the print order's tolerances are numbers
  v3_design_notes.md               why each change was made + measured before/after
  master_prompt.md                 the full spec (28 sections: 0-26 the rules, 27 the v3
                                   decisions, 28 what the physics round changed)
  6 x .png                         every figure drawn from these STLs: drawing sheet, exploded,
                                   fixing detail, fixing sections, all views, v2-vs-v3
  build_v3_PARAMETRIC_generator.py the whole model in one file (params at the top)
  verify_v3_INDEPENDENT.py         run it against any future export to catch a bad STL
  audit_v3_PHYSICS.py              the physics auditor (slow: it slices at 0.01 mm and models the
                                   slicer's density layer by layer - 14 min, worth it after edits)
  orient_v3.py                     the one table that puts every part in its printing attitude
  viewer_offline.html              open by double-click: v3, v2 and v1 side by side, no server
