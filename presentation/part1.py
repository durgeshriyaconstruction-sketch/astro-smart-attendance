"""
ASTRO SMART ATTENDANCE - deck part 1: slides 1-20.
The story half: the system, the electronics, the cloud, and the CAD pipeline.
"""
from deck_lib import *   # noqa


# =============================================================  01  TITLE
def s01_title(prs, i, n):
    s = slide_new(prs)
    # faint grid, top-right glow bar
    grid_texture(s, RGBColor(0x15, 0x18, 0x1F), 0.5)
    rect(s, 0, 0, 0.16, SH, fill=AMBER)

    text(s, 1.05, 0.78, 7.2, 0.3,
         "Team Sun Rises India  ·  The Aditya Birla Public School, Renukoot  ·  Class 9",
         size=10, color=AMBER, bold=True, caps=True, spc=200)
    text(s, 1.05, 1.28, 7.6, 1.9, "Astro Smart\nAttendance", size=58, color=WHITE,
         bold=True, line=0.98)
    rect(s, 1.07, 3.42, 1.5, 0.05, fill=CYAN)
    text(s, 1.05, 3.66, 6.95, 1.0,
         "A ₹1,500 RFID + fingerprint terminal that marks attendance\nwithout internet, heals itself when a sensor fails,\nand screws to a classroom wall.",
         size=13.5, color=SOFT, line=1.46)

    # four technology pills
    x = 1.05
    for label, col in [("ESP32", CYAN), ("RC522 13.56 MHz", GREEN),
                       ("R307 optical", MAGENTA), ("Firebase cloud", AMBER)]:
        w = 0.42 + len(label) * 0.098
        pill(s, x, 4.92, w, 0.34, label, fill=PANEL, color=col, size=9, line=LINE)
        x += w + 0.12

    text(s, 1.05, 5.66, 7.2, 0.34, "STEM 2026-27  ·  Kreativity League  ·  Sonbhadra, Uttar Pradesh, India",
         size=10, color=FAINT)

    # hero render
    fig_light(s, A("hero_iso"), 8.72, 1.30, 3.88, 3.42)
    text(s, 8.72, 4.86, 3.88, 0.5,
         "The shipped enclosure, v3.6 — 110 × 155 × 46 mm,\nfour printed parts, 22 screws",
         size=9, color=DIM, line=1.35, align=PP_ALIGN.CENTER)

    footer(s, i, n, "Astro Smart Attendance — the technology")
    notes(s, """
OPEN WITH THIS (45 s).
"Indian schools lose 10 to 15 minutes of teaching in every single period to roll call,
and the register, the parent and the report card never talk to each other. We built a
box that costs fifteen hundred rupees, mounts on the wall, and does it with a tap of a
card or a thumb - with no internet needed at the moment of scanning."

Say what the deck is: it is the technology behind the product, and every number in it
can be reproduced from the repository.
""")
    return s


# =============================================================  02  HOW TO USE
def s02_howto(prs, i, n):
    s = slide_new(prs)
    header(s, "How to use this deck", "Three parts, one argument",
           "Read it straight through, or jump to the part the jury is asking about. "
           "Every slide carries speaker notes and says which file produced its numbers.")

    parts = [
        ("01", "THE SYSTEM", CYAN, "Slides 3–13",
         "What it does, what is inside, how a tap becomes a parent's email. Hardware choices "
         "explained against the alternatives they beat."),
        ("02", "THE ENGINEERING", AMBER, "Slides 14–25",
         "The part no other school team has: a parametric CAD model, four independent checkers, "
         "and a physics audit that argues with the model until it gives up."),
        ("03", "THE EVIDENCE", GREEN, "Slides 26–39",
         "Reproduce it, break it, find every risk we know about, and see where each file lives."),
    ]
    x, w, gap = ML, 3.86, 0.20
    for num, head, col, range_, body in parts:
        rect(s, x, 2.14, w, 3.28, fill=PANEL, line=LINE, lw=0.75, radius=0.04)
        rect(s, x, 2.14, w, 0.045, fill=col)
        text(s, x + 0.30, 2.44, 1.0, 0.5, num, size=34, color=col, bold=True, line=1.0)
        text(s, x + 0.30, 3.05, w - 0.6, 0.3, head, size=13, color=WHITE, bold=True, spc=90)
        text(s, x + 0.30, 3.38, w - 0.6, 0.25, range_, size=9.5, color=col, bold=True)
        text(s, x + 0.30, 3.76, w - 0.6, 1.5, body, size=10.5, color=SOFT, line=1.42)
        x += w + gap

    rect(s, ML, 5.66, CW, 1.06, fill=PANEL2, line=LINE, lw=0.75, radius=0.05)
    text(s, ML + 0.30, 5.80, CW - 0.6, 0.26,
         "If you have only three minutes", size=10, color=AMBER, bold=True, caps=True, spc=160)
    text(s, ML + 0.30, 6.06, CW - 0.6, 0.30,
         "3  →  4  →  5  →  7  →  14  →  17  →  19  →  30",
         size=14, color=CYAN, bold=True, font=MONO)
    text(s, ML + 0.30, 6.38, CW - 0.6, 0.30,
         "system · stack · problem · RFID · CAD method · the four checkers · the RFID fix · the results — "
         "the spine of the 7-minute zonal video.",
         size=9, color=SOFT, line=1.25)

    footer(s, i, n, "How to use this deck")
    notes(s, "Point at the three parts, then tell them which three slides to watch if they are short of time.")
    return s


# =============================================================  03  SYSTEM MAP
def s03_system(prs, i, n):
    s = slide_new(prs)
    header(s, "System architecture", "Six layers between a thumb and a report card")

    def node(x, y, w, h, num, head, sub, col, dashed=False):
        rect(s, x, y, w, h, fill=PANEL, line=col, lw=1.1, radius=0.05)
        text(s, x + 0.14, y + 0.10, 0.4, 0.22, num, size=8.5, color=col, bold=True, spc=100)
        hs = fit_size(head, 10.5, w - 0.28, min_size=8.5)
        text(s, x + 0.14, y + 0.34, w - 0.28, 0.34, head, size=hs, color=WHITE,
             bold=True, line=1.10)
        text(s, x + 0.14, y + 0.74, w - 0.28, h - 0.80, sub, size=8.2, color=DIM, line=1.22)

    # row 1 - the terminal
    y1, h1 = 1.94, 1.40
    node(ML, y1, 2.18, h1, "①", "Card or finger", "MIFARE / ISO 14443A card or a registered thumb", CYAN)
    arrow(s, ML + 2.24, y1 + 0.62, 0.34, color=FAINT)
    node(ML + 2.64, y1, 2.52, h1, "②", "RC522 + R307", "13.56 MHz reader and optical fingerprint, both 3.3 V", GREEN)
    arrow(s, ML + 5.22, y1 + 0.62, 0.34, color=FAINT)
    node(ML + 5.62, y1, 2.72, h1, "③", "ESP32 DevKit V1", "Dual core 240 MHz, Wi-Fi, every module on its own bus", AMBER)
    arrow(s, ML + 8.40, y1 + 0.62, 0.34, color=FAINT)
    node(ML + 8.80, y1, 3.28, h1, "④", "Local proof", "LCD confirms, buzzer sounds, record queued in flash", MAGENTA)

    # row 2 - the cloud
    y2, h2 = 3.80, 1.36
    node(ML, y2, 2.62, h2, "⑤", "Offline queue", "Every scan survives a power cut or a dead router", CYAN)
    arrow(s, ML + 2.68, y2 + 0.60, 0.34, color=FAINT)
    node(ML + 3.08, y2, 2.86, h2, "⑥", "Firebase", "Auth · Realtime DB · Hosting, all HTTPS", AMBER)
    arrow(s, ML + 6.00, y2 + 0.60, 0.34, color=FAINT)
    node(ML + 6.40, y2, 2.72, h2, "⑦", "Dashboards", "Admin, student and guardian views, live", GREEN)
    arrow(s, ML + 9.18, y2 + 0.60, 0.34, color=FAINT)
    node(ML + 9.58, y2, 2.50, h2, "⑧", "Parent alert", "Automatic email on a late or absent mark", MAGENTA)

    # the two feedback arrows
    vline(s, ML + 6.98, y1 + h1, 0.60, color=AMBER, lw=1.2)
    down_arrow(s, ML + 6.90, y1 + h1 + 0.58, 0.56, color=AMBER)
    text(s, ML + 4.90, y1 + h1 + 0.08, 1.90, 0.22, "sync when the link is up", size=8.2,
         color=AMBER, align=PP_ALIGN.RIGHT)

    vline(s, ML + 1.20, y2 + h2 - 0.04, 0.38, color=RED, lw=1.2)
    down_arrow(s, ML + 1.12, y2 + h2 + 0.30, 0.34, color=RED)
    text(s, ML + 1.46, y2 + h2 + 0.10, 4.8, 0.44,
         "Astro AI 2.0 watches every layer above\nand recovers it", size=8.4, color=RED, line=1.2)

    text(s, ML, 6.06, CW, 0.24,
         "Two rules hold the architecture together", size=10, color=AMBER, bold=True,
         caps=True, spc=160)
    bullets(s, ML, 6.30, 5.9, 0.7, [
        ("Local first.", "a scan is never lost because the internet was down"),
    ], size=10.5, marker="\u25aa", mcolor=CYAN)
    bullets(s, ML + 6.2, 6.30, 5.9, 0.7, [
        ("Server second.", "the cloud is a replica the dashboards read, not the source of truth"),
    ], size=10.5, marker="\u25aa", mcolor=GREEN)

    footer(s, i, n, "Architecture — README · docs/master_prompt.md")
    notes(s, """
Walk the arrows once, left to right, top then bottom.

The important sentence: the ESP32 decides. It does not wait for Firebase to say the
student is present - it proves the scan locally, tells the student with the LCD and the
buzzer, and queues the record. The cloud is the replica the dashboards read.
""")
    return s


# =============================================================  04  BILL
def s04_bill(prs, i, n):
    s = slide_new(prs)
    header(s, "Bill of materials", "What ₹1,500 actually buys",
           "Five parts from a hobby-electronics catalogue, a 3D-printed box, and no licence fee — "
           "ever.")

    rows = [
        ["Layer", "What we chose", "Why this one"],
        ["Compute", "ESP32 DevKit V1", "Wi-Fi + dual core for ₹450-class money"],
        ["Identity", "RC522 13.56 MHz reader", "₹150-class MIFARE reader, 10 mm range"],
        ["Biometric", "R307 optical module", "1,000 templates, matched on the module"],
        ["Feedback", "LCD1602 + I²C backpack", "Two wires instead of ten"],
        ["Enclosure", "4 printed parts, 159 g PLA", "₹200 of filament, not a ₹4,000 box"],
        ["Cloud", "Firebase Spark tier", "No servers to run; HTTPS and rules included"],
    ]
    table(s, ML, 2.00, 8.10, [1.24, 2.34, 4.52], rows, size=9.2, head_size=9,
          row_h=0.56, first_bold=True, align=[PP_ALIGN.LEFT, PP_ALIGN.LEFT, PP_ALIGN.LEFT])

    kpi(s, 8.96, 2.00, 3.72, 1.30, "₹1,500", "Target cost per unit, per our brief",
        AMBER, vsize=40, lsize=9)
    kpi(s, 8.96, 3.46, 3.72, 1.30, "95 %", "Cheaper than a commercial biometric terminal",
        GREEN, vsize=40, lsize=9)
    kpi(s, 8.96, 4.92, 3.72, 1.30, "₹0", "Recurring licence. Free tier covers a school",
        CYAN, vsize=40, lsize=9)

    text(s, ML + 8.52, 6.44, 3.58, 0.62,
         "Honesty note: the CAD audit carries no price at all — master_prompt §3.1 forbids it. The ₹1,500 is the "
         "team's target, not a quote.", size=8.4, color=FAINT, line=1.26)

    footer(s, i, n, "Bill of materials — README.md")
    notes(s, """
Do not read the table. Say the sentence: "the whole trick is that nothing in this box is
a specialist part. Every line is in a hobby catalogue in Mirzapur, or printed on our own bed."

If asked about the ₹1,500: it is the target in our brief. The margin we actually protect is
the recurring one - there is no licence, ever.
""")
    return s


# =============================================================  05  PROBLEM
def s05_problem(prs, i, n):
    s = slide_new(prs)
    header(s, "Problem", "Ten minutes of teaching, lost every period",
           "Manual attendance is slow, disconnected and unverifiable — and it is not a "
           "problem of one school.")

    kpi(s, ML, 2.02, 2.86, 1.44, "10–15", "minutes of teaching lost per class, every period",
        RED, vsize=34)
    kpi(s, ML + 3.06, 2.02, 2.86, 1.44, "15 Lakh+", "schools in India facing the same register",
        ORANGE, vsize=34)
    kpi(s, ML + 6.12, 2.02, 2.86, 1.44, "3", "separate registers that never meet: class, parent, report",
        AMBER, vsize=34)
    kpi(s, ML + 9.18, 2.02, 2.86, 1.44, "0", "offline behaviour in the systems schools can afford",
        CYAN, vsize=34)

    text(s, ML, 3.78, 6.0, 0.26, "What goes wrong today", size=10, color=AMBER, bold=True,
         caps=True, spc=160)
    bullets(s, ML, 4.06, 6.05, 2.6, [
        ("The teacher reads 40 names.", "Two minutes minimum, four if the room is noisy — seven times a day."),
        ("The register is paper.", "A parent finds out at month-end, or never."),
        ("Proxy attendance is trivial.", "One friend answers for three students."),
        ("Reporting is manual.", "Someone re-keys the register for the monthly return."),
        ("Nothing works offline.", "The affordable systems need the internet up at 8 a.m."),
    ], size=10.6, gap=0.10, line=1.26)

    text(s, ML + 6.42, 3.78, 5.6, 0.26, "What we insist on instead", size=10, color=GREEN,
         bold=True, caps=True, spc=160)
    rect(s, ML + 6.42, 4.06, 5.68, 2.62, fill=PANEL, line=LINE, lw=0.75, radius=0.04)
    items = [
        ("Two factors, not one.", "a card that can be handed to a friend, plus a thumb that cannot."),
        ("Proof at the door.", "the student sees the mark before they sit down."),
        ("Offline first.", "the day runs with the router unplugged."),
        ("The parent knows by 9:15.", "not at the end of the month."),
        ("₹1,500, no licence.", "affordable at 15-lakh-school scale or it is not a solution."),
    ]
    bullets(s, ML + 6.66, 4.24, 5.2, 2.3, items, size=10.5, gap=0.08, marker="\u2713", mcolor=GREEN)

    footer(s, i, n, "Problem — README.md")
    notes(s, """
Land the four numbers, then the left column, then the right.

The strongest line: "we are not trying to make attendance clever. We are trying to make it
cost fifteen hundred rupees and still work when the internet is down, because that is the
only version fifteen lakh schools can actually buy."
""")
    return s


# =============================================================  06  ESP32
def s06_esp32(prs, i, n):
    s = slide_new(prs)
    header(s, "The microcontroller", "ESP32 DevKit V1 — chosen for the buses, not the Wi-Fi",
           "Every module in the box gets its own hardware bus, which is what makes the "
           "self-healing firmware possible at all.")

    rows = [
        ["Bus", "Carries", "What it protects"],
        ["SPI (VSPI)", "RC522 RFID reader", "10 Mbps clock, so a card's 4-byte UID is read before the student moves"],
        ["UART 2", "R307 fingerprint", "its own wire pair: fingerprint traffic cannot corrupt an RFID read"],
        ["I²C", "LCD1602 backpack", "2 pins for the whole display, leaving GPIO free for the buzzer and fan"],
        ["Flash", "offline queue (LittleFS)", "a full school day of scans survives a power cut"],
        ["Wi-Fi", "Firebase sync", "one batched HTTPS call per shift, not one per scan"],
        ["RTC + NTP", "time", "a record keeps the right period even if the router is down at 8 a.m."],
    ]
    table(s, ML, 2.02, 7.90, [1.30, 2.26, 4.34], rows, size=9.8, head_size=9,
          row_h=0.56, first_bold=True)

    text(s, ML + 8.24, 2.02, 3.86, 0.26, "Why not the obvious board", size=10, color=AMBER,
         bold=True, caps=True, spc=160)
    card(s, ML + 8.24, 2.28, 3.86, 1.26, "Arduino Uno — ₹450",
         "16 MHz, 2 KB RAM, no Wi-Fi. Adding connectivity costs more than the ESP32 itself.",
         accent=RED, hsize=10.5, bsize=8.6)

    card(s, ML + 8.24, 3.62, 3.86, 1.26, "ESP8266 — ₹250",
         "One core, so the RFID loop and the cloud sync fight each other for the CPU.",
         accent=ORANGE, hsize=10.5, bsize=8.6)

    card(s, ML + 8.24, 4.96, 3.86, 1.22, "ESP32 DevKit V1 — ₹450",
         "240 MHz dual core · 520 KB SRAM · 4 MB flash · Wi-Fi + BLE · OTA · 3.3 V.",
         accent=GREEN, hsize=10.5, bsize=8.6)

    rect(s, ML, 6.28, 7.90, 0.62, fill=PANEL2, line=LINE, lw=0.75, radius=0.05)
    text(s, ML + 0.22, 6.42, 7.5, 0.36,
         "Board is 51.45 × 28.33 × 1.6 mm with 11 mm of header stack — the enclosure reserves "
         "16 mm of component height inside a 40 mm cavity.", size=9.2, color=SOFT)

    footer(s, i, n, "Compute layer — docs/master_prompt.md §5, §9")
    notes(s, """
The line that wins this slide: "we did not choose the ESP32 because it has Wi-Fi. We chose
it because it has enough separate buses that no sensor can starve another one, and enough
flash to hold a whole day of scans."

The Uno and ESP8266 cards are there so the choice looks like a decision, not a default.
""")
    return s


# =============================================================  07  RFID
def s07_rfid(prs, i, n):
    s = slide_new(prs)
    header(s, "Identity — RFID", "13.56 MHz, and the 3 mm mistake that killed v1",
           "The reader is the reason the enclosure exists in this shape. An RFID antenna "
           "will not scan through plastic.")

    # pin map
    text(s, ML, 1.98, 5.6, 0.26, "RC522 → ESP32 (VSPI bus)", size=10, color=AMBER, bold=True,
         caps=True, spc=160)
    rows = [
        ["RC522 pin", "ESP32", "Role"],
        ["SDA / SS", "GPIO 5", "chip select"],
        ["SCK", "GPIO 18", "SPI clock"],
        ["MOSI", "GPIO 23", "data to reader"],
        ["MISO", "GPIO 19", "data from reader"],
        ["RST", "GPIO 27", "hard reset line"],
        ["3.3 V / GND", "3V3 / GND", "≈26 mA, never 5 V"],
    ]
    table(s, ML, 2.26, 5.30, [1.50, 1.55, 2.25], rows, size=9.5, head_size=9, row_h=0.36,
          first_bold=True)
    text(s, ML, 4.92, 5.30, 0.34,
         "These are the Arduino core's default VSPI pins — no software remap needed.",
         size=8.2, color=FAINT, italic=True, line=1.2)

    # physics cards
    text(s, ML + 5.72, 1.98, 6.2, 0.26, "What actually blocks a scan", size=10, color=AMBER,
         bold=True, caps=True, spc=160)
    card(s, ML + 5.72, 2.26, 3.00, 1.38, "Plastic is invisible",
         "13.56 MHz through 2.20 mm of PLA = 0.0001 dB. The wall was never the problem.", accent=GREEN, hsize=10.2, bsize=8.8)

    card(s, ML + 8.92, 2.26, 3.00, 1.38, "Air gap is everything",
         "v1 printed 3 mm of floor over the antenna and the 10 mm card range collapsed.", accent=RED, hsize=10.2, bsize=8.8)

    card(s, ML + 5.72, 3.78, 3.00, 1.38, "Metal detunes the coil",
         "Nearest steel screw head is 38 mm from the coil centre, against a ~25 mm loop.", accent=ORANGE, hsize=10.2, bsize=8.8)

    card(s, ML + 8.92, 3.78, 3.00, 1.38, "Bars cast a shadow",
         "v2's two stiffener bars cost 190 mm² of shadow. v3: 0 of 8,269 rays blocked.", accent=MAGENTA, hsize=10.2, bsize=8.8)

    # read sequence
    text(s, ML, 5.26, CW, 0.26, "One tap, 40 milliseconds", size=10, color=AMBER, bold=True,
         caps=True, spc=160)
    steps = [("Field on", "reader radiates 13.56 MHz"), ("Card wakes", "harvests power from the field"),
             ("Anti-collision", "one card answers, others stay silent"), ("UID + CRC", "4 or 7 bytes, integrity checked"),
             ("Lookup", "UID → student, local table in flash")]
    x = ML
    for k, (h, b) in enumerate(steps):
        rect(s, x, 5.54, 2.24, 0.86, fill=PANEL, line=LINE, lw=0.75, radius=0.05)
        text(s, x + 0.16, 5.66, 1.95, 0.24, h, size=10, color=CYAN, bold=True)
        text(s, x + 0.16, 5.92, 1.95, 0.42, b, size=8.3, color=DIM, line=1.2)
        if k < 4:
            arrow(s, x + 2.28, 5.90, 0.20, color=FAINT)
        x += 2.48

    footer(s, i, n, "RC522 layer — master_prompt §8 · v3_physics_audit.txt §6")
    notes(s, """
This is a story slide. Tell it as one: "v1 did not work. The box looked right and the reader
would not read, because we had printed three millimetres of plastic between the student's
card and the antenna. We measured it, we took the floor out, and we proved by ray-casting
that all 8,269 lines through the window are open."

The pin map is here because the jury usually asks "how is it wired".
""")
    return s


# =============================================================  08  FINGERPRINT
def s08_bio(prs, i, n):
    s = slide_new(prs)
    header(s, "Identity — biometric", "The fingerprint never leaves the sensor",
           "R307 does its own matching, so the ESP32 only ever learns 'template 41 matched'. "
           "That is a privacy decision, not a shortcut.")

    rect(s, ML, 2.02, 6.10, 2.22, fill=PANEL, line=LINE, lw=0.75, radius=0.04)
    text(s, ML + 0.26, 2.20, 5.6, 0.28, "ON THE MODULE", size=9.5, color=GREEN, bold=True, spc=180)
    bullets(s, ML + 0.26, 2.48, 5.5, 1.6, [
        ("500 DPI optical prism,", "19 × 21 mm glass"),
        ("1,000 templates in its own flash", "— nothing external to leak"),
        ("matching happens in the module", "1:1 by ID or 1:N across the school"),
        ("only a verdict crosses the wire", "match / no-match plus a template number"),
    ], size=9.8, gap=0.06, marker="\u25aa", mcolor=GREEN)

    rect(s, ML, 4.38, 6.10, 1.76, fill=PANEL, line=LINE, lw=0.75, radius=0.04)
    text(s, ML + 0.26, 4.54, 5.6, 0.28, "NEVER ON THE WIRE", size=9.5, color=RED, bold=True, spc=180)
    bullets(s, ML + 0.26, 4.84, 5.5, 1.2, [
        "no fingerprint image",
        "no template copy",
        "no name — the cloud stores an ID, the register maps it",
    ], size=9.8, gap=0.05, marker="\u2715", mcolor=RED)

    # the two-factor argument
    text(s, ML + 6.52, 2.02, 5.5, 0.26, "Why two factors and not one", size=10, color=AMBER,
         bold=True, caps=True, spc=160)
    rows = [
        ["Threat", "Card only", "Card + thumb"],
        ["Card handed to a friend", "works", "fails"],
        ["Card left at home", "no mark", "thumb still marks"],
        ["Wet or dirty thumb", "—", "card still marks"],
        ["Cost of the second factor", "—", "₹650"],
    ]
    table(s, ML + 6.52, 2.30, 5.40, [2.30, 1.30, 1.80], rows, size=9.6, head_size=9,
          row_h=0.44,
          colors={(1, 2): RED, (2, 1): RED, (3, 1): GREEN, (4, 1): GREEN})

    rect(s, ML + 6.52, 5.02, 5.40, 1.16, fill=PANEL2, line=LINE, lw=0.75, radius=0.05)
    text(s, ML + 6.74, 5.18, 5.0, 0.26, "The rule we chose", size=9.5, color=AMBER, bold=True,
         caps=True, spc=160)
    text(s, ML + 6.74, 5.46, 5.0, 0.6, "A scan is valid when either factor matches, and both are "
         "logged as separate evidence. The teacher can always see which one marked the student.",
         size=9.8, color=SOFT, line=1.3)

    footer(s, i, n, "R307 layer — master_prompt §5, §13 · physics audit §7")
    notes(s, """
Say the privacy sentence out loud - juries remember it: "the fingerprint image never leaves
the sensor. The cloud only ever sees 'template 41 matched at 08:41'."

The table answers the obvious question: why pay 650 rupees for a second factor.
""")
    return s


# =============================================================  09  OFFLINE
def s09_offline(prs, i, n):
    s = slide_new(prs)
    header(s, "Offline-first", "A day of attendance survives the router being unplugged",
           "The ESP32 is the source of truth for the school day. Firebase is the replica "
           "that the dashboards read.")

    steps = [
        ("①", "SCAN", "card UID or fingerprint verdict", CYAN),
        ("②", "DECIDE", "local lookup table, in flash", GREEN),
        ("③", "PROVE", "LCD + buzzer, before the student sits", MAGENTA),
        ("④", "QUEUE", "CRC-checked record appended to a ring buffer", AMBER),
        ("⑤", "SYNC", "batched HTTPS write when Wi-Fi returns", ORANGE),
    ]
    x, w = ML, 2.26
    for num, head, body, col in steps:
        rect(s, x, 2.02, w, 1.22, fill=PANEL, line=col, lw=1.0, radius=0.05)
        text(s, x + 0.16, 2.14, 0.4, 0.24, num, size=12, color=col, bold=True)
        text(s, x + 0.16, 2.44, w - 0.32, 0.26, head, size=11, color=WHITE, bold=True, spc=90)
        text(s, x + 0.16, 2.74, w - 0.32, 0.44, body, size=8.6, color=DIM, line=1.22)
        if x + w + 0.22 < SW - MR:
            arrow(s, x + w + 0.02, 2.55, 0.18, color=FAINT)
        x += w + 0.22

    text(s, ML, 3.52, CW, 0.26, "The four failures a school actually has, and what the box does",
         size=10, color=AMBER, bold=True, caps=True, spc=160)
    rows = [
        ["Failure", "What a network-only system does", "What Astro does"],
        ["Internet down at 8 a.m.", "no attendance at all", "full day runs; 4 MB flash holds weeks of scans"],
        ["Power cut mid-period", "the scan in progress is lost", "each record is appended the moment it is confirmed"],
        ["Wi-Fi back, sync restarts", "duplicate or out-of-order rows", "idempotent write keyed on (student, date, period) — a double sync cannot duplicate"],
        ["Clock wrong after an outage", "scans land in the wrong period", "NTP re-sync at boot; a monotonic counter keeps order if time is unknown"],
    ]
    table(s, ML, 3.80, CW, [2.30, 3.30, 6.49], rows, size=9.6, head_size=9, row_h=0.50,
          first_bold=True)

    rect(s, ML, 6.04, CW, 0.86, fill=PANEL2, line=LINE, lw=0.75, radius=0.05)
    rect(s, ML, 6.04, 0.05, 0.86, fill=CYAN)
    text(s, ML + 0.26, 6.16, CW - 0.5, 0.64,
         "Design rule that came out of this table: a record is written to flash before the LCD may say "
         "\u201cpresent\u201d. A student who has seen their mark can walk away knowing it exists, network or not.",
         size=9.4, color=SOFT, line=1.28)

    footer(s, i, n, "Offline behaviour — README.md; firmware design rule")
    notes(s, """
The single sentence for this slide: "the box tells the student they are marked before it
phones home, and it never queues an unconfirmed record."

If asked how the firmware knows the period: NTP gives the time, a timetable table in flash
turns the time into period 1-8, and the monotonic counter orders records if the clock is wrong.
""")
    return s


# =============================================================  10  FIREBASE
def s10_firebase(prs, i, n):
    s = slide_new(prs)
    header(s, "Cloud layer", "Firebase does four jobs so a school runs no servers",
           "Authentication, a realtime database, hosting and security rules — all on the free "
           "tier, all HTTPS by default.")

    services = [
        ("AUTHENTICATION", "Email / password plus custom claims: one login tree, three roles. "
         "Claims are checked in the rules, not in the page.", AMBER),
        ("REALTIME DATABASE", "A JSON tree with a client-side cache. A write from the ESP32 "
         "appears on the dashboard with no refresh.", CYAN),
        ("HOSTING", "Static dashboards on a global CDN with TLS included. Nothing to patch, "
         "nothing to pay.", GREEN),
        ("SECURITY RULES", "Tested per path: a guardian reads only their ward, a student only "
         "their own row, an admin the school.", MAGENTA),
    ]
    x, w = ML, 2.92
    for k, (head, body, col) in enumerate(services):
        y = 2.02 if k < 2 else 3.66
        x = ML + (k % 2) * (w + 0.22)
        rect(s, x, y, w, 1.46, fill=PANEL, line=LINE, lw=0.75, radius=0.04)
        rect(s, x, y, w, 0.04, fill=col)
        text(s, x + 0.22, y + 0.20, w - 0.44, 0.24, head, size=9, color=col, bold=True, spc=160)
        text(s, x + 0.22, y + 0.50, w - 0.44, 0.88, body, size=9.2, color=SOFT, line=1.30)

    # data model
    rect(s, ML + 6.30, 2.02, 5.62, 3.10, fill=RGBColor(0x0A, 0x0C, 0x10), line=LINE, lw=0.75,
         radius=0.03)
    text(s, ML + 6.52, 2.16, 5.2, 0.24, "THE TREE THE APP READS", size=9, color=DIM, bold=True, spc=160)
    code = (
        "schools/\n"
        "  {schoolId}/\n"
        "    students/{uid}/       name, class, section, guardian\n"
        "    attendance/{YYYY-MM-DD}/\n"
        "      P1: { state: \"P\", at: \"08:41\", by: \"rfid\" }\n"
        "      P2: { state: \"L\", at: \"09:12\", by: \"finger\" }\n"
        "    devices/{mac}/        firmware, lastSync, health"
    )
    box = tb(s, ML + 6.52, 2.44, 5.2, 2.5)
    for k, ln in enumerate(code.split("\n")):
        para(box.text_frame, ln, size=8.5, color=GREEN if k % 2 == 0 else CYAN,
             font=MONO, first=(k == 0), line=1.32)

    text(s, ML + 6.52, 4.82, 5.2, 0.26, "≈10 KB per sync — it survives a 2G link",
         size=9.5, color=AMBER, bold=True)

    rect(s, ML, 5.36, 5.90, 1.54, fill=PANEL2, line=LINE, lw=0.75, radius=0.05)
    text(s, ML + 0.24, 5.50, 5.4, 0.24, "WHY NOT A REAL SERVER", size=9, color=AMBER, bold=True, spc=160)
    text(s, ML + 0.24, 5.76, 5.42, 1.02,
         "A school has no sysadmin. Firebase's free tier costs nothing, needs no patching, and "
         "gives HTTPS, auth and a CDN out of the box. If the school later needs SQL reporting, the "
         "data is one export away.", size=9.0, color=SOFT, line=1.30)

    kpi(s, ML + 6.30, 5.36, 2.72, 1.48, "0", "servers to run or patch", CYAN, vsize=30, lsize=9)
    kpi(s, ML + 9.20, 5.36, 2.72, 1.48, "HTTPS", "by default, with auth and rules", GREEN,
        vsize=24, lsize=9)

    footer(s, i, n, "Cloud layer — README.md")
    notes(s, """
Four services, four sentences. Then point at the JSON on the right and say: "this is the
whole database. A school's attendance is a tree about ten kilobytes per sync."

The 'why not a real server' box is the answer to the jury member who says 'why not just use
MySQL' - because the school would then need an administrator.
""")
    return s


# =============================================================  11  ROLES
def s11_roles(prs, i, n):
    s = slide_new(prs)
    header(s, "Access model", "Three roles, three views of the same record",
           "Role is a claim in the login token, and the database rules enforce it — the "
           "dashboard is not the security boundary.")

    roles = [
        ("ADMIN", "Principal, class teacher", AMBER, [
            "mark, edit and justify any record",
            "enrol students and cards",
            "daily and period reports, CSV export",
            "device health and last-sync for every box",
        ]),
        ("STUDENT", "The learner", CYAN, [
            "own attendance, day and period",
            "own percentage and trend",
            "cannot see any other student's row",
            "cannot write anything",
        ]),
        ("GUARDIAN", "Parent at home", GREEN, [
            "their ward only, read-only",
            "the same email the alert comes from",
            "period-level detail, not just a daily tick",
            "can opt out of email, not of the record",
        ]),
    ]
    x, w = ML, 3.86
    for k, (head, sub, col, items) in enumerate(roles):
        rect(s, x, 2.02, w, 3.30, fill=PANEL, line=LINE, lw=0.75, radius=0.04)
        rect(s, x, 2.02, w, 0.045, fill=col)
        text(s, x + 0.28, 2.26, w - 0.5, 0.3, head, size=13, color=col, bold=True, spc=140)
        text(s, x + 0.28, 2.58, w - 0.5, 0.24, sub, size=9, color=DIM, italic=True)
        bullets(s, x + 0.28, 2.96, w - 0.54, 2.1, items, size=10, gap=0.10, marker="\u25aa",
                mcolor=col, color=SOFT)
        x += w + 0.20

    text(s, ML, 5.54, CW, 0.26, "The rule that makes this real", size=10, color=AMBER,
         bold=True, caps=True, spc=160)
    rect(s, ML, 5.82, CW, 1.02, fill=RGBColor(0x0A, 0x0C, 0x10), line=LINE, lw=0.75, radius=0.04)
    box = tb(s, ML + 0.28, 5.96, CW - 0.6, 0.8)
    para(box.text_frame,
         'attendance/$date/$period:  write if isAdmin(school) || isDevice(mac)',
         size=9.2, color=GREEN, font=MONO, first=True, line=1.4)
    para(box.text_frame,
         '                           read  if isAdmin(school) || uid == auth.uid || wardOf(auth.uid) == uid',
         size=9.2, color=CYAN, font=MONO, line=1.4)

    footer(s, i, n, "Access model — README.md · deck slide 10")
    notes(s, """
The point of the pseudo-rules: a student who opens developer tools and edits the page still
cannot read another student's attendance, because the rule runs on the server.

Guardian can opt out of email but not of the record - attendance is a legal record in India.
""")
    return s


# =============================================================  12  ALERTS
def s12_alerts(prs, i, n):
    s = slide_new(prs)
    header(s, "Guardian alerts", "The parent knows at 9:15, not at month-end",
           "An email is a notification about a record — never the record itself. If the mail "
           "fails, the attendance does not.")

    # timeline
    text(s, ML, 1.98, 7.4, 0.26, "A morning, minute by minute", size=10, color=AMBER,
         bold=True, caps=True, spc=160)
    tl = [("08:40", "Card tap", CYAN), ("08:41", "Row written to flash", GREEN),
          ("08:42", "Synced to Firebase", AMBER), ("09:15", "Absence list closes", ORANGE),
          ("09:16", "Guardian email queued", MAGENTA), ("09:17", "Delivered / retried", RED)]
    hline(s, ML + 0.1, 2.94, 7.2, color=LINE, lw=1.5)
    x = ML
    for t, label, col in tl:
        dot(s, x + 0.02, 2.895, 0.11, col)
        text(s, x - 0.10, 2.48, 1.28, 0.24, t, size=9.5, color=col, bold=True)
        text(s, x - 0.10, 3.12, 1.24, 0.5, label, size=8.6, color=DIM, line=1.2)
        x += 1.22

    text(s, ML, 3.92, 7.4, 0.26, "Anti-spam rules learned the hard way", size=10, color=AMBER,
         bold=True, caps=True, spc=160)
    bullets(s, ML, 4.18, 7.30, 2.4, [
        ("One digest per student per day.", "a parent who gets eleven emails stops reading all of them."),
        ("Quiet hours.", "nothing is sent between 21:00 and 07:00; it goes out at 07:05."),
        ("Late is not absent.", "the first alert says late; only an unmarked period escalates."),
        ("Retry with backoff, then fall back.", "three attempts, then the admin's dashboard shows the row as undelivered."),
        ("The record wins.", "a failed email never changes an attendance state."),
    ], size=9.6, gap=0.08, line=1.24)

    # email mock
    rect(s, ML + 7.74, 1.98, 4.22, 3.90, fill=RGBColor(0xF7, 0xF8, 0xFA), line=LINE, lw=0.75,
         radius=0.03)
    text(s, ML + 7.96, 2.14, 3.8, 0.24, "To: guardian@example.com", size=8.4, color=RGBColor(0x55, 0x5F, 0x70), font=MONO)
    hline(s, ML + 7.96, 2.42, 3.78, color=RGBColor(0xD5, 0xD9, 0xE0))
    text(s, ML + 7.96, 2.54, 3.78, 0.5, "Attendance update —\nRenukoot Public School, Class 9-B",
         size=10.5, color=RGBColor(0x1A, 0x1F, 0x28), bold=True, line=1.3)
    text(s, ML + 7.96, 3.14, 3.78, 1.0,
         "Anant was marked ABSENT in period 2 (09:10)\non 12 Nov 2026.\n\n"
         "Period 1 — present, by card, 08:41", size=9, color=RGBColor(0x3A, 0x44, 0x54), line=1.36)
    rect(s, ML + 7.96, 4.30, 1.62, 0.32, fill=RGBColor(0x1F, 0x33, 0x55))
    text(s, ML + 7.96, 4.38, 1.62, 0.24, "View full record", size=8, color=WHITE,
         bold=True, align=PP_ALIGN.CENTER)
    hline(s, ML + 7.96, 4.86, 3.78, color=RGBColor(0xD5, 0xD9, 0xE0))
    text(s, ML + 7.96, 4.96, 3.78, 0.7,
         "Sent automatically. Do not reply.\nTo stop these, ask the class teacher.",
         size=7.8, color=RGBColor(0x7A, 0x85, 0x95), line=1.35)
    text(s, ML + 7.74, 5.92, 4.22, 0.26, "Illustrative mock-up of the digest email",
         size=7.8, color=FAINT, italic=True, align=PP_ALIGN.CENTER)

    footer(s, i, n, "Alerting — README.md key features")
    notes(s, """
The email mock is the slide parents in the audience remember. Point at the period line: the
parent does not just learn 'absent', they learn period 1 was fine and period 2 was not.

Say the anti-spam line as a design decision: "we cap it at one email a day per child, because
a parent who is spammed stops reading, and then the system has failed socially even if it
worked technically."
""")
    return s


# =============================================================  13  ENCLOSURE PROBLEM
def s13_encl(prs, i, n):
    s = slide_new(prs)
    header(s, "The enclosure", "Six parts, four impossible constraints, no supports",
           "Everything inside the box was given before the box was drawn. The outer size is "
           "an output, not an input.")

    cons = [
        ("RFID needs air", "The 13.56 MHz coil cannot scan through a printed floor. The window must "
         "be a true through-cut, nothing across it.", CYAN),
        ("Optics need a cone", "The R307 prism needs a clear 20° cone to the finger; the LCD needs "
         "±34° horizontally.", GREEN),
        ("No supports allowed", "It must print on a school's own bed, front face down, with no "
         "support material and no raft.", AMBER),
        ("Summer PLA", "Renukoot in May puts a wall-mounted box near PLA's 60 °C glass transition.",
         ORANGE),
    ]
    x, w = ML, 2.92
    for k, (head, body, col) in enumerate(cons):
        y = 2.02 if k < 2 else 3.34
        x = ML + (k % 2) * (w + 0.22)
        rect(s, x, y, w, 1.22, fill=PANEL, line=LINE, lw=0.75, radius=0.04)
        rect(s, x, y, 0.04, 1.22, fill=col)
        text(s, x + 0.22, y + 0.16, w - 0.4, 0.26, head, size=11, color=col, bold=True)
        text(s, x + 0.22, y + 0.46, w - 0.4, 0.70, body, size=8.8, color=DIM, line=1.26)

    text(s, ML, 4.80, 6.1, 0.26, "The answer: derive the shell from the parts", size=10,
         color=AMBER, bold=True, caps=True, spc=160)
    bullets(s, ML, 5.08, 6.05, 1.8, [
        ("Place the real envelopes first,", "with the vendor-tolerance clearances."),
        ("Then wrap 2.6–3.0 mm walls around them", "— the size falls out of that arithmetic."),
        ("Result: 110 × 155 × 46 mm,", "4 printed parts, 172.2 cm³ of plastic."),
    ], size=10.2, gap=0.10, line=1.28)

    kpi(s, ML + 6.50, 4.80, 1.82, 1.14, "110", "mm wide", CYAN, vsize=26, lsize=8.5)
    kpi(s, ML + 6.50 + 1.94, 4.80, 1.82, 1.14, "155", "mm tall", GREEN, vsize=26, lsize=8.5)
    kpi(s, ML + 6.50 + 3.88, 4.80, 1.82, 1.14, "46", "mm deep", AMBER, vsize=26, lsize=8.5)

    fig_light(s, A("exploded"), ML + 6.50, 2.02, 5.60, 2.56)
    text(s, ML + 6.50, 4.60, 5.60, 0.22,
         "Exploded assembly: shell, rear plate, R307 bracket, RC522 ring — the four printed parts",
         size=8, color=FAINT, align=PP_ALIGN.CENTER)

    footer(s, i, n, "Enclosure constraints — master_prompt §6, §8, §13, §14")
    notes(s, """
Frame it as a puzzle: four things are true about the parts before a single line is drawn, and
the four of them fight each other. The RFID wants air. The optics want an opening. The printer
wants no supports. The PLA wants thickness.

The answer is the method, and that is the next ten slides.
""")
    return s


# =============================================================  14  CAD AS CODE
def s14_cadcode(prs, i, n):
    s = slide_new(prs)
    header(s, "Method", "The CAD is a program, not a drawing",
           "tools/build_v3.py holds every dimension as a named, sourced parameter. Change one "
           "number, and the box, every check and every report rebuild in about a minute.")

    code = (
        'P = dict(\n'
        '    W=110.0, H=155.0, D=46.0,\n'
        '    wall_side=2.6, wall_top=3.0, wall_front=3.0, plate_t=3.0,\n'
        '    fit=0.35, rebate=(0.45, 3.0),\n'
        '\n'
        '    lcd_window=(66.0, 17.5), lcd_centre=(0.0, 51.95),   # [V1]\n'
        '    lcd_hole_pitch=(75.1, 31.0),                        # [V1] == 1602 std\n'
        '\n'
        '    r307_window=(19.3, 21.2), r307_centre=(35.95, -24.1),\n'
        '    r307_body=(20.0, 44.1, 23.5),\n'
        '\n'
        '    rc522_board=(40.0, 60.0, 1.6),\n'
        '    rfid_window=(38.0, 56.0), rfid_bars=(0, 0.0),\n'
        ')'
    )
    rect(s, ML, 1.98, 6.52, 4.42, fill=RGBColor(0x0A, 0x0C, 0x10), line=LINE, lw=0.75, radius=0.03)
    text(s, ML + 0.24, 2.12, 5.9, 0.24, "tools/build_v3.py  —  the parameter block, verbatim",
         size=8.6, color=DIM, bold=True, font=MONO)
    box = tb(s, ML + 0.24, 2.42, 6.1, 3.3)
    for k, ln in enumerate(code.split("\n")):
        col = CYAN if ln.strip().startswith(('W=', 'wall', 'fit', 'rebate')) else \
            (GREEN if '#' in ln else SOFT)
        para(box.text_frame, ln if ln else " ", size=8.4, color=col, font=MONO,
             first=(k == 0), line=1.28)

    text(s, ML + 6.86, 1.98, 5.2, 0.26, "Provenance is in the comments", size=10, color=AMBER,
         bold=True, caps=True, spc=160)
    rows = [
        ["Tag", "Means", "If it is wrong"],
        ["[V1]", "measured from the team's own v1 STL", "built from the delivered part"],
        ["[REF]", "component reference from the team", "a printed fit absorbs 0.35 mm"],
        ["[EST]", "engineering estimate", "tagged VERIFY_ACTUAL_HARDWARE"],
        ["[WEB]", "a published vendor drawing", "dated in the source comment"],
    ]
    table(s, ML + 6.86, 2.26, 5.22, [0.72, 2.36, 2.14], rows, size=8.6, head_size=8.4,
          row_h=0.44, first_bold=True)

    text(s, ML + 6.86, 4.90, 5.2, 0.26, "The stack", size=10, color=AMBER, bold=True,
         caps=True, spc=160)
    libs = [("trimesh 5.1.1", "mesh I/O, watertight tests, booleans"),
            ("manifold3d 3.5.4", "exact boolean kernel — this is what makes unions watertight"),
            ("shapely 2.2.0", "2-D booleans for every cut profile"),
            ("mapbox-earcut 2.1.0", "triangulation of the resulting polygons"),
            ("numpy / scipy", "ray sampling, probes, audit statistics"),
            ("matplotlib", "the drawing sheets and section figures"),
            ("Canvas 2D + JS", "the 3D viewer: hand-written rasteriser, no library")]
    x = ML + 6.86
    for k, (lib, use) in enumerate(libs):
        col = k % 2
        yy = 5.14 + (k // 2) * 0.52
        text(s, x + col * 2.60, yy, 2.55, 0.22, lib, size=8.6, color=CYAN, bold=True, font=MONO)
        text(s, x + col * 2.60, yy + 0.20, 2.55, 0.34, use, size=8, color=DIM, line=1.15)

    hline(s, ML + 0.24, 5.18, 6.04, color=RGBColor(0x2A, 0x30, 0x3C))
    text(s, ML + 0.24, 5.28, 6.0, 0.24, "One command rebuilds every part, check and report",
         size=9, color=AMBER, bold=True, caps=True, spc=140)
    text(s, ML + 0.24, 5.54, 6.04, 0.28,
         "$ python3 tools/build_v3.py", size=9.5, color=GREEN, font=MONO)
    text(s, ML + 0.24, 5.80, 6.04, 0.28,
         "  → cad/v3/*.stl  +  docs/v3_audit.txt", size=9.5, color=DIM, font=MONO)
    text(s, ML + 0.24, 6.14, 6.04, 0.24, "about 60 seconds, and it refuses to write a bad mesh",
         size=8.6, color=FAINT, italic=True)

    footer(s, i, n, "Method — tools/build_v3.py · tools/requirements_v3.txt")
    notes(s, """
This is the slide that separates the project from a school 3D-printing project.

"The CAD is not a drawing. It is a Python program with a dictionary at the top. Every number
in that dictionary has a comment saying where it came from - our own part, the team's
measurement, a vendor drawing, or an estimate that we are obliged to verify."

If someone asks about Blender: Blender renders and exports; it does not decide. The geometry
is decided by the program.
""")
    return s


# =============================================================  15  PIPELINE
def s15_pipeline(prs, i, n):
    s = slide_new(prs)
    header(s, "Pipeline", "From a dictionary to a printed part",
           "Six stages, and a gate between every two of them. Nothing reaches the pack unless "
           "a program said PASS.")

    stages = [
        ("01", "PARAMETERS", "P = dict(...) with provenance on every value", CYAN),
        ("02", "SOLIDS", "primitives → boolean union → exact manifold body", GREEN),
        ("03", "CUTS", "openings, pilots, rebates, then re-union what must survive", AMBER),
        ("04", "STL", "watertight, 1 body, 0 open edges — asserted before writing", ORANGE),
        ("05", "ORIENT", "bed alignment baked into the triangles, then re-verified", MAGENTA),
        ("06", "PACK", "4 STLs + print order + SHA-256 + figures + .blend + .glb", RED),
    ]
    x, w = ML, 1.94
    for k, (num, head, body, col) in enumerate(stages):
        rect(s, x, 2.06, w, 1.46, fill=PANEL, line=LINE, lw=0.75, radius=0.04)
        rect(s, x, 2.06, w, 0.04, fill=col)
        text(s, x + 0.18, 2.22, w - 0.34, 0.24, num, size=9, color=col, bold=True, spc=120)
        text(s, x + 0.18, 2.48, w - 0.34, 0.26, head, size=10.5, color=WHITE, bold=True, spc=80)
        text(s, x + 0.18, 2.80, w - 0.34, 0.62, body, size=8.4, color=DIM, line=1.24)
        if k < 5:
            arrow(s, x + w + 0.005, 2.72, 0.16, color=FAINT)
        x += w + 0.16

    text(s, ML, 3.78, CW, 0.26, "The gate that matters", size=10, color=AMBER, bold=True,
         caps=True, spc=160)
    rect(s, ML, 4.06, 6.0, 2.60, fill=PANEL, line=LINE, lw=0.75, radius=0.04)
    text(s, ML + 0.26, 4.22, 5.5, 0.26, "A file is never written on trust", size=11, color=WHITE, bold=True)
    bullets(s, ML + 0.26, 4.54, 5.5, 2.0, [
        "the STL must report watertight = True and bodies = 1",
        "normals must point outward and the volume must be positive",
        "a pilot must break through exactly one surface, never become an enclosed void",
        "every bolt-on feature must overlap its host by ≥ 0.5 mm or the mesh splits",
    ], size=9.6, gap=0.07, marker="\u2713", mcolor=GREEN, line=1.24)

    text(s, ML + 6.36, 4.22, 5.7, 0.26, "Why this order (master_prompt §19)", size=11,
         color=WHITE, bold=True)
    bullets(s, ML + 6.36, 4.54, 5.7, 2.0, [
        ("Hollow first, then union.", "the pocket cut would otherwise delete the bosses."),
        ("Cut, then re-union.", "grille bars, stiffeners and ribs are cut in and put back with overlap."),
        ("Re-audit after every change", "— a stale PASS is worse than a FAIL."),
        ("Regenerate the pack last,", "so the SHA-256 manifest always describes what shipped."),
    ], size=9.6, gap=0.07, line=1.24)

    footer(s, i, n, "Pipeline — master_prompt §19 · tools/build_v3.py · tools/make_pack_v3.py")
    notes(s, """
Do not explain all six boxes. Explain the gate: "the builder refuses to write a file that is
not watertight and a single body. We learned that the hard way - our first gauge printed
hollow because the mesh was closed with its normals pointing inward."

That story is real and it is in docs/v3_design_notes.md section 8.
""")
    return s


# =============================================================  16  FOUR CHECKERS
def s16_checkers(prs, i, n):
    s = slide_new(prs)
    header(s, "Verification", "Four independent programs, one mesh",
           "Each one asks a different question, and none of them can see the others' answers. "
           "The second one never imports the generator at all.")

    rows = [
        ["Program", "The question it asks", "Output", "Result"],
        ["build_v3.py", "Sections A–K: is the parametric model itself consistent — walls, fits, keep-outs, apertures?",
         "docs/v3_audit.txt", "ALL CHECKS PASS"],
        ["verify_v3.py", "Forget the generator: re-type every dimension and re-measure the shipped triangles alone",
         "independent_verify.txt", "ALL CHECKS PASS"],
        ["audit_physics_v3.py", "10 sections of physics: fasteners, airflow, RF, optics, PLA, kinematics, slicer",
         "v3_physics_audit.txt", "no failures"],
        ["check_grooves_v3.py", "Walk a 0.02 mm probe down every rebate, lip and hole — what does the plastic actually offer?",
         "v3_groove_check.txt", "34/34 as designed"],
        ["hole_probe_v3.py", "Cast a ray down all 22 pilots: can the documented screw length actually seat?",
         "v3_hole_probe.txt", "gate: exit ≠ 0"],
    ]
    table(s, ML, 2.02, CW, [1.92, 6.42, 2.02, 1.73], rows, size=9.4, head_size=8.8,
          row_h=0.62, first_bold=True,
          colors={(1, 3): GREEN, (2, 3): GREEN, (3, 3): GREEN, (4, 3): GREEN, (5, 3): AMBER})

    cards = [
        ("Independence, not repetition", "verify_v3.py shares no code with build_v3.py. It re-types 30+ "
         "dimensions by hand and re-measures them off the triangles, so a wrong parameter cannot "
         "hide behind a passing check.", CYAN),
        ("The audit argues back", "audit_physics_v3.py found three real defects that both CAD checkers "
         "had passed: a countersink opening onto a corner round, a plate with a hole through it, "
         "and an RFID board that could not physically be installed.", MAGENTA),
        ("Docs are checked too", "Section 10 of the physics audit re-reads every number in the design "
         "notes and the print order and compares it with the mesh. A stale claim is treated as a bug.",
         AMBER),
    ]
    x, w = ML, 3.86
    for head, body, col in cards:
        rect(s, x, 5.24, w, 1.56, fill=PANEL, line=LINE, lw=0.75, radius=0.04)
        rect(s, x, 5.24, 0.04, 1.56, fill=col)
        text(s, x + 0.22, 5.38, w - 0.4, 0.26, head, size=10, color=col, bold=True)
        text(s, x + 0.22, 5.66, w - 0.42, 1.0, body, size=9, color=DIM, line=1.26)
        x += w + 0.20

    footer(s, i, n, "Verification — docs/v3_*.txt · tools/verify_v3.py, audit_physics_v3.py")
    notes(s, """
The killer line for a technical jury: "one program wrote the box, but four others had to agree
before we were allowed to print it - and one of them is not allowed to import the program
that made the box."

The magenta card is the honest part: the physics audit found three defects that both CAD
checkers passed. That is why it exists.
""")
    return s


# =============================================================  17  FASTENERS
def s17_fasteners(prs, i, n):
    s = slide_new(prs)
    header(s, "Mechanical detail", "22 pilots, all at the thread's minor diameter",
           "A self-tapping screw into printed PLA needs a pilot smaller than nominal, or it "
           "spins instead of biting. Every hole is measured in the shipped mesh.")

    rows = [
        ["Joint", "Screw", "n", "Pilot", "Depth", "Pull-out", "Load held", "Reserve"],
        ["LCD1602 bezel", "M2.5", "4", "Ø2.04", "6.3", "188 N", "0.88 N", "213×"],
        ["R307 bracket", "M3", "2", "Ø2.48", "6.3", "221 N", "0.18 N", "1253×"],
        ["RC522 ring", "M2.5", "4", "Ø2.04", "2.5", "75 N", "0.17 N", "447×"],
        ["ESP32 bosses", "M2.2", "4", "Ø1.78", "5.7", "147 N", "0.25 N", "598×"],
        ["Fan posts", "M3", "4", "Ø2.48", "10.3", "362 N", "0.15 N", "2458×"],
        ["Rear plate", "M3", "4", "Ø2.48", "8.3", "291 N", "0.59 N", "495×"],
    ]
    table(s, ML, 2.02, 8.20, [1.80, 0.86, 0.40, 0.94, 0.84, 1.10, 1.12, 1.14], rows,
          size=9.4, head_size=8.4, row_h=0.42, first_bold=True,
          colors={7: GREEN})

    rect(s, ML + 8.56, 2.02, 3.54, 1.42, fill=RGBColor(0x0A, 0x0C, 0x10), line=LINE, lw=0.75, radius=0.04)
    text(s, ML + 8.74, 2.16, 3.2, 0.22, "PULL-OUT MODEL", size=8.6, color=AMBER, bold=True, spc=140)
    text(s, ML + 8.74, 2.42, 3.2, 0.9, "F = τ · π · d_minor · L · 0.55\nτ = 8.5 MPa cross-layer shear\n0.55 = thread fill",
         size=8.8, color=GREEN, font=MONO, line=1.4)

    kpi(s, ML + 8.56, 3.60, 3.54, 1.16, "213–2458×", "reserve on every joint", CYAN, vsize=22, lsize=8.5)
    kpi(s, ML + 8.56, 4.90, 3.54, 1.16, "0", "glue joints, clips or snap-fits in v3", MAGENTA, vsize=30, lsize=8.5)

    rect(s, ML, 6.12, 8.20, 0.80, fill=PANEL2, line=LINE, lw=0.75, radius=0.05)
    rect(s, ML, 6.12, 0.05, 0.80, fill=AMBER)
    text(s, ML + 0.26, 6.19, 7.7, 0.22, "The audit's own conclusion", size=9.2, color=AMBER,
         bold=True, caps=True, spc=140)
    text(s, ML + 0.26, 6.42, 7.72, 0.44,
         "Fastener count and screwdriver access govern this box — not fastener strength. Every "
         "module got its own 2–4 screws and a clear, straight driver path; nothing needs a washer "
         "or a nut.", size=8.8, color=SOFT, line=1.24)

    footer(s, i, n, "Fasteners — v3_physics_audit.txt §1, §2; v3_hole_probe.txt")
    notes(s, """
The formula is here so nobody can accuse us of a made-up strength number.

Then the punchline, which is genuinely the interesting engineering result: the screws are
four to two-thousand times stronger than they need to be. What actually decides this design is
whether a screwdriver can reach the screw - which is why v3 replaced v2's clip bars with
screws everywhere.
""")
    return s


# =============================================================  18  RFID FIX
def s18_rfidfix(prs, i, n):
    s = slide_new(prs)
    header(s, "Case study", "v1 did not scan. Here is the exact fix.",
           "The single most important change between the first printed box and the shipped "
           "one, and how it was proved rather than assumed.")

    fig_dark(s, A("rfid_fix"), ML, 1.98, 6.30, 3.10)
    text(s, ML, 5.14, 6.30, 0.24,
         "Front face, same projection: v2's two 2.5 mm stiffener bars (left) vs v3's fully open aperture (right)",
         size=8.2, color=FAINT, line=1.2)

    steps = [
        ("THE DEFECT", "v1 printed a closed pocket floor 3 mm in front of the RC522 antenna. The card's "
         "field could not reach it; no card ever read.", RED),
        ("THE FIRST FIX", "v2 opened a 56 × 38 mm window but kept two stiffener bars across it. The "
         "window was 90.4 % open — and 190 mm² of antenna shadow remained.", ORANGE),
        ("THE REAL FIX", "v3 turns the board portrait and cuts a 38 × 56 mm window with rounded R5 "
         "corners: 100 % open, nothing across the coil, and the wall around it is a 2.0 mm ledge "
         "ring braced by four corner gussets instead of bars.", GREEN),
    ]
    y = 1.98
    for head, body, col in steps:
        rect(s, ML + 6.56, y, 5.54, 1.46, fill=PANEL, line=LINE, lw=0.75, radius=0.04)
        rect(s, ML + 6.56, y, 0.045, 1.46, fill=col)
        text(s, ML + 6.76, y + 0.14, 5.1, 0.24, head, size=9, color=col, bold=True, spc=160)
        text(s, ML + 6.76, y + 0.42, 5.1, 0.98, body, size=9.0, color=SOFT, line=1.28)
        y += 1.58

    rect(s, ML, 5.46, 6.30, 1.42, fill=PANEL2, line=LINE, lw=0.75, radius=0.05)
    text(s, ML + 0.24, 5.58, 5.9, 0.24, "HOW IT IS PROVED — NOT ASSERTED", size=9, color=AMBER,
         bold=True, spc=160)
    text(s, ML + 0.24, 5.88, 5.9, 0.90,
         "8,269 rays are cast through the aperture from outside the front face. 0 are blocked. "
         "A separate keep-out volume in front of the coil is proved empty of printed material — "
         "and the 13.56 MHz loss through the remaining 2.20 mm of PLA is 0.0001 dB.",
         size=9.2, color=SOFT, line=1.3)

    footer(s, i, n, "RFID fix — v3_design_notes.md §1, §6 · physics audit §6")
    notes(s, """
This is the story to tell if you have only one story. v1 failed. Not "looked imperfect" -
failed: no card could be read. The team found the cause, changed the layout, and then built a
ray-casting proof so the defect could never come back silently.

Numbers: v2 lost 190 mm2 of antenna shadow to two stiffener bars. v3: 8,269 rays, 0 blocked.
""")
    return s


# =============================================================  19  KINEMATICS
def s19_assembly(prs, i, n):
    s = slide_new(prs)
    header(s, "Assembly", "Every part fits through the back — proved with a swept column",
           "The rear plate is the only opening. So a part is installable only if a column "
           "swept from its seat out of the box misses every printed surface.")

    rows = [
        ["Module", "Envelope (mm)", "Swept column"],
        ["LCD1602 + backpack", "80.0 × 36.0", "0.00 mm³"],
        ["RC522 board", "60.0 × 40.0", "0.00 mm³"],
        ["R307 module", "44.1 × 20.0", "0.00 mm³"],
        ["ESP32 DevKit", "51.5 × 28.3", "0.00 mm³"],
        ["3010 fan", "30.0 × 30.0", "0.00 mm³"],
        ["hand + 4 mm hex key", "60.0 × 60.0", "clear"],
    ]
    text(s, ML, 2.16, 6.36, 0.24, "Every module clears the 104.8 × 149.0 mm rear opening",
         size=9.2, color=DIM, italic=True)
    table(s, ML, 2.46, 6.36, [2.52, 2.02, 1.82], rows, size=9.6, head_size=8.6,
          row_h=0.50, first_bold=True, colors={3: GREEN})

    rect(s, ML, 6.02, 6.36, 0.86, fill=PANEL2, line=LINE, lw=0.75, radius=0.05)
    text(s, ML + 0.22, 6.14, 6.0, 0.62,
         "Also proved: the plate leaves and returns without disturbing any module — 0.00 mm³ swept "
         "against the shell, the bracket and the ring.", size=8.8, color=SOFT, line=1.26)

    text(s, ML + 6.70, 1.98, 5.4, 0.26, "Order of assembly", size=10, color=AMBER, bold=True,
         caps=True, spc=160)
    order = [("1", "ESP32", "onto four stand-off bosses on the −X wall"),
             ("2", "RC522 + ring", "board drops in, one ring clamps both edges"),
             ("3", "R307", "two 23.5 mm posts, dog-bone bracket over it"),
             ("4", "LCD1602", "onto four bosses, the last thing visible from outside"),
             ("5", "fan", "into its Ø28 bore on four internal posts"),
             ("6", "rear plate", "four M3 into 9 mm bosses — closed")]
    y = 2.26
    for num, head, body in order:
        rect(s, ML + 6.70, y, 0.34, 0.34, fill=PANEL3, line=LINE, lw=0.6, radius=0.5)
        text(s, ML + 6.70, y + 0.035, 0.34, 0.28, num, size=10, color=AMBER, bold=True,
             align=PP_ALIGN.CENTER)
        text(s, ML + 7.16, y - 0.02, 4.9, 0.26, head, size=10, color=WHITE, bold=True)
        text(s, ML + 7.16, y + 0.24, 4.9, 0.4, body, size=8.6, color=DIM, line=1.2)
        y += 0.74

    rect(s, ML + 6.70, 6.72, 5.40, 0.0, fill=None)
    footer(s, i, n, "Assembly — physics audit §3; v3_design_notes.md §6, §10")
    notes(s, """
The interesting failure the audit caught: in v3.0 the RC522 was laid landscape, 60 mm across a
bay that is 58.35 mm wide. The board could not physically go in - in any orientation. That is
the kind of error you only find by sweeping the part through the space instead of looking at a
drawing.

The fix was to mount the reader portrait, which also widened the ligament between the RFID
window and the fingerprint window from 17.5 to 22.5 mm.
""")
    return s


# =============================================================  20  PRINT
def s20_print(prs, i, n):
    s = slide_new(prs)
    header(s, "Manufacturing", "Four parts, one bed, zero supports",
           "Printed on any 220 × 220 × 250 mm FDM printer. The orientation a slicer must see is "
           "baked into the STL triangles.")

    rows = [
        ["File", "x", "Volume", "Printed", "Footprint", "First layer"],
        ["01_MAIN_SHELL", "1", "115.2 cm³", "113.6 g", "110 × 155 × 43", "11,396 mm², 1 contour"],
        ["02_REAR_PLATE", "1", "53.8 cm³", "41.5 g", "110 × 155 × 5", "2,997 mm², 1 contour"],
        ["04_RC522_RING", "1", "2.2 cm³", "2.7 g", "43.6 × 76.0 × 2.6", "883 mm², 1 contour"],
        ["03_R307_BRACKET", "1", "1.0 cm³", "1.2 g", "36.8 × 14.0 × 3.2", "501 mm², 1 contour"],
        ["all four", "", "172.2 cm³", "159 g", "0.45 nozzle, 3 walls, 15 %", "no supports, no raft"],
    ]
    table(s, ML, 2.02, 7.90, [1.62, 0.34, 1.10, 0.96, 1.98, 1.90], rows, size=9.2,
          head_size=8.5, row_h=0.50, first_bold=True,
          colors={(5, 3): GREEN, (5, 2): GREEN}, align=[PP_ALIGN.LEFT, PP_ALIGN.CENTER] +
          [PP_ALIGN.LEFT] * 4)

    kpi(s, ML + 8.52, 2.02, 3.58, 1.26, "0.30 %", "of faces steeper than 60°, each bridging < 3 mm",
        GREEN, vsize=24, lsize=8.0)
    kpi(s, ML + 8.52, 3.42, 3.58, 1.26, "6.3", "sets from one 1 kg spool — 53 m of filament",
        CYAN, vsize=24, lsize=8.0)
    kpi(s, ML + 8.52, 4.82, 3.58, 1.26, "214", "slices checked: 0 self-intersections, 0 empty layers",
        AMBER, vsize=24, lsize=8.0)

    text(s, ML, 5.40, 7.9, 0.24, "Printer settings the print order specifies", size=10,
         color=AMBER, bold=True, caps=True, spc=160)
    settings = [("0.2 mm", "layer height"), ("3", "perimeters"), ("15–20 %", "infill"),
                ("3", "top/bottom skins"), ("PLA or PETG", "material"), ("none", "supports")]
    x = ML
    for val, lab in settings:
        rect(s, x, 5.70, 1.22, 0.58, fill=PANEL, line=LINE, lw=0.7, radius=0.06)
        text(s, x + 0.04, 5.76, 1.14, 0.24, val, size=9.8, color=CYAN, bold=True, align=PP_ALIGN.CENTER)
        text(s, x + 0.04, 6.02, 1.14, 0.22, lab, size=7.2, color=DIM, align=PP_ALIGN.CENTER,
             line=1.05)
        x += 1.28

    rect(s, ML, 6.44, 7.62, 0.46, fill=PANEL2, line=LINE, lw=0.7, radius=0.06)
    text(s, ML + 0.22, 6.54, 7.3, 0.26,
         "Every one of those four first layers is a single closed contour — islands on a first layer lift and shed debris.",
         size=8.8, color=SOFT)

    footer(s, i, n, "Printing — exports/README_PRINT_ORDER_v3.txt · physics audit §9")
    notes(s, """
The number to say: 159 grams, four parts, no supports, one spool prints six and a third sets.

The subtle engineering bit at the bottom: every part's first layer is one closed contour. A
printed island on the first layer is what peels off mid-print, so the audit checks for it on
all four files.
""")
    return s
