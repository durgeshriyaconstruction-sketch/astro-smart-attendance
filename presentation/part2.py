"""
ASTRO SMART ATTENDANCE - deck part 2: slides 21-38.
The engineering depth, the evidence, the risk register, and the delivery plan.
"""
from deck_lib import *   # noqa


# =============================================================  21  AIRFLOW
def s21_airflow(prs, i, n):
    s = slide_new(prs)
    header(s, "Thermal", "We deleted the vents and measured the cost",
           "A 3010 fan, a Ø28 bore as the only air opening, and a heat path that mostly does "
           "not care about openings at all.")

    # the two paths
    text(s, ML, 1.98, 6.2, 0.26, "Two paths in parallel", size=10, color=AMBER, bold=True,
         caps=True, spc=160)
    for k, (title_, formula, result, col) in enumerate([
        ("1 · Passive skin", "ΔT = P / (h · A)", "2.7 K above ambient", CYAN),
        ("2 · Fan through-flow", "0.25 L/s through 784 cm³", "one air change every 3.2 s", GREEN)]):
        x = ML + k * 3.20
        rect(s, x, 2.26, 3.02, 1.62, fill=PANEL, line=LINE, lw=0.75, radius=0.04)
        rect(s, x, 2.26, 3.02, 0.035, fill=col)
        text(s, x + 0.20, 2.42, 2.62, 0.24, title_, size=10.5, color=col, bold=True)
        text(s, x + 0.20, 2.72, 2.62, 0.28, formula, size=8.8, color=SOFT, font=MONO)
        text(s, x + 0.20, 3.06, 2.62, 0.26, result, size=9.4, color=WHITE, bold=True)
        text(s, x + 0.20, 3.42, 2.62, 0.38,
             "heat leaves through the PLA by convection and radiation" if k == 0
             else "orifices in series with the fan's own curve", size=7.8, color=DIM, line=1.15)

    rows = [
        ["Measured", "v3.3 (12 grille slots)", "v3.4 (1 bore, shipped)"],
        ["Outlet area", "1,069 mm² across 12 slots", "0 mm² — all twelve filled in"],
        ["Air opening", "bore + grilles", "615 mm² Ø28, and nothing else"],
        ["ΔT at 1.6 W (both paths)", "1.6 K", "1.8 K"],
        ["Ceiling for the ESP32 crystal", "12 K", "12 K"],
        ["Plastic saved", "—", "3.2 cm³ / 3 g"],
    ]
    table(s, ML, 4.04, 6.22, [2.30, 2.04, 1.88], rows, size=9, head_size=8.4, row_h=0.40,
          first_bold=True, colors={(3, 2): GREEN, (3, 1): GREEN})

    fig_dark(s, A("wall_map"), ML + 6.54, 1.98, 5.56, 1.72)
    text(s, ML + 6.54, 3.76, 5.56, 0.30,
         "Every opening on the printed box, measured at mid-thickness",
         size=8.0, color=FAINT, line=1.2)

    rect(s, ML + 6.54, 4.60, 5.56, 1.70, fill=PANEL2, line=LINE, lw=0.75, radius=0.05)
    text(s, ML + 6.76, 4.74, 5.1, 0.24, "THE HONEST RESULT", size=9, color=AMBER, bold=True, spc=160)
    text(s, ML + 6.76, 5.02, 5.1, 1.16,
         "Closing twelve vents costs about 0.2 K. What the fan actually does inside a near-sealed "
         "box is break the boundary layer off the LCD and the R307 prism, and hold the enclosure "
         "slightly above room pressure so dust is pushed out of the optics rather than sucked in.",
         size=9.2, color=SOFT, line=1.3)

    rect(s, ML, 6.52, 6.22, 0.38, fill=PANEL, line=LINE, lw=0.7, radius=0.06)
    text(s, ML + 0.18, 6.60, 5.9, 0.24,
         "Ceiling check: 12 K is where the ESP32 crystal starts to drift. We sit 10.2 K inside it.",
         size=8.6, color=GREEN)

    footer(s, i, n, "Thermal — physics audit §4 · v3_design_notes.md §7, §9")
    notes(s, """
This slide is deliberately honest, and that is the point. The jury will assume more holes means
better cooling. The measurement says otherwise: the plastic skin is the resistor, not the holes.

The best sentence: "we removed twelve openings because the user asked for a clean box, and then
we measured what it cost. Two-tenths of a kelvin."
""")
    return s


# =============================================================  22  MATERIAL
def s22_material(prs, i, n):
    s = slide_new(prs)
    header(s, "Material and environment", "This box hangs on a wall in Sonbhadra",
           "The ambient numbers matter more than the CAD numbers. PLA's glass transition is the "
           "constraint that decided the wall thickness.")

    rows = [
        ["Condition", "Surface temp", "PLA Tg ≈ 60 °C", "Verdict"],
        ["Shaded indoor wall, May peak", "45 °C", "+15 K margin", "PLA is fine"],
        ["Sun through a window onto the wall", "55 °C", "+5 K margin", "PLA is fine"],
        ["Unshaded outside wall / closed room", "65 °C", "−5 K", "print PETG (Tg ≈ 80 °C)"],
    ]
    table(s, ML, 2.02, 7.56, [2.90, 1.36, 1.52, 1.78], rows, size=9.6, head_size=8.6,
          row_h=0.52, first_bold=True,
          colors={(1, 3): GREEN, (2, 3): GREEN, (3, 3): RED, (3, 2): RED})

    text(s, ML + 7.90, 2.02, 4.2, 0.26, "SHRINKAGE VS THE PRINTED FIT", size=10, color=AMBER,
         bold=True, spc=140)
    rows2 = [
        ["Filament", "Shrink", "Effect on the 0.25 mm register"],
        ["dry, tuned", "0.2 %", "0.21 mm — absorbed"],
        ["humid, monsoon", "0.5 %", "0.52 mm — still closes"],
    ]
    table(s, ML + 7.90, 2.30, 4.18, [1.40, 0.78, 2.00], rows2, size=9, head_size=8.4,
          row_h=0.50, colors={2: GREEN})

    text(s, ML, 4.10, 7.56, 0.26, "Why a humid spool still closes the box", size=10,
         color=AMBER, bold=True, caps=True, spc=160)
    bullets(s, ML, 4.38, 7.40, 1.6, [
        ("The register frame is eight separate ribs", "— an oversized rib flexes, it cannot lock the plate out."),
        ("Four M3 screws draw the plate home", "against any 0.5 % growth."),
        ("Both parts are the same plastic,", "so thermal growth is common-mode and cancels."),
        ("Switching to PETG needs no geometry change", "— only the nozzle and bed temperatures change."),
    ], size=9.8, gap=0.06, line=1.26)

    card(s, ML + 7.90, 4.10, 4.18, 1.34, "PETG is the drop-in upgrade",
         "230–240 °C nozzle, 80–90 °C bed. Same four files, same 22 pilots, no re-drawing.",
         accent=ORANGE, hsize=10.2, bsize=8.8)

    rect(s, ML + 7.90, 5.44, 4.18, 1.46, fill=PANEL2, line=LINE, lw=0.75, radius=0.05)
    text(s, ML + 8.10, 5.58, 3.8, 0.24, "AND THE DUST", size=9, color=AMBER, bold=True, spc=160)
    text(s, ML + 8.10, 5.86, 3.8, 0.94, "The enclosure runs at slight positive pressure, so air "
         "leaves through the R307 prism relief and the plate seam rather than entering around the "
         "optics. Dust on an optical sensor is a recalibration, not a cleaning.", size=9, color=SOFT, line=1.28)

    footer(s, i, n, "Material — physics audit §5 · v3_design_notes.md §4")
    notes(s, """
This is the slide that makes the design local. Most teams design a box for a lab. This one is
designed for a classroom in Sonbhadra in May, where a west wall in the afternoon is 55 degrees.

The PETG line is the answer to "what if it is hotter": no re-design, print it in PETG.
""")
    return s


# =============================================================  23  VARIANTS
def s23_variants(prs, i, n):
    s = slide_new(prs)
    header(s, "Design iteration", "v2 was a repaired v1. v3 is a different decision.",
           "Same layout engine, different answers — and every change is measured before and after.")

    rows = [
        ["", "v2", "v3 (shipped)", "Why"],
        ["Overall size", "110 × 155 × 48", "110 × 155 × 46", "depth came out of the RFID stack, not a guess"],
        ["Side wall", "2.4 mm", "2.6 mm", "v2's thinnest structural wall was 1.2 mm at the vents"],
        ["RFID aperture", "56 × 38 + 2 bars (90.4 % open)", "38 × 56, 100 % open", "8,269 rays, 0 blocked; 190 mm² of shadow removed"],
        ["RC522 hold-down", "2 clamp bars, printed ×2", "1 flat ring, printed ×1", "2.2 cm³ instead of two 1.6 cm³ bars; nothing in front of the coil"],
        ["Fan opening", "Ø26 with 3 moulded bars", "Ø28, nothing across it", "the print's most fragile sliver is gone"],
        ["Front openings", "flush cut", "0.45 × 3.0 mm rebate ring", "each module's own bezel registers; no chipped edge"],
        ["Fingerprint mount", "2 posts + flat strap over the glass", "dog-bone bracket + seat ribs", "the bracket lifts off without prying on the glass"],
        ["Rear closure", "2 mm solid plug (79.6 cm³)", "8-sided register frame (53.8 cm³)", "26 cm³ less plastic, real clearance for the ESP32"],
        ["Plastic", "199.6 cm³", "172.2 cm³", "159 g printed instead of 396 g all-up"],
    ]
    table(s, ML, 1.98, CW, [1.60, 2.86, 2.90, 4.73], rows, size=8.5, head_size=8.5,
          row_h=0.40, first_bold=True)

    rect(s, ML, 6.12, CW, 0.78, fill=PANEL2, line=LINE, lw=0.75, radius=0.05)
    rect(s, ML, 6.12, 0.05, 0.78, fill=AMBER)
    text(s, ML + 0.24, 6.24, CW - 0.5, 0.55,
         "Every one of these is a flag in build_v3.py, not a lost version: side_intake=True restores v3.2's "
         "perforated wall, grilles=True restores v3.3's twelve slots. The decisions are reversible in one line, "
         "so they can be argued with instead of defended.", size=9.3, color=SOFT, line=1.28)

    footer(s, i, n, "Iteration — v3_design_notes.md §1")
    notes(s, """
Do not read the table. Say: "v2 was our first box with the mistakes patched. v3 was us deciding
again from the parts, and the differences are measured in the same table."

If a jury member questions a change, every row has a number and a file.
""")
    return s


# =============================================================  24  BLEND
def s24_blend(prs, i, n):
    s = slide_new(prs)
    header(s, "Deliverables", "A .blend, a .glb and a viewer anyone can open",
           "The CAD is not a screenshot in a report. It ships as editable 3D, with the modules, "
           "the fan and all 22 screws modelled at their measured lengths.")

    fig_dark(s, A("exploded_dark"), ML, 1.98, 6.10, 3.32)
    text(s, ML, 5.36, 6.10, 0.62,
         "Exploded view generated by tools/make_fixing_v3.py — shell, rear plate, R307 bracket and "
         "the RC522 ring, with the fastener positions measured off the mesh.",
         size=8.2, color=FAINT, line=1.24)
    text(s, ML, 5.94, 6.10, 0.46,
         "The viewer needs no three.js: tools/make_offline_viewer.py embeds the meshes and a painter's-algorithm "
         "renderer in one HTML file.", size=8.0, color=FAINT, line=1.22)

    rows = [
        ["File", "What it is"],
        ["ASTRO_…_v3.blend", "Blender 4.5 LTS scene: 4 solids, 5 module envelopes, a real 3010 fan, 22 screws"],
        ["ASTRO_…_v3_assembly.glb", "one-file glTF for any web viewer or phone"],
        ["v3_assembly STLs ×4", "the print files, bed-aligned, SHA-256 listed"],
        ["viewer_offline.html", "2.6 MB single file — meshes and a Canvas 2D viewer, no library"],
        ["README_PRINT_ORDER_v3.txt", "print order, screws, settings, assembly sequence"],
    ]
    table(s, ML + 6.44, 1.98, 5.66, [2.22, 3.44], rows, size=8.8, head_size=8.6, row_h=0.56,
          first_bold=True)

    rect(s, ML + 6.44, 4.94, 5.66, 1.96, fill=PANEL, line=LINE, lw=0.75, radius=0.04)
    text(s, ML + 6.66, 5.08, 5.2, 0.24, "THE .BLEND IS CHECKED TOO", size=9, color=AMBER,
         bold=True, spc=160)
    bullets(s, ML + 6.66, 5.30, 5.24, 1.5, [
        ("It re-derives every volume", "from the file's own polygons: 115.22 / 53.80 / 1.01 / 2.19 cm³"),
        ("Every screw axis lands on a hole centre", "— worst error 0.000 mm"),
        ("Nothing may poke outside the case + 2.5 mm", "— caught a floating USB plug"),
        ("Three Cycles frames must not be blank", "— checked by pixel variance"),
    ], size=7.9, gap=0.03, line=1.14)

    footer(s, i, n, "Deliverables — v3_design_notes.md §11 · tools/make_blend_v3.py, check_blend_v3.py")
    notes(s, """
Offer the .glb to the jury on a phone. That is the moment this stops being a report and becomes
a product.

The four bullets are there to make the point that even the presentation artefact is verified.
""")
    return s


# =============================================================  25  SELF HEALING
def s25_selfheal(prs, i, n):
    s = slide_new(prs)
    header(s, "Astro AI 2.0", "Eleven checks that keep a classroom box alive",
           "An attendance terminal has no technician. Astro AI is the firmware layer that detects, "
           "recovers and reports — without a student ever losing a mark.")

    checks = [
        ("RFID reader absent", "SPI version register silent → re-init bus, retry ×3"),
        ("Card read errors", "CRC failures spike → lower SPI clock, re-tune"),
        ("Fingerprint sensor", "UART timeout → power-cycle the module"),
        ("Display blank", "I²C NACK → re-address 0x27/0x3F, re-init backpack"),
        ("Clock drift", "NTP delta over 60 s → resync, keep order"),
        ("Wi-Fi down", "keep scanning, buffer, retry with backoff"),
        ("Flash full", "flush synced batches first, never unsynced"),
        ("Power brown-out", "detector trips → safe write, clean boot"),
        ("Watchdog", "task stalled → only that task is reset"),
        ("Firmware integrity", "OTA hash mismatch → roll back"),
        ("Memory pressure", "heap low → drop the log, keep the queue"),
    ]
    x0, y0 = ML, 1.98
    colw, rowh = 3.98, 0.80
    for k, (head, body) in enumerate(checks):
        col = k % 3
        row = k // 3
        x = x0 + col * (colw + 0.16)
        y = y0 + row * (rowh + 0.245)
        rect(s, x, y, colw, rowh, fill=PANEL, line=LINE, lw=0.6, radius=0.08)
        text(s, x + 0.14, y + 0.085, 0.28, 0.2, f"{k+1:02d}", size=8.0, color=AMBER, bold=True)
        text(s, x + 0.45, y + 0.105, colw - 0.56, 0.24, head, size=9.8, color=WHITE, bold=True)
        text(s, x + 0.45, y + 0.375, colw - 0.56, 0.36, body, size=8.4, color=DIM, line=1.12)

    rect(s, ML, 5.94, CW, 0.92, fill=PANEL2, line=LINE, lw=0.75, radius=0.05)
    rect(s, ML, 5.94, 0.05, 0.92, fill=RED)
    text(s, ML + 0.26, 6.03, 6.2, 0.22, "THE RULE IT IS BUILT ON", size=9, color=RED, bold=True, spc=160)
    text(s, ML + 0.26, 6.28, 6.16, 0.52, "Never lose a mark to recover a sensor. A dead reader leaves "
         "the fingerprint working, and the other way round.", size=9.2, color=SOFT, line=1.24)
    text(s, ML + 6.90, 6.03, 5.1, 0.22, "WHY 11 AND NOT 3", size=9, color=AMBER, bold=True, spc=160)
    text(s, ML + 6.90, 6.28, 5.12, 0.52, "Each one is a failure we could reach on the bench: a pulled "
         "jumper wire, a dead router, a drained battery.", size=9.2, color=SOFT, line=1.24)

    footer(s, i, n, "Astro AI 2.0 — README.md key features")
    notes(s, """
Say the red rule first: "never lose a mark to recover a sensor."

Then explain that the eleven are not hypothetical - each one is a failure the team could produce
in the workshop with a pulled wire or an unplugged router. That is the difference between a
feature list and a testable one.
""")
    return s


# =============================================================  26  TESTING
def s26_testing(prs, i, n):
    s = slide_new(prs)
    header(s, "Validation", "What was tested, and what the numbers actually mean",
           "Two kinds of evidence in this project: tests the team ran on the prototype, and "
           "checks that regenerate themselves from the shipped files.")

    text(s, ML, 1.98, 6.2, 0.26, "Prototype test results", size=10, color=AMBER, bold=True,
         caps=True, spc=160)
    rows = [
        ["Metric", "Result"],
        ["Feature tests passing", "140 / 140"],
        ["Stress-test cases verified", "10,000,000"],
        ["Compiler warnings", "0"],
        ["Compiler errors", "0"],
        ["Prototype status", "working, ready"],
    ]
    table(s, ML, 2.26, 6.06, [3.40, 2.66], rows, size=11, head_size=9.5, row_h=0.52,
          first_bold=True, colors={1: GREEN})

    text(s, ML, 5.74, 6.06, 0.26, "What the stress number is, precisely", size=9, color=AMBER,
         bold=True, caps=True, spc=140)
    text(s, ML, 6.02, 6.06, 0.86,
         "The 10,000,000 is generated input space — UID × timestamp × duplicate × offline-length "
         "combinations driven through the record logic. It is not ten million students, and we do "
         "not present it as such.", size=9, color=DIM, line=1.3)

    text(s, ML + 6.42, 1.98, 5.6, 0.26, "Checks that ship with the repository", size=10,
         color=AMBER, bold=True, caps=True, spc=160)
    rows2 = [
        ["Check", "Coverage"],
        ["Parametric audit A–K", "walls, fits, keep-outs, apertures"],
        ["STL-only verification", "manifold, bed-aligned, every hole"],
        ["Physics audit, 10 sections", "fasteners, air, RF, optics, PLA, slicer"],
        ["Groove probe, 34 values", "each rebate and lip at 0.02 mm"],
        ["Hole probe, 22 pilots", "does the documented screw seat?"],
        ["Blend check", "volumes, screw axes, render frames"],
    ]
    table(s, ML + 6.42, 2.26, 5.68, [2.48, 3.20], rows2, size=9.2, head_size=8.6,
          row_h=0.52, first_bold=True)

    rect(s, ML + 6.42, 5.74, 5.68, 1.14, fill=PANEL2, line=LINE, lw=0.75, radius=0.05)
    rect(s, ML + 6.42, 5.74, 0.05, 1.14, fill=GREEN)
    text(s, ML + 6.66, 5.86, 5.2, 0.24, "THE DIFFERENCE", size=9, color=GREEN, bold=True, spc=160)
    text(s, ML + 6.66, 6.14, 5.2, 0.66, "Prototype tests prove the electronics. The generated "
         "checks prove the product — and they re-run on every rebuild, so they cannot go stale.",
         size=9.2, color=SOFT, line=1.26)

    footer(s, i, n, "Validation — README.md · docs/v3_*.txt")
    notes(s, """
Be precise about 10,000,000. Say exactly what the deck says: it is input-combination space, not
students. A jury that catches you inflating one number stops believing the rest, and the rest is
better than the inflated number.
""")
    return s


# =============================================================  27  IMPACT 1
def s27_impact(prs, i, n):
    s = slide_new(prs)
    header(s, "Impact — time and money", "Where the 10–15 minutes comes back",
           "A conservative classroom arithmetic, using our own numbers and nothing else.")

    kpi(s, ML, 2.02, 2.86, 1.34, "105", "minutes per day per section (7 periods × 15 min)", CYAN, vsize=30)
    kpi(s, ML + 3.06, 2.02, 2.86, 1.34, "≈32", "teaching days recovered per year per section", GREEN, vsize=30)
    kpi(s, ML + 6.12, 2.02, 2.86, 1.34, "8", "sections served by one ₹1,500 terminal", AMBER, vsize=30)
    kpi(s, ML + 9.18, 2.02, 2.86, 1.34, "256", "teaching days returned across those sections", MAGENTA, vsize=30)

    text(s, ML, 3.62, CW, 0.26, "The arithmetic, shown so it can be argued with", size=10,
         color=AMBER, bold=True, caps=True, spc=160)
    rows = [
        ["Step", "Calculation", "Result"],
        ["Time lost per section per day", "7 periods × 15 min of manual roll call", "105 min"],
        ["Teaching days lost per section per year", "105 min × 220 school days ÷ 720 min in a teaching day", "≈32 days"],
        ["One terminal, rotating sections", "8 sections × 32 days", "256 teaching days"],
        ["Hardware cost", "₹1,500 one time, plus ₹200 of filament per replacement shell", "₹0 recurring"],
        ["Parent notification", "was month-end or never; is 09:15 the same day", "same-day"],
    ]
    table(s, ML, 3.90, 8.20, [2.62, 3.86, 1.72], rows, size=9.4, head_size=8.8, row_h=0.50,
          first_bold=True, colors={2: GREEN})

    rect(s, ML + 8.56, 3.90, 3.54, 2.50, fill=PANEL, line=LINE, lw=0.75, radius=0.04)
    text(s, ML + 8.78, 4.06, 3.1, 0.24, "WHAT WE DO NOT CLAIM", size=9, color=RED, bold=True, spc=160)
    bullets(s, ML + 8.78, 4.36, 3.1, 1.9, [
        "all 15 minutes is recoverable — a card tap still takes 2 s per student",
        "the teacher is not replaced by the box",
        "the pilot school result is not yet measured",
    ], size=9, gap=0.08, marker="\u2715", mcolor=RED, line=1.24)

    rect(s, ML, 6.44, 8.20, 0.46, fill=PANEL2, line=LINE, lw=0.7, radius=0.06)
    text(s, ML + 0.22, 6.55, 7.8, 0.26,
         "Even at a third of that recovery the terminal pays for itself in teaching time inside one term.",
         size=9, color=SOFT)

    footer(s, i, n, "Impact — deck arithmetic from README.md figures")
    notes(s, """
Show the arithmetic, then point at the red box. Juries reward a team that bounds its own claim.

If pushed: "the honest statement is two to four minutes per period is recoverable, not fifteen.
Even that is 8 to 16 teaching days per section per year."
""")
    return s


# =============================================================  28  IMPACT 2
def s28_impact2(prs, i, n):
    s = slide_new(prs)
    header(s, "Impact — beyond the register", "What else becomes possible once attendance is data",
           "The terminal is the cheapest way to get one reliable fact per student per period. "
           "Everything here is a consequence of having that fact.")

    cards = [
        ("Early-warning for dropouts", "Three consecutive absences is the earliest reliable signal a "
         "school has. A record that writes itself can flag it the same week.", GREEN),
        ("Teacher's own workload", "The monthly return is generated, not re-keyed. That is hours per "
         "teacher per term, and it is the complaint we heard most.", CYAN),
        ("Mid-day meal planning", "Head-count at 09:15 rather than at the counter. Less waste, and a "
         "number the kitchen can act on.", AMBER),
        ("Honest report cards", "Attendance becomes a per-period fact instead of a monthly guess, so "
         "the report card and the register finally agree.", MAGENTA),
        ("A platform, not a product", "The same box with a different sensor is a lab-equipment register, "
         "a library ledger, a staff muster roll.", ORANGE),
        ("Local manufacture", "Every part is printable in Renukoot. Replacing one is a filament spool, "
         "not a purchase order.", RED),
    ]
    x0, y0, w, h = ML, 1.98, 3.86, 1.78
    for k, (head, body, col) in enumerate(cards):
        x = x0 + (k % 3) * (w + 0.20)
        y = y0 + (k // 3) * (h + 0.14)
        rect(s, x, y, w, h, fill=PANEL, line=LINE, lw=0.75, radius=0.04)
        rect(s, x, y, 0.04, h, fill=col)
        text(s, x + 0.24, y + 0.18, w - 0.44, 0.44, head, size=11, color=col, bold=True, line=1.1)
        text(s, x + 0.24, y + 0.66, w - 0.44, h - 0.78, body, size=9.0, color=DIM, line=1.26)

    rect(s, ML, 5.94, CW, 1.00, fill=PANEL2, line=LINE, lw=0.75, radius=0.05)
    rect(s, ML, 5.94, 0.05, 1.00, fill=CYAN)
    text(s, ML + 0.26, 6.04, CW - 0.5, 0.22, "THE SCALE ARGUMENT", size=8.8, color=CYAN, bold=True, spc=160)
    text(s, ML + 0.26, 6.28, CW - 0.52, 0.58,
         "There are over 15 lakh schools in India. What lets this reach them is not cleverness — it is that it costs "
         "₹1,500, prints locally, needs no technician and runs with the internet down. A ₹40,000 terminal with an "
         "annual licence cannot cross that gap.", size=8.9, color=SOFT, line=1.26)

    footer(s, i, n, "Impact — README.md; team interviews")
    notes(s, """
Do not oversell. Pick two cards and explain them properly: the early-warning signal and the
teacher's monthly return. Those are the two teachers actually asked for.
""")
    return s


# =============================================================  29  RESULTS
def s29_results(prs, i, n):
    s = slide_new(prs)
    header(s, "Evidence", "The scoreboard — every line has a file behind it")

    rows = [
        ["What is claimed", "Measured by", "Result", "File"],
        ["The shell is one watertight solid", "build_v3.py, from triangles", "11,108 tris, 1 body, 0 open edges", "v3_audit.txt"],
        ["The RFID window is genuinely open", "8,269 rays through the aperture", "0 blocked", "v3_audit.txt"],
        ["Nothing printed is in front of the coil", "boolean volume of the keep-out", "0.00 mm³", "v3_audit.txt"],
        ["The box is dry and closed", "plate sliced at mid-thickness", "exactly 6 voids = 4 screws + 2 keyhole slots", "v3_independent_verify.txt"],
        ["Every rebate and lip is as designed", "0.02 mm probe walk", "34 / 34 values within 0.035 mm", "v3_groove_check.txt"],
        ["Every documented screw can seat", "ray down 22 pilot axes", "all 22 pass, exit code 0", "v3_hole_probe.txt"],
        ["Holes cannot crack the corners", "plastic between cone and outline", "min 2.25 mm (v3.0: 0.08 mm)", "v3_physics_audit.txt §8"],
        ["The parts print where we say", "214 slicer layers", "0 self-intersections, 0 empty layers", "v3_physics_audit.txt §9"],
        ["The docs match the mesh", "text re-read and compared", "no stale claims", "v3_physics_audit.txt §10"],
        ["The .blend is the parts it says it is", "volumes from its own polygons", "172.22 cm³ total, 110.00 × 155.00 × 46.00", "v3_blend_check.txt"],
    ]
    table(s, ML, 1.98, CW, [3.32, 3.06, 3.98, 1.73], rows, size=8.6, head_size=8.6,
          row_h=0.455, first_bold=False, colors={3: GREEN})

    footer(s, i, n, "Scoreboard — docs/*.txt, each regenerated by a program in tools/")
    notes(s, """
This is the slide to leave on screen while the jury asks questions. Every row is a claim we can
defend by running a command.

Pick two rows to talk about: the 8,269 rays (because it is vivid) and the 34 groove values
(because it proves the plastic is where it was told to be, not merely where it was designed).
""")
    return s


# =============================================================  30  HONESTY
def s30_honesty(prs, i, n):
    s = slide_new(prs)
    header(s, "Honest limitations", "What is not closed yet",
           "The repository's own audit file lists these as open items, so the deck does too. "
           "A claim list without a limitation list is a sales pitch, not engineering.")

    rows = [
        ["Open item", "Status", "How it is handled", "Owner"],
        ["ESP32 pad-hole diameter", "unpublished", "M2.2 or M2 both pass the Ø1.8 pilot; decides nothing geometric", "vendor data"],
        ["RC522 corner-hole pitch", "deliberately unused", "the ring clamps the board edges, so any brand fits", "by design"],
        ["R307 mounting holes", "do not exist", "the bracket clamps the housing, exactly as stock kits do", "by design"],
        ["Pressure drop across the plate seam", "assumed", "recorded as a NOTE in the audit, never as a gate", "print-dependent"],
        ["Field trial in a real classroom", "not yet run", "pilot planned; impact numbers are arithmetic, not measured", "next phase"],
        ["PLA on an unshaded external wall", "out of spec", "print in PETG — no geometry change needed", "material advice"],
    ]
    table(s, ML, 2.02, CW, [3.10, 1.70, 5.60, 1.69], rows, size=9, head_size=8.6,
          row_h=0.54, first_bold=True, colors={2: ORANGE})

    rect(s, ML, 5.94, CW, 0.94, fill=PANEL2, line=LINE, lw=0.75, radius=0.05)
    rect(s, ML, 5.94, 0.05, 0.94, fill=AMBER)
    text(s, ML + 0.26, 6.04, CW - 0.5, 0.24, "THE RULE WE WORKED BY", size=9, color=AMBER,
         bold=True, spc=160)
    text(s, ML + 0.26, 6.32, CW - 0.5, 0.44,
         "Never write PASS unless a check produced that PASS. Where a value is unknown, write VERIFY_ACTUAL_HARDWARE "
         "and say so. It is in the master prompt as a non-negotiable rule, and it is the reason this deck can show a "
         "limitations slide at all.", size=9.6, color=SOFT, line=1.28)

    footer(s, i, n, "Limitations — master_prompt §3, §4 · v3_design_notes.md §5, §10")
    notes(s, """
Open this slide before the jury asks the hard question. Say: "here is what is not closed, and
here is how each one is contained."

The rule at the bottom is from §3 of our own brief. Quoting your own constraint document is a
strong move - it shows the discipline was chosen, not improvised.
""")
    return s


# =============================================================  31  REPRODUCE
def s31_reproduce(prs, i, n):
    s = slide_new(prs)
    header(s, "Reproducibility", "Anyone can rebuild this in about a minute",
           "Pinned dependencies, one command per stage, and a SHA-256 manifest that proves the "
           "bytes in the pack are the bytes the checks passed.")

    code = [
        ("# 1  environment", DIM),
        ("python3 -m venv .venv", SOFT),
        (".venv/bin/pip install -r tools/requirements_v3.txt", SOFT),
        ("", None),
        ("# 2  rebuild the geometry + run the parametric audit", DIM),
        (".venv/bin/python tools/build_v3.py            # RESULT: ALL CHECKS PASS", GREEN),
        ("", None),
        ("# 3  verify the STLs alone (does not import the builder)", DIM),
        (".venv/bin/python tools/verify_v3.py           # INDEPENDENT RESULT: ALL CHECKS PASS", GREEN),
        ("", None),
        ("# 4  the physics, the grooves and the screw depths", DIM),
        (".venv/bin/python tools/audit_physics_v3.py    # PHYSICS RESULT: no failures", GREEN),
        (".venv/bin/python tools/check_grooves_v3.py    # EVERY GROOVE AND FIT MEASURES AS DESIGNED", GREEN),
        (".venv/bin/python tools/hole_probe_v3.py       # gate: non-zero exit if a screw cannot seat", GREEN),
        ("", None),
        ("# 5  rebuild the pack and the .blend", DIM),
        (".venv/bin/python tools/make_pack_v3.py && .venv/bin/python tools/make_blend_v3.py", SOFT),
    ]
    rect(s, ML, 1.98, 7.34, 4.42, fill=RGBColor(0x0A, 0x0C, 0x10), line=LINE, lw=0.75, radius=0.03)
    box = tb(s, ML + 0.24, 2.14, 6.9, 4.1)
    for k, (ln, col) in enumerate(code):
        para(box.text_frame, ln if ln else " ", size=8.1, color=col or DIM, font=MONO,
             first=(k == 0), line=1.20)

    text(s, ML + 7.68, 1.98, 4.4, 0.26, "Pinned, so it rebuilds the same", size=10, color=AMBER,
         bold=True, caps=True, spc=160)
    rows = [
        ["Package", "Pin"],
        ["numpy", "2.4.6"],
        ["trimesh", "5.1.1"],
        ["manifold3d", "3.5.4"],
        ["mapbox-earcut", "2.1.0"],
        ["shapely", "2.2.0"],
        ["scipy / matplotlib", "1.17.1 / 3.11.2"],
        ["bpy (optional)", "4.5.14"],
    ]
    table(s, ML + 7.68, 2.26, 4.40, [2.40, 2.00], rows, size=9, head_size=8.6, row_h=0.38,
          first_bold=True)

    rect(s, ML + 7.68, 5.36, 4.40, 1.14, fill=PANEL2, line=LINE, lw=0.75, radius=0.05)
    text(s, ML + 7.88, 5.46, 4.0, 0.22, "AND IT REPRODUCES EXACTLY", size=8.8, color=GREEN,
         bold=True, spc=160)
    text(s, ML + 7.88, 5.70, 4.02, 0.72, "A from-scratch rebuild with these pins reproduces 3 of the 4 STLs "
         "byte-for-byte, and the shell as the same solid — same volume, same area.",
         size=8.2, color=SOFT, line=1.22)

    rect(s, ML, 6.56, CW, 0.38, fill=PANEL, line=LINE, lw=0.7, radius=0.06)
    text(s, ML + 0.22, 6.64, CW - 0.4, 0.24,
         "exports/SHA256SUMS_v3.txt lists a hash for every file in the pack, so a download can be proved against the build that passed.",
         size=8.6, color=SOFT)

    footer(s, i, n, "Reproducibility — tools/requirements_v3.txt · exports/SHA256SUMS_v3.txt")
    notes(s, """
Offer the command. If the jury has a laptop with python, this is runnable in front of them.

The byte-for-byte line matters: it says the build is deterministic apart from a known
triangulation-diagonal flip, which the requirements file names explicitly.
""")
    return s


# =============================================================  32  FAILURE
def s32_failure(prs, i, n):
    s = slide_new(prs)
    header(s, "Failure analysis", "Three defects the checks caught — and one they missed",
           "The most useful part of this project is the list of things that were wrong. Each one "
           "changed a design rule permanently.")

    items = [
        ("F11", "A rear-plate countersink opened onto a corner round", "medium",
         "The Ø6.6 mm 90° cone was 0.08 mm from the R3 corner, so the screw head had a hole to fall into. "
         "Fixed by moving all four screws 3.5 mm inboard — plastic at the corners went from 0.08 to 2.25 mm.",
         "New rule: an audit must measure plastic between a cone and the outline, not just the hole.", ORANGE),
        ("F12", "The rear plate had a 15.6 × 63 mm hole through it", "high",
         "A cut meant only to clear the ESP32's bosses ran through the whole 3 mm skin instead of the 2 mm "
         "frame. The shipped plate was open to dust. Fixed by stopping the cut at the frame's own top surface.",
         "New rule: slice the plate at mid-thickness and demand exactly 6 voids.", RED),
        ("F13", "The RFID reader could not be installed at all", "high",
         "Laid landscape, the 60 mm board needed a 58.35 mm bay. It could not go in in any orientation, and "
         "no build order fixes plastic printed into the wall. Fixed by mounting it portrait.",
         "New rule: sweep every part's real path, do not look at a drawing.", MAGENTA),
        ("v1", "The reader could not scan — the defect that started v2", "high",
         "A closed 3 mm pocket floor over the antenna blocked the field. Everything looked right, and nothing "
         "worked. This is the defect that produced the ray-cast aperture proof.",
         "New rule: a scan window is proved by rays through it, never by a picture of it.", RED),
    ]
    y = 1.98
    for fid, head, sev, body, rule, col in items:
        rect(s, ML, y, CW, 1.18, fill=PANEL, line=LINE, lw=0.75, radius=0.03)
        rect(s, ML, y, 0.05, 1.18, fill=col)
        text(s, ML + 0.24, y + 0.14, 0.7, 0.24, fid, size=11, color=col, bold=True)
        text(s, ML + 0.98, y + 0.13, 5.9, 0.26, head, size=10.5, color=WHITE, bold=True)
        text(s, ML + 0.98, y + 0.42, 5.9, 0.68, body, size=8.6, color=DIM, line=1.24)
        pill(s, ML + 7.06, y + 0.14, 0.86, 0.24, sev, fill=PANEL3, color=col, size=7.4)
        text(s, ML + 8.12, y + 0.14, 3.9, 0.22, "THE RULE IT CREATED", size=7.6, color=col,
             bold=True, spc=140)
        text(s, ML + 8.12, y + 0.40, 3.9, 0.70, rule, size=8.6, color=SOFT, line=1.24)
        y += 1.26

    footer(s, i, n, "Defects — v3_design_notes.md §6, §8 · master_prompt status header")
    notes(s, """
This is the strongest slide for a technical jury and the weakest for a nervous one. Choose it
deliberately.

Say: "we are showing you our bugs because every one of them turned into a permanent check. F13
in particular is embarrassing - the reader physically could not go in - and that is exactly why
section 3 of the physics audit exists."
""")
    return s


# =============================================================  33  TEAM
def s33_team(prs, i, n):
    s = slide_new(prs)
    header(s, "Team", "Five people, five parts of the same box",
           "Class 9, The Aditya Birla Public School, Renukoot — with a mentor who made us prove "
           "every number.")

    members = [
        ("Shaurya Gupta", "Team lead · firmware & cloud", CYAN,
         "ESP32 firmware, Astro AI, Firebase schema, the web dashboards."),
        ("Anant Tiwari", "Ideation & user research", GREEN,
         "The problem interviews with teachers and parents, and the offline-first requirement."),
        ("Tejash Upadhyaye", "Hardware integration", AMBER,
         "Wiring, bus assignment, power budget and every bench test that produced a failure row."),
        ("Diwakar Singh", "Product design & 3D", MAGENTA,
         "The enclosure programme: parametric CAD, the four checkers, print validation."),
        ("Devansh Dakard", "Testing & documentation", ORANGE,
         "The audit trail, the print order, the pack and this deck's evidence chain."),
    ]
    x, w = ML, 2.26
    for name, role, col, body in members:
        rect(s, x, 2.02, w, 2.70, fill=PANEL, line=LINE, lw=0.75, radius=0.04)
        rect(s, x, 2.02, w, 0.045, fill=col)
        initials = "".join(p[0] for p in name.split()[:2])
        rect(s, x + 0.24, 2.28, 0.52, 0.52, fill=PANEL3, line=col, lw=1.0, radius=0.5,
             shape=MSO_SHAPE.OVAL)
        text(s, x + 0.24, 2.40, 0.52, 0.26, initials, size=12, color=col, bold=True,
             align=PP_ALIGN.CENTER)
        text(s, x + 0.24, 2.96, w - 0.44, 0.44, name, size=11.5, color=WHITE, bold=True, line=1.1)
        text(s, x + 0.24, 3.42, w - 0.44, 0.44, role, size=8.4, color=col, bold=True, line=1.2)
        text(s, x + 0.24, 3.90, w - 0.44, 0.74, body, size=8.3, color=DIM, line=1.22)
        x += w + 0.14

    rect(s, ML, 4.90, 6.0, 2.00, fill=PANEL2, line=LINE, lw=0.75, radius=0.05)
    text(s, ML + 0.26, 5.10, 5.5, 0.24, "MENTOR", size=9, color=AMBER, bold=True, spc=160)
    text(s, ML + 0.26, 5.38, 5.5, 0.30, "Dr. Jayesh Shinde", size=14, color=WHITE, bold=True)
    text(s, ML + 0.26, 5.72, 5.5, 0.28, "The Aditya Birla Public School, Renukoot", size=9, color=DIM)
    text(s, ML + 0.26, 5.98, 5.5, 0.86, "The standing instruction that shaped this project: no claim "
         "without a measurement, and no PASS that a program did not produce.", size=9, color=SOFT, line=1.26)

    rect(s, ML + 6.24, 4.90, 5.86, 2.00, fill=PANEL, line=LINE, lw=0.75, radius=0.04)
    text(s, ML + 6.48, 5.10, 5.4, 0.24, "HOW THE WORK WAS SPLIT", size=9, color=CYAN, bold=True, spc=160)
    text(s, ML + 6.48, 5.38, 5.4, 1.36,
         "Every member owns a deliverable that is checked by someone else — firmware by the hardware "
         "owner, CAD by the testing owner, documentation by all five. Nothing in the pack was signed "
         "off by the person who made it.", size=9.4, color=SOFT, line=1.30)

    footer(s, i, n, "Team — README.md")
    notes(s, """
Teamwork is 20 of the 100 League points, so do not skip this. Name each person and the thing
they own. Then say the cross-check sentence - it is what 'collaboration' looks like in practice.
""")
    return s


# =============================================================  34  ROADMAP
def s34_roadmap(prs, i, n):
    s = slide_new(prs)
    header(s, "Next", "What a pilot term would actually test",
           "Five questions that cannot be answered in a workshop, in the order a school would "
           "need them answered.")

    rows = [
        ["#", "Question for the pilot", "How it is measured", "Pass criterion"],
        ["1", "Does a whole class clear the door in under two minutes?", "Time 40 students, 20 school days, with the teacher timing", "≤ 3 min at the 95th percentile"],
        ["2", "What is the real false-reject rate on growing fingers?", "Every reject logged with reason and retried within 10 s", "< 2 % of scans needing a retry"],
        ["3", "How many days a term run with no internet at all?", "Sync backlog and recovery on the dashboard", "zero lost records, all reconciled"],
        ["4", "Does the PLA survive one full summer on a west wall?", "Surface thermocouple plus a monthly fit check", "no sag, plate still closes by hand"],
        ["5", "Do parents read the alerts?", "Open and click rate on the digest", "≥ 50 % open within 24 h"],
    ]
    table(s, ML, 1.98, CW, [0.42, 4.28, 4.10, 3.29], rows, size=9.2, head_size=8.6,
          row_h=0.62, first_bold=True)

    rect(s, ML, 5.42, 5.90, 1.46, fill=PANEL, line=LINE, lw=0.75, radius=0.04)
    text(s, ML + 0.24, 5.56, 5.4, 0.24, "SHIPPED TODAY", size=9, color=GREEN, bold=True, spc=160)
    bullets(s, ML + 0.24, 5.84, 5.4, 0.94, [
        "working prototype, 140/140 feature tests",
        "four print files and a verified assembly model",
        "a cloud dashboard with three roles live",
    ], size=8.8, gap=0.04, marker="\u2713", mcolor=GREEN, line=1.2)

    rect(s, ML + 6.16, 5.42, 5.94, 1.46, fill=PANEL, line=LINE, lw=0.75, radius=0.04)
    text(s, ML + 6.40, 5.56, 5.4, 0.24, "NEEDED TO REACH A SECOND SCHOOL", size=9, color=AMBER,
         bold=True, spc=160)
    bullets(s, ML + 6.40, 5.84, 5.4, 0.94, [
        "a provisioning flow a teacher can run unaided",
        "SMS fallback for guardians without email",
        "a district deployment guide with the SQL export",
    ], size=8.8, gap=0.04, marker="\u25aa", mcolor=AMBER, line=1.2)

    footer(s, i, n, "Pilot plan — deck 27, 28 and 30 turned into pass criteria")
    notes(s, """
Every pilot question has a pass criterion with a number, which is what makes it a pilot and not
a wish. If the jury asks 'what next', read row 1 and row 3.
""")
    return s


# =============================================================  35  APPENDIX PINS
def s35_pins(prs, i, n):
    s = slide_new(prs)
    header(s, "Appendix A", "Pin-out and power budget")

    rows = [
        ["Signal", "ESP32 pin", "Module", "Notes"],
        ["SPI SCK", "GPIO 18", "RC522", "VSPI, 4–10 MHz, 3.3 V"],
        ["SPI MISO", "GPIO 19", "RC522", "3.3 V logic, no level shifter"],
        ["SPI MOSI", "GPIO 23", "RC522", "—"],
        ["SPI SS", "GPIO 5", "RC522", "software chip-select"],
        ["RST", "GPIO 27", "RC522", "also used by Astro AI to recover"],
        ["UART2 TX", "GPIO 17", "R307", "57600 baud, 3.3 V"],
        ["UART2 RX", "GPIO 16", "R307", "—"],
        ["I²C SDA", "GPIO 21", "LCD1602 backpack", "address 0x27 or 0x3F, probed at boot"],
        ["I²C SCL", "GPIO 22", "LCD1602 backpack", "shared-bus recovery in Astro AI"],
        ["Buzzer", "GPIO 25", "buzzer", "confirm tone, PWM"],
        ["Fan", "3V3 + MOSFET", "3010 fan", "continuous, ~0.1 W"],
    ]
    table(s, ML, 1.98, 7.54, [1.42, 1.66, 1.90, 2.56], rows, size=8.8, head_size=8.4,
          row_h=0.352, first_bold=True)

    text(s, ML + 7.88, 1.98, 4.2, 0.26, "POWER", size=10, color=AMBER, bold=True, spc=160)
    rows2 = [
        ["Rail", "Load", "Note"],
        ["3.3 V logic", "≈ 26 mA", "RC522, idle"],
        ["3.3 V logic", "peak ≈ 120 mA", "RC522 field on + ESP32 TX"],
        ["R307", "≈ 60 mA / 120 mA", "idle / capture"],
        ["LCD + backpack", "≈ 20 mA", "backlight on"],
        ["3010 fan", "≈ 30 mA", "continuous"],
    ]
    table(s, ML + 7.88, 2.26, 4.22, [1.52, 1.24, 1.46], rows2, size=8.6, head_size=8.2,
          row_h=0.44, first_bold=True)

    rect(s, ML + 7.88, 4.98, 4.22, 1.90, fill=PANEL2, line=LINE, lw=0.75, radius=0.05)
    text(s, ML + 8.10, 5.12, 3.8, 0.24, "WHY THE RAIL MATTERS", size=9, color=AMBER, bold=True, spc=160)
    text(s, ML + 8.10, 5.40, 3.8, 1.36,
         "Peak draw is about 300 mA with the field on and the sensor capturing, so a 5 V 1 A supply "
         "into the DevKit's regulator is enough with headroom. The enclosure's USB slot is the only "
         "cable opening on the box — 20.4 × 12.4 mm, sized around a real plug body plus 1.2 mm all round.",
         size=8.8, color=SOFT, line=1.26)

    rect(s, ML, 6.44, 7.54, 0.46, fill=PANEL, line=LINE, lw=0.7, radius=0.06)
    text(s, ML + 0.20, 6.55, 7.3, 0.26,
         "No pin is used twice: SPI, UART2, I2C, buzzer and fan each own their lines.",
         size=8.6, color=SOFT)

    footer(s, i, n, "Appendix A — wiring and power")
    notes(s, "Reference slide. Use it only if a jury member asks how it is wired or what it draws.")
    return s


# =============================================================  36  APPENDIX DATA
def s36_data(prs, i, n):
    s = slide_new(prs)
    header(s, "Appendix B", "The numbers, in one place",
           "Every figure quoted in this deck, with the audit section that produced it.")

    rows = [
        ["Quantity", "Value", "Source"],
        ["Outer size", "110.00 × 155.00 × 46.00 mm", "physics audit §10"],
        ["Shell volume / triangles", "115.2 cm³ / 11,108 tris", "v3_audit.txt, verify_v3.py"],
        ["All four parts", "172.2 cm³ CAD → 159 g printed", "physics audit §9"],
        ["RFID aperture", "38.00 × 56.00, 0 of 8,269 rays blocked", "audit §K, physics §6"],
        ["Fan bore", "Ø28.00 mm, 615 mm², the only air opening", "physics §4"],
        ["LCD window / rebate", "66.00 × 17.50 / 72.00 × 23.53 × 0.45", "groove check"],
        ["R307 window / relief", "19.3 × 21.2 in a 25.3 × 27.2 rebate", "groove check"],
        ["Register lip", "104.305 × 148.503 in 104.785 × 148.982", "groove check"],
        ["Pilots", "22 holes Ø1.78–2.50, thinnest skin 1.40 mm", "hole probe"],
        ["Pull-out reserve", "213× to 2,458× on every joint", "physics audit §1"],
        ["ΔT at 1.6 W", "1.8 K combined (ceiling 12 K)", "physics audit §4"],
        ["13.56 MHz loss in 2.20 mm PLA", "0.0001 dB", "physics audit §6"],
        ["Supports needed", "none; 0.30 % of faces over 60°", "physics audit §9"],
        ["Print from one 1 kg spool", "6.3 sets", "physics audit §9"],
    ]
    table(s, ML, 1.94, CW, [3.34, 6.09, 2.66], rows, size=8.8, head_size=8.6, row_h=0.330,
          first_bold=True, colors={1: CYAN})

    footer(s, i, n, "Appendix B — traceability table")
    notes(s, "The reference page. Every number here can be re-derived by running one of the five programs in tools/.")
    return s


# =============================================================  37  APPENDIX FILES
def s37_files(prs, i, n):
    s = slide_new(prs)
    header(s, "Appendix C", "Where every file lives",
           "The repository is organised so that a stranger can rebuild the product, not just read "
           "about it.")

    cols = [
        ("docs/", CYAN, [
            ("master_prompt.md", "the consolidated engineering brief, §1–26"),
            ("v3_design_notes.md", "the measured design history, v3 → v3.6"),
            ("v3_audit.txt", "parametric audit A–K"),
            ("v3_independent_verify.txt", "STL-only verification"),
            ("v3_physics_audit.txt", "10 sections of physics"),
            ("v3_groove_check.txt", "34 probed fits"),
            ("v3_hole_probe.txt", "22 screw depths"),
            ("v3_blend_build / check.txt", "the .blend and its verification"),
        ]),
        ("tools/", GREEN, [
            ("build_v3.py", "the generator; every dimension is a parameter"),
            ("verify_v3.py", "independent STL checker"),
            ("audit_physics_v3.py", "10-section physics audit"),
            ("check_grooves_v3.py", "0.02 mm probe walk"),
            ("hole_probe_v3.py", "screw-depth gate"),
            ("make_blend_v3.py", ".blend, .glb, Cycles frames"),
            ("make_pack_v3.py", "the shipping pack and SHA-256 list"),
            ("requirements_v3.txt", "every pin in the environment"),
        ]),
        ("cad/ · exports/ · renders/", AMBER, [
            ("cad/v3/*.stl", "the four print files, bed-aligned"),
            ("v2/ and v1/", "the two earlier generations"),
            ("exports/*.zip", "print pack, STL-only pack, full pack"),
            ("*.blend / *.glb", "editable 3D and web 3D"),
            ("viewer_offline.html", "single-file 3D viewer"),
            ("SHA256SUMS_v3.txt", "a hash for every shipped file"),
            ("renders/*.png", "drawing sheets, sections, exploded views"),
            ("presentation/", "this deck and the script that builds it"),
        ]),
    ]
    x, w = ML, 3.94
    for head, col, items in cols:
        rect(s, x, 1.98, w, 4.88, fill=PANEL, line=LINE, lw=0.75, radius=0.04)
        rect(s, x, 1.98, w, 0.045, fill=col)
        text(s, x + 0.24, 2.16, w - 0.44, 0.28, head, size=11, color=col, bold=True, font=MONO)
        y = 2.54
        for name, desc in items:
            text(s, x + 0.24, y, w - 0.44, 0.22, name, size=8.4, color=WHITE, bold=True, font=MONO)
            text(s, x + 0.24, y + 0.19, w - 0.44, 0.30, desc, size=7.8, color=DIM, line=1.15)
            y += 0.52
        x += w + 0.22

    footer(s, i, n, "Appendix C — repository map")
    notes(s, "Reference slide. Point at tools/ and say: this is the part you can run.")
    return s


# =============================================================  38  CLOSING
def s38_closing(prs, i, n):
    s = slide_new(prs)
    grid_texture(s, RGBColor(0x15, 0x18, 0x1F), 0.5)
    rect(s, 0, 0, 0.16, SH, fill=AMBER)

    text(s, ML + 0.42, 1.10, 7.4, 0.3, "IN ONE SENTENCE", size=10, color=AMBER, bold=True,
         caps=True, spc=220)
    text(s, ML + 0.42, 1.52, 7.6, 2.62,
         "A ₹1,500 box that marks\nattendance with a card or a\nthumb, works with the internet\ndown, and is proved before\nit is printed.",
         size=24, color=WHITE, bold=True, line=1.26)
    rect(s, ML + 0.44, 4.10, 1.5, 0.05, fill=CYAN)

    stats = [("140/140", "feature tests", CYAN), ("4", "independent checkers", GREEN),
             ("0", "supports needed", AMBER), ("159 g", "of printed plastic", MAGENTA)]
    x = ML + 0.42
    for val, lab, col in stats:
        text(s, x, 4.48, 1.86, 0.36, val, size=17, color=col, bold=True)
        text(s, x, 4.86, 1.86, 0.44, lab, size=8.4, color=DIM, caps=True, spc=100, line=1.2)
        x += 1.92

    text(s, ML + 0.42, 5.66, 7.4, 0.9,
         "Team Sun Rises India  ·  Class 9  ·  The Aditya Birla Public School, Renukoot\n"
         "Mentor: Dr. Jayesh Shinde  ·  Sonbhadra, Uttar Pradesh, India",
         size=9.5, color=FAINT, line=1.5)

    fig_light(s, A("front"), 8.92, 1.52, 3.72, 3.94)
    text(s, 8.92, 5.56, 3.72, 0.5, "Front face, v3.6: LCD window, R307 optical\nwindow, 100 % open RFID aperture",
         size=8.4, color=DIM, line=1.3, align=PP_ALIGN.CENTER)

    footer(s, i, n, "Thank you — questions")
    notes(s, """
Close on the sentence, not the specs. Then stop talking and let them ask.

If a jury member asks 'what are you most proud of', the answer is on slide 32: the list of things
that were wrong. That answer is hard to fake and it is true.
""")
    return s


# =============================================================  03b  TECH STACK
def s03b_techstack(prs, i, n):
    s = slide_new(prs)
    header(s, "Technology inventory", "Every technology in the product, and what it is for",
           "Six columns, grouped by layer. Nothing on this slide is decoration — each entry is a "
           "decision, and the slide after each one explains why.")

    groups = [
        ("HARDWARE", CYAN, [
            ("ESP32 DevKit V1", "compute + Wi-Fi"),
            ("RC522 13.56 MHz", "card identity"),
            ("R307 optical", "finger identity"),
            ("LCD1602 + I²C", "student feedback"),
            ("3010 fan", "air + demisting"),
            ("PLA / PETG", "the body"),
        ]),
        ("BUSES & PINS", GREEN, [
            ("SPI (VSPI)", "reader"),
            ("UART2", "fingerprint"),
            ("I²C", "display"),
            ("LittleFS", "offline queue"),
            ("NTP + RTC", "period timing"),
            ("OTA partitions", "field updates"),
        ]),
        ("FIRMWARE", AMBER, [
            ("Arduino C++", "sketches on ESP32"),
            ("Astro AI 2.0", "11 self-checks"),
            ("Task watchdog", "per-task recovery"),
            ("Brown-out detect", "safe writes"),
            ("FreeRTOS tasks", "scan ∥ sync"),
            ("Exponential backoff", "sync retry"),
        ]),
        ("CLOUD", ORANGE, [
            ("Firebase Auth", "three roles"),
            ("Realtime Database", "attendance tree"),
            ("Security rules", "server-side access"),
            ("Firebase Hosting", "dashboards + CDN"),
            ("Email alerts", "guardian digest"),
        ]),
        ("CAD PIPELINE", MAGENTA, [
            ("Python + numpy", "the generator"),
            ("trimesh", "mesh + watertight"),
            ("manifold3d", "exact booleans"),
            ("shapely", "2-D cut profiles"),
            ("Blender 4.5 LTS", "assembly + renders"),
            ("glTF / .glb", "web 3D"),
        ]),
        ("VERIFICATION", RED, [
            ("Ray casting", "aperture + keep-outs"),
            ("0.02 mm probing", "every rebate and lip"),
            ("Envelope sweep", "installability"),
            ("Slicer simulation", "layer reality"),
            ("SHA-256 manifest", "pack integrity"),
            ("Canvas 2D viewer", "review in a browser"),
        ]),
    ]
    x, w, gap = ML, 1.86, 0.13
    for gi, (head, col, items) in enumerate(groups):
        rect(s, x, 1.98, w, 4.52, fill=PANEL, line=LINE, lw=0.75, radius=0.04)
        rect(s, x, 1.98, w, 0.035, fill=col)
        text(s, x + 0.14, 2.12, w - 0.28, 0.22, head, size=8.2, color=col, bold=True, spc=120)
        y = 2.44
        for name, use in items:
            text(s, x + 0.14, y, w - 0.26, 0.20, name, size=8.2, color=WHITE, bold=True, line=1.1)
            text(s, x + 0.14, y + 0.20, w - 0.26, 0.20, use, size=7.4, color=DIM, line=1.1)
            y += 0.66
        x += w + gap

    rect(s, ML, 6.62, CW, 0.36, fill=PANEL2, line=LINE, lw=0.7, radius=0.06)
    text(s, ML + 0.20, 6.70, CW - 0.4, 0.22,
         "36 technologies across six layers — and the rest of this deck takes each layer apart, with the measurement that justified it.",
         size=8.8, color=SOFT)

    footer(s, i, n, "Technology inventory — README.md, tools/, cad/, exports/")
    notes(s, """
Use this as the map. Do not read it out: say "six layers, thirty-six technologies, and from
here on the deck takes each layer apart."

If a jury member asks "what did you actually learn", pick one entry from each column and
explain the trade-off. That is the slide's purpose - it makes the breadth visible in one glance.
""")
    return s
