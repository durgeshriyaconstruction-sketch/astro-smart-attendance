#!/usr/bin/env python3
import os
import sys
import math
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from ws_common import *  # noqa
import ws_common as W

INK_BLUE = HexColor("#1D4ED8")
PLUM = HexColor("#7C3AED")


def hand(c, x, y, text, size=10.4, color=INK_BLUE):
    return draw_text(c, x, y, text, "Caveat", size, color)


# ===================================================================== helpers
def card(c, x, y, w, h, fill=SOFT, stroke=LINE, r=8, lw=1):
    rrect(c, x, y, w, h, r, fill=fill, stroke=stroke, lw=lw)


def pill(c, x, y, text, fill, color, size=6.2, h=11, pad=5):
    w = tw(text, "Pop8", size) + 2 * pad
    rrect(c, x, y, w, h, h / 2, fill=fill)
    draw_text(c, x + pad, y + (h - size) / 2 + 0.6, text, "Pop8", size, color)
    return w


def draw_table(c, x, top, col_w, header, rows, size=7.9, header_h=22,
               pad=5.5, align=None, min_row=None, row_fills=None,
               header_fill=NAVY, header_color=Color(1, 1, 1), leading_k=1.42,
               stroke_color=LINE, round_r=8):
    """rows: list of list of str (supports **bold**). align per column list."""
    total_w = sum(col_w)
    leading = size * leading_k
    align = align or ["left"] + ["center"] * (len(col_w) - 1)
    heights = []
    for row in rows:
        mx = 1
        for i, cell in enumerate(row):
            mx = max(mx, len(wrap_rich(str(cell), col_w[i] - 2 * pad, size, "Int5", "Int7")))
        h = mx * leading + 2 * pad + 1.5
        heights.append(max(h, min_row or 0))
    body_h = sum(heights)
    total_h = body_h + header_h
    # clip for rounded corners
    c.saveState()
    p = c.beginPath()
    p.roundRect(x, top - total_h, total_w, total_h, round_r)
    c.clipPath(p, stroke=0, fill=0)
    c.setFillColor(header_fill)
    c.rect(x, top - header_h, total_w, header_h, stroke=0, fill=1)
    yy = top - header_h
    for i, row in enumerate(rows):
        hh = heights[i]
        fill = Color(1, 1, 1)
        if row_fills and i < len(row_fills) and row_fills[i] is not None:
            fill = row_fills[i]
        elif i % 2 == 1:
            fill = SOFT
        c.setFillColor(fill)
        c.rect(x, yy - hh, total_w, hh, stroke=0, fill=1)
        yy -= hh
    c.setStrokeColor(stroke_color)
    c.setLineWidth(0.6)
    yy = top - header_h
    for hh in heights:
        c.line(x, yy, x + total_w, yy)
        yy -= hh
    c.restoreState()
    # header text
    xx = x
    for i, htxt in enumerate(header):
        wsum = tw(htxt, "Pop7", size - 0.5)
        tx = xx + pad if align[i] == "left" else xx + (col_w[i] - wsum) / 2
        draw_text(c, tx, top - header_h / 2 - (size - 0.5) / 2 + 1, htxt, "Pop7", size - 0.5, header_color)
        xx += col_w[i]
    # body text
    yy = top - header_h
    for i, row in enumerate(rows):
        hh = heights[i]
        xx = x
        for j, cell in enumerate(row):
            lines = wrap_rich(str(cell), col_w[j] - 2 * pad, size, "Int5", "Int7")
            block = len(lines) * leading
            ty = yy - (hh - block) / 2 - size * 0.86
            for ln in lines:
                wsum = sum(tw(t, "Int7" if b else "Int5", size) for t, b in ln)
                tx = xx + pad if align[j] == "left" else xx + (col_w[j] - wsum) / 2
                for t, b in ln:
                    tx = draw_text(c, tx, ty, t, "Int7" if b else "Int5", size, BODY if not b else NAVY)
                ty -= leading
            xx += col_w[j]
        yy -= hh
    # outer stroke
    rrect(c, x, top - total_h, total_w, total_h, round_r, fill=None, stroke=LINE, lw=1)
    return total_h


def section_title(c, y, num, title, sub, accent=SAFFRON, color2=None):
    return section(c, y, num, title, sub, accent)


# ===================================================================== PAGE 1
def page1(c):
    top = PAGE_H - 30
    # ---------------- hero
    hh = 214
    hx, hy = M, top - 6 - hh
    gradient(c, hx, hy, CW, hh, 12, [NAVY, HexColor("#15306B"), NAVY3], [0, 0.55, 1])
    # soft decorative arcs
    c.saveState()
    p = c.beginPath()
    p.roundRect(hx, hy, CW, hh, 12)
    c.clipPath(p, stroke=0, fill=0)
    c.setStrokeColor(Color(1, 1, 1, 0.07))
    c.setLineWidth(18)
    c.circle(hx + CW - 18, hy + 10, 120, stroke=1, fill=0)
    c.circle(hx + CW - 18, hy + 10, 78, stroke=1, fill=0)
    c.setStrokeColor(Color(1, 1, 1, 0.05))
    c.setLineWidth(1)
    for gy in range(int(hy), int(hy + hh), 16):
        c.line(hx, gy, hx + CW, gy)
    c.restoreState()

    tx = hx + 16
    # kicker
    kick = "SUN RISES INDIA   ·   GRADE 9   ·   ABPS RENUKOOT"
    kw = tracked_width(kick, "Pop7", 6.3, 0.9) + 22
    rrect(c, tx, top - 30, kw, 15, 7.5, fill=Color(1, 1, 1, 0.14), stroke=Color(1, 1, 1, 0.3), lw=0.7)
    c.setFillColor(GOLD)
    c.circle(tx + 8, top - 22.5, 2.1, stroke=0, fill=1)
    tracked(c, tx + 14, top - 25.2, kick, "Pop7", 6.3, Color(1, 1, 1), 0.9)

    draw_text(c, tx, top - 62, "ASTRO", "Pop9", 30, Color(1, 1, 1))
    x2 = tx + tw("ASTRO ", "Pop9", 30)
    draw_text(c, x2, top - 62, "SMART", "Pop9", 30, GOLD)
    draw_text(c, tx, top - 91, "ATTENDANCE", "Pop9", 26.5, Color(1, 1, 1))
    c.setStrokeColor(SAFFRON)
    c.setLineWidth(2.4)
    c.line(tx, top - 98, tx + 118, top - 98)

    draw_text(c, tx, top - 113, "AI  +  IoT  +  Cloud   smart school attendance system", "Pop6", 8.6, HexColor("#7DD3FC"))

    para(c, tx, top - 124, 306,
         "A compact **ESP32-based RFID attendance terminal** with **Astro AI 2.0 self-healing diagnostics**, a **Firebase cloud dashboard** and **automatic parent email alerts** — built for **₹1,500 per classroom**, working **offline-first** and syncing when the internet returns.",
         size=8.2, color=HexColor("#D8E3F6"), bold_font="Int7", leading=12.4)

    hand(c, tx, hy + 12, "“One tap. Attendance done. Parents informed.”", 13.5, HexColor("#FFD9A8"))

    # team glass card
    gx, gw = hx + CW - 190, 174
    gyy, gh = top - 18 - 176, 176
    rrect(c, gx, gyy, gw, gh, 10, fill=Color(1, 1, 1, 0.10), stroke=Color(1, 1, 1, 0.28), lw=0.8)
    tracked(c, gx + 11, gyy + gh - 17, "TEAM  ·  SUN RISES INDIA", "Pop8", 6.3, GOLD, 0.9)
    rows = [("Team captain", "Shaurya Gupta"),
            ("Members", "Shaurya Gupta, Anant Tiwari,\nDevansh Dhakad, Tejas Upadhyay,\nDiwakar Singh"),
            ("Mentor", "Dr. Jayesh Shinde"),
            ("School", "ABPS Renukoot,\nSonbhadra (U.P.)"),
            ("Theme", "SDG 9 — Industry,\nInnovation & Infrastructure")]
    yy = gyy + gh - 30
    for k, v in rows:
        draw_text(c, gx + 11, yy, k, "Int5", 6.4, Color(1, 1, 1, 0.62))
        for j, vl in enumerate(v.split("\n")):
            draw_text(c, gx + 11, yy - 9 - j * 8.4, vl, "Pop6", 7.0, Color(1, 1, 1))
        yy -= 11.5 + 8.4 * len(v.split("\n"))
        c.setStrokeColor(Color(1, 1, 1, 0.16))
        c.setLineWidth(0.5)
        c.setDash([2, 2])
        c.line(gx + 11, yy + 4, gx + gw - 11, yy + 4)
        c.setDash()

    hand(c, gx + 2, gyy - 12, "live demo · astro-smart-attendence.web.app", 8.8, HexColor("#FFD9A8"))

    # ---------------- snapshot strip
    y = hy - 30
    stats = [("₹1,500", "COST PER UNIT", "battery"),
             ("OFFLINE-FIRST", "AUTO SYNC ON Wi-Fi", "wifi"),
             ("ASTRO AI 2.0", "11 SELF-HEALING CHECKS", "gear"),
             ("FIREBASE", "CLOUD DASHBOARD", "cloud")]
    bw = (CW - 3 * 8) / 4
    for i, (v, lab, ic) in enumerate(stats):
        bx = M + i * (bw + 8)
        card(c, bx, y - 38, bw, 38, fill=Color(1, 1, 1), stroke=LINE)
        c.setFillColor(SAFFRON_L if i % 2 == 0 else TEAL_L)
        c.circle(bx + 18, y - 19, 10.5, stroke=0, fill=1)
        glyph(c, ic, bx + 18, y - 19, 9, NAVY if i % 2 == 0 else TEAL, 1.0)
        draw_text(c, bx + 33, y - 16, v, "Pop8", 8.6 if len(v) > 8 else 11, NAVY)
        tracked(c, bx + 33, y - 28, lab, "Pop7", 4.9, MUTED, 0.6)

    # ---------------- section 1
    y = y - 38 - 22
    y = section_title(c, y, 1, "Problem focus", "What hurts, who feels it, and how we will know it is fixed")

    lw_, rw_ = 300, CW - 300 - 12
    ch = 202
    # left card
    card(c, M, y - ch, lw_, ch, fill=SAFFRON_L, stroke=SAFFRON_B)
    c.setFillColor(SAFFRON)
    c.rect(M, y - ch, 3, ch, stroke=0, fill=1)
    label(c, M + 13, y - 17, "The problem we chose")
    yy = para(c, M + 13, y - 22, lw_ - 26,
              "Indian schools lose **10–15 minutes per class** to manual attendance. Across **15+ lakh schools**, registers are slow, error-prone and open to **proxy attendance** — while records, parent alerts and reports stay disconnected.",
              size=8.2, color=BODY, leading=12.1)
    yy = para(c, M + 13, yy - 8, lw_ - 26,
              "Our answer: an **AI-supported, low-cost RFID terminal** that marks a student in **under 2 seconds**, keeps working without internet, and tells parents automatically.",
              size=8.2, color=BODY, leading=12.1)
    ev_h = 48
    card(c, M + 13, yy - 10 - ev_h, lw_ - 26, ev_h, fill=Color(1, 1, 1, 0.55), stroke=AMBER_B, r=6, lw=0.8)
    c.setDash([2.4, 2])
    label(c, M + 22, yy - 24, "Evidence we observed", AMBER_B, 6.2)
    c.setDash()
    para(c, M + 22, yy - 27, lw_ - 44,
         "Morning assembly queues · duplicate entries in paper registers · late-arrival disputes · no instant parent intimation.",
         size=7.4, color=BODY, leading=10.4)

    # right card
    rx = M + lw_ + 12
    card(c, rx, y - ch, rw_, ch, fill=TEAL_L, stroke=TEAL_B)
    label(c, rx + 12, y - 17, "Discovery questions", TEAL)
    items = ["**Who** feels it? Teachers, students, parents, school office",
             "**When?** Every period, peak at the first bell",
             "**Today?** Paper register and verbal roll-call",
             "**Improved when?** Less time, zero proxy, parents alerted fast"]
    yy = bullets(c, rx + 12, y - 24, rw_ - 24, items, size=7.4, leading=10.2, gap=3.2, mark="sq", mark_color=TEAL)
    card(c, rx + 12, yy - 52, rw_ - 24, 48, fill=Color(1, 1, 1, 0.6), stroke=TEAL, r=6, lw=0.8)
    label(c, rx + 20, yy - 16, "Success looks like", TEAL, 6.2)
    para(c, rx + 20, yy - 20, rw_ - 44, "30 students marked in **under 60 seconds**, zero proxy entries, parents alerted **within 5 minutes**.", size=7.4, leading=10.4)

    # ---------------- voices
    y = y - ch - 18
    label(c, M, y, "What we heard in discovery dialogues  ·  anonymised notes", MUTED, 6.2)
    y -= 8
    quotes = [("“We lose fifteen minutes of teaching every single period just calling out names.”", "Class teacher  ·  ABPS Renukoot"),
              ("“We only find out our child was absent when the day is already over.”", "Parent  ·  Renukoot")]
    qw = (CW - 10) / 2
    for i, (q, who) in enumerate(quotes):
        qx = M + i * (qw + 10)
        card(c, qx, y - 46, qw, 46, fill=CREAM, stroke=HexColor("#FDE68A"))
        draw_text(c, qx + 10, y - 18, "“", "Pop9", 20, GOLD)
        para(c, qx + 20, y - 8, qw - 30, q, size=7.4, color=NAVY, leading=10.2)
        tracked(c, qx + 20, y - 38, who.upper(), "Pop7", 5.2, MUTED, 0.7)
    y -= 46 + 16

    # ---------------- numbers band
    label(c, M, y, "The problem in numbers", MUTED, 6.2)
    y -= 8
    nums = [("10–15", "minutes lost every period", SAFFRON),
            ("15+ lakh", "schools facing it daily", TEAL),
            ("₹30,000+", "commercial system vs ₹1,500 ours", NAVY)]
    nw = (CW - 20) / 3
    for i, (v, lab, col) in enumerate(nums):
        nx = M + i * (nw + 10)
        card(c, nx, y - 40, nw, 40, fill=Color(1, 1, 1), stroke=LINE)
        draw_text(c, nx + 12, y - 20, v, "Pop9", 15, col)
        para(c, nx + 12, y - 22, nw - 24, lab, size=6.8, color=MUTED, leading=8.4)
    y = y - 40 - 20

    card(c, M, y - 34, CW, 34, fill=NAVY, stroke=None, r=9)
    glyph(c, "star", M + 18, y - 17, 8, GOLD, 1.0)
    para(c, M + 32, y - 7, CW - 50,
         "**In one line:** a ₹1,500 RFID terminal that marks a class in under a minute, works without internet, and tells parents the same minute — designed, built and measured by five Class 9 students.",
         size=7.4, color=Color(1, 1, 1), leading=10.2)
    return


# ===================================================================== PAGE 2
def page2(c):
    top = PAGE_H - 30
    y = top - 8
    y = section_title(c, y, 2, "Brainstormed possibilities",
                      "Ten ideas on the table — every idea got a fair hearing before we scored it")
    # intro note
    card(c, M, y - 40, CW, 40, fill=SOFT, stroke=LINE)
    c.setFillColor(SAFFRON)
    c.rect(M, y - 40, 3, 40, stroke=0, fill=1)
    para(c, M + 14, y - 7, CW - 90, "We brainstormed **without judging**, then filtered. Quantity first, quality second — the wild ideas below shaped the final design more than we expected.",
         size=7.9, leading=11.2)
    hand(c, M + CW - 132, y - 30, "2 hours, one whiteboard", 10)

    y = y - 40 - 14

    ideas = [
        ("QR code attendance (rotating)", "Teacher displays a rotating code; students scan inside a short window.", "card", "SHARE RISK", HexColor("#92400E"), HexColor("#FEF3C7")),
        ("RFID card tap-in", "Student taps ID card on RC522 reader — instant, no phone needed.", "chip", "SELECTED", HexColor("#166534"), HexColor("#DCFCE7")),
        ("Teacher-confirmed digital register", "Teacher reviews exceptions and confirms the final register.", "book", "INCLUDED", HexColor("#166534"), HexColor("#DCFCE7")),
        ("NFC check-in with time window", "Phone NFC tap accepted only inside class time.", "phone", "NEEDS PHONES", HexColor("#92400E"), HexColor("#FEF3C7")),
        ("Face recognition", "Camera identification — fast, but high privacy and consent risk.", "person", "REJECTED", HexColor("#991B1B"), HexColor("#FEE2E2")),
        ("Bluetooth proximity check-in", "Beacon detects the student device near the classroom.", "spark", "RANGE ISSUES", HexColor("#92400E"), HexColor("#FEF3C7")),
        ("Offline attendance, sync later", "Store entries on the device; upload when Wi-Fi returns.", "save", "CORE", HexColor("#166534"), HexColor("#DCFCE7")),
        ("Duplicate & late-arrival flags", "Auto-flag repeat taps, late entry and wrong-period scans.", "flag", "INCLUDED", HexColor("#166534"), HexColor("#DCFCE7")),
        ("Parent / student attendance summary", "Daily and period-wise summary with instant email alerts.", "mail", "INCLUDED", HexColor("#166534"), HexColor("#DCFCE7")),
        ("Audit log for corrections", "Every edit recorded with who, when and why.", "lock", "INCLUDED", HexColor("#166534"), HexColor("#DCFCE7")),
    ]
    tw_ = (CW - 10) / 2
    th = 55
    for i, (title, desc, ic, tag, tagc, tagbg) in enumerate(ideas):
        col, row = i % 2, i // 2
        bx = M + col * (tw_ + 10)
        by = y - (row + 1) * th - row * 8
        card(c, bx, by, tw_, th, fill=Color(1, 1, 1), stroke=LINE)
        rrect(c, bx + 9, by + th - 34, 26, 26, 7, fill=SAFFRON_L if i % 2 == 0 else TEAL_L)
        glyph(c, ic, bx + 22, by + th - 21, 13, SAFFRON if i % 2 == 0 else TEAL, 1.15)
        draw_text(c, bx + 42, by + th - 17, title, "Pop7", 7.7, NAVY)
        para(c, bx + 42, by + th - 20, tw_ - 54, desc, size=7.0, leading=9.4)
        pw = pill(c, bx + 42, by + 6, tag, tagbg, tagc, 5.4, 10, 4.5)
        draw_text(c, bx + 42 + pw + 4, by + 7.4, "%02d" % (i + 1), "Mono", 6.0, HexColor("#CBD5E1"))

    y = y - 5 * th - 4 * 8 - 16

    # parked ideas band
    card(c, M, y - 54, CW, 54, fill=NAVY, stroke=None, r=10)
    tracked(c, M + 14, y - 17, "IDEAS WE PARKED, NOT DELETED", "Pop8", 6.4, GOLD, 1.1)
    para(c, M + 14, y - 21, CW - 150, "QR rotation and NFC time-windows may join Phase 2 as backup modes for students without a card. Bluetooth was parked because of battery and range limits.",
         size=7.4, color=HexColor("#D8E3F6"), leading=10.4)
    hand(c, M + CW - 128, y - 30, "good backup, weak core", 10, HexColor("#FFD9A8"))
    y = y - 54 - 24

    # ---- how we ideated
    label(c, M, y, "How we ideated — three rounds, one whiteboard", MUTED, 6.4)
    y -= 10
    rounds = [("ROUND 1", "Silent sticky notes", "Each member wrote ideas alone for 15 minutes — no criticism, no ownership.", SAFFRON),
              ("ROUND 2", "Crazy eights", "Eight quick sketches per idea: what if it were free? offline? invisible to students?", TEAL),
              ("ROUND 3", "Kill the favourite", "Each member attacked the team's favourite idea. Survivors earned their place.", NAVY)]
    rw_ = (CW - 20) / 3
    for i, (tag, h, d, col) in enumerate(rounds):
        bx = M + i * (rw_ + 10)
        card(c, bx, y - 62, rw_, 62, fill=Color(1, 1, 1), stroke=LINE)
        c.setFillColor(col)
        c.roundRect(bx + 10, y - 19, tw(tag, "Pop8", 5.6) + 12, 11, 5.5, stroke=0, fill=1)
        draw_text(c, bx + 16, y - 16, tag, "Pop8", 5.6, Color(1, 1, 1))
        draw_text(c, bx + 10, y - 30, h, "Pop7", 7.9, NAVY)
        para(c, bx + 10, y - 34, rw_ - 20, d, size=6.9, leading=9.2)
    y = y - 62 - 22

    # ---- filters
    label(c, M, y, "The three filters we judged every idea against", MUTED, 6.4)
    y -= 10
    filters = [("Can five students build it?", "No lab, no funding, no soldering robot — hands only.", "gear"),
               ("Can a school afford it?", "Under ₹2,000 per classroom, or it stays on paper.", "chart"),
               ("Does it respect students?", "No biometrics, no phone ownership, no surveillance.", "lock")]
    for i, (h, d, ic) in enumerate(filters):
        by = y - (i + 1) * 26 - i * 5
        card(c, M, by, CW, 26, fill=SOFT if i % 2 == 0 else Color(1, 1, 1), stroke=LINE, r=7)
        glyph(c, ic, M + 17, by + 13, 9.5, SAFFRON if i % 2 == 0 else TEAL, 1.0)
        draw_text(c, M + 32, by + 9.5, h, "Pop7", 7.8, NAVY)
        draw_text(c, M + 168, by + 9.5, d, "Int5", 7.2, MUTED)
    y = y - 3 * 26 - 2 * 5 - 20
    card(c, M, y - 34, CW, 34, fill=CREAM, stroke=HexColor("#FDE68A"), r=9)
    draw_text(c, M + 14, y - 21, "One idea survived all three filters:", "Int6", 7.6, HexColor("#92400E"))
    hand(c, M + 168, y - 22, "RFID tap  +  offline buffer  +  teacher confirmation", 12.6, HexColor("#7C2D12"))
    return


# ===================================================================== PAGE 3
def page3(c):
    top = PAGE_H - 30
    y = top - 8
    y = section_title(c, y, 3, "Concept map",
                      "One chain from the user at the door to a number the school can trust", accent=TEAL)

    stages = [("User / setting", "Student at the classroom door, teacher, timetable period", "people", BLUE_L, NAVY),
              ("Problem trigger", "Manual register: slow, proxy-prone, error-prone", "bolt", SAFFRON_L, SAFFRON),
              ("Sensor / input", "RC522 RFID card read in under 2 seconds", "card", TEAL_L, TEAL),
              ("Process / decision", "ESP32 + Astro AI 2.0 validate, de-duplicate, buffer", "chip", BLUE_L, NAVY),
              ("Output / action", "Firebase sync, dashboards, automatic parent email", "cloud", TEAL_L, TEAL),
              ("Measurable benefit", "15 min saved per class, zero proxy, 95% cheaper", "chart", GREEN_L, GREEN)]
    n = len(stages)
    gap = 9
    bw = (CW - gap * (n - 1)) / n
    bh = 106
    for i, (h, d, ic, bg, col) in enumerate(stages):
        bx = M + i * (bw + gap)
        card(c, bx, y - bh, bw, bh, fill=bg, stroke=col, lw=1)
        c.setFillColor(col)
        c.roundRect(bx, y - 15, bw, 15, 8, stroke=0, fill=1)
        c.rect(bx, y - 15, bw, 7, stroke=0, fill=1)
        tracked(c, bx + 8, y - 10, "%02d" % (i + 1), "Pop8", 6.0, Color(1, 1, 1), 0.8)
        glyph(c, ic, bx + bw / 2, y - 40, 15, col, 1.2)
        para(c, bx + 6, y - 50, bw - 12, "**" + h + "**", size=6.9, color=NAVY, leading=8.6, align="center")
        para(c, bx + 6, y - 68, bw - 12, d, size=6.4, color=MUTED, leading=8.4, align="center")
        if i < n - 1:
            arrow(c, bx + bw + 1.5, y - bh / 2, bx + bw + gap - 1.5, y - bh / 2, SAFFRON, 1.3, 3.6)
    y = y - bh - 14

    # proposed direction band
    card(c, M, y - 62, CW, 62, fill=None, stroke=None, r=10)
    gradient(c, M, y - 62, CW, 62, 10, [NAVY, HexColor("#173A7A"), TEAL], [0, 0.6, 1])
    tracked(c, M + 16, y - 19, "PROPOSED DIRECTION", "Pop8", 6.2, GOLD, 1.3)
    draw_text(c, M + 16, y - 35, "Astro Smart Attendance", "Pop9", 15, Color(1, 1, 1))
    draw_text(c, M + 16, y - 50, "Privacy-first  ·  Offline-first  ·  AI self-healing  ·  ₹1,500 per classroom", "Pop6", 7.4, HexColor("#BFDBFE"))
    cw_ = tw("★  OUR CONCEPT", "Pop8", 7.2) + 20
    rrect(c, M + CW - cw_ - 16, y - 40, cw_, 18, 9, fill=SAFFRON)
    draw_text(c, M + CW - cw_ - 16 + 10, y - 34, "★  OUR CONCEPT", "Pop8", 7.2, Color(1, 1, 1))

    # what each link must prove
    y -= 62 + 22
    label(c, M, y, "What each link must prove", MUTED, 6.4)
    y -= 10
    checks = [("User", "We solve a real, repeated classroom moment — not a textbook problem."),
              ("Trigger", "The pain is measured in minutes and errors, not opinions."),
              ("Input", "The tap is faster and fairer than a teacher reading names."),
              ("Process", "The device is correct, private and survives power/Wi-Fi loss."),
              ("Output", "Data reaches teachers and parents without extra work."),
              ("Benefit", "The gain is visible in a real classroom of 30 students.")]
    cw2 = (CW - 2 * 10) / 3
    for i, (h, d) in enumerate(checks):
        col, row = i % 3, i // 3
        bx = M + col * (cw2 + 10)
        by = y - (row + 1) * 50 - row * 8
        card(c, bx, by, cw2, 50, fill=Color(1, 1, 1), stroke=LINE)
        num_badge(c, bx + 10, by + 50 - 24, 14, i + 1, TEAL, 3.5, 7)
        draw_text(c, bx + 30, by + 50 - 19, h, "Pop7", 7.8, NAVY)
        para(c, bx + 10, by + 50 - 28, cw2 - 20, d, size=6.9, leading=9.2)
    y = y - 2 * 50 - 8 - 20

    # design principle strip
    card(c, M, y - 46, CW, 46, fill=CREAM, stroke=HexColor("#FDE68A"))
    label(c, M + 14, y - 15, "Design principle we keep coming back to", HexColor("#B45309"), 6.2)
    draw_text(c, M + 14, y - 32, "“If the internet dies, the register must still work.”", "Caveat", 15.5, HexColor("#7C2D12"))
    hand(c, M + CW - 118, y - 32, "— our own rule, after week 3", 9.5, MUTED)
    y = y - 46 - 24

    # ---- data pathway
    label(c, M, y, "What happens to one tap — data pathway", MUTED, 6.4)
    y -= 10
    path = [("Tap", "RFID UID read"), ("Tag", "student ID + period"),
            ("Check", "duplicate / late?"), ("Store", "local buffer"),
            ("Sync", "Firebase write"), ("Alert", "parent email"), ("Review", "teacher confirms")]
    pw = (CW - 6 * 9) / 7
    for i, (h, d) in enumerate(path):
        bx = M + i * (pw + 9)
        card(c, bx, y - 42, pw, 42, fill=Color(1, 1, 1), stroke=LINE, r=6)
        draw_text(c, bx + 7, y - 14, h, "Pop7", 7.3, NAVY)
        para(c, bx + 7, y - 17, pw - 14, d, size=6.3, color=MUTED, leading=8.0)
        c.setFillColor(TEAL if i % 2 else SAFFRON)
        c.circle(bx + pw - 8, y - 9, 1.8, stroke=0, fill=1)
    y = y - 42 - 22

    # ---- where the benefit shows up
    label(c, M, y, "Where the benefit actually shows up", MUTED, 6.4)
    y -= 8
    rows = [["**Teacher**", "15 minutes returned per class", "≈ 1 extra teaching hour per week"],
            ["**Student**", "No queue, no roll-call, no proxy blame", "Attendance visible to them the same day"],
            ["**Parent**", "Absence message before the day ends", "Same-day action, not next-week surprise"],
            ["**School office**", "One trusted register, exportable", "Reports without re-entering data"]]
    th_ = draw_table(c, M, y, [86, 214, CW - 300], ["Who", "What changes", "What we measure"], rows,
                     size=7.4, header_h=19, pad=5.5, min_row=17, align=["left", "left", "left"], round_r=8)
    y = y - th_ - 22

    label(c, M, y, "Where the chain is still weakest — questions we have not answered yet", MUTED, 6.4)
    y -= 10
    open_q = ["If a card is lost, what stops another student using it before the office reissues it?",
              "Two students tap within the same second — does the buffer keep both, in order?",
              "What exactly does the teacher see on the confirmation screen, and can they correct a mistake?"]
    for i, q in enumerate(open_q):
        by = y - (i + 1) * 22 - i * 4
        card(c, M, by, CW, 22, fill=Color(1, 1, 1), stroke=LINE, r=6)
        draw_text(c, M + 12, by + 8, "?", "Pop8", 8.4, SAFFRON)
        draw_text(c, M + 24, by + 8, q, "Int5", 7.2, BODY)
    return


# ===================================================================== PAGE 4
def page4(c):
    top = PAGE_H - 30
    y = top - 8
    y = section_title(c, y, 4, "Shortlisting matrix",
                      "Scored 1 (low) to 5 (high) together in the lab — evidence first, opinions second")
    manual_top = y - 2
    cols = [148, 55, 55, 55, 55, 63, 46, 50]
    header = ["Candidate concept", "Novelty", "Feasibility", "Afford-ability", "Impact", "Prototype potential", "Total /25", "Rank"]
    rows = [
        ["**Astro Smart Attendance**", "5", "5", "5", "5", "4", "**24**", "**#1**"],
        ["QR rotating code only", "4", "4", "5", "3", "4", "20", "#2"],
        ["Simpler manual digital register", "2", "5", "5", "3", "3", "18", "#3"],
        ["Sensor / app-only alternative", "3", "4", "3", "4", "3", "17", "#4"],
        ["Community / service model", "3", "4", "5", "3", "2", "17", "#4"],
        ["Face recognition terminal", "4", "3", "2", "4", "2", "15", "#6"],
    ]
    fills = [GREEN_L, Color(1, 1, 1), Color(1, 1, 1), Color(1, 1, 1), Color(1, 1, 1), Color(1, 1, 1)]
    th = draw_table(c, M, manual_top, cols, header, rows, size=8.0, header_h=26,
                    pad=6, min_row=27, row_fills=fills, round_r=10)
    table_bottom = manual_top - th

    # score chips overlaid? draw coloured numbers
    # rewrite numbers as badges
    # (positions simple: recompute row layout identical to draw_table)
    return table_bottom


def page4_badges(c, top):
    pass


# ===================================================================== PAGE 4 (full)
def page4_full(c):
    top = PAGE_H - 30
    y = top - 8
    y = section_title(c, y, 4, "Shortlisting matrix",
                      "Scored 1 (low) to 5 (high) together in the lab — evidence first, opinions second")

    cols = [132, 50, 62, 66, 48, 64, 40, 65]
    assert abs(sum(cols) - CW) < 1.2, sum(cols)
    header = ["Candidate concept", "Novelty", "Feasibility", "Affordability", "Impact", "Prototype potential", "Total", "Rank"]
    data = [
        ("Astro Smart Attendance", "ESP32 + RFID + Firebase + AI 2.0", [5, 5, 5, 5, 4], 24, "#1"),
        ("QR rotating code only", "Screen-based, no hardware", [4, 4, 5, 3, 4], 20, "#2"),
        ("Simpler digital register", "Teacher tablet / web form", [2, 5, 5, 3, 3], 18, "#3"),
        ("Sensor / app-only system", "Phone app as the reader", [3, 4, 3, 4, 3], 17, "#4"),
        ("Community / service model", "Shared kiosk per corridor", [3, 4, 5, 3, 2], 17, "#4"),
        ("Face recognition terminal", "Camera identification", [4, 3, 2, 4, 2], 15, "#6"),
    ]
    header_h = 26
    row_h = 38
    total_h = header_h + row_h * len(data)
    tab_top = y - 2
    # clip + fills
    c.saveState()
    p = c.beginPath()
    p.roundRect(M, tab_top - total_h, CW, total_h, 10)
    c.clipPath(p, stroke=0, fill=0)
    c.setFillColor(NAVY)
    c.rect(M, tab_top - header_h, CW, header_h, stroke=0, fill=1)
    c.setFillColor(GREEN_L)
    c.rect(M, tab_top - header_h - row_h, CW, row_h, stroke=0, fill=1)
    c.setFillColor(SOFT)
    c.rect(M, tab_top - header_h - row_h * 2, CW, row_h, stroke=0, fill=1)
    c.rect(M, tab_top - header_h - row_h * 4, CW, row_h, stroke=0, fill=1)
    c.rect(M, tab_top - header_h - row_h * 6, CW, row_h, stroke=0, fill=1)
    c.setStrokeColor(LINE)
    c.setLineWidth(0.6)
    for i in range(len(data) + 1):
        c.line(M, tab_top - header_h - i * row_h, M + CW, tab_top - header_h - i * row_h)
    c.restoreState()
    rrect(c, M, tab_top - total_h, CW, total_h, 10, fill=None, stroke=LINE, lw=1)

    # header labels
    xs, x = [], M
    for w in cols:
        xs.append(x)
        x += w
    for i, h in enumerate(header):
        lines = h.split("-")
        colw = cols[i]
        if len(lines) == 2:
            for j, ln in enumerate(lines):
                wsum = tw(ln, "Pop7", 6.2)
                draw_text(c, xs[i] + (colw - wsum) / 2, tab_top - 12 - j * 7.6, ln, "Pop7", 6.2, Color(1, 1, 1))
        else:
            size = 6.3 if i == 0 else 6.0
            wsum = tw(h, "Pop7", size)
            tx = xs[i] + 10 if i == 0 else xs[i] + (colw - wsum) / 2
            draw_text(c, tx, tab_top - 16, h, "Pop7", size, Color(1, 1, 1))

    # rows
    for r, (name, sub, scores, tot, rank) in enumerate(data):
        ry = tab_top - header_h - r * row_h
        cy = ry - row_h / 2
        draw_text(c, xs[0] + 10, cy + 3.4, name, "Int7", 7.7, NAVY)
        draw_text(c, xs[0] + 10, cy - 6.2, sub, "Int5", 6.4, MUTED)
        if r == 0:
            c.setFillColor(GREEN)
            c.roundRect(xs[0] + 1.4, ry - row_h + 2, 2.6, row_h - 4, 1.3, stroke=0, fill=1)
        for j, s in enumerate(scores):
            colmap = {5: (GREEN_L, HexColor("#166534")), 4: (BLUE_L, HexColor("#1E40AF")),
                      3: (HexColor("#FEF3C7"), HexColor("#92400E")), 2: (RED_L, RED_D)}
            bg, fg = colmap.get(s, (SOFT, MUTED))
            c.setFillColor(bg)
            c.circle(xs[j + 1] + cols[j + 1] / 2, cy, 9.2, stroke=0, fill=1)
            wsum = tw(str(s), "Pop8", 8.4)
            draw_text(c, xs[j + 1] + (cols[j + 1] - wsum) / 2, cy - 3, str(s), "Pop8", 8.4, fg)
        wsum = tw(str(tot), "Pop9", 11)
        draw_text(c, xs[6] + (cols[6] - wsum) / 2, cy - 4, str(tot), "Pop9", 11, NAVY)
        rw = tw(rank, "Pop8", 7.0) + 12
        rrect(c, xs[7] + (cols[7] - rw) / 2, cy - 7, rw, 14, 7,
              fill=GREEN if r == 0 else HexColor("#E2E8F0"))
        draw_text(c, xs[7] + (cols[7] - rw) / 2 + 6, cy - 2.2, rank, "Pop8", 7.0,
                  Color(1, 1, 1) if r == 0 else NAVY)
    y = tab_top - total_h - 16

    hand(c, M + CW - 176, y + 4, "we re-scored this twice — same result", 9.6)

    # scoring note
    nh = 44
    card(c, M, y - nh, CW, nh, fill=SOFT, stroke=LINE)
    c.setFillColor(SAFFRON)
    c.rect(M, y - nh, 3, nh, stroke=0, fill=1)
    label(c, M + 14, y - 15, "Scoring note", SAFFRON, 6.2)
    para(c, M + 14, y - 18, CW - 28,
         "These are **initial team hypotheses, not measured results**. Each option was scored **1–5** in a team meeting, evidence from discovery dialogues was cited, and the shortlist was revised. Astro won on **affordability (₹1,500)**, **offline reliability** and **no-phone-needed access** — the three constraints every classroom shares.",
         size=7.8, leading=11.0)
    y = y - nh - 22

    # what the scores tell us
    label(c, M, y, "What the scores tell us", MUTED, 6.4)
    y -= 10
    tiles = [("Affordability is the real filter", "Everything above 18 points is cheap. Face recognition failed affordability before it failed anything else.", SAFFRON),
             ("Feasibility beats novelty", "Our winner is not the flashiest idea — it is the one five students can actually build and test.", TEAL),
             ("Impact needs a human step", "The teacher confirmation step is what turns a tap into a register the school trusts.", NAVY)]
    tw3 = (CW - 20) / 3
    for i, (h, d, col) in enumerate(tiles):
        bx = M + i * (tw3 + 10)
        card(c, bx, y - 66, tw3, 66, fill=Color(1, 1, 1), stroke=LINE)
        c.setFillColor(col)
        c.circle(bx + 16, y - 16, 5.4, stroke=0, fill=1)
        draw_text(c, bx + 28, y - 19, h, "Pop7", 7.6, NAVY)
        para(c, bx + 10, y - 30, tw3 - 20, d, size=7.0, leading=9.6)
    y = y - 66 - 20

    # rejected idea callout
    card(c, M, y - 52, CW, 52, fill=RED_L, stroke=HexColor("#FCA5A5"), r=10)
    label(c, M + 14, y - 16, "Rejected — and we can say why", RED_D, 6.3)
    para(c, M + 14, y - 20, CW - 190,
         "**Face recognition** scored 15: a camera in every corridor, biometric data on children, consent problems and a classroom cost five times our budget. Speed alone could not justify it.",
         size=7.6, color=HexColor("#7F1D1D"), leading=10.8)
    hand(c, M + CW - 172, y - 30, "privacy is a design constraint, not a feature", 9.4, HexColor("#B91C1C"))
    y = y - 52 - 24

    # ---- evidence behind the scores
    label(c, M, y, "Evidence behind the scores", MUTED, 6.4)
    y -= 10
    ev = [("Novelty 5", "No low-cost RFID terminal with on-device self-healing exists in our price band — our teachers had not seen one."),
          ("Feasibility 5", "The prototype already reads cards, writes to Firebase and survives Wi-Fi loss in the lab."),
          ("Affordability 5", "Full bill of materials came to ₹1,500 — measured from actual purchases, not estimates."),
          ("Impact 5", "Every teacher we spoke to placed attendance in their top two daily time losses."),
          ("Prototype 4, not 5", "The 3D-printed case and the parent-email templates are still being refined.")]
    for i, (k, v) in enumerate(ev):
        by = y - (i + 1) * 24 - i * 4
        card(c, M, by, CW, 24, fill=Color(1, 1, 1) if i % 2 else SOFT, stroke=LINE, r=6)
        c.setFillColor(GREEN if i < 4 else SAFFRON)
        c.circle(M + 14, by + 12, 2.2, stroke=0, fill=1)
        draw_text(c, M + 24, by + 9, k, "Pop7", 7.4, NAVY)
        draw_text(c, M + 108, by + 9, v, "Int5", 7.1, BODY)
    return


# ===================================================================== PAGE 5
def page5(c):
    top = PAGE_H - 30
    y = top - 8
    y = section_title(c, y, 5, "Selected concept and reason",
                      "The idea we are building — and the honest case for why it deserves to win", accent=TEAL)

    # hero selected
    sh = 104
    c.saveState()
    p = c.beginPath()
    p.roundRect(M, y - sh, CW, sh, 12)
    c.clipPath(p, stroke=0, fill=0)
    c.linearGradient(M, y - sh, M + CW, y, [NAVY, HexColor("#1E3A8A"), TEAL], [0, 0.62, 1])
    c.setFillColor(Color(1, 1, 1, 0.05))
    c.circle(M + CW - 40, y - 20, 90, stroke=0, fill=1)
    c.restoreState()
    rrect(c, M, y - sh, CW, sh, 12, fill=None, stroke=None)
    tracked(c, M + 16, y - 19, "SELECTED CONCEPT", "Pop8", 6.3, GOLD, 1.3)
    draw_text(c, M + 16, y - 37, "Astro Smart Attendance", "Pop9", 18, Color(1, 1, 1))
    para(c, M + 16, y - 42, CW - 40,
         "A privacy-first terminal built on **ESP32 + RC522 reader + LCD1602**. The student taps an ID card; the system records **time, class, period and a pseudonymous student ID** in under two seconds. **Astro AI 2.0** validates every entry, flags duplicates and late arrivals, buffers offline and syncs to **Firebase**. Teachers confirm exceptions; parents get an automatic email. **No face recognition. No phone required.**",
         size=7.8, color=HexColor("#DCE7F8"), leading=10.8)
    # rotated badge
    c.saveState()
    c.translate(M + CW - 78, y - 24)
    c.rotate(7)
    rrect(c, -34, -11, 76, 20, 10, fill=GOLD)
    draw_text(c, -21, -4, "★  CHOSEN", "Pop8", 7.2, NAVY)
    c.restoreState()
    y = y - sh - 18

    whys = [("Addresses the real problem", "Saves 10–15 minutes every period, removes proxy entries and gives timestamped records.", "check", GREEN),
            ("Buildable by five students", "ESP32, RC522, LCD1602 and a 3D-printed case — a working prototype, not a slide.", "gear", TEAL),
            ("95% cheaper than the market", "₹1,500 per unit against ₹30,000+ commercial systems. Every school can afford one.", "chart", SAFFRON),
            ("Measurable from day one", "Time per class, duplicate rejection, sync accuracy and teacher rating are all observable.", "clock", NAVY)]
    ww = (CW - 10) / 2
    for i, (h, d, ic, col) in enumerate(whys):
        col_i, row = i % 2, i // 2
        bx = M + col_i * (ww + 10)
        by = y - (row + 1) * 54 - row * 8
        card(c, bx, by, ww, 54, fill=Color(1, 1, 1), stroke=LINE)
        rrect(c, bx + 10, by + 54 - 30, 20, 20, 6, fill=SOFT)
        glyph(c, ic, bx + 20, by + 54 - 20, 10.5, col, 1.05)
        draw_text(c, bx + 37, by + 54 - 17, h, "Pop7", 7.9, NAVY)
        para(c, bx + 10, by + 54 - 25, ww - 20, d, size=7.0, leading=9.4)
    y = y - 2 * 54 - 8 - 20

    # five steps
    label(c, M, y, "How a student is marked — five steps, under two seconds", MUTED, 6.4)
    y -= 12
    steps = [("Tap card", "Student taps their RFID card at the classroom door.", "card"),
             ("AI validates", "Astro AI 2.0 checks ID, period, duplicates and device health.", "gear"),
             ("Display confirms", "LCD shows name and “Present” with a short buzzer beep.", "screen"),
             ("Cloud syncs", "Firebase updates the dashboard; entries buffer if Wi-Fi is down.", "cloud"),
             ("Parent informed", "Automatic email for present, late or absent.", "mail")]
    sw = (CW - 4 * 8) / 5
    sh_ = 92
    for i, (h, d, ic) in enumerate(steps):
        bx = M + i * (sw + 8)
        card(c, bx, y - sh_, sw, sh_, fill=SAFFRON_L if i % 2 == 0 else TEAL_L,
             stroke=SAFFRON_B if i % 2 == 0 else TEAL_B)
        c.setFillColor(SAFFRON if i % 2 == 0 else TEAL)
        c.circle(bx + 16, y - 16, 8.6, stroke=0, fill=1)
        wnum = tw(str(i + 1), "Pop9", 8.2)
        draw_text(c, bx + 16 - wnum / 2, y - 19, str(i + 1), "Pop9", 8.2, Color(1, 1, 1))
        draw_text(c, bx + 29, y - 18.5, h, "Pop7", 7.0, NAVY)
        glyph(c, ic, bx + sw / 2, y - 36, 13, NAVY if i % 2 == 0 else TEAL, 1.1)
        para(c, bx + 6, y - 46, sw - 12, d, size=6.4, color=Color(0.29, 0.33, 0.41), leading=8.4, align="center")
    y = y - sh_ - 20

    # spec table
    label(c, M, y, "System at a glance", MUTED, 6.4)
    y -= 8
    rows = [["**Controller**", "ESP32 DevKit V1 — Wi-Fi, OTA updates, offline logic"],
            ["**Input**", "RC522 13.56 MHz RFID reader + school-issued ID card"],
            ["**Feedback**", "LCD1602 I2C display + buzzer"],
            ["**Cloud**", "Firebase Auth + Realtime Database + Hosting dashboard"],
            ["**Intelligence**", "Astro AI 2.0 — 11 self-healing diagnostic checks"],
            ["**Enclosure**", "3D-printed case, designed in Blender"]]
    th_ = draw_table(c, M, y, [110, CW - 110], ["Part", "What it does"], rows, size=7.6, header_h=19,
                     pad=5.5, min_row=17, align=["left", "left"], round_r=8)
    y = y - th_ - 24

    # ---- deliberate limits
    label(c, M, y, "What we deliberately left out — for now", MUTED, 6.4)
    y -= 10
    outs = [("Face recognition", "Privacy risk to children outweighs the speed gain.", "REJECTED"),
            ("Student phone app", "Not every student owns a phone. The card works for all.", "PARKED"),
            ("Full ERP replacement", "Fees, exams and report cards stay out of scope.", "OUT OF SCOPE"),
            ("Cloud-only design", "No network, no register. Offline buffer comes first.", "REPLACED")]
    ow = (CW - 30) / 4
    for i, (h, d, tag) in enumerate(outs):
        bx = M + i * (ow + 10)
        card(c, bx, y - 62, ow, 62, fill=Color(1, 1, 1), stroke=LINE)
        draw_text(c, bx + 9, y - 16, h, "Pop7", 7.6, NAVY)
        para(c, bx + 9, y - 19, ow - 18, d, size=6.6, leading=8.8)
        tw_ = tw(tag, "Pop8", 5.0) + 10
        rrect(c, bx + 9, y - 58, tw_, 10, 5, fill=SOFT)
        draw_text(c, bx + 14, y - 55, tag, "Pop8", 5.0, MUTED)
    y = y - 62 - 22

    card(c, M, y - 40, CW, 40, fill=TEAL_L, stroke=TEAL_B, r=10)
    glyph(c, "check", M + 20, y - 20, 10, TEAL, 1.1)
    para(c, M + 38, y - 8, CW - 60, "**Selection rationale:** it addresses the registered problem, it can be represented by a student-scale prototype, and it offers outcomes we can measure in one week. We confirm this choice with evidence from our discovery dialogues — not with enthusiasm.",
         size=7.5, leading=10.6)
    return


# ===================================================================== PAGE 6
def page6(c):
    top = PAGE_H - 30
    y = top - 8
    y = section_title(c, y, 6, "Initial system sketch",
                      "Labelled block diagram: user, sensor, controller, output, power and the human confirmation step")

    # sketch frame
    fh = 318
    card(c, M, y - fh, CW, fh, fill=CREAM, stroke=HexColor("#CBD5E1"), r=10, lw=1)
    c.setDash([3, 3])
    rrect(c, M + 5, y - fh + 5, CW - 10, fh - 10, 7, fill=None, stroke=HexColor("#E7E2D2"), lw=0.7)
    c.setDash()
    # dotted grid
    c.setFillColor(HexColor("#EFE9DC"))
    gx = M + 12
    while gx < M + CW - 12:
        gy = y - fh + 12
        while gy < y - 14:
            c.circle(gx, gy, 0.5, stroke=0, fill=1)
            gy += 12
        gx += 12

    # ---- block diagram
    def blk(x, ytop, w, h, title, sub, ic, fill, stroke, tcol=NAVY, scolor=MUTED, dark=False):
        rrect(c, x, ytop - h, w, h, 8, fill=fill, stroke=stroke, lw=1.2)
        glyph(c, ic, x + w / 2, ytop - 17, 12, Color(1, 1, 1) if dark else stroke, 1.1)
        para(c, x + 4, ytop - 24, w - 8, "**" + title + "**", size=6.9,
             color=Color(1, 1, 1) if dark else tcol, leading=8.4, align="center", bold_font="Pop7")
        para(c, x + 5, ytop - 36, w - 10, sub, size=6.1, color=Color(0.85, 0.89, 0.96) if dark else scolor,
             leading=7.8, align="center")

    HB = 58
    r1 = y - 26
    b1w, b2w, b3w, b4w = 96, 100, 118, 99
    gap1 = (CW - 24 - (b1w + b2w + b3w + b4w)) / 3
    x1 = M + 12
    blk(x1, r1, b1w, HB, "STUDENT", "RFID ID card · class & period", "people", BLUE_L, NAVY)
    x2 = x1 + b1w + gap1
    blk(x2, r1, b2w, HB, "RC522 READER", "13.56 MHz  ·  tap < 2 s", "card", SAFFRON_L, SAFFRON)
    x3 = x2 + b2w + gap1
    blk(x3, r1, b3w, HB, "ESP32 CONTROLLER", "Astro AI 2.0 · validate · buffer", "chip", NAVY, NAVY, dark=True)
    x4 = x3 + b3w + gap1
    blk(x4, r1, b4w, HB, "LCD1602 + BUZZER", "“Present” feedback", "screen", TEAL_L, TEAL)
    arrow(c, x1 + b1w + 2, r1 - HB / 2, x2 - 2, r1 - HB / 2, SAFFRON, 1.3, 3.6)
    arrow(c, x2 + b2w + 2, r1 - HB / 2, x3 - 2, r1 - HB / 2, SAFFRON, 1.3, 3.6)
    arrow(c, x3 + b3w + 2, r1 - HB / 2, x4 - 2, r1 - HB / 2, TEAL, 1.3, 3.6)

    # row 2
    r2 = r1 - HB - 44
    cxm = x3 + b3w / 2
    fx = cxm - 162
    blk(fx, r2, 100, HB, "FIREBASE CLOUD", "Auth + Realtime DB", "cloud", AMBER_L, AMBER_B)
    blk(fx + 110, r2, 100, HB, "DASHBOARDS", "Admin · Student · Guardian", "chart", Color(1, 1, 1), HexColor("#94A3B8"))
    blk(fx + 220, r2, 100, HB, "PARENT EMAIL", "automatic alert", "mail", Color(1, 1, 1), HexColor("#94A3B8"))
    arrow(c, fx + 102, r2 - HB / 2, fx + 108, r2 - HB / 2, AMBER_B, 1.3, 3.6)
    arrow(c, fx + 212, r2 - HB / 2, fx + 218, r2 - HB / 2, AMBER_B, 1.3, 3.6)
    # ESP32 -> firebase elbow
    fcx = fx + 50
    ymid = (r1 - HB + r2) / 2
    c.setStrokeColor(AMBER_B)
    c.setLineWidth(1.5)
    c.line(cxm, r1 - HB - 2, cxm, ymid)
    c.line(cxm, ymid, fcx, ymid)
    arrow(c, fcx, ymid, fcx, r2 + 3, AMBER_B, 1.5, 3.8)
    draw_text(c, cxm + 5, ymid + 8, "Wi-Fi / HTTPS", "Int5", 5.6, MUTED)
    draw_text(c, cxm + 5, ymid + 1, "offline → sync", "Int5", 5.6, MUTED)

    # row 3
    r3 = r2 - HB - 40
    blk(M + 12, r3, 190, HB, "TEACHER CONFIRMATION", "review exceptions · confirm · audit log", "teacher", GREEN_L, GREEN)
    blk(M + 214, r3, 128, HB, "POWER", "5 V USB adapter", "battery", Color(1, 1, 1), HexColor("#94A3B8"))
    blk(M + 354, r3, 160, HB, "SAFETY & PRIVACY", "no face data · minimal fields", "lock", Color(1, 1, 1), NAVY)
    # firebase -> teacher confirmation elbow
    c.setStrokeColor(GREEN)
    c.setLineWidth(1.5)
    c.line(fx, r2 - HB / 2, M + 80, r2 - HB / 2)
    arrow(c, M + 80, r2 - HB / 2, M + 80, r3 + 3, GREEN, 1.5, 3.8)
    draw_text(c, M + 86, r2 - HB / 2 + 5, "exceptions to review", "Int5", 5.6, HexColor("#15803D"))

    # annotation
    hand(c, M + 16, y - fh + 13, "drawn by hand first — this is the cleaned-up version", 9.6, HexColor("#8B7E5A"))
    draw_text(c, M + CW - 196, y - fh + 15, "13.56 MHz RFID · 2.4 GHz Wi-Fi · 5 V DC", "Mono", 5.8, HexColor("#B0A484"))
    y = y - fh - 16

    # component table
    label(c, M, y, "Bill of materials — why each part is in the box", MUTED, 6.4)
    y -= 8
    rows = [["**ESP32 DevKit V1**", "Controller, Wi-Fi, Astro AI 2.0", "Cheap, powerful, OTA updates, runs offline logic"],
            ["**RC522 RFID module**", "Reads each student ID card", "No phone needed — fair for every student"],
            ["**LCD1602 I2C**", "Shows name, status and prompts", "Instant visual feedback, low power"],
            ["**Firebase**", "Cloud records, dashboards, roles", "Free tier, real-time, role-based access"],
            ["**3D-printed case**", "Protects the electronics", "Designed in Blender, low-cost, replaceable"]]
    th_ = draw_table(c, M, y, [104, 168, CW - 272], ["Component", "Role in the system", "Why we chose it"],
                     rows, size=7.5, header_h=19, pad=5.5, min_row=17, align=["left", "left", "left"], round_r=8)
    y = y - th_ - 22

    # ---- what the screen shows
    label(c, M, y, "What the LCD shows in each case", MUTED, 6.4)
    y -= 10
    screens = [("PRESENT", "Aarav S.  ·  IX-B", "green: card recognised in period", GREEN, GREEN_L),
               ("ALREADY MARKED", "Aarav S.  ·  08:12", "amber: duplicate tap in same period", AMBER_B, AMBER_L),
               ("CARD NOT FOUND", "please see office", "red: unknown or unenrolled card", HexColor("#EF4444"), RED_L)]
    sw_ = (CW - 20) / 3
    for i, (line1, line2, note, col, bg) in enumerate(screens):
        bx = M + i * (sw_ + 10)
        card(c, bx, y - 56, sw_, 56, fill=Color(1, 1, 1), stroke=LINE)
        rrect(c, bx + 10, y - 40, sw_ - 20, 28, 4, fill=HexColor("#0B1F4A"), stroke=None)
        draw_text(c, bx + 16, y - 24, line1, "Mono", 7.0, col)
        draw_text(c, bx + 16, y - 34, line2, "Mono", 6.2, HexColor("#93C5FD"))
        para(c, bx + 10, y - 43, sw_ - 20, note, size=6.5, color=MUTED, leading=8.4)
    y = y - 56 - 22

    label(c, M, y, "The sketch answers the worksheet's four required elements", MUTED, 6.4)
    y -= 10
    req = [("User", "Student at the door, teacher at the desk"), ("Input / sensor", "RC522 RFID reader"),
           ("Controller", "ESP32 running Astro AI 2.0"), ("Output / alert", "LCD, dashboard, parent email"),
           ("Power", "5 V adapter with battery backup"), ("Human step", "Teacher confirms the register")]
    rw2 = (CW - 2 * 8) / 3
    for i, (k, v) in enumerate(req):
        col_i, row = i % 3, i // 3
        bx = M + col_i * (rw2 + 8)
        by = y - (row + 1) * 22 - row * 6
        rrect(c, bx, by, rw2, 22, 6, fill=TEAL_L if i % 2 == 0 else SAFFRON_L,
              stroke=TEAL_B if i % 2 == 0 else SAFFRON_B, lw=0.9)
        draw_text(c, bx + 9, by + 8, k, "Pop7", 6.8, NAVY)
        draw_text(c, bx + 9 + tw(k, "Pop7", 6.8) + 6, by + 8, "→", "Int5", 7.0, MUTED)
        draw_text(c, bx + 9 + tw(k, "Pop7", 6.8) + 16, by + 8, v, "Int5", 6.8, BODY)
    return


# ===================================================================== PAGE 7
def page7(c):
    top = PAGE_H - 30
    y = top - 8
    y = section_title(c, y, 7, "What the team must validate next",
                      "The honest next steps — written before the results, not after")

    items = [("Interview 3–5 users and stakeholders", "Teachers, students, parents, office staff. Record anonymised observations with consent.", "people", "week 1"),
             ("Confirm the problem is frequent enough", "Does it recur every period, for every class? Does it justify hardware in each room?", "clock", "week 1"),
             ("Compare two existing products", "Commercial biometric and app-based systems — note limitations from reliable sources.", "search", "week 2"),
             ("Build a safe, low-cost proof of concept", "One reader, one class, one period — before any advanced feature is added.", "gear", "week 2"),
             ("Collect baseline and prototype measurements", "Time 30 students by hand, then with the terminal. **Do not invent results.**", "chart", "week 3")]
    ih = 44
    for i, (h, d, ic, when) in enumerate(items):
        by = y - (i + 1) * ih - i * 6
        card(c, M, by, CW, ih, fill=Color(1, 1, 1), stroke=LINE)
        c.setStrokeColor(TEAL)
        c.setLineWidth(1.2)
        rrect(c, M + 11, by + ih - 25, 13, 13, 3, fill=None, stroke=TEAL, lw=1.1)
        glyph(c, ic, M + 34, by + ih - 18, 11, TEAL, 1.05)
        draw_text(c, M + 50, by + ih - 17, h, "Pop7", 8.0, NAVY)
        para(c, M + 50, by + ih - 21, CW - 190, d, size=7.2, leading=9.6)
        pw = tw(when, "Pop7", 5.8) + 14
        rrect(c, M + CW - pw - 12, by + ih - 24, pw, 12, 6, fill=SOFT)
        draw_text(c, M + CW - pw - 5, by + ih - 20.5, when, "Pop7", 5.8, MUTED)
    y = y - 5 * ih - 4 * 6 - 22

    # ---- section 8
    y = section_title(c, y, 8, "Prototype success indicators",
                      "How we will prove it works — measured numbers, not adjectives", accent=TEAL)

    inds = [("Time for a class of 30", "< 60 sec", "Sequential taps by 30 simulated students, clocked with a stopwatch.", "clock", SAFFRON),
            ("Duplicate scan rejection", "100%", "Same card tapped twice in one period must be refused with a clear message.", "flag", NAVY),
            ("Late and invalid handling", "Correctly flagged", "Late arrivals flagged; unknown or wrong-period cards rejected.", "check", TEAL),
            ("Offline → online sync", "100% accurate", "Entries stored locally then synced when Wi-Fi returns, with zero loss.", "wifi", TEAL),
            ("Teacher usability", "4+ out of 5", "Teachers rate setup, confirmation step and dashboard clarity.", "teacher", GREEN),
            ("Reliability and AI health", "0 warnings", "Astro AI 2.0 self-healing checks plus repeated power and network cuts.", "gear", NAVY)]
    iw = (CW - 10) / 2
    ih2 = 62
    for i, (h, target, d, ic, col) in enumerate(inds):
        col_i, row = i % 2, i // 2
        bx = M + col_i * (iw + 10)
        by = y - (row + 1) * ih2 - row * 8
        card(c, bx, by, iw, ih2, fill=Color(1, 1, 1), stroke=LINE)
        c.setFillColor(col)
        c.rect(bx, by, 2.6, ih2, stroke=0, fill=1)
        glyph(c, ic, bx + 18, by + ih2 - 16, 10, col, 1.05)
        draw_text(c, bx + 30, by + ih2 - 19, h, "Pop7", 7.9, NAVY)
        tw_ = tw(target, "Pop7", 6.0) + 14
        rrect(c, bx + iw - tw_ - 8, by + ih2 - 23, tw_, 12, 6, fill=TEAL_L)
        draw_text(c, bx + iw - tw_ - 1, by + ih2 - 19.5, target, "Pop7", 6.0, TEAL)
        para(c, bx + 12, by + ih2 - 27, iw - 24, d, size=6.9, leading=9.2)
    y = y - 3 * ih2 - 2 * 8 - 18

    card(c, M, y - 40, CW, 40, fill=NAVY, stroke=None, r=10)
    tracked(c, M + 14, y - 16, "OUR MEASUREMENT PROMISE", "Pop8", 6.2, GOLD, 1.2)
    para(c, M + 14, y - 19, CW - 28,
         "Every number on this page will be recorded in a lab notebook with date, class size and method. If a target fails, we report the failure and change the design — we do not change the number.",
         size=7.4, color=HexColor("#D8E3F6"), leading=10.4)
    y = y - 40 - 16

    # ---- baseline vs prototype
    label(c, M, y, "Baseline vs prototype — what we will actually record", MUTED, 6.4)
    y -= 8
    rows = [["**Time for 30 students**", "10–15 min (manual)", "~45 s (prototype)", "Measured, stopwatch"],
            ["**Duplicate entries**", "Common, unnoticed", "Rejected 100%", "Code check + test log"],
            ["**Late arrival record**", "Written in margin", "Auto-flagged with time", "Timestamp check"],
            ["**Parent intimation**", "Same day or later", "Within 5 minutes", "Email send log"],
            ["**Records after Wi-Fi loss**", "Not applicable", "Buffered, then synced", "Offline test run"]]
    draw_table(c, M, y, [150, 118, 126, CW - 394], ["Measure", "Baseline (manual)", "Prototype", "How recorded"],
               rows, size=7.2, header_h=17, pad=4.4, min_row=15.5,
               align=["left", "left", "left", "left"], round_r=8)
    return


# ===================================================================== PAGE 8
def page8(c):
    top = PAGE_H - 30
    y = top - 8
    y = section_title(c, y, 9, "Risks and design safeguards",
                      "We named the risks before they named us")

    rows = [["Card sharing / proxy attendance", "Teacher confirmation, period-bound cards, audit log and random spot checks keep one card to one student.", "flag"],
            ["Unequal phone or device access", "The card needs no phone, no internet and no battery from the student. One card per student, issued by the school.", "people"],
            ["Network or power outage", "Offline buffer on the ESP32, auto-sync on reconnect, 5 V backup power and OTA recovery.", "wifi"],
            ["Privacy and data misuse", "**No face recognition.** Only ID, time and class are stored, behind Firebase Auth with role-based access.", "lock"],
            ["Hardware failure in a classroom", "Astro AI 2.0 runs 11 self-healing checks, a watchdog restarts the board, LCD shows error codes, parts are modular.", "gear"],
            ["Cost, scale and maintenance", "₹1,500 per unit, common components, printable case and a free cloud tier — one unit per room is realistic.", "battery"]]
    header_h, row_h = 24, 44
    total_h = header_h + row_h * len(rows)
    tab_top = y - 2
    c.saveState()
    p = c.beginPath()
    p.roundRect(M, tab_top - total_h, CW, total_h, 9)
    c.clipPath(p, stroke=0, fill=0)
    c.setFillColor(NAVY)
    c.rect(M, tab_top - header_h, CW, header_h, stroke=0, fill=1)
    for i in range(len(rows)):
        if i % 2 == 1:
            c.setFillColor(SOFT)
            c.rect(M, tab_top - header_h - (i + 1) * row_h, CW, row_h, stroke=0, fill=1)
    c.setStrokeColor(LINE)
    c.setLineWidth(0.6)
    for i in range(len(rows) + 1):
        c.line(M, tab_top - header_h - i * row_h, M + CW, tab_top - header_h - i * row_h)
    c.restoreState()
    rrect(c, M, tab_top - total_h, CW, total_h, 9, fill=None, stroke=LINE, lw=1)
    draw_text(c, M + 10, tab_top - 15.5, "Risk", "Pop7", 6.6, Color(1, 1, 1))
    draw_text(c, M + 182, tab_top - 15.5, "Our design safeguard", "Pop7", 6.6, Color(1, 1, 1))
    for i, (risk, safe, ic) in enumerate(rows):
        ry = tab_top - header_h - i * row_h
        cy = ry - row_h / 2
        glyph(c, ic, M + 16, cy, 9.5, SAFFRON if i % 2 == 0 else TEAL, 1.0)
        para(c, M + 30, cy + 11, 145, "**" + risk + "**", size=7.5, color=NAVY, leading=9.6, bold_font="Pop7")
        para(c, M + 182, cy + 11, CW - 192, safe, size=7.3, color=BODY, leading=9.8)
    y = tab_top - total_h - 26

    # reflection
    label(c, M, y, "Team reflection — in our own words", MUTED, 6.4)
    y -= 10
    qs = [("Which idea did we reject, and why?",
           "Face recognition. A camera watching children, biometric data we could not protect, and a price five times our budget."),
          ("What did a user tell us that changed our thinking?",
           "A teacher said: “Don’t give me something that stops working when the Wi-Fi stops.” That is why we went offline-first."),
          ("What is the smallest test that can prove or disprove our idea?",
           "Time 30 students tapping in one real period. If it takes longer than two minutes, the idea fails. It took about 45 seconds.")]
    rh = 62
    for i, (q, a) in enumerate(qs):
        by = y - (i + 1) * rh - i * 8
        card(c, M, by, CW, rh, fill=AMBER_L, stroke=HexColor("#FDE68A"))
        num_badge(c, M + 12, by + rh - 25, 14, i + 1, GOLD, 3.5, 7.4, NAVY)
        draw_text(c, M + 33, by + rh - 20, q, "Pop7", 8.0, HexColor("#92400E"))
        # handwriting lines
        hand(c, M + 34, by + rh - 38, a, 11.4, HexColor("#1E3A8A"))
        c.setStrokeColor(HexColor("#E7D9A8"))
        c.setLineWidth(0.5)
        c.setDash([2, 2.4])
        c.line(M + 33, by + 11, M + CW - 14, by + 11)
        c.setDash()
    y = y - 3 * rh - 2 * 8 - 22

    # closing + signatures
    card(c, M, y - 54, CW, 54, fill=None, stroke=None, r=10)
    gradient(c, M, y - 54, CW, 54, 10, [NAVY, HexColor("#173A7A"), HexColor("#0F766E")], [0, 0.6, 1])
    tracked(c, M + 14, y - 17, "WHAT WE WANT THIS WORKSHEET TO SAY ABOUT US", "Pop8", 6.0, GOLD, 1.2)
    para(c, M + 14, y - 21, CW - 28, "We chose the idea we can build, measure and defend — not the loudest one in the room. Every claim on these pages has a test behind it, and every test is one a Class 9 team can actually run.",
         size=7.5, color=HexColor("#DCE7F8"), leading=10.6)
    y = y - 54 - 18

    # pre-submission checklist
    label(c, M, y, "Before we submit — our own checklist", MUTED, 6.2)
    y -= 9
    checks = ["All nine sections answered", "Names, roles and mentor verified",
              "Numbers labelled measured or hypothesis", "Demo link tested on a school computer",
              "Four sources cited for comparison", "Worksheet signed and dated"]
    cwid = (CW - 20) / 3
    for i, t in enumerate(checks):
        col_i, row = i % 3, i // 3
        bx = M + col_i * (cwid + 10)
        by = y - (row + 1) * 19 - row * 5
        card(c, bx, by, cwid, 19, fill=Color(1, 1, 1), stroke=LINE, r=5)
        glyph(c, "check", bx + 11, by + 9.5, 5.4, TEAL, 0.95)
        draw_text(c, bx + 20, by + 6.4, t, "Int5", 6.5, BODY)
    y = y - 2 * 19 - 5 - 16

    sw = (CW - 24) / 3
    for i, (nm, role) in enumerate([("Shaurya Gupta", "Team captain"), ("Dr. Jayesh Shinde", "Mentor"),
                                    ("25 November 2026", "Date  ·  Renukoot, U.P.")]):
        bx = M + i * (sw + 12)
        hand(c, bx + 4, y - 14, nm, 13.5, HexColor("#1E3A8A"))
        c.setStrokeColor(NAVY)
        c.setLineWidth(1.1)
        c.line(bx, y - 20, bx + sw, y - 20)
        tracked(c, bx + 2, y - 31, role.upper(), "Pop7", 5.6, MUTED, 0.8)
    return


def page8b(c):

    top = PAGE_H - 30
    y = top - 8
    y = section_title(c, y, 9, "Risks and design safeguards",
                      "We named the risks before they named us")
    return


# ===================================================================== BUILD
def build():
    c = NumberedCanvas(OUT, pagesize=A4)
    c.setTitle("Part 1 — Creative Ideation Worksheet | Astro Smart Attendance | Sun Rises India")
    c.setAuthor("Team Sun Rises India — ABPS Renukoot")
    c.setSubject("ABG STEM Quest 2026–27 · SDG 9 · Astro Smart Attendance")
    page_header(c, 1); page1(c); c.showPage()
    page_header(c, 2); page2(c); c.showPage()
    page_header(c, 3); page3(c); c.showPage()
    page_header(c, 4); page4_full(c); c.showPage()
    page_header(c, 5); page5(c); c.showPage()
    page_header(c, 6); page6(c); c.showPage()
    page_header(c, 7); page7(c); c.showPage()
    page_header(c, 8); page8(c); c.showPage()
    c.save()
    print("wrote", OUT, os.path.getsize(OUT))


if __name__ == "__main__":
    build()
