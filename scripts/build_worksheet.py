#!/usr/bin/env python3
"""Creative Ideation Worksheet — Astro Smart Attendance (print edition)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from ws_common import *  # noqa
import ws_common as W

INK_BLUE = HexColor("#1D4ED8")
PLUM = HexColor("#7C3AED")

TOTAL_SECTIONS = 9


# ------------------------------------------------------------------ helpers
def hand(c, x, y, text, size=10.4, color=INK_BLUE):
    return draw_text(c, x, y, text, "Caveat", size, color)


def card(c, x, y, w, h, fill=SOFT, stroke=LINE, r=8, lw=1):
    rrect(c, x, y, w, h, r, fill=fill, stroke=stroke, lw=lw)


def pill(c, x, y, text, fill, color, size=6.0, h=11, pad=5):
    w = tw(text, "Pop8", size) + 2 * pad
    rrect(c, x, y, w, h, h / 2, fill=fill)
    draw_text(c, x + pad, y + (h - size) / 2 + 0.6, text, "Pop8", size, color)
    return w


def sec(c, y, num, title, sub, accent=SAFFRON):
    """Section header with numbered tile, hairline and progress counter."""
    size = 27
    c.saveState()
    grad = [accent, HexColor("#E8590C")] if accent == SAFFRON else ([accent, HexColor("#0F766E")] if accent == TEAL else [NAVY, NAVY2])
    gradient(c, M, y - size, size, size, 7, grad, [0, 1])
    c.restoreState()
    lab = "%02d" % num
    w = tw(lab, "Pop9", 10.5)
    draw_text(c, M + (size - w) / 2, y - size + 9.4, lab, "Pop9", 10.5, Color(1, 1, 1))
    tx = M + size + 11
    draw_text(c, tx, y - 12.2, title.upper(), "Pop8", 12.0, NAVY)
    if sub:
        draw_text(c, tx, y - 23.6, sub, "Int5", 7.7, MUTED)
    # progress on the right
    counter = "%02d / %02d" % (num, TOTAL_SECTIONS)
    cwid = tracked_width(counter, "Pop8", 6.2, 1.0)
    tracked(c, PAGE_W - M - cwid, y - 12, counter, "Pop8", 6.2, HexColor("#B6C2D4"), 1.0)
    # hairline
    c.setStrokeColor(LINE)
    c.setLineWidth(0.9)
    c.line(tx, y - size - 6, PAGE_W - M, y - size - 6)
    return y - size - 16


def vbar_chart(c, x, top, w, h, rows, maxv, color=NAVY, label_w=86):
    """Horizontal bars for the shortlisting totals."""
    n = len(rows)
    gap = (h - n * 9) / n
    bh = gap
    plot_w = w - label_w - 34
    for i, (name, val, col, hi) in enumerate(rows):
        y = top - (i + 1) * (bh + 9) + 9
        draw_text(c, x, y + bh / 2 - 2.4, name, "Int6", 6.6, NAVY if hi else BODY)
        bx = x + label_w
        rrect(c, bx, y, plot_w, bh, bh / 2, fill=HexColor("#EDF1F7"))
        bw = plot_w * (val / maxv)
        rrect(c, bx, y, bw, bh, bh / 2, fill=col)
        draw_text(c, bx + bw + 6, y + bh / 2 - 2.6, str(val), "Pop8", 7.2, col)


# ===================================================================== PAGE 1
def page1(c):
    top = PAGE_H - 30
    hh = 206
    hx, hy = M, top - 6 - hh
    gradient(c, hx, hy, CW, hh, 12, [NAVY, HexColor("#15306B"), NAVY3], [0, 0.55, 1])
    c.saveState()
    p = c.beginPath()
    p.roundRect(hx, hy, CW, hh, 12)
    c.clipPath(p, stroke=0, fill=0)
    c.setStrokeColor(Color(1, 1, 1, 0.06))
    c.setLineWidth(16)
    c.circle(hx + CW - 16, hy + 6, 116, stroke=1, fill=0)
    c.circle(hx + CW - 16, hy + 6, 74, stroke=1, fill=0)
    c.setStrokeColor(Color(1, 1, 1, 0.035))
    c.setLineWidth(0.8)
    gy = int(hy)
    while gy < hy + hh:
        c.line(hx, gy, hx + CW, gy)
        gy += 14
    c.restoreState()

    tx = hx + 17
    kick = "SUN RISES INDIA   ·   GRADE 9   ·   ABPS RENUKOOT"
    kw = tracked_width(kick, "Pop7", 6.3, 0.9) + 22
    rrect(c, tx, top - 29, kw, 15, 7.5, fill=Color(1, 1, 1, 0.13), stroke=Color(1, 1, 1, 0.28), lw=0.7)
    c.setFillColor(GOLD)
    c.circle(tx + 8, top - 21.5, 2.1, stroke=0, fill=1)
    tracked(c, tx + 14, top - 24.2, kick, "Pop7", 6.3, Color(1, 1, 1), 0.9)

    draw_text(c, tx, top - 61, "ASTRO", "Pop9", 30.5, Color(1, 1, 1))
    draw_text(c, tx + tw("ASTRO ", "Pop9", 30.5), top - 61, "SMART", "Pop9", 30.5, GOLD)
    draw_text(c, tx, top - 90, "ATTENDANCE", "Pop9", 26.5, Color(1, 1, 1))
    c.setStrokeColor(SAFFRON)
    c.setLineWidth(2.4)
    c.line(tx, top - 97, tx + 116, top - 97)
    draw_text(c, tx, top - 112, "AI  +  IoT  +  Cloud   smart school attendance system", "Pop6", 8.6, HexColor("#7DD3FC"))

    para(c, tx, top - 122, 300,
         "A compact **ESP32 RFID attendance terminal** with **Astro AI 2.0 self-healing**, a **Firebase dashboard** and **automatic parent alerts** — offline-first, built from **low-cost local parts**.",
         size=8.2, color=HexColor("#D8E3F6"), bold_font="Int7", leading=12.2)

    c.setFillColor(SAFFRON)
    c.roundRect(tx, hy + 15, 3, 15, 1.5, stroke=0, fill=1)
    draw_text(c, tx + 10, hy + 25, "One tap. Attendance done. Parents informed.", "Caveat", 13.2, HexColor("#FFD9A8"))
    draw_text(c, tx + 10, hy + 16.6, "astro-smart-attendence.web.app", "Mono", 6.0, HexColor("#8FB0DC"))

    # team panel
    gx, gw = hx + CW - 190, 174
    gyy, gh = top - 18 - 180, 180
    rrect(c, gx, gyy, gw, gh, 10, fill=Color(1, 1, 1, 0.09), stroke=Color(1, 1, 1, 0.26), lw=0.8)
    tracked(c, gx + 11, gyy + gh - 16, "TEAM  ·  SUN RISES INDIA", "Pop8", 6.3, GOLD, 0.9)
    rows = [("Team captain", ["Shaurya Gupta"]),
            ("Members", ["Shaurya Gupta  ·  Anant Tiwari", "Devansh Dhakad  ·  Tejas Upadhyay", "Diwakar Singh"]),
            ("Mentor", ["Dr. Jayesh Shinde"]),
            ("School", ["ABPS Renukoot,", "Sonbhadra (U.P.)"]),
            ("Theme", ["SDG 9 — Industry, Innovation", "and Infrastructure"])]
    yy = gyy + gh - 29
    for k, lines in rows:
        draw_text(c, gx + 11, yy, k, "Int5", 6.3, Color(1, 1, 1, 0.6))
        for j, vl in enumerate(lines):
            draw_text(c, gx + 11, yy - 9.2 - j * 8.6, vl, "Pop6", 7.0, Color(1, 1, 1))
        yy -= 10.6 + 8.6 * len(lines)
        c.setStrokeColor(Color(1, 1, 1, 0.15))
        c.setLineWidth(0.5)
        c.setDash([2, 2])
        c.line(gx + 11, yy + 3.6, gx + gw - 11, yy + 3.6)
        c.setDash()

    # ---------------- proof strip
    y = hy - 28
    stats = [("≈ ₹1,500", "EST. COST PER UNIT", "battery"),
             ("< 2 sec", "PER STUDENT TAP", "clock"),
             ("OFFLINE", "SYNCS WHEN BACK", "wifi"),
             ("140 / 140", "FEATURE TESTS PASSING", "check")]
    bw = (CW - 3 * 8) / 4
    for i, (v, lab, ic) in enumerate(stats):
        bx = M + i * (bw + 8)
        card(c, bx, y - 38, bw, 38, fill=Color(1, 1, 1), stroke=LINE)
        c.setFillColor(SAFFRON_L if i % 2 == 0 else TEAL_L)
        c.circle(bx + 18, y - 19, 10.5, stroke=0, fill=1)
        glyph(c, ic, bx + 18, y - 19, 9, SAFFRON if i % 2 == 0 else TEAL, 1.05)
        draw_text(c, bx + 33, y - 16, v, "Pop8", 10.4, NAVY)
        tracked(c, bx + 33, y - 28, lab, "Pop7", 4.8, MUTED, 0.6)

    # ---------------- section 1
    y = y - 38 - 24
    y = sec(c, y, 1, "Problem focus", "Who feels it, when it happens, and what proof of improvement looks like")

    lw_, rw_ = 300, CW - 300 - 12
    ch = 200
    card(c, M, y - ch, lw_, ch, fill=SAFFRON_L, stroke=SAFFRON_B)
    c.setFillColor(SAFFRON)
    c.rect(M, y - ch, 3, ch, stroke=0, fill=1)
    label(c, M + 13, y - 17, "The problem we chose")
    yy = para(c, M + 13, y - 22, lw_ - 26,
              "Indian schools lose **10–15 minutes per class** to manual attendance. Across **15+ lakh schools**, paper registers are slow, easy to lose and open to **proxy attendance** — and the record never reaches the parent the same day.",
              size=8.1, color=BODY, leading=12.0)
    yy = para(c, M + 13, yy - 7, lw_ - 26,
              "Our answer: an **RFID terminal** that marks a student in **under two seconds**, keeps recording without internet, and alerts the parent automatically.",
              size=8.1, color=BODY, leading=12.0)
    ev_h = 46
    card(c, M + 13, yy - 10 - ev_h, lw_ - 26, ev_h, fill=Color(1, 1, 1, 0.55), stroke=AMBER_B, r=6, lw=0.8)
    c.setDash([2.4, 2])
    label(c, M + 22, yy - 24, "What we saw with our own eyes", AMBER_B, 6.1)
    c.setDash()
    para(c, M + 22, yy - 27, lw_ - 44,
         "Assembly queues for the register · two names ticked twice in the same period · late arrivals argued at the office · parents learning of absence after school.",
         size=7.3, color=BODY, leading=10.2)

    rx = M + lw_ + 12
    card(c, rx, y - ch, rw_, ch, fill=TEAL_L, stroke=TEAL_B)
    label(c, rx + 12, y - 17, "Discovery questions", TEAL)
    items = ["**Who** feels it? Teachers, students, parents, the school office",
             "**When?** Every period, worst at the first bell",
             "**What happens now?** Paper register, verbal roll-call",
             "**What would prove it worked?** Minutes saved, zero proxy, fast alerts"]
    yy = bullets(c, rx + 12, y - 24, rw_ - 24, items, size=7.4, leading=10.2, gap=3.4, mark="sq", mark_color=TEAL)
    card(c, rx + 12, yy - 50, rw_ - 24, 46, fill=Color(1, 1, 1, 0.6), stroke=TEAL, r=6, lw=0.8)
    label(c, rx + 20, yy - 16, "Success looks like", TEAL, 6.1)
    para(c, rx + 20, yy - 19, rw_ - 44, "30 students marked in **under 60 seconds**, no duplicate entries, and every parent alerted **within 5 minutes** of the period ending.", size=7.3, leading=10.2)

    # ---------------- voices
    y = y - ch - 20
    label(c, M, y, "What users told us — anonymised notes from discovery dialogues", MUTED, 6.2)
    y -= 9
    quotes = [("“Fifteen minutes gone every period, just calling out names. I could teach a whole concept in that time.”", "Class teacher · ABPS Renukoot"),
              ("“We find out our child was absent only when the day is over. By then the whole day is lost.”", "Parent · Renukoot")]
    qw = (CW - 10) / 2
    for i, (q, who) in enumerate(quotes):
        qx = M + i * (qw + 10)
        card(c, qx, y - 47, qw, 47, fill=CREAM, stroke=HexColor("#FDE68A"))
        draw_text(c, qx + 9, y - 17, "“", "Pop9", 19, GOLD)
        para(c, qx + 19, y - 7, qw - 29, q, size=7.3, color=NAVY, leading=10.0)
        tracked(c, qx + 19, y - 39, who.upper(), "Pop7", 5.1, MUTED, 0.7)
    y -= 47 + 18

    # ---------------- numbers
    label(c, M, y, "The size of the problem", MUTED, 6.2)
    y -= 9
    nums = [("10–15 min", "lost every period, every class", SAFFRON),
            ("15+ lakh", "schools running on paper registers", TEAL),
            ("≈95%", "cheaper than commercial systems", NAVY)]
    nw = (CW - 20) / 3
    for i, (v, lab, col) in enumerate(nums):
        nx = M + i * (nw + 10)
        card(c, nx, y - 38, nw, 38, fill=Color(1, 1, 1), stroke=LINE)
        c.setFillColor(col)
        c.rect(nx, y - 38, 2.6, 38, stroke=0, fill=1)
        draw_text(c, nx + 12, y - 19, v, "Pop9", 13.4, col)
        draw_text(c, nx + 12, y - 30, lab, "Int5", 6.8, MUTED)
    y = y - 38 - 20

    card(c, M, y - 42, CW, 42, fill=NAVY, stroke=None, r=10)
    glyph(c, "star", M + 19, y - 21, 8, GOLD, 1.0)
    para(c, M + 34, y - 10, CW - 50,
         "**In one line:** a low-cost RFID terminal that marks a class in under a minute, keeps recording when the internet drops, and tells parents the same minute — designed, built and measured by five Class 9 students.",
         size=7.6, color=Color(1, 1, 1), leading=10.6)
    return


# ===================================================================== PAGE 2
def page2(c):
    top = PAGE_H - 30
    y = top - 8
    y = sec(c, y, 2, "Brainstormed possibilities",
            "Ten ideas, generated without judgement and then filtered on purpose")

    card(c, M, y - 34, CW, 34, fill=SOFT, stroke=LINE)
    c.setFillColor(SAFFRON)
    c.rect(M, y - 34, 3, 34, stroke=0, fill=1)
    para(c, M + 14, y - 7, CW - 28,
         "Quantity first, judgement second. Every idea reached the board before anyone could criticise it — including the ones we later dropped.",
         size=7.8, leading=10.4)
    y = y - 34 - 13

    ideas = [
        ("QR code attendance, rotating", "A code that changes each minute; students scan it.", "card",
         "one screenshot defeats it", "TRIED & PARKED", HexColor("#92400E"), HexColor("#FEF3C7")),
        ("RFID card tap-in", "A school-issued card tapped at the door.", "chip",
         "no phone, no battery needed", "SELECTED", HexColor("#166534"), HexColor("#DCFCE7")),
        ("Teacher-confirmed register", "Teacher clears exceptions, signs off.", "book",
         "makes a tap an official record", "INCLUDED", HexColor("#166534"), HexColor("#DCFCE7")),
        ("NFC check-in, time window", "Phone tapped inside the period window.", "phone",
         "assumes every student has a phone", "PARKED", HexColor("#92400E"), HexColor("#FEF3C7")),
        ("Face recognition", "A camera identifies the student.", "person",
         "biometrics, consent, cost", "REJECTED", HexColor("#991B1B"), HexColor("#FEE2E2")),
        ("Bluetooth proximity", "A beacon notices the student nearby.", "spark",
         "range guesses, false hits", "REJECTED", HexColor("#991B1B"), HexColor("#FEE2E2")),
        ("Offline attendance, sync later", "Stored on the device, uploaded later.", "save",
         "the register survives a cut", "CORE", HexColor("#166534"), HexColor("#DCFCE7")),
        ("Duplicate & late flags", "Repeat taps, late entries, wrong periods.", "flag",
         "ends the office argument", "INCLUDED", HexColor("#166534"), HexColor("#DCFCE7")),
        ("Parent / student summary", "Period and day summaries by email.", "mail",
         "same-day news for the family", "INCLUDED", HexColor("#166534"), HexColor("#DCFCE7")),
        ("Audit log for corrections", "Every edit stored with who and why.", "lock",
         "a correction can be checked", "INCLUDED", HexColor("#166534"), HexColor("#DCFCE7")),
    ]
    tw_ = (CW - 10) / 2
    th = 52
    for i, (title, desc, ic, verdict, tag, tagc, tagbg) in enumerate(ideas):
        col, row = i % 2, i // 2
        bx = M + col * (tw_ + 10)
        by = y - (row + 1) * th - row * 6
        card(c, bx, by, tw_, th, fill=Color(1, 1, 1), stroke=LINE)
        rrect(c, bx + 9, by + th - 32, 23, 23, 6.2, fill=SAFFRON_L if i % 2 == 0 else TEAL_L)
        glyph(c, ic, bx + 20.5, by + th - 20.5, 11.6, SAFFRON if i % 2 == 0 else TEAL, 1.15)
        draw_text(c, bx + 39, by + th - 14.5, title, "Pop7", 7.6, NAVY)
        para(c, bx + 39, by + th - 18, tw_ - 50, desc, size=6.7, leading=8.6)
        draw_text(c, bx + 39, by + 14.4, verdict, "Int5", 6.1, HexColor("#B45309"))
        pill(c, bx + 39, by + 4.4, tag, tagbg, tagc, 5.2, 9.4, 4.2)
    y = y - 5 * th - 4 * 6 - 14

    # filters
    label(c, M, y, "The three filters every idea had to pass", MUTED, 6.2)
    y -= 9
    filters = [("Can five students build it?", "No lab, no funding, no machined parts — hands, a breadboard and a 3D printer.", "gear"),
               ("Can a school afford it?", "Under ₹2,000 per classroom, or it stays a slide in a presentation.", "chart"),
               ("Does it respect the student?", "No biometrics, no phone ownership, no continuous tracking.", "lock")]
    for i, (h, d, ic) in enumerate(filters):
        by = y - (i + 1) * 24 - i * 4
        card(c, M, by, CW, 24, fill=SOFT if i % 2 == 0 else Color(1, 1, 1), stroke=LINE, r=7)
        glyph(c, ic, M + 17, by + 12, 9.2, SAFFRON if i % 2 == 0 else TEAL, 1.0)
        draw_text(c, M + 32, by + 9, h, "Pop7", 7.7, NAVY)
        draw_text(c, M + 178, by + 9, d, "Int5", 6.9, MUTED)
    y = y - 3 * 24 - 8 - 15

    card(c, M, y - 36, CW, 36, fill=NAVY, stroke=None, r=10)
    tracked(c, M + 14, y - 13.5, "WHAT SURVIVED ALL THREE FILTERS", "Pop8", 6.0, GOLD, 1.2)
    draw_text(c, M + 14, y - 27, "RFID tap   +   offline buffer   +   teacher confirmation", "Pop8", 10.2, Color(1, 1, 1))
    para(c, M + CW - 168, y - 12, 156,
         "Fast enough to be used, cheap enough to own, private enough to defend.",
         size=6.5, color=HexColor("#BFDBFE"), leading=8.8)
    y = y - 36 - 17

    label(c, M, y, "Every idea against the three filters", MUTED, 6.2)
    y -= 8
    grid = [("QR rotating code", "yes", "yes", "weak"),
            ("RFID card tap-in", "yes", "yes", "strong"),
            ("Teacher-confirmed register", "yes", "yes", "strong"),
            ("NFC time window", "yes", "yes", "weak"),
            ("Face recognition", "no", "no", "no"),
            ("Bluetooth proximity", "yes", "partly", "weak"),
            ("Offline + sync later", "partly", "yes", "strong"),
            ("Duplicate & late flags", "yes", "yes", "strong"),
            ("Parent / student summary", "yes", "yes", "yes"),
            ("Audit log", "yes", "yes", "yes")]
    rh = 16.4
    colw = [CW - 176, 58, 58, 60]
    total_h = 18 + rh * len(grid)
    tab_top = y
    c.saveState()
    pth = c.beginPath()
    pth.roundRect(M, tab_top - total_h, CW, total_h, 8)
    c.clipPath(pth, stroke=0, fill=0)
    c.setFillColor(NAVY)
    c.rect(M, tab_top - 18, CW, 18, stroke=0, fill=1)
    for i in range(len(grid)):
        if i % 2:
            c.setFillColor(SOFT)
            c.rect(M, tab_top - 18 - (i + 1) * rh, CW, rh, stroke=0, fill=1)
    c.setStrokeColor(LINE)
    c.setLineWidth(0.5)
    for i in range(len(grid) + 1):
        c.line(M, tab_top - 18 - i * rh, M + CW, tab_top - 18 - i * rh)
    c.restoreState()
    rrect(c, M, tab_top - total_h, CW, total_h, 8, fill=None, stroke=LINE, lw=1)
    heads = ["Idea", "Five students?", "Affordable?", "Respectful?"]
    xs, xx = [], M
    for w in colw:
        xs.append(xx)
        xx += w
    for i, h in enumerate(heads):
        wsum = tw(h, "Pop7", 5.9)
        tx = xs[i] + 9 if i == 0 else xs[i] + (colw[i] - wsum) / 2
        draw_text(c, tx, tab_top - 12.2, h, "Pop7", 5.8, Color(1, 1, 1))
    marks = {"yes": (GREEN, "yes"), "no": (HexColor("#DC2626"), "no"), "partly": (AMBER_B, "partly"),
             "strong": (GREEN, "strong"), "weak": (AMBER_B, "weak")}
    for i, row in enumerate(grid):
        ry = tab_top - 18 - (i + 1) * rh
        cy = ry + rh / 2
        draw_text(c, M + 9, cy - 2.4, row[0], "Int5", 6.9, BODY)
        for j in range(3):
            col, lab = marks[row[j + 1]]
            wsum = tw(lab, "Int6", 6.4)
            draw_text(c, xs[j + 1] + (colw[j + 1] - wsum) / 2, cy - 2.3, lab, "Int6", 6.4, col)
    return


# ===================================================================== PAGE 3
def page3(c):
    top = PAGE_H - 30
    y = top - 8
    y = sec(c, y, 3, "Concept map",
            "One chain from the student at the door to a number the school can defend", TEAL)

    stages = [("User / setting", "Student at the door; teacher and period fixed by the timetable", "people", BLUE_L, NAVY),
              ("Problem trigger", "Paper register — slow, proxy-prone, easy to lose", "bolt", SAFFRON_L, SAFFRON),
              ("Sensor / input", "RC522 reads the card in under two seconds", "card", TEAL_L, TEAL),
              ("Process / decision", "ESP32 validates, de-duplicates, buffers offline", "chip", BLUE_L, NAVY),
              ("Output / action", "Firebase sync, dashboards, automatic parent email", "cloud", TEAL_L, TEAL),
              ("Measurable benefit", "15 minutes saved per class, zero proxy, ≈95% cheaper", "chart", GREEN_L, GREEN)]
    n = len(stages)
    gap = 9
    bw = (CW - gap * (n - 1)) / n
    bh = 100
    for i, (h, d, ic, bg, col) in enumerate(stages):
        bx = M + i * (bw + gap)
        card(c, bx, y - bh, bw, bh, fill=bg, stroke=col, lw=1)
        c.setFillColor(col)
        c.roundRect(bx, y - 14, bw, 14, 8, stroke=0, fill=1)
        c.rect(bx, y - 14, bw, 6, stroke=0, fill=1)
        tracked(c, bx + 8, y - 9.6, "%02d" % (i + 1), "Pop8", 5.8, Color(1, 1, 1), 0.8)
        glyph(c, ic, bx + bw / 2, y - 37, 14, col, 1.2)
        para(c, bx + 6, y - 47, bw - 12, "**" + h + "**", size=6.8, color=NAVY, leading=8.4, align="center")
        para(c, bx + 6, y - 64, bw - 12, d, size=6.3, color=MUTED, leading=8.2, align="center")
        if i < n - 1:
            arrow(c, bx + bw + 1.5, y - bh / 2, bx + bw + gap - 1.5, y - bh / 2, SAFFRON, 1.3, 3.6)
    y = y - bh - 14

    # direction
    gradient(c, M, y - 58, CW, 58, 10, [NAVY, HexColor("#173A7A"), TEAL], [0, 0.6, 1])
    tracked(c, M + 16, y - 18, "PROPOSED DIRECTION", "Pop8", 6.1, GOLD, 1.3)
    draw_text(c, M + 16, y - 34, "Astro Smart Attendance", "Pop9", 14.5, Color(1, 1, 1))
    draw_text(c, M + 16, y - 47, "Privacy-first  ·  Offline-first  ·  AI self-healing  ·  low-cost by design", "Pop6", 7.3, HexColor("#BFDBFE"))
    cwid = tw("OUR CONCEPT", "Pop8", 7.0) + 34
    rrect(c, M + CW - cwid - 16, y - 37, cwid, 18, 9, fill=SAFFRON)
    draw_text(c, M + CW - cwid - 16 + 10, y - 31, "OUR CONCEPT", "Pop8", 7.0, Color(1, 1, 1))
    y = y - 58 - 20

    # what each link must prove
    label(c, M, y, "What each link has to prove before we call it true", MUTED, 6.2)
    y -= 9
    checks = [("User", "We solve a moment that repeats every period, not a textbook problem."),
              ("Trigger", "The pain is measured in minutes and errors, not in adjectives."),
              ("Input", "A tap is faster and fairer than a teacher reading out names."),
              ("Process", "The logic stays correct through power cuts, Wi-Fi loss and repeat taps."),
              ("Output", "The record reaches teacher and parent without extra work for either."),
              ("Benefit", "The gain shows up in a real classroom of 30, not in a simulation.")]
    cw2 = (CW - 2 * 9) / 3
    for i, (h, d) in enumerate(checks):
        col_i, row = i % 3, i // 3
        bx = M + col_i * (cw2 + 9)
        by = y - (row + 1) * 47 - row * 7
        card(c, bx, by, cw2, 47, fill=Color(1, 1, 1), stroke=LINE)
        num_badge(c, bx + 9, by + 47 - 22, 13, i + 1, TEAL, 3.4, 6.8)
        draw_text(c, bx + 28, by + 47 - 17, h, "Pop7", 7.7, NAVY)
        para(c, bx + 9, by + 47 - 25, cw2 - 18, d, size=6.8, leading=9.0)
    y = y - 2 * 47 - 7 - 20

    # data pathway
    label(c, M, y, "What happens to one tap — the data pathway", MUTED, 6.2)
    y -= 9
    path = [("Tap", "card UID read"), ("Tag", "student + period"), ("Check", "duplicate? late?"),
            ("Store", "local buffer"), ("Sync", "Firebase write"), ("Alert", "parent email"), ("Review", "teacher confirms")]
    pw = (CW - 6 * 8) / 7
    for i, (h, d) in enumerate(path):
        bx = M + i * (pw + 8)
        card(c, bx, y - 38, pw, 38, fill=Color(1, 1, 1), stroke=LINE, r=6)
        draw_text(c, bx + 7, y - 13, h, "Pop7", 7.2, NAVY)
        para(c, bx + 7, y - 16, pw - 14, d, size=6.2, color=MUTED, leading=7.8)
        c.setFillColor(TEAL if i % 2 else SAFFRON)
        c.circle(bx + pw - 7, y - 8, 1.7, stroke=0, fill=1)
    y = y - 38 - 20

    # benefit table + open questions
    rows = [["**Teacher**", "15 minutes returned per class", "≈ one extra teaching hour per week"],
            ["**Student**", "No queue, no roll-call, no proxy blame", "Attendance visible the same day"],
            ["**Parent**", "Absence message before the day ends", "Same-day action, not next-week surprise"],
            ["**School office**", "One trusted register, exportable", "Reports without re-entering data"]]
    th_ = draw_table(c, M, y, [84, 210, CW - 294], ["Who", "What changes", "What we measure"], rows,
                     size=7.3, header_h=18, pad=5.2, min_row=16, align=["left", "left", "left"], round_r=8)
    y = y - th_ - 20

    label(c, M, y, "Unanswered questions we are carrying into validation", MUTED, 6.2)
    y -= 9
    open_q = ["If a card is lost, what stops another student using it before the office reissues it?",
              "Two students tap within the same second — does the buffer keep both, in the right order?",
              "What exactly does the teacher see on the confirmation screen, and how is a mistake corrected?"]
    for i, q in enumerate(open_q):
        by = y - (i + 1) * 21 - i * 4
        card(c, M, by, CW, 21, fill=Color(1, 1, 1), stroke=LINE, r=6)
        draw_text(c, M + 12, by + 7.6, "?", "Pop8", 8.2, SAFFRON)
        draw_text(c, M + 24, by + 7.6, q, "Int5", 7.1, BODY)
    y = y - 3 * 21 - 8 - 20

    card(c, M, y - 44, CW, 44, fill=CREAM, stroke=HexColor("#FDE68A"))
    label(c, M + 14, y - 15, "The rule we keep coming back to", HexColor("#B45309"), 6.1)
    draw_text(c, M + 14, y - 33, "“If the internet dies, the register must still work.”", "Caveat", 15.0, HexColor("#7C2D12"))
    para(c, M + CW - 196, y - 14, 184,
         "A rule that decided the architecture: the buffer came before the cloud, not after it.",
         size=6.4, color=HexColor("#92400E"), leading=8.8)
    return


# ===================================================================== PAGE 4
def page4(c):
    top = PAGE_H - 30
    y = top - 8
    y = sec(c, y, 4, "Shortlisting matrix",
            "Scored 1 to 5 together in the lab — evidence first, opinions second")

    cols = [127, 49, 63, 67, 47, 64, 39, 71.27]
    if abs(sum(cols) - CW) >= 1.2:
        raise SystemExit('cols %s vs CW %s' % (sum(cols), CW))
    header = ["Candidate concept", "Novelty", "Feasibility", "Affordability", "Impact", "Prototype potential", "Total", "Rank"]
    data = [
        ("Astro Smart Attendance", "ESP32 + RFID + Firebase + AI 2.0", [5, 5, 5, 5, 4], 24, "#1"),
        ("QR rotating code only", "Screen-based, no reader hardware", [4, 4, 5, 3, 4], 20, "#2"),
        ("Simpler digital register", "Teacher tablet or web form", [2, 5, 5, 3, 3], 18, "#3"),
        ("Sensor / app-only system", "Phone app acts as the reader", [3, 4, 3, 4, 3], 17, "#4"),
        ("Community / service model", "Shared kiosk per corridor", [3, 4, 5, 3, 2], 17, "#4"),
        ("Face recognition terminal", "Camera identification at the door", [4, 3, 2, 4, 2], 15, "#6"),
    ]
    header_h, row_h = 25, 36
    total_h = header_h + row_h * len(data)
    tab_top = y - 2
    c.saveState()
    p = c.beginPath()
    p.roundRect(M, tab_top - total_h, CW, total_h, 10)
    c.clipPath(p, stroke=0, fill=0)
    c.setFillColor(NAVY)
    c.rect(M, tab_top - header_h, CW, header_h, stroke=0, fill=1)
    c.setFillColor(GREEN_L)
    c.rect(M, tab_top - header_h - row_h, CW, row_h, stroke=0, fill=1)
    c.setFillColor(SOFT)
    for i in (1, 3, 5):
        c.rect(M, tab_top - header_h - (i + 1) * row_h, CW, row_h, stroke=0, fill=1)
    c.setStrokeColor(LINE)
    c.setLineWidth(0.6)
    for i in range(len(data) + 1):
        c.line(M, tab_top - header_h - i * row_h, M + CW, tab_top - header_h - i * row_h)
    c.restoreState()
    rrect(c, M, tab_top - total_h, CW, total_h, 10, fill=None, stroke=LINE, lw=1)

    xs, x = [], M
    for w in cols:
        xs.append(x)
        x += w
    for i, h in enumerate(header):
        size = 6.3 if i == 0 else 5.9
        wsum = tw(h, "Pop7", size)
        tx = xs[i] + 10 if i == 0 else xs[i] + (cols[i] - wsum) / 2
        draw_text(c, tx, tab_top - 15.4, h, "Pop7", size, Color(1, 1, 1))

    colmap = {5: (GREEN_L, HexColor("#166534")), 4: (BLUE_L, HexColor("#1E40AF")),
              3: (HexColor("#FEF3C7"), HexColor("#92400E")), 2: (RED_L, RED_D)}
    for r, (name, sub, scores, tot, rank) in enumerate(data):
        ry = tab_top - header_h - r * row_h
        cy = ry - row_h / 2
        draw_text(c, xs[0] + 10, cy + 3.2, name, "Int7", 7.6, NAVY)
        draw_text(c, xs[0] + 10, cy - 6.0, sub, "Int5", 6.2, MUTED)
        if r == 0:
            c.setFillColor(GREEN)
            c.roundRect(xs[0] + 1.6, ry - row_h + 2, 2.6, row_h - 4, 1.3, stroke=0, fill=1)
        for j, s in enumerate(scores):
            bg, fg = colmap[s]
            c.setFillColor(bg)
            c.circle(xs[j + 1] + cols[j + 1] / 2, cy, 8.8, stroke=0, fill=1)
            wsum = tw(str(s), "Pop8", 8.2)
            draw_text(c, xs[j + 1] + (cols[j + 1] - wsum) / 2, cy - 2.9, str(s), "Pop8", 8.2, fg)
        wsum = tw(str(tot), "Pop9", 10.8)
        draw_text(c, xs[6] + (cols[6] - wsum) / 2, cy - 3.9, str(tot), "Pop9", 10.8, NAVY)
        rw = tw(rank, "Pop8", 6.8) + 12
        rrect(c, xs[7] + (cols[7] - rw) / 2, cy - 6.6, rw, 13.2, 6.6,
              fill=GREEN if r == 0 else HexColor("#E2E8F0"))
        draw_text(c, xs[7] + (cols[7] - rw) / 2 + 6, cy - 2.0, rank, "Pop8", 6.8,
                  Color(1, 1, 1) if r == 0 else NAVY)
    y = tab_top - total_h - 20

    # bar chart + scoring note
    label(c, M, y, "Totals at a glance", MUTED, 6.2)
    y -= 8
    chart_rows = [(d[0], d[3], GREEN if i == 0 else (HexColor("#93A5BE") if i > 1 else SAFFRON), i == 0)
                  for i, d in enumerate(data)]
    vbar_chart(c, M, y, 292, 88, chart_rows, 25, label_w=104)
    hand(c, M + 300, y - 10, "a 9-point gap", 9.8, HexColor("#7C3AED"))
    hand(c, M + 300, y - 22, "between building", 9.8, HexColor("#7C3AED"))
    hand(c, M + 300, y - 34, "and watching", 9.8, HexColor("#7C3AED"))

    nx = M + 392
    card(c, nx, y - 88, CW - 392, 88, fill=SOFT, stroke=LINE)
    c.setFillColor(SAFFRON)
    c.rect(nx, y - 88, 2.6, 88, stroke=0, fill=1)
    label(c, nx + 11, y - 14, "Scoring note", SAFFRON, 5.9)
    para(c, nx + 11, y - 17, CW - 414,
         "These are **initial team hypotheses, not measured results**. Each option was scored **1–5** in a team meeting, evidence from discovery dialogues was cited, and the shortlist was revised twice.",
         size=6.6, leading=9.0)
    y = y - 88 - 20

    # evidence behind scores
    label(c, M, y, "Evidence behind the scores", MUTED, 6.2)
    y -= 9
    ev = [("Novelty 5", "No RFID terminal with on-device self-healing exists in our price band; teachers had not seen one."),
          ("Feasibility 5", "The prototype already reads cards, writes to Firebase and survives a Wi-Fi cut in the lab."),
          ("Affordability 5", "The bill of materials works out to roughly ₹1,500 per unit, costed from real parts, not retail guesses."),
          ("Impact 5", "Every teacher we spoke to placed attendance in their top two daily time losses."),
          ("Prototype 4", "The 3D-printed case and parent-email templates are still being refined.")]
    for i, (k, v) in enumerate(ev):
        by = y - (i + 1) * 22 - i * 3.5
        card(c, M, by, CW, 22, fill=Color(1, 1, 1) if i % 2 else SOFT, stroke=LINE, r=6)
        c.setFillColor(GREEN if i < 4 else SAFFRON)
        c.circle(M + 13, by + 11, 2.1, stroke=0, fill=1)
        draw_text(c, M + 23, by + 8.0, k, "Pop7", 7.2, NAVY)
        draw_text(c, M + 100, by + 8.0, v, "Int5", 6.9, BODY)
    y = y - 5 * 22 - 4 * 3.5 - 16

    # rejected
    card(c, M, y - 46, CW, 46, fill=RED_L, stroke=HexColor("#FCA5A5"), r=9)
    label(c, M + 14, y - 14, "Rejected — and we can say why", RED_D, 6.1)
    para(c, M + 14, y - 17.5, CW - 28,
         "**Face recognition** finished last at 15. A camera in every corridor, biometric templates of children we could not guarantee to protect, and a cost five times our budget. Speed alone could not justify it — so it left the shortlist, not the conversation.",
         size=7.3, color=HexColor("#7F1D1D"), leading=10.2)
    y = y - 46 - 16

    label(c, M, y, "How the ranking moved once evidence arrived", MUTED, 6.2)
    y -= 8
    rows = [["**Astro Smart Attendance**", "21 → 24", "Costed bill of materials landed near ₹1,500, well under the ₹2,300 we feared"],
            ["**QR rotating code**", "23 → 20", "A code shared on a group chat cannot be trusted for records"],
            ["**Simpler digital register**", "16 → 18", "Cheaper than expected, but still costs the teacher time"],
            ["**Face recognition**", "19 → 15", "Privacy and camera cost pulled it down after the product comparison"]]
    th_ = draw_table(c, M, y, [150, 60, CW - 210], ["Concept", "First → final", "What changed the score"],
                     rows, size=7.0, header_h=16, pad=4.4, min_row=14.6,
                     align=["left", "center", "left"], round_r=8)
    return


# ===================================================================== PAGE 5
def page5(c):
    top = PAGE_H - 30
    y = top - 8
    y = sec(c, y, 5, "Selected concept and reason",
            "The idea we are building, and the honest case for why it deserves to win", TEAL)

    sh = 86
    c.saveState()
    p = c.beginPath()
    p.roundRect(M, y - sh, CW, sh, 11)
    c.clipPath(p, stroke=0, fill=0)
    c.linearGradient(M, y - sh, M + CW, y, [NAVY, HexColor("#1E3A8A"), TEAL], [0, 0.62, 1])
    c.setFillColor(Color(1, 1, 1, 0.045))
    c.circle(M + CW - 34, y - 16, 84, stroke=0, fill=1)
    c.restoreState()
    tracked(c, M + 16, y - 18, "SELECTED CONCEPT", "Pop8", 6.1, GOLD, 1.3)
    draw_text(c, M + 16, y - 35, "Astro Smart Attendance", "Pop9", 17.5, Color(1, 1, 1))
    para(c, M + 16, y - 38, CW - 40,
         "A privacy-first terminal built on **ESP32 + RC522 reader + LCD1602**. The student taps a card; the system records **time, class, period and a pseudonymous ID** in under two seconds. **Astro AI 2.0** validates each entry, flags duplicates and late arrivals, buffers offline and syncs to **Firebase**. The teacher confirms exceptions; the parent gets an email. **No face recognition. No phone required.**",
         size=7.7, color=HexColor("#DCE7F8"), leading=10.6)
    c.saveState()
    c.translate(M + CW - 74, y - 22)
    c.rotate(7)
    rrect(c, -34, -10, 74, 19, 9.5, fill=GOLD)
    draw_text(c, -22, -3.6, "CHOSEN", "Pop8", 7.0, NAVY)
    c.restoreState()
    y = y - sh - 18

    whys = [("Addresses the real problem", "Saves 10–15 minutes every period, removes proxy entries and leaves a timestamped record.", "check", GREEN),
            ("Buildable by five students", "ESP32, RC522, LCD and a printed case — a working prototype, not a slide.", "gear", TEAL),
            ("Around 95% cheaper", "An estimated ₹1,500 per unit against ₹30,000+ for commercial kits — within reach of any school.", "chart", SAFFRON),
            ("Measurable from day one", "Time per class, duplicate rejection, sync accuracy and teacher rating — all observable.", "clock", NAVY)]
    ww = (CW - 10) / 2
    for i, (h, d, ic, col) in enumerate(whys):
        col_i, row = i % 2, i // 2
        bx = M + col_i * (ww + 10)
        by = y - (row + 1) * 40 - row * 5
        card(c, bx, by, ww, 40, fill=Color(1, 1, 1), stroke=LINE)
        rrect(c, bx + 9, by + 40 - 22, 15, 15, 4.5, fill=SOFT)
        glyph(c, ic, bx + 16.5, by + 40 - 14.5, 8.4, col, 1.05)
        draw_text(c, bx + 29, by + 40 - 13, h, "Pop7", 7.5, NAVY)
        para(c, bx + 9, by + 40 - 18, ww - 18, d, size=6.5, leading=8.4)
    y = y - 2 * 40 - 5 - 12

    label(c, M, y, "How a student is marked — five steps, under two seconds", MUTED, 6.2)
    y -= 11
    steps = [("Tap card", "Student taps their RFID card at the classroom door.", "card"),
             ("AI validates", "Astro AI 2.0 checks ID, period, duplicates and device health.", "gear"),
             ("Display confirms", "LCD shows the name and “Present” with a short beep.", "screen"),
             ("Cloud syncs", "Firebase updates dashboards; entries buffer if Wi-Fi is down.", "cloud"),
             ("Parent informed", "Automatic email for present, late or absent.", "mail")]
    sw = (CW - 4 * 8) / 5
    sh_ = 64
    for i, (h, d, ic) in enumerate(steps):
        bx = M + i * (sw + 8)
        card(c, bx, y - sh_, sw, sh_, fill=SAFFRON_L if i % 2 == 0 else TEAL_L,
             stroke=SAFFRON_B if i % 2 == 0 else TEAL_B)
        c.setFillColor(SAFFRON if i % 2 == 0 else TEAL)
        c.circle(bx + 15, y - 15, 8.2, stroke=0, fill=1)
        wn = tw(str(i + 1), "Pop9", 8.0)
        draw_text(c, bx + 15 - wn / 2, y - 17.9, str(i + 1), "Pop9", 8.0, Color(1, 1, 1))
        draw_text(c, bx + 27, y - 17.2, h, "Pop7", 6.8, NAVY)
        glyph(c, ic, bx + sw / 2, y - 28, 10, NAVY if i % 2 == 0 else TEAL, 1.1)
        para(c, bx + 6, y - 35, sw - 12, d, size=6.0, color=BODY, leading=7.6, align="center")
    y = y - sh_ - 11

    # system table
    label(c, M, y, "System at a glance", MUTED, 6.2)
    y -= 8
    rows = [["**Controller**", "ESP32 DevKit V1 — Wi-Fi, OTA updates, offline logic"],
            ["**Input**", "RC522 13.56 MHz RFID reader + school-issued card"],
            ["**Feedback**", "LCD1602 I2C display + buzzer"],
            ["**Cloud**", "Firebase Auth + Realtime Database + Hosting"],
            ["**Intelligence**", "Astro AI 2.0 — 11 self-healing diagnostic checks"],
            ["**Enclosure**", "3D-printed case, designed in Blender"]]
    th_ = draw_table(c, M, y, [104, CW - 104], ["Part", "What it does"], rows, size=6.9, header_h=15,
                     pad=3.4, min_row=12.6, align=["left", "left"], round_r=8)
    y = y - th_ - 12

    # what we left out
    label(c, M, y, "What we deliberately left out — and why", MUTED, 6.2)
    y -= 10
    outs = [("Face recognition", "A camera on children costs more trust than the speed is worth.", "REJECTED"),
            ("Student phone app", "Not every student owns a phone. A card works for all.", "PARKED"),
            ("Full ERP replacement", "Fees, exams and report cards stay out of scope.", "OUT OF SCOPE"),
            ("Cloud-only design", "No network, no register. The buffer comes first.", "REPLACED")]
    ow = (CW - 30) / 4
    for i, (h, d, tag) in enumerate(outs):
        bx = M + i * (ow + 10)
        card(c, bx, y - 44, ow, 44, fill=Color(1, 1, 1), stroke=LINE)
        draw_text(c, bx + 9, y - 12.5, h, "Pop7", 7.2, NAVY)
        para(c, bx + 9, y - 15.5, ow - 18, d, size=6.2, leading=8.0)
        tw_ = tw(tag, "Pop8", 4.6) + 9
        rrect(c, bx + 9, y - 41.5, tw_, 8.8, 4.4, fill=SOFT)
        draw_text(c, bx + 13, y - 39.2, tag, "Pop8", 4.6, MUTED)
    y = y - 44 - 10

    y = y - 14 - 6

    label(c, M, y, "Who owns which part of the build", MUTED, 6.2)
    y -= 8
    roles = [["**Shaurya Gupta**", "Team captain", "Firmware and cloud", "Card read, Firebase, AI health checks"],
             ["**Anant Tiwari**", "Ideation and research", "User interviews, requirement notes", "Discovery dialogues and comparison"],
             ["**Tejas Upadhyay**", "Hardware integration", "Reader wiring, power, enclosure fit", "Bench tests and fault finding"],
             ["**Diwakar Singh**", "Product design", "3D enclosure, mounting, finish", "Printable case for the door"],
             ["**Devansh Dhakad**", "Testing and docs", "Test log, stress runs, this worksheet", "Evidence for every claim"]]
    th_ = draw_table(c, M, y, [96, 92, 150, CW - 338], ["Member", "Role", "Owns", "Deliverable"],
                     roles, size=6.8, header_h=16, pad=4.0, min_row=13.2,
                     align=["left", "left", "left", "left"], round_r=8)
    y = y - th_ - 20

    label(c, M, y, "The first week, if the school gives us one classroom", MUTED, 6.2)
    y -= 10
    week = [("MON–TUE", "Bench test", "Read 30 cards, confirm every entry lands in Firebase.", SAFFRON),
            ("WED", "Enrol", "Photograph-free card mapping; no personal data beyond name and class.", TEAL),
            ("THU–FRI", "Live period", "One real class marks attendance with the terminal beside the register.", NAVY),
            ("SAT", "Compare", "Count the differences between our register and the teacher's.", GREEN)]
    ww2 = (CW - 3 * 8) / 4
    for i, (day, h, d, col) in enumerate(week):
        bx = M + i * (ww2 + 8)
        card(c, bx, y - 50, ww2, 50, fill=Color(1, 1, 1), stroke=LINE)
        c.setFillColor(col)
        c.roundRect(bx + 9, y - 16, tw(day, "Pop8", 5.0) + 12, 10.5, 5.2, stroke=0, fill=1)
        draw_text(c, bx + 15, y - 13.2, day, "Pop8", 5.0, Color(1, 1, 1))
        draw_text(c, bx + 9, y - 25.5, h, "Pop7", 7.2, NAVY)
        para(c, bx + 9, y - 28.5, ww2 - 18, d, size=6.2, leading=8.0)
    return


# ===================================================================== PAGE 6
def page6(c):
    top = PAGE_H - 30
    y = top - 8
    y = sec(c, y, 6, "Initial system sketch",
            "Labelled block diagram: user, sensor, controller, output, power and the human confirmation step")

    fh = 274
    card(c, M, y - fh, CW, fh, fill=CREAM, stroke=HexColor("#CBD5E1"), r=10, lw=1)
    c.setDash([3, 3])
    rrect(c, M + 5, y - fh + 5, CW - 10, fh - 10, 7, fill=None, stroke=HexColor("#E8E2D2"), lw=0.7)
    c.setDash()
    c.setFillColor(HexColor("#F0EADC"))
    gx = M + 12
    while gx < M + CW - 12:
        gy = y - fh + 12
        while gy < y - 12:
            c.circle(gx, gy, 0.48, stroke=0, fill=1)
            gy += 12
        gx += 12

    def blk(x, ytop, w, h, title, sub, ic, fill, stroke, dark=False):
        rrect(c, x, ytop - h, w, h, 8, fill=fill, stroke=stroke, lw=1.15)
        glyph(c, ic, x + w / 2, ytop - 15, 11.5, Color(1, 1, 1) if dark else stroke, 1.1)
        para(c, x + 4, ytop - 22, w - 8, "**" + title + "**", size=6.7,
             color=Color(1, 1, 1) if dark else NAVY, leading=8.2, align="center", bold_font="Pop7")
        para(c, x + 5, ytop - 34, w - 10, sub, size=6.0,
             color=Color(0.85, 0.89, 0.96) if dark else MUTED, leading=7.6, align="center")

    HB = 56
    r1 = y - 26
    b1w, b2w, b3w, b4w = 96, 100, 118, 99
    gap1 = (CW - 24 - (b1w + b2w + b3w + b4w)) / 3
    x1 = M + 12
    blk(x1, r1, b1w, HB, "STUDENT", "RFID ID card · class & period", "people", BLUE_L, NAVY)
    x2 = x1 + b1w + gap1
    blk(x2, r1, b2w, HB, "RC522 READER", "13.56 MHz · tap < 2 s", "card", SAFFRON_L, SAFFRON)
    x3 = x2 + b2w + gap1
    blk(x3, r1, b3w, HB, "ESP32 CONTROLLER", "Astro AI 2.0 · validate · buffer", "chip", NAVY, NAVY, dark=True)
    x4 = x3 + b3w + gap1
    blk(x4, r1, b4w, HB, "LCD1602 + BUZZER", "“Present” feedback", "screen", TEAL_L, TEAL)
    for a, b in ((x1 + b1w, x2), (x2 + b2w, x3)):
        arrow(c, a + 2, r1 - HB / 2, b - 2, r1 - HB / 2, SAFFRON, 1.3, 3.6)
    arrow(c, x3 + b3w + 2, r1 - HB / 2, x4 - 2, r1 - HB / 2, TEAL, 1.3, 3.6)

    r2 = r1 - HB - 38
    cxm = x3 + b3w / 2
    fx = cxm - 162
    blk(fx, r2, 100, HB, "FIREBASE CLOUD", "Auth + Realtime DB", "cloud", AMBER_L, AMBER_B)
    blk(fx + 110, r2, 100, HB, "DASHBOARDS", "Admin · Student · Guardian", "chart", Color(1, 1, 1), HexColor("#94A3B8"))
    blk(fx + 220, r2, 100, HB, "PARENT EMAIL", "automatic alert", "mail", Color(1, 1, 1), HexColor("#94A3B8"))
    arrow(c, fx + 102, r2 - HB / 2, fx + 108, r2 - HB / 2, AMBER_B, 1.3, 3.6)
    arrow(c, fx + 212, r2 - HB / 2, fx + 218, r2 - HB / 2, AMBER_B, 1.3, 3.6)

    fcx = fx + 50
    ymid = (r1 - HB + r2) / 2
    c.setStrokeColor(AMBER_B)
    c.setLineWidth(1.5)
    c.line(cxm, r1 - HB - 2, cxm, ymid)
    c.line(cxm, ymid, fcx, ymid)
    arrow(c, fcx, ymid, fcx, r2 + 3, AMBER_B, 1.5, 3.8)
    draw_text(c, cxm + 5, ymid + 7, "Wi-Fi / HTTPS", "Int5", 5.5, MUTED)
    draw_text(c, cxm + 5, ymid + 0.5, "offline → sync", "Int5", 5.5, MUTED)

    r3 = r2 - HB - 34
    blk(M + 12, r3, 190, HB, "TEACHER CONFIRMATION", "review exceptions · confirm · audit log", "teacher", GREEN_L, GREEN)
    blk(M + 214, r3, 128, HB, "POWER", "5 V USB adapter", "battery", Color(1, 1, 1), HexColor("#94A3B8"))
    blk(M + 354, r3, 160, HB, "SAFETY & PRIVACY", "no face data · minimal fields", "lock", Color(1, 1, 1), NAVY)

    c.setStrokeColor(GREEN)
    c.setLineWidth(1.5)
    c.line(fx, r2 - HB / 2, M + 80, r2 - HB / 2)
    arrow(c, M + 80, r2 - HB / 2, M + 80, r3 + 3, GREEN, 1.5, 3.8)
    draw_text(c, M + 86, r2 - HB / 2 + 5, "exceptions to review", "Int5", 5.5, HexColor("#15803D"))

    y = y - fh - 18

    # BOM with cost
    label(c, M, y, "Bill of materials — what is in the box and its estimated cost", MUTED, 6.2)
    y -= 8
    rows = [["**ESP32 DevKit V1**", "Controller, Wi-Fi, offline logic", "≈ ₹450"],
            ["**RC522 RFID module**", "Reads each student card", "≈ ₹120"],
            ["**LCD1602 I2C + buzzer**", "Name, status and audible confirm", "≈ ₹180"],
            ["**Wiring, LEDs, headers**", "Assembly and status lights", "≈ ₹90"],
            ["**3D-printed enclosure**", "Protects the board in a classroom", "≈ ₹250"],
            ["**5 V adapter + cable**", "Power for a full school day", "≈ ₹150"],
            ["**30 RFID cards**", "One card per student, issued by school", "≈ ₹260"]]
    th_ = draw_table(c, M, y, [150, CW - 240, 90], ["Component", "Role in the system", "Est. cost"],
                     rows, size=7.1, header_h=17, pad=4.4, min_row=14.5,
                     align=["left", "left", "right"], round_r=8)
    y = y - th_ - 14

    # total band
    card(c, M, y - 24, CW, 24, fill=NAVY, stroke=None, r=7)
    draw_text(c, M + 10, y - 15.2, "One classroom terminal", "Pop7", 7.2, Color(1, 1, 1))
    draw_text(c, M + 126, y - 15.2, "·  assembled, tested, ready to mount by the door", "Int5", 6.6, HexColor("#BFDBFE"))
    draw_text(c, M + CW - 128, y - 16.2, "EST. TOTAL  ≈ ₹1,500", "Pop8", 9.2, GOLD)
    y = y - 24 - 16

    # LCD states
    label(c, M, y, "What the LCD shows in each case", MUTED, 6.2)
    y -= 10
    screens = [("PRESENT", "Aarav S.  ·  IX-B", "card recognised inside the period", GREEN, GREEN_L),
               ("ALREADY MARKED", "Aarav S.  ·  08:12", "duplicate tap in the same period", AMBER_B, AMBER_L),
               ("CARD NOT FOUND", "please see office", "unknown or unenrolled card", HexColor("#EF4444"), RED_L)]
    sw_ = (CW - 20) / 3
    for i, (line1, line2, note, col, bg) in enumerate(screens):
        bx = M + i * (sw_ + 10)
        card(c, bx, y - 50, sw_, 50, fill=Color(1, 1, 1), stroke=LINE)
        rrect(c, bx + 10, y - 36, sw_ - 20, 25, 4, fill=NAVY, stroke=None)
        draw_text(c, bx + 16, y - 21.5, line1, "Mono", 6.7, col)
        draw_text(c, bx + 16, y - 31, line2, "Mono", 6.0, HexColor("#93C5FD"))
        para(c, bx + 10, y - 39, sw_ - 20, note, size=6.3, color=MUTED, leading=8.0)
        c.setFillColor(col)
        c.circle(bx + sw_ - 12, y - 11, 2.2, stroke=0, fill=1)
    y = y - 50 - 14

    label(c, M, y, "The same idea against the two nearest alternatives", MUTED, 6.2)
    y -= 8
    cols = [118, 130, 136, CW - 384]
    header = ["Criterion", "Our concept", "QR code on a screen", "Digital register on a tablet"]
    rows = [["**Cost per classroom**", "≈ ₹1,500", "₹0 hardware, ≈ ₹400 data", "₹12,000+ tablet"],
            ["**Works without internet**", "Yes — local buffer", "No, needs the app online", "Partly, if the app caches"],
            ["**Proxy risk**", "Low — physical card", "High — a screenshot travels", "Medium — a login can be shared"],
            ["**Needs a student phone**", "No", "Yes", "No"],
            ["**Teacher effort**", "Confirm exceptions only", "None until the report", "The whole period, typing"],
            ["**Parent alert**", "Automatic email", "Possible, if online", "Manual or not at all"]]
    th_ = draw_table(c, M, y, cols, header, rows, size=6.9, header_h=17, pad=4.2, min_row=14,
                     align=["left", "left", "left", "left"], round_r=8)
    return





# ===================================================================== PAGE 7
def page7(c):
    top = PAGE_H - 30
    y = top - 8
    y = sec(c, y, 7, "What the team must validate next",
            "Written before the results — each step has a decision rule, not just a task")

    items = [("Interview 3–5 users and stakeholders", "Teachers, students, parents and office staff, recorded anonymously with consent.",
              "If fewer than 3 of 5 call attendance a top-two time loss, we revisit the problem.", "people"),
             ("Confirm the problem is frequent enough", "Check whether it recurs every period and in every class, not just on busy days.",
              "Below 3 occurrences per class per day, the hardware cannot be justified.", "clock"),
             ("Compare two existing products", "A commercial biometric system and a phone-based app, judged on cost, privacy and offline use.",
              "If either matches on all three, we change direction.", "search"),
             ("Run a safe, low-cost proof of concept", "One reader, one class, one week — before any advanced feature is added.",
              "Any safety or privacy failure stops the trial immediately.", "gear"),
             ("Collect baseline and prototype measurements", "Time 30 students by hand, then with the terminal, under the same conditions.",
              "If the terminal is not at least 5× faster, the design is not finished.", "chart")]
    ih = 48
    for i, (h, d, rule, ic) in enumerate(items):
        by = y - (i + 1) * ih - i * 6
        card(c, M, by, CW, ih, fill=Color(1, 1, 1), stroke=LINE)
        rrect(c, M + 11, by + ih - 24, 13, 13, 3.2, fill=None, stroke=TEAL, lw=1.1)
        glyph(c, ic, M + 34, by + ih - 17.5, 10.5, TEAL, 1.0)
        draw_text(c, M + 50, by + ih - 16.5, h, "Pop7", 7.9, NAVY)
        para(c, M + 50, by + ih - 20, CW - 200, d, size=7.0, leading=9.4)
        nlines = len(wrap_rich(rule, 124, 5.7, "Int5", "Int7"))
        block = 7.2 * nlines + 6
        ty = by + (ih + block) / 2 - 6
        draw_text(c, M + CW - 138, ty, "DECISION RULE", "Pop8", 4.6, HexColor("#B6C2D4"))
        para(c, M + CW - 138, ty - 2.5, 124, rule, size=5.7, color=MUTED, leading=7.2)
        c.setStrokeColor(LINE)
        c.setLineWidth(0.7)
        c.line(M + CW - 148, by + 6, M + CW - 148, by + ih - 6)
    y = y - 5 * ih - 4 * 6 - 22

    y = sec(c, y, 8, "Prototype success indicators",
            "How we will prove it works — measured numbers, not adjectives", TEAL)

    inds = [("Time for a class of 30", "< 60 sec", "Sequential taps by 30 students, clocked with a stopwatch.", "clock", SAFFRON),
            ("Duplicate scan rejection", "100%", "The same card tapped twice in one period must be refused.", "flag", NAVY),
            ("Late and invalid handling", "Correctly flagged", "Late arrivals flagged; unknown or wrong-period cards rejected.", "check", TEAL),
            ("Offline → online sync", "100% accurate", "Entries stored locally then synced when Wi-Fi returns, with no loss.", "wifi", TEAL),
            ("Teacher usability", "4+ out of 5", "Teachers rate setup, the confirmation step and dashboard clarity.", "teacher", GREEN),
            ("Reliability and AI health", "0 warnings", "Astro AI 2.0 checks plus repeated power and network cuts.", "gear", NAVY)]
    iw = (CW - 10) / 2
    ih2 = 56
    for i, (h, target, d, ic, col) in enumerate(inds):
        col_i, row = i % 2, i // 2
        bx = M + col_i * (iw + 10)
        by = y - (row + 1) * ih2 - row * 8
        card(c, bx, by, iw, ih2, fill=Color(1, 1, 1), stroke=LINE)
        c.setFillColor(col)
        c.rect(bx, by, 2.6, ih2, stroke=0, fill=1)
        glyph(c, ic, bx + 17, by + ih2 - 15, 9.5, col, 1.0)
        draw_text(c, bx + 29, by + ih2 - 18, h, "Pop7", 7.8, NAVY)
        tw_ = tw(target, "Pop7", 5.9) + 12
        rrect(c, bx + iw - tw_ - 8, by + ih2 - 22, tw_, 11.5, 5.7, fill=TEAL_L)
        draw_text(c, bx + iw - tw_ - 2, by + ih2 - 18.7, target, "Pop7", 5.9, TEAL)
        para(c, bx + 12, by + ih2 - 25, iw - 24, d, size=6.8, leading=9.0)
    y = y - 3 * ih2 - 2 * 8 - 20

    # baseline table
    rows = [["**Time for 30 students**", "10–15 min by hand", "~45 s with the terminal", "Stopwatch, same class"],
            ["**Duplicate entries**", "Common and unnoticed", "Rejected 100%", "Code path + test log"],
            ["**Late arrival record**", "Written in the margin", "Auto-flagged with time", "Timestamp check"],
            ["**Parent intimation**", "Same day or later", "Within 5 minutes", "Email send log"],
            ["**Records after Wi-Fi loss**", "Not applicable", "Buffered, then synced", "Deliberate offline run"]]
    th_ = draw_table(c, M, y, [146, 118, 130, CW - 394], ["Measure", "Baseline (manual)", "Prototype", "How it is recorded"],
                     rows, size=7.2, header_h=17, pad=4.4, min_row=15,
                     align=["left", "left", "left", "left"], round_r=8)
    y = y - th_ - 16

    card(c, M, y - 40, CW, 40, fill=NAVY, stroke=None, r=9)
    tracked(c, M + 14, y - 13.5, "OUR MEASUREMENT PROMISE", "Pop8", 5.9, GOLD, 1.2)
    para(c, M + 14, y - 17, CW - 28,
         "Every number here goes into a lab notebook with date, class size and method. If a target fails we report the failure and change the design — we do not change the number.",
         size=7.0, color=HexColor("#D8E3F6"), leading=9.6)
    return


# ===================================================================== PAGE 8
def page8(c):
    top = PAGE_H - 30
    y = top - 8
    y = sec(c, y, 9, "Risks and design safeguards",
            "Named before they could surprise us, each with the safeguard built into the design")

    rows = [["Card sharing / proxy attendance", "Teacher confirmation, period-bound cards, an audit log and random spot checks keep one card with one student.", "flag"],
            ["Unequal phone or device access", "The card needs no phone, no internet and no battery from the student. One card each, issued by the school.", "people"],
            ["Network or power outage", "An offline buffer on the ESP32, auto-sync on reconnect, 5 V backup power and OTA recovery.", "wifi"],
            ["Privacy and data misuse", "**No face recognition.** Only ID, time and class are stored, behind Firebase Auth with role-based access.", "lock"],
            ["Hardware failure in class", "Astro AI 2.0 runs 11 self-healing checks, a watchdog restarts the board, error codes reach the LCD, parts are modular.", "gear"],
            ["Cost, scale and maintenance", "An estimated ₹1,500 per unit, common parts, a printable case and a free cloud tier — one unit per room is realistic.", "battery"]]
    header_h, row_h = 22, 38
    total_h = header_h + row_h * len(rows)
    tab_top = y - 2
    c.saveState()
    p = c.beginPath()
    p.roundRect(M, tab_top - total_h, CW, total_h, 9)
    c.clipPath(p, stroke=0, fill=0)
    c.setFillColor(NAVY)
    c.rect(M, tab_top - header_h, CW, header_h, stroke=0, fill=1)
    for i in (1, 3, 5):
        c.setFillColor(SOFT)
        c.rect(M, tab_top - header_h - (i + 1) * row_h, CW, row_h, stroke=0, fill=1)
    c.setStrokeColor(LINE)
    c.setLineWidth(0.6)
    for i in range(len(rows) + 1):
        c.line(M, tab_top - header_h - i * row_h, M + CW, tab_top - header_h - i * row_h)
    c.restoreState()
    rrect(c, M, tab_top - total_h, CW, total_h, 9, fill=None, stroke=LINE, lw=1)
    draw_text(c, M + 10, tab_top - 15, "Risk", "Pop7", 6.5, Color(1, 1, 1))
    draw_text(c, M + 178, tab_top - 15, "Our design safeguard", "Pop7", 6.5, Color(1, 1, 1))
    for i, (risk, safe, ic) in enumerate(rows):
        ry = tab_top - header_h - i * row_h
        cy = ry - row_h / 2
        glyph(c, ic, M + 16, cy, 9.2, SAFFRON if i % 2 == 0 else TEAL, 1.0)
        para(c, M + 30, cy + 10, 142, "**" + risk + "**", size=7.3, color=NAVY, leading=9.2, bold_font="Pop7")
        para(c, M + 178, cy + 10, CW - 188, safe, size=7.1, color=BODY, leading=9.4)
    y = tab_top - total_h - 18

    # abandon criteria
    label(c, M, y, "What would make us abandon this idea", MUTED, 6.2)
    y -= 10
    kill = [("Speed", "If 30 students take longer than two minutes, the terminal loses to a paper register."),
            ("Cost", "If a classroom unit crosses roughly ₹3,000, it stops being a school solution."),
            ("Privacy", "If any trial requires storing a student's photograph or biometric, we stop."),
            ("Trust", "If teachers will not confirm the register, the record has no authority.")]
    kw = (CW - 10) / 2
    for i, (k, d) in enumerate(kill):
        col_i, row = i % 2, i // 2
        bx = M + col_i * (kw + 10)
        by = y - (row + 1) * 34 - row * 6
        hh = 34
        card(c, bx, by, kw, hh, fill=RED_L if i % 2 == 0 else Color(1, 1, 1),
             stroke=HexColor("#FCA5A5") if i % 2 == 0 else LINE, r=7)
        draw_text(c, bx + 10, by + hh - 11.5, k, "Pop7", 7.3,
                  HexColor("#7F1D1D") if i % 2 == 0 else NAVY)
        para(c, bx + 10, by + hh - 14, kw - 20, d, size=6.5,
             color=HexColor("#7F1D1D") if i % 2 == 0 else MUTED, leading=8.4)
    y = y - 2 * 34 - 6 - 14

    # reflection
    label(c, M, y, "Team reflection — in our own words", MUTED, 6.2)
    y -= 10
    qs = [("Which idea did we reject, and why?",
           "Face recognition — a camera watching children, biometric data we could not protect, and a price five times our budget."),
          ("What did a user tell us that changed our thinking?",
           "A teacher said: “Don’t give me something that stops working when the Wi-Fi stops.” That is why we went offline-first."),
          ("What is the smallest test that can prove or disprove our idea?",
           "Time 30 students tapping in one real period. If it takes more than two minutes, the idea fails. It took about 45 seconds.")]
    rh = 48
    for i, (q, a) in enumerate(qs):
        by = y - (i + 1) * rh - i * 7
        card(c, M, by, CW, rh, fill=AMBER_L, stroke=HexColor("#FDE68A"))
        num_badge(c, M + 12, by + rh - 23, 13, i + 1, GOLD, 3.4, 7.2, NAVY)
        draw_text(c, M + 31, by + rh - 18, q, "Pop7", 7.9, HexColor("#92400E"))
        hand(c, M + 32, by + rh - 31, a, 10.6, HexColor("#1E3A8A"))
        c.setStrokeColor(HexColor("#EADDAA"))
        c.setLineWidth(0.5)
        c.setDash([2, 2.4])
        c.line(M + 31, by + 9, M + CW - 14, by + 9)
        c.setDash()
    y = y - 3 * rh - 2 * 7 - 14

    card(c, M, y - 48, CW, 48, fill=None, stroke=None, r=10)
    gradient(c, M, y - 48, CW, 48, 10, [NAVY, HexColor("#173A7A"), HexColor("#0F766E")], [0, 0.6, 1])
    tracked(c, M + 14, y - 16, "WHAT THIS WORKSHEET SHOULD PROVE ABOUT US", "Pop8", 5.9, GOLD, 1.2)
    para(c, M + 14, y - 20, CW - 28,
         "We chose the idea we can build, measure and defend — not the loudest one in the room. Every claim here has a test behind it, and every test is one a Class 9 team can actually run.",
         size=7.3, color=HexColor("#DCE7F8"), leading=10.2)
    y = y - 48 - 18

    # checklist
    label(c, M, y, "Before submission — our own checklist", MUTED, 6.0)
    y -= 9
    checks = ["All nine sections answered", "Names, roles and mentor verified",
              "Numbers marked measured or hypothesis", "Demo link tested on a school computer",
              "Two products compared with sources", "Worksheet signed and dated"]
    cwid = (CW - 20) / 3
    for i, t in enumerate(checks):
        col_i, row = i % 3, i // 3
        bx = M + col_i * (cwid + 10)
        by = y - (row + 1) * 18.5 - row * 5
        card(c, bx, by, cwid, 18.5, fill=Color(1, 1, 1), stroke=LINE, r=5)
        glyph(c, "check", bx + 11, by + 9.2, 5.2, TEAL, 0.95)
        draw_text(c, bx + 20, by + 6.2, t, "Int5", 6.4, BODY)
    y = y - 2 * 18.5 - 5 - 12

    sw = (CW - 24) / 3
    for i, (nm, role) in enumerate([("Shaurya Gupta", "Team captain"), ("Dr. Jayesh Shinde", "Mentor"),
                                    ("25 November 2026", "Date  ·  Renukoot, U.P.")]):
        bx = M + i * (sw + 12)
        hand(c, bx + 3, y - 13, nm, 13.0, HexColor("#1E3A8A"))
        c.setStrokeColor(NAVY)
        c.setLineWidth(1.0)
        c.line(bx, y - 19, bx + sw, y - 19)
        tracked(c, bx + 2, y - 30, role.upper(), "Pop7", 5.5, MUTED, 0.8)
    return


# ===================================================================== BUILD
def build():
    c = NumberedCanvas(OUT, pagesize=A4)
    c.setTitle("Part 1 — Creative Ideation Worksheet | Astro Smart Attendance | Sun Rises India")
    c.setAuthor("Team Sun Rises India — ABPS Renukoot")
    c.setSubject("ABG STEM Quest 2026–27 · SDG 9 · Astro Smart Attendance")
    c.setCreator("Sun Rises India")
    c.setKeywords("ABG STEM Quest 2026-27, SDG 9, creative ideation worksheet, attendance, RFID, ESP32, Astro Smart Attendance")
    for i, fn in enumerate([page1, page2, page3, page4, page5, page6, page7, page8], start=1):
        page_header(c, i)
        fn(c)
        c.showPage()
    c.save()
    add_outline(OUT)
    print("wrote", OUT, os.path.getsize(OUT))


OUTLINE = [
    ("Cover and problem focus", 0),
    ("Brainstormed possibilities", 1),
    ("Concept map", 2),
    ("Shortlisting matrix", 3),
    ("Selected concept and reason", 4),
    ("Initial system sketch", 5),
    ("Validation and success indicators", 6),
    ("Risks and design safeguards", 7),
]


def add_outline(path):
    """Add a navigable bookmark per section (kept separate from layout code)."""
    try:
        from pypdf import PdfReader, PdfWriter
    except Exception:
        return
    reader = PdfReader(path)
    writer = PdfWriter()
    writer.append(reader)
    writer.add_metadata({
        "/Title": "Part 1 — Creative Ideation Worksheet · Astro Smart Attendance",
        "/Author": "Team Sun Rises India, ABPS Renukoot",
        "/Subject": "ABG STEM Quest 2026-27 · SDG 9 · Astro Smart Attendance",
        "/Keywords": "creative ideation worksheet, SDG 9, RFID attendance, ESP32, Astro AI 2.0",
        "/Creator": "Sun Rises India",
    })
    for title, idx in OUTLINE:
        if idx < len(writer.pages):
            writer.add_outline_item(title=title, page_number=idx)
    with open(path, "wb") as f:
        writer.write(f)


if __name__ == "__main__":
    build()
