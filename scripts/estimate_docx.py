#!/usr/bin/env python3
"""
Estimates the printed height of each page of the DOCX, so a section that would
spill onto a second page is caught before it reaches Word.

Text is measured with Carlito (metric-compatible with Calibri) at 96 dpi, so the
line breaks match what Word produces. Line height, cell padding and minimum row
heights mirror the Word defaults the builder uses.
"""
import os
import sys

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml.ns import qn
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCX = os.path.join(HERE, "Creative-Ideation-Worksheet-Astro-Smart-Attendance.docx")

DPI = 96
PX_PT = DPI / 72.0                  # pixels per point
PAGE_H = 29.7 - 1.7 - 1.6           # cm of usable height
USABLE_PT = PAGE_H * 28.35          # ≈ 748 pt
USABLE_PX = USABLE_PT * PX_PT
BODY_W = 17.6                       # cm

FONTS = {
    False: "/home/user/fonts/Carlito-Regular.ttf",
    True: "/home/user/fonts/Carlito-Bold.ttf",
}
_cached = {}
_draw = ImageDraw.Draw(Image.new("RGB", (8, 8)))


def font(size_pt, bold=False):
    key = (round(size_pt, 1), bold)
    if key not in _cached:
        try:
            _cached[key] = ImageFont.truetype(FONTS[bold], max(6, int(round(size_pt * PX_PT))))
        except Exception:
            _cached[key] = ImageFont.load_default()
    return _cached[key]


def iter_blocks(doc):
    for child in doc.element.body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, doc)
        elif child.tag == qn("w:tbl"):
            yield Table(child, doc)


def para_runs(p):
    out = []
    for r in p.runs:
        if not r.text:
            continue
        size = r.font.size.pt if r.font.size else 9.5
        out.append((r.text, size, bool(r.font.bold)))
    return out


def wrap_count(runs, width_px):
    """Number of rendered lines for a run list inside width_px."""
    if not runs:
        return 0
    words = []
    for text, size, bold in runs:
        words += [(w, size, bold) for w in text.split(" ")]
    lines, cur_w = 1, 0.0
    for word, size, bold in words:
        w = _draw.textlength(word + " ", font=font(size, bold))
        if cur_w + w > width_px and cur_w > 0:
            lines += 1
            cur_w = 0.0
        cur_w += w
    return lines


def line_px(size):
    return size * PX_PT * 1.22          # Word's single spacing for Calibri


def para_height(p, width_cm=BODY_W):
    w_px = width_cm * 28.35 * PX_PT
    pf = p.paragraph_format
    before = pf.space_before.pt if pf.space_before else 0
    after = pf.space_after.pt if pf.space_after else 0
    runs = para_runs(p)
    if not runs:
        return (before + after) * PX_PT
    size = runs[0][1]
    return wrap_count(runs, w_px) * line_px(size) + (before + after) * PX_PT


def cell_pad(cell):
    """Vertical cell padding (top + bottom), in pixels, from w:tcMar."""
    tcPr = cell._tc.find(qn("w:tcPr"))
    top = bottom = 60                    # Word default 60 twips each
    if tcPr is not None:
        mar = tcPr.find(qn("w:tcMar"))
        if mar is not None:
            for edge, val in (("top", "top"), ("bottom", "bottom")):
                el = mar.find(qn("w:" + edge))
                if el is not None and el.get(qn("w:w")):
                    if edge == "top":
                        top = int(el.get(qn("w:w")))
                    else:
                        bottom = int(el.get(qn("w:w")))
    return (top + bottom) / 20.0 * PX_PT


def cell_height(cell, width_cm):
    h = 0.0
    for ext in cell._tc.iter(qn("wp:extent")):
        h += int(ext.get("cy")) / 360000 * 28.35 * PX_PT
    for p in cell.paragraphs:
        runs = para_runs(p)
        if not runs:
            h += 4
            continue
        h += wrap_count(runs, width_cm * 28.35 * PX_PT - 12) * line_px(runs[0][1]) + 1
    return h + cell_pad(cell)


def table_height(t):
    total = 0.0
    grid = t._tbl.find(qn("w:tblGrid"))
    widths = [int(gc.get(qn("w:w"))) / 567 for gc in grid.findall(qn("w:gridCol"))] if grid is not None else []
    for row in t.rows:
        h = 0.0
        for i, cell in enumerate(row.cells):
            w = widths[i] if i < len(widths) else BODY_W / max(1, len(row.cells))
            h = max(h, cell_height(cell, w))
        trPr = row._tr.find(qn("w:trPr"))
        if trPr is not None:
            trh = trPr.find(qn("w:trHeight"))
            if trh is not None:
                h = max(h, int(trh.get(qn("w:val"))) / 567 * 28.35 * PX_PT)
        total += h
    return total


def main():
    doc = Document(DOCX)
    page, used = 1, 0.0
    report = []
    for block in iter_blocks(doc):
        if isinstance(block, Paragraph):
            if any(br.get(qn("w:type")) == "page" for br in block._p.iter(qn("w:br"))):
                report.append((page, used))
                page += 1
                used = 0.0
                continue
            used += para_height(block)
        else:
            used += table_height(block)

    report.append((page, used))
    print(f"usable height per page: {USABLE_PT:.0f} pt  ({PAGE_H:.1f} cm)\n")
    worst = 0
    for i, h in report:
        pt = h / PX_PT
        fill = h / USABLE_PX * 100
        flag = "  <-- overflows" if fill > 100 else ("  (tight)" if fill > 97 else "")
        print(f"  page {i}: {pt:6.0f} pt   {fill:5.1f}% full{flag}")
        if fill > 100:
            worst += 1
    print(f"\n{len(report)} pages, {worst} overflowing")
    return 1 if worst else 0


if __name__ == "__main__":
    sys.exit(main())
