ASTRO SMART ATTENDANCE - ENCLOSURE v2  (110 x 155 x 48 mm, 4 printed parts)
==========================================================================
PRINT (PLA, 0.2 mm layers, 3 walls, 15-20 % infill, NO supports)
  1. 01_MAIN_SHELL_v2.stl      x1   front face DOWN on the bed, rear opening UP
  2. 02_REAR_PLATE_v2.stl      x1   flat, lip UP
  3. 03_R307_BRACKET_v2.stl    x1   flat
  4. 04_RC522_CLAMP_v2.stl     x2   flat - ROTATE the second copy 180 deg about Z

SCREWS (every fixing is a circular self-tapping pilot hole, all verified)
  4 x M3 x 10       rear plate  -> 9 mm bosses            (pilot d2.5 x 9.0)
  4 x M2.5 x 12     LCD1602     -> 6 x 6 bosses           (pilot d2.5 x 8.5)
  2 x M3            R307 bracket-> 23.5 mm posts          (pilot d2.5 x 8.0)
  4 x M2.5 x 6      RC522 clamps-> 4 pads 2.5 mm          (pilot d2.2 x 4.1)
  4 x M3 x 20       fan 3010    -> 4 posts 12 mm          (pilot d2.5 x 12.0)
  4 x M2.2 x 6      ESP32 pads  -> 4 pads 10 mm           (pilot d2.2 x 7.0)
  3 x cable ties through d4.0 holes (3 posts)

ASSEMBLY ORDER
  1. Screw the LCD onto its 4 bosses from inside (window at the top of the front face).
  2. Drop the R307 into its 19.3 x 21.2 window, screw the 2 mm bracket on the posts.
  3. Put the RC522 in its 62.7 x 44.7 recess (antenna toward the 54 x 36 open window),
     then screw the two clamp bars across the top and bottom edges (2 x M2.5 each).
  4. Screw the ESP32 on its 4 pads (USB edge toward the bottom-wall slot).
  5. Screw the fan on the 4 posts on the -X wall, cable toward the board.
  6. Cable ties on the 3 posts, USB/DC out through the 18 x 10 slot.
  7. Close with the rear plate (4 x M3); keyhole hanger d7.5 + 4.6 slot fits a screw head.

VERIFY ON YOUR HARDWARE BEFORE PRINTING (docs/master_prompt.md section 23)
  - ESP32 pad hole inset (assumed 3.5 mm)
  - RC522 corner hole pitch (not used - boards are clamped, not screwed)
  - R307 bracket hole pitch (assumed 28 mm centres)
  - LCD + I2C backpack total depth (assumed 18.24 mm)
