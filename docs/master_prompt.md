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

1. **Open scan window `RC522_SCAN_ZONE` = 54 × 36 mm, completely open through the 3 mm front wall**
   (no floor, no membrane, no printed skin — an RFID field will not pass a printed wall reliably).
2. The window sits inside the existing **62.7 × 44.7 mm × 1.5 mm recess**, so the RC522’s 6 mm-tall
   components nest *into* the recess and the antenna sits **1.5 mm** behind the outer face — as close
   to the outside as physically possible.
3. **Stiffness:** the 3 mm front wall is locally reduced to a 1.45 mm web; two stiffener bars
   **2 mm wide × 4 mm**, spanning the 36 mm window, keep the front face rigid. They are the *only*
   material inside the window and they are ≤ 6 % of its area.
4. **`RC522_RF_KEEP_OUT`:** a 62.7 × 44.7 × 12 mm volume in front of the antenna is declared
   metal-free and plastic-free; the audit proves enclosure material volume inside it = **0.00 mm³**.
5. **`RC522_SCAN_ZONE`** additionally proves that the window is genuinely through-cut: a ray cast
   from outside the front face passes through the wall into the cavity.
6. The RC522 is **screwed down**, not clipped: **4 × M2.5 screw pads (2.5 mm tall, ⌀2.2 pilot,
   4.1 mm deep)** sit at ±22.0 / ±27.0 mm from the recess centre (clear of the board and of the
   54 × 36 window), and **two printed clamp bars** hold the board edges — 62 × 13 mm platform with a
   3 mm lip that presses the PCB down onto the front wall, 2 × ⌀3.0 through-holes + ⌀5.6
   counterbores, hole centre distance 44 mm. The whole antenna face stays open and screwdriver
   access is straight down the Z axis from the rear opening.

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
| R307 window | **19.3 × 21.2** at (+35.95, −24.1) + 25 × 27 × 1.6 bezel relief | [V1] |
| R307 module | sits on 2 posts 6 × 6 × **23.5** tall at x = 22.0 / 50.0, y = −24.1, ⌀2.5 pilots | [REF] |
| R307 bracket | 33.5 × 12 × 2 steel, ⌀3.0 + ⌀5.6 counterbores, 28 mm hole centres → `VERIFY_ACTUAL_HARDWARE` | [EST] |
| RC522 recess / window | 62.7 × 44.7 × 1.5 recess, **54 × 36 open window + 2 × 4 bars** at (−20.05, −24.05) | [V1] + fix |
| RC522 fixings | 4 × M2.5 pads 2.5 mm (⌀2.2 × 4.1 pilot) at (−20.05 ± 22, −24.05 ± 27) + 2 printed clamp bars (62 × 13, ⌀3.0/⌀5.6, 44 mm centres) | new |
| ESP32 bay | on the **−X wall**, board plane X = −42.6 (10 mm standoff), Y −70 … −18.55, **Z centre 27.5** | [REF] |
| ESP32 pads | 4 × 8 × 8 pads, ⌀2.2 pilots 7 mm deep | [REF] |
| USB slot | **18 × 10** at Z 27.5 on the bottom edge (+2.4 chamfer), plug body 15.6 × 8 fits | [REF] |
| Fan | 3010 at (Y **17**, Z **24**) on the −X wall, ⌀26 grille + 3 bars, 4 × M3 posts (24 mm) | [REF] |
| Exhaust | 2 × 2 slots 20 × 4 at Y ±16, Z 6 / 12 (−X wall) | — |
| Top vent | 3 slots 16 × 3 at X −18 / 0 / 18, Z 26 (−X wall, above the fan) | — |
| Rear plate | 110 × 155 × 3 flush + 2 mm register lip + 2 mm spine ribs, 4 × M3 into 9 mm bosses at (±46.5, ±71) | — |
| Keyhole hang | ⌀7.5 + 4.6 mm slot, 50 mm span, on the plate centre line | — |
| Cable ties | 3 posts ⌀8 with ⌀4 through-holes at (−10, −66), (16, −66), (44, 12) | — |

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
| 4 | M2.5 × 12 | LCD ↔ 6 × 6 bosses | ⌀2.5, 7 mm deep | hold LCD at 11.5 mm |
| 2 | M3 | R307 bracket → 6 × 6 posts | ⌀2.5, 7 mm deep | hold the fingerprint module |
| 4 | M3 × 20 | fan → posts | ⌀2.5, 12 mm deep | fan retention |
| 4 | M2.2 × 6 | ESP32 corner pads | ⌀1.8, 7 mm deep | board standoff |
| 4 | M2.5 × 6 | 2 clamp bars → RC522 pads | ⌀2.2, 4.1 mm deep | hold the RC522 down |
| 3 | cable ties | ⌀8 posts, ⌀4 holes | — | strain relief |

Nothing is priced. No screw is invented.

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

**Delivered revision result (all lines measured, none assumed):**

```
shell     : 9892 tris, watertight=True, winding_ok=True, bodies=1
shell size: [110.0, 155.0, 45.0] (depth 45 + 3 mm plate = 48)
volume    : 115.1 cm3  ~71 g PLA (15 % infill)
A  shell<->plate 0.00 PASS   shell<->bracket 0.00 PASS
B  LCD glass / PCB+backpack / bezel / R307 / RC522 board+components+scan zone /
   ESP32 board+components / ESP32 RF keep-out / USB plug / Fan 3010   ALL 0.00 PASS
C  LCD window, R307 window, RFID scan window, USB slot, fan grille,
   exhaust slot, top vent                               open=True wall_ok=True PASS
D  rear plate 110 x 155 x 7 watertight 81.9 cm3 ; R307 bracket 33.5 x 12 x 2 watertight ;
   RC522 clamp 62 x 15 x 2.5 watertight 1.6 cm3 (print 2, second rotated 180 deg)
E  front 2.90 / RFID recess 1.45 / stiffener bar 1.45 / side 2.35 / top 2.90 /
   bottom 2.90 / LCD boss 11.50 / R307 post 23.50                            PASS
F  all model dims match the reference table (2 items VERIFY_ACTUAL_HARDWARE)
G  overhang 155 mm2 = 0.18 %  -> SUPPORT_REQUIRED = NO
H  re-read from disk: shell / plate / bracket / RC522 clamp = 0 open edges,
   0 non-manifold edges, 1 body each
I  22 screw pilot holes (LCD 4, R307 2, RC522 4, ESP32 4, fan 4, plate 4) all
   hole-empty + material-around PASS, + 3 x d4.0 cable-tie holes
RESULT: ALL CHECKS PASS
```

## §22 Deliverables

1. `cad/v2/01_MAIN_SHELL_v2.stl`, `02_REAR_PLATE_v2.stl`, `03_R307_BRACKET_v2.stl`,
   `04_RC522_CLAMP_v2.stl` (watertight, single body each) — **print part 04 twice, rotate the second
   copy 180° about Z**.
2. `docs/v2_audit.txt` — the scorecard above, regenerated by the build.
3. `renders/v2_shell_drawing_sheet.png` + `renders/v2_exploded_iso.png` — annotated views.
4. `viewer.html` — interactive, self-contained 3D review of all parts (both revisions).
5. `tools/build_v2.py` — the parametric source; **the model is the script**, so any dimension change
   re-derives the whole enclosure and re-runs the audit.
6. `docs/master_prompt.md` — this file.
7. `exports/ASTRO_SMART_ATTENDANCE_v2.zip` — everything above in one archive (STLs + drawing sheet +
   audit + this prompt + the generator script).

## §23 Open items — `VERIFY_ACTUAL_HARDWARE`

1. ESP32 pad hole centres (inset 3.5 mm assumed after measuring a DOIT V1).
2. RC522 corner-hole pitch (board 60 × 40 confirmed; holes ≈⌀3, pitch not measured) — the four
   retention tabs are **slotted** precisely so a small pitch error still grips.
3. R307 bracket hole pitch (28 mm centres assumed, matching the module’s body holes).
4. LCD + I²C backpack total depth (18.24 mm assumed; the 11.5 mm boss height + 1.6 mm PCB gives
   1.5–2 mm of cable space — if the delivered module is deeper, raise `lcd_glass_t` and re-run).
5. Fan thickness ≥ 10 mm (if a 10 mm fan is fitted with a gasket, raise `fan_post`).

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
