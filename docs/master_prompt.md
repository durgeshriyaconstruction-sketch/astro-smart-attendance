# ASTRO SMART ATTENDANCE — ENCLOSURE MASTER PROMPT (single consolidated prompt)

> **What this file is.** The two prompt blocks that were sent separately —
> *(A)* the base “model the enclosure in Blender” prompt and *(B)* “FINAL MISSING ENGINEERING
> REQUIREMENTS §1–26” — merged into **one** self-contained prompt, with every component dimension
> cross-checked against the real hardware, the corrected final layout, and the acceptance rules.
> Paste this whole file as the prompt. Nothing else is required.
>
> **Status of the model it describes:** implemented and audited. `tools/build_v2.py` regenerates
> `cad/v2/01_MAIN_SHELL_v2.stl` (single watertight body, 9892 tris, 115.1 cm³),
> `cad/v2/02_REAR_PLATE_v2.stl`, `cad/v2/03_R307_BRACKET_v2.stl` and `docs/v2_audit.txt`
> (**RESULT: ALL CHECKS PASS**). See §21 for the scorecard and §23 for the remaining
> `VERIFY_ACTUAL_HARDWARE` items.

---

## §1 Mission

Model a wall-mountable, 3D-printable enclosure for the **Astro Smart Attendance** ESP32 RFID
attendance terminal. It holds an ESP32 DevKit V1, an RC522 13.56 MHz RFID reader, an R307 optical
fingerprint sensor and a 1602 LCD with I²C backpack, plus a 3010 fan. The enclosure is a
**housing, not a gadget**: no electronics are invented, nothing is decorative, every feature exists
because a real part needs it.

Deliver millimetre-accurate geometry that can be sliced and printed **without support material**,
**without a single clearance failure**, and with every claim backed by a measurement.

## §2 Units, scale and axis frame

* Metric, **millimetres**, **1:1 scale** (Blender: `scene.unit_settings.system='METRIC'`,
  `scale_length=0.001`, `length_unit='MILLIMETERS'`).
* Axis frame used everywhere (STL frame too):
  * **X = width** (110 mm, device left/right)
  * **Y = height** (155 mm, top/bottom)
  * **Z = depth** (48 mm); **z = 0 is the FRONT face the user touches**, z = 45 is the shell’s rear
    edge, z = 45…48 is the rear service plate.
* Print orientation = this frame: **front face down on the bed, rear opening up** (`+Z` up).

## §3 Honesty rules (non-negotiable)

1. **Never model:** an RFID card, a card holder/cradle, any price (₹912 / ₹442 / ₹67 / ₹15 / ₹87 /
   ₹108 / ₹43), fictional components, decorative electronics, dummy LEDs, logos that are not the
   product name, or any geometry that is not needed to hold a real part.
2. **No placeholder geometry, ever.** Every boss, rib, pilot, slot and opening is dimensioned from a
   real part or from a stated engineering estimate.
3. **No fake openings** (an opening that does not open into the cavity) and **no fake mounting
   holes** (a hole with no matching hole in a real part).
4. **Never write PASS unless a check produced that PASS.** If a value is unknown, write
   `VERIFY_ACTUAL_HARDWARE` and say so in the report.
5. **Never merge components into one mesh.** Every real part is a separately named, separately
   editable object (§20).

## §4 Dimension priority

`actual measurement of the delivered hardware` **>** `dimension supplied by the team` **>**
`generic internet dimension`. Anything from the third tier or unverifiable is tagged
`VERIFY_ACTUAL_HARDWARE` in the audit and in the object name if it affects a fit.

## §5 Component register (the only parts that exist)

| Part | Model dims used (mm) | Source | Notes |
|---|---|---|---|
| ESP32 DevKit V1 (DOIT) | PCB **51.45 × 28.33 × 1.6**, components ≤ 12, +USB | [REF] team | 4 corner pads, hole inset 3.5 → `VERIFY_ACTUAL_HARDWARE` |
| RC522 reader | PCB **60 × 40 × 1.6**, components 6 (spec 3–8) | [REF] + web | 40 × 60 confirmed (espboards.dev, ifuturetech, sunrom, robotshop); corner holes ≈⌀3, pitch unverified → `VERIFY_ACTUAL_HARDWARE` |
| R307 fingerprint | body **44.1 × 20 × 23.5**, optical window 19 × 21 | [REF] manual | the single highest-risk part; mounts on a 2 mm steel bracket |
| LCD1602 + I²C backpack | PCB **80 × 36**, glass 71.2 × 24.2, **one combined assembly ≈ 18.24 deep** | [REF] | **do not** model the backpack as a separate 42 × 19 board |
| Fan | **30 × 30 × 10**, holes ⌀3.2/M3 on **24 mm** pitch | [REF] | grille ⌀26, 3 bars |
| Fasteners | 4 × M3 (plate), 4 × M2.5 (fan), 4 × M2.2 self-tap (ESP32 pads), 4 × M2.5 (LCD), 2 × M3 bracket | `FASTENER_SCHEDULE` | pilots: M3 → ⌀2.5, M2.5 → ⌀2.2, M2.2 → ⌀1.8 |

## §6 The enclosure is *derived from* the layout — never the other way round

The outer size is an **output**, not an input: place the parts first with their real clearances,
then wrap walls around them. The result here is **110 × 155 × 48 mm** (110 × 155 × 45 shell +
3 mm plate) with walls **front 3.0 / sides 2.4 / top & bottom 3.0 / plate 3.0 mm**.
Walls must stay inside 2.4–3.0 mm everywhere; the only permitted thin feature is the deliberate
1.45 mm web across the RFID recess (§8).

## §7 Tolerances

* Printed mating fit (lip, snap tabs, plate register): **0.35 mm** total clearance per side.
* Component clearance to enclosure walls: **1.0–2.0 mm**; pocket clearance 2.0 mm.
* Pilot holes = nominal ⌀ − 0.5 for self-tapping into PLA.
* Every mating pair is stated in the audit; nothing is allowed to interfere.

## §8 RFID reader — the reason this revision exists

The v1 shell had a **closed pocket floor at z ≈ 3 mm over the RC522 antenna**, which blocks
13.56 MHz scanning. That is fixed and must stay fixed:

1. **Open scan window `RC522_SCAN_ZONE` = 56 × 38 mm, completely open through the 3 mm front wall**
   (no floor, no membrane, no printed skin — an RFID field will not pass a printed wall reliably).
2. The window sits inside the existing **62.7 × 44.7 mm recess, 1.0 mm deep**, whose floor carries
   **1.0 mm locating ribs** (1.2 mm wide, 0.35 mm fit): the 60 × 40 board lies at **z = 3.0 … 4.6**,
   component side up into the cavity, so only **2.0 mm** of printed wall stands in front of the PCB —
   the thinnest the wall can be while still giving the board something to rest on.
3. **Stiffness:** the front wall is locally reduced to a **1.95 mm** web; **two** stiffener bars
   **2.5 mm wide × 1.95 mm thick**, spanning the 38 mm window, keep the front face rigid (measured in
   §21-E: bar 1.90 vs 1.95 design). They are the *only* material inside the window and they are
   **9 %** of its area — ray-proved in the audit, not assumed.
4. **`RC522_RF_KEEP_OUT`:** a 62.7 × 44.7 × 12 mm volume in front of the antenna is declared
   metal-free and plastic-free; the audit proves enclosure material volume inside it = **0.00 mm³**.
5. **`RC522_SCAN_ZONE`** additionally proves that the window is genuinely through-cut: a ray cast
   from outside the front face passes through the wall into the cavity.
6. The RC522 is **screwed down**, not clipped: **4 × 8 × 8 mm screw pads (2.5 mm tall, ⌀2.2 pilot,
   4.1 mm deep)** sit at ±22.0 / ±27.0 mm from the recess centre (outside the board edge and clear of
   the 56 × 38 window), and **two printed clamp bars** (part 04) hold the board's two short edges —
   a 62 × 15 mm platform with a **0.9 mm lip step** that presses the PCB onto the front wall, plus a
   **2 × ⌀3.0 through-hole + ⌀5.6 × 1.4 head recess** at each screw, 44 mm hole centres. The stack is
   closed by arithmetic: platform underside 5.50 = pad top 5.50 (0.00 interference), lip bottom
   4.60 = board top 4.60. The whole antenna face stays open and every screwdriver approach is
   straight down the Z axis from the rear opening (§21-I, §21-J).

## §9 Pin-out, header and connector space (the “leave room for the header” rule)

Nothing in this enclosure may be dimensioned as if the boards were bare PCBs. Real assemblies carry
**2.54 mm headers and Dupont housings**, so:

* **RC522:** its 8-pin header (plus the optional 2 extra I/O pins) is on the board’s long edge and
  adds **11.5 mm** normal to the PCB. The pocket rim is 2.4 mm tall and the tabs grip only the board
  edge, so the header side faces the cavity with **≥ 12 mm** of free space; the SPI jumper wires leave
  through the ≈ 9 mm gap between the R307 bezel relief (up to X 48.45) and the pocket rim (to X 14.35).
* **ESP32 DevKit V1:** two 19-pin headers at 2.54 mm pitch add **11 mm** to the 1.6 mm board. The bay
  holds the board on **10 mm standoff pads** and the board’s plane sits at X = −42.6, leaving
  **25 mm** of depth behind it in the cavity — header pins plus Dupont housings (≈ 15 mm) fit with
  room to spare, and the pins never touch the rear plate ribs at Z 41.
* **USB / power:** the micro-USB plug body is 15.6 × 8 mm and passes the 18 × 10 mm slot with 1.2 mm
  of clearance all round; the DC feed shares the same bottom-left corridor, which is why the rear
  boss in that corner starts at Z 33 instead of running to the wall.
* **Access for the pin headers:** the rear opening is 105.2 × 148.3 mm; the ESP32’s header rows and
  the RC522’s pins are both within 90 mm of it, so a Dupont housing can be plugged and unplugged
  without removing any printed part except the plate. The RC522 clamp bars sit only over the two
  short board edges (y = −51.1 and +2.9), i.e. 13 mm each, leaving the header edge free.
* **Every header clearance is measured** in the audit (envelope overlap = 0.00 mm³) — a header that
  touches a boss is a FAIL, not a note.

## §10 Final layout (the delivered model)

| Feature | Position / size (mm) | Provenance |
|---|---|---|
| LCD1602 window | 66 × 17.5 at (0, **+51.95**), wall cut | [V1] |
| LCD module | 80 × 36 glass 11.5 above the inner face, 4 × M2.5 bosses 6 × 6 at 75.1 × 31 pitch | [REF] |
| R307 window | **19.3 × 21.2** at (+35.95, −24.1) + **21 × 25 × 1.6** bezel relief (a 25 × 27 relief cut 1.55 mm into both M3 posts) + 1.2 mm seat ribs, 0.35 fit | [V1] |
| R307 module | sits on 2 posts 6 × 6 × **23.5** tall at x = 22.0 / 50.0, y = −24.1, ⌀2.5 pilots | [REF] |
| R307 bracket | 33.5 × 12 × 2 steel, ⌀3.0 + ⌀5.6 counterbores, 28 mm hole centres → `VERIFY_ACTUAL_HARDWARE` | [EST] |
| RC522 recess / window | 62.7 × 44.7 × **1.0** recess, **56 × 38 open window + 2 × 2.5 bars** at (−20.05, −24.05); board on 1.0 mm locating ribs, plane z 3.0 … 4.6 | [V1] + fix |
| RC522 fixings | 4 × 8 × 8 pads, 2.5 mm tall (⌀2.2 × 4.1 pilot) at (−20.05 ± 22, −24.05 ± 27) + 2 printed clamp bars (62 × 15 platform + 0.9 lip, ⌀3.0 hole / ⌀5.6 × 1.4 head recess, 44 mm centres) | new |
| ESP32 bay | on the **−X wall**, board plane X = −42.6 (10 mm standoff), Y −70 … −18.55, **Z centre 27.5** | [REF] |
| ESP32 pads | 4 × 8 × 8 pads, ⌀2.2 pilots 7 mm deep | [REF] |
| USB slot | **18 × 10** at Z 27.5 on the bottom edge (+2.4 chamfer), plug body 15.6 × 8 fits | [REF] |
| Fan | 3010 at (Y **17**, Z **24**) on the −X wall, ⌀26 grille + 3 bars, 4 × M3 posts (24 mm) | [REF] |
| Exhaust | **4** slots 20 × 4 in the bottom wall | — |
| Top vent | 3 slots 16 × 3 at X −18 / 0 / 18, Z 26 (−X wall, above the fan) | — |
| Rear plate | 110 × 155 × 3 flush + 2 mm register lip + 2 mm spine ribs, 4 × M3 into 9 mm bosses at (±46.5, ±71) | — |
| Keyhole hang | ⌀7.5 + 4.6 mm slot, 50 mm span, on the plate centre line | — |
| Cable ties | **4** posts ⌀8 with ⌀4 through-holes at (−10, −66), (16, −66), (44, 12), (−48, −66) | — |
| Corners / rims | front-face corners r3.0 (0.12 mm overshoot so the fillet never ends tangent → no sliver faces); 1.0 mm chamfer on the shell rim and the plate rim | new |
| Plate fixings | 4 × M3 into 9 mm bosses at (±46.5, ±71) with **⌀6.6 × 90° countersinks** (flat heads sit flush) + ⌀7.5 / 4.6 mm keyhole hang, 50 mm span | — |

## §11 Named keep-out & check objects (exact names required in the file)

`ESP32_RF_ANTENNA_KEEP_OUT` · `RC522_RF_KEEP_OUT` · `RC522_SCAN_ZONE` · `R307_OPTICAL_WINDOW` ·
`PRINT_BED_ENVELOPE` · `FASTENER_SCHEDULE` · `CABLE_PINCH_CHECK` · `SCREWDRIVER_ACCESS_CHECK`

Each is a real object/record in the model or audit file — not a comment. Keep-outs are rendered in
the wireframe review and are proven empty by boolean volume in §21.

## §12 `ESP32_RF_ANTENNA_KEEP_OUT`

The DevKit’s PCB antenna is at the top edge of the board (the end away from the USB socket).
No metal, no screw, no boss and no printed wall may enter **the 25 × 15 × 8 mm volume at that end +
2 mm of air in front of it**; the bay is oriented so the antenna points **away** from the fan, the
RC522 antenna and the rear plate fasteners. Verified empty (§21, section B).

## §13 `R307_OPTICAL_WINDOW`

The R307’s 19 × 21 mm optical window must be a genuine through-window in the 3 mm front wall — no
printed material, no glue ridge, no flash-over across the optical area; proven by a through-ray
(section C). Around the window a **25 × 27 mm relief thins the bezel to 1.6 mm**, so the module’s
20 mm shoulder sits against a flat 1.6 mm shelf instead of a 3 mm step, while the module itself is
carried by the two 6 × 6 × 23.5 mm posts and the bracket — its sensor face lands flush with the
cavity-side face of the front wall (z = 3.0), so the fingerprint is taken straight through the
window.

## §14 Airflow / thermal path

Fresh air enters the **4 bottom slots (2 rows × 2) in the bottom wall**, crosses the ESP32 bay and the RC522 pocket, is pushed
by the **3010 fan** (Y 17, Z 24) through the ⌀26 grille, and leaves through the **3 top vents**.
Measured areas: low intakes 4 × (20 × 4) = **320 mm²**, outlet 3 slots × (16 × 3) = **144 mm²**,
grille free area = 531 mm² aperture − 231 mm² of bars = **300 mm²** (56 % of the aperture, 33 % of
the fan’s 30 × 30 face). Inlet 1.07 : 1 and outlet 0.48 : 1 against the grille free area — more than
enough for a build dissipating well under 1 W; the fan is a circulation aid, not a cooling
requirement, and the grille is kept open so it can never stall against back pressure.
No vent is placed above the LCD electronics. Fan screws are reachable from the rear opening with a
100 mm driver (verified, §16).

## §15 `CABLE_PINCH_CHECK`

Every internal cable route must have **≥ 2 mm** clearance from any moving/closing surface and must
not be trapped by the plate lip or a rib. Routes: LCD ribbon and I²C (LCD → board), R307 5-pin
(through the 25 × 27 relief), RC522 SPI (right of the pocket), fan 2-pin (fan → board), 5 V feed
(bottom edge). The **truncated bottom-left rear boss** exists only to keep the DC/USB corridor clear;
it starts at Z 33 instead of the wall and never crosses the cable path.

## §16 `SCREWDRIVER_ACCESS_CHECK`

Every screw must be reachable by a straight driver from an opening, with the tool axis clear:

| Screw set | Driver axis | Verified clearance |
|---|---|---|
| 4 × M3 plate → bosses at (±46.5, ±71) | along −Z through the plate | clear, boss counterbore ⌀2.5 |
| 4 × M3 fan posts | from the rear opening, along −X | clear (cable ties moved to (−10, −66)/(16, −66), RC522 rim below Z 5.5, fan screws Z 12–36) |
| 4 × M2.2 ESP32 pads | from the rear opening, ±20° of the wall normal | clear, 10 mm standoff |
| 2 × M3 R307 bracket | from the rear of the LCD pocket, along −Z | clear, bracket sits on the 23.5 mm posts |
| 4 × M2.5 RC522 clamps | from the rear opening, along −Z | clear, pads sit in the 44 mm band between the clamp bars’ lips |

## §17 Printability & `PRINT_BED_ENVELOPE`

* `PRINT_BED_ENVELOPE` ≥ **120 × 165 × 50 mm** (the 110 × 155 × 48 part + brim).
* **Supports: none.** Designed orientation: front face down, rear opening up. Measured unsupported
  overhang > 60°: **155 mm² = 0.18 % of the surface** — all of it is the 3 mm rear register lip
  edge, which bridges/curls harmlessly.
* Minimum wall 1.45 mm (RFID web) / 2.4 mm everywhere else; minimum feature 2 mm (stiffener bars),
  minimum hole ⌀1.8 (pad pilots).
* With the front face on the bed the RFID window and its two stiffener bars are printed in the
  first layers directly over the bed, so they have no unsupported span at all — the long span that
  survives in the slicer is closed. The only bridge-like features are the top vents (16 mm) and the
  USB slot roof (18 mm), both short and both bridged across solid material.
* Print mass is reported, not guessed: ≈ 71 g PLA at 15 % infill for the shell.

## §18 `FASTENER_SCHEDULE`

| Qty | Screw | Into | Pilot | Function |
|---|---|---|---|---|
| 4 | M3 × 10 | rear plate → 9 mm bosses | ⌀2.5, 9 mm deep | close the enclosure |
| 4 | M2.5 × 12 | LCD ↔ 6 × 6 bosses | ⌀2.5, **8.5 mm deep** | hold LCD at 11.5 mm |
| 2 | M3 | R307 bracket → 6 × 6 posts | ⌀2.5, **8.0 mm deep** | hold the fingerprint module |
| 4 | M3 × 20 | fan → posts | ⌀2.5, 12 mm deep | fan retention |
| 4 | M2.5 × 6 | ESP32 corner pads | ⌀2.2, 7 mm deep | board standoff |
| 4 | M2.5 × 6 | 2 clamp bars → RC522 pads | ⌀2.2, 4.1 mm deep | hold the RC522 down |
| 4 | cable ties | ⌀8 posts, ⌀4 through-holes | — | strain relief |

Nothing is priced. No screw is invented. **22 circular pilot holes in total** (LCD 4, R307 2,
RC522 4, ESP32 4, fan 4, plate 4) — every one proved empty in the middle *and* surrounded by material
(§21-I), with a clear 6 mm screwdriver path over its whole length (§16 / §21-J).

## §19 Verification-first build order (the “no claim without a measurement” rule)

Build in this order and re-run the whole audit after every change:

1. Place the component envelopes from the real numbers in §5.
2. Derive the cavity, then the outer shell (walls §6).
3. Hollow the cavity **first**, then union bosses/pads/posts (otherwise the pocket cut deletes them).
4. Cut all openings/pilots, then **re-union** anything that must live inside a cut (grille bars,
   stiffener bars, plate ribs) with ≥ 0.5 mm overlap into its host — this is what keeps the STL a
   single watertight body.
5. Prefer an **open-ended** pilot: it must break through exactly one surface (the screw entry) and
   stop 0.9–1.5 mm short of the other. A pilot that touches no surface becomes an enclosed void and
   the STL splits into “extra bodies” (§25.4).
6. Re-audit: `python3 tools/build_v2.py` → `docs/v2_audit.txt`. The STL must report
   **`watertight=True`, `bodies=1`** before any other number is quoted.

## §20 Blender implementation requirements (if the model is authored in Blender)

* One object per real part, named exactly (`ESP32_DevKit_V1`, `RC522`, `R307`, `LCD1602_I2C`,
  `Fan_3010`, `Main_Shell`, `Rear_Plate`, `R307_Bracket`, plus the keep-out objects of §11).
* Never join/merge into a single mesh. Never apply a boolean that erases a named object; use them as
  boolean *tools* and keep the originals in a separate collection.
* Origin of every object at its own datum; the shell’s origin at the front-face centre.
* Solids only — no zero-thickness planes, no non-manifold edges, no inverted normals, no duplicate
  vertices; run *3D-Print Toolbox → Check All* and quote the result.
* Booleans: exact, self-intersection off after each cut; apply modifiers; no ngon > 12 verts.
* Text/annotations live on a separate `ANNOTATIONS` collection and are exported to the drawing
  sheet, never to the STL.

## §21 Audit / scorecard (must be delivered with every revision)

Report as a table with `measured`, `target`, `verdict ∈ {PASS, FAIL, VERIFY_ACTUAL_HARDWARE}`:

* **A printed-part interference** — shell ↔ plate, shell ↔ bracket: 0.00 mm³ required.
* **B component fit** — every envelope (§5) vs shell: 0.00 mm³ overlap required.
* **C openings** — for each opening: *through?* and *is there still wall beside it?* both must be yes.
* **D other printed parts** — plate and bracket: watertight, right bbox.
* **E thickness probes** — ray-measured wall/feature thickness vs design (±0.15 mm).
* **F dimensional audit** — model vs the §5 reference table, flagging `VERIFY_ACTUAL_HARDWARE`.
* **G printability** — overhang area %, support requirement, wall summary.
* **H STL file re-read** — reload every exported STL from disk and count open edges, non-manifold
  edges and bodies (0 / 0 / 1 required). In-memory watertightness is not enough: the *file* is what
  the slicer reads.
* **I screw fixing map** — every screw fixing must be a **circular pilot hole** with the hole empty
  (proved by a point inside it missing the mesh) *and* surrounded by material (proved by a point in
  the wall hitting the mesh). 22 holes are checked this way, group by group.
* **J polish / assembly features** — 12 probed features that only exist to make the part usable:
  rounded front corners (rounded *and* material kept), front-rim chamfer + material below it, plate
  rear chamfer, plate corner round, plate countersink open + wall kept behind it, the RC522 seat rib,
  the RC522 ledge ring, the R307 seat rib, the strain-relief post. Each is two probes: the feature is
  there, and the material that makes it useful is still there.
* **K independent re-verification** — `tools/verify_v2.py` re-opens *only* the exported STLs (it
  imports nothing from the generator) and re-measures 12 groups of facts: mesh integrity, 240 slice
  cross-sections, a 4 mm wall-thickness map, every component envelope re-typed from first principles,
  every pilot radius measured with 8-way rays, opening escape rays, 0.2 mm layer printability, driver
  access cylinders, the RF path, the printed-part fits, mesh dimensions and mass. Output:
  `docs/v2_independent_verify.txt`; it exits non-zero if anything fails.

**Delivered revision result (all lines measured, none assumed):**

```
shell     : watertight=True, bodies=1, volume 116.1 cc
shell size: [110.0, 155.0, 45.0] (depth 45 + 3 mm plate = 48)  plate 110 x 155 x 7
volume    : shell 116.1 / plate 79.6 / bracket 0.75 / clamp 1.58 x2 cm3  ~123 g PLA (15 % infill)
A  shell<->plate 0.00 PASS   shell<->bracket 0.00 PASS
B  LCD glass / PCB+backpack / bezel / R307 / RC522 board+components+scan zone /
   ESP32 board+components / ESP32 RF keep-out / USB plug / Fan 3010   ALL 0.00 PASS
C  LCD window, R307 window, RFID scan window, USB slot, fan grille,
   exhaust slot, top vent                               open=True wall_ok=True PASS
D  rear plate 110 x 155 x 7 watertight 79.6 cc ; R307 bracket 33.5 x 12 x 2 watertight ;
   RC522 clamp 62 x 15 x 2.5 watertight 1.58 cc (print 2, second rotated 180 deg)
E  front 2.90 / RFID ledge ring 1.95 / stiffener bar 1.90 / side 2.35 / top 2.90 /
   bottom 2.90 / LCD boss 11.50 / R307 post 23.50 / fan ring 1.35                 PASS
F  all model dims match the reference table (2 items VERIFY_ACTUAL_HARDWARE)
G  overhang 155 mm2 = 0.18 %  -> SUPPORT_REQUIRED = NO
H  re-read from disk: 4 parts = 0 open edges, 0 non-manifold edges, 1 body each;
   9 + 7 sub-micron sliver faces where the corner fillet meets the rim chamfer
   (all < 1 um2, at x +-54.3 / y +-76.8, z 0.25 / 15.1) - cosmetic, slicers ignore them
I  22 screw pilot holes (LCD 4, R307 2, RC522 4, ESP32 4, fan 4, plate 4) all
   hole-empty + material-around PASS, + 4 x d4.0 cable-tie holes
J  12/12 polish + assembly probes PASS
K  independent STL-only re-verification: 12 sections, 0 failures
   (docs/v2_independent_verify.txt) - incl. thinnest wall 1.20 mm (fan ring),
   0 of 11100 samples of the 12 mm RF scan volume inside material, 240/240 valid
   slices, 22/22 pilot radii measured to +-0.05 mm, 198.0 cc total material
RESULT: ALL CHECKS PASS
```

## §22 Deliverables

1. `cad/v2/01_MAIN_SHELL_v2.stl`, `02_REAR_PLATE_v2.stl`, `03_R307_BRACKET_v2.stl`,
   `04_RC522_CLAMP_v2.stl` (watertight, single body each) — **print part 04 twice, rotate the second
   copy 180° about Z**.
2. `docs/v2_audit.txt` — the scorecard above, regenerated by the build.
3. `renders/v2_shell_drawing_sheet.png`, `renders/v2_exploded_iso.png`,
   `renders/v2_fixing_detail.png` (exploded + section proof of the RC522 screw fixing — in the
   section, bright material is what the cut plane passes through and dim material sits behind
   it, so a reader cannot mistake background for a cut face; the section is dimensioned with
   the stack-up wall 3.0 / board 1.6 / lip 0.9 / platform 1.6 / pad 2.5 and the 4.1 mm blind
   pilot that leaves 1.4 mm of wall underneath) , `renders/v2_all_views.png` (all four sheets
   on one page) and `renders/rfid_before_after.png` — annotated views.
4. `viewer.html` — interactive, self-contained 3D review of all parts (both revisions).
5. `tools/build_v2.py` — the parametric source; **the model is the script**, so any dimension change
   re-derives the whole enclosure and re-runs the audit.
5b. `tools/verify_v2.py` + `docs/v2_independent_verify.txt` — the independent check: it reads only the
   exported STLs and re-measures the same facts from scratch, so a mistake in the generator cannot
   hide behind itself.
6. `docs/master_prompt.md` — this file.
7. `exports/ASTRO_SMART_ATTENDANCE_v2.zip` — everything above in one archive (STLs + drawing sheet +
   audit + this prompt + the generator script).

## §23 Open items — `VERIFY_ACTUAL_HARDWARE`

1. ESP32 pad hole centres (inset 3.5 mm assumed after measuring a DOIT V1).
2. RC522 corner-hole pitch — **not used**: the board is held by two clamp bars over its short edges,
   so no RC522 hole is relied on at all. Board outline 60 × 40 × 1.6 confirmed.
3. R307 bracket hole pitch (28 mm centres assumed, matching the module’s body holes).
4. LCD + I²C backpack total depth (18.24 mm assumed; the 11.5 mm boss height + 1.6 mm PCB gives
   1.5–2 mm of cable space — if the delivered module is deeper, raise `lcd_glass_t` and re-run).
5. Fan thickness ≥ 10 mm (if a 10 mm fan is fitted with a gasket, raise `fan_post`).

The 60 × 40 board's fixing pads are printed at ±22 / ±27 mm from the recess centre — that is *our*
choice of where to grip the board, not a hole position on the module, so it cannot be wrong.

If any of these measures differently on the delivered hardware, change the parameter in
`tools/build_v2.py`, re-run, and re-issue the audit table. That is the whole point of the parameter
table: **no dimension is hard-coded twice.**

## §24 Review workflow (how a revision is presented)

1. `python3 tools/build_v2.py` → STLs + `docs/v2_audit.txt` (scorecard §21).
2. `python3 tools/make_sheet_v2.py` → `renders/v2_shell_drawing_sheet.png` (front / iso / −X side /
   rear plate, annotated from the same parameter table) and `renders/v2_exploded_iso.png`.
3. `viewer.html` served over HTTP — rotate/zoom, Iso/Front/Side/Top/Rear, Explode, Half-cut, and
   per-part visibility, with the v1 parts kept alongside for comparison.
4. Quote `RESULT:` line of the audit verbatim in the reply. If it is not `ALL CHECKS PASS`, the
   revision is not delivered — the failing line is the work item.

## §25 Anti-patterns that already cost this project a revision (do not repeat)

1. **A closed pocket floor over the RFID antenna** — the v1 shell had 3 mm of plastic across the
   whole RC522 recess: the reader could not scan. Any wall in front of an antenna is a defect.
2. **Hollowing the cavity after the bosses were added** — the pocket cut deletes bosses, so thickness
   probes read 0. Order: hollow → union structure → cut openings → re-union in-cut features.
3. **Edge-contact unions.** Two ribs that meet exactly on a shared edge (or two solids that touch
   on a face) produce a non-manifold edge counting four faces: trimesh reports
   `watertight=False` on the exported file even though nothing is open. Overlap every union by
   ≥ 0.5 mm (here 1.0 mm) in **both** in-plane directions and re-check section H.
4. **Pilots that open into nothing.** A blind hole that touches no surface becomes an internal void;
   the STL then reports several “bodies” with negative volume and slicers disagree. Every pilot must
   break through exactly one surface (screw entry) and stop short of the other (§19.5).
5. **Reversed box coordinates** build a mirrored 12-face solid that reports “watertight” and then
   fails every boolean. Sort coordinates in the box helper.
6. **Oversized boolean cutters** that remove the wall they were meant to leave, and **coplanar cut
   faces** that leave zero-thickness skins — offset every cutter 0.1–2.0 mm past the face.
7. **Retainer hooks over a board** — a hook that intrudes 0.5 mm into the board envelope is a fit
   failure even if it “looks right”; the envelope test is the judge.
8. **Interference “fixed” by deleting the part** — shell↔plate clashes are relief/height problems:
   add the register-lip relief, shorten the boss, never remove the feature.

## §26 Acceptance checklist (done = every line ticked)

- [x] RFID scan window open through the front wall over the whole antenna, keep-out proven empty.
- [x] Fingerprint optical window open, sensor 1.6 mm proud, posts exactly 23.5 mm.
- [x] LCD window/bezel matches the 80 × 36 module and the 75.1 × 31 hole pitch.
- [x] ESP32 bay sized from 51.45 × 28.33, antenna keep-out clear, USB plug passes the slot.
- [x] Fan grille + 4 posts at 24 mm, pilots reachable by a driver from the rear.
- [x] Enclosure derived from the layout; walls 2.4–3.0 mm; fit 0.35 mm; clearance 1–2 mm.
- [x] Single watertight body, no supports, front-face-down print.
- [x] Every part a separately named object; no card, no card holder, no prices, no fictional parts.
- [x] Every module fixed by **circular pilot holes** (22 holes, hole-empty + material-around proved).
- [x] Scorecard delivered with measured values; unresolved items marked `VERIFY_ACTUAL_HARDWARE`.

---

## §27 v3 APPENDIX - the complete re-design (and what a v4 must not lose)

v2 kept failing the human test: after every repair the box still looked like the box. v3 is
therefore **not** a re-tune. `tools/build_v3.py` is a fork of the v2 generator whose *decisions*
were replaced, and it re-derives the same keep-outs, envelopes and proof figures. If you rebuild
again, these are the eight decisions that make v3 what it is - keep them or beat them with a
measurement, never silently revert them:

1. **Depth is an output, not a choice.** 46 mm = 3.0 front wall + the RC522 stack (1.6 board +
   2.6 ring + heads) + the ESP32 bay + 3.0 cover. v2's 48 mm was 2 mm of solid rear plug.
2. **Side walls 2.6 mm** (v2: 2.4) and a flat 3.0 mm fan wall; the thinnest *sheet* in the print
   is the 2.2 mm band the RC522 lies on.
3. **The scan aperture is one opening**: 38 x 56 (portrait, since v3.2), R5 corners, no bars,
   no floor, no recess
   material inside it. Proof: `K1` ray-scans 8269 points masked to the same rounded rectangle
   the geometry uses - 0 blocked. A rectangular grid over a rounded opening reports a false
   failure at its own corners; a rectangular metric over a rounded feature reports a false pass.
4. **The RC522 is held by one flat ring**, printed once: its inner lip stands 0.5 mm inside the
   aperture, its 4 corner tabs land on 4 pads whose tops are coplanar with the board's front
   face (z = 4.6), and 4 x M2.5 pull it down into blind d2.05 x 3.8 pilots (the thread's minor,
   not nominal) with 1.4 mm of wall left under them. The tabs are generated FROM the pad offsets
   `(rc522_post_off)`, never typed - v3.0 typed them and 22 mm of tab hung in air after the swap. No clamp bar crosses the antenna, no reliance on the module's own hole pitch.
5. **Rebate rings, not flush cuts**: 0.45 x 3.0 mm sunk around the LCD and fingerprint openings,
   so each module's bezel registers on the rebate floor (2.55 mm of wall remains under the ring).
   The fingerprint opening is the *bezel relief* footprint (21 x 25) with the 19.3 x 21.2 optical
   window inside it - the ledge that v2 left between the internal pocket and the rebate was
   1.15 mm and is deleted.
6. **Rear plate = register frame** (2 mm proud, 0.25 mm per side, 8-sided) with the whole ESP32
   zone cut out by ONE clearance box. Per-boss notches and rib-splitting both failed: the ESP32
   has 4 bosses *and* 2 locating tabs, and the -Y rib's end collided too. Build the frame
   continuous, then subtract one generous box; 90 of 148 mm of register remains, plenty for
   4 screws. 53.8 cm3 instead of a 79.6 cc solid plug (v3.1 added the relief cut through the
   skin, which is +2.4 cc of frame and -0 mm of interference).
7. **Air path**: 8 x 30 x 5 mm stadium slots (1157 mm2) on the wall opposite the fan - never
   round holes there, a d5.0 hole 5.5 mm from a 3 mm wall leaves a 2.0 mm ligament and splits on
   the spool's own tension. d28 bore with no grille and no seat lip, 4 x (20 x 4) exhaust slots and
   3 x (16 x 3) top vents. v2's 3 grille bars left 50 % of the bore closed.
8. **Everything is measured twice.** `build_v3.py` sections A-K (interference, envelopes,
   openings, other parts, probes, printability, STL re-read, the 22-hole pilot census, the
   bed envelope, the measured v2->v3 deltas) and `verify_v3.py`, which imports nothing from the
   generator - re-types the reference dimensions, re-cuts the meshes, re-measures every pilot
   diameter with 8 rays at 3 depths, slices every 0.2 mm, and re-derives the outer dimensions.

### New checks worth keeping in any future verifier
* `K1`/`K2` aperture and bore ray-scans (masked to the real shape) - catches "opening" claims
  that a bar or a lip quietly invalidates.
* `K3` pad-top flatness probes + the bearing-face probes - the ring only works if the surface it
  sits on is one plane; probe the *feature*, not a point 30 mm away that lands on a side wall.
* `K4` plate volume vs the plug it replaced - a fit relief that adds plastic back is a design
  regression even when every hole passes.
* "the register is a frame, not a plug": count material inside the opening at z = shell top
  (v3: 19.3 % of the opening area, all of it the frame).
* driver access as a 6 mm x 25 mm cylinder swept from outside to each head; the R307 bracket
  needed 13 mm of *lateral* corridor, so measure access along the actual approach direction.
* hole-position checks must go through the section's world transform. `Path2D` frames are offset
  (here by (+6.45, +9.05) mm), so a hole centre read straight out of `to_2D()` will not match a
  design coordinate and a filter on "is this the RFID opening" will find nothing.
* envelope boxes must be built from absolute min/max coordinates. A helper that centres a box on
  the origin turns a whole clearance section into a false PASS (it happened, and the fix was to
  re-run the section, not to re-state the numbers).

### Figures a rebuild must regenerate (additions to §22)
`v3_drawing_sheet.png`, `v3_exploded_iso.png`, `v3_fixing_detail.png`, `v3_fixing_section.png`,
`v3_all_views.png`, `v3_vs_v2.png`. The two fixing panels are cut from the shipped STLs with
`mesh.section()`, so they cannot drift; `v3_vs_v2.png` renders both versions with the same
`projection()` call, which is what makes "it looks unchanged" impossible to argue with.

## §28 v3.1 / v3.2 APPENDIX - the physics round (a third checker, and what it caught)

After both CAD checkers said PASS the box was still not *physically* checked, so
`tools/audit_physics_v3.py` was written: 10 sections, no re-use of the generator's numbers, each
one re-measured off `cad/v3/*.stl`. It is now the third gate and has to say
`PHYSICS RESULT: no failures` before a pack is cut.

| section | question it answers | verdict on the shipped model |
|---|---|---|
| 1 fasteners | is each pilot at the thread's minor, and will the thread pull out? | play 0.01-0.05 mm; 75-362 N per screw vs the 0.15-0.88 N it actually holds |
| 2 clamping | is anything crushed, and is any head too tall for the gap behind it? | LCD bezel and R307 shoulder in compression; every head clears the plate |
| 3 kinematics | can each part actually be *installed*, straight in, no tilting? | all 6 modules + the plate descend with 0 blocked samples |
| 4 airflow | does the fan get air on both sides of the loop? | 615 mm2 bore in series with 1609 mm2 of grille-free path = 2.6x the bore; 0.86 L/s = 86 % of free air; dT 1.6 K; box changed every 0.9 s |
| 5 optics | can the sensor see a finger, and can a human read the display? | 1815 of 1815 cone samples clear of the ring; LCD visible to 113 deg |
| 6-7 RF | does plastic or metal sit in front of an antenna? | RC522 0 of 4350 points in material (aperture 100 % open), ESP32 keep-out 0 of 4350, no copper within 6 mm of the trace |
| 8 plastic stress | plate peel, hook shear, wall ligaments, countersink edge distance | 289x peel reserve; hooks 0.16 MPa vs 8.5; RFID<->R307 ligament 22.50 mm; countersink wall 2.25 mm |
| 9 slicer reality | first layer, overhangs, thin sheets, density, thermal | 11 396 mm2 single contour, 0.40 % of faces steeper than 60 deg, all >= 2.2 mm, 154 g, PETG note |
| 10 doc truth | does every sentence in the pack match the triangles? | re-greps the docs, checks the required strings AND every `cm3` figure against the mesh volumes |

**Four real defects it found, all fixed in the geometry - not in the text:**
* **F11 (v3.1) - the plate's countersinks opened onto a corner round.** A d6.6 x 90 deg cone at
  (+/-50, +/-71) left 0.08 mm of plastic on one side: it would print as a lip that shears off, and
  the flat head would sit on air. Fixed by moving the 4 plate screws to (+/-46.5, +/-67.5) and
  keeping the corner rounds; measured wall now 2.25-3.80 mm.
* **F12 (v3.1) - the ESP32 fit relief was cut *through* the plate skin.** v3.0's "clearance" was a
  hole: the board saw 0 mm of gap but rain and dust had a 34 x 20 mm doorway. Fixed by reliefs on
  the frame's 4 vertical ribs and the +/-X ribs only, so the 3 mm skin stays continuous; the mid-
  thickness slice of the skin must show **exactly 6 voids** (2 keyholes + 4 countersinks) - the
  verifier fails if a 7th appears. Plate 51.4 -> 53.8 cm3 (+4.9 g) for a closure that closes.
* **F13 (v3.2) - the RC522 could not be installed.** Landscape, the board is 59.6 mm wide and the
  front-wall bay between the ESP32 post ends (x -42.4) and the R307's -X post (x +15.95) is
  **58.35 mm**; every dodge path is closed by the fan standoffs (y 1..7 and 27..33). Rotated to
  portrait: 40.6 across, 58.4 along, drops straight in with 6.4 mm to spare, and it lengthened the
  thin RFID<->R307 ligament from 17.50 to 22.50 mm as a bonus. Side effect the user wanted: the
  front face now visibly differs from v2 (portrait swipe window).
* **F14 (v3.2) - the two checkers disagreed on mass by 50 g.** `verify_v3` applied a blanket 0.62
  factor; the shell is a thin-walled box where 3 perimeters x 0.45 mm fill a 2.6 mm wall *solid*.
  Both now use the same model - walls solid, 3 skins, 15 % core -> 154 g, 1 kg spool = 6.5 sets.

**Accepted by design (recorded as notes, not failures):** the M2.5 pan head ends 0.90 mm proud of
the ring's inner face (it sits in the recess, on the PCB side - it never touches the rear plate);
and if the unit is mounted on an unshaded outside wall, print in PETG because the top surface of a
black-ish PLA box in Indian sun passes PLA's 55-60 deg heat-deflection point.

**Rules a rebuild must keep from this round:**
1. Every module must enter by **descending along one axis** with 0 blocked samples at every
   intermediate position - check kinematics, not just the final assembled overlap.
2. Intact area of an intake/exhaust must be **>= 1.5x the fan bore**, and slots (not round holes)
   within 3 mm of a wall.
3. Countersink edge distance >= half the cone diameter, measured to the *real* outline.
4. A closure plate gets no through-holes for clearance; relieve the register instead.
5. Any feature that reaches a mounting pad is **generated from the pad's offset**, never typed.
6. Pilots are at the thread's minor (2.05 / 2.50 / 1.80), never nominal.
7. Reader header over the pads must be <= ~6 mm (the channel under the ESP32 posts is 9.8 mm) or
   fit the reader before the ESP32; no M3 at the ESP32's antenna end, and no steel or brass
   washers under those heads.
8. A claim in a doc is a measurement the third checker re-runs: when geometry changes, the doc
   edit is part of the fix (`docs/v3_physics_audit.txt` section 10 refuses a stale number).
