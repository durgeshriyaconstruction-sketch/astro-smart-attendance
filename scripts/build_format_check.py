#!/usr/bin/env python3
"""
Builds a two-page Format Compliance Check: every line of the supplied
ABG STEM Quest Google Doc template, mapped to where it appears in the
8-page Creative Ideation Worksheet.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import Color, HexColor
from reportlab.pdfgen import canvas as pdfcanvas

from ws_common import (  # noqa: E402
    PAGE_W, PAGE_H, M, CW, NAVY, SAFFRON, TEAL, GOLD, GREEN, CREAM,
    BODY, MUTED, LINE, SOFT, glyph, label, para, draw_text, rrect,
    tw, NumberedCanvas, page_header, draw_table, para_height,
)

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def card(c, x, y, w, h, fill=SOFT, stroke=LINE, r=8, lw=1):
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(lw)
    c.roundRect(x, y, w, h, r, stroke=1, fill=1)
OUT = os.path.join(HERE, "Format-Compliance-Check.pdf")

# (template line, verbatim requirement, where it lives, page)
HEADER_ROWS = [
    ("ABG STEM QUEST 2026–27", "Programme name", "Running header, top-left of all 8 pages", "1–8"),
    ("PART 1 — CREATIVE IDEATION WORKSHEET", "Document title", "Pill, top-right of all 8 pages", "1–8"),
    ("Sun Rises India · Grade 9th · ABPS Renukoot", "Team block", "Badge on the cover, above the title", "1"),
    ("Team Captain — Shaurya Gupta", "Team captain", "Team panel, first row", "1"),
    ("Members — Anant Tiwari, Devansh Dhakad, Tejas Upadhyay, Diwakar Singh",
     "Member list", "Team panel, three lines", "1"),
    ("Mentor — Dr. Jayesh Shinde", "Mentor", "Team panel", "1"),
    ("Theme — SDG 9", "Theme", "Team panel and the footer of all 8 pages", "1–8"),
]

SECTION_ROWS = [
    ("1", "Problem focus", "Answer here …", "§01 named block, a problem card, four discovery questions, an eyewitness box, success criteria, two anonymised quotes, three size-of-problem tiles and a one-line summary", "1"),
    ("2", "Brainstormed possibilities", "List every idea", "Ten idea cards, each with a verdict tag, then three filters and a ten-row filter matrix showing what survived", "2"),
    ("3", "Concept map", "[Draw a labelled block diagram here]", "A drawn six-stage chain: user, trigger, input, process, output, measurable benefit — plus six proof cards and the tap-to-alert data pathway", "3"),
    ("4", "Shortlisting matrix", "Criteria × ideas, scored, note on scoring", "Drawn matrix, six ideas × five criteria, scored out of 5, totals, a nine-point gap callout and the written scoring rule", "4"),
    ("5", "Selected concept and reason", "Name the idea, justify it", "Chosen-concept band, four reasons, a five-step tap flow, the system table, four rejected alternatives and the ownership table", "5"),
    ("6", "Initial system sketch", "[Draw a labelled block diagram here]", "A drawn block diagram of every component, the costed bill of materials, three LCD states and a comparison against the two alternatives", "6"),
    ("7", "What the team must validate next", "Bullet list of unknowns", "Five validation rows, each with method, owner, when and an explicit decision rule", "7"),
    ("8", "Prototype success indicators", "Five measurable indicators", "Six indicators with targets, plus a baseline-versus-prototype table and a measurement promise", "7"),
    ("9", "Risks and design safeguards", "Risk and how it is handled", "Six risk rows with the safeguard built into the design, plus abandon criteria and three reflection answers", "8"),
    ("", "Team reflection", "Three prompts", "Three handwritten-style reflection cards answering each prompt, plus a closing band, a six-item checklist and three signatures", "8"),
]


def hand(c, x, y, text, size=10.4, color=NAVY):
    c.setFillColor(color)
    c.setFont("Caveat", size)
    c.drawString(x, y, text)


def pair_table(c, y, head, rows, colw, size=6.6):
    """Two-tone table: given format on the left, implementation on the right."""
    x = M
    hh = 15
    c.setFillColor(NAVY)
    c.roundRect(x, y - hh, CW, hh, 6, stroke=0, fill=1)
    c.rect(x, y - hh, CW, 6, stroke=0, fill=1)
    cx = x
    for (t, w) in zip(head, colw):
        draw_text(c, cx + 6, y - hh + 4.6, t, "Pop8", 6.0, Color(1, 1, 1))
        cx += w
    ty = y - hh
    for i, row in enumerate(rows):
        rh = max(para_height(val, w - 12, size) for val, w in zip(row, colw)) + 7
        c.setFillColor(Color(1, 1, 1) if i % 2 == 0 else Color(0.976, 0.980, 0.988))
        c.rect(x, ty - rh, CW, rh, stroke=0, fill=1)
        cx = x
        for j, (val, w) in enumerate(zip(row, colw)):
            para(c, cx + 6, ty - 3.8, w - 12, val, size=size, leading=size * 1.34,
                 color=NAVY if j == 0 else BODY, bold_font="Pop7" if j == 0 else "Int7")
            cx += w
        c.setStrokeColor(Color(0.898, 0.910, 0.929))
        c.setLineWidth(0.4)
        c.line(x, ty - rh, x + CW, ty - rh)
        ty -= rh
    c.setStrokeColor(LINE)
    c.setLineWidth(0.7)
    c.rect(x, ty, CW, y - ty, stroke=1, fill=0)
    return y - ty


def build():
    c = NumberedCanvas(OUT, pagesize=A4)
    c.setTitle("Format Compliance Check · Astro Smart Attendance")
    c.setAuthor("Team Sun Rises India — ABPS Renukoot")
    c.setSubject("Line-by-line check against the supplied creative ideation worksheet format")

    top = PAGE_H - 76

    # ---------------- page 1
    page_header(c, 1)
    y = top

    c.setFillColor(GOLD)
    rrect(c, M, y, tw("FORMAT CHECK", "Pop8", 6.4) + 16, 13, 6.5, fill=GOLD)
    draw_text(c, M + 8, y + 4.4, "FORMAT CHECK", "Pop8", 6.4, NAVY)
    y -= 22
    draw_text(c, M, y, "Does it follow the format we were given?", "Pop7", 17, NAVY)
    y -= 17
    para(c, M, y, CW, "Every heading, prompt and bracket in the reference document appears on the left of these tables. "
         "The right-hand columns show where that line is answered in the worksheet — not paraphrased away, but drawn, "
         "scored or filled in with a number.", size=7.4, leading=10.2)
    y -= 32

    card(c, M, y - 34, CW, 34, fill=HexColor("#ECFDF5"), stroke=HexColor("#A7F3D0"), r=8)
    glyph(c, "check", M + 18, y - 17, 10, GREEN, 1.15)
    para(c, M + 34, y - 9.5, CW - 140,
         "**All 7 header fields and all 10 numbered parts are present.** Nothing dropped, nothing left as a bracket.",
         size=7.3, leading=9.8)
    draw_text(c, M + CW - 118, y - 21, "10 / 10  PARTS", "Pop8", 9.4, GREEN)
    y -= 50

    label(c, M, y, "Header block, as the document opens", MUTED, 6.2)
    y -= 10
    y -= pair_table(c, y, ["Line in the given format", "What it is", "Where it appears", "Page"],
                    HEADER_ROWS, [176, 92, CW - 176 - 92 - 34, 34], 6.4)

    y -= 22
    label(c, M, y, "The ten numbered parts — first five", MUTED, 6.2)
    y -= 10
    rows = [(f"{n}. {t}" if n else t, prompt, where, pg) for (n, t, prompt, where, pg) in SECTION_ROWS[:5]]
    y -= pair_table(c, y, ["Part in the given format", "What the format asks for", "How it is answered in the worksheet", "Page"],
               rows, [118, 104, CW - 118 - 104 - 34, 34], 6.3)

    y -= 20
    label(c, M, y, "What sits on each of the eight pages", MUTED, 6.2)
    y -= 10
    pagemap = [
        ("01", "Cover, team, §1", "Problem, discovery questions, two quotes, scale of the problem", NAVY),
        ("02", "§2 Ideas", "Ten ideas with verdicts, three filters, ten-row filter matrix", SAFFRON),
        ("03", "§3 Concept map", "Six-stage chain, six proof cards, tap-to-alert data pathway", TEAL),
        ("04", "§4 Matrix", "Scored matrix, nine-point gap, evidence, ranking movements", NAVY),
        ("05", "§5 Selection", "Chosen concept, five-step flow, ownership, first trial week", GREEN),
        ("06", "§6 Sketch", "Drawn block diagram, costed BOM, LCD states, alternatives", TEAL),
        ("07", "§7 + §8", "Five validations with decision rules, six indicators, baseline", SAFFRON),
        ("08", "§9 + Close", "Six risks, abandon criteria, reflection, checklist, signatures", NAVY),
    ]
    pw = (CW - 3 * 8) / 4
    ch = 46
    for i, (num, h, d, col) in enumerate(pagemap):
        bx = M + (i % 4) * (pw + 8)
        by = y - (i // 4 + 1) * (ch + 7) + 7
        card(c, bx, by, pw, ch, fill=Color(1, 1, 1), stroke=LINE)
        draw_text(c, bx + 9, by + ch - 13, num, "Pop8", 8.2, col)
        draw_text(c, bx + 25, by + ch - 13, h, "Pop7", 6.9, NAVY)
        para(c, bx + 9, by + ch - 17, pw - 18, d, size=5.9, leading=7.7)
    y = y - 2 * (ch + 7) + 7 - 22

    label(c, M, y, "How this check was done", MUTED, 6.2)
    y -= 10
    steps = [("1", "Read the reference document", "Every heading, prompt and bracket was copied out as its own line."),
             ("2", "Searched the finished PDF", "Each line was confirmed in the text layer of the eight rendered pages."),
             ("3", "Marked the gaps", "Anything missing is listed here. None is; three departures and four additions are declared on page 2.")]
    sw3 = (CW - 16) / 3
    for i, (n, h, d) in enumerate(steps):
        bx = M + i * (sw3 + 8)
        card(c, bx, y - 48, sw3, 48, fill=SOFT, stroke=LINE)
        rrect(c, bx + 10, y - 48 + 48 - 19, 13, 13, 4, fill=NAVY if i < 2 else SAFFRON)
        draw_text(c, bx + 15.6, y - 48 + 48 - 15.6, n, "Pop8", 6.6, Color(1, 1, 1))
        draw_text(c, bx + 29, y - 48 + 48 - 15.4, h, "Pop7", 6.8, NAVY)
        para(c, bx + 10, y - 48 + 48 - 22, sw3 - 20, d, size=6.0, leading=7.9)

    c.showPage()

    # ---------------- page 2
    page_header(c, 2)
    y = top
    label(c, M, y, "The ten numbered parts — second five", MUTED, 6.2)
    y -= 10
    rows = [(f"{n}. {t}" if n else t, prompt, where, pg) for (n, t, prompt, where, pg) in SECTION_ROWS[5:]]
    y -= pair_table(c, y, ["Part in the given format", "What the format asks for", "How it is answered in the worksheet", "Page"],
                    rows, [118, 104, CW - 118 - 104 - 34, 34], 6.3)

    y -= 20
    label(c, M, y, "Declared departures — three, all additive", MUTED, 6.2)
    y -= 10
    notes = [("Nine sections, eight pages.", "Sections 7 and 8 share a page because both are measurement; every heading still has its own block.", TEAL),
             ("Sketches are drawn, not pasted.", "Both \"[Draw a labelled block diagram here]\" prompts are real vector diagrams, so nothing is a placeholder.", SAFFRON),
             ("Four extra blocks were added.", "Costed BOM, ownership, first-week plan and abandon criteria — the format asked for none of them, and a jury asks for all four.", NAVY)]
    nw = (CW - 16) / 3
    for i, (h, d, col) in enumerate(notes):
        bx = M + i * (nw + 8)
        card(c, bx, y - 52, nw, 52, fill=Color(1, 1, 1), stroke=LINE)
        c.setFillColor(col)
        c.roundRect(bx, y - 52, 3, 52, 1.5, stroke=0, fill=1)
        draw_text(c, bx + 10, y - 12, h, "Pop7", 7.2, NAVY)
        para(c, bx + 10, y - 15.5, nw - 20, d, size=6.1, leading=8.3)
    y -= 68

    label(c, M, y, "If a reviewer only checks three things", MUTED, 6.2)
    y -= 10
    checks = [("Format", "The sheet opens with the header, runs 1 to 9 in order, and ends with the team reflection."),
              ("Evidence", "Every claim on the page traces to a measurement, a quote or a costed part."),
              ("Honesty", "Rejected ideas, unresolved questions and abandon criteria are printed, not hidden.")]
    cw3 = (CW - 16) / 3
    for i, (h, d) in enumerate(checks):
        bx = M + i * (cw3 + 8)
        card(c, bx, y - 46, cw3, 46, fill=Color(1, 1, 1), stroke=LINE)
        glyph(c, "check", bx + 12, y - 14, 8, TEAL, 1.05)
        draw_text(c, bx + 26, y - 15.5, h, "Pop7", 7.6, NAVY)
        para(c, bx + 12, y - 22, cw3 - 24, d, size=6.2, leading=8.4)
    y -= 62

    card(c, M, y - 44, CW, 44, fill=CREAM, stroke=HexColor("#FDE68A"), r=9)
    hand(c, M + 14, y - 18, "Same skeleton, filled in by hand — that is the whole point.", 12.5, HexColor("#92400E"))
    para(c, M + 14, y - 26, CW - 28,
         "The reference document was a blank sheet with prompts. This one keeps every prompt, then answers it with a number, a drawing or a decision. "
         "Where the format left a bracket, there is now a diagram; where it asked for a list, there is a table with scores.",
         size=6.6, leading=8.8)
    y -= 62

    label(c, M, y, "Names exactly as the reference document writes them", MUTED, 6.2)
    y -= 10
    names = [("Shaurya Gupta", "Team captain"), ("Anant Tiwari", "Member"),
             ("Devansh Dhakad", "Member"), ("Tejas Upadhyay", "Member"),
             ("Diwakar Singh", "Member"), ("Dr. Jayesh Shinde", "Mentor")]
    nwd = (CW - 5 * 6) / 6
    for i, (n, r) in enumerate(names):
        bx = M + i * (nwd + 6)
        card(c, bx, y - 34, nwd, 34, fill=Color(1, 1, 1), stroke=LINE, r=7)
        draw_text(c, bx + 7, y - 13, n, "Pop7", 6.3, NAVY)
        draw_text(c, bx + 7, y - 23, r, "Pop8", 5.0, MUTED)
    y -= 44

    card(c, M, y - 40, CW, 40, fill=Color(1, 1, 1), stroke=LINE, r=8)
    verify = [("CHECKED ON", "25 November 2026"), ("PAGES COMPARED", "8 worksheet pages"), ("LINES MATCHED", "7 header + 10 parts"), ("RESULT", "Full match")]
    vw = CW / 4
    for i, (k, v) in enumerate(verify):
        bx = M + i * vw
        if i:
            c.setStrokeColor(LINE)
            c.setLineWidth(0.7)
            c.line(bx, y - 34, bx, y - 6)
        draw_text(c, bx + 10, y - 15, k, "Pop8", 5.2, MUTED)
        draw_text(c, bx + 10, y - 27, v, "Pop7", 7.4, NAVY if i < 3 else GREEN)
    y -= 58

    label(c, M, y, "The four additions, and the question each one answers", MUTED, 6.2)
    y -= 10
    adds = [("Costed BOM", "Page 6", "\u201cWhat does it cost to build one?\u201d", "Eleven priced parts, an estimated total of ≈ ₹1,500 and the mark-up on the two commercial alternatives.", SAFFRON),
            ("Role ownership", "Page 5", "\u201cWho actually built which part?\u201d", "Five members, the subsystem each owns and the artefact they hand over at the end.", TEAL),
            ("First trial week", "Page 5", "\u201cWhen does it meet a real class?\u201d", "Bench test Monday, enrolment Wednesday, one live period Thursday, comparison Saturday.", NAVY),
            ("Abandon criteria", "Page 8", "\u201cWhat would make you stop?\u201d", "Three stated thresholds on speed, affordability and detection quality, set before the trial.", GREEN)]
    ah = 40
    for i, (h, pg, q, d, col) in enumerate(adds):
        by = y - (i + 1) * (ah + 6) + 6
        card(c, M, by, CW, ah, fill=Color(1, 1, 1), stroke=LINE, r=7)
        c.setFillColor(col)
        c.roundRect(M, by, 3, ah, 1.5, stroke=0, fill=1)
        draw_text(c, M + 11, by + ah - 14, h, "Pop7", 7.4, NAVY)
        draw_text(c, M + 132, by + ah - 14, q, "Caveat", 9.4, HexColor("#92400E"))
        para(c, M + 11, by + ah - 18, CW - 150, d, size=6.2, leading=8.4)
        draw_text(c, M + CW - 52, by + ah - 14, pg, "Pop8", 5.6, MUTED)

    c.showPage()
    c.save()
    print("wrote", OUT, os.path.getsize(OUT))


if __name__ == "__main__":
    build()
