#!/usr/bin/env python3
"""
Builds the designed, editable Word version of the Creative Ideation Worksheet.

This is not a plain dump of the content: it reproduces the PDF's design system —
navy banner, coloured section badges, card grids, a rainbow score matrix, a
six-stage chain, a costed BOM with a navy total row, cream reflection cards and
signature rules — using native Word tables, so every word stays editable.
"""
import math
import os

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "Creative-Ideation-Worksheet-Astro-Smart-Attendance.docx")

# ---------------------------------------------------------------- palette
NAVY = "0B1F4A"
NAVY_RGB = RGBColor(0x0B, 0x1F, 0x4A)
SAFFRON = "FF7A18"
SAFFRON_RGB = RGBColor(0xC2, 0x41, 0x0C)
TEAL = "0EA5A4"
TEAL_RGB = RGBColor(0x0E, 0x74, 0x74)
GOLD = "FFB703"
GREEN = "10B981"
GREEN_RGB = RGBColor(0x04, 0x78, 0x57)
WHITE = "FFFFFF"
white = RGBColor(0xFF, 0xFF, 0xFF)
BODY_HEX = "334155"
body = RGBColor(0x33, 0x41, 0x55)
MUTED_HEX = "64748B"
muted = RGBColor(0x64, 0x74, 0x8B)
LINE = "D8DEE9"
SOFT = "F5F7FB"
CREAM = "FDFCF8"
AMBER_L = "FFF7E6"
TEAL_L = "E6F7F6"
GREEN_L = "ECFDF5"
SAFFRON_L = "FFF1E6"
RED_L = "FEF2F2"
BLUE_L = "EEF3FB"

# score bubbles: 5 green, 4 blue, 3 amber, 2 red
SCORE_FILL = {5: "D1FAE5", 4: "DBEAFE", 3: "FEF3C7", 2: "FEE2E2", 1: "FEE2E2"}
SCORE_TEXT = {5: RGBColor(0x04, 0x78, 0x57), 4: RGBColor(0x1D, 0x4E, 0xD8),
              3: RGBColor(0xB4, 0x53, 0x09), 2: RGBColor(0xB9, 0x1C, 0x1C)}

FONT = "Calibri"
HAND = "Segoe Script"
CW = 17.6  # usable width in cm (A4 minus 1.7cm margins)


# ---------------------------------------------------------------- low level
def _el(tag, **attrs):
    e = OxmlElement(tag)
    for k, v in attrs.items():
        e.set(qn("w:" + k), str(v))
    return e


def shade(cell, hexcolor):
    cell._tc.get_or_add_tcPr().append(
        _el("w:shd", val="clear", color="auto", fill=hexcolor))


def cell_borders(cell, color=LINE, sz=4, edges=("top", "left", "bottom", "right")):
    tcPr = cell._tc.get_or_add_tcPr()
    borders = _el("w:tcBorders")
    for edge in edges:
        borders.append(_el("w:" + edge, val="single", sz=sz, color=color, space=0))
    tcPr.append(borders)


def no_borders(cell):
    tcPr = cell._tc.get_or_add_tcPr()
    borders = _el("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        borders.append(_el("w:" + edge, val="nil"))
    tcPr.append(borders)


def cell_margins(cell, top=60, bottom=60, left=90, right=90):
    tcPr = cell._tc.get_or_add_tcPr()
    mar = _el("w:tcMar")
    for name, val in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        mar.append(_el("w:" + name, w=val, type="dxa"))
    tcPr.append(mar)


def table_layout(table, widths):
    """Force fixed layout with explicit column widths (cm)."""
    tblPr = table._tbl.tblPr
    tblPr.append(_el("w:tblLayout", type="fixed"))
    tblPr.append(_el("w:tblW", w=int(sum(widths) * 567), type="dxa"))
    table.autofit = False
    grid = table._tbl.find(qn("w:tblGrid"))
    if grid is not None:
        for i, gc in enumerate(grid.findall(qn("w:gridCol"))):
            gc.set(qn("w:w"), str(int(widths[i] * 567)))
    for row in table.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)


def row_height(row, cm):
    trPr = row._tr.get_or_add_trPr()
    trPr.append(_el("w:trHeight", val=int(cm * 567), hRule="atLeast"))


def keep_row(row):
    row._tr.get_or_add_trPr().append(_el("w:cantSplit"))


def keep_with_next(par):
    par.paragraph_format.keep_with_next = True


def spacing(run, twips):
    """Letter-spacing, the Word equivalent of tracked uppercase labels."""
    run._element.get_or_add_rPr().append(_el("w:spacing", val=twips))


def put(cell, text, size=9, bold=False, color=body, align=None, space=0,
        before=0, font=FONT, italic=False, track=None, caps=False, line=None):
    """Write text into a cell, replacing its content."""
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    p = cell.paragraphs[0]
    p.text = ""
    pf = p.paragraph_format
    pf.space_after = Pt(space)
    pf.space_before = Pt(before)
    if line:
        pf.line_spacing = line
    if align == "c":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == "r":
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p.add_run(text.upper() if caps else text)
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    r.font.color.rgb = color
    r.font.name = font
    if track:
        spacing(r, track)
    return p


def add(cell, text, size=9, bold=False, color=body, align=None, space=2,
        before=3, italic=False, track=None, caps=False, font=FONT, line=None):
    """Append another paragraph to a cell (for card bodies)."""
    p = cell.add_paragraph()
    pf = p.paragraph_format
    pf.space_after = Pt(space)
    pf.space_before = Pt(before)
    if line:
        pf.line_spacing = line
    if align == "c":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text.upper() if caps else text)
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    r.font.color.rgb = color
    r.font.name = font
    if track:
        spacing(r, track)
    return p


def para(doc, text, size=10, bold=False, color=body, space_after=6, italic=False,
         before=0, align=None, line=None):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_after = Pt(space_after)
    pf.space_before = Pt(before)
    if line:
        pf.line_spacing = line
    if align == "c":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    r.font.color.rgb = color
    r.font.name = FONT
    return p


def gap(doc, pt=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.space_before = Pt(0)
    p.add_run("").font.size = Pt(pt)


def hairline(doc, color=LINE, size=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(8)
    pPr = p._p.get_or_add_pPr()
    bdr = _el("w:pBdr")
    bdr.append(_el("w:bottom", val="single", sz=size, color=color, space=1))
    pPr.append(bdr)


# ---------------------------------------------------------------- components
def section_head(doc, number, title, subtitle, color=SAFFRON, color_rgb=SAFFRON_RGB):
    """Coloured number tile + big title + subtitle + hairline, as on the PDF."""
    t = doc.add_table(rows=1, cols=2)
    table_layout(t, [1.35, CW - 1.35])
    no_borders(t.rows[0].cells[0])
    no_borders(t.rows[0].cells[1])
    badge = t.rows[0].cells[0]
    shade(badge, color)
    cell_margins(badge, top=70, bottom=70, left=20, right=20)
    put(badge, f"{number:02d}", size=13, bold=True, color=white, align="c")

    right = t.rows[0].cells[1]
    cell_margins(right, top=0, bottom=0, left=140, right=0)
    put(right, title, size=16, bold=True, color=NAVY_RGB, space=0)
    add(right, subtitle, size=8.3, color=muted, space=0, before=1)
    # thin rule under the whole heading
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(6)
    pPr = p._p.get_or_add_pPr()
    bdr = _el("w:pBdr")
    bdr.append(_el("w:bottom", val="single", sz=6, color=LINE, space=1))
    pPr.append(bdr)


def label(doc, text, color_rgb=SAFFRON_RGB, before=8, after=3):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    r = p.add_run(text.upper())
    r.font.size = Pt(7.5)
    r.font.bold = True
    r.font.color.rgb = color_rgb
    r.font.name = FONT
    spacing(r, 24)
    return p


def banner(doc, kicker, title, sub, body_text, fill=NAVY, kicker_color=GOLD,
           title_size=20, tag=None, tag_fill=SAFFRON):
    t = doc.add_table(rows=1, cols=1)
    table_layout(t, [CW])
    c = t.rows[0].cells[0]
    shade(c, fill)
    no_borders(c)
    cell_margins(c, top=150, bottom=150, left=170, right=170)
    put(c, kicker, size=7, bold=True, color=RGBColor(0xFF, 0xB7, 0x03), track=30, space=2)
    add(c, title, size=title_size, bold=True, color=white, space=2, before=2)
    add(c, sub, size=8.5, bold=True, color=RGBColor(0xDC, 0xE7, 0xF8), space=2, before=2)
    if body_text:
        add(c, body_text, size=8.5, color=RGBColor(0xC9, 0xD8, 0xEE), space=0, before=4, line=1.25)
    if tag:
        tp = add(c, tag, size=7, bold=True, color=white, align="r", space=0, before=4, track=20)
        # a small filled chip, the Word equivalent of the rotated badge in the PDF
        pPr = tp._p.get_or_add_pPr()
        shd = _el("w:shd", val="clear", color="auto", fill=tag_fill)
        pPr.append(shd)
    return t


def card_grid(doc, cards, cols=2, widths=None, min_h=1.5,
              fill=WHITE, border=LINE, title_color=NAVY_RGB, body_color=body):
    """cards: list of dicts {title, body, tag, accent} rendered as bordered cells."""
    rows = math.ceil(len(cards) / cols)
    widths = widths or [CW / cols] * cols
    t = doc.add_table(rows=rows, cols=cols)
    table_layout(t, widths)
    for idx, card in enumerate(cards):
        r, cc = divmod(idx, cols)
        cell = t.rows[r].cells[cc]
        shade(cell, card.get("fill", fill))
        cell_borders(cell, card.get("border", border))
        cell_margins(cell, top=100, bottom=100, left=120, right=120)
        accent = card.get("accent")
        if accent:
            cell_borders(cell, accent, sz=18, edges=("left",))
        put(cell, card["title"], size=9.5, bold=True, color=title_color, space=1)
        if card.get("body"):
            add(cell, card["body"], size=8.3, color=body_color, space=1, before=1, line=1.2)
        if card.get("tag"):
            add(cell, card["tag"], size=6.8, bold=True,
                color=card.get("tag_color", muted), space=0, before=2, track=16)
    # blank out unused cells
    for idx in range(len(cards), rows * cols):
        r, cc = divmod(idx, cols)
        no_borders(t.rows[r].cells[cc])
    for row in t.rows:
        keep_row(row)
        row_height(row, min_h)
    return t


def stat_strip(doc, stats):
    """big number + small caption tiles."""
    widths = [CW / len(stats)] * len(stats)
    t = doc.add_table(rows=1, cols=len(stats))
    table_layout(t, widths)
    for i, (value, caption, color_rgb) in enumerate(stats):
        c = t.rows[0].cells[i]
        shade(c, WHITE)
        cell_borders(c, LINE)
        cell_margins(c, top=110, bottom=110, left=100, right=100)
        put(c, value, size=15, bold=True, color=color_rgb, align="c", space=1)
        add(c, caption, size=6.5, bold=True, color=muted, align="c", space=0, before=2, track=14)
    keep_row(t.rows[0])
    return t


def data_table(doc, head, rows, widths, size=8.5, head_fill=NAVY, zebra=True,
               aligns=None, first_bold=True):
    t = doc.add_table(rows=1, cols=len(head))
    table_layout(t, widths)
    hdr = t.rows[0]
    for i, h in enumerate(head):
        c = hdr.cells[i]
        shade(c, head_fill)
        cell_borders(c, head_fill)
        cell_margins(c, top=70, bottom=70, left=100, right=100)
        put(c, h, size=size - 0.5, bold=True, color=white)
    keep_row(hdr)
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        for i, val in enumerate(row):
            c = cells[i]
            shade(c, WHITE if (ri % 2 == 0 or not zebra) else SOFT)
            cell_borders(c, LINE)
            cell_margins(c, top=60, bottom=60, left=100, right=100)
            al = None
            if aligns and aligns[i] == "r":
                al = "r"
            elif aligns and aligns[i] == "c":
                al = "c"
            put(c, val, size=size, bold=(first_bold and i == 0),
                color=NAVY_RGB if (first_bold and i == 0) else body, align=al)
        keep_row(t.rows[-1])
    return t


def score_table(doc, head, rows, widths):
    """Matrix with coloured score bubbles, like the PDF."""
    t = doc.add_table(rows=1, cols=len(head))
    table_layout(t, widths)
    for i, h in enumerate(head):
        c = t.rows[0].cells[i]
        shade(c, NAVY)
        cell_borders(c, NAVY)
        cell_margins(c, top=80, bottom=80, left=90, right=90)
        put(c, h, size=7.2, bold=True, color=white,
            align="c" if i > 0 else None)
    keep_row(t.rows[0])
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        for i, val in enumerate(row):
            c = cells[i]
            cell_borders(c, LINE)
            cell_margins(c, top=60, bottom=60, left=90, right=90)
            if i in (1, 2, 3, 4, 5) and str(val).isdigit():
                n = int(val)
                shade(c, SCORE_FILL.get(n, WHITE))
                put(c, val, size=10, bold=True, color=SCORE_TEXT.get(n, body), align="c")
            elif i == 0:
                shade(c, GREEN_L if ri == 0 else (WHITE if ri % 2 == 0 else SOFT))
                put(c, val, size=8.6, bold=True, color=NAVY_RGB)
            else:
                shade(c, GREEN_L if ri == 0 else (WHITE if ri % 2 == 0 else SOFT))
                put(c, val, size=9, bold=True, color=NAVY_RGB, align="c")
        keep_row(t.rows[-1])
    return t


def chain(doc, stages, colors):
    """Six stage cards with arrows between them, as a single row."""
    n = len(stages)
    arrow_w = 0.55
    card_w = (CW - arrow_w * (n - 1)) / n
    widths = []
    for i in range(n):
        widths.append(card_w)
        if i < n - 1:
            widths.append(arrow_w)
    t = doc.add_table(rows=1, cols=len(widths))
    table_layout(t, widths)
    for i, (num, title, text) in enumerate(stages):
        c = t.rows[0].cells[i * 2]
        col = colors[i % len(colors)]
        shade(c, WHITE)
        cell_borders(c, col, sz=8)
        cell_margins(c, top=90, bottom=90, left=80, right=80)
        put(c, num, size=6.5, bold=True, color=muted, track=20, space=1)
        add(c, title, size=7, bold=True, color=NAVY_RGB, space=1, before=3, track=10)
        add(c, text, size=6.6, color=muted, space=0, before=2, line=1.15)
        if i < n - 1:
            a = t.rows[0].cells[i * 2 + 1]
            no_borders(a)
            put(a, "→", size=12, bold=True, color=SAFFRON_RGB, align="c")
    keep_row(t.rows[0])
    return t


def callout(doc, kicker, text, fill=CREAM, border=GOLD, kicker_rgb=SAFFRON_RGB,
            text_rgb=NAVY_RGB, size=8.8, hand=False):
    t = doc.add_table(rows=1, cols=1)
    table_layout(t, [CW])
    c = t.rows[0].cells[0]
    shade(c, fill)
    cell_borders(c, border)
    cell_margins(c, top=110, bottom=110, left=140, right=140)
    put(c, kicker, size=6.8, bold=True, color=kicker_rgb, track=22, space=2)
    add(c, text, size=size, color=text_rgb, space=0, before=3,
        italic=hand, font=HAND if hand else FONT,
        line=1.3 if not hand else None)
    keep_row(t.rows[0])
    return t


def lcd(doc, rows):
    """Three dark LCD mockups."""
    widths = [CW / 3] * 3
    t = doc.add_table(rows=1, cols=3)
    table_layout(t, widths)
    for i, (line1, line2, note, rgb) in enumerate(rows):
        c = t.rows[0].cells[i]
        shade(c, WHITE)
        cell_borders(c, LINE)
        cell_margins(c, top=90, bottom=90, left=100, right=100)
        put(c, line1, size=8, bold=True, color=rgb, font="Consolas", space=0)
        add(c, line2, size=7.5, color=RGBColor(0x93, 0xC5, 0xFD), font="Consolas",
            space=3, before=1)
        add(c, note, size=6.8, color=muted, space=0, before=3)
    keep_row(t.rows[0])
    return t


def signature_row(doc, items):
    widths = [CW / 3] * 3
    t = doc.add_table(rows=2, cols=3)
    table_layout(t, widths)
    for i, (name, role) in enumerate(items):
        c = t.rows[0].cells[i]
        no_borders(c)
        cell_margins(c, top=200, bottom=20, left=20, right=140)
        put(c, name, size=14, color=NAVY_RGB, font=HAND)
        cell_borders(c, NAVY, sz=8, edges=("bottom",))
        d = t.rows[1].cells[i]
        no_borders(d)
        cell_margins(d, top=30, bottom=20, left=20, right=140)
        put(d, role, size=6.5, bold=True, color=muted, track=18)
    return t


def field_footer(section):
    p = section.footer.paragraphs[0]
    p.text = ""
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for txt, fld in (("Page ", None), (None, "PAGE"), (" of ", None), (None, "NUMPAGES")):
        if fld:
            r = p.add_run()
            r.font.size = Pt(8)
            r.font.color.rgb = muted
            fldEl = _el("w:fldSimple", instr=fld)
            r._element.addnext(fldEl)
        else:
            r = p.add_run(txt)
            r.font.size = Pt(8)
            r.font.color.rgb = muted


# ---------------------------------------------------------------- document
def build():
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name = FONT
    st.font.size = Pt(9.5)
    st.paragraph_format.space_after = Pt(4)

    s = doc.sections[0]
    s.page_width, s.page_height = Cm(21.0), Cm(29.7)
    s.top_margin = Cm(1.7)
    s.bottom_margin = Cm(1.6)
    s.left_margin = Cm(1.7)
    s.right_margin = Cm(1.7)

    # running header: navy bar with programme + part
    hp = s.header.paragraphs[0]
    hp.text = ""
    hp.paragraph_format.space_after = Pt(2)
    r = hp.add_run("ABG STEM QUEST 2026–27")
    r.font.size = Pt(8.5)
    r.font.bold = True
    r.font.color.rgb = NAVY_RGB
    r.font.name = FONT
    spacing(r, 20)
    r2 = hp.add_run("     ·     PART 1 — CREATIVE IDEATION WORKSHEET")
    r2.font.size = Pt(8.5)
    r2.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)
    r2.font.name = FONT
    spacing(r2, 12)
    field_footer(s)

    # ================= cover
    banner(doc, "SUN RISES INDIA  ·  GRADE 9  ·  ABPS RENUKOOT",
           "ASTRO SMART ATTENDANCE",
           "AI + IoT + Cloud  ·  smart school attendance system",
           "A compact ESP32 RFID + fingerprint terminal with Astro AI 2.0 self-healing, a Firebase "
           "dashboard and automatic parent alerts — two factors against proxy, offline-first, built "
           "from low-cost local parts.",
           title_size=26,
           tag="CHOSEN CONCEPT")

    gap(doc, 4)
    t = doc.add_table(rows=1, cols=1)
    table_layout(t, [CW])
    c = t.rows[0].cells[0]
    shade(c, CREAM)
    cell_borders(c, GOLD)
    cell_margins(c, top=110, bottom=110, left=140, right=140)
    put(c, "One tap. Attendance done. Parents informed.", size=12, color=NAVY_RGB, font=HAND, space=1)
    add(c, "astro-smart-attendence.web.app", size=8, color=muted, space=0, before=1, track=10)

    gap(doc, 6)
    stat_strip(doc, [("≈ ₹2,450", "EST. COST PER UNIT", SAFFRON_RGB),
                     ("≈ 3 sec", "CARD + FINGERPRINT", TEAL_RGB),
                     ("OFFLINE", "SYNCS WHEN BACK", NAVY_RGB),
                     ("140 / 140", "FEATURE TESTS PASSING", GREEN_RGB)])

    gap(doc, 8)
    label(doc, "Team and school", NAVY_RGB)
    data_table(doc, ["Field", "Detail"],
               [["School", "ABPS Renukoot, Sonbhadra (U.P.)"],
                ["Team", "Sun Rises India"],
                ["Grade", "9th"],
                ["Theme", "SDG 9 — Industry, Innovation and Infrastructure"],
                ["Team captain", "Shaurya Gupta"],
                ["Members", "Shaurya Gupta, Anant Tiwari, Devansh Dhakad, Tejas Upadhyay, Diwakar Singh"],
                ["Mentor", "Dr. Jayesh Shinde"]],
               [3.6, CW - 3.6], size=9)

    gap(doc, 10)
    label(doc, "The build, in five blocks", NAVY_RGB)
    chain(doc, [("01", "STUDENT", "ID card + enrolled finger"),
                ("02", "RC522 + R307", "card, then finger"),
                ("03", "ESP32", "both must agree"),
                ("04", "LCD1602", "“Present” + beep"),
                ("05", "FIREBASE", "dashboard + parent email")],
          [NAVY, SAFFRON, TEAL, NAVY, TEAL])

    gap(doc, 8)
    label(doc, "Why this proposal exists", NAVY_RGB)
    card_grid(doc, [
        {"title": "The problem", "accent": SAFFRON,
         "body": "10–15 minutes lost every period to a paper register, and a parent learns about an absence only "
                 "when the day is over."},
        {"title": "The change", "accent": TEAL,
         "body": "A card and a finger, verified at the door in about three seconds, written to a buffer first and "
                 "the cloud second."},
        {"title": "The proof", "accent": GREEN,
         "body": "30 students in under 90 seconds, duplicate and proxy attempts refused, parents alerted within "
                 "five minutes."},
    ], cols=3, widths=[CW / 3] * 3, min_h=2.2)

    gap(doc, 6)
    callout(doc, "How to read this worksheet",
            "Nine numbered parts, in the order the format asks for: the problem we chose, the ideas we generated, "
            "the map, the scored matrix, the concept we selected, the system sketch, what we must validate, how we "
            "will measure success, and the risks we have already designed against. Every number is either measured "
            "in our lab or marked as a hypothesis.",
            fill=SOFT, border=LINE, kicker_rgb=NAVY_RGB, text_rgb=body, size=8.6)

    doc.add_page_break()

    # ================= 1
    section_head(doc, 1, "Problem focus", "Who feels it, when it happens, and what proof of improvement looks like")
    para(doc, "Manual attendance can be time-consuming and vulnerable to recording errors or proxy attendance. "
              "The team proposes an AI-supported system to record and manage attendance.", size=9.5)
    para(doc, "Indian schools lose 10–15 minutes per class to manual attendance. Across 15+ lakh schools, paper "
              "registers are slow, easy to lose and open to proxy attendance — and the record never reaches the "
              "parent the same day. Our answer: an RFID + fingerprint terminal that verifies a student in about "
              "three seconds, keeps recording without internet, and alerts the parent automatically.", size=9.5)

    label(doc, "Discovery questions")
    data_table(doc, ["Question", "Our answer"],
               [["Who feels it?", "Teachers, students, parents, the school office"],
                ["When?", "Every period, worst at the first bell"],
                ["What happens now?", "Paper register, verbal roll-call"],
                ["What would prove it worked?", "Minutes saved, zero proxy, fast alerts"]],
               [6.0, CW - 6.0], size=9)

    gap(doc, 6)
    label(doc, "Why those four questions, and not others", TEAL_RGB)
    card_grid(doc, [
        {"title": "Who", "accent": TEAL,
         "body": "Four groups feel it differently: the teacher loses time, the student loses trust, the parent "
                 "loses information, the office loses the record."},
        {"title": "When", "accent": TEAL,
         "body": "Worst at the first bell, when 30 students arrive at once; better later, which is why the trial "
                 "runs in period one."},
        {"title": "What now", "accent": TEAL,
         "body": "A paper register and a verbal roll-call — both slow, neither timestamped, both easy to alter."},
        {"title": "What would prove it", "accent": TEAL,
         "body": "Minutes saved per class, zero duplicates and proxies, and a parent message inside five minutes."},
    ], cols=4, widths=[CW / 4] * 4, min_h=2.0)

    label(doc, "What we saw with our own eyes")
    callout(doc, "Assembly, first bell",
            "Assembly queues for the register · two names ticked twice in the same period · late arrivals argued "
            "about at the office · parents learning of absence after school.",
            fill=SAFFRON_L, border="FCD9BC", size=8.8)

    label(doc, "Success looks like", TEAL_RGB)
    callout(doc, "Target for the trial",
            "30 students verified in under 90 seconds, no duplicate entries, and every parent alerted within "
            "5 minutes of the period ending.",
            fill=TEAL_L, border="A7E3E1", kicker_rgb=TEAL_RGB, size=8.8)

    label(doc, "What users told us — anonymised notes from discovery dialogues")
    card_grid(doc, [
        {"title": "“Fifteen minutes gone every period, just calling out names. I could teach a whole concept in that time.”",
         "body": "Class teacher · ABPS Renukoot", "fill": CREAM, "border": "F3E0A8"},
        {"title": "“We find out our child was absent only when the day is over. By then the whole day is lost.”",
         "body": "Parent · Renukoot", "fill": CREAM, "border": "F3E0A8"},
    ], cols=2, widths=[CW / 2, CW / 2])

    gap(doc, 4)
    stat_strip(doc, [("10–15 min", "LOST EVERY PERIOD, EVERY CLASS", SAFFRON_RGB),
                     ("15+ lakh", "SCHOOLS ON PAPER REGISTERS", TEAL_RGB),
                     ("≈90%", "CHEAPER THAN COMMERCIAL SYSTEMS", NAVY_RGB)])

    gap(doc, 6)
    callout(doc, "In one line",
            "a low-cost terminal that verifies a student by card and finger, marks a 30-student class in under "
            "two minutes, keeps recording when the internet drops, and tells parents the same period.",
            fill=NAVY, border=NAVY, kicker_rgb=RGBColor(0xFF, 0xB7, 0x03),
            text_rgb=RGBColor(0xDC, 0xE7, 0xF8))

    doc.add_page_break()

    # ================= 2
    section_head(doc, 2, "Brainstormed possibilities",
                 "Ten ideas, generated without judgement and then filtered on purpose", SAFFRON, SAFFRON_RGB)
    callout(doc, "How the board was run",
            "Quantity first, judgement second. Every idea reached the board before anyone could criticise it — "
            "including the ones we later dropped.", fill=SOFT, border=LINE,
            kicker_rgb=SAFFRON_RGB, text_rgb=body)

    gap(doc, 4)
    ideas = [
        ("RFID card tap-in", "A school-issued card tapped at the door.", "SELECTED", GREEN_RGB),
        ("QR code attendance, rotating", "A code that changes each minute; students scan it.", "TRIED & PARKED", SAFFRON_RGB),
        ("Teacher-confirmed register", "Teacher clears exceptions, signs off.", "INCLUDED", GREEN_RGB),
        ("NFC check-in, time window", "Phone tapped inside the period window.", "PARKED", SAFFRON_RGB),
        ("Face recognition", "A camera identifies the student.", "REJECTED", RGBColor(0xB9, 0x1C, 0x1C)),
        ("Bluetooth proximity", "A beacon notices the student nearby.", "REJECTED", RGBColor(0xB9, 0x1C, 0x1C)),
        ("Offline attendance, sync later", "Stored on the device, uploaded later.", "CORE", GREEN_RGB),
        ("Duplicate & late flags", "Repeat taps, late entries, wrong periods.", "INCLUDED", GREEN_RGB),
        ("Parent / student attendance summary", "Period and day summaries by email.", "INCLUDED", GREEN_RGB),
        ("Audit log for corrections", "Every edit stored with who and why.", "INCLUDED", GREEN_RGB),
    ]
    card_grid(doc, [{"title": h, "body": d, "tag": t, "tag_color": col} for h, d, t, col in ideas],
              cols=2, widths=[CW / 2, CW / 2], min_h=1.5)

    label(doc, "The three filters every idea had to pass")
    data_table(doc, ["Filter", "The question we asked"],
               [["Can five students build it?", "Do we have the skills and the lab time, this term?"],
                ["Can a school afford it?", "Roughly ₹2,450 per classroom, or it stays a slide?"],
                ["Does it respect the student?", "Does it collect less data than the register it replaces?"]],
               [6.2, CW - 6.2], size=9)

    label(doc, "Every idea against the three filters")
    data_table(doc, ["Idea", "Five students?", "Affordable?", "Respectful?"],
               [["QR rotating code", "yes", "yes", "weak"],
                ["RFID card tap-in", "yes", "yes", "strong"],
                ["Teacher-confirmed register", "yes", "yes", "strong"],
                ["NFC time window", "yes", "yes", "weak"],
                ["Face recognition", "no", "no", "no"],
                ["Bluetooth proximity", "yes", "partly", "weak"],
                ["Offline + sync later", "partly", "yes", "strong"],
                ["Duplicate & late flags", "yes", "yes", "strong"],
                ["Parent / student attendance summary", "yes", "yes", "yes"],
                ["Audit log", "yes", "yes", "yes"]],
               [8.6, 3.0, 3.0, 3.0], size=8.2, aligns=["l", "c", "c", "c"])

    gap(doc, 6)
    callout(doc, "What survived all three filters",
            "RFID tap + fingerprint + offline buffer + teacher confirmation — fast enough to be used, cheap "
            "enough to own, private enough to defend.",
            fill=NAVY, border=NAVY, kicker_rgb=RGBColor(0xFF, 0xB7, 0x03),
            text_rgb=RGBColor(0xDC, 0xE7, 0xF8))

    doc.add_page_break()

    # ================= 3
    section_head(doc, 3, "Concept map",
                 "One chain from the student at the door to a number the school can defend", TEAL, TEAL_RGB)
    chain(doc, [("01", "USER / SETTING", "Student at the door; teacher and period fixed by the timetable"),
                ("02", "PROBLEM TRIGGER", "Paper register — slow, proxy-prone, easy to lose"),
                ("03", "SENSOR OR INPUT", "RC522 reads the card, R307 checks the finger"),
                ("04", "PROCESS / DECISION", "ESP32 validates both, de-duplicates, buffers offline"),
                ("05", "OUTPUT / ACTION", "Firebase sync, dashboards, automatic parent email"),
                ("06", "MEASURABLE BENEFIT", "15 minutes saved per class, zero proxy, ≈90% cheaper")],
          [NAVY, SAFFRON, TEAL, NAVY, TEAL, GREEN])

    gap(doc, 6)
    banner(doc, "PROPOSED DIRECTION", "Astro Smart Attendance",
           "Two-factor  ·  Offline-first  ·  AI self-healing  ·  privacy by design",
           None, title_size=17, tag="OUR CONCEPT", tag_fill=TEAL)

    label(doc, "What each link has to prove before we call it true")
    card_grid(doc, [
        {"title": "1  User", "body": "We solve a moment that repeats every period, not a textbook problem.", "accent": TEAL},
        {"title": "2  Trigger", "body": "The pain is measured in minutes and errors, not in adjectives.", "accent": TEAL},
        {"title": "3  Input", "body": "A tap plus a finger is faster and fairer than reading out names.", "accent": TEAL},
        {"title": "4  Process", "body": "The logic stays correct through power cuts, Wi-Fi loss and repeat taps.", "accent": TEAL},
        {"title": "5  Output", "body": "The record reaches teacher and parent without extra work for either.", "accent": TEAL},
        {"title": "6  Benefit", "body": "The gain shows up in a real classroom of 30, not in a simulation.", "accent": TEAL},
    ], cols=3, widths=[CW / 3] * 3, min_h=1.3)

    label(doc, "What happens to one tap — the data pathway")
    data_table(doc, ["Tap", "Finger", "Match", "Check", "Store", "Sync", "Alert"],
               [["card UID read", "template match", "both agree?", "duplicate? late?", "local buffer",
                 "Firebase write", "parent email"]],
               [CW / 7] * 7, size=7.6, head_fill=TEAL, zebra=False)

    label(doc, "Who gains what")
    data_table(doc, ["Who", "What changes", "What we measure"],
               [["Teacher", "15 minutes returned per class", "≈ one extra teaching hour per week"],
                ["Student", "No queue, no roll-call, no proxy blame", "Attendance visible the same day"],
                ["Parent", "Absence message before the day ends", "Same-day action, not next-week surprise"],
                ["School office", "One trusted register, exportable", "Reports without re-entering data"]],
               [3.6, 7.2, CW - 10.8], size=9)

    label(doc, "Unanswered questions we are carrying into validation", TEAL_RGB)
    for q in ["If a card is lost, what stops another student using it before the office reissues it?",
              "Two students tap within the same second — does the buffer keep both, in the right order?",
              "What exactly does the teacher see on the confirmation screen, and how is a mistake corrected?"]:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.left_indent = Cm(0.4)
        r = p.add_run("?   ")
        r.font.bold = True
        r.font.size = Pt(9.5)
        r.font.color.rgb = TEAL_RGB
        r2 = p.add_run(q)
        r2.font.size = Pt(9)
        r2.font.color.rgb = body

    gap(doc, 4)
    callout(doc, "The rule we keep coming back to",
            "“If the internet dies, the register must still work.” A rule that decided the architecture: "
            "the buffer came before the cloud, not after it.",
            fill=CREAM, border=GOLD, hand=True, size=11)

    doc.add_page_break()

    # ================= 4
    section_head(doc, 4, "Shortlisting matrix",
                 "Scored 1 to 5 together in the lab — evidence first, opinions second", SAFFRON, SAFFRON_RGB)
    score_table(doc,
                ["Candidate concept", "Novelty", "Feasibility", "Affordability", "Impact", "Prototype potential", "Total", "Rank"],
                [["Astro Smart Attendance", "5", "5", "5", "5", "4", "24", "#1"],
                 ["QR rotating code only", "4", "4", "5", "3", "4", "20", "#2"],
                 ["Simpler digital register", "2", "5", "5", "3", "3", "18", "#3"],
                 ["Sensor / app-only system", "3", "4", "3", "4", "3", "17", "#4"],
                 ["Community / service model", "3", "4", "5", "3", "2", "17", "#4"],
                 ["Face recognition terminal", "4", "3", "2", "4", "2", "15", "#6"]],
                [4.6, 1.9, 2.2, 2.3, 1.6, 2.3, 1.4, 1.2])

    gap(doc, 4)
    label(doc, "Totals at a glance", NAVY_RGB, before=2)
    bars = [("Astro Smart Attendance", 24, "10B981"), ("QR rotating code only", 20, "FF7A18"),
            ("Simpler digital register", 18, "93A5BE"), ("Sensor / app-only system", 17, "93A5BE"),
            ("Community / service model", 17, "93A5BE"), ("Face recognition terminal", 15, "93A5BE")]
    SEG = 24
    LABEL_W = 4.8
    seg_w = (CW - LABEL_W - 1.3) / SEG
    t = doc.add_table(rows=len(bars), cols=SEG + 2)
    table_layout(t, [LABEL_W] + [seg_w] * SEG + [1.3])
    for ri, (name, val, col) in enumerate(bars):
        cells = t.rows[ri].cells
        c = cells[0]
        no_borders(c)
        cell_margins(c, top=50, bottom=50, left=0, right=90)
        put(c, name, size=8.2, color=NAVY_RGB, align="r")
        for ci in range(SEG):
            c = cells[ci + 1]
            no_borders(c)
            cell_margins(c, top=50, bottom=50, left=0, right=0)
            put(c, "", size=3)
            shade(c, col if ci < val else "EEF2F7")
        c = cells[SEG + 1]
        no_borders(c)
        cell_margins(c, top=50, bottom=50, left=70, right=0)
        put(c, str(val), size=8.6, bold=True, color=NAVY_RGB)
        keep_row(t.rows[ri])

    gap(doc, 4)
    callout(doc, "Scoring note",
            "These are initial team hypotheses, not measured results. Each option was scored 1 (low) to 5 (high) "
            "in a team meeting, evidence from discovery dialogues was cited, and the shortlist was revised twice. "
            "Any score without cited evidence drops to a 3, and the matrix is re-scored after each validation step.",
            fill=SOFT, border=LINE, kicker_rgb=SAFFRON_RGB, text_rgb=body, size=8.6)

    label(doc, "Evidence behind the scores")
    data_table(doc, ["Score", "The evidence"],
               [["Novelty 5", "No card-plus-fingerprint terminal with on-device self-healing exists in our price band; teachers had not seen one."],
                ["Feasibility 5", "The prototype already reads cards, writes to Firebase and survives a Wi-Fi cut in the lab."],
                ["Affordability 5", "The bill of materials works out to roughly ₹2,450 per unit, costed from real parts."],
                ["Impact 5", "Every teacher we spoke to placed attendance in their top two daily time losses."],
                ["Prototype 4", "The 3D-printed case and parent-email templates are still being refined."]],
               [3.4, CW - 3.4], size=8.8)

    label(doc, "How the ranking moved once evidence arrived", TEAL_RGB)
    data_table(doc, ["Concept", "First → final", "What changed the score"],
               [["Astro Smart Attendance", "21 → 24", "Costed bill of materials landed near ₹2,450, under the ₹3,000 ceiling we set"],
                ["QR rotating code", "23 → 20", "A code shared on a group chat cannot be trusted for records"],
                ["Simpler digital register", "16 → 18", "Cheaper than expected, but still costs the teacher time"],
                ["Face recognition", "19 → 15", "Privacy and camera cost pulled it down after the product comparison"]],
               [4.4, 2.8, CW - 7.2], size=8.8)

    doc.add_page_break()

    # ================= 5
    section_head(doc, 5, "Selected concept and reason",
                 "The idea we are building, and the honest case for why it deserves to win", TEAL, TEAL_RGB)
    banner(doc, "SELECTED CONCEPT", "Astro Smart Attendance",
           "ESP32 + RC522 reader + R307 fingerprint + LCD1602",
           "The student taps a card and presses a finger; time, class, period and a pseudonymous ID are recorded "
           "in about three seconds, and both checks must agree before an entry is written. Astro AI 2.0 flags "
           "duplicates, late arrivals and proxy attempts, buffers offline and syncs to Firebase. Fingerprint "
           "templates stay inside the sensor. No face recognition. No phone required.",
           title_size=16, tag="CHOSEN", tag_fill=GOLD)

    gap(doc, 2)
    card_grid(doc, [
        {"title": "✓  Answers the registered problem",
         "body": "Saves 10–15 minutes every period, removes proxy entries and leaves a timestamped record.", "accent": GREEN},
        {"title": "⚙  Buildable by five students",
         "body": "ESP32, RC522, R307, LCD and a printed case — a working prototype, not a slide.", "accent": TEAL},
        {"title": "▤  Around 90% cheaper",
         "body": "An estimated ₹2,450 per unit against ₹30,000+ for commercial kits — within reach of any school.",
         "accent": SAFFRON},
        {"title": "◷  Measurable from day one",
         "body": "Time per class, duplicate rejection, proxy rejection, sync accuracy and teacher rating — all observable.",
         "accent": NAVY},
    ], cols=2, widths=[CW / 2, CW / 2], min_h=1.3)

    label(doc, "How a student is verified — four steps, about three seconds, two independent checks")
    card_grid(doc, [
        {"title": "1  Tap card", "body": "RFID card read at the door — who is claiming.", "accent": SAFFRON},
        {"title": "2  Press finger", "body": "R307 matches the template — is it really them.", "accent": TEAL},
        {"title": "3  AI validates", "body": "Both must agree; then period, duplicates and device health.", "accent": SAFFRON},
        {"title": "4  Confirm + alert", "body": "LCD confirms with a beep; Firebase syncs; parent emailed.", "accent": TEAL},
    ], cols=4, widths=[CW / 4] * 4, min_h=1.5)

    label(doc, "System at a glance", before=6)
    data_table(doc, ["Part", "What it does"],
               [["Controller", "ESP32 DevKit V1 — Wi-Fi, OTA updates, offline logic"],
                ["Input", "RC522 13.56 MHz reader + R307 fingerprint + school card"],
                ["Feedback", "LCD1602 I2C display + buzzer"],
                ["Cloud", "Firebase Auth + Realtime Database + Hosting"],
                ["Intelligence", "Astro AI 2.0 — 11 self-healing diagnostic checks"],
                ["Enclosure", "3D-printed case, designed in Blender"]],
               [3.4, CW - 3.4], size=8.3)

    label(doc, "What we deliberately left out — and why", before=6)
    card_grid(doc, [
        {"title": "Face recognition", "body": "A camera on children costs more trust than the speed is worth.", "tag": "REJECTED"},
        {"title": "Student phone app", "body": "Not every student owns a phone. A card works for all.", "tag": "PARKED"},
        {"title": "Full ERP replacement", "body": "Fees, exams and report cards stay out of scope.", "tag": "OUT OF SCOPE"},
        {"title": "Cloud-only design", "body": "No network, no register. The buffer comes first.", "tag": "REPLACED"},
    ], cols=4, widths=[CW / 4] * 4, min_h=1.3)

    label(doc, "Who owns which part of the build", before=6)
    data_table(doc, ["Member", "Role", "Owns", "Deliverable"],
               [["Shaurya Gupta", "Team captain", "Firmware and cloud", "Card read, Firebase, AI health checks"],
                ["Anant Tiwari", "Ideation and research", "User interviews, requirement notes", "Discovery dialogues and comparison"],
                ["Tejas Upadhyay", "Hardware integration", "Reader wiring, power, enclosure fit", "Bench tests and fault finding"],
                ["Diwakar Singh", "Product design", "3D enclosure, mounting, finish", "Printable case for the door"],
                ["Devansh Dhakad", "Testing and docs", "Test log, stress runs, this worksheet", "Evidence for every claim"]],
               [3.4, 3.6, 5.2, CW - 12.2], size=8.2)

    doc.add_page_break()

    # ================= 6
    section_head(doc, 6, "Initial system sketch",
                 "Labelled block diagram: user, sensor, controller, output, power and the human confirmation step")
    doc.paragraphs[-1].paragraph_format.space_after = Pt(2)
    label(doc, "The chain, drawn", NAVY_RGB, before=0, after=2)
    chain(doc, [("01", "STUDENT", "ID card + enrolled finger"),
                ("02", "RC522 READER", "13.56 MHz card tap"),
                ("03", "R307 SENSOR", "fingerprint, 1:1 match"),
                ("04", "ESP32 CONTROLLER", "both factors must agree · buffers"),
                ("05", "LCD1602 + BUZZER", "“Present” feedback")],
          [NAVY, SAFFRON, TEAL, NAVY, TEAL])

    gap(doc, 2)
    label(doc, "Then down to the cloud, and back to a human", NAVY_RGB, before=2, after=2)
    chain(doc, [("06", "FIREBASE CLOUD", "Auth + Realtime DB"),
                ("07", "DASHBOARDS", "Admin · Student · Guardian"),
                ("08", "PARENT EMAIL", "automatic alert")],
          [GOLD, TEAL, GREEN])

    gap(doc, 2)
    card_grid(doc, [
        {"title": "HUMAN CONFIRMATION", "body": "teacher reviews exceptions · confirms · audit log", "accent": GREEN},
        {"title": "POWER SOURCE", "body": "5 V USB adapter, full school day", "accent": MUTED_HEX},
        {"title": "PRIVACY BY DESIGN", "body": "templates on-sensor · no images", "accent": NAVY},
    ], cols=3, widths=[CW / 3] * 3, min_h=0.75)

    label(doc, "Bill of materials — what is in the box and its estimated cost")
    t = doc.add_table(rows=1, cols=3)
    table_layout(t, [5.2, CW - 8.4, 3.2])
    for i, h in enumerate(["Component", "Role in the system", "Est. cost"]):
        c = t.rows[0].cells[i]
        shade(c, NAVY)
        cell_borders(c, NAVY)
        cell_margins(c, top=70, bottom=70, left=100, right=100)
        put(c, h, size=8, bold=True, color=white, align="r" if i == 2 else None)
    keep_row(t.rows[0])
    bom = [["ESP32 DevKit V1", "Controller, Wi-Fi, offline logic", "≈ ₹450"],
           ["RC522 RFID module", "First factor: reads each student card", "≈ ₹120"],
           ["R307 fingerprint sensor", "Second factor: proves the card holder is that student", "≈ ₹950"],
           ["LCD1602 I2C + buzzer", "Name, status and audible confirm", "≈ ₹180"],
           ["Wiring, LEDs, headers", "Assembly, level shifting, status lights", "≈ ₹120"],
           ["3D-printed enclosure", "Holds board, reader and sensor; mounts at the door", "≈ ₹280"],
           ["5 V adapter + cable", "Power for a full school day", "≈ ₹150"],
           ["30 RFID cards", "One card per student, issued by school", "≈ ₹200"]]
    for ri, row in enumerate(bom):
        cells = t.add_row().cells
        for i, val in enumerate(row):
            c = cells[i]
            shade(c, WHITE if ri % 2 == 0 else SOFT)
            cell_borders(c, LINE)
            cell_margins(c, top=40, bottom=40, left=100, right=100)
            put(c, val, size=8.1, bold=(i == 0), color=NAVY_RGB if i == 0 else body,
                align="r" if i == 2 else None)
        keep_row(t.rows[-1])
    # total row
    cells = t.add_row().cells
    merged = cells[0].merge(cells[1])
    shade(merged, NAVY)
    cell_borders(merged, NAVY)
    cell_margins(merged, top=90, bottom=90, left=110, right=110)
    put(merged, "EST. TOTAL", size=9, bold=True, color=white, track=14)
    add(merged, "one classroom terminal, assembled and tested", size=7.4,
        color=RGBColor(0xBF, 0xDB, 0xFE), before=1)
    tc = cells[2]
    shade(tc, NAVY)
    cell_borders(tc, NAVY)
    cell_margins(tc, top=90, bottom=90, left=100, right=110)
    put(tc, "≈ ₹2,450", size=12, bold=True, color=RGBColor(0xFF, 0xB7, 0x03), align="r")

    label(doc, "What the LCD shows in each case", before=6)
    lcd(doc, [("PRESENT", "Aarav S.  ·  IX-B", "card recognised inside the period", RGBColor(0x34, 0xD3, 0x99)),
              ("ALREADY MARKED", "Aarav S.  ·  08:12", "duplicate tap in the same period", RGBColor(0xFB, 0xBF, 0x24)),
              ("CARD NOT FOUND", "please see office", "unknown or unenrolled card", RGBColor(0xF8, 0x71, 0x71))])

    label(doc, "Against the two nearest alternatives")
    data_table(doc, ["Criterion", "Our concept", "QR code on a screen", "Digital register on a tablet"],
               [["Cost per classroom", "≈ ₹2,450", "₹0 hardware, ≈ ₹400 data", "₹12,000+ tablet"],
                ["Works without internet", "Yes — local buffer", "No, needs the app online", "Partly, if the app caches"],
                ["Proxy risk", "Very low — card + finger", "High — a screenshot travels", "Medium — a login can be shared"],
                ["Needs a student phone", "No", "Yes", "No"],
                ["Teacher effort", "Confirm exceptions only", "None until the report", "The whole period, typing"],
                ["Parent alert", "Automatic email", "Possible, if online", "Manual or not at all"]],
               [4.0, 4.2, 4.6, CW - 12.8], size=7.9)

    doc.add_page_break()

    # ================= 7
    section_head(doc, 7, "What the team must validate next",
                 "Written before the results — each step has a decision rule, not just a task", SAFFRON, SAFFRON_RGB)
    data_table(doc, ["Validation step", "What we do", "Decision rule"],
               [["Interview 3–5 users and stakeholders", "Teachers, students, parents and office staff, recorded anonymously with consent.", "If fewer than 3 of 5 call attendance a top-two time loss, we revisit the problem."],
                ["Confirm the problem is frequent enough", "Check whether it recurs every period and in every class, not just on busy days.", "Below 3 occurrences per class per day, the hardware cannot be justified."],
                ["Compare two existing products", "A commercial biometric system and a phone-based app, judged on cost, privacy and offline use.", "If either matches on all three, we change direction."],
                ["Run a safe, low-cost proof of concept", "One reader, one class, one week — before any advanced feature is added.", "Any safety or privacy failure stops the trial immediately."],
                ["Collect baseline and prototype measurements", "Time 30 students by hand, then with the terminal, same conditions — invent nothing.", "If the terminal is not at least 5× faster, the design is not finished."],
                ["Test the fingerprint factor honestly", "Enrol 30 fingers, then try a borrowed card with the wrong finger, and a wet or bandaged finger.", "Any proxy that gets through drops the fingerprint stage to a 2 in the matrix."]],
               [4.4, 6.4, CW - 10.8], size=8.2, head_fill="C2410C")

    label(doc, "The first week, if the school gives us one classroom", TEAL_RGB)
    data_table(doc, ["Day", "Activity", "What we do"],
               [["MON–TUE", "Bench test", "Read 30 cards and 30 fingers, confirm every entry lands in Firebase."],
                ["WED", "Enrol", "Card plus finger, with written parent consent; only a template is stored."],
                ["THU–FRI", "Live period", "One real class marks attendance with the terminal beside the register."],
                ["SAT", "Compare", "Count the differences between our register and the teacher's."]],
               [2.4, 3.0, CW - 5.4], size=8.2, head_fill=TEAL)

    gap(doc, 6)
    section_head(doc, 8, "Prototype success indicators",
                 "How we will prove it works — measured numbers, not adjectives", TEAL, TEAL_RGB)
    card_grid(doc, [
        {"title": "◷  Time for a class of 30 (simulated)", "body": "30 simulated students doing card then finger, clocked with a stopwatch.", "tag": "TARGET  < 90 SEC", "tag_color": TEAL_RGB, "accent": SAFFRON},
        {"title": "⚑  Duplicate scan rejection", "body": "Same card twice in one period is refused, even with the right finger.", "tag": "TARGET  100%", "tag_color": TEAL_RGB, "accent": NAVY},
        {"title": "✓  Late and invalid handling", "body": "Late arrivals flagged; unknown or wrong-period cards rejected.", "tag": "TARGET  CORRECTLY FLAGGED", "tag_color": TEAL_RGB, "accent": TEAL},
        {"title": "≋  Offline → online sync", "body": "Entries stored locally then synced when Wi-Fi returns, with no loss.", "tag": "TARGET  100% ACCURATE", "tag_color": TEAL_RGB, "accent": TEAL},
        {"title": "◉  Teacher usability", "body": "Teachers rate setup, the confirmation step and dashboard clarity.", "tag": "TARGET  4+ OUT OF 5", "tag_color": TEAL_RGB, "accent": GREEN},
        {"title": "⚿  Proxy attempt rejected", "body": "An enrolled card with a different finger must never write an entry.", "tag": "TARGET  100%", "tag_color": TEAL_RGB, "accent": NAVY},
    ], cols=2, widths=[CW / 2, CW / 2], min_h=1.7)

    label(doc, "Baseline against prototype", TEAL_RGB)
    data_table(doc, ["Measure", "Baseline (paper register)", "Target (prototype)"],
               [["Time for 30 students", "10–15 min, teacher-driven", "< 90 s"],
                ["Duplicate entries", "Common and unnoticed", "Rejected 100%"],
                ["Late-arrival record", "Written by hand", "Flagged with a timestamp"],
                ["Parent notification", "Same day if at all", "Within 5 minutes"],
                ["Records after a Wi-Fi cut", "Not applicable", "Buffered, then synced"],
                ["Evidence for an audit", "None", "Timestamped log per tap"]],
               [6.0, 6.0, CW - 12.0], size=8.8)

    gap(doc, 4)
    callout(doc, "Our measurement promise",
            "Every number here goes into a lab notebook with date, class size and method. If a target fails we "
            "report the failure and change the design — we do not change the number.",
            fill=NAVY, border=NAVY, kicker_rgb=RGBColor(0xFF, 0xB7, 0x03),
            text_rgb=RGBColor(0xDC, 0xE7, 0xF8))

    doc.add_page_break()

    # ================= 8
    section_head(doc, 8 if False else 9, "Risks and design safeguards",
                 "Named before they could surprise us, each with the safeguard built into the design", TEAL, TEAL_RGB)
    data_table(doc, ["Risk", "Our design safeguard"],
               [["Card sharing / proxy attendance", "Two factors: the card says who is claiming, the finger proves it is them. No entry until both agree."],
                ["Finger fails in class", "A wet, dry or bandaged finger fails, so the LCD offers a teacher-override code that is logged and emailed to the parent."],
                ["Biometric data and consent", "The R307 keeps templates inside the sensor, not on the network. Written parent consent, deletion on request, no images leave the board."],
                ["Unequal phone or device access", "The card needs no phone, no internet and no battery from the student. One card each, issued by the school."],
                ["Network or power outage", "An offline buffer on the ESP32, auto-sync on reconnect, 5 V backup power and OTA recovery."],
                ["Privacy and data misuse", "No face recognition. Only ID, time and class are stored, behind Firebase Auth with role-based access."],
                ["Hardware failure in class", "Astro AI 2.0 runs 11 self-healing checks, a watchdog restarts the board, error codes reach the LCD, parts are modular."],
                ["Cost, scale and maintenance", "An estimated ₹2,450 per unit, common parts, a printable case and a free cloud tier — one unit per room is realistic."]],
               [4.6, CW - 4.6], size=8.2)

    label(doc, "What would make us abandon this idea")
    data_table(doc, ["We abandon if…", "…because"],
               [["30 taps slower than two minutes", "the terminal loses to a paper register"],
                ["A unit above roughly ₹3,000", "it stops being a school solution"],
                ["Any proxy that beats the two factors", "the extra sensor earns its place or it goes"],
                ["Templates we cannot store safely", "no biometric data, no fingerprint stage"]],
               [CW / 2, CW / 2], size=8.8, head_fill="B91C1C")

    label(doc, "Team reflection — in our own words", TEAL_RGB)
    reflections = [("1", "Which idea did we reject, and why?",
                    "Face recognition. We kept fingerprint as a second factor instead: one finger, verified locally, far less data than a camera."),
                   ("2", "What did a user tell us that changed our thinking?",
                    "A teacher said: “Don’t give me something that stops working when the Wi-Fi stops.” That is why we went offline-first."),
                   ("3", "What is the smallest test that can prove or disprove our idea?",
                    "One period, 30 students, card and finger. Slower than two minutes and a borrowed card beats it, it fails.")]
    for num, q, a in reflections:
        t = doc.add_table(rows=1, cols=2)
        table_layout(t, [1.0, CW - 1.0])
        c0 = t.rows[0].cells[0]
        shade(c0, GOLD)
        cell_borders(c0, GOLD)
        put(c0, num, size=11, bold=True, color=NAVY_RGB, align="c")
        c1 = t.rows[0].cells[1]
        shade(c1, AMBER_L)
        cell_borders(c1, "F3E0A8")
        cell_margins(c1, top=90, bottom=90, left=130, right=130)
        put(c1, q, size=9.2, bold=True, color=RGBColor(0x92, 0x40, 0x0E), space=1)
        add(c1, a, size=9.4, color=NAVY_RGB, font=FONT, italic=True, before=2, line=1.25)
        keep_row(t.rows[0])
        gap(doc, 3)

    gap(doc, 2)
    callout(doc, "What this worksheet should prove about us",
            "We chose the idea we can build, measure and defend — not the loudest one in the room. Every claim "
            "here has a test behind it, and every test is one a Class 9 team can actually run.",
            fill=NAVY, border=NAVY, kicker_rgb=RGBColor(0xFF, 0xB7, 0x03),
            text_rgb=RGBColor(0xDC, 0xE7, 0xF8))

    label(doc, "Before submission — our own checklist")
    card_grid(doc, [
        {"title": "✓  All nine sections answered"},
        {"title": "✓  Names, roles and mentor verified"},
        {"title": "✓  Numbers marked measured or hypothesis"},
        {"title": "✓  Demo link tested on a school computer"},
        {"title": "✓  Two products compared with sources"},
        {"title": "✓  Fingerprint consent taken from parents"},
        {"title": "✓  Worksheet signed and dated"},
    ], cols=3, widths=[CW / 3] * 3, min_h=0.85)

    gap(doc, 8)
    signature_row(doc, [("Shaurya Gupta", "TEAM CAPTAIN"),
                        ("Dr. Jayesh Shinde", "MENTOR"),
                        ("25 November 2026", "DATE  ·  RENUKOOT, U.P.")])

    cp = doc.core_properties
    cp.title = "Part 1 — Creative Ideation Worksheet · Astro Smart Attendance"
    cp.author = "Team Sun Rises India, ABPS Renukoot"
    cp.subject = "ABG STEM Quest 2026-27 · SDG 9"
    cp.keywords = "creative ideation worksheet, SDG 9, RFID attendance, ESP32, fingerprint, Astro AI 2.0"
    cp.comments = ""

    doc.save(OUT)
    print("wrote", OUT, os.path.getsize(OUT))


if __name__ == "__main__":
    build()
