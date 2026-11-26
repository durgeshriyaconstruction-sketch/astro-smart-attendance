#!/usr/bin/env python3
"""
Renders an approximate visual preview of the DOCX (PNG per page) so the design
can be reviewed without Word. Colours, block order and text wrapping are drawn
from the real document XML; exact Word metrics are not reproduced.
"""
import os
import sys

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCX = os.path.join(HERE, "Creative-Ideation-Worksheet-Astro-Smart-Attendance.docx")
OUTDIR = os.path.join(HERE, ".preview")
DPI = 96
CM = DPI / 2.54
MARGIN_L = 1.7 * CM
MARGIN_R = 1.7 * CM
MARGIN_T = 1.7 * CM
MARGIN_B = 1.6 * CM
PAGE_W = int(21.0 * CM)
PAGE_H = int(29.7 * CM)
USABLE_W = PAGE_W - MARGIN_L - MARGIN_R

FONT_PATHS = [
    "/home/user/fonts/Inter-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
BOLD_PATHS = [
    "/home/user/fonts/Poppins-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
import glob
if not os.path.exists(FONT_PATHS[0]):
    FONT_PATHS[0] = (glob.glob("/usr/share/fonts/**/DejaVuSans.ttf", recursive=True) or ["/dev/null"])[0]
if not os.path.exists(BOLD_PATHS[0]):
    BOLD_PATHS[0] = (glob.glob("/usr/share/fonts/**/DejaVuSans-Bold.ttf", recursive=True) or ["/dev/null"])[0]

_fonts = {}
_DOC = [None]


def font(size, bold=False):
    key = (round(size), bold)
    if key not in _fonts:
        path = BOLD_PATHS[0] if bold else FONT_PATHS[0]
        try:
            _fonts[key] = ImageFont.truetype(path, max(6, int(round(size))))
        except Exception:
            _fonts[key] = ImageFont.load_default()
    return _fonts[key]


def norm_hex(v, default="FFFFFF"):
    if not v:
        return "#" + default
    v = v.replace("#", "")
    if len(v) == 3:
        v = "".join(ch * 2 for ch in v)
    if len(v) != 6:
        return "#" + default
    return "#" + v


def tc_fill(tc):
    tcPr = tc.find(qn("w:tcPr"))
    if tcPr is None:
        return None
    shd = tcPr.find(qn("w:shd"))
    return shd.get(qn("w:fill")) if shd is not None else None


def tc_borders(tc):
    tcPr = tc.find(qn("w:tcPr"))
    if tcPr is None:
        return None
    b = tcPr.find(qn("w:tcBorders"))
    if b is None:
        return None
    top = b.find(qn("w:top"))
    if top is None:
        return None
    if top.get(qn("w:val")) == "nil":
        return "none"
    return top.get(qn("w:color"))


def tc_left(tc):
    tcPr = tc.find(qn("w:tcPr"))
    if tcPr is None:
        return None
    b = tcPr.find(qn("w:tcBorders"))
    if b is None:
        return None
    left = b.find(qn("w:left"))
    if left is None:
        return None
    sz = int(left.get(qn("w:sz")) or 0)
    if sz >= 12:
        return left.get(qn("w:color"))
    return None


def para_runs(p):
    out = []
    for r in p.runs:
        if not r.text:
            continue
        size = r.font.size.pt if r.font.size else 9.5
        color = r.font.color.rgb if (r.font.color and r.font.color.rgb) else None
        out.append((r.text, size, bool(r.font.bold), "#" + str(color) if color else None))
    return out


def wrap(draw, runs, width):
    """Greedy wrap across runs; returns list of lines, each a list of (text,size,bold,color)."""
    words = []
    for text, size, bold, color in runs:
        for i, chunk in enumerate(text.split(" ")):
            words.append((chunk, size, bold, color))
    lines, cur, cur_w = [], [], 0.0
    for word, size, bold, color in words:
        w = draw.textlength(word + " ", font=font(size, bold))
        if cur_w + w > width and cur:
            lines.append(cur)
            cur, cur_w = [], 0.0
        cur.append((word + " ", size, bold, color))
        cur_w += w
    if cur:
        lines.append(cur)
    return lines


def cell_images(cell):
    """Return (rId, width_em) for inline pictures in a cell."""
    out = []
    for blip in cell._tc.iter(qn("a:blip")):
        rid = blip.get(qn("r:embed"))
        if rid:
            out.append(rid)
    return out


def draw_cell(draw, cell, x, y, w, h, doc=None, img=None):
    fill = tc_fill(cell._tc)
    border = tc_borders(cell._tc)
    left = tc_left(cell._tc)
    if border != "none":
        draw.rectangle([x, y, x + w, y + h],
                       fill=norm_hex(fill) if fill else None,
                       outline=norm_hex(border) if border else "#D8DEE9")
    elif fill:
        draw.rectangle([x, y, x + w, y + h], fill=norm_hex(fill))
    if left:
        draw.rectangle([x, y, x + 3, y + h], fill=norm_hex(left))

    # inline pictures sit on their own line inside the cell
    pic_h = 0
    if doc is not None:
        for rid in cell_images(cell):
            try:
                part = doc.part.related_parts[rid]
                import io
                im = Image.open(io.BytesIO(part.blob)).convert("RGBA")
                maxw = int(w - 6)
                if im.width > maxw:
                    im = im.resize((maxw, int(im.height * maxw / im.width)), Image.LANCZOS)
                px = int(x + (w - im.width) / 2)
                if img is not None:
                    img.paste(im, (px, int(y + 3)), im)
                pic_h = max(pic_h, im.height)
            except Exception:
                pass

    pad = 5
    ty = y + 4 + pic_h
    for p in cell.paragraphs:
        runs = para_runs(p)
        if not runs:
            ty += 4
            continue
        size = runs[0][1]
        lines = wrap(draw, runs, w - pad * 2)
        align_c = p.alignment is not None and "CENTER" in str(p.alignment)
        for ln in lines:
            total = sum(draw.textlength(t, font=font(s, b)) for t, s, b, _ in ln)
            lx = x + (w - total) / 2 if align_c else x + pad
            for t, s, b, c in ln:
                draw.text((lx, ty), t, font=font(s, b), fill=c or "#334155")
                lx += draw.textlength(t, font=font(s, b))
            ty += size * 1.28
        ty += 1
    return ty


def table_size(table):
    widths = []
    grid = table._tbl.find(qn("w:tblGrid"))
    if grid is not None:
        widths = [int(gc.get(qn("w:w"))) / 567 * CM for gc in grid.findall(qn("w:gridCol"))]
    if not widths or abs(sum(widths) - USABLE_W) > 12:
        widths = [USABLE_W / len(table.columns)] * len(table.columns)
    heights = []
    for row in table.rows:
        h = 0
        for i, cell in enumerate(row.cells):
            w = widths[i] if i < len(widths) else USABLE_W / len(row.cells)
            probe = Image.new("RGB", (10, 10))
            d = ImageDraw.Draw(probe)
            hh = 8
            for ext in cell._tc.iter(qn("wp:extent")):
                hh += int(ext.get("cy")) / 360000 * CM
            for p in cell.paragraphs:
                runs = para_runs(p)
                if not runs:
                    hh += 4
                    continue
                size = runs[0][1]
                hh += len(wrap(d, runs, w - 12)) * size * 1.28 + 1
            h = max(h, hh)
        trPr = row._tr.find(qn("w:trPr"))
        if trPr is not None:
            trh = trPr.find(qn("w:trHeight"))
            if trh is not None:
                h = max(h, int(trh.get(qn("w:val"))) / 567 * CM)
        heights.append(h)
    return widths, heights


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    doc = Document(DOCX)
    _DOC[0] = doc
    pages, page, y = [], Image.new("RGB", (PAGE_W, PAGE_H), "white"), MARGIN_T
    draw = ImageDraw.Draw(page)

    for block in doc.element.body.iterchildren():
        if block.tag == qn("w:p"):
            p = Paragraph(block, doc)
            if any(br.get(qn("w:type")) == "page" for br in block.iter(qn("w:br"))):
                pages.append(page)
                page = Image.new("RGB", (PAGE_W, PAGE_H), "white")
                draw = ImageDraw.Draw(page)
                y = MARGIN_T
                continue
            runs = para_runs(p)
            if not runs:
                y += 4
                continue
            size = runs[0][1]
            lines = wrap(draw, runs, USABLE_W)
            for ln in lines:
                lx = MARGIN_L
                for t, s, b, c in ln:
                    draw.text((lx, y), t, font=font(s * 1.05, b), fill=c or "#334155")
                    lx += draw.textlength(t, font=font(s * 1.05, b))
                y += size * 1.34
            y += 3
        elif block.tag == qn("w:tbl"):
            table = Table(block, doc)
            widths, heights = table_size(table)
            for ri, row in enumerate(table.rows):
                h = heights[ri]
                x = MARGIN_L
                for ci, cell in enumerate(row.cells):
                    w = widths[ci] if ci < len(widths) else USABLE_W / len(row.cells)
                    draw_cell(draw, cell, x, y, w, h, _DOC[0], page)
                    x += w
                y += h
            y += 2
            if y > PAGE_H - MARGIN_B:
                pages.append(page)
                page = Image.new("RGB", (PAGE_W, PAGE_H), "white")
                draw = ImageDraw.Draw(page)
                y = MARGIN_T
    pages.append(page)

    for i, im in enumerate(pages, 1):
        draw = ImageDraw.Draw(im)
        draw.text((MARGIN_L, 20), "ABG STEM QUEST 2026-27   ·   PART 1 — CREATIVE IDEATION WORKSHEET",
                  font=font(8, True), fill="#0B1F4A")
        draw.line([(MARGIN_L, 34), (PAGE_W - MARGIN_R, 34)], fill="#E2E8F0")
        draw.line([(MARGIN_L, PAGE_H - 40), (PAGE_W - MARGIN_R, PAGE_H - 40)], fill="#E2E8F0")
        draw.text((MARGIN_L, PAGE_H - 34), "ASTRO SMART ATTENDANCE · Sun Rises India · ABPS Renukoot · SDG 9",
                  font=font(7), fill="#64748B")
        draw.text((PAGE_W - MARGIN_R - 40, PAGE_H - 34), f"Page {i}", font=font(7), fill="#64748B")
        im.save(os.path.join(OUTDIR, f"page{i}.png"))
    print(f"rendered {len(pages)} preview pages into {OUTDIR}")


if __name__ == "__main__":
    main()
