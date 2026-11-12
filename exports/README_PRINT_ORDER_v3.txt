ASTRO SMART ATTENDANCE - ENCLOSURE v3  (complete re-design, parametric rebuild)
outer 110 x 155 x 46 mm | 4 printed parts | no supports | 22 screw holes
==============================================================================

WHAT THIS IS
  v3 is not a re-tuned v2. The depth came out of the RFID stack instead of being picked, the
  front face was re-drawn around the three modules with a sunk rebate ring, the RFID hold-down
  was replaced by one flat ring, the rear closure was replaced by a register frame, the fan
    grille and its 1.4 mm seat lip were deleted.  v3.3 then removed the eight slots that had been
  cut into the right-hand wall: the fan moves the air, so its own bore is the inlet (mounted
  blowing IN).  v3.4 finished the job - **the grilles are gone**, all twelve bottom and top slots
  filled in, and the d28 fan bore is the box's **only air opening**; only the USB opening is left
  in the bottom wall for the cable.  What cooling that costs is measured, not assumed: 2.7 K above
    ambient on the skin alone, 1.8 K with the fan's through-flow added, against a 12 K ceiling.
  See
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
WHAT IS SETTLED, SO THAT YOU DO NOT HAVE TO MEASURE ANYTHING
  Checked 2026-10-08 against published vendor outlines, module by module (design notes
  section 10 carries the sources).  Where the box and a vendor number disagreed, the box
  would move - today none of them did.
    R307         44.1 x 20 x 23.5 mm body, 19 x 21 mm glass - modelled exactly: a 21.0 x 25.0
                 relief in a 25.3 x 27.2 rebate with a 0.35 seat fit.  The module has NO
                 mounting holes of its own - stock R305/R307 kits clamp it with a bracket and two
                 long screws - which is exactly what 03_R307_BRACKET does, so there is no hole
                 pitch of yours to match and nothing on the sensor to measure.
    LCD1602+I2C  80 x 36 outline; stack depth 13.2 / 18.24 / 20.0 mm depending on the backpack -
                 the pocket reserves 24.0 behind the glass, so the deepest one sold still fits
                 with 4 mm spare, and the visible text area (64.5 x 16.2) clears the 66 x 17.5
                 window.
    RC522        60 x 40 with a 1.6 PCB and a header 6 mm or less - a 62.7 x 44.7 x 2.9 recess,
                 a 1.0 mm shelf and 4 ribs.  The board's own hole pitch is deliberately unused:
                 the ring clamps the edges, so any brand of that size fits.
    3010 fan     30 x 30 x 10, mounting pattern 24 +/- 0.3, four 3 mm holes - modelled exactly,
                 and its bore is the only air opening in the box.
    ESP32        51.45 x 28.33 outline, 52 x 28 x 14 mm with headers - 16.0 of height reserved
                 inside a 40.0 cavity, and the audit proves the plate still closes over the heads.
  The one number still open is the ESP32 pad-hole diameter (users report 2.5 mm, the closest
  published drawing says 3.0).  It moves no geometry: it decides only whether M2.2 or M2 is the
  easier screw to find, and both pass the d8 boss and bite the d1.8 pilot.

  1. 01_MAIN_SHELL_v3.stl      x1   front face DOWN on the bed, rear opening UP
  2. 02_REAR_PLATE_v3.stl      x1   flat, register frame UP (the frame is 2 mm proud)
  3. 04_RC522_RING_v3.stl      x1   flat  (this replaces v2's two clamp bars: one part now)
  4. 03_R307_BRACKET_v3.stl    x1   flat
    material, all four parts together: 172.2 cm3 of solid model
    -> **159 g printed PLA** at 15 % infill, 0.45 nozzle, 3
  walls (shell 115.2 cm3 / 114 g, plate 53.8 / 42 g, ring 2.2 / 3 g, bracket 1.0 / 1 g; the
  independent verifier's typed fractions land on 158 g - the same model, sampled differently).
  That is a layer-by-layer slicer model, not a flat "15 %" factor: a 2.6 mm wall needs 3 lines of
  0.45 = 2.7 mm, so the walls print SOLID and only the plate's faces and the big bosses carry
    infill. 1 kg spool = 6.3 sets (53.0 m of filament). With the modules in it the box weighs
    396 g on two wall hooks.
  (v3.0 quoted ~102 g from a blanket 50 % factor - too low, corrected here and in the notes.)
  Thinnest sheet anywhere: 2.2 mm (the bearing band the RC522 lies on). Faces steeper than 60 deg:
    0.30 % of the shell (244 mm2), every one bridging under 3 mm -> supports off. First layer
  11 469 mm2, one closed contour on all four parts, no island to lift.

SCREWS  (every fixing is a real circular self-tapping pilot; each one was found in the mesh,
         its diameter measured with 8 rays, and the wall around it checked - 22 holes.
         v3.6 added the third measurement, `tools/hole_probe_v3.py`: the DEPTH of every void, so
         the lengths below are what the printed holes can actually take, not what was intended.
         Three rows changed as a result: the LCD to x 8, the reader ring to x 4, the R307
         bracket to x 8.  Re-run `python3 tools/hole_probe_v3.py` after any geometry edit.)
  4 x M3 x 10     rear plate     -> 9 mm bosses, 6.6 mm 90-deg countersunk from outside
                                    (measured through the plate and the boss: 10.2 mm of void from
                                    the countersink floor at z 44.2 down to z 34.0, so x 10 seats and
                                    x 12 would be at the limit)
  4 x M2.5 x 8    LCD1602+I2C    -> 6 x 6 bosses, glass sits on the wall's 1.6 mm shelf
                                    (the pilot measures d2.05 x 7.0 deep off the shipped STL, at the
                                    thread's minor so it bites: 1.6 of PCB + 7.0 of pilot + 0.4 of tip
                                    chamfer = 9.0 of room, so x 8 seats and x 12 - the length this file
                                    used to carry - would float the display 3 mm off its bosses)
  2 x M3 x 8      R307 bracket   -> the dog-bone bracket onto 2 posts.  Measured off the mesh the
                                    whole void - the bracket's 3.2 mm through-hole and the pilot in
                                    the post below it - is 8.2 mm deep, so x 8 seats with 0.4 to
                                    spare and the x 10 this file used to carry would stand the
                                    bracket 1.8 mm off the posts, which is exactly the gap the
                                    0.35 mm seat fit is meant to close.  Pan or flat head, your
                                    choice: the audit measured 14.5 mm of headroom above both.
  4 x M2.5 x 4    RC522 ring     -> 4 x 8 x 8 pads at (+/-17, +/-34) from the reader centre, heads
                                    sunk in the ring's own d5.6 x 1.5 recesses.  MEASURED, off the
                                    mesh: the pocket floor is at z 5.7 and the blind pilot ends at
                                    z 1.4, so there are 4.3 mm of void (d2.05, and 1.4 mm of wall
                                    left under it - blind, not a through-hole).  x 4 seats flush;
                                    x 6 would float the ring 1.3 mm and x 8 - the length this file
                                    used to recommend, and what the audit's fastener table still
                                    models - would float it 3.3 mm, which is enough to lose the
                                    0.5 mm lip overlap that holds the board down.  If you own only
                                    x 6, use them and let the pocket be 1.5 mm deeper next print.
  4 x M3 x 12     fan 3010       -> 4 standoffs, 24 mm pitch, pilot d2.5 measured 11.0 mm deep
                                    with 1.6 mm of wall left behind it (blind, not a leak).
                                    THE LENGTH IS YOUR FAN'S, and it is one look, not a caliper job:
                                      holes through the whole 10 mm frame (the common 3010)  -> M3 x 20
                                      holes in a thin 2.5-3 mm tab at the back plane         -> M3 x 12
                                    Both stay inside the 11.0 pilot; longer would push the wall out.
                                    v2's list said x 20 unconditionally, which is right for the first
                                    case and 8 mm too long for the second.
  4 x M2.2 x 8    ESP32 DevKit   -> 4 round d8 bosses with d3.2 x 0.7 exit reliefs so the plate
                                    (no M2.2 in the drawer?  M2 x 8 self-tapping bites the same
                                    pilot and still clears a 2.5 mm board hole.  Do NOT substitute
                                    M2.5 - it may not pass that hole.  Never M3.)
                                    still closes over the heads (pilot d1.8 x 5.7). M2.2 x 8 ONLY
                                    at the antenna end: the heads are 10.7 mm from the trace and a
                                    long shank beside it pulls the 2.4 GHz match. No steel or brass
                                    washers under those two heads. The boss pilot measures d1.78 x
                                    7.0 deep, so 1.6 of board + 7.0 + 0.4 = 9.0 of room and x 8 seats
                                    with 1.0 to spare.
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
     20.4 x 12.4 slot in the -Y wall (that is the 18 x 10 USB plug plus 1.2 mm of room per side,
     measured through the whole 3 mm of wall - the connector shell never touches the plastic). The board has 0.5 mm of clearance to the front wall and the
     antenna end keeps its full keep-out box (verified: 0 of 27 000 samples inside material).
    5. 3010 fan: 4 x M3 x 12 into the standoffs on the -X wall, **mounted so it blows IN** - the
     arrows on the fan's frame have to point at the box, because the d28 bore (615 mm2, no grille)
     is the enclosure's **only air opening**: v3.3 deleted the eight side slots and v3.4 deleted the
     8 x 21 x 4.5 mm bottom grille and the 4 x 21 x 4 mm top grille, so those twelve hollows are
     solid wall now and the only hole left in a wall for a cable is the 20.4 x 12.4 mm USB opening.
     Two consequences, both measured:
       - the fan IS a closure. Its 30 x 30 frame spans the bore with 1 mm of plastic all round, so
         a built box has nothing a finger can follow; a shell used without the fan has a 28 mm hole
         in the side. Do not commission the box before the fan is fitted.
       - cooling is now carried by the skin, which is why it is not a problem: 1.6 W over 0.0585 m2
         of PLA at h = 10 W/m2.K is 2.7 K above ambient, and the through-flow the plate seam still
                  leaks (0.25 L/s at 12.2 Pa through A_eff 125 mm2, the 784 cm3 box changed every 3.2 s)
         puts the box at 1.8 K overall. v3.3 measured 1.6 K, so the twelve hollows were worth
         0.2 K - and the flow is now 30 % of what it was, which is what a d28 bore does to a
         3.6 m3/h blower whatever is on the other side of it. Physics audit section 4 has both derivations, and the seam
         row there is labelled ASSUMED because it depends on your print, not on the model.
     It is a demister as much as a cooler: run it continuously off the ESP32's supply.
  6. Loom: cable ties through the 4 x d4.0 holes, USB / DC leads out through the 20.4 x 12.4 mm
     USB opening in the bottom wall - the only wall opening that is not the fan bore. Nothing hangs
     in front of the fan (checked: 0 blocked rays across the whole bore).
  7. Close with the rear plate: the 2 mm register frame goes INTO the opening (0.25 mm per
     side, printed fit), 4 x M3 flat heads flush in the countersinks. Hang it on the wall with
     the two keyhole hooks (d7.5 + 4.6 slot, 50 mm span) - the plate carries 4 screws, so the
     hooks are not structural.

BEFORE YOU PRINT - NOTHING (design notes section 10 closed this list)
  - fan 10 mm thick, 24 mm pattern, d3.2 holes for M3        CONFIRMED against vendor listings
  - R307 44.1 x 20 x 23.5 with a 19 x 21 window              CONFIRMED three times over, and it
    is clamped rather than drilled, so the 28.0 bracket pitch is ours, not yours
  - LCD + backpack depth 13.2-20.0 in the wild               the pocket reserves 24.0
  - ESP32 51.45 x 28.33 x 14 with headers                    16.0 reserved
  - ESP32 pad-hole 2.5 or 3.0                                the only one DOIT never published:
    either way M2.2 or M2 x 8 fits and nothing about the box moves
  If you want a sanity check anyway, a steel rule across the LCD window (66 x 17.5) and the fan
  bore (d28) takes a minute and needs no print at all.
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

  Since v3.6 there is a fourth measurement, and it is the one that found mistakes here:
  tools/hole_probe_v3.py reads the depth of all 22 pilots out of the triangles - the face the head
  bears on, how deep the void really is, and how much plastic is left behind the bottom.  A diameter
  was always checkable, a length was only ever remembered, and three of the six lengths below were
  wrong.  It is a gate, not a report: if a documented screw does not fit its own hole the tool exits
  non-zero.  Run it after any change to a hole.

THE .BLEND MODEL (v3.6)
  exports/ASTRO_SMART_ATTENDANCE_v3.blend is the whole product as a native Blender scene, built by
  tools/make_blend_v3.py from these four STLs - the printed parts sit exactly where the print
  orientation table says they must (the tool asserts each part's lowest point equals its own lift),
  plus the five modules as reserved envelopes, a real 3010 with its d28 bore and its 4 x d3.2 on
  24 mm, and the 22 screws, each dropped into a hole the probe measured.  Nothing was typed.
  It carries:
    01 PRINTED      the 4 parts, assembled
    02 MODULES      LCD + backpack, R307, RC522, ESP32, fan, USB plug (reference, not printed)
    03 FASTENERS    22 screws with heads, the only things that may be hidden if you want the print
                    bag on its own
    04 BED ALIGNED  the 4 parts exactly as the STLs sit, switched off by default, so you can see
                    what the slicer sees without re-importing anything
    00 RIG          7 empties, one per group, keyframed: frames 1-24 apart, 24-48 back together,
                    3 cameras (ortho front, 55 mm iso, ortho fan wall) and a sun
  Units are millimetres at scene scale 0.001, so 1 unit = 1 mm and the numbers in the Outliner are
  the numbers on this sheet.  The .glb is the same geometry for anyone who has no Blender: it keeps
  1 unit = 1 mm too, so a viewer that assumes metres will show the case 1000x too big - set the
  import scale to 0.001 and it is exact.
  Check it yourself:  python3 tools/check_blend_v3.py   (needs `pip install bpy==4.5.14`, the official
  Blender module, plus the same trimesh that tools/requirements_v3.txt already asks for).  It opens the
  saved file, re-measures every solid from its own triangles, confirms each screw axis lands on a
  measured hole to 0.000 mm, moves the timeline to prove the explode, re-imports the .glb and proves
  the two copies agree to 0.05 mm, then reads the pixels of the three renders so a blank or black
  frame would fail.  docs/v3_blend_check.txt is what it printed here.
  Proof: docs/v3_hole_probe.txt (the holes), docs/v3_blend_build.txt (the build),
  docs/v3_blend_check.txt (the gate, from the saved file).

FILES IN THIS PACK
  01..04 *.stl                     the four prints
  v3_audit.txt                     the generator's own A-K checks, with the numbers
  v3_independent_verify.txt        the STL-only check (12 sections, 4-12 mm probes)
  v3_physics_audit.txt             the third gate: fasteners, airflow, RF, optics, kinematics,
                                   PLA limits, slicer reality - and a re-measurement of this file
  v3_groove_check.txt              the fourth gate: measured size of every groove and the fit of
                                   every mating part, so the print order's tolerances are numbers
    v3_design_notes.md               why each change was made + measured before/after - section 7 is
                                   the v3.3 air path, 8 the fit gauge (built, and now kept
                                   out of the pack), 9 the v3.4 decision to close every grille
                                   and what it cost in cooling, 10 the vendor data that closed
                                   the measuring list, 11 the .blend and what measuring the
                                   hole depths found
  ASTRO_SMART_ATTENDANCE_v3.blend  the native Blender assembly above (v3.6)
  ASTRO_SMART_ATTENDANCE_v3_assembly.glb   the same geometry for any other viewer
  v3_hole_probe.txt                the depth gate: 22 pilots measured, every documented screw
                                   checked against the plastic that has to take it
  v3_blend_build.txt               what the builder put into the .blend, with the volumes it
                                   re-measured on the way in
  v3_blend_check.txt               the independent gate, run against the saved .blend file
  master_prompt.md                 the full spec (33 sections: 0-26 the rules, 27 the v3
                                   decisions, 28 the physics round, 29 v3.3, 30 the gauge
                                   card, 31 v3.4 - one hole, not twelve, 32 v3.5 - four
                                   files and a checked size list, 33 v3.6 - the .blend and
                                   the day the screw lengths got measured)
  7 x .png                         every figure drawn from these STLs: drawing sheet, exploded,
                                   fixing detail, fixing sections, all views, v2-vs-v3, the fit
                                   v3.4 opening inventory (each side wall sliced at
                                   mid-thickness, every void labelled at the size it
                                   measured - it refuses to render 1 / 0 / 0 / 1 as
                                   anything else).  The fit-gauge figure is in the repo
                                   at renders/v3_fit_gauge.png, not in this pack.
  build_v3_PARAMETRIC_generator.py the whole model in one file (params at the top)
  verify_v3_INDEPENDENT.py         run it against any future export to catch a bad STL
  audit_v3_PHYSICS.py              the physics auditor (slow: it slices at 0.01 mm and models the
                                   slicer's density layer by layer - 14 min, worth it after edits)
  check_v3_GROOVES.py              the groove / printed-fit walker (47 s) - run it on any future
                                   export to see the rebate, recess, lip and hole sizes it really has
    make_grille_map_v3.py            redraws the opening inventory from any STL (3 s, and it fails
                                   if an opening count is not the 1 / 0 / 0 / 1 v3.4 has: the USB
                                   slot, nothing, nothing, the fan bore)
  orient_v3.py                     the one table that puts every part in its printing attitude
  viewer_offline.html              open by double-click: v3, v2 and v1 side by side, no server
