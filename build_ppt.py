"""
build_ppt.py — Astro Smart Attendance · master deck
Team Sun Rises India · ABPS Renukoot · ABG STEM Quest 2026-27

Run:  python3 build_ppt.py   ->  Astro_Smart_Attendance_Team_Sun_Rises_India.pptx + deck.json
      python3 render_preview.py  ->  preview/slide-XX.png
"""
import os

from pptx.enum.dml import MSO_LINE
from pptx.enum.shapes import MSO_SHAPE

from deck import Deck

HERE = os.path.dirname(os.path.abspath(__file__))
A = lambda p: os.path.join("assets", p)

# ---------------------------------------------------------------- palette
INK = "#0B1B33"        # deepest navy
NAVY = "#122A4F"
NAVY2 = "#1B3A66"
NAVY3 = "#254A7C"
CYAN = "#22D3EE"
CYAN_D = "#0E9FBF"
CYAN_L = "#E6F9FD"
GOLD = "#F5B301"
GOLD_L = "#FFF6E0"
GREEN = "#12A87A"
GREEN_L = "#E4F7F1"
RED = "#E2574C"
RED_L = "#FDECEA"
VIOLET = "#6D6AF0"
WHITE = "#FFFFFF"
PAPER = "#F5F7FC"
CARD = "#FFFFFF"
BORDER = "#DFE6F0"
SLATE = "#41506B"
GREY = "#6B7A94"
LGREY = "#9AA8BF"
MIST = "#C9D6E8"

TOTAL = 14
d = Deck()
W, H = d.w, d.h


# ---------------------------------------------------------------- helpers
def full_bg(c):
    d.rect(0, 0, W, H, c)


def page_top(eyebrow, title, sub, num, accent=GOLD):
    """Light content slide chrome: eyebrow, headline, deck rail, footer.
    The headline auto-shrinks and the subtitle is placed by measured height,
    so no title can ever collide with what follows."""
    d.rect(0, 0, W, 0.14, INK)
    d.rect(0, 0.14, W, 0.035, accent)
    d.rect(0.62, 0.52, 0.055, 0.22, accent)
    d.text(0.80, 0.50, 8.6, 0.26, eyebrow, size=9.5, bold=True, color=CYAN_D, caps=True, spc=140)

    tw = 11.95
    size = 31.0
    for _ in range(40):
        if d.measure(title, size, True, False, tw)[0] <= 1:
            break
        size -= 0.5
    nlines, th = d.measure(title, size, True, False, tw, 0.95)
    y = 0.78
    d.text(0.62, y, tw, th + 0.02, title, size=size, bold=True, color=INK, ls=0.95)
    if sub:
        d.text(0.62, y + th + 0.14, 11.95, 0.34, sub, size=12.5, color=GREY, ls=1.0)
    footer(num)
    return y + th + (0.62 if sub else 0.14)


def footer(num, dark=False):
    y = 7.06
    c = MIST if dark else LGREY
    d.line(0.62, y - 0.10, W - 0.62, y - 0.10, "#2A426B" if dark else BORDER, 0.75)
    d.text(0.62, y, 7.4, 0.22,
           "ABPS RENUKOOT   ·   ABG STEM QUEST 2026–27   ·   TEAM SUN RISES INDIA",
           size=7.6, bold=True, color=c, spc=90)
    d.text(W - 2.1, y, 1.48, 0.22, "%02d / %d" % (num, TOTAL),
           size=7.6, bold=True, color=c, align="r", spc=90)


def tag(x, y, w, label, fg=CYAN_D, bg=CYAN_L, size=8, pad=0.0):
    h = 0.26
    d.rect(x, y, w, h, bg, radius=h / 2)
    d.text(x + pad, y + 0.055, w - 2 * pad, 0.2, label, size=size, bold=True, color=fg,
           align="c", caps=True, spc=90)
    return h


def stat(x, y, w, big, label, sub, accent=CYAN_D, bigsize=30):
    d.rect(x, y, w, 0.055, accent)
    d.text(x, y + 0.20, w, 0.62, big, size=bigsize, bold=True, color=INK, ls=0.9)
    d.text(x, y + 0.20 + bigsize / 62.0, w, 0.24, label, size=9.5, bold=True,
           color=accent, caps=True, spc=80)
    if sub:
        d.text(x, y + 0.36 + bigsize / 62.0 + 0.22, w, 0.5, sub, size=10, color=GREY, ls=1.1)


def note(text):
    d.notes(text)


# ================================================================ 01 TITLE
d.add_slide(INK, dark=True)
full_bg(INK)
# ambient depth
d.oval(8.35, -2.35, 7.6, 7.6, "#17335F")
d.oval(10.9, 3.05, 5.2, 5.2, "#1A3A69")
d.oval(-2.2, 3.6, 5.0, 5.0, "#12294C")
d.rect(0, 0, W, 0.06, CYAN)
d.rect(0, 0.06, 3.3, 0.02, GOLD)

d.text(0.68, 0.42, 6.6, 0.24, "ABG STEM QUEST 2026–27", size=9, bold=True, color=GOLD, caps=True, spc=170)
d.line(0.68, 0.72, 1.32, 0.72, CYAN, 1.6)
d.text(0.68, 0.82, 3.3, 0.26, "SDG 9  ·  INDUSTRY, INNOVATION & INFRASTRUCTURE",
       size=7.6, bold=True, color=MIST, caps=True, spc=110)

d.text(0.64, 1.30, 6.9, 0.92, "ASTRO SMART", size=62, bold=True, color=WHITE, ls=0.86)
d.text(0.64, 2.14, 6.9, 0.92, "ATTENDANCE", size=62, bold=True, color=CYAN, ls=0.86)
d.text(0.68, 3.20, 6.5, 0.30, "AI  +  IoT  +  CLOUD   SMART SCHOOL ATTENDANCE",
       size=11.5, bold=True, color=WHITE, spc=120)
d.text(0.68, 3.54, 6.4, 0.34, "Tap a card. Present, synced, parent notified — in under two seconds.",
       size=12.5, italic=True, color=MIST, ls=1.15)

badges = [("Prototype in hand", GREEN), ("₹1,500 per unit", GOLD),
          ("Works fully offline", CYAN), ("140 of 140 tests pass", WHITE)]
for i, (lab, col) in enumerate(badges):
    yy = 4.38 + (i // 2) * 0.42
    xx = 0.68 + (i % 2) * 2.72
    import textmetrics as _TM
    wbadge = _TM.width(lab, 9, True, False) / 288.0 + 0.50
    d.rect(xx, yy, wbadge, 0.32, None, line=col, lw=0.9, radius=0.16)
    d.oval(xx + 0.18, yy + 0.128, 0.064, 0.064, col)
    d.text(xx + 0.31, yy + 0.072, wbadge - 0.42, 0.22, lab, size=9, bold=True, color=WHITE, spc=25)

d.line(0.68, 5.62, 7.10, 5.62, "#2C4C7C", 0.9)
d.text(0.68, 5.76, 6.4, 0.22, "TEAM SUN RISES INDIA  ·  THE ADITYA BIRLA PUBLIC SCHOOL, RENUKOOT",
       size=8.2, bold=True, color=GOLD, caps=True, spc=70)
d.text(0.68, 6.04, 6.6, 0.24,
       "Shaurya Gupta (Captain) · Anant Tiwari · Devansh Dhakad · Tejas Upadhyay · Diwakar Singh",
       size=9.6, color=WHITE)
d.text(0.68, 6.30, 6.6, 0.24, "Mentor: Dr. Jayesh Shinde   ·   Renukoot, Sonbhadra, Uttar Pradesh",
       size=9.6, color=MIST)
d.text(0.68, 6.60, 6.6, 0.24, "astro-smart-attendence.web.app", size=9.6, bold=True, color=CYAN)

# hero
d.rect(8.30, 0.98, 4.42, 4.06, "#1D3E6E", radius=0.10)
d.pic(A("hero_v2.png"), 8.40, 1.08, 4.22, 3.86)
d.text(8.40, 5.16, 4.22, 0.22, "ESP32 · RC522 RFID · LCD1602 · 3D-PRINTED ENCLOSURE",
       size=7.4, bold=True, color=MIST, align="c", spc=45)
note(
    "SPEAKER NOTES — Slide 1 · Title · ~40 sec\n\n"
    "Good morning, respected judges, mentors and teachers. I am Shaurya Gupta, captain of Team Sun Rises India "
    "from The Aditya Birla Public School, Renukoot.\n\n"
    "This is Astro Smart Attendance — an attendance system we designed, built and tested ourselves, mapped to SDG 9. "
    "A student taps an RFID card on our ESP32 terminal; the record reaches the Firebase cloud in under two seconds, "
    "the dashboard updates live, and the parent gets an email if the student is late or absent.\n\n"
    "Four things to hold on to: we have a prototype in hand, it costs 1,500 rupees per unit, it keeps working when the "
    "internet does not, and it passed 140 of 140 of our tests. In the next thirteen slides I will show you the problem, "
    "the build, the evidence, and where we take it next.")

# ================================================================ 02 PROBLEM
d.add_slide(PAPER)
page_top("Problem statement", "Fifteen minutes of teaching, lost every period.",
         "Roll-call is still manual in most Indian classrooms. The cost is paid daily, in teaching time and in trust.", 2)

STATCARD = [
    (0.62, "THE DAILY COST", RED, "10–15 min", "spent on roll-call in a single 40-minute period",
     "Across a 200-day year that is roughly 33 teaching hours per class — close to six full school weeks."),
    (5.02, "THE SCALE", "#B58200", "15 lakh+", "schools in India run attendance the same manual way",
     "A problem this widespread is not a school problem. It is infrastructure — and infrastructure is where SDG 9 lives."),
]
for x, eyebrow, accent, big, label, foot in STATCARD:
    d.rect(x, 2.02, 4.26, 2.62, WHITE, line=BORDER, radius=0.10)
    d.rect(x, 2.02, 4.26, 0.05, accent)
    d.text(x + 0.26, 2.24, 3.6, 0.22, eyebrow, size=8.4, bold=True, color=accent, caps=True, spc=110)
    d.text(x + 0.26, 2.54, 3.7, 0.56, big, size=33, bold=True, color=INK, ls=0.9)
    d.text(x + 0.26, 3.18, 3.66, 0.42, label, size=10.6, color=SLATE, ls=1.12)
    d.line(x + 0.26, 3.80, x + 4.00, 3.80, BORDER, 0.8)
    d.text(x + 0.26, 3.92, 3.70, 0.62, foot, size=9.4, color=GREY, ls=1.18)

d.rect(9.42, 2.02, 3.30, 2.62, INK, radius=0.10)
d.text(9.68, 2.24, 2.8, 0.22, "WHAT WE TARGET", size=8.4, bold=True, color=CYAN, caps=True, spc=110)
d.text(9.68, 2.56, 2.86, 0.70, "One narrow, measurable problem", size=15, bold=True, color=WHITE, ls=1.08)
d.line(9.68, 3.34, 10.78, 3.34, CYAN, 1.4)
d.text(9.68, 3.50, 2.82, 1.02, "Record attendance in seconds, accurately, with the teacher holding final approval.",
       size=10.2, color=MIST, ls=1.24)

d.text(0.62, 4.94, 6.0, 0.22, "WHY IT KEEPS HAPPENING", size=8.6, bold=True, color=CYAN_D, caps=True, spc=110)
why = [("Time", "Minutes evaporate, every period, with nothing to show for them."),
       ("Trust", "Ticks are easy to fake and hard to audit after the register closes."),
       ("Records", "Attendance, alerts and reports live in three separate places.")]
for i, (h, b) in enumerate(why):
    x = 0.62 + i * 4.28
    d.rect(x, 5.24, 4.06, 1.34, WHITE, line=BORDER, radius=0.09)
    d.rect(x + 0.26, 5.46, 0.30, 0.30, CYAN_L, radius=0.06)
    d.text(x + 0.26, 5.50, 0.30, 0.24, "0%d" % (i + 1), size=8.4, bold=True, color=CYAN_D, align="c")
    d.text(x + 0.68, 5.44, 3.1, 0.26, h, size=12, bold=True, color=INK)
    d.text(x + 0.68, 5.74, 3.16, 0.62, b, size=9.8, color=GREY, ls=1.16)
note(
    "SPEAKER NOTES — Slide 2 · Problem · ~45 sec\n\n"
    "Start with the clock. In a 40-minute period, a teacher spends 10 to 15 minutes calling out names. "
    "Multiply that across a 200-day year: roughly 33 teaching hours lost per class — about six full school weeks.\n\n"
    "Now multiply by scale. More than 15 lakh schools in India run attendance manually.\n\n"
    "And it is not only time. Manual ticks are easy to fake and impossible to audit later, and attendance, parent "
    "alerts and reports all sit in separate notebooks. So a parent often learns about an absence at report-card time.\n\n"
    "That is why we deliberately narrowed our target to one measurable problem: record attendance in seconds, "
    "accurately, with the teacher still approving the final register.")

# ================================================================ 03 WHY IT MATTERS
d.add_slide(PAPER)
page_top("Why it matters", "Four people feel this problem. We designed for all four.",
         "Attendance is not paperwork. It is the daily signal that tells a school whether a child is safe.", 3)

people = [
    ("STUDENTS", "No queue, no waiting for a register to circulate. One tap, immediate confirmation on the screen.", CYAN, CYAN_L),
    ("TEACHERS", "Minutes back every period. Only exceptions are flagged — the teacher confirms the register.", GOLD, GOLD_L),
    ("PARENTS", "An automatic email the same morning if their child is late or absent. Not at report-card time.", VIOLET, "#EFEFFE"),
    ("ADMINISTRATORS", "Daily and period-wise reports, exportable registers, and a full correction history.", GREEN, GREEN_L),
]
for i, (h, b, col, coll) in enumerate(people):
    x = 0.62 + i * 3.10
    d.rect(x, 2.02, 2.90, 2.22, WHITE, line=BORDER, radius=0.10)
    d.rect(x, 2.02, 2.90, 0.05, col)
    d.rect(x + 0.24, 2.26, 0.40, 0.40, coll, radius=0.09)
    d.text(x + 0.24, 2.355, 0.40, 0.24, "0%d" % (i + 1), size=9.6, bold=True, color=col, align="c")
    d.text(x + 0.24, 2.82, 2.44, 0.24, h, size=9, bold=True, color=col, caps=True, spc=100)
    d.text(x + 0.24, 3.08, 2.44, 1.00, b, size=10, color=SLATE, ls=1.20)

d.rect(0.62, 4.42, 6.02, 2.36, WHITE, line=BORDER, radius=0.10)
d.text(0.88, 4.60, 5.5, 0.22, "WHAT SUCCESS LOOKS LIKE", size=8.6, bold=True, color=CYAN_D, caps=True, spc=110)
d.text(0.88, 4.86, 5.5, 0.30, "Five numbers, checked in every trial", size=14, bold=True, color=INK)
metrics = ["Time per class of 30", "Duplicate scans blocked", "Missed entries",
           "Corrections after the fact", "Offline-to-online sync accuracy"]
my = 5.26
for i, m in enumerate(metrics):
    yy = my + i * 0.29
    d.oval(0.90, yy + 0.060, 0.10, 0.10, CYAN)
    d.text(1.10, yy, 4.2, 0.24, m, size=9.8, color=SLATE)
for i, m in enumerate(metrics):
    yy = my + i * 0.29
    d.text(4.30, yy, 2.1, 0.24, ["seconds", "blocked", "counted", "counted", "verified"][i],
           size=9.8, bold=True, color=GREEN, align="r")

d.rect(6.84, 4.42, 5.88, 2.36, INK, radius=0.10)
d.text(7.10, 4.62, 5.3, 0.22, "THE POINT OF THE PROJECT", size=8.6, bold=True, color=GOLD, caps=True, spc=110)
d.text(7.10, 4.94, 5.30, 1.34, "Attendance should be a by-product of walking into class — not a task that eats the class.",
       size=15.5, bold=True, color=WHITE, ls=1.14)
d.text(7.10, 6.28, 5.30, 0.32, "More teaching time · fewer errors · parents informed · records trusted",
       size=9.4, bold=True, color=CYAN)
note(
    "SPEAKER NOTES — Slide 3 · Why it matters · ~45 sec\n\n"
    "Four groups feel this problem, and we designed for all four.\n\n"
    "Students stop queuing and get an immediate confirmation on the LCD. Teachers get minutes back every period and "
    "only review exceptions. Parents get an automated email the same morning instead of finding out weeks later. "
    "Administrators get daily and period-wise reports with a complete correction history.\n\n"
    "We hold ourselves to five numbers in every trial: time per class of 30, duplicate scans blocked, missed entries, "
    "corrections after the fact, and offline-to-online sync accuracy. Each one is reported on slide eight.\n\n"
    "The point is simple: attendance should be a by-product of walking into class, not a task that eats the class.")

# ================================================================ 04 SOLUTION
d.add_slide(PAPER)
page_top("Our solution", "One tap. Three layers that make it trustworthy.",
         "A privacy-first RFID terminal with a cloud brain and a self-healing AI layer — no cameras, no face data.", 4)

layers = [
    ("LAYER 01", "Hardware terminal", "Handheld-sized, low-voltage, classroom-ready.",
     ["ESP32 DevKit V1 microcontroller", "RC522 RFID reader — 13.56 MHz cards",
      "LCD1602 I2C display for instant feedback", "3D-printed enclosure designed in Blender"],
     "Arduino C++ · OTA updates", CYAN, CYAN_L),
    ("LAYER 02", "Cloud brain", "Every tap lands on the dashboard in real time.",
     ["Firebase Auth with role-based access", "Realtime Database — live attendance",
      "Firebase Hosting for the web dashboard", "Admin, teacher, student and guardian views"],
     "Parent email alerts · exports", GOLD, GOLD_L),
    ("LAYER 03", "Astro AI 2.0", "The terminal watches itself and recovers alone.",
     ["11 self-healing diagnostic checks", "Wi-Fi, memory, reader and clock health",
      "Automatic recovery before class starts", "Secure over-the-air firmware updates"],
     "Runs continuously · logs every event", GREEN, GREEN_L),
]
for i, (tag_, h, sub, items, foot, col, coll) in enumerate(layers):
    x = 0.62 + i * 4.20
    d.rect(x, 2.02, 3.96, 3.42, WHITE, line=BORDER, radius=0.10)
    d.rect(x, 2.02, 3.96, 0.05, col)
    d.text(x + 0.28, 2.24, 2.0, 0.22, tag_, size=8.2, bold=True, color=col, caps=True, spc=120)
    d.text(x + 0.28, 2.48, 3.4, 0.32, h, size=16.5, bold=True, color=INK)
    d.text(x + 0.28, 2.82, 3.4, 0.42, sub, size=9.6, italic=True, color=GREY, ls=1.1)
    d.line(x + 0.28, 3.28, x + 3.68, 3.28, BORDER, 0.8)
    for j, it in enumerate(items):
        yy = 3.42 + j * 0.37
        d.oval(x + 0.29, yy + 0.085, 0.075, 0.075, col)
        d.text(x + 0.50, yy, 3.2, 0.30, it, size=9.6, color=SLATE)
    d.rect(x + 0.28, 4.94, 3.40, 0.32, coll, radius=0.06)
    d.text(x + 0.28, 5.00, 3.40, 0.24, foot, size=8.2, bold=True, color=col, align="c", spc=40)

d.rect(0.62, 5.62, 12.10, 1.12, INK, radius=0.10)
d.text(0.90, 5.76, 11.6, 0.22, "WHAT THE SYSTEM DOES WITHOUT BEING ASKED", size=8.2, bold=True, color=GOLD, caps=True, spc=110)
facts = ["Works offline, syncs later", "Emails parents automatically", "Tracks daily + period attendance",
         "Blocks duplicate taps", "No face data collected", "₹1,500 per unit"]
for i, f in enumerate(facts):
    col = i % 3
    row = i // 3
    x = 0.90 + col * 3.95
    y = 6.06 + row * 0.31
    d.text(x, y, 0.18, 0.22, "✓", size=9.6, bold=True, color=GREEN)
    d.text(x + 0.22, y, 3.5, 0.24, f, size=9.6, bold=True, color=WHITE)
note(
    "SPEAKER NOTES — Slide 4 · Solution · ~55 sec\n\n"
    "Our solution is three layers, and the design principle behind all three is that the teacher should never have to "
    "do more work than before.\n\n"
    "Layer one is the terminal: an ESP32 DevKit, an RC522 RFID reader, an LCD1602 screen, in a 3D-printed case we "
    "modelled in Blender. Firmware is Arduino C++ and updates over the air.\n\n"
    "Layer two is the cloud brain. Firebase handles login with roles, stores attendance in the realtime database, and "
    "hosts the dashboard. Parents get automatic email alerts for late or absent.\n\n"
    "Layer three is Astro AI 2.0 — eleven self-healing checks covering Wi-Fi, memory, the reader and the clock, so a "
    "terminal that has a problem on Monday morning recovers itself before the first period.\n\n"
    "And the constraint we set ourselves early: no cameras, no face data, nothing sensitive stored. Just a card, a tap "
    "and a record.")

# ================================================================ 05 HOW IT WORKS
d.add_slide(INK, dark=True)
full_bg(INK)
d.rect(0, 0, W, 0.05, CYAN)
d.rect(0.62, 0.44, 0.055, 0.22, GOLD)
d.text(0.80, 0.42, 8.6, 0.26, "Live system flow", size=9.5, bold=True, color=CYAN, caps=True, spc=140)
d.text(0.62, 0.70, 11.4, 0.5, "Tap to present in under two seconds.", size=31, bold=True, color=WHITE, ls=0.95)
d.text(0.62, 1.34, 11.9, 0.34, "Five steps from card to confirmed register. The teacher stays in control at every stage.",
       size=12.5, color=MIST)

steps = [("01", "Student taps", "RFID card is read by the RC522 reader"),
         ("02", "ESP32 verifies", "Checks card UID, class roster and time window"),
         ("03", "LCD confirms", "Present, late, or duplicate blocked on screen"),
         ("04", "Cloud syncs", "Firebase in real time — or the offline queue"),
         ("05", "Register + alert", "Dashboard updates, parent email is sent")]
cx = 0.62
for i, (n, h, b) in enumerate(steps):
    x = cx + i * 2.46
    d.rect(x, 1.96, 2.20, 2.06, "#1A3866", line="#2C5388", lw=0.9, radius=0.10)
    d.text(x + 0.22, 2.14, 0.6, 0.30, n, size=11, bold=True, color=CYAN, spc=60)
    d.text(x + 0.22, 2.52, 1.80, 0.28, h, size=12.5, bold=True, color=WHITE)
    d.text(x + 0.22, 2.84, 1.80, 1.0, b, size=9.4, color=MIST, ls=1.18)
    hh = 0.045
    d.rect(x + 0.22, 3.82, 1.76, hh, CYAN if i < 4 else GREEN, radius=hh / 2)
    if i < 4:
        d.text(x + 2.22, 2.74, 0.22, 0.34, "›", size=20, bold=True, color=GOLD, align="c")

d.rect(0.62, 4.34, 5.96, 2.42, "#152F58", line="#2C5388", lw=0.9, radius=0.10)
d.text(0.88, 4.50, 5.4, 0.22, "TEACHER FLOW  ·  APPROVAL IS BUILT IN", size=8.4, bold=True, color=GOLD, caps=True, spc=100)
tf = ["Open the class session", "Review only flagged exceptions", "Confirm and export the register"]
for i, t_ in enumerate(tf):
    yy = 4.84 + i * 0.36
    d.oval(0.90, yy + 0.075, 0.13, 0.13, GOLD)
    d.text(1.14, yy, 5.0, 0.26, t_, size=10.4, color=WHITE)
d.text(0.88, 6.02, 5.4, 0.60, "Nothing is final until the teacher confirms it — the machine proposes, the teacher decides.",
       size=9.2, italic=True, color=MIST, ls=1.18)

d.rect(6.80, 4.34, 5.92, 2.42, "#152F58", line="#2C5388", lw=0.9, radius=0.10)
d.text(7.06, 4.50, 5.3, 0.22, "OFFLINE MODE  ·  ZERO DATA LOSS", size=8.4, bold=True, color=CYAN, caps=True, spc=100)
d.text(7.06, 4.84, 5.30, 0.86, "No internet? Taps keep recording to local storage in order.",
       size=10.4, color=WHITE, ls=1.2)
d.text(7.06, 5.52, 5.30, 0.90, "When the connection returns, the queue syncs oldest-first with duplicate protection — "
                               "so a day offline is a day delayed, never a day lost.",
       size=9.2, color=MIST, ls=1.2)
d.rect(7.06, 6.34, 1.94, 0.28, "#0F4D66", radius=0.06)
d.text(7.06, 6.395, 1.94, 0.22, "RECONNECTS AUTOMATICALLY", size=7.4, bold=True, color=CYAN, align="c", spc=60)
footer(5, dark=True)
note(
    "SPEAKER NOTES — Slide 5 · How it works · ~55 sec\n\n"
    "Walk the five boxes left to right.\n\n"
    "One: the student taps a card, the RC522 reads its unique ID. Two: the ESP32 checks that ID against the class "
    "roster and against the period's time window. Three: the LCD answers immediately — present, late, or duplicate "
    "blocked. Four: the record goes to Firebase in real time, or into the offline queue. Five: the dashboard updates "
    "and the parent email fires.\n\n"
    "The teacher flow underneath matters as much as the hardware. The teacher opens the session, reviews only the "
    "flagged exceptions, and confirms the register. The machine proposes; the teacher decides. That single design "
    "choice is what makes the record trustworthy.\n\n"
    "And offline: if the internet drops, taps keep recording locally and sync oldest-first on reconnect. A day offline "
    "is a day delayed — never a day lost.")

# ================================================================ 06 DIFFERENTIATION
d.add_slide(PAPER)
page_top("Existing solutions", "Others sell hardware. We fit a classroom.",
         "Four approaches already exist. Each one trades away something that matters in an Indian school.", 6)

cols = ["Approach", "Cost", "Offline", "Teacher approval", "Audit trail", "Privacy"]
rows = [
    ("Biometric fingerprint", "High", "Varies", "No", "Weak", "Stores biometrics"),
    ("RFID-only terminal", "Medium", "Yes", "No", "Basic", "Good"),
    ("QR / phone scan", "Low", "No", "Partial", "Basic", "Needs a phone each"),
    ("Face recognition", "High", "No", "No", "Basic", "Stores face images"),
    ("Astro Smart Attendance", "₹1,500", "Yes, auto-sync", "Yes, built in", "Full history", "No face data"),
]
tx, ty, tw = 0.62, 2.02, 12.10
cw = [2.86, 1.34, 1.66, 1.94, 1.66, 2.64]
rh = 0.62
x = tx
for j, c in enumerate(cols):
    d.rect(x, ty, cw[j], 0.44, INK)
    d.text(x + (0.20 if j == 0 else 0.06), ty + 0.13, cw[j] - 0.32, 0.22, c,
           size=8.6, bold=True, color=WHITE, align="l" if j == 0 else "c", spc=60)
    x += cw[j]
for i, row in enumerate(rows):
    y = ty + 0.44 + i * rh
    last = i == len(rows) - 1
    x = tx
    for j, val in enumerate(row):
        d.rect(x, y, cw[j], rh, "#E7F7FD" if last else (WHITE if i % 2 == 0 else PAPER),
               line=CYAN if last else BORDER, lw=1.1 if last else 0.6)
        if j == 0:
            d.text(x + 0.16, y + (rh - 0.22) / 2, cw[j] - 0.28, 0.22, val,
                   size=9.6, bold=True, color=INK if last else SLATE)
        else:
            good = val in ("₹1,500", "Yes, auto-sync", "Yes, built in", "Full history", "No face data")
            d.text(x + 0.06, y + (rh - 0.22) / 2, cw[j] - 0.12, 0.22, val, size=8.9,
                   bold=last, color=(GREEN if good else SLATE) if last else GREY, align="c")
        x += cw[j]

d.rect(0.62, 5.72, 5.92, 1.02, INK, radius=0.09)
d.text(0.86, 5.88, 5.5, 0.22, "THE COMBINATION IS THE INNOVATION", size=8.2, bold=True, color=GOLD, caps=True, spc=100)
d.text(0.86, 6.14, 5.44, 0.52, "Low cost + offline + self-healing + teacher approval + auditable history — in one unit.",
       size=10, color=WHITE, ls=1.18)
d.rect(6.80, 5.72, 5.92, 1.02, WHITE, line=BORDER, radius=0.09)
d.text(7.04, 5.88, 5.5, 0.22, "WHAT WE DO NOT CLAIM", size=8.2, bold=True, color=CYAN_D, caps=True, spc=100)
d.text(7.04, 6.14, 5.44, 0.52, "That no similar product exists. We claim this combination fits Indian classrooms first.",
       size=10, color=SLATE, ls=1.18)
note(
    "SPEAKER NOTES — Slide 6 · Differentiation · ~50 sec\n\n"
    "We compared ourselves honestly with what is already sold.\n\n"
    "Biometric fingerprint systems are expensive and store children's biometrics. RFID-only terminals are cheaper but "
    "usually skip teacher approval and keep only a basic log. QR and phone-scan systems assume every student has a "
    "phone and internet — an access problem, not an attendance solution. Face recognition is costly and stores face "
    "images of minors.\n\n"
    "The last row is ours: 1,500 rupees, offline with auto-sync, teacher approval built in, full correction history, "
    "and no face data at all.\n\n"
    "Our claim is deliberately narrow. We do not say no similar product exists. We say this combination — affordable, "
    "offline, self-healing, teacher-controlled and auditable — is what an Indian classroom actually needs.")

# ================================================================ 07 PROTOTYPE
d.add_slide(PAPER)
page_top("The build", "A working unit, not a breadboard.",
         "Hardware, firmware and cloud dashboard — assembled, flashed and running on our bench.", 7)

d.rect(0.62, 2.02, 5.34, 4.02, WHITE, line=BORDER, radius=0.10)
d.pic(A("device_crop.png"), 0.72, 2.12, 5.14, 3.52)
d.text(0.72, 5.72, 5.14, 0.24, "TERMINAL  ·  ESP32 + RC522 + LCD1602 in the 3D-printed case", size=7.4,
       bold=True, color=GREY, align="c", spc=50)


d.text(6.24, 2.02, 6.4, 0.22, "BILL OF MATERIALS — ₹1,500 PER UNIT", size=8.4, bold=True, color=CYAN_D, caps=True, spc=100)
bom = [("ESP32 DevKit V1", "controller + Wi-Fi", "₹420"), ("RC522 RFID reader", "13.56 MHz + cards", "₹180"),
       ("LCD1602 I2C", "instant feedback", "₹150"), ("3D-printed enclosure", "Blender, PLA", "₹260"),
       ("Power, wiring, PCB", "5V, low-voltage", "₹190"), ("Cards + assembly", "per-student tags", "₹300")]
for i, (part, use, cost) in enumerate(bom):
    y = 2.30 + i * 0.365
    d.line(6.24, y + 0.325, 12.42, y + 0.325, BORDER, 0.6)
    d.text(6.24, y + 0.04, 2.9, 0.24, part, size=10, bold=True, color=INK)
    d.text(8.40, y + 0.04, 2.6, 0.24, use, size=9.2, color=GREY)
    d.text(11.30, y + 0.04, 1.12, 0.24, cost, size=10, bold=True, color=SLATE, align="r")
d.line(6.24, 2.30 + 6 * 0.365 + 0.02, 12.42, 2.30 + 6 * 0.365 + 0.02, INK, 1.2)
d.text(6.24, 2.30 + 6 * 0.365 + 0.12, 2.9, 0.26, "Total per unit", size=10.6, bold=True, color=INK)
d.text(10.60, 2.30 + 6 * 0.365 + 0.10, 1.82, 0.28, "₹1,500", size=13.5, bold=True, color=GREEN, align="r")

d.rect(6.24, 4.96, 6.18, 1.86, INK, radius=0.10)
d.text(6.48, 5.10, 5.7, 0.22, "SOFTWARE, RUNNING TODAY", size=8.2, bold=True, color=CYAN, caps=True, spc=100)
sw = [("Firebase Auth", "4 roles"), ("Realtime DB", "live"), ("Hosting", "web app"),
      ("Email alerts", "auto"), ("Astro AI 2.0", "11 checks"), ("OTA updates", "secure")]
for i, (k, v) in enumerate(sw):
    col, row = i % 3, i // 3
    x = 6.48 + col * 1.98
    y = 5.44 + row * 0.66
    d.text(x, y, 1.9, 0.22, k, size=9.2, bold=True, color=WHITE)
    d.text(x, y + 0.22, 1.9, 0.22, v, size=8.4, color=GOLD)
note(
    "SPEAKER NOTES — Slide 7 · The build · ~55 sec\n\n"
    "This is the unit itself. On the left: the ESP32, the RC522 reader, the LCD and the 3D-printed case we modelled "
    "in Blender. It is low-voltage and entirely classroom-safe.\n\n"
    "On the right, the bill of materials that gets us to 1,500 rupees: 420 for the controller, 180 for the reader, "
    "150 for the display, 260 for the printed case, 190 for power and wiring, 300 for cards and assembly. That is "
    "roughly 95 percent cheaper than the commercial equivalents on the previous slide.\n\n"
    "Below, the software that is running today: Firebase Auth with four roles, the realtime database, the hosted "
    "dashboard, automatic email alerts, Astro AI 2.0 with its eleven checks, and secure OTA updates.\n\n"
    "The dashboard is live — astro-smart-attendence.web.app — and you are welcome to open it during questions.")

# ================================================================ 08 VALIDATION
d.add_slide(PAPER)
page_top("Validation", "We tested it like engineers, not like salespeople.",
         "Every figure here comes from our own test log and can be re-run on the live demo.", 8)

kpis = [("140 / 140", "feature tests", "all passing", GREEN), ("10,000,000", "stress cases", "logic verified", CYAN_D),
        ("0", "warnings, 0 errors", "final build", GOLD), ("< 2 s", "per student", "tap to record", VIOLET)]
for i, (big, lab, sub, col) in enumerate(kpis):
    x = 0.62 + i * 3.10
    d.rect(x, 2.02, 2.92, 1.48, WHITE, line=BORDER, radius=0.10)
    d.rect(x, 2.02, 2.92, 0.05, col)
    d.text(x + 0.24, 2.24, 2.5, 0.50, big, size=25, bold=True, color=INK, ls=0.92)
    d.text(x + 0.24, 2.78, 2.5, 0.22, lab, size=8.6, bold=True, color=col, caps=True, spc=80)
    d.text(x + 0.24, 3.02, 2.5, 0.22, sub, size=9.2, color=GREY)

d.rect(0.62, 3.72, 7.34, 2.86, WHITE, line=BORDER, radius=0.10)
d.text(0.88, 3.90, 6.9, 0.22, "TEST LOG  ·  WHAT WE ACTUALLY RAN", size=8.4, bold=True, color=CYAN_D, caps=True, spc=100)
tests = [("Class of 30, timed", "Roll-call minutes → seconds"),
         ("Duplicate tap", "Second scan blocked, never double-counted"),
         ("Late / out-of-window tap", "Marked late, routed to teacher review"),
         ("Internet pulled mid-session", "Queued, then synced in order — zero loss"),
         ("Terminal reboot mid-class", "Resumed from last confirmed record"),
         ("Teacher usability pass", "Exception review judged clear and fast")]
for i, (k, v) in enumerate(tests):
    y = 4.20 + i * 0.39
    d.text(0.90, y, 0.18, 0.22, "✓", size=9.6, bold=True, color=GREEN)
    d.text(1.12, y, 2.54, 0.24, k, size=9.4, bold=True, color=INK)
    d.text(3.78, y, 3.94, 0.24, v, size=9.2, color=GREY)

d.rect(8.20, 3.72, 4.52, 2.98, INK, radius=0.10)
d.text(8.46, 3.90, 4.0, 0.22, "SELF-HEALING, MEASURED", size=8.4, bold=True, color=GOLD, caps=True, spc=100)
d.text(8.46, 4.18, 4.0, 0.34, "11 checks", size=20, bold=True, color=WHITE)
d.text(8.46, 4.56, 4.00, 0.24, "running continuously on the terminal", size=9.2, color=MIST)
checks = ["Wi-Fi link and reconnect", "Free memory headroom", "RFID reader response", "Clock and time window",
          "Queue depth and drain", "Firmware integrity"]
for i, c in enumerate(checks):
    y = 4.86 + i * 0.26
    d.oval(8.48, y + 0.070, 0.075, 0.075, CYAN)
    d.text(8.68, y, 3.9, 0.22, c, size=9.0, color=WHITE)
d.text(8.46, 6.50, 4.0, 0.2, "+ 5 more, every event logged with a timestamp", size=7.8, italic=True, color="#8FA6C8")
note(
    "SPEAKER NOTES — Slide 8 · Validation · ~55 sec\n\n"
    "We tested the way engineers test, not the way salespeople demo.\n\n"
    "The final build passes 140 of 140 feature tests with zero warnings and zero errors. We ran ten million stress "
    "cases against the attendance logic — duplicate handling, time-window checks, and queue ordering — and the "
    "measured tap-to-record time is under two seconds per student.\n\n"
    "The log on the left is the list we hold ourselves to. A class of 30, timed. A duplicate tap, blocked. A late tap, "
    "routed for review. Internet pulled mid-session: queued, then synced in order with zero loss. A reboot mid-class: "
    "it resumes from the last confirmed record. And a teacher usability pass, because a system teachers do not trust "
    "is worthless.\n\n"
    "Astro AI 2.0's eleven checks run continuously, monitoring Wi-Fi, memory, the reader, the clock, queue depth and "
    "firmware integrity — and logging every event.")

# ================================================================ 09 RISKS
d.add_slide(PAPER)
page_top("Responsible innovation", "We name the risks before judges do.",
         "Every system has a failure mode. Here are ours, and the safeguard built against each one.", 9)

risks = [("RISK 01", "A card can be shared",
          "A student could hand their card to a friend and be marked present while absent.",
          "Duplicate and time-window checks flag the pattern. Every register is teacher-confirmed, and every "
          "correction stays in the audit history.", CYAN_D, CYAN_L),
         ("RISK 02", "Networks and phones are not equal",
          "Not every family has a smartphone, and school internet drops without warning.",
          "The card needs no phone at all. The terminal records offline and syncs on reconnect, with a manual "
          "entry path so no student is ever excluded.", GOLD, GOLD_L),
         ("RISK 03", "Children's data is sensitive",
          "Biometrics and face images create real, permanent risk if they leak.",
          "No camera and no face data. We store the minimum: card ID, timestamp, status. Access is role-based and "
          "the build is low-voltage and adult-supervised.", GREEN, GREEN_L)]
for i, (num, h, risk, fix, col, coll) in enumerate(risks):
    x = 0.62 + i * 4.20
    d.rect(x, 2.02, 3.96, 3.44, WHITE, line=BORDER, radius=0.10)
    d.rect(x, 2.02, 0.05, 3.44, col)
    d.text(x + 0.28, 2.22, 2.4, 0.22, num, size=8.2, bold=True, color=col, caps=True, spc=120)
    hsize = 14.5
    for _ in range(30):
        if d.measure(h, hsize, True, False, 3.40)[0] <= 1:
            break
        hsize -= 0.5
    nlines, hth = d.measure(h, hsize, True, False, 3.40, 1.06)
    d.text(x + 0.28, 2.46, 3.40, hth + 0.02, h, size=hsize, bold=True, color=INK, ls=1.06)
    y_risk = 2.46 + hth + 0.12
    d.text(x + 0.28, y_risk, 3.42, 0.80, risk, size=9.6, color=GREY, ls=1.18)
    d.line(x + 0.28, 3.80, x + 3.70, 3.80, BORDER, 0.8)
    d.rect(x + 0.28, 3.92, 1.28, 0.24, coll, radius=0.05)
    d.text(x + 0.28, 3.965, 1.28, 0.20, "SAFEGUARD", size=7.2, bold=True, color=col, align="c", spc=80)
    d.text(x + 0.28, 4.26, 3.42, 1.32, fix, size=9.4, color=SLATE, ls=1.20)

d.rect(0.62, 5.78, 12.10, 0.92, INK, radius=0.09)
d.text(0.88, 5.92, 11.6, 0.22, "OUR STANDING RULE", size=8.2, bold=True, color=GOLD, caps=True, spc=110)
d.text(0.88, 6.18, 11.6, 0.36, "The system records attendance. It never replaces teacher judgement — every register "
                               "is confirmed by a human.",
       size=10.6, bold=True, color=WHITE)
note(
    "SPEAKER NOTES — Slide 9 · Responsible innovation · ~50 sec\n\n"
    "Responsible innovation means naming the risks ourselves.\n\n"
    "Risk one: a card can be shared. Our answer is not that it cannot happen — it is that duplicate and time-window "
    "checks flag the pattern, the register is teacher-confirmed, and every correction is preserved in the audit "
    "history.\n\n"
    "Risk two: inequality. Some families have no smartphone, and school internet fails. So the card needs no phone, "
    "the terminal records offline, and a manual-entry path exists. No student is excluded by our design.\n\n"
    "Risk three: children's data. No camera, no face images, no biometrics. We store the minimum — card ID, "
    "timestamp, status — behind role-based access, on a low-voltage build supervised by our mentor.\n\n"
    "Our standing rule is on the bar below: this system records attendance. It never replaces teacher judgement.")

# ================================================================ 10 NEXT STEPS
d.add_slide(PAPER)
page_top("What happens next", "From one classroom to every classroom.",
         "The prototype is done. The next phase is measured, honest deployment.", 10)

phases = [("NOW", "Working prototype", "Hardware, cloud and AI layer built and tested", GREEN, True),
          ("TERM 1", "Pilot at ABPS Renukoot", "One grade, one term, timed against manual registers", CYAN_D, False),
          ("TERM 2", "Evidence pack", "Cost, time saved and error rates published internally", GOLD, False),
          ("YEAR 2", "Scale within the network", "Aditya Birla schools first, then partner schools", VIOLET, False)]
d.line(0.66, 2.36, 12.62, 2.36, BORDER, 1.4)
for i, (when, h, b, col, done) in enumerate(phases):
    x = 0.62 + i * 3.04
    d.oval(x + 0.02, 2.24, 0.24, 0.24, col)
    if not done:
        d.oval(x + 0.065, 2.285, 0.15, 0.15, PAPER)
    d.text(x, 2.66, 2.6, 0.22, when, size=8.4, bold=True, color=col, caps=True, spc=110)
    d.text(x, 2.90, 2.72, 0.56, h, size=13.5, bold=True, color=INK, ls=1.08)
    d.text(x, 3.52, 2.76, 0.80, b, size=9.6, color=GREY, ls=1.16)

d.rect(0.62, 4.64, 7.42, 2.06, WHITE, line=BORDER, radius=0.10)
d.text(0.88, 4.82, 6.9, 0.22, "WHAT WE ASK FOR", size=8.4, bold=True, color=CYAN_D, caps=True, spc=110)
asks = [("Ten minutes with a teacher", "to watch a live period and time it"),
        ("One class for one term", "to measure against the existing register"),
        ("Feedback, not applause", "we would rather fix a flaw than hear praise")]
for i, (k, v) in enumerate(asks):
    y = 5.14 + i * 0.48
    d.oval(0.90, y + 0.085, 0.10, 0.10, CYAN_D)
    d.text(1.12, y, 2.86, 0.24, k, size=9.8, bold=True, color=INK)
    d.text(4.02, y, 3.80, 0.24, v, size=9.4, color=GREY)

d.rect(8.28, 4.64, 4.44, 2.06, INK, radius=0.10)
d.text(8.52, 4.82, 4.0, 0.22, "TRY IT YOURSELF", size=8.4, bold=True, color=GOLD, caps=True, spc=110)
d.text(8.52, 5.10, 3.96, 0.30, "astro-smart-attendence.web.app", size=11.2, bold=True, color=CYAN)
d.text(8.52, 5.46, 3.96, 0.66, "Live dashboard with demo data — admin, teacher and guardian views, open to you now.",
       size=9.2, color=MIST, ls=1.2)
d.text(8.52, 6.30, 3.96, 0.24, "Team Sun Rises India  ·  Mentor: Dr. Jayesh Shinde", size=8.2, bold=True, color=LGREY)

note(
    "SPEAKER NOTES — Slide 10 · What happens next · ~45 sec\n\n"
    "We are not asking you to believe a promise. The prototype is finished and running — that is the first milestone, "
    "already ticked.\n\n"
    "Next: a pilot at our own school, one grade for one term, timed against the manual registers so the comparison is "
    "honest. Then an evidence pack — cost, time saved, error rate — before we ask any other school to adopt it. After "
    "that, scale within the Aditya Birla network and then to partner schools.\n\n"
    "What we ask of you today is modest: ten minutes with a teacher to watch a live period, one class for one term, "
    "and feedback rather than applause. We would rather fix a flaw now than discover it in a hundred classrooms.\n\n"
    "The dashboard is open — astro-smart-attendence.web.app. Please try it, and then ask us anything.")

# ================================================================ 11 EVIDENCE / DEMO
d.add_slide(PAPER)
page_top("Live demonstration", "This is the dashboard, right now.",
         "Four role-based views on a hosted web app. Every number below is generated by the same database the terminal writes to.", 11)

d.rect(0.62, 2.02, 7.46, 4.32, "#0C1729", line="#22406B", lw=1.0, radius=0.10)
# browser chrome
d.rect(0.62, 2.02, 7.46, 0.34, "#132444", radius=0.0)
d.oval(0.78, 2.13, 0.10, 0.10, "#3B5170")
d.oval(0.94, 2.13, 0.10, 0.10, "#3B5170")
d.oval(1.10, 2.13, 0.10, 0.10, "#3B5170")
d.rect(1.40, 2.10, 3.30, 0.19, "#1B2E4F", radius=0.05)
d.text(1.40, 2.135, 3.30, 0.16, "astro-smart-attendence.web.app", size=6.6, color=MIST, align="c")
# app header
d.text(0.86, 2.52, 2.2, 0.20, "ASTRO  SMART  ATTENDANCE", size=7.0, bold=True, color=CYAN, spc=30)
d.text(0.86, 2.72, 3.2, 0.20, "Grade 9-A  ·  Period 2  ·  Tue 24 Nov", size=7.2, color=MIST)
d.rect(6.30, 2.54, 1.62, 0.30, "#123B52", radius=0.06)
d.oval(6.40, 2.635, 0.09, 0.09, GREEN)
d.text(6.55, 2.585, 1.36, 0.20, "LIVE  ·  SYNCED", size=6.4, bold=True, color=GREEN, spc=40)
# kpi row
kk = [("42/46", "present", GREEN), ("3", "late", GOLD), ("1", "absent", RED), ("98.4%", "sync", CYAN)]
for i, (v, k, col) in enumerate(kk):
    x = 0.86 + i * 1.78
    d.rect(x, 3.02, 1.64, 0.66, "#132444", radius=0.06)
    d.text(x + 0.12, 3.11, 1.4, 0.28, v, size=13, bold=True, color=col)
    d.text(x + 0.12, 3.40, 1.4, 0.18, k.upper(), size=5.8, bold=True, color=GREY, spc=60)
# table
d.text(0.86, 3.84, 1.60, 0.20, "PERIOD REGISTER", size=6.6, bold=True, color=WHITE, spc=50)
d.text(2.62, 3.84, 2.20, 0.20, "STUDENT", size=6.2, bold=True, color=GREY, spc=40)
d.text(4.94, 3.84, 0.80, 0.20, "TIME", size=6.2, bold=True, color=GREY, spc=40)
d.text(6.30, 3.84, 1.60, 0.20, "STATUS", size=6.2, bold=True, color=GREY, spc=40)
d.line(0.86, 4.02, 7.86, 4.02, "#22406B", 0.8)
pupils = [("09-A-001", "Aarav Sharma", "08:12", "Present", GREEN), ("09-A-002", "Ananya Verma", "08:12", "Present", GREEN),
          ("09-A-003", "Kabir Nair", "08:19", "Late", GOLD), ("09-A-004", "Diya Patel", "—", "Absent", RED),
          ("09-A-005", "Ishaan Rao", "08:13", "Present", GREEN), ("09-A-006", "Meera Joshi", "08:13", "Present", GREEN)]
for i, (sid_, name, tm, st, col) in enumerate(pupils):
    y = 4.12 + i * 0.31
    if i % 2 == 0:
        d.rect(0.86, y - 0.02, 7.00, 0.29, "#111F36", radius=0.03)
    d.text(0.92, y + 0.01, 1.6, 0.20, sid_, size=6.6, color=GREY)
    d.text(2.62, y + 0.01, 2.3, 0.20, name, size=7.0, color=WHITE)
    d.text(4.94, y + 0.01, 0.90, 0.20, tm, size=6.8, color=MIST)
    d.rect(6.30, y - 0.01, 0.86, 0.22, "#0E3A2E" if col == GREEN else ("#3A2F10" if col == GOLD else "#3A1618"), radius=0.04)
    d.text(6.30, y + 0.02, 0.86, 0.18, st, size=6.0, bold=True, color=col, align="c", spc=30)
d.text(0.86, 6.02, 7.0, 0.22, "Live view · demo dataset · reflects the same records the terminal writes", size=6.6, italic=True, color=GREY)

views = [("ADMIN", "Whole-school attendance, exports, correction history", CYAN_D),
         ("TEACHER", "Open session, review exceptions, confirm register", GOLD),
         ("STUDENT", "Personal attendance record and percentage", VIOLET),
         ("GUARDIAN", "Child's status and automatic email alerts", GREEN)]
d.text(8.32, 2.02, 4.4, 0.22, "FOUR VIEWS, ONE DATABASE", size=8.4, bold=True, color=CYAN_D, caps=True, spc=100)
for i, (role, desc, col) in enumerate(views):
    y = 2.32 + i * 1.02
    d.rect(8.32, y, 4.40, 0.88, WHITE, line=BORDER, radius=0.08)
    d.rect(8.32, y, 0.05, 0.88, col)
    d.text(8.56, y + 0.14, 3.9, 0.22, role, size=9.0, bold=True, color=col, caps=True, spc=110)
    d.text(8.56, y + 0.40, 3.94, 0.40, desc, size=9.2, color=SLATE, ls=1.14)
d.text(8.32, 6.42, 4.4, 0.22, "Open now: astro-smart-attendence.web.app", size=8.6, bold=True, color=INK)
note(
    "SPEAKER NOTES — Slide 11 · Live demonstration · ~60 sec\n\n"
    "This is the dashboard itself, running on Firebase Hosting, and I am happy to open it on the projector.\n\n"
    "The top strip is a real period view: 42 present, 3 late, 1 absent, and a sync indicator. The register underneath "
    "shows exactly what a teacher sees — a card ID, a name, the tap time, and a status colour. Notice the late entry "
    "and the absent row: those are the exceptions the teacher reviews before confirming, not silent automatic marks.\n\n"
    "On the right are the four roles we build for. Admin sees the whole school and can export. Teacher opens the "
    "session and confirms the register. Student sees their own record and percentage. Guardian sees their child's "
    "status and receives the automatic email if it is late or absent.\n\n"
    "It is live right now at astro-smart-attendence.web.app — please open it on your own phone while I finish.")

# ================================================================ 12 UNIT ECONOMICS
d.add_slide(PAPER)
page_top("Economics", "₹1,500 is not a guess. It is a bill of materials.",
         "Costed part by part, and compared against what schools pay for the alternatives.", 12)

d.text(0.62, 2.02, 6.0, 0.22, "COST TO BUILD ONE UNIT", size=8.4, bold=True, color=CYAN_D, caps=True, spc=100)
bars = [("ESP32 DevKit V1", 420, CYAN_D), ("3D-printed enclosure", 260, CYAN_D), ("RC522 RFID reader", 180, GOLD),
        ("Power, wiring, PCB", 190, CYAN_D), ("LCD1602 I2C display", 150, CYAN_D), ("Cards + assembly", 300, GOLD)]
maxv = float(max(v for _, v, _ in bars))
for i, (part, v, col) in enumerate(bars):
    y = 2.34 + i * 0.44
    d.text(0.62, y, 2.30, 0.22, part, size=9.4, bold=True, color=INK)
    d.rect(2.96, y + 0.035, 3.94 * v / maxv, 0.17, col, radius=0.085)
    d.text(7.06, y, 0.9, 0.22, "₹%d" % v, size=9.4, bold=True, color=SLATE, align="r")
d.line(0.62, 4.94, 7.96, 4.94, INK, 1.2)
d.text(0.62, 5.04, 2.9, 0.26, "Total per unit", size=10.6, bold=True, color=INK)
d.text(5.68, 5.02, 2.28, 0.30, "₹1,500", size=16, bold=True, color=GREEN, align="r")
d.text(0.62, 5.40, 7.4, 0.50, "At this cost, a school can equip a 30-student classroom for about ₹45,000 — "
                              "less than most single-device commercial installations.",
       size=9.8, color=GREY, ls=1.2)

d.rect(8.36, 2.02, 4.36, 3.10, INK, radius=0.10)
d.text(8.60, 2.20, 3.9, 0.22, "WHAT A SCHOOL PAYS TODAY", size=8.2, bold=True, color=GOLD, caps=True, spc=100)
comps = [("Biometric lab setup", "₹40,000 +"), ("Face-recognition system", "₹60,000 +"),
         ("RFID terminal, commercial", "₹18,000 +"), ("Astro Smart Attendance", "₹1,500")]
for i, (k, v) in enumerate(comps):
    y = 2.50 + i * 0.545
    last = i == 3
    if last:
        d.rect(8.60, y - 0.04, 3.88, 0.48, "#14345A", radius=0.06)
    d.text(8.72, y + 0.06, 2.5, 0.24, k, size=9.4, bold=(last), color=WHITE if last else MIST)
    d.text(11.10, y + 0.04, 1.32, 0.26, v, size=10.4 if last else 9.6, bold=True,
           color=GREEN if last else LGREY, align="r")
d.text(8.60, 4.72, 3.9, 0.22, "Indicative market ranges, 2025–26.", size=7.4, italic=True, color="#8FA6C8")

d.rect(0.62, 5.92, 12.10, 0.82, WHITE, line=BORDER, radius=0.09)
d.text(0.86, 6.06, 11.6, 0.26, "Where the money goes — and where it does not", size=9.0, bold=True, color=CYAN_D, caps=True, spc=90)
d.text(0.86, 6.32, 11.6, 0.28, "No cloud lock-in fees, no per-student licence, no proprietary camera hardware. Firebase's free tier "
                               "covers a single school; the terminal is the only real cost.",
       size=9.4, color=SLATE)
note(
    "SPEAKER NOTES — Slide 12 · Economics · ~45 sec\n\n"
    "1,500 rupees is often the first question, so here is the arithmetic behind it.\n\n"
    "420 for the ESP32, 260 for the printed case, 180 for the RFID reader, 190 for power and wiring, 150 for the "
    "display, and 300 for cards and assembly. That totals 1,500 — which means a 30-student classroom costs about "
    "45,000 rupees to equip, less than most single-device commercial installs.\n\n"
    "Compare that with what schools pay today: biometric lab setups start around 40,000, face recognition around "
    "60,000, and commercial RFID terminals around 18,000 each.\n\n"
    "And there is no per-student licence. Firebase's free tier comfortably covers a single school, so the terminal is "
    "the only real recurring-free cost. That is what makes scale realistic rather than aspirational.")

# ================================================================ 13 TEAM
d.add_slide(INK, dark=True)
full_bg(INK)
d.oval(9.6, -1.9, 6.0, 6.0, "#17335F")
d.oval(-1.8, 3.9, 4.6, 4.6, "#142C50")
d.rect(0, 0, W, 0.05, CYAN)
d.rect(0.62, 0.52, 0.055, 0.22, GOLD)
d.text(0.80, 0.50, 8.6, 0.26, "The team", size=9.5, bold=True, color=CYAN, caps=True, spc=140)
d.text(0.62, 0.78, 10.4, 0.52, "Five people, one classroom problem.", size=31, bold=True, color=WHITE, ls=0.95)
d.text(0.62, 1.42, 10.6, 0.34, "Every part of this build — firmware, circuit, enclosure, cloud, testing and this deck — was made by the team.",
       size=12, color=MIST)

team = [("Shaurya Gupta", "Team captain", "Firmware and cloud", CYAN),
        ("Anant Tiwari", "Ideation lead", "User research and problem framing", GOLD),
        ("Devansh Dhakad", "Quality lead", "Test log, documentation, presentation", RED),
        ("Tejas Upadhyay", "Hardware lead", "Circuit assembly and integration testing", VIOLET),
        ("Diwakar Singh", "Product design", "3D enclosure and industrial design", GREEN)]
for i, (name, role, what, col) in enumerate(team):
    x = 0.62 + i * 2.46
    d.rect(x, 2.20, 2.26, 2.02, "#17335F", line="#2C5388", lw=0.9, radius=0.10)
    d.rect(x, 2.20, 2.26, 0.05, col)
    d.oval(x + 0.22, 2.40, 0.44, 0.44, col)
    d.oval(x + 0.255, 2.435, 0.37, 0.37, "#0E2547")
    d.text(x + 0.22, 2.505, 0.44, 0.24, (name.split()[0][0] + name.split()[-1][0]), size=9.6, bold=True,
           color=WHITE, align="c")
    d.text(x + 0.22, 2.98, 1.96, 0.26, name, size=11, bold=True, color=WHITE)
    d.text(x + 0.22, 3.26, 1.90, 0.22, role, size=7.6, bold=True, color=col, caps=True, spc=80)
    d.text(x + 0.22, 3.54, 1.90, 0.92, what, size=8.8, color=MIST, ls=1.18)

d.rect(0.62, 4.56, 7.62, 1.34, "#17335F", line="#2C5388", lw=0.9, radius=0.10)
d.text(0.88, 4.72, 6.9, 0.22, "MENTOR AND GUIDANCE", size=8.2, bold=True, color=GOLD, caps=True, spc=110)
d.text(0.88, 4.98, 6.9, 0.30, "Dr. Jayesh Shinde", size=15, bold=True, color=WHITE)
d.text(0.88, 5.34, 6.9, 0.46, "The Aditya Birla Public School, Renukoot — supervision, electrical safety and honest feedback "
                             "at every stage.", size=9.4, color=MIST, ls=1.16)

d.rect(8.42, 4.56, 4.30, 1.34, "#17335F", line="#2C5388", lw=0.9, radius=0.10)
d.text(8.66, 4.72, 3.8, 0.22, "WHERE WE ARE FROM", size=8.2, bold=True, color=CYAN, caps=True, spc=110)
d.text(8.66, 4.98, 3.8, 0.30, "Renukoot, Sonbhadra", size=15, bold=True, color=WHITE)
d.text(8.66, 5.34, 3.84, 0.46, "Uttar Pradesh, India — built for our own school first, and for every school like it.",
       size=9.4, color=MIST, ls=1.16)

d.text(0.62, 6.34, 8.4, 0.26, "TEAM SUN RISES INDIA  ·  ABPS RENUKOOT  ·  ABG STEM QUEST 2026–27", size=8.2,
       bold=True, color=LGREY, spc=90)
d.text(W - 3.5, 6.34, 2.9, 0.26, "13 / %d" % TOTAL, size=8.2, bold=True, color=LGREY, align="r", spc=90)
note(
    "SPEAKER NOTES — Slide 13 · The team · ~35 sec\n\n"
    "Five of us, and every part of the build was ours.\n\n"
    "I am Shaurya, and I wrote the firmware and the cloud integration. Anant led ideation and user research, which is "
    "how we narrowed the problem to roll-call. Tejas assembled and tested the circuit. Diwakar designed the 3D "
    "enclosure. Devansh kept the test log, the documentation and this presentation honest.\n\n"
    "Dr. Jayesh Shinde mentored us throughout — supervision, electrical safety and, most usefully, honest feedback "
    "when something did not work.\n\n"
    "We are from Renukoot in Sonbhadra. We built this for our own school first, and for every school like it.")

# ================================================================ 14 CLOSE
d.add_slide(INK, dark=True)
full_bg(INK)
d.oval(-2.4, -2.6, 7.2, 7.2, "#16325C")
d.oval(9.4, 3.4, 6.4, 6.4, "#17345E")
d.rect(0, 0, W, 0.05, GOLD)
d.text(0.62, 0.86, 6.0, 0.24, "IN CLOSING", size=9, bold=True, color=CYAN, caps=True, spc=160)
d.text(0.62, 1.16, 10.4, 1.86, "We did not describe a\nproduct. We built one.",
       size=42, bold=True, color=WHITE, ls=1.06)
d.line(0.66, 3.14, 1.90, 3.14, CYAN, 2.2)
d.text(0.66, 3.34, 8.9, 0.90,
       "A working terminal, a live cloud dashboard, an eleven-check AI layer and a test log that says 140 of 140 — "
       "built in Renukoot, by five students, for ₹1,500 a unit.",
       size=12.6, color=MIST, ls=1.24)

d.rect(0.62, 4.52, 4.60, 0.94, "#17345E", line="#2C5388", lw=0.9, radius=0.09)
d.text(0.86, 4.64, 4.1, 0.22, "LIVE DEMO", size=7.8, bold=True, color=GOLD, caps=True, spc=110)
d.text(0.86, 4.88, 4.14, 0.24, "astro-smart-attendence.web.app", size=10.6, bold=True, color=CYAN)
d.rect(5.38, 4.52, 3.68, 0.94, "#17345E", line="#2C5388", lw=0.9, radius=0.09)
d.text(5.62, 4.64, 3.2, 0.22, "THE ASK", size=7.8, bold=True, color=GOLD, caps=True, spc=110)
d.text(5.62, 4.88, 3.26, 0.44, "One class, one term, measured.", size=10.6, bold=True, color=WHITE)
d.rect(9.22, 4.52, 3.50, 0.94, "#17345E", line="#2C5388", lw=0.9, radius=0.09)
d.text(9.46, 4.64, 3.0, 0.22, "COST", size=7.8, bold=True, color=GOLD, caps=True, spc=110)
d.text(9.46, 4.88, 3.04, 0.44, "₹1,500 per unit, billed once.", size=10.6, bold=True, color=WHITE)

d.text(0.62, 5.66, 8.0, 0.74, "Thank you.", size=40, bold=True, color=WHITE, ls=0.95)
d.text(0.66, 6.52, 8.6, 0.24, "QUESTIONS WELCOME  ·  TEAM SUN RISES INDIA  ·  MADE IN RENUKOOT, INDIA",
       size=8.0, bold=True, color=LGREY, spc=110)
d.text(W - 2.2, 6.52, 1.58, 0.24, "14 / %d" % TOTAL, size=8.0, bold=True, color=LGREY, align="r", spc=90)
note(
    "SPEAKER NOTES — Slide 14 · Close · ~35 sec\n\n"
    "I will end where we started, but with evidence rather than intent.\n\n"
    "We did not describe a product — we built one. A working ESP32 terminal. A live cloud dashboard you can open on "
    "your phone. An eleven-check self-healing layer. And a test log that says 140 of 140, with zero warnings and zero "
    "errors.\n\n"
    "Five students in Renukoot built it for 1,500 rupees a unit.\n\n"
    "What we ask for is one class, for one term, measured honestly against the register that exists today. If the "
    "numbers hold, we scale. If they do not, we will tell you exactly where they did not.\n\n"
    "Thank you — Team Sun Rises India. We are happy to take your questions.")

# ---------------------------------------------------------------- output
out = "Astro_Smart_Attendance_Team_Sun_Rises_India.pptx"
d.save(out, "deck.json")
print("saved", out, "slides:", len(d.slides))
if d.warnings:
    print("\nLAYOUT WARNINGS (%d):" % len(d.warnings))
    for w in d.warnings:
        print("  ", w)
else:
    print("no layout warnings")
