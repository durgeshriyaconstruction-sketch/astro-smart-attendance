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

PRINT  (PLA or PETG, 0.2 mm layers, 3 perimeters, 15-20 % infill, NO supports)
  1. 01_MAIN_SHELL_v3.stl      x1   front face DOWN on the bed, rear opening UP
  2. 02_REAR_PLATE_v3.stl      x1   flat, register frame UP (the frame is 2 mm proud)
  3. 04_RC522_RING_v3.stl      x1   flat  (this replaces v2's two clamp bars: one part now)
  4. 03_R307_BRACKET_v3.stl    x1   flat
  material: 169.2 cm3 of solid model -> ~105 g PLA at 15 % infill (shell 112.4 / 70 g,
  plate 52.8 / 33 g, ring 3.0, bracket 1.0). Thinnest sheet anywhere: 2.2 mm (the bearing
  band the RC522 lies on). Faces steeper than 60 deg: 0.41 % of the shell, every one
  bridging under 3 mm -> supports off.

SCREWS  (every fixing is a real circular self-tapping pilot; each one was found in the mesh,
         its diameter measured with 8 rays, and the wall around it checked - 22 holes)
  4 x M3 x 10     rear plate     -> 9 mm bosses, 6.6 mm 90-deg countersunk from outside
                                    (pilot d2.5 x 9.0)
  4 x M2.5 x 12   LCD1602+I2C    -> 6 x 6 bosses, glass sits on the wall's 1.6 mm shelf
                                    (pilot d2.5 x 8.5)
  2 x M3 x 10     R307 bracket   -> the dog-bone bracket onto 2 posts   (pilot d2.5 x 8.0)
  4 x M2.5 x 6    RC522 ring     -> 4 x 8 x 8 pads, heads sunk in the ring's own recesses
                                    (pilot d2.2 x 3.8 in the ring + blind d2.2 x 3.8 in the
                                    shell, 1.4 mm of wall left under it - no through-hole)
  4 x M3 x 12     fan 3010       -> 4 standoffs, 24 mm pitch            (pilot d2.5 x 12.0)
                                    (v2's list said M3 x 20; that bottoms out - the pilot is
                                    12 deep and the fan's lug 2.5 mm, so use M3 x 12-14)
  4 x M2.2 x 8    ESP32 DevKit   -> 4 round d7 bosses with d3.6 x 0.7 spotfaces so the plate
                                    still closes over the heads
  4 x cable ties  through the d4.0 holes in the 4 strain-relief posts

ASSEMBLY ORDER
  1. LCD1602 with its I2C backpack: drop it into the 66 x 17.5 window from INSIDE so the glass
     stands proud in the 0.45 deep rebate, then 4 x M2.5 into the corner bosses. The backpack
     has 24 mm of room and the rebate hides the bezel step.
  2. R307: slide the module into the 21 x 25 opening from inside - its own bezel shoulder
     registers on the floor of the 0.45 rebate, and the two 1.2 x 1.5 seat ribs stop it
     rotating. Then the dog-bone bracket over the sensor's two flanges, 2 x M3. The narrow
     middle of the bracket spans the glass so you can undo it without prying on the window.
  3. RC522: lay the 60 x 40 board on the 2.2 mm bearing band inside the 62.7 x 44.7 x 0.8
     recess; the four 1.2 x 1.0 seat ribs locate it at 0.35 mm per side. The 56 x 38 aperture
     under it is completely open - nothing crosses it, which is the whole point of v3. Put the
     ring on the board's front face, its 4 corner tabs onto the 4 pads, and 4 x M2.5 into the
     blind pilots. The ring's inner lip stands 0.5 mm inside the aperture, so the board cannot
     creep; the heads sit 1.15 mm below the ring's outer face, so the rear plate clears it.
  4. ESP32 DevKit V1: 4 x M2.2 into the round bosses on the -X wall, USB edge toward the
     18 x 10 slot in the -Y wall. The board has 0.5 mm of clearance to the front wall and the
     antenna end keeps its full keep-out box (verified: 0 of 27 000 samples inside material).
  5. 3010 fan: 4 x M3 x 12 into the standoffs on the -X wall. The d28 bore has no grille, so
     the fan moves the air straight out; 6 x d5.0 intake holes in the opposite wall feed it.
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

  If a measurement is off by more than that: edit the number in tools/build_v3.py and re-run
  it - it re-exports all four STLs and re-runs every one of the A-K checks (interference,
  component fit, openings, printability, the 22-hole pilot census, the v2/v3 deltas) and
  either prints RESULT: ALL CHECKS PASS or refuses. Then re-run tools/verify_v3.py, which
  repeats the important measurements from the STL files alone.

FILES IN THIS PACK
  01..04 *.stl                     the four prints
  v3_audit.txt                     the generator's own A-K checks, with the numbers
  v3_independent_verify.txt        the STL-only check (12 sections, 4-12 mm probes)
  v3_design_notes.md               why each change was made + measured before/after
  master_prompt.md                 the full spec this model was built against (26 sections
                                   + the v3 appendix: what a future rebuild must not lose)
  6 x .png                         every figure drawn from these STLs: drawing sheet, exploded,
                                   fixing detail, fixing sections, all views, v2-vs-v3
  build_v3_PARAMETRIC_generator.py the whole model in one file (params at the top)
  verify_v3_INDEPENDENT.py         run it against any future export to catch a bad STL
  viewer_offline.html              open by double-click: v3, v2 and v1 side by side, no server
