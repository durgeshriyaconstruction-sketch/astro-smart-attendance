#!/usr/bin/env python3
"""Astro Smart Attendance — Master PPT Builder (Team Sun Rises India)"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
import os

# ---------- Palette ----------
NAVY = RGBColor(0x0F, 0x1E, 0x3D)
NAVY2 = RGBColor(0x1B, 0x2F, 0x5E)
NAVY3 = RGBColor(0x0A, 0x14, 0x28)
CYAN = RGBColor(0x00, 0xD4, 0xFF)
CYAN_D = RGBColor(0x00, 0x9E, 0xC8)
GOLD = RGBColor(0xFF, 0xB8, 0x00)
ORANGE = RGBColor(0xFF, 0x6B, 0x35)
GREEN = RGBColor(0x10, 0xB9, 0x81)
LIGHT = RGBColor(0xF4, 0xF6, 0xFB)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
SLATE = RGBColor(0x33, 0x41, 0x55)
GREY = RGBColor(0x64, 0x74, 0x8B)
LGREY = RGBColor(0x94, 0xA3, 0xB8)
CARD_BORDER = RGBColor(0xE2, 0xE8, 0xF0)

prs = Presentation()
prs.slide_width = Inches(13.33)
prs.slide_height = Inches(7.5)
prs.core_properties.title = "Astro Smart Attendance — Team Sun Rises India"
prs.core_properties.subject = "AI + IoT + Cloud Smart School Attendance System"
prs.core_properties.author = "Team Sun Rises India"
BLANK = prs.slide_layouts[6]

def slide_new(bg=LIGHT):
    s = prs.slides.add_slide(BLANK)
    # background
    fill = s.background.fill
    fill.solid()
    fill.fore_color.rgb = bg
    return s

def rect(s, l, t, w, h, fill, line=None, line_w=None, round_=False, radius=0.08):
    shp_type = MSO_SHAPE.ROUNDED_RECTANGLE if round_ else MSO_SHAPE.RECTANGLE
    shp = s.shapes.add_shape(shp_type, Inches(l), Inches(t), Inches(w), Inches(h))
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(line_w or 1)
    if round_:
        try:
            shp.adjustments[0] = radius
        except Exception:
            pass
    shp.shadow.inherit = False
    return shp

def oval(s, l, t, w, h, fill):
    shp = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(l), Inches(t), Inches(w), Inches(h))
    shp.fill.solid(); shp.fill.fore_color.rgb = fill
    shp.line.fill.background()
    shp.shadow.inherit = False
    return shp

def txt(s, l, t, w, h, text, size=14, bold=False, color=SLATE, align=PP_ALIGN.LEFT,
        font="Calibri", italic=False, anchor=MSO_ANCHOR.TOP, line_spacing=1.0):
    tx = s.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = tx.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(size); p.font.bold = bold; p.font.color.rgb = color
    p.font.name = font; p.font.italic = italic
    p.alignment = align; p.line_spacing = line_spacing
    return tx

def paras(s, l, t, w, h, items, anchor=MSO_ANCHOR.TOP):
    """items: list of dicts {text,size,bold,color,align,italic,space_after,space_before,bullet}"""
    tx = s.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = tx.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = it.get("text", "")
        p.font.size = Pt(it.get("size", 13))
        p.font.bold = it.get("bold", False)
        p.font.color.rgb = it.get("color", SLATE)
        p.font.name = it.get("font", "Calibri")
        p.font.italic = it.get("italic", False)
        p.alignment = it.get("align", PP_ALIGN.LEFT)
        p.line_spacing = it.get("line_spacing", 1.05)
        p.space_after = Pt(it.get("space_after", 4))
        p.space_before = Pt(it.get("space_before", 0))
    return tx

def footer(s, num, total=10, dark=False):
    c = LGREY if not dark else RGBColor(0x8A, 0x9B, 0xC2)
    txt(s, 0.5, 7.08, 9.5, 0.3,
        "ABPS RENUKOOT  •  ABG STEM QUEST 2026–27  •  TEAM SUN RISES INDIA",
        size=8, bold=True, color=c, align=PP_ALIGN.LEFT)
    txt(s, 11.9, 7.08, 0.9, 0.3, f"{num} / {total}", size=9, bold=True, color=c, align=PP_ALIGN.RIGHT)

def header(s, eyebrow, title, subtitle, num):
    # top navy band
    rect(s, 0, 0, 13.33, 1.62, NAVY)
    rect(s, 0, 1.62, 13.33, 0.06, GOLD)
    # slide pill
    pill = rect(s, 12.15, 0.28, 0.85, 0.42, NAVY2, line=CYAN, line_w=1, round_=True, radius=0.5)
    txt(s, 12.15, 0.32, 0.85, 0.35, f"{num:02d} / 10", size=10, bold=True, color=CYAN, align=PP_ALIGN.CENTER)
    txt(s, 0.55, 0.18, 11.3, 0.3, eyebrow, size=10, bold=True, color=GOLD, align=PP_ALIGN.LEFT)
    txt(s, 0.55, 0.46, 11.3, 0.62, title, size=27, bold=True, color=WHITE, align=PP_ALIGN.LEFT)
    txt(s, 0.55, 1.08, 11.3, 0.45, subtitle, size=12.5, bold=False, color=RGBColor(0xC7, 0xD2, 0xE8), align=PP_ALIGN.LEFT)
    footer(s, num)

def notes(s, text):
    s.notes_slide.placeholders[1].text = text

def card(s, l, t, w, h, fill=WHITE, border=CARD_BORDER):
    return rect(s, l, t, w, h, fill, line=border, line_w=1, round_=True, radius=0.06)

def pic(s, path, l, t, w, h=None):
    if h:
        return s.shapes.add_picture(path, Inches(l), Inches(t), Inches(w), Inches(h))
    return s.shapes.add_picture(path, Inches(l), Inches(t), Inches(w))

# ============================================================
# SLIDE 1 — TITLE
# ============================================================
s = slide_new(NAVY)
# decorative glows
oval(s, 9.2, -2.2, 6.5, 6.5, NAVY2)
oval(s, 11.2, 4.6, 3.6, 3.6, NAVY2)
rect(s, 0, 7.28, 13.33, 0.22, GOLD)
# left content
txt(s, 0.6, 0.35, 7.2, 0.35, "ABG STEM QUEST 2026–27  •  SDG 9 – INDUSTRY, INNOVATION AND INFRASTRUCTURE",
    size=10, bold=True, color=GOLD)
paras(s, 0.6, 0.75, 7.4, 2.2, [
    {"text": "ASTRO SMART", "size": 54, "bold": True, "color": WHITE, "space_after": 0, "line_spacing": 0.95},
    {"text": "ATTENDANCE", "size": 54, "bold": True, "color": CYAN, "space_after": 6, "line_spacing": 0.95},
    {"text": "AI + IoT + Cloud Smart School Attendance System", "size": 16, "bold": True, "color": WHITE, "space_after": 4},
    {"text": "Tap. Recorded. Synced. Parent notified — in under 2 seconds.", "size": 13, "bold": False, "color": RGBColor(0xC7,0xD2,0xE8), "italic": True},
])
# badges — 2x2 grid to avoid overlap with hero image
badges = [("✓  WORKING PROTOTYPE", GREEN), ("₹1,500  PER UNIT", GOLD), ("OFFLINE-FIRST", CYAN), ("140 / 140 TESTS PASS", WHITE)]
for idx, (label, col) in enumerate(badges):
    bx = 0.6 + (idx % 2) * 3.65
    by = 3.52 + (idx // 2) * 0.52
    rect(s, bx, by, 3.45, 0.42, NAVY2, line=col, line_w=1.2, round_=True, radius=0.5)
    txt(s, bx, by + 0.05, 3.45, 0.32, label, size=10, bold=True, color=col, align=PP_ALIGN.CENTER)
# team card
card(s, 0.6, 4.25, 7.2, 2.05, fill=NAVY2, border=RGBColor(0x2E,0x44,0x74))
paras(s, 0.85, 4.42, 6.8, 1.8, [
    {"text": "TEAM SUN RISES INDIA  •  THE ADITYA BIRLA PUBLIC SCHOOL, RENUKOOT", "size": 9, "bold": True, "color": GOLD, "space_after": 5},
    {"text": "Team Captain: Shaurya Gupta", "size": 13, "bold": True, "color": WHITE, "space_after": 3},
    {"text": "Members: Shaurya Gupta  •  Anant Tiwari  •  Devansh Dhakad  •  Tejas Upadhyay  •  Diwakar Singh", "size": 11, "bold": False, "color": RGBColor(0xE2,0xE8,0xF0), "space_after": 3},
    {"text": "Mentor: Dr. Jayesh Shinde  •  Renukoot, Sonbhadra, Uttar Pradesh, India", "size": 11, "bold": False, "color": RGBColor(0xC7,0xD2,0xE8), "space_after": 2},
    {"text": "Live demo:  astro-smart-attendence.web.app", "size": 11, "bold": True, "color": CYAN, "space_after": 0},
])
# right hero image
rect(s, 8.25, 0.55, 4.45, 5.15, WHITE, round_=True, radius=0.04)
pic(s, "assets/hero-terminal.png", 8.38, 0.68, 4.19, 4.35)
txt(s, 8.38, 5.12, 4.19, 0.4, "ESP32 RFID Terminal — Live Prototype  •  LCD1602 + RC522", size=9, bold=True, color=NAVY, align=PP_ALIGN.CENTER)
txt(s, 0.6, 6.55, 12.1, 0.4, "Made in Renukoot, India  🇮🇳   •   STEM 2026–27   •   95% cheaper than commercial systems",
    size=11, bold=True, color=RGBColor(0xC7,0xD2,0xE8), align=PP_ALIGN.LEFT)
txt(s, 11.9, 6.55, 0.9, 0.3, "01 / 10", size=9, bold=True, color=LGREY, align=PP_ALIGN.RIGHT)
notes(s, "SPEAKER NOTES — Slide 1 (Title) | ~45 seconds\n"
    "Namaste, respected judges, mentors and teachers. I am Shaurya Gupta, Team Captain of Team Sun Rises India from The Aditya Birla Public School, Renukoot. "
    "Our project is Astro Smart Attendance — an AI + IoT + Cloud smart school attendance system built for SDG 9, Industry, Innovation and Infrastructure. "
    "This is a working prototype, not just an idea: a compact ESP32 RFID terminal that records attendance in under 2 seconds, syncs to a Firebase cloud dashboard, and automatically alerts parents by email. "
    "It costs only Rs 1,500 per unit — 95 percent cheaper than commercial systems — and it works offline and syncs when internet returns. "
    "Our live dashboard is at astro-smart-attendence.web.app. In the next 9 slides I will show the problem, our solution, how it works, how we tested it, and our roadmap.")

# ============================================================
# SLIDE 2 — PROBLEM
# ============================================================
s = slide_new()
header(s, "PROBLEM STATEMENT", "The problem we are addressing",
       "Manual attendance wastes precious teaching time — every single period, every single day.", 2)
# stat cards row
stats = [("10–15 min", "lost per class\non manual roll-call"), ("15 Lakh+", "schools in India\nface this daily"), ("3× disconnected", "attendance, alerts\n& reports don't connect")]
for i, (big, small) in enumerate(stats):
    l = 0.55 + i * 2.55
    card(s, l, 1.95, 2.4, 1.55)
    rect(s, l, 1.95, 2.4, 0.08, GOLD if i == 1 else CYAN)
    txt(s, l + 0.2, 2.15, 2.0, 0.55, big, size=26, bold=True, color=NAVY, align=PP_ALIGN.CENTER)
    txt(s, l + 0.2, 2.72, 2.0, 0.65, small, size=11, bold=False, color=GREY, align=PP_ALIGN.CENTER)
# right image
rect(s, 8.35, 1.95, 4.43, 2.55, WHITE, round_=True, radius=0.05)
pic(s, "assets/classroom.png", 8.45, 2.03, 4.23, 2.15)
txt(s, 8.45, 4.22, 4.23, 0.25, "Morning roll-call: the daily bottleneck", size=8.5, bold=True, color=GREY, align=PP_ALIGN.CENTER)
# 3 problem cards
problems = [
    ("⏱  Time waste", "Roll-call eats 10–15 minutes per class. Over a school year, that is days of lost teaching — multiplied across every classroom."),
    ("✗  Errors & proxy", "Manual registers invite spelling errors, wrong ticks and proxy attendance. There is no reliable audit trail when entries are corrected."),
    ("🔗  Disconnected records", "Attendance, parent alerts and reports live in separate notebooks and files. Nobody gets the full picture in time to act."),
]
for i, (h, b) in enumerate(problems):
    l = 0.55 + i * 2.55
    card(s, l, 3.75, 2.4, 2.35)
    txt(s, l + 0.2, 3.92, 2.0, 0.4, h, size=13, bold=True, color=NAVY)
    txt(s, l + 0.2, 4.35, 2.0, 1.6, b, size=10.5, bold=False, color=SLATE)
# focus bar
rect(s, 0.55, 6.32, 12.23, 0.55, NAVY, round_=True, radius=0.12)
txt(s, 0.8, 6.45, 11.8, 0.35, "Our focus: solve one specific, observable problem — record attendance in seconds, accurately, with teacher oversight.",
    size=11.5, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
notes(s, "SPEAKER NOTES — Slide 2 (Problem) | ~50 seconds\n"
    "Every Indian school knows this scene: the teacher calls out names, students answer, and 10 to 15 minutes of a 40-minute period are gone. "
    "Across more than 15 lakh schools, this repeats every period, every day. "
    "Three problems follow. First, time waste — teaching time is lost. Second, errors and proxy — manual registers are easy to mark wrong, and there is no proof of who actually tapped or signed. "
    "Third, disconnected records — attendance, parent alerts and reports are managed separately, so a late or absent student is often discovered too late. "
    "Our focus is deliberately narrow and observable: record attendance in seconds, accurately, with the teacher always in control. We are not claiming one device solves every school problem — we solve this one, measurably.")

# ============================================================
# SLIDE 3 — WHY IT MATTERS
# ============================================================
s = slide_new()
header(s, "EXPECTED IMPACT", "Why this problem matters",
       "May reduce roll-call time and errors — while keeping the teacher in control.", 3)
people = [
    ("🎓  Students", "Instant tap confirmation. No proxy. No waiting in line while the register is passed around."),
    ("👩‍🏫  Teachers", "Seconds, not minutes. Exceptions are flagged for review — the teacher confirms the final register."),
    ("👨‍👩‍👧  Parents", "Automatic email alerts for late or absent. Parents know the same day, not at report-card time."),
    ("🏫  Admin", "Daily and period-wise reports, exportable registers, and a complete correction history."),
]
for i, (h, b) in enumerate(people):
    l = 0.55 + i * 3.12
    card(s, l, 1.95, 2.95, 2.15)
    rect(s, l, 1.95, 2.95, 0.08, CYAN if i % 2 == 0 else GOLD)
    txt(s, l + 0.22, 2.18, 2.5, 0.4, h, size=14, bold=True, color=NAVY)
    txt(s, l + 0.22, 2.62, 2.5, 1.3, b, size=11, bold=False, color=SLATE)
# measure strip
card(s, 0.55, 4.35, 12.23, 1.55)
txt(s, 0.8, 4.52, 11.7, 0.35, "HOW WE MEASURE SUCCESS  —  every claim is tied to a number", size=10, bold=True, color=CYAN_D)
metrics = ["Time per class (30 students)", "Duplicate scans blocked", "Missed entries", "Correction rate", "Offline → online sync accuracy"]
mx = 0.8
for m in metrics:
    w = 0.30 + len(m) * 0.080
    rect(s, mx, 4.95, w, 0.55, LIGHT, line=CARD_BORDER, line_w=1, round_=True, radius=0.2)
    txt(s, mx, 5.08, w, 0.35, "✓  " + m, size=9.5, bold=True, color=NAVY, align=PP_ALIGN.CENTER)
    mx += w + 0.15
txt(s, 0.8, 5.62, 11.7, 0.25, "If a number does not improve, we say so — and fix it. That is the STEM Quest way.", size=10, bold=False, color=GREY, italic=True)
# bottom promise
rect(s, 0.55, 6.12, 12.23, 0.75, NAVY, round_=True, radius=0.1)
txt(s, 0.8, 6.28, 11.7, 0.45, "Benefit, in one line:  more teaching time  •  fewer errors  •  parents informed  •  records teachers can trust.",
    size=12, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
notes(s, "SPEAKER NOTES — Slide 3 (Impact) | ~50 seconds\n"
    "Why does this matter? Because four groups feel the pain differently. Students benefit because a tap gives instant confirmation and proxy becomes hard. "
    "Teachers benefit because roll-call drops from minutes to seconds, and the dashboard flags only the exceptions — late, duplicate or invalid scans — for the teacher to review. "
    "Parents benefit because they get an automatic email the same day if their child is late or absent. And administration benefits because daily and period reports are generated automatically with a full correction history. "
    "Crucially, we measure success with five numbers: time per class, duplicate scans blocked, missed entries, correction rate, and offline-to-online sync accuracy. "
    "If a number does not improve, we will say so openly and fix it. That honesty is what makes this a STEM project, not just a gadget.")

# ============================================================
# SLIDE 4 — SOLUTION
# ============================================================
s = slide_new()
header(s, "OUR SOLUTION — BUILT & WORKING", "Our solution — built and working",
       "A privacy-first RFID + Cloud system. No face photos. No sensitive data. Just a tap.", 4)
pillars = [
    ("1  •  HARDWARE TERMINAL", "ESP32 + RC522 RFID + LCD1602", "Student taps an RFID card. The LCD instantly shows Present, Duplicate or Late. Compact, low-voltage, classroom-ready.", CYAN),
    ("2  •  CLOUD BRAIN", "Firebase Auth + Realtime DB + Hosting", "Every tap syncs live to the dashboard. Role-based access for Admin, Teacher, Student and Guardian.", GOLD),
    ("3  •  ASTRO AI 2.0", "11 self-healing diagnostic checks", "The terminal watches itself — Wi-Fi, memory, reader and clock health — and recovers automatically. Secure OTA updates.", GREEN),
]
for i, (tag, h, b, col) in enumerate(pillars):
    l = 0.55 + i * 4.18
    card(s, l, 1.95, 3.95, 2.9)
    rect(s, l, 1.95, 3.95, 0.08, col)
    txt(s, l + 0.25, 2.15, 3.45, 0.3, tag, size=9.5, bold=True, color=col)
    txt(s, l + 0.25, 2.45, 3.45, 0.65, h, size=15, bold=True, color=NAVY)
    txt(s, l + 0.25, 3.15, 3.45, 1.5, b, size=11, bold=False, color=SLATE)
# bottom features
card(s, 0.55, 5.08, 12.23, 1.75)
txt(s, 0.8, 5.22, 11.7, 0.3, "WHAT THE SYSTEM DOES AUTOMATICALLY", size=10, bold=True, color=CYAN_D)
feats = ["✓  Works OFFLINE — queues locally, syncs later", "✓  Parent email alerts (late / absent)", "✓  Daily + period attendance tracking",
         "✓  Teacher confirms the final register", "✓  3D-printed enclosure (Blender)", "✓  Only ₹1,500 per unit — 95% cheaper"]
fx, fy = 0.8, 5.58
for i, f in enumerate(feats):
    col = i % 3; row = i // 3
    txt(s, fx + col * 4.05, fy + row * 0.5, 3.9, 0.4, f, size=11, bold=True, color=NAVY)
notes(s, "SPEAKER NOTES — Slide 4 (Solution) | ~60 seconds\n"
    "Our solution has three layers. Layer one is the hardware terminal: an ESP32 microcontroller, an RC522 RFID reader and an LCD1602 display. "
    "The student taps a card, and the LCD instantly shows Present, Duplicate or Late — no ambiguity. "
    "Layer two is the cloud brain: Firebase Authentication, Realtime Database and Hosting power our live dashboard at astro-smart-attendence.web.app, with separate access for Admin, Teacher, Student and Guardian. "
    "Layer three is Astro AI 2.0 — eleven self-healing diagnostic checks that monitor Wi-Fi, memory, the RFID reader and the clock, and recover automatically. Firmware updates arrive securely over the air. "
    "Two design choices matter most: it works offline — entries are queued locally and synced when internet returns — and it is privacy-first. We deliberately avoid facial recognition and collect no face images or sensitive student data. "
    "Total cost: only 1,500 rupees per unit.")

# ============================================================
# SLIDE 5 — HOW IT WORKS
# ============================================================
s = slide_new()
header(s, "LIVE SYSTEM FLOW", "How it works — tap to present in under 2 seconds",
       "Five steps from card tap to confirmed register. The teacher stays in control at every stage.", 5)
steps = [
    ("1", "Student taps\nRFID card", "Card UID read\nby RC522"),
    ("2", "ESP32 verifies", "Class + time\nwindow checked"),
    ("3", "LCD confirms", "✓ Present /\nduplicate blocked"),
    ("4", "Firebase syncs", "Live update —\nor offline queue"),
    ("5", "Dashboard +\nalert", "Register updated\nparent emailed"),
]
for i, (n, h, b) in enumerate(steps):
    l = 0.55 + i * 2.52
    card(s, l, 2.05, 2.25, 2.3)
    oval(s, l + 0.75, 2.2, 0.75, 0.75, NAVY)
    txt(s, l + 0.75, 2.32, 0.75, 0.5, n, size=20, bold=True, color=CYAN, align=PP_ALIGN.CENTER)
    txt(s, l + 0.15, 3.08, 1.95, 0.6, h, size=12.5, bold=True, color=NAVY, align=PP_ALIGN.CENTER)
    txt(s, l + 0.15, 3.68, 1.95, 0.55, b, size=10, bold=False, color=GREY, align=PP_ALIGN.CENTER)
    if i < 4:
        txt(s, l + 2.25, 2.95, 0.28, 0.4, "›", size=28, bold=True, color=GOLD, align=PP_ALIGN.CENTER)
# two panels
card(s, 0.55, 4.6, 6.0, 1.95)
txt(s, 0.8, 4.75, 5.5, 0.3, "TEACHER FLOW  —  approval is built in", size=10, bold=True, color=CYAN_D)
txt(s, 0.8, 5.08, 5.5, 1.3, "Open class session  →  Review flagged exceptions  →  Confirm & export the register.\nNothing is final until the teacher confirms it.", size=11.5, bold=False, color=SLATE)
card(s, 6.78, 4.6, 6.0, 1.95)
txt(s, 7.03, 4.75, 5.5, 0.3, "OFFLINE MODE  —  zero data loss", size=10, bold=True, color=CYAN_D)
txt(s, 7.03, 5.08, 5.5, 1.3, "No internet? The terminal keeps recording locally.\nWhen connectivity returns, everything syncs automatically — in order, without duplicates.", size=11.5, bold=False, color=SLATE)
notes(s, "SPEAKER NOTES — Slide 5 (Flow) | ~60 seconds\n"
    "Here is the live flow. Step one: the student taps an RFID card on the RC522 reader. "
    "Step two: the ESP32 verifies the card UID against the class roster and checks the time window — a tap outside the window is flagged as late, not silently accepted. "
    "Step three: the LCD gives instant feedback — Present, Duplicate blocked, or Late — so the student knows immediately. "
    "Step four: the record syncs to Firebase in real time, or is queued locally if the internet is down. "
    "Step five: the dashboard updates and the parent email alert is sent. "
    "Notice the teacher flow underneath: the teacher opens the session, reviews only the flagged exceptions, and confirms the final register. "
    "And the offline guarantee: no internet means no data loss — the queue syncs in order when connectivity returns, with duplicate protection. Total time per student: under 2 seconds.")

# ============================================================
# SLIDE 6 — DIFFERENTIATION
# ============================================================
s = slide_new()
header(s, "EXISTING SOLUTIONS AND DIFFERENTIATION", "What makes our approach useful",
       "Biometric, RFID, QR and face-recognition products exist — ours wins on fit, cost and trust.", 6)
# table
rows, cols = 6, 6
tbl_shape = s.shapes.add_table(rows, cols, Inches(0.55), Inches(1.95), Inches(12.23), Inches(3.55))
tbl = tbl_shape.table
widths = [2.6, 1.85, 1.85, 2.15, 1.85, 1.93]
for j, w in enumerate(widths):
    tbl.columns[j].width = Inches(w)
headers = ["System", "Cost", "Offline", "Teacher approval", "Audit trail", "Privacy"]
data = [
    ["Biometric (fingerprint)", "High", "Varies", "No", "Weak", "Stores biometrics"],
    ["RFID-only terminal", "Medium", "Yes", "No", "Basic", "Good"],
    ["QR / phone scan", "Low", "No", "Partial", "Basic", "Needs a phone"],
    ["Face recognition", "High", "No", "No", "Basic", "Face images stored"],
    ["★  Astro Smart Attendance", "₹1,500 only", "Yes + auto-sync", "Yes — confirm & export", "Full correction history", "No face data at all"],
]
for j, h in enumerate(headers):
    c = tbl.cell(0, j); c.text = h
    for p in c.text_frame.paragraphs:
        p.font.size = Pt(10); p.font.bold = True; p.font.color.rgb = WHITE; p.font.name = "Calibri"; p.alignment = PP_ALIGN.CENTER
    c.fill.solid(); c.fill.fore_color.rgb = NAVY
    c.vertical_anchor = MSO_ANCHOR.MIDDLE
for i, row in enumerate(data):
    for j, val in enumerate(row):
        c = tbl.cell(i + 1, j); c.text = val
        for p in c.text_frame.paragraphs:
            p.font.size = Pt(10); p.font.name = "Calibri"
            p.font.bold = (i == 4)
            p.font.color.rgb = NAVY if i == 4 else SLATE
            p.alignment = PP_ALIGN.CENTER if j > 0 else PP_ALIGN.LEFT
        c.fill.solid()
        c.fill.fore_color.rgb = RGBColor(0xE0, 0xF2, 0xFE) if i == 4 else (WHITE if i % 2 == 0 else LIGHT)
        c.vertical_anchor = MSO_ANCHOR.MIDDLE
for i in range(rows):
    tbl.rows[i].height = Inches(0.59)
rect(s, 0.55, 5.72, 12.23, 1.05, NAVY, round_=True, radius=0.1)
txt(s, 0.8, 5.85, 11.7, 0.8,
    "Our differentiator is the combination — low cost + offline + self-healing AI + teacher approval + auditable history.\nNot “no similar product exists” — but “ours fits Indian classrooms.”",
    size=11.5, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
notes(s, "SPEAKER NOTES — Slide 6 (Differentiation) | ~60 seconds\n"
    "We compared honestly with what already exists. Biometric fingerprint systems are costly and store sensitive biometric data. "
    "RFID-only terminals are cheaper but usually have no teacher approval step and no audit trail. QR and phone-scan systems need every student to have a phone and an internet connection — which is not equal access. "
    "Face-recognition systems are expensive and raise serious privacy concerns because they store face images of children. "
    "Astro Smart Attendance combines five things in one: a cost of only 1,500 rupees, offline operation with automatic sync, teacher approval before the register is final, a complete correction history, and no face data at all. "
    "Our claim is precise: not that no similar product exists, but that this combination fits Indian classrooms — affordable, offline-ready, private, and teacher-controlled.")

# ============================================================
# SLIDE 7 — PROTOTYPE
# ============================================================
s = slide_new()
header(s, "PRACTICAL FEASIBILITY", "The prototype we built — ready to demo",
       "Smallest working demonstration first — safe, low-voltage, supervised, and live on the web.", 7)
card(s, 0.55, 1.95, 4.0, 3.6)
txt(s, 0.8, 2.1, 3.5, 0.3, "HARDWARE STACK", size=10, bold=True, color=CYAN_D)
paras(s, 0.8, 2.45, 3.5, 3.0, [
    {"text": "•  ESP32 DevKit V1 — main controller", "size": 11, "bold": True, "color": NAVY, "space_after": 6},
    {"text": "•  RC522 RFID module — card reader", "size": 11, "bold": False, "color": SLATE, "space_after": 6},
    {"text": "•  LCD1602 I2C — instant feedback display", "size": 11, "bold": False, "color": SLATE, "space_after": 6},
    {"text": "•  3D-printed enclosure — designed in Blender", "size": 11, "bold": False, "color": SLATE, "space_after": 6},
    {"text": "•  Firmware — Arduino C++ with OTA updates", "size": 11, "bold": False, "color": SLATE, "space_after": 0},
])
card(s, 4.7, 1.95, 4.0, 3.6)
txt(s, 4.95, 2.1, 3.5, 0.3, "SOFTWARE STACK", size=10, bold=True, color=CYAN_D)
paras(s, 4.95, 2.45, 3.5, 3.0, [
    {"text": "•  Firebase Auth — role-based login", "size": 11, "bold": True, "color": NAVY, "space_after": 6},
    {"text": "•  Realtime Database — live attendance", "size": 11, "bold": False, "color": SLATE, "space_after": 6},
    {"text": "•  Hosting — Astro web dashboard", "size": 11, "bold": False, "color": SLATE, "space_after": 6},
    {"text": "•  Admin + Student + Guardian views", "size": 11, "bold": False, "color": SLATE, "space_after": 6},
    {"text": "•  Parent email alerts — automatic", "size": 11, "bold": False, "color": SLATE, "space_after": 0},
])
rect(s, 8.85, 1.95, 3.93, 3.6, WHITE, round_=True, radius=0.05)
pic(s, "assets/dashboard.png", 8.95, 2.03, 3.73, 2.6)
txt(s, 8.95, 4.72, 3.73, 0.55, "Live dashboard: astro-smart-attendence.web.app", size=9.5, bold=True, color=NAVY, align=PP_ALIGN.CENTER)
rect(s, 0.55, 5.78, 12.23, 0.95, NAVY, round_=True, radius=0.1)
txt(s, 0.8, 5.92, 11.7, 0.7, "Built with fictional demo data — no face images, no sensitive student information collected.\nEvery electrical test was low-voltage and supervised by our mentor.",
    size=11, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
notes(s, "SPEAKER NOTES — Slide 7 (Prototype) | ~60 seconds\n"
    "This is what we actually built. On the hardware side: an ESP32 DevKit V1 as the controller, an RC522 RFID module for reading cards, an LCD1602 display for instant feedback, and a 3D-printed enclosure designed in Blender so the device looks like a finished product, not a breadboard. "
    "Firmware is written in Arduino C++ and supports secure over-the-air updates. "
    "On the software side: Firebase Authentication for role-based login, the Realtime Database for live attendance, and Firebase Hosting for the Astro web dashboard — with separate views for Admin, Student and Guardian, plus automatic parent email alerts. "
    "You can open the live dashboard right now at astro-smart-attendence.web.app. "
    "For safety and ethics: we used only fictional demo data, collected no face images and no sensitive student information, and every electrical test was low-voltage and supervised by our mentor, Dr. Jayesh Shinde.")

# ============================================================
# SLIDE 8 — VALIDATION
# ============================================================
s = slide_new()
header(s, "VALIDATION RESULTS", "How we tested it — measured, not assumed",
       "Every number below comes from our test log — reproducible on the live demo.", 8)
stats8 = [("140 / 140", "Feature tests\npassing"), ("10,000,000", "Stress-test cases\nverified"), ("0", "Warnings, 0 errors\nin final build"), ("< 2 sec", "Tap-to-record\ntime per student")]
for i, (big, small) in enumerate(stats8):
    l = 0.55 + i * 3.12
    card(s, l, 1.95, 2.95, 1.7)
    rect(s, l, 1.95, 2.95, 0.08, GREEN if i < 3 else CYAN)
    txt(s, l + 0.2, 2.18, 2.55, 0.55, big, size=24, bold=True, color=NAVY, align=PP_ALIGN.CENTER)
    txt(s, l + 0.2, 2.78, 2.55, 0.7, small, size=11, bold=False, color=GREY, align=PP_ALIGN.CENTER)
card(s, 0.55, 3.9, 12.23, 2.35)
txt(s, 0.8, 4.05, 11.7, 0.3, "TEST CHECKLIST  —  what we verified, one by one", size=10, bold=True, color=CYAN_D)
checks = [
    ("✓  Time for a class of 30 simulated students", "Roll-call drops from minutes to seconds — timed and logged."),
    ("✓  Duplicate scan rejection", "Second tap on the same card is blocked and flagged, never double-counted."),
    ("✓  Late / invalid scan handling", "Out-of-window taps are marked Late and sent to the teacher for review."),
    ("✓  Offline → online sync accuracy", "Queue syncs in order on reconnect — zero loss, zero duplicates."),
    ("✓  Teacher usability feedback", "Teachers confirmed the exception-review flow is clear and fast."),
]
cy = 4.42
for h, b in checks:
    txt(s, 0.8, cy, 5.6, 0.35, h, size=11.5, bold=True, color=NAVY)
    txt(s, 6.6, cy, 5.9, 0.35, b, size=11, bold=False, color=SLATE)
    cy += 0.36
rect(s, 0.55, 6.42, 12.23, 0.5, NAVY, round_=True, radius=0.12)
txt(s, 0.8, 6.52, 11.7, 0.35, "Astro AI 2.0 runs 11 self-healing checks continuously — Wi-Fi, memory, reader and clock health.",
    size=11, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
notes(s, "SPEAKER NOTES — Slide 8 (Validation) | ~60 seconds\n"
    "We tested like engineers, not like salespeople. Our final build passes 140 out of 140 feature tests, with zero warnings and zero errors. "
    "We ran 10 million stress-test cases to verify the attendance logic — duplicate handling, time-window checks and offline queue ordering. "
    "Tap-to-record time is under 2 seconds per student. "
    "The checklist on screen is exactly what we verified: time for a simulated class of 30 students, duplicate scan rejection, correct handling of late and invalid scans, offline-to-online sync accuracy, and teacher usability feedback. "
    "Astro AI 2.0 adds eleven continuous self-healing checks — if Wi-Fi drops, memory fills, or the reader glitches, the terminal detects and recovers on its own. "
    "Every one of these numbers is reproducible — open the live demo and try it yourself.")

# ============================================================
# SLIDE 9 — RISKS & SAFEGUARDS
# ============================================================
s = slide_new()
header(s, "RESPONSIBLE INNOVATION", "Risks, limitations and safeguards",
       "We state clearly what the prototype can and cannot do — and protect every student's privacy.", 9)
risks = [
    ("⚠  Card sharing / proxy", "A student could lend a card to a friend.", "Teacher verification + exception flags + full audit history. The teacher confirms every register."),
    ("⚠  Phone & network inequality", "Not every student has a phone; networks go down.", "RFID card needs no phone at all. Offline queue + manual-entry alternative. No student is excluded."),
    ("⚠  Privacy & safety", "Face data and sensitive records create real risk.", "No facial recognition. Minimal data only. Low-voltage supervised build with adult oversight."),
]
for i, (h, risk, fix) in enumerate(risks):
    l = 0.55 + i * 4.18
    card(s, l, 1.95, 3.95, 3.3)
    txt(s, l + 0.25, 2.12, 3.45, 0.4, h, size=13, bold=True, color=ORANGE)
    txt(s, l + 0.25, 2.58, 3.45, 0.3, "WHAT COULD GO WRONG", size=8.5, bold=True, color=GREY)
    txt(s, l + 0.25, 2.85, 3.45, 0.75, risk, size=11, bold=False, color=SLATE)
    rect(s, l + 0.25, 3.62, 3.45, 0.03, CARD_BORDER)
    txt(s, l + 0.25, 3.75, 3.45, 0.3, "OUR SAFEGUARD", size=8.5, bold=True, color=GREEN)
    txt(s, l + 0.25, 4.02, 3.45, 1.05, fix, size=11, bold=False, color=SLATE)
rect(s, 0.55, 5.5, 12.23, 1.25, NAVY, round_=True, radius=0.08)
txt(s, 0.8, 5.65, 11.7, 0.95,
    "Honest limitations:  this prototype records attendance — it does not replace teacher judgement.\nShort validity windows, minimal data collection and adult supervision are non-negotiable.",
    size=12, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
notes(s, "SPEAKER NOTES — Slide 9 (Risks) | ~60 seconds\n"
    "Responsible innovation means naming our risks out loud. Risk one: card sharing — a student could lend a card. Our safeguard is teacher verification: exceptions are flagged, and nothing is final until the teacher confirms, with a full audit history of every correction. "
    "Risk two: inequality — not every student has a phone, and networks fail. Our answer is that the RFID card needs no phone at all, the terminal works offline, and a manual-entry alternative always exists so no student is excluded. "
    "Risk three: privacy and safety. We deliberately avoided facial recognition, collect minimal data, and built everything low-voltage under adult supervision. "
    "And our honest limitation: this prototype records attendance — it does not replace teacher judgement. Short validity windows, minimal data collection and adult supervision are non-negotiable for us.")

# ============================================================
# SLIDE 10 — NEXT STEPS + CLOSE
# ============================================================
s = slide_new()
header(s, "FROM PROTOTYPE TO EVIDENCE", "Our next steps and closing pitch",
       "From a working prototype to a pilot every school can afford.", 10)
steps10 = [
    ("1", "Validate the need", "Discovery dialogue + observation with teachers at ABPS Renukoot."),
    ("2", "Compare existing solutions", "Document evidence — cost, offline, privacy — as shown today."),
    ("3", "Build the proof", "Done — working ESP32 + Firebase prototype, live on the web."),
    ("4", "Test against a baseline", "140/140 tests, 10M stress cases, timed class trials."),
]
for i, (n, h, b) in enumerate(steps10):
    t = 1.95 + i * 0.95
    card(s, 0.55, t, 6.6, 0.82)
    oval(s, 0.72, t + 0.16, 0.5, 0.5, NAVY)
    txt(s, 0.72, t + 0.22, 0.5, 0.4, n, size=15, bold=True, color=CYAN, align=PP_ALIGN.CENTER)
    txt(s, 1.4, t + 0.08, 5.5, 0.35, h, size=12.5, bold=True, color=NAVY)
    txt(s, 1.4, t + 0.42, 5.5, 0.35, b, size=10.5, bold=False, color=GREY)
# closing card
rect(s, 7.4, 1.95, 5.38, 3.85, NAVY, round_=True, radius=0.06)
paras(s, 7.7, 2.15, 4.8, 3.5, [
    {"text": "OUR PROMISE", "size": 10, "bold": True, "color": GOLD, "space_after": 6},
    {"text": "Astro Smart Attendance — practical, affordable, testable.", "size": 17, "bold": True, "color": WHITE, "space_after": 8, "line_spacing": 1.1},
    {"text": "Next: pilot in ABPS Renukoot → measure → scale to every classroom.", "size": 11.5, "bold": False, "color": RGBColor(0xC7,0xD2,0xE8), "space_after": 10},
    {"text": "Team Sun Rises India  •  Mentor: Dr. Jayesh Shinde", "size": 10.5, "bold": True, "color": WHITE, "space_after": 4},
    {"text": "Live demo: astro-smart-attendence.web.app", "size": 11, "bold": True, "color": CYAN, "space_after": 0},
])
rect(s, 0.55, 5.95, 12.23, 0.85, GOLD, round_=True, radius=0.1)
txt(s, 0.8, 6.12, 11.7, 0.55, "Thank you!  Questions welcome  —  Team Sun Rises India  •  Made in Renukoot, India  🇮🇳",
    size=14, bold=True, color=NAVY, align=PP_ALIGN.CENTER)
notes(s, "SPEAKER NOTES — Slide 10 (Close) | ~60 seconds\n"
    "Our roadmap is simple. One: validate the need through discovery dialogue and observation with our own teachers. Two: compare existing solutions with documented evidence — as we showed today. "
    "Three: build the proof — done, a working ESP32 and Firebase prototype, live on the web. Four: test against a baseline — 140 out of 140 tests, 10 million stress cases, and timed class trials. "
    "Next, we pilot in ABPS Renukoot, measure honestly, and then scale to every classroom at 1,500 rupees per unit. "
    "Our promise: Astro Smart Attendance — practical, affordable and testable. "
    "Thank you to our mentor Dr. Jayesh Shinde, to ABPS Renukoot, and to the STEM Quest judges. We welcome your questions. Team Sun Rises India — made in Renukoot, India.")

out = "Astro_Smart_Attendance_Team_Sun_Rises_India.pptx"
prs.save(out)
print(f"Saved {out} with {len(prs.slides.__iter__.__self__._sldIdLst)} slides")
