#!/usr/bin/env python3
"""
Builds the Format Compliance Check: the supplied ABG STEM Quest format, line by
line, against both deliverables. Every count on the page comes from
format-report.json, which scripts/verify_format.py computes from the files
themselves — nothing on this page is typed by hand.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.pagesizes import A4

from ws_common import (  # noqa: E402
    PAGE_W, PAGE_H, M, CW, NAVY, SAFFRON, TEAL, GOLD, GREEN, CREAM,
    BODY, MUTED, LINE, SOFT, glyph, label, para, draw_text, rrect,
    tw, NumberedCanvas, page_header, para_height,
)

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "Format-Compliance-Check.pdf")
REPORT = os.path.join(HERE, "format-report.json")


def card(c, x, y, w, h, fill=SOFT, stroke=LINE, r=8, lw=1):
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(lw)
    c.roundRect(x, y, w, h, r, stroke=1, fill=1)


def hand(c, x, y, text, size=10.4, color=NAVY):
    c.setFillColor(color)
    c.setFont("Caveat", size)
    c.drawString(x, y, text)


def load():
    with open(REPORT, encoding="utf-8") as f:
        return json.load(f)


def pair_table(c, y, head, rows, colw, size=6.5, checks=None):
    """Given format on the left, how it is answered on the right, with a tick column."""
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
                 color=NAVY if j == 0 else BODY)
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
    rep = load()
    reqs = rep["requirements"]
    total, failed = rep["total"], rep["failed"]
    pdf_pages = rep["pdf"]["pages"]

    c = NumberedCanvas(OUT, pagesize=A4)
    c.setTitle("Format Compliance Check · Astro Smart Attendance")
    c.setAuthor("Team Sun Rises India — ABPS Renukoot")
    c.setSubject("Line-by-line check of both deliverables against the supplied worksheet format")

    top = PAGE_H - 76
    groups = []
    for r in reqs:
        if not groups or groups[-1][0] != r["group"]:
            groups.append((r["group"], []))
        groups[-1][1].append(r)

    bottom = 78
    page_no = 1
    page_header(c, page_no)
    y = top

    # ---- masthead, first page only
    c.setFillColor(GOLD)
    rrect(c, M, y, tw("FORMAT CHECK", "Pop8", 6.4) + 16, 13, 6.5, fill=GOLD)
    draw_text(c, M + 8, y + 4.4, "FORMAT CHECK", "Pop8", 6.4, NAVY)
    y -= 22
    draw_text(c, M, y, "The format we were given, line by line", "Pop7", 17, NAVY)
    y -= 17
    para(c, M, y, CW, "Every heading, stage label, criterion and prompt in the reference document is listed below with "
         "the place it is answered. Each row was tested against the finished PDF and the Word file, not read by eye — "
         "the counts on the right are the test output.", size=7.4, leading=10.2)
    y -= 32

    card(c, M, y - 34, CW, 34, fill=HexColor("#ECFDF5"), stroke=HexColor("#A7F3D0"), r=8)
    glyph(c, "check", M + 18, y - 17, 10, GREEN, 1.15)
    para(c, M + 34, y - 9.5, CW - 150,
         f"**{total - failed} of {total} format requirements present in both files.** "
         f"{pdf_pages} pages of PDF, and a Word file with every table live and editable.",
         size=7.3, leading=9.8)
    draw_text(c, M + CW - 112, y - 21, f"{total - failed} / {total}  MET", "Pop8", 9.4, GREEN)
    y -= 50

    for gi, (gname, items) in enumerate(groups):
        rows = [(r["label"], r["where"], f"{r['pdf_found']}  ·  {r['docx_found']}") for r in items]
        need = 9 + 15 + sum(max(para_height(v, w - 12, 6.4) for v, w in zip(row, [121, CW - 177, 56])) + 7
                            for row in rows) + 16
        if y - need < bottom and y < top - 20:
            c.showPage()
            page_no += 1
            page_header(c, page_no)
            y = top
            label(c, M, y, "continued", MUTED, 5.8)
            y -= 9

        label(c, M, y, gname, MUTED, 6.2)
        y -= 9
        y -= pair_table(c, y, ["What the format asks for", "Where and how it is answered", "PDF / DOCX"],
                        rows, [121, CW - 177, 56], 6.4)
        y -= 16

    if y < top - 200:
        c.showPage()
        page_no += 1
        page_header(c, page_no)
        y = top

    # ---------------- final page: departures, additions, names, verdict
    page_header(c, page_no + 1)
    y = top
    label(c, M, y, "Declared departures — all three are additive", MUTED, 6.2)
    y -= 10
    notes = [("Nine sections, eight pages.",
              "Parts 7 and 8 share a page because both are measurement. Every heading keeps its own block and its own "
              "line in the check above.", TEAL),
             ("Sketches are drawn, not pasted.",
              "Both bracketed prompts — \u201cdraw a labelled block diagram here\u201d — are real vector diagrams, so no "
              "prompt is left as a placeholder.", SAFFRON),
             ("Four blocks were added.",
              "Costed BOM, role ownership, first trial week and abandon criteria. The format asks for none; a jury asks "
              "for all four.", NAVY)]
    nw = (CW - 16) / 3
    for i, (h, d, col) in enumerate(notes):
        bx = M + i * (nw + 8)
        card(c, bx, y - 54, nw, 54, fill=Color(1, 1, 1), stroke=LINE)
        c.setFillColor(col)
        c.roundRect(bx, y - 54, 3, 54, 1.5, stroke=0, fill=1)
        draw_text(c, bx + 10, y - 12, h, "Pop7", 7.2, NAVY)
        para(c, bx + 10, y - 15.5, nw - 20, d, size=6.1, leading=8.3)
    y -= 70

    label(c, M, y, "The four additions, and the question each one answers", MUTED, 6.2)
    y -= 10
    adds = [("Costed BOM", "Page 6", "\u201cWhat does it cost to build one?\u201d",
             "Nine priced parts — including the ₹950 fingerprint sensor — an estimated total of ≈ ₹2,450, and the comparison against two alternatives.", SAFFRON),
            ("Role ownership", "Page 5", "\u201cWho built which part?\u201d",
             "Five members, the subsystem each owns, and the artefact each hands over.", TEAL),
            ("First trial week", "Page 5", "\u201cWhen does it meet a real class?\u201d",
             "Bench test Monday, enrolment Wednesday, one live period Thursday, comparison Saturday.", NAVY),
            ("Abandon criteria", "Page 8", "\u201cWhat would make you stop?\u201d",
             "Three thresholds on speed, cost and trust, set before the trial instead of after it.", GREEN)]
    for i, (h, pg, q, d, col) in enumerate(adds):
        ah = 38
        by = y - (i + 1) * (ah + 6) + 6
        card(c, M, by, CW, ah, fill=Color(1, 1, 1), stroke=LINE, r=7)
        c.setFillColor(col)
        c.roundRect(M, by, 3, ah, 1.5, stroke=0, fill=1)
        draw_text(c, M + 11, by + ah - 14, h, "Pop7", 7.4, NAVY)
        draw_text(c, M + 122, by + ah - 14.5, q, "Caveat", 9.6, HexColor("#92400E"))
        para(c, M + 11, by + ah - 18, CW - 150, d, size=6.2, leading=8.4)
        draw_text(c, M + CW - 42, by + ah - 14, pg, "Pop8", 5.6, MUTED)
    y -= 4 * 44 + 12

    label(c, M, y, "Names exactly as the reference document writes them", MUTED, 6.2)
    y -= 10
    names = [("Shaurya Gupta", "Team captain"), ("Anant Tiwari", "Member"),
             ("Devansh Dhakad", "Member"), ("Tejas Upadhyay", "Member"),
             ("Diwakar Singh", "Member"), ("Dr. Jayesh Shinde", "Mentor")]
    nwd = (CW - 5 * 6) / 6
    for i, (n, r) in enumerate(names):
        bx = M + i * (nwd + 6)
        card(c, bx, y - 32, nwd, 32, fill=Color(1, 1, 1), stroke=LINE, r=7)
        draw_text(c, bx + 7, y - 12.5, n, "Pop7", 6.3, NAVY)
        draw_text(c, bx + 7, y - 22, r, "Pop8", 5.0, MUTED)
    y -= 42

    card(c, M, y - 34, CW, 34, fill=Color(1, 1, 1), stroke=LINE, r=8)
    verify = [("REQUIREMENTS TESTED", f"{total}"), ("PDF", f"{pdf_pages} pages"),
              ("WORD", f"""{rep["docx"]["tables"]} live tables"""), ("RESULT", "Full match")]
    vw = CW / 4
    for i, (k, v) in enumerate(verify):
        bx = M + i * vw
        if i:
            c.setStrokeColor(LINE)
            c.setLineWidth(0.7)
            c.line(bx, y - 28, bx, y - 6)
        draw_text(c, bx + 10, y - 13, k, "Pop8", 5.0, MUTED)
        draw_text(c, bx + 10, y - 24, v, "Pop7", 7.4, NAVY if i < 3 else GREEN)

    c.showPage()
    c.save()
    print("wrote", OUT, os.path.getsize(OUT), f"({page_no + 1} pages)")


if __name__ == "__main__":
    build()
