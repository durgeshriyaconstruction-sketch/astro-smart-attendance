#!/usr/bin/env python3
"""Edit ASTRO.pptx IN PLACE (text-only) — fingerprint sensor + two-step verification.

Every edit replaces text inside an existing run, so all formatting, colors,
fonts, images and layout of the original design are preserved byte-for-byte.
"""
import copy, re
from pptx import Presentation
from pptx.oxml.ns import qn

SRC = "google_drive/ASTRO.pptx"
OUT = "ASTRO-updated.pptx"

prs = Presentation(SRC)
slides = list(prs.slides)


def walk(shapes):
    for sh in shapes:
        if sh.shape_type == 6:  # group
            yield from walk(sh.shapes)
        else:
            yield sh


def shape(slide_no, name):
    for sh in walk(slides[slide_no - 1].shapes):
        if sh.name == name:
            return sh
    raise AssertionError(f"slide {slide_no}: shape {name!r} not found")


def edit(slide_no, shape_name, para_i, run_i, old, new):
    p = shape(slide_no, shape_name).text_frame.paragraphs[para_i]
    r = p.runs[run_i]
    assert r.text == old, (slide_no, shape_name, para_i, run_i, repr(r.text))
    r.text = new
    print(f"  s{slide_no} {shape_name} p{para_i} r{run_i}: OK")


print("Applying fingerprint + two-step edits:")

# E1 — title subtitle
edit(1, "TextBox 5", 1, 0,
     "Proposed Offline-First Dual-Mode Classroom Attendance System",
     "Proposed Offline-First Dual-Mode Classroom Attendance System "
     "with Fingerprint + RFID Two-Step Verification")

# E2 — slide 4, first bullet body
edit(4, "TextBox 4", 0, 1,
     " Will pair optical templates and RFID cards with 16×2 LCD, LEDs, and buzzer.",
     " Will pair a fingerprint sensor (AS608/R307) and RFID cards with 16×2 LCD, LEDs, and buzzer.")

# E3 — slide 4, NEW bullet after the first one (copy keeps identical style)
sh = shape(4, "TextBox 4")
tf = sh.text_frame
p0 = tf.paragraphs[0]
new_p = copy.deepcopy(p0._p)
p0._p.addnext(new_p)
runs = new_p.findall(qn("a:r"))
assert len(runs) == 2, len(runs)
runs[0].find(qn("a:t")).text = "Two-step verification:"
runs[1].find(qn("a:t")).text = (" Fingerprint must match the tapped RFID card before a mark "
                                "is recorded—preventing proxy attendance.")
print("  s4 TextBox 4: new bullet inserted (identical style)")

# E4 — slide 5, step 2
edit(5, "TextBox 13", 0, 0,
     "Student will tap an RFID card or use the optical sensor.",
     "Student will tap an RFID card, then verify with a fingerprint scan (two-step match).")

# E5 — slide 5, step 3
edit(5, "TextBox 18", 0, 0,
     "Device will check ID, window, and duplicates; queue offline.",
     "Device will match fingerprint to card, check window and duplicates; queue offline.")

# E6 — slide 6, comparison table cell (row 1, last column)
tbl = shape(6, "Table 3").table
cell = tbl.cell(1, 4)
p = cell.text_frame.paragraphs[0]
assert cell.text == "Dual RFID + Optical", repr(cell.text)
p.runs[0].text = "Fingerprint + RFID (2-step)"
for r in p.runs[1:]:
    r.text = ""
print("  s6 Table 3 cell(1,4): OK")

# E7 — slide 6, differentiator line
edit(6, "TextBox 4", 0, 0,
     "Our proposed differentiator is combining dual-mode hardware, offline queueing, privacy, "
     "and teacher oversight—not claiming exclusivity.",
     "Our proposed differentiator is combining fingerprint + RFID two-step verification, "
     "offline queueing, privacy, and teacher oversight—not claiming exclusivity.")

# E8 — slide 7, sensor stack
edit(7, "TextBox 4", 1, 1,
     " AS608/R307 optical sensor, RC522 RFID, 16×2 LCD, LEDs, buzzer.",
     " AS608/R307 optical fingerprint sensor, RC522 RFID, 16×2 LCD, LEDs, buzzer.")

# E9 — slide 7, demo box
edit(7, "TextBox 7", 0, 0,
     "We plan to validate check-in, duplicate blocking, and offline sync "
     "using fictional IDs and demo cards only.",
     "We plan to validate two-step check-in, duplicate blocking, and offline sync "
     "using fictional IDs, demo cards, and test fingerprint templates only.")

# E10 — slide 8, integrity card title
edit(8, "TextBox 13", 0, 0,
     "Duplicate rejection",
     "Proxy & duplicate rejection")

# E11 — slide 8, integrity card body
edit(8, "TextBox 14", 0, 0,
     "Will confirm repeated card taps or scans in the same period are blocked.",
     "Will confirm fingerprints match their cards and repeated taps in the same period are blocked.")

# E12 — slide 8, edge cases body
edit(8, "TextBox 20", 0, 0,
     "Will verify flagging of late entries, unknown cards, and unmatched scans.",
     "Will verify flagging of late entries, unknown cards, and unmatched fingerprints.")

# E13 — slide 9, risk bullet
edit(9, "TextBox 6", 0, 1,
     " Lent cards or dusty fingers.",
     " Lent cards, spoofed prints, or dusty fingers.")

# E14 — slide 9, safeguard bullet
edit(9, "TextBox 10", 0, 0,
     "Dual-mode + review:",
     "Two-step match + review:")
edit(9, "TextBox 10", 0, 1,
     " Fallback + teacher sign-off.",
     " Fingerprint must match card + teacher sign-off.")

# E15 — slide 10, PoC step
edit(10, "TextBox 14", 0, 0,
     "Assemble a safe, low-voltage benchtop demo with fictional IDs.",
     "Assemble a safe, low-voltage benchtop demo with fingerprint + RFID "
     "two-step check-in and fictional IDs.")

prs.save(OUT)
print("Saved", OUT)

# ---------- safety scan: no claims of already-created work (incl. notes) ----------
bad_pat = re.compile(
    r"\b(already\b|we (?:have|'ve) (?:built|created|developed|implemented)|"
    r"working prototype|prototype (?:is|works)|we built|we created|we implemented|"
    r"completed development|successfully (?:built|tested|created)|is (?:fully )?functional)",
    re.I)
findings = []
for i, sl in enumerate(prs.slides, 1):
    for sh in walk(sl.shapes):
        texts = []
        if sh.has_text_frame:
            texts.append(sh.text_frame.text)
        if sh.has_table:
            texts += [c.text for r in sh.table.rows for c in r.cells]
        for t in texts:
            for m in bad_pat.finditer(t):
                findings.append((i, m.group(0)))
    if sl.has_notes_slide:
        for m in bad_pat.finditer(sl.notes_slide.notes_text_frame.text):
            findings.append((i, "NOTES: " + m.group(0)))
print("SAFETY SCAN — claims of completed work:", findings if findings else "NONE (all proposal tense)")
