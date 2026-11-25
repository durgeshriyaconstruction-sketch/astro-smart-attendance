#!/usr/bin/env python3
"""Build the Astro Smart Attendance concept proposal deck (10 slides).

Reproduces the Google Slides deck's exact text structure/format, with ONLY the
fingerprint sensor + two-step verification changes applied. Everything stays in
proposal tense ("proposed / planned / will") — nothing claims already-built work.
"""
import re
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

# ---------- palette (kept simple & consistent) ----------
NAVY = RGBColor(0x12, 0x31, 0x4F)
GOLD = RGBColor(0xE8, 0xA3, 0x3D)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GRAY = RGBColor(0x5B, 0x6B, 0x7B)
DARK = RGBColor(0x24, 0x33, 0x42)
CARD = RGBColor(0xF2, 0xF5, 0xF9)
LIGHT = RGBColor(0xD9, 0xE2, 0xEC)
FONT = "Calibri"

FOOTER = "ABPS RENUKOOT · ABG STEM QUEST 2026–27 · CONCEPT PROPOSAL · {n}"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]


def tb(slide, x, y, w, h, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    return tf


def para(tf, text, size, color, bold=False, italic=False, first=False,
         align=PP_ALIGN.LEFT, space_after=0, font=FONT):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align
    p.space_after = Pt(space_after)
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    r.font.color.rgb = color
    r.font.name = font
    return p


def rect(slide, x, y, w, h, fill, line=None):
    from pptx.enum.shapes import MSO_SHAPE
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(1)
    s.shadow.inherit = False
    return s


def footer(slide, n):
    rect(slide, 0.6, 7.02, 12.13, 0.012, LIGHT)
    tf = tb(slide, 0.6, 7.08, 12.13, 0.35)
    para(tf, FOOTER.format(n=n), 10, GRAY, first=True, align=PP_ALIGN.CENTER)


def head(slide, kicker, headline, subhead):
    """Standard content-slide header: kicker / headline / subhead."""
    rect(slide, 0.6, 0.55, 0.09, 0.62, GOLD)
    tf = tb(slide, 0.85, 0.5, 11.9, 0.45)
    para(tf, kicker, 13, GOLD, bold=True, first=True)
    tf = tb(slide, 0.85, 0.88, 11.9, 0.55)
    para(tf, headline, 26, NAVY, bold=True, first=True)
    tf = tb(slide, 0.85, 1.46, 11.9, 0.4)
    para(tf, subhead, 14, GRAY, italic=True, first=True)


def card(slide, x, y, w, h, label, title, body):
    rect(slide, x, y, w, h, CARD)
    rect(slide, x, y, 0.07, h, GOLD)
    tf = tb(slide, x + 0.22, y + 0.16, w - 0.4, h - 0.3)
    para(tf, label, 11.5, GOLD, bold=True, first=True, space_after=2)
    para(tf, title, 14, NAVY, bold=True, space_after=4)
    para(tf, body, 11.5, GRAY)


def bullets_block(slide, items, x=0.85, y=2.15, w=11.7):
    tf = tb(slide, x, y, w, 3.2)
    for i, (label, text) in enumerate(items):
        p = para(tf, "", 14, DARK, first=(i == 0), space_after=8)
        r = p.add_run(); r.text = "▪  " + label + ": "
        r.font.size = Pt(14); r.font.bold = True; r.font.color.rgb = NAVY; r.font.name = FONT
        r = p.add_run(); r.text = text
        r.font.size = Pt(14); r.font.color.rgb = DARK; r.font.name = FONT


def callout(slide, label, text, y=5.55):
    rect(slide, 0.85, y, 11.63, 0.95, NAVY)
    tf = tb(slide, 1.15, y + 0.14, 11.0, 0.7, anchor=MSO_ANCHOR.MIDDLE)
    para(tf, label, 13, GOLD, bold=True, first=True, space_after=2)
    para(tf, text, 12.5, WHITE)


# =========================================================
# SLIDE 1 — TITLE
# =========================================================
s = prs.slides.add_slide(BLANK)
bg = rect(s, 0, 0, 13.333, 7.5, NAVY)
rect(s, 0, 0, 13.333, 0.14, GOLD)
tf = tb(s, 1.0, 1.45, 11.3, 0.5)
para(tf, "ABG STEM QUEST 2026–27 · STAGE 2 CONCEPT PROPOSAL", 15, GOLD, bold=True, first=True)
tf = tb(s, 1.0, 2.1, 11.3, 1.1)
para(tf, "Astro Smart Attendance", 44, WHITE, bold=True, first=True)
tf = tb(s, 1.0, 3.15, 11.3, 0.9)
para(tf, "Proposed Offline-First Dual-Mode Classroom Attendance System "
         "with Fingerprint + RFID Two-Step Verification", 19, LIGHT, first=True)
tf = tb(s, 1.0, 4.35, 11.3, 1.2)
para(tf, "Team Sun Rises India · ABPS Renukoot · SDG 9: Innovation & Infrastructure",
     14.5, WHITE, first=True, space_after=6)
para(tf, "Captain: Shaurya Gupta · Anant Tiwari, Devansh Dhakad, Tejas Upadhyay, Diwakar Singh",
     13, LIGHT)
footer(s, 1)

# =========================================================
# SLIDE 2 — PROBLEM STATEMENT (unchanged text)
# =========================================================
s = prs.slides.add_slide(BLANK)
head(s, "PROBLEM STATEMENT", "The problem we are addressing",
     "Manual roll-call creates daily classroom friction, transfer errors, and proxy risks")
cw, gap, x0, cy, ch = 2.82, 0.18, 0.6, 2.3, 3.9
cards2 = [
    ("Efficiency", "Teaching minutes lost daily",
     "Calling roll verbally each period consumes valuable classroom instruction time."),
    ("Accuracy", "Recording & transfer errors",
     "Paper registers invite misread marks, tally errors, and slow manual digitization."),
    ("Integrity", "Proxy attendance risk",
     "Verbal roll-call in busy classrooms makes it hard to prevent proxy responses."),
    ("Focused Scope", "One observable workflow",
     "Our proposal targets daily classroom logging—not promising one device solves every school issue."),
]
for i, (l, t, b) in enumerate(cards2):
    card(s, x0 + i * (cw + gap), cy, cw, ch, l, t, b)
footer(s, 2)

# =========================================================
# SLIDE 3 — EXPECTED IMPACT & BENEFICIARIES (unchanged text)
# =========================================================
s = prs.slides.add_slide(BLANK)
head(s, "EXPECTED IMPACT & BENEFICIARIES", "Why this problem matters",
     "Aimed at faster roll-call and fewer errors with teacher oversight")
items3 = [
    ("SDG 9 School Infrastructure", "Affordable, offline-capable classroom tools designed for real schools."),
    ("Primary users — Teachers:", "Intended to speed up roll-call with instant exception flags and final sign-off."),
    ("Beneficiaries — Students & parents:", "Aims to protect instructional time and support accurate, transparent records."),
    ("Maintainers — School IT & admin:", "Envisioned with modular low-cost hardware and a simple web interface to maintain."),
    ("Impact metrics we will measure:", "Class roll-call time, duplicate blocks, missed entries, and correction rate."),
]
tf = tb(s, 0.85, 2.3, 11.7, 4.2)
for i, (l, t) in enumerate(items3):
    p = para(tf, "", 15, DARK, first=(i == 0), space_after=14)
    r = p.add_run(); r.text = l + "  "
    r.font.size = Pt(15); r.font.bold = True; r.font.color.rgb = NAVY; r.font.name = FONT
    r = p.add_run(); r.text = t
    r.font.size = Pt(15); r.font.color.rgb = DARK; r.font.name = FONT
footer(s, 3)

# =========================================================
# SLIDE 4 — CONCEPT OVERVIEW (fingerprint + two-step added)
# =========================================================
s = prs.slides.add_slide(BLANK)
head(s, "CONCEPT OVERVIEW", "Our proposed solution",
     "Proposed dual-mode, offline-first classroom terminal with teacher approval")
bullets_block(s, [
    ("Dual-mode check-in",
     "Will pair a fingerprint sensor (AS608/R307) and RFID cards with 16×2 LCD, LEDs, and buzzer."),
    ("Two-step verification",
     "Fingerprint must match the tapped RFID card before a mark is recorded—preventing proxy attendance."),
    ("Offline-first queueing",
     "Planned local flash will buffer logs during Wi-Fi drops and sync later."),
    ("Teacher sign-off",
     "Proposed web dashboard will flag exceptions for review, edits, and export."),
])
callout(s, "Privacy by Design",
        "No facial cameras or raw fingerprint photos—only mathematical templates or pseudonymous card IDs.")
footer(s, 4)

# =========================================================
# SLIDE 5 — CONCEPTUAL SYSTEM FLOW (two-step check-in in steps 2–3)
# =========================================================
s = prs.slides.add_slide(BLANK)
head(s, "CONCEPTUAL SYSTEM FLOW", "How the concept works",
     "Five-step proposed classroom workflow from session open to verified export")
steps5 = [
    ("STEP 1", "Open session", "Teacher will start the period and open the attendance window."),
    ("STEP 2", "Student scans",
     "Student will tap an RFID card, then verify with a fingerprint scan (two-step match)."),
    ("STEP 3", "Local check",
     "Device will match fingerprint to card, check window and duplicates; queue offline."),
    ("STEP 4", "Cloud sync", "Logs will sync via scoped RPCs and flag any exceptions."),
    ("STEP 5", "Teacher confirms", "Teacher will review exceptions, approve edits, and export."),
]
cw, gap, x0, cy, ch = 2.32, 0.15, 0.6, 2.35, 3.85
for i, (st, t, b) in enumerate(steps5):
    x = x0 + i * (cw + gap)
    rect(s, x, cy, cw, ch, CARD)
    rect(s, x, cy, cw, 0.07, GOLD)
    tf = tb(s, x + 0.18, cy + 0.22, cw - 0.36, ch - 0.4)
    para(tf, str(i + 1), 26, GOLD, bold=True, first=True, space_after=2)
    para(tf, st, 10.5, GRAY, bold=True, space_after=4)
    para(tf, t, 14, NAVY, bold=True, space_after=5)
    para(tf, b, 11, DARK)
footer(s, 5)

# =========================================================
# SLIDE 6 — EXISTING SOLUTIONS & DIFFERENTIATION (table, 2-step wording)
# =========================================================
s = prs.slides.add_slide(BLANK)
head(s, "EXISTING SOLUTIONS & DIFFERENTIATION", "What makes our approach useful",
     "Commercial products exist—our proposed focus is school workflow, privacy, and offline resilience")
rows6 = [
    ["CRITERION", "PAPER REGISTER", "COMMERCIAL BIOMETRIC", "FACE / PHONE QR", "ASTRO (PROPOSED)"],
    ["Check-in Mode", "Manual roll-call", "Single sensor", "Camera or phone", "Fingerprint + RFID (2-step)"],
    ["Offline Resilience", "Paper only", "Often cloud-locked", "Needs live network", "Local flash queue"],
    ["Privacy Safeguard", "Open paper log", "Proprietary store", "Face images / phones", "Templates, no camera"],
    ["Teacher Oversight", "Full manual work", "Rigid auto-log", "High phone friction", "Review & audit trail"],
    ["School Practicality", "Slow, error-prone", "High license cost", "Unequal phone access", "Modular, low-cost"],
]
nrows, ncols = len(rows6), 5
tw, th = 11.9, 3.15
table = s.shapes.add_table(nrows, ncols, Inches(0.72), Inches(2.15), Inches(tw), Inches(th)).table
widths = [2.3, 2.35, 2.5, 2.45, 2.3]
for j, w in enumerate(widths):
    table.columns[j].width = Inches(w)
for i, row in enumerate(rows6):
    table.rows[i].height = Inches(th / nrows)
    for j, val in enumerate(row):
        c = table.cell(i, j)
        c.text = val
        c.vertical_anchor = MSO_ANCHOR.MIDDLE
        c.margin_left = Inches(0.08); c.margin_right = Inches(0.06)
        p = c.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT
        r = p.runs[0]
        r.font.name = FONT
        if i == 0:
            r.font.size = Pt(11); r.font.bold = True
            r.font.color.rgb = WHITE
            c.fill.solid(); c.fill.fore_color.rgb = NAVY
        else:
            is_ours = (j == ncols - 1)
            r.font.size = Pt(11.5); r.font.bold = (j == 0 or is_ours)
            r.font.color.rgb = NAVY if (j == 0 or is_ours) else DARK
            c.fill.solid()
            c.fill.fore_color.rgb = RGBColor(0xE9, 0xF0, 0xF7) if is_ours else (
                WHITE if i % 2 else CARD)
tf = tb(s, 0.72, 5.65, 11.9, 0.8)
para(tf, "Our proposed differentiator is combining fingerprint + RFID two-step verification, "
         "offline queueing, privacy, and teacher oversight—not claiming exclusivity.",
     13, DARK, italic=True, first=True)
footer(s, 6)

# =========================================================
# SLIDE 7 — PRACTICAL FEASIBILITY (fingerprint sensor named)
# =========================================================
s = prs.slides.add_slide(BLANK)
head(s, "PRACTICAL FEASIBILITY", "Prototype we can build",
     "Planned safe, low-voltage benchtop proof of concept using accessible STEM hardware")
bullets_block(s, [
    ("Planned ESP32 core", "240 MHz Wi-Fi board with SoftAP setup and LittleFS local queue."),
    ("Planned sensor stack", "AS608/R307 optical fingerprint sensor, RC522 RFID, 16×2 LCD, LEDs, buzzer."),
    ("Planned 3.3V power", "Stabilized rail inside a compact 3D-printed wall enclosure."),
])
callout(s, "Smallest Safe Demo First",
        "We plan to validate two-step check-in, duplicate blocking, and offline sync "
        "using fictional IDs, demo cards, and test fingerprint templates only.")
footer(s, 7)

# =========================================================
# SLIDE 8 — MEASURABLE VALIDATION PLAN (proxy rejection test added)
# =========================================================
s = prs.slides.add_slide(BLANK)
head(s, "MEASURABLE VALIDATION PLAN", "How we will test it",
     "Five evaluation tests planned against a manual roll-call baseline")
cards8 = [
    ("Speed", "30-student baseline",
     "Will compare check-in time for 30 simulated students vs. manual roll-call."),
    ("Integrity", "Proxy & duplicate rejection",
     "Will confirm fingerprints match their cards and repeated taps in the same period are blocked."),
    ("Edge Cases", "Late & invalid scans",
     "Will verify flagging of late entries, unknown cards, and unmatched fingerprints."),
    ("Resilience", "Offline queue sync",
     "Will drop Wi-Fi mid-session and confirm queued entries sync afterward."),
    ("Usability", "Teacher feedback",
     "Will collect teacher ratings on dashboard clarity, review speed, and export."),
]
cw, gap, x0 = 3.83, 0.17, 0.6
for i, (l, t, b) in enumerate(cards8):
    if i < 3:
        x = x0 + i * (cw + gap); y = 2.3; h = 1.95
        card(s, x, y, cw, h, l, t, b)
    else:
        cw2 = (12.13 - gap) / 2
        x = x0 + (i - 3) * (cw2 + gap); y = 4.42; h = 1.95
        card(s, x, y, cw2, h, l, t, b)
footer(s, 8)

# =========================================================
# SLIDE 9 — RESPONSIBLE INNOVATION (two-step safeguard wording)
# =========================================================
s = prs.slides.add_slide(BLANK)
head(s, "RESPONSIBLE INNOVATION", "Risks, limitations and safeguards",
     "Honest prototype boundaries and planned risk safeguards")

def panel(slide, x, y, w, h, title, items):
    rect(slide, x, y, w, h, CARD)
    rect(slide, x, y, w, 0.07, GOLD)
    tf = tb(slide, x + 0.28, y + 0.25, w - 0.55, h - 0.45)
    para(tf, title, 15.5, NAVY, bold=True, first=True, space_after=8)
    for it in items:
        para(tf, "▪  " + it, 12.5, DARK, space_after=7)

panel(s, 0.72, 2.25, 5.85, 4.35, "Risks & Limitations", [
    "Sharing or misreads: Lent cards, spoofed prints, or dusty fingers.",
    "Wi-Fi & power drops: Outages or voltage dips.",
    "Privacy & safety: Student data and wiring need strict care.",
    "Scope limit: Hardware cannot replace teacher judgment.",
])
panel(s, 6.75, 2.25, 5.85, 4.35, "Planned Safeguards", [
    "Two-step match + review: Fingerprint must match card + teacher sign-off.",
    "Offline + 3.3V filter: Local queue + power filtering.",
    "Templates + oversight: Fictional IDs, no photos, adult supervision.",
    "Audit trail: Every manual edit will be logged transparently.",
])
footer(s, 9)

# =========================================================
# SLIDE 10 — FROM CONCEPT TO EVIDENCE (PoC mentions two-step check-in)
# =========================================================
s = prs.slides.add_slide(BLANK)
head(s, "FROM CONCEPT TO EVIDENCE", "Our next steps and closing pitch", "")
steps10 = [
    ("1. Validate user need", "Conduct discovery dialogue and classroom observation with teachers."),
    ("2. Benchmark solutions", "Compare existing attendance tools and document baseline evidence."),
    ("3. Build small PoC", "Assemble a safe, low-voltage benchtop demo with fingerprint + RFID "
                          "two-step check-in and fictional IDs."),
    ("4. Test & record results", "Measure against a 30-student manual baseline and log actual findings."),
]
cw, gap, x0, cy, ch = 5.85, 0.18, 0.72, 2.05, 1.75
for i, (t, b) in enumerate(steps10):
    x = x0 + (i % 2) * (cw + gap)
    y = cy + (i // 2) * (ch + 0.16)
    rect(s, x, y, cw, ch, CARD)
    rect(s, x, y, 0.07, ch, GOLD)
    tf = tb(s, x + 0.25, y + 0.22, cw - 0.45, ch - 0.4)
    para(tf, t, 14.5, NAVY, bold=True, first=True, space_after=5)
    para(tf, b, 12, DARK)
callout(s, "Our promise",
        "Develop Astro Smart Attendance into a practical, affordable, and testable classroom solution.",
        y=5.95)
footer(s, 10)

OUT = "Astro-Smart-Attendance-Concept-Proposal.pptx"
prs.save(OUT)

# ---------- safety scan: no claims of already-created work ----------
texts = []
for sl in prs.slides:
    for sh in sl.shapes:
        if sh.has_text_frame:
            texts.append(sh.text_frame.text)
        if sh.has_table:
            for r in sh.table.rows:
                for c in r.cells:
                    texts.append(c.text)
all_text = "\n".join(texts)
bad = re.findall(r"[^.]*\b(already|we (?:have|'ve) (?:built|created|developed|implemented)|"
                 r"working prototype|prototype is|we built|we created|is ready)\b[^.]*",
                 all_text, flags=re.I)
print("SAFETY SCAN — phrases claiming completed work:", bad if bad else "NONE (all proposal tense)")
print("Saved:", OUT)
