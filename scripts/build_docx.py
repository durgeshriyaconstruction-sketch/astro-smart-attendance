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
PLUM_RGB = RGBColor(0x7C, 0x3A, 0xED)
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
ASSETS = os.path.join(HERE, "assets")


def asset(name):
    return os.path.join(ASSETS, name)
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


def put_image(cell, path, width_cm, align="c"):
    """Place a sticker in a cell, keeping it inline so tables stay tidy."""
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    p = cell.paragraphs[0] if not cell.paragraphs[0].text else cell.add_paragraph()
    if align == "c":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == "r":
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    if os.path.exists(path):
        p.add_run().add_picture(path, width=Cm(width_cm))
    return p


def sticker_row(doc, items, widths=None, pad_top=0):
    """items: list of (asset name, width cm). Renders them side by side."""
    widths = widths or [CW / len(items)] * len(items)
    t = doc.add_table(rows=1, cols=len(items))
    table_layout(t, widths)
    for i, (name, wcm) in enumerate(items):
        c = t.rows[0].cells[i]
        no_borders(c)
        cell_margins(c, top=pad_top, bottom=0, left=0, right=0)
        put_image(c, asset(name), wcm)
    keep_row(t.rows[0])
    return t


def margin_note(doc, scribble, caption, color=RGBColor(0x92, 0x40, 0x0E),
                img_w=1.5, side="right"):
    """A doodle with a handwritten caption beside it, like a margin annotation."""
    widths = [img_w + 0.3, CW - (img_w + 0.3)] if side == "left" else [CW - (img_w + 0.3), img_w + 0.3]
    t = doc.add_table(rows=1, cols=2)
    table_layout(t, widths)
    ci = 0 if side == "left" else 1
    for c in t.rows[0].cells:
        no_borders(c)
    pic = t.rows[0].cells[ci]
    cell_margins(pic, top=20, bottom=20, left=0, right=0)
    put_image(pic, asset(scribble), img_w, align="r" if side == "right" else "l")
    txt = t.rows[0].cells[1 - ci]
    cell_margins(txt, top=20, bottom=20, left=90 if side == "right" else 20, right=20 if side == "right" else 90)
    p = put(txt, caption, size=10.5, color=color, font=HAND,
            align="r" if side == "right" else None)
    keep_row(t.rows[0])
    return t


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


def add_hand_note(doc, text):
    """A single hand-written line, right-aligned, as a margin aside."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run(text)
    r.font.size = Pt(9.5)
    r.font.name = HAND
    r.font.color.rgb = PLUM_RGB
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
    add(c, title, size=title_size, bold=True, color=white, space=1, before=1)
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
    r2 = hp.add_run(" ·     PART 1 — CREATIVE IDEATION WORKSHEET")
    r2.font.size = Pt(8.5)
    r2.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)
    r2.font.name = FONT
    spacing(r2, 12)
    field_footer(s)

    # ================= cover
    banner(doc, "SUN RISES INDIA ·  GRADE 9 ·  ABPS RENUKOOT",
           "ASTRO SMART ATTENDANCE",
           "AI + IoT + Cloud ·  smart school attendance system",
           "A compact ESP32 RFID + fingerprint terminal — two factors against proxy, an offline-first buffer, "
           "an automatic parent alert, and an estimated ₹2,450 a unit from local parts.",
           title_size=26,
           tag="CHOSEN CONCEPT")

    gap(doc, 2)
    sticker_row(doc, [("note-1.png", 4.6), ("note-2.png", 4.6), ("note-3.png", 4.6)],
                widths=[CW / 3] * 3)

    gap(doc, 2)
    t = doc.add_table(rows=1, cols=1)
    table_layout(t, [CW])
    c = t.rows[0].cells[0]
    shade(c, CREAM)
    cell_borders(c, GOLD)
    cell_margins(c, top=110, bottom=110, left=140, right=140)
    put(c, "One tap. Attendance done. Parents informed.", size=12, color=NAVY_RGB, font=HAND, space=1)
    add(c, "CONCEPT BRIEF  ·  PART 1  ·  ABG STEM QUEST 2026–27", size=7.5, color=muted, space=0, before=1, track=16)

    gap(doc, 6)
    stat_strip(doc, [("≈ ₹2,450", "EST. COST PER UNIT", SAFFRON_RGB),
                     ("≈ 3 sec", "CARD + FINGERPRINT", TEAL_RGB),
                     ("OFFLINE", "SYNCS WHEN BACK", NAVY_RGB),
                     ("9 / 9", "SECTIONS ANSWERED", GREEN_RGB)])

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
               [3.4, CW - 3.4], size=8.4)

    gap(doc, 10)
    label(doc, "The proposal, in five blocks", NAVY_RGB)
    chain(doc, [("01", "STUDENT", "ID card + enrolled finger"),
                ("02", "RC522 + R307", "card, then finger"),
                ("03", "ESP32", "both must agree"),
                ("04", "LCD1602", "“Present” + beep"),
                ("05", "FIREBASE", "dashboard + parent email")],
          [NAVY, SAFFRON, TEAL, NAVY, TEAL])

    gap(doc, 6)
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
    ], cols=3, widths=[CW / 3] * 3, min_h=1.8)

    gap(doc, 5)
    label(doc, "The five of us, and the part each one owns", NAVY_RGB)
    card_grid(doc, [
        {"title": "Shaurya Gupta", "body": "Captain · firmware and cloud", "accent": SAFFRON},
        {"title": "Anant Tiwari", "body": "Discovery and comparison", "accent": TEAL},
        {"title": "Tejas Upadhyay", "body": "Reader, power, enclosure fit", "accent": SAFFRON},
        {"title": "Diwakar Singh", "body": "3D case and mounting", "accent": TEAL},
        {"title": "Devansh Dhakad", "body": "Test plan and this worksheet", "accent": SAFFRON},
    ], cols=5, widths=[CW / 5] * 5, min_h=0.7)

    gap(doc, 5)
    callout(doc, "How to read this worksheet",
            "Nine numbered parts, in the order the format asks for: the problem we chose, the ideas we generated, "
            "the map, the scored matrix, the concept we selected, the system sketch, what we must validate, how we "
            "will measure success, and the risks we designed against. Every number is either measured in our own "
            "tests or marked as a hypothesis.",
            fill=SOFT, border=LINE, kicker_rgb=NAVY_RGB, text_rgb=body, size=8.4)

    gap(doc, 4)
    margin_note(doc, "star-gold.png",
                "one classroom, five students, nine parts — and a school that has to say yes at the end.",
                color=PLUM_RGB, img_w=0.7)

    gap(doc, 4)
    t = doc.add_table(rows=1, cols=2)
    table_layout(t, [CW / 2, CW / 2])
    c0, c1 = t.rows[0].cells
    shade(c0, "ECFDF5")
    cell_borders(c0, "A7E3E1")
    cell_margins(c0, top=80, bottom=80, left=130, right=130)
    put(c0, "WHAT THIS IS", size=6.6, bold=True, color=GREEN_RGB, track=22, space=2)
    for line in ["A two-factor terminal a school can own outright",
                 "An offline-first register that syncs later",
                 "A prototype plan with a test behind every number"]:
        add(c0, "✓  " + line, size=8.4, color=body, before=2, line=1.22)
    shade(c1, "FEF2F2")
    cell_borders(c1, "FCA5A5")
    cell_margins(c1, top=80, bottom=80, left=130, right=130)
    put(c1, "WHAT THIS IS NOT", size=6.6, bold=True, color=RGBColor(0x99, 0x1B, 0x1B), track=22, space=2)
    for line in ["A finished product, or a promise of one",
                 "A camera that watches a child all day",
                 "A subscription the school has to renew"]:
        add(c1, "✕  " + line, size=8.4, color=body, before=2, line=1.22)
    keep_row(t.rows[0])

    doc.add_page_break()

    # ================= contents spread
    t = doc.add_table(rows=1, cols=1)
    table_layout(t, [CW])
    c = t.rows[0].cells[0]
    shade(c, NAVY)
    no_borders(c)
    cell_margins(c, top=95, bottom=95, left=170, right=170)
    put(c, "WHAT IS INSIDE", size=7, bold=True, color=RGBColor(0xFF, 0xB7, 0x03), track=34, space=2)
    add(c, "Nine parts, in the order the format asks", size=20, bold=True, color=white, before=3)
    add(c, "Start at the top if you have two minutes; jump to 06 if you only want the machine.",
        size=8.2, color=RGBColor(0xC9, 0xD8, 0xEE), before=3)

    gap(doc, 5)
    contents = [
        ("01", "Problem focus", "Who feels it, when, and what proof would look like", "03"),
        ("02", "Brainstormed possibilities", "Ten ideas, then three filters to cut them down", "04"),
        ("03", "Concept map", "Six stages from the door to a number the school can defend", "05"),
        ("04", "Shortlisting matrix", "Six concepts, five criteria, scored 1 to 5 with evidence", "06"),
        ("05", "Selected concept and reason", "The idea we take forward and why it beat the other five", "07"),
        ("06", "Initial system sketch", "Block diagram, costed bill of materials, LCD states", "08"),
        ("07", "What we must validate next", "Six tests, each with a decision rule written beforehand", "09"),
        ("08", "Prototype success indicators", "Six numbers we will be judged on, with targets", "09"),
        ("09", "Risks and design safeguards", "The safeguards built in, and when we would abandon", "10"),
    ]
    t = doc.add_table(rows=len(contents), cols=3)
    table_layout(t, [1.5, CW - 3.5, 2.0])
    for i, (num, title, desc, page) in enumerate(contents):
        c0, c1, c2 = t.rows[i].cells
        for cc in (c0, c1, c2):
            cell_borders(cc, LINE)
            cell_margins(cc, top=30, bottom=30, left=110, right=110)
            shade(cc, WHITE if i % 2 == 0 else SOFT)
        put(c0, num, size=12, bold=True, color=SAFFRON_RGB, align="c")
        put(c1, title, size=10.5, bold=True, color=NAVY_RGB, space=0)
        add(c1, desc, size=8.2, color=muted, before=1)
        put(c2, "PAGE " + page, size=7, bold=True, color=muted, align="r", track=16)
        keep_row(t.rows[i])

    gap(doc, 8)
    card_grid(doc, [
        {"title": "Two ways to read it", "accent": TEAL,
         "body": "Read straight through for the argument, or take the nine headings as the index and open the page "
                 "you need. Nothing important is said only once."},
        {"title": "What is measured, what is assumed", "accent": SAFFRON,
         "body": "Measured numbers carry a method. Estimates are marked as estimates. Where we have not "
                 "measured something, the page names the test and the result that would change our mind."},
        {"title": "Every number has a home", "accent": GREEN,
         "body": "≈ ₹2,450 is itemised on page 8. 24 is the matrix total on page 6. 9/9 is the sections."},
    ], cols=3, widths=[CW / 3] * 3, min_h=1.0)

    gap(doc, 3)
    label(doc, "Method — the six passes behind this worksheet", NAVY_RGB)
    weeks = [["PASS 1", "Looked", "Assembly, corridor, office. Counted how long a register really takes."],
             ["PASS 2", "Asked", "Fourteen conversations with teachers, parents and office staff; two changed the design."],
             ["PASS 3", "Widened", "Ten ideas on the board before a single one was allowed to be judged."],
             ["PASS 4", "Filtered", "Three filters, six concepts into the matrix, one direction chosen."],
             ["PASS 5", "Pressure-tested", "Named every way it could fail, then wrote the safeguard beside each risk."],
             ["PASS 6", "Wrote", "This worksheet — nine sections, every number labelled measured or hypothesis."]]
    t = doc.add_table(rows=len(weeks), cols=3)
    table_layout(t, [2.0, 2.2, CW - 4.2])
    for i, (wk, verb, txt) in enumerate(weeks):
        c0, c1, c2 = t.rows[i].cells
        for cc in (c0, c1, c2):
            cell_borders(cc, LINE)
            cell_margins(cc, top=34, bottom=34, left=110, right=110)
            shade(cc, WHITE if i % 2 == 0 else SOFT)
        put(c0, wk, size=7.6, bold=True, color=muted, track=14)
        put(c1, verb, size=9.5, bold=True, color=NAVY_RGB)
        put(c2, txt, size=8.4, color=body)
        keep_row(t.rows[i])

    gap(doc, 8)
    t = doc.add_table(rows=1, cols=2)
    table_layout(t, [7.4, CW - 7.4])
    c0, c1 = t.rows[0].cells
    shade(c0, AMBER_L)
    cell_borders(c0, "F3E0A8")
    cell_margins(c0, top=110, bottom=110, left=150, right=150)
    put(c0, "THE LINE WE KEPT RETURNING TO", size=6.2, bold=True, color=RGBColor(0x92, 0x40, 0x0E), track=18)
    add(c0, "“If the internet dies, the register must still work.”", size=13, color=NAVY_RGB,
        font=HAND, before=4, line=1.1)
    shade(c1, WHITE)
    cell_borders(c1, LINE)
    cell_margins(c1, top=110, bottom=110, left=150, right=150)
    put(c1, "AND THE ONE THING WE REFUSED", size=6.6, bold=True, color=muted, track=22)
    add(c1, "A camera on a child. Everything else was negotiable; that was not.", size=9.2,
        color=NAVY_RGB, before=4, line=1.25)
    add(c1, "Which is why the second factor is a finger and not a face.", size=8.0, color=muted, before=2)
    keep_row(t.rows[0])

    gap(doc, 8)
    t = doc.add_table(rows=1, cols=1)
    table_layout(t, [CW])
    c = t.rows[0].cells[0]
    shade(c, NAVY)
    no_borders(c)
    cell_margins(c, top=90, bottom=90, left=170, right=170)
    put(c, "THE ONE QUESTION THIS DOCUMENT ANSWERS", size=6.8, bold=True, color=RGBColor(0xFF, 0xB7, 0x03),
        track=30, space=3)
    add(c, "Can five Class 9 students build a two-factor attendance terminal a school can actually afford, "
           "run without internet, and defend to a parent?", size=10.8, bold=True, color=white, before=3, line=1.18)
    add(c, "Nine parts, one answer — every number that is not measured is labelled with the test that will.",
        size=8.0, color=RGBColor(0xC9, 0xD8, 0xEE), before=3, line=1.2)

    gap(doc, 1)
    margin_note(doc, "star-gold.png",
                "nine parts, written the week we were still arguing about the third one.",
                color=PLUM_RGB, img_w=0.9)

    gap(doc, 5)
    label(doc, "Five numbers that carry the worksheet — read as targets, not as results", NAVY_RGB, before=0, after=2)
    stat_strip(doc, [("10–15 min", "LOST PER PERIOD", SAFFRON_RGB),
                     ("≈ 3 sec", "CARD + FINGERPRINT", TEAL_RGB),
                     ("< 90 s", "A CLASS OF 30", NAVY_RGB),
                     ("≈ ₹2,450", "EST. PER CLASSROOM", SAFFRON_RGB),
                     ("24 / 25", "TOP SCORE IN §4", GREEN_RGB)])

    t = doc.add_table(rows=1, cols=1)
    table_layout(t, [CW])
    c = t.rows[0].cells[0]
    shade(c, SOFT)
    cell_borders(c, LINE)
    cell_margins(c, top=60, bottom=60, left=120, right=120)
    put(c, "THE THREE QUESTIONS A JUDGE WILL ASK", size=6.4, bold=True, color=muted, track=16, space=1)
    add(c, "Why not a phone app? Not every student carries one, and a screenshot travels further than any card. "
           "Why not a register? It is edited silently and never reaches the parent. Why so cheap? Every part is an "
           "off-the-shelf module — nothing custom, nothing licensed, nothing renews.",
        size=8.2, color=body, before=2, line=1.22)


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
    ], cols=4, widths=[CW / 4] * 4, min_h=1.45)

    label(doc, "What we saw with our own eyes")
    callout(doc, "Assembly, first bell",
            "Assembly queues for the register · two names ticked twice in the same period · late arrivals argued "
            "about at the office · parents learning of absence after school.",
            fill=SAFFRON_L, border="FCD9BC", size=8.4)

    label(doc, "Success looks like", TEAL_RGB)
    callout(doc, "Target for the trial",
            "30 students verified in under 90 seconds, no duplicate entries, every parent alerted within "
            "5 minutes of the period ending.",
            fill=TEAL_L, border="A7E3E1", kicker_rgb=TEAL_RGB, size=8.4)

    label(doc, "What users told us — anonymised notes from discovery dialogues")
    card_grid(doc, [
        {"title": "“Fifteen minutes gone every period, just calling out names. I could teach a whole concept in that time.”",
         "body": "Class teacher · ABPS Renukoot", "fill": CREAM, "border": "F3E0A8"},
        {"title": "“We find out our child was absent only when the day is over. By then the whole day is lost.”",
         "body": "Parent · Renukoot", "fill": CREAM, "border": "F3E0A8"},
    ], cols=2, widths=[CW / 2, CW / 2])

    gap(doc, 2)
    stat_strip(doc, [("10–15 min", "LOST EVERY PERIOD, EVERY CLASS", SAFFRON_RGB),
                     ("15+ lakh", "SCHOOLS ON PAPER REGISTERS", TEAL_RGB),
                     ("≈90%", "CHEAPER THAN COMMERCIAL SYSTEMS", NAVY_RGB)])

    gap(doc, 5)
    callout(doc, "In one line",
            "a low-cost terminal that verifies a student by card and finger, marks a 30-student class in under "
            "two minutes, keeps recording when the internet drops, and tells parents the same period.",
            fill=NAVY, border=NAVY, kicker_rgb=RGBColor(0xFF, 0xB7, 0x03),
            text_rgb=RGBColor(0xDC, 0xE7, 0xF8))

    gap(doc, 3)
    label(doc, "What one period costs the school, counted in minutes", NAVY_RGB)
    data_table(doc, ["Moment in the day", "What happens on paper", "What we would change"],
               [["First bell, roll-call", "4–6 minutes while the register goes round",
                 "Each student taps as they enter — the register fills itself"],
                ["Late arrivals, 2nd period", "Names added by hand at the office, no time recorded",
                 "A timestamp is written the moment the card is tapped"],
                ["Absence message home", "Written after school, or never at all",
                 "An email leaves the moment the period closes"],
                ["Corrections and disputes", "The register is edited and the earlier entry is lost",
                 "Every correction is logged with who changed it and why"]],
               [3.8, 6.4, CW - 10.2], size=8.2)

    gap(doc, 5)
    callout(doc, "Two facts that fixed the scale",
            "15+ lakh schools run on paper; a commercial system starts near ₹30,000 a room, plus a licence.",
            fill=SOFT, border=LINE, kicker_rgb=TEAL_RGB, text_rgb=body, size=8.0)

    gap(doc, 2)
    margin_note(doc, "spark-saffron.png",
                "four places a period leaks — and only one of them is the roll-call.", img_w=0.65)

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
              cols=2, widths=[CW / 2, CW / 2], min_h=1.1)

    gap(doc, 4)
    t = doc.add_table(rows=1, cols=1)
    table_layout(t, [CW])
    c1 = t.rows[0].cells[0]
    shade(c1, "FEE2E2")
    cell_borders(c1, "FCA5A5")
    cell_margins(c1, top=80, bottom=80, left=130, right=130)
    put(c1, "CROSSED OFF THE BOARD ON PURPOSE", size=6.4, bold=True, color=RGBColor(0x99, 0x1B, 0x1B),
        track=20, space=2)
    add(c1, "Face recognition was the only idea that failed all three filters at once — privacy, consent and camera "
            "cost. It is listed because an idea you cannot name is an idea you never really considered.",
        size=8.2, color=RGBColor(0x7F, 0x1D, 0x1D), before=2, line=1.22)
    keep_row(t.rows[0])

    gap(doc, 5)
    label(doc, "What each surviving idea buys — and what it costs us", NAVY_RGB)
    card_grid(doc, [
        {"title": "Card tap-in", "body": "₹200 for 30 cards; a lost card means the office.", "accent": TEAL},
        {"title": "Finger second factor", "body": "₹950 — the largest part in the box.", "accent": TEAL},
        {"title": "Offline buffer", "body": "Firmware complexity and a sync queue to test.", "accent": TEAL},
        {"title": "Duplicate flags", "body": "One more rule for the teacher to learn.", "accent": TEAL},
    ], cols=4, widths=[CW / 4] * 4, min_h=0.9)

    gap(doc, 3)
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
               [8.6, 3.0, 3.0, 3.0], size=7.6, aligns=["l", "c", "c", "c"])


    gap(doc, 4)
    callout(doc, "What survived all three filters",
            "RFID tap + fingerprint + offline buffer + teacher confirmation — fast enough to be used, cheap "
            "enough to own, private enough to defend.",
            fill=NAVY, border=NAVY, kicker_rgb=RGBColor(0xFF, 0xB7, 0x03),
            text_rgb=RGBColor(0xDC, 0xE7, 0xF8))

    gap(doc, 3)
    margin_note(doc, "star-gold.png",
                "ten ideas in, four out, one forward — that is what a filter is for.", img_w=0.8)

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
           "Two-factor ·  Offline-first ·  Teacher in the loop ·  Privacy by design",
           None, title_size=17, tag="OUR CONCEPT", tag_fill=TEAL)

    label(doc, "What each link has to prove before we call it true")
    card_grid(doc, [
        {"title": "1 User", "body": "We solve a moment that repeats every period, not a textbook problem.", "accent": TEAL},
        {"title": "2 Trigger", "body": "The pain is measured in minutes and errors, not in adjectives.", "accent": TEAL},
        {"title": "3 Input", "body": "A tap plus a finger is faster and fairer than reading out names.", "accent": TEAL},
        {"title": "4 Process", "body": "The logic stays correct through power cuts, Wi-Fi loss and repeat taps.", "accent": TEAL},
        {"title": "5 Output", "body": "The record reaches teacher and parent without extra work for either.", "accent": TEAL},
        {"title": "6 Benefit", "body": "The gain shows up in a real classroom of 30, not in a simulation.", "accent": TEAL},
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

    gap(doc, 6)
    label(doc, "The weak link, named on purpose")
    card_grid(doc, [
        {"title": "What could break the chain", "accent": SAFFRON,
         "body": "If the R307 rejects a wet or bandaged finger, the chain stops at stage 03 and a student is "
                 "marked absent while standing at the door."},
        {"title": "What we put in the chain to stop it", "accent": TEAL,
         "body": "A teacher-override code on the LCD: the entry is written, flagged as unverified, and the "
                 "parent email says which check passed and which did not."},
        {"title": "What we measure to know it worked", "accent": GREEN,
         "body": "How often the fallback is used per 100 taps, and whether any fallback entry was ever wrong in "
                 "the comparison against the paper register."},
    ], cols=3, widths=[CW / 3] * 3, min_h=1.6)

    gap(doc, 5)
    label(doc, "The two-minute version, drawn as a sentence", NAVY_RGB)
    chain(doc, [("01", "AT THE DOOR", "card tapped, finger pressed"),
                ("02", "IN THE BOX", "both checks agree, entry written"),
                ("03", "IN THE CLOUD", "dashboards update, parent emailed"),
                ("04", "IN THE OFFICE", "one register, exportable, auditable")],
          [NAVY, TEAL, SAFFRON, GREEN])

    gap(doc, 2)
    margin_note(doc, "arrow-saffron.png",
                "We are not pretending to have these answers yet. That is what the pilot month is for.",
                color=PLUM_RGB, img_w=1.0)
    sticker_row(doc, [("card.png", 0.75), ("finger.png", 0.75), ("cloud.png", 0.9), ("swoosh.png", 2.0)],
                widths=[1.3, 1.3, 1.6, 3.4], pad_top=4)

    doc.add_page_break()

    # ================= 4
    section_head(doc, 4, "Shortlisting matrix",
                 "Scored 1 to 5 together at the whiteboard — evidence first, opinions second", SAFFRON, SAFFRON_RGB)
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
        cell_margins(c, top=18, bottom=18, left=0, right=90)
        put(c, name, size=7.8, color=NAVY_RGB, align="r")
        for ci in range(SEG):
            c = cells[ci + 1]
            no_borders(c)
            cell_margins(c, top=18, bottom=18, left=0, right=0)
            put(c, "", size=2)
            shade(c, col if ci < val else "EEF2F7")
        c = cells[SEG + 1]
        no_borders(c)
        cell_margins(c, top=18, bottom=18, left=70, right=0)
        put(c, str(val), size=8.4, bold=True, color=NAVY_RGB)
        keep_row(t.rows[ri])

    gap(doc, 4)
    callout(doc, "Scoring note",
            "Initial team hypotheses, not measured results. Each option was scored 1 (low) to 5 (high) in a team "
            "meeting, evidence was cited, and the shortlist was revised twice. Any score without cited evidence "
            "drops to a 3, and the matrix is re-scored after each validation step.",
            fill=SOFT, border=LINE, kicker_rgb=SAFFRON_RGB, text_rgb=body, size=8.3)


    label(doc, "Evidence behind the scores")
    data_table(doc, ["Score", "The evidence"],
               [["Novelty 5", "No card-plus-fingerprint terminal with on-device self-healing exists in our price band."],
                ["Feasibility 5", "Every part is an off-the-shelf module; the risk is assembly time, not invention."],
                ["Affordability 5", "The bill of materials works out to roughly ₹2,450 per unit, costed from real parts."],
                ["Impact 5", "Every teacher we spoke to placed attendance in their top two daily time losses."],
                ["Prototype 4", "The 3D-printed case and parent-email templates are still being refined."]],
               [3.2, CW - 3.2], size=8.0)

    label(doc, "How the ranking moved once evidence arrived", TEAL_RGB)
    data_table(doc, ["Concept", "First → final", "What changed the score"],
               [["Astro Smart Attendance", "21 → 24", "Costed bill of materials landed near ₹2,450, under the ₹3,000 ceiling we set"],
                ["QR rotating code", "23 → 20", "A code shared on a group chat cannot be trusted for records"],
                ["Simpler digital register", "16 → 18", "Cheaper than expected, but still costs the teacher time"],
                ["Face recognition", "19 → 15", "Privacy and camera cost pulled it down after the comparison"]],
               [4.2, 2.6, CW - 6.8], size=8.0)

    gap(doc, 3)
    label(doc, "What this matrix cannot measure — a 9-point gap is not a result until a class runs it", SAFFRON_RGB)
    data_table(doc, ["Blind spot", "Why a score misses it", "What we do instead"],
               [["Trust in the room", "A row cannot show whether a teacher would let it touch the register.",
                 "We run one live period beside the register and ask the teacher afterwards."],
                ["Cost after year one", "₹2,450 is parts, not maintenance, cards or a replacement finger sensor.",
                 "We cost a three-year replacement line and say so on page 8."],
                ["The student's view", "Novelty and impact are scored by the team, not the child.",
                 "Twelve students try it and rate it 1 to 5, anonymously."]],
               [3.2, 6.6, CW - 9.8], size=8.0)

    gap(doc, 5)
    t = doc.add_table(rows=1, cols=2)
    table_layout(t, [3.3, CW - 3.3])
    c0, c1 = t.rows[0].cells
    no_borders(c0)
    cell_margins(c0, top=40, bottom=40, left=0, right=110)
    put_image(c0, asset("stamp-rejected.png"), 2.8)
    shade(c1, "FEE2E2")
    cell_borders(c1, "FCA5A5")
    cell_margins(c1, top=100, bottom=100, left=130, right=130)
    put(c1, "REJECTED — AND WE CAN SAY WHY", size=6.6, bold=True, color=RGBColor(0x99, 0x1B, 0x1B),
        track=22, space=2)
    add(c1, "Face recognition finished last at 15: a camera in every corridor, templates of children we could not "
            "guarantee to protect, and five times our budget. Speed alone could not justify it.",
        size=8.4, color=RGBColor(0x7F, 0x1D, 0x1D), before=2, line=1.24)
    keep_row(t.rows[0])

    gap(doc, 4)
    margin_note(doc, "bulb.png",
                "the row we argued about longest is the one we cut — and that is the row the matrix earned.",
                color=PLUM_RGB, img_w=0.7)

    doc.add_page_break()

    # ================= 5
    section_head(doc, 5, "Selected concept and reason",
                 "The idea we are taking into Part 2, and the honest case for why it deserves to win", TEAL, TEAL_RGB)
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
         "body": "ESP32, RC522, R307, LCD and a printed case — five parts, one week, no machining.", "accent": TEAL},
        {"title": "▤  Around 90% cheaper",
         "body": "An estimated ₹2,450 per unit against ₹30,000+ for commercial kits — within reach of any school.",
         "accent": SAFFRON},
        {"title": "◷  Measurable from day one",
         "body": "Time per class, duplicate rejection, proxy rejection, sync accuracy and teacher rating — all observable.",
         "accent": NAVY},
    ], cols=2, widths=[CW / 2, CW / 2], min_h=1.3)

    label(doc, "How a student is verified — four steps, about three seconds, two independent checks")
    card_grid(doc, [
        {"title": "1 Tap card", "body": "RFID card read at the door — who is claiming.", "accent": SAFFRON},
        {"title": "2 Press finger", "body": "R307 matches the template — is it really them.", "accent": TEAL},
        {"title": "3 AI validates", "body": "Both must agree; then period, duplicates and device health.", "accent": SAFFRON},
        {"title": "4 Confirm + alert", "body": "LCD confirms with a beep; Firebase syncs; parent emailed.", "accent": TEAL},
    ], cols=4, widths=[CW / 4] * 4, min_h=1.15)

    label(doc, "System at a glance", before=6)
    data_table(doc, ["Part", "What it does"],
               [["Controller", "ESP32 DevKit V1 — Wi-Fi, OTA updates, offline logic"],
                ["Input", "RC522 13.56 MHz reader + R307 fingerprint + school card"],
                ["Feedback", "LCD1602 I2C display + buzzer"],
                ["Cloud", "Firebase Auth + Realtime Database + Hosting"],
                ["Intelligence", "Astro AI 2.0 — 11 self-healing checks, to be proven one at a time"],
                ["Enclosure", "3D-printed case, designed in Blender"]],
               [3.2, CW - 3.2], size=7.8)

    label(doc, "What we deliberately left out — and why", before=6)
    card_grid(doc, [
        {"title": "Face recognition", "body": "A camera on children costs more trust than the speed is worth.", "tag": "REJECTED"},
        {"title": "Student phone app", "body": "Not every student owns a phone. A card works for all.", "tag": "PARKED"},
        {"title": "Full ERP replacement", "body": "Fees, exams and report cards stay out of scope.", "tag": "OUT OF SCOPE"},
        {"title": "Cloud-only design", "body": "No network, no register. The buffer comes first.", "tag": "REPLACED"},
    ], cols=4, widths=[CW / 4] * 4, min_h=1.05)

    label(doc, "Who owns which part of the build", before=6)
    data_table(doc, ["Member", "Role", "Owns", "Deliverable"],
               [["Shaurya Gupta", "Team captain", "Firmware and cloud", "Card read, Firebase, AI health checks"],
                ["Anant Tiwari", "Ideation and research", "User interviews, requirement notes", "Discovery dialogues and comparison"],
                ["Tejas Upadhyay", "Hardware integration", "Reader wiring, power, enclosure fit", "Bench tests and fault finding"],
                ["Diwakar Singh", "Product design", "3D enclosure, mounting, finish", "Printable case for the door"],
                ["Devansh Dhakad", "Testing and docs", "Test plan, stress runs, this worksheet", "A method behind every number"]],
               [3.3, 3.4, 5.1, CW - 11.8], size=7.7)

    gap(doc, 4)
    t = doc.add_table(rows=1, cols=2)
    table_layout(t, [CW - 5.6, 5.6])
    c0, c1 = t.rows[0].cells
    shade(c0, CREAM)
    cell_borders(c0, GOLD)
    cell_margins(c0, top=90, bottom=90, left=150, right=150)
    put(c0, "THE PITCH, AT THE DOOR", size=6.4, bold=True, color=RGBColor(0x92, 0x40, 0x0E), track=20, space=2)
    add(c0, "“A card and a finger. Two checks, three seconds, one entry. If the internet drops the register keeps "
            "writing and syncs when it returns, and the parent knows before the period ends. About ₹2,450 a "
            "classroom, because every part is a module we can buy locally.”",
        size=8.6, color=NAVY_RGB, font=HAND, line=1.15)
    shade(c1, WHITE)
    cell_borders(c1, LINE)
    cell_margins(c1, top=120, bottom=120, left=140, right=140)
    put(c1, "WHAT WE STILL HAVE TO EARN", size=6.4, bold=True, color=muted, track=20, space=2)
    for line in ["that a wet finger still gets a fair entry",
                 "that five students can build it in a week",
                 "that the school will say yes to one unit"]:
        add(c1, "→ " + line, size=8, color=body, before=2, line=1.2)
    keep_row(t.rows[0])

    gap(doc, 3)
    callout(doc, "What would make us drop this concept",
            "A borrowed card that gets through the finger check, a class of 30 that takes longer than two "
            "minutes, or a unit that costs more than roughly ₹3,000 once wiring and a case are counted. Any one "
            "of those sends us back to the shortlist — the matrix is not a verdict, it is a current best guess.",
            fill="FEF3C7", border="F3E0A8", kicker_rgb=RGBColor(0x92, 0x40, 0x0E), size=8.4)

    gap(doc, 3)
    label(doc, "Why this one, in the words of the matrix", TEAL_RGB, before=0)

    card_grid(doc, [
        {"title": "QR code — lost on trust", "accent": SAFFRON,
         "body": "A screenshot of a code travels further than any card. Feasible, but single-factor."},
        {"title": "Digital register — lost on proof", "accent": TEAL,
         "body": "Cheaper by ₹450 and still one factor: whoever holds the sheet writes the record."},
        {"title": "Face recognition — lost on consent", "accent": RGBColor(0xB9, 0x1C, 0x1C),
         "body": "Nine points behind: a camera in every corridor is a cost and a consent problem."},
    ], cols=3, widths=[CW / 3] * 3, min_h=0.9)

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
            cell_margins(c, top=22, bottom=22, left=100, right=100)
            put(c, val, size=7.7, bold=(i == 0), color=NAVY_RGB if i == 0 else body,
                align="r" if i == 2 else None)
        keep_row(t.rows[-1])
    # total row
    cells = t.add_row().cells
    merged = cells[0].merge(cells[1])
    shade(merged, NAVY)
    cell_borders(merged, NAVY)
    cell_margins(merged, top=90, bottom=90, left=110, right=110)
    put(merged, "EST. TOTAL", size=9, bold=True, color=white, track=14)
    add(merged, "one classroom terminal, assembled and tested", size=7.2,
        color=RGBColor(0xBF, 0xDB, 0xFE), before=1)
    tc = cells[2]
    shade(tc, NAVY)
    cell_borders(tc, NAVY)
    cell_margins(tc, top=90, bottom=90, left=100, right=110)
    put(tc, "≈ ₹2,450", size=12, bold=True, color=RGBColor(0xFF, 0xB7, 0x03), align="r")

    margin_note(doc, "arrow-teal.png",
                "the sensor is 39% of the build — the honest price of two factors.",
                color=RGBColor(0x0F, 0x76, 0x6E), img_w=1.7, side="left")

    label(doc, "What the LCD will show in each case", before=6)
    lcd(doc, [("PRESENT", "Aarav S. ·  IX-B", "card recognised inside the period", RGBColor(0x34, 0xD3, 0x99)),
              ("ALREADY MARKED", "Aarav S. ·  08:12", "duplicate tap in the same period", RGBColor(0xFB, 0xBF, 0x24)),
              ("CARD NOT FOUND", "please see office", "unknown or unenrolled card", RGBColor(0xF8, 0x71, 0x71))])

    label(doc, "Against the two nearest alternatives")
    data_table(doc, ["Criterion", "Our concept", "QR code on a screen", "Digital register on a tablet"],
               [["Cost per classroom", "≈ ₹2,450", "₹0 hardware, ≈ ₹400 data", "₹12,000+ tablet"],
                ["Works without internet", "Yes — local buffer", "No, needs the app online", "Partly, if the app caches"],
                ["Proxy risk", "Very low — card + finger", "High — a screenshot travels", "Medium — a login can be shared"],
                ["Needs a student phone", "No", "Yes", "No"],
                ["Teacher effort", "Confirm exceptions only", "None until the report", "The whole period, typing"],
                ["Parent alert", "Automatic email", "Possible, if online", "Manual or not at all"]],
               [3.9, 4.1, 4.5, CW - 12.5], size=7.1)

    gap(doc, 5)
    label(doc, "The three questions the sketch still cannot answer", NAVY_RGB)
    card_grid(doc, [
        {"title": "Where does the box live?", "accent": SAFFRON,
         "body": "A door frame, a desk or a corridor wall — it decides cable length, power and whether the overflow "
                 "at the bell needs a second reader."},
        {"title": "Who enrols the finger?", "accent": TEAL,
         "body": "One teacher, one afternoon, written consent per child. An enrolment is a template, not a photo."},
        {"title": "What happens on a power cut?", "accent": GREEN,
         "body": "The buffer holds entries in memory, not a dead battery. A small UPS keeps the register alive for "
                 "one period."},
    ], cols=3, widths=[CW / 3] * 3, min_h=1.1)

    gap(doc, 4)
    callout(doc, "What the school has to give us — and what it does not",
            "One door, one socket, one teacher's afternoon. No server, no subscription, no phone per student "
            "and no cable at the door — the box buffers and syncs later.",
            fill=CREAM, border=GOLD, size=8.2)

    gap(doc, 4)
    callout(doc, "The block the school owns is the human one",
            "Five hardware blocks, one human: a teacher's override is the only way an entry is marked unverified, "
            "and that exception is written into the log rather than rubbed out of a register.",
            fill=SOFT, border=LINE, kicker_rgb=TEAL_RGB, text_rgb=body, size=8.4)

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
               [4.1, 6.0, CW - 10.1], size=7.6, head_fill="C2410C")
    margin_note(doc, "bulb.png", "a task is not a test until it says what would change your mind.",
                img_w=1.0, side="left")

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
        {"title": "⚑  Duplicate scan rejection", "body": "Same card twice in one period is refused, even with the right finger.", "tag": "TARGET 100%", "tag_color": TEAL_RGB, "accent": NAVY},
        {"title": "✓  Late and invalid handling", "body": "Late arrivals flagged; unknown or wrong-period cards rejected.", "tag": "TARGET CORRECTLY FLAGGED", "tag_color": TEAL_RGB, "accent": TEAL},
        {"title": "≋  Offline → online sync", "body": "Entries stored locally then synced when Wi-Fi returns, with no loss.", "tag": "TARGET 100% ACCURATE", "tag_color": TEAL_RGB, "accent": TEAL},
        {"title": "◉  Teacher usability", "body": "Teachers rate setup, the confirmation step and dashboard clarity.", "tag": "TARGET 4+ OUT OF 5", "tag_color": TEAL_RGB, "accent": GREEN},
        {"title": "⚿  Proxy attempt rejected", "body": "An enrolled card with a different finger must never write an entry.", "tag": "TARGET 100%", "tag_color": TEAL_RGB, "accent": NAVY},
    ], cols=3, widths=[CW / 3] * 3, min_h=1.35)

    label(doc, "Baseline against prototype", TEAL_RGB, before=4)
    data_table(doc, ["Measure", "Baseline (paper)", "Target (prototype)"],
               [["Time for 30 students", "10–15 min, teacher-driven", "< 90 s"],
                ["Duplicate entries", "Common and unnoticed", "Rejected 100%"],
                ["Late-arrival record", "Written by hand", "Flagged with a timestamp"],
                ["Parent notification", "Same day if at all", "Within 5 minutes"],
                ["Records after a Wi-Fi cut", "Not applicable", "Buffered, then synced"],
                ["Evidence for an audit", "None", "Timestamped log per tap"]],
               [5.6, 5.2, CW - 10.8], size=7.8)

    gap(doc, 2)
    label(doc, "How each number gets taken", TEAL_RGB, before=0)
    data_table(doc, ["Indicator", "Instrument", "Recorded in"],
               [["Time for 30 students", "Stopwatch: first tap to thirtieth", "Lab notebook, page per trial"],
                ["Proxy rejection", "Borrowed card, wrong finger, 10 tries", "Firebase log, screenshot per run"],
                ["Offline sync", "Wi-Fi off mid-period, then back", "Entry count before and after"]],
               [4.4, 6.6, CW - 11.0], size=7.9)

    margin_note(doc, "swoosh.png",
                "a target is a promise we have not kept yet — that is why it is written down.",
                color=PLUM_RGB, img_w=1.3)


    gap(doc, 2)
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
                ["Hardware failure in class", "Astro AI 2.0 is specified to run 11 self-healing checks, a watchdog to restart the board, error codes on the LCD, modular parts."],
                ["Cost, scale and maintenance", "An estimated ₹2,450 per unit, common parts, a printable case and a free cloud tier — one unit per room is realistic."]],
               [4.4, CW - 4.4], size=7.9)

    label(doc, "What would make us abandon this idea")
    data_table(doc, ["We abandon if…", "…because"],
               [["30 taps slower than two minutes", "the terminal loses to a paper register"],
                ["A unit above roughly ₹3,000", "it stops being a school solution"],
                ["Any proxy that beats the two factors", "the extra sensor earns its place or it goes"],
                ["Templates we cannot store safely", "no biometric data, no fingerprint stage"]],
               [CW / 2, CW / 2], size=8.2, head_fill="B91C1C")

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
            "has a test behind it, and every test is one a Class 9 team can run.",
            fill=NAVY, border=NAVY, kicker_rgb=RGBColor(0xFF, 0xB7, 0x03),
            text_rgb=RGBColor(0xDC, 0xE7, 0xF8))

    label(doc, "Before submission — our own checklist")
    card_grid(doc, [
        {"title": "✓  All nine sections answered"},
        {"title": "✓  Names, roles and mentor verified"},
        {"title": "✓  Numbers marked measured or hypothesis"},
        {"title": "✓  Every part bench-tested before the pilot"},
        {"title": "✓  Two products compared with sources"},
        {"title": "✓  Fingerprint consent taken from parents"},
        {"title": "✓  Worksheet signed and dated"},
    ], cols=3, widths=[CW / 3] * 3, min_h=0.85)

    gap(doc, 4)
    t = doc.add_table(rows=1, cols=1)
    table_layout(t, [CW])
    c = t.rows[0].cells[0]
    shade(c, CREAM)
    cell_borders(c, GOLD)
    cell_margins(c, top=100, bottom=100, left=150, right=150)
    put(c, "IN ONE SENTENCE, FOR THE JURY", size=6.6, bold=True, color=RGBColor(0x92, 0x40, 0x0E),
        track=22, space=2)
    add(c, "Two factors at the door, a buffer that outlasts the Wi-Fi, and an estimated ₹2,450 a classroom — "
           "built by five of us, tested in one room, honest about every number not yet measured.",
        size=8.4, color=NAVY_RGB, font=HAND, before=2, line=1.18)


    gap(doc, 7)
    gap(doc, 3)
    callout(doc, "Before this leaves the room — each claim has a name against it",
            "Devansh signs off that every section is answered rather than headed; Shaurya, that every number is "
            "marked measured or hypothesis; Tejas, that every claim can be shown on one bench; Diwakar, that the "
            "build fits inside ₹3,000 and one week.",
            fill=SOFT, border=LINE, kicker_rgb=NAVY_RGB, text_rgb=body, size=8.0)

    gap(doc, 3)
    signature_row(doc, [("Shaurya Gupta", "TEAM CAPTAIN"),
                        ("Dr. Jayesh Shinde", "MENTOR"),
                        ("25 November 2026", "DATE ·  RENUKOOT, U.P.")])

    gap(doc, 6)
    t = doc.add_table(rows=1, cols=1)
    table_layout(t, [CW])
    c = t.rows[0].cells[0]
    shade(c, NAVY)
    no_borders(c)
    cell_margins(c, top=130, bottom=130, left=160, right=160)
    put(c, "SUBMITTED TO ABG STEM QUEST 2026–27  ·  PART 1 OF 2", size=6.6, bold=True,
        color=RGBColor(0xFF, 0xB7, 0x03), track=26, space=2)
    add(c, "Theme SDG 9 — Industry, Innovation and Infrastructure   ·   Sun Rises India, Class 9   ·   "
           "The Aditya Birla Public School, Renukoot, Sonbhadra (U.P.)",
        size=8.2, color=RGBColor(0xC9, 0xD8, 0xEE), before=3, line=1.24)

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
