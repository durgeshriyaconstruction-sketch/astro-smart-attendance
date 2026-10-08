# STL 1 — `01_MAIN_SHELL.stl` — what is in the file

Measured directly from the mesh (see `tools/` and `docs/stl_measurements.txt`).
Coordinates: **X = width**, **Y = height**, **Z = depth**, Z0 = the *device front* face,
Z48 = the rear (closed by part 02).

## Overall
| | |
|---|---|
| Overall size | 110.0 (X) × 155.0 (Y) × 48.0 (Z) mm |
| Triangles / shell | 4096 tris, 2018 unique vertices, closed shell |
| Wall thickness | 2.4 – 3.0 mm |
| Shell volume | ≈ 108.2 cm³ |

## Front face (z = 0)
| Feature | X | Y | Size | Depth |
|---|---|---|---|---|
| LCD1602 window (through slot) | −32.6 … 32.5 | 44.5 … 59.4 | 65.1 × 14.9 | through |
| Reader opening | 26.3 … 45.6 | −34.7 … −13.5 | 19.3 × 21.2 | through |
| Recessed pocket | −51.4 … 11.3 | −46.4 … −1.7 | 62.7 × 44.7 | 1.5 deep |

## Rear opening (z = 48)
102.9 × 150.2 mm, leaving a 3.0 mm rim all round → closed by `02_DETACHABLE_WALL_PLATE.stl`
(plate 110 × 155 × 9.45 mm, weight-relieved 1.5 mm deep on the inside, four ⌀4.35 mm corner holes).

## Left wall (x = −55)
Four vents, 2.8 × 11.8 mm, at Y ≈ 0.6 / 8.6 / 16.6 / 24.6, Z 11.1 … 22.9.

## Inside the shell
| Feature | Position | Notes |
|---|---|---|
| LCD frame | 4 bosses 12.7 × 12.7 mm, corners at ±37.55, 36.45 / 67.45 | z 3.0 … 11.0, ⌀1.5 pilots 4.5 mm deep |
| Rear standoffs | 3.3 mm square, x ±23.4…25.4 / 45.1…48.6, y 22.1…35.5 / 36.8…43.5 | z 37.5 … 40.0 |
| R307 retention | pads z 28.1 … 30.1, ⌀2.2 holes at (22.5, −24.0) and (49.5, −24.0) | pilot in shell at z 8.3: (22.4/49.4, −24.0) |
| RC522 retention | pads z 4.35 … 5.95, ⌀2.2 holes at (−52.0, −7.0) and (12.0, −7.0) | pilot in shell at z 5.5: (12.0, −7.0) |
| ESP32 retention | pads z 35.4 … 36.8, ⌀2.2 holes at (9.5, −25.0) and (46.5, −25.0) | |

## Other parts
| File | Size | What it is |
|---|---|---|
| `02_DETACHABLE_WALL_PLATE.stl` | 110 × 155 × 9.45 | rear wall plate, 4 corner holes ⌀4.35 at ±34, ±52 |
| `03_R307_RETENTION.stl` | 34 × 12 × 2 | bracket for the R307 fingerprint module |
| `04_RC522_RETENTION.stl` | 72 × 4 × 1.6 | bracket for the RC522 RFID reader |
| `05_ESP32_RETENTION.stl` | 44 × 4 × 1.4 | bracket for the ESP32 dev board |

## Views
`renders/shell_drawing_sheet.png` — 4-panel annotated drawing,
`renders/exploded_iso.png` — exploded assembly, `renders/*.png` — individual views.
Interactive: open `viewer.html` (rotate / zoom / explode / half-cut).
