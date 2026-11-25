#!/usr/bin/env python3
"""
Estimates the printed height of each page of the DOCX, so a section that would
spill onto a second page is caught before it reaches Word.

Word paginates for real; this is a conservative approximation (text width per
line, line height, cell padding, minimum row heights) used as a build check.
"""
import math
import os
import sys

from docx import Document
from docx.shared import Pt
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml.ns import qn

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCX = os.path.join(HERE, "Creative-Ideation-Worksheet-Astro-Smart-Attendance.docx")

PAGE_H = 29.7 - 1.7 - 1.6          # cm of usable height
CM_TO_PT = 28.35
BODY_W = 17.6                       # cm


def iter_blocks(doc):
    body = doc.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, doc)
        elif child.tag == qn("w:tbl"):
            yield Table(child, doc)


def para_height(p):
    """Approximate rendered height of a paragraph, in points."""
    text = p.text
    size = 9.5
    for r in p.runs:
        if r.font.size:
            size = r.font.size.pt
            break
    if not text.strip():
        return (p.paragraph_format.space_after.pt if p.paragraph_format.space_after else 0) + \
               (p.paragraph_format.space_before.pt if p.paragraph_format.space_before else 0)
    # average glyph width ≈ 0.50 em for Calibri at these sizes
    width_pt = BODY_W * CM_TO_PT
    per_line = max(10, int(width_pt / (size * 0.50)))
    lines = max(1, math.ceil(len(text) / per_line))
    before = p.paragraph_format.space_before.pt if p.paragraph_format.space_before else 0
    after = p.paragraph_format.space_after.pt if p.paragraph_format.space_after else 0
    return lines * size * 1.22 + before + after


def cell_height(cell, width_cm):
    h = 0.0
    for p in cell.paragraphs:
        text = p.text
        size = 9.0
        for r in p.runs:
            if r.font.size:
                size = r.font.size.pt
                break
        per_line = max(4, int(width_cm * CM_TO_PT / (size * 0.50)))
        lines = max(1, math.ceil(len(text) / per_line)) if text.strip() else 0
        before = p.paragraph_format.space_before.pt if p.paragraph_format.space_before else 0
        after = p.paragraph_format.space_after.pt if p.paragraph_format.space_after else 0
        h += lines * size * 1.22 + before + after
    # default cell padding: 60 twips top + 60 bottom = 6pt, plus a little slack
    return h + 7.5


def table_height(t):
    total = 0.0
    # column widths from tblGrid
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
                h = max(h, int(trh.get(qn("w:val"))) / 567 * CM_TO_PT)
        total += h
    return total


def main():
    doc = Document(DOCX)
    usable = PAGE_H * CM_TO_PT
    page, used = 1, 0.0
    report = []
    for block in iter_blocks(doc):
        if isinstance(block, Paragraph):
            page_break = any(br.get(qn("w:type")) == "page"
                             for br in block._p.iter(qn("w:br")))
            if page_break:
                report.append((page, used))
                page += 1
                used = 0.0
                continue
            used += para_height(block)
        else:
            used += table_height(block)

    report.append((page, used))
    print(f"usable height per page: {usable:.0f} pt  ({PAGE_H:.1f} cm)\n")
    worst = 0
    for i, h in report:
        fill = h / usable * 100
        flag = "  <-- overflows" if fill > 100 else ("  (tight)" if fill > 97 else "")
        print(f"  page {i}: {h:6.0f} pt   {fill:5.1f}% full{flag}")
        if fill > 100:
            worst += 1
    print(f"\n{len(report)} pages, {worst} overflowing")
    return 1 if worst else 0


if __name__ == "__main__":
    sys.exit(main())
