# Presentation — `Astro_Smart_Attendance_Technology.pptx`

A 39-slide, 16:9 technology presentation for **Astro Smart Attendance**, built by
Team Sun Rises India (Class 9, The Aditya Birla Public School, Renukoot).

Open the `.pptx` in PowerPoint, Google Slides, Keynote or LibreOffice. Every slide
carries **speaker notes** with what to say and which file the numbers came from.

---

## What is in it

| | Part | Slides | Covers |
|---|---|---|---|
| **01** | The system | 3–13 | problem, ₹1,500 bill of materials, ESP32, RC522, R307, offline-first, Firebase, roles, guardian alerts |
| **02** | The engineering | 14–25 | parametric CAD-as-code, build pipeline, four independent checkers, fasteners, the RFID fix, assembly, printing, thermal, material, v2→v3, deliverables |
| **03** | The evidence | 26–39 | Astro AI, validation, impact, results scoreboard, limitations, reproducibility, failure analysis, team, pilot plan, three appendices |

**Short on time?** Slides 3 → 4 → 5 → 7 → 14 → 17 → 19 → 30 are the spine of the
7-minute zonal video the Kreativity League asks for.

The structure follows the League's 100-point rubric — 20 each for problem solving,
STEM/computational thinking, innovation and implementation, communication, and teamwork —
which is why there is a real problem slide, a real code slide, a real scoreboard, an
explicit limitations slide and a team slide.

---

## Design

* Palette, type and the "audit" look are taken from the repository's own 3D viewer
  (`viewer.html`): near-black `#0E1014`, amber `#FFCD50`, cyan `#78DCFF`, green `#8FE0A8`,
  magenta `#F0A8D8`.
* Every slide is generated from data in `part1.py` / `part2.py` using the helpers in
  `deck_lib.py` — no hand-placed shapes to repair later.
* Figures are the project's **real Blender and mesh renders** from `renders/`, cropped and
  optimised into `assets/`. No stock or AI-generated imagery is used anywhere.
* Headlines are auto-fitted to one line by measuring the string, and `kpi()` / `card()`
  derive their text positions from measured heights, so edits cannot quietly collide.

---

## Rebuild

```bash
pip install python-pptx pillow
python3 presentation/build_deck.py
```

Output: `presentation/Astro_Smart_Attendance_Technology.pptx`.

### Layout QA without PowerPoint

`preview_deck.py` re-draws the `.pptx` (shapes, tables, pictures, text) into PNGs with
PIL, using DejaVu — deliberately ~8 % wider than Segoe UI, so anything that fits in the
preview fits in PowerPoint. It also emulates PowerPoint's two nastiest behaviours: text
spilling out of its box, and table rows growing taller than their nominal height.

```bash
python3 presentation/preview_deck.py \
        presentation/Astro_Smart_Attendance_Technology.pptx /tmp/preview
```

It prints every text overflow and table overrun it finds, slide by slide.

### Editing content

| Want to change | Edit |
|---|---|
| a slide's wording or numbers | `part1.py` (slides 1–20) or `part2.py` (21–39) |
| colours, fonts, margins | `deck_lib.py` palette block |
| slide order | `SLIDES` list in `build_deck.py` |
| speaker notes | the `notes(s, ...)` call at the end of each slide function |

---

## Where every number comes from

Nothing in this deck is invented. The source of each figure:

| Claim | File |
|---|---|
| enclosure dimensions, walls, fits, keep-outs | `docs/v3_audit.txt`, `docs/master_prompt.md` |
| independent re-measurement of the STLs | `docs/v3_independent_verify.txt` |
| fasteners, airflow, RF, optics, PLA, slicer | `docs/v3_physics_audit.txt` |
| every rebate and lip at 0.02 mm | `docs/v3_groove_check.txt` |
| the 22 screw depths | `docs/v3_hole_probe.txt` |
| design history v3 → v3.6 | `docs/v3_design_notes.md` |
| the `.blend` verification | `docs/v3_blend_check.txt` |
| electronics, features, cost, team | `README.md` |

> The deck deliberately does **not** claim a classroom field trial, and slide 31 says so,
> because the project's own audit rule (`master_prompt.md` §3) is "never write PASS unless
> a check produced that PASS".
