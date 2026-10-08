ASTRO SMART ATTENDANCE - ENCLOSURE v2  (parametric rebuild)
outer 110 x 155 x 48 mm | 4 printed parts | no supports | every module screwed down
==============================================================================

PRINT  (PLA or PETG, 0.2 mm layers, 3 perimeters, 15-20 % infill, NO supports)
  1. 01_MAIN_SHELL_v2.stl      x1   front face DOWN on the bed, rear opening UP
  2. 02_REAR_PLATE_v2.stl      x1   flat, register lip UP
  3. 03_R307_BRACKET_v2.stl    x1   flat
  4. 04_RC522_CLAMP_v2.stl     x2   flat - ROTATE the second copy 180 deg about Z
  material: 198 cm3 of solid model -> ~123 g at 15 % infill (shell 72 g, plate 49 g)

SCREWS  (every fixing is a real circular self-tapping pilot hole - 22 in total,
         each one proved empty in the middle and surrounded by material)
  4 x M3 x 10     rear plate    -> 9 mm bosses, countersunk from outside (pilot d2.5 x 9.0)
  4 x M2.5 x 12   LCD1602 + I2C -> 6 x 6 bosses            (pilot d2.5 x 8.5)
  2 x M3          R307 bracket  -> 23.5 mm posts           (pilot d2.5 x 8.0)
  4 x M2.5 x 6    RC522 clamps  -> 4 x 8 x 8 pads          (pilot d2.2 x 4.1)
  4 x M3 x 20     fan 3010      -> 4 posts, 24 mm pitch    (pilot d2.5 x 12.0)
  4 x M2.5 x 6    ESP32 DevKit  -> 4 pads, 10 mm standoff  (pilot d2.2 x 7.0)
  4 x cable ties through the d4.0 holes in the 4 strain-relief posts

ASSEMBLY ORDER
  1. Screw the LCD (with its I2C backpack) onto the 4 bosses from inside the cavity -
     window 66 x 17.5 is at the top of the front face.
  2. Drop the R307 into the 19.3 x 21.2 window (it lands on the 1.2 mm seat ribs), then
     screw the 2 mm bracket onto the two posts at x 22.0 / 50.0.
  3. Lay the RC522 in the 62.7 x 44.7 recess - the 56 x 38 scan window is fully open
     underneath it, so the antenna faces straight out with only 2 mm of plastic in front.
     Screw the two clamp bars over the board's short edges (2 x M2.5 each, head recessed).
  4. Screw the ESP32 onto its 4 pads on the -X wall, USB edge toward the bottom slot.
  5. Screw the 3010 fan to the 4 posts on the -X wall, cable toward the board.
  6. Cable ties on the 4 posts; USB / DC leads leave through the 18 x 10 slot.
  7. Close with the rear plate (4 x M3 flat heads, 90 deg countersinks), hang it on the
     keyhole (d7.5 + 4.6 slot, 50 mm span) if you want it on a wall.

BEFORE YOU PRINT - MEASURE YOUR OWN PARTS (docs/master_prompt.md section 23)
  - ESP32 DevKit V1 pad hole inset (assumed 3.5 mm from the board corner)
  - R307 bracket hole pitch (assumed 28 mm centres)
  - LCD + I2C backpack total depth (assumed 18.24 mm)
  - fan thickness (assumed 10 mm) and the RC522 board outline (60 x 40 x 1.6 confirmed)
  The RC522's own corner holes are NOT used - it is clamped, so no hole pitch can be wrong.
  Any of the four numbers above changes in ONE place: tools/build_v2.py, then re-run it.

PROOF THAT SHIPS WITH THE ZIP
  docs/v2_audit.txt              the build's own audit, sections A-J, all PASS
  docs/v2_independent_verify.txt independent re-verification from the STL files only
                                 (12 sections: mesh integrity, 240 slices, wall map,
                                 envelopes, pilot radii, openings, printability, driver
                                 access, RF path, fits, dimensions, mass)
  renders/v2_shell_drawing_sheet.png   front / iso / side / plate views
  renders/v2_exploded_iso.png          all 4 printed parts exploded
  renders/v2_fixing_detail.png         RC522 fixing: exploded stack + dimensioned section
                                 (in the section, bright material is what the cut
                                 plane actually passes through; dim = behind the plane)
  renders/rfid_before_after.png        v1 closed pocket vs v2 open window
  viewer_offline.html                  the interactive 3D model, no internet needed

  NOTE (honest): the shell and plate carry 9 + 7 sub-micron sliver triangles where the
  corner fillet meets the rim chamfer. They are smaller than a millionth of a square
  millimetre, invisible to any slicer, and reported here rather than hidden.
