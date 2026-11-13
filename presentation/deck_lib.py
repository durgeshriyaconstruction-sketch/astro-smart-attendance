"""
ASTRO SMART ATTENDANCE - presentation design system.

A small, dependency-light toolkit on top of python-pptx so the whole deck is
generated from data instead of hand-placed shapes.  Every colour, size and
margin lives here; the slide content lives in build_deck.py.

Palette is the project's own (taken from the repository's 3D viewer), so the
deck and the engineering deliverables look like one product.
"""
import os

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn

# --------------------------------------------------------------------- canvas
SW, SH = 13.333, 7.5          # 16:9 inches
ML, MR = 0.62, 0.62           # side margins
CW = SW - ML - MR             # content width 12.093

# --------------------------------------------------------------------- palette
NAVY    = RGBColor(0x0E, 0x10, 0x14)
PANEL   = RGBColor(0x17, 0x1A, 0x21)
PANEL2  = RGBColor(0x1E, 0x22, 0x2B)
PANEL3  = RGBColor(0x25, 0x2A, 0x35)
LINE    = RGBColor(0x2C, 0x32, 0x3E)
WHITE   = RGBColor(0xF4, 0xF6, 0xFA)
SOFT    = RGBColor(0xC8, 0xD0, 0xDE)
DIM     = RGBColor(0x9A, 0xA1, 0xB1)
FAINT   = RGBColor(0x60, 0x68, 0x78)
AMBER   = RGBColor(0xFF, 0xCD, 0x50)
CYAN    = RGBColor(0x78, 0xDC, 0xFF)
GREEN   = RGBColor(0x8F, 0xE0, 0xA8)
MAGENTA = RGBColor(0xF0, 0xA8, 0xD8)
RED     = RGBColor(0xFF, 0x7A, 0x7A)
ORANGE  = RGBColor(0xF2, 0x9E, 0x4B)

FONT = "Segoe UI"
MONO = "Consolas"

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def A(name):
    return os.path.join(ASSETS, name + ".png")


# -- text measurement ------------------------------------------------------
# DejaVu is ~8 % wider than Segoe UI at the same point size, so measuring with
# it means "fits here" implies "fits in PowerPoint".  Used to auto-shrink
# headlines and to keep authored text inside its box.
_FP = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
_FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_font_cache = {}


def _pil_font(bold):
    key = bool(bold)
    if key not in _font_cache:
        from PIL import ImageFont
        try:
            _font_cache[key] = ImageFont.truetype(_FP if bold else _FR, 100)
        except Exception:
            _font_cache[key] = None
    return _font_cache[key]


def text_width(s, size_pt, bold=False, spc=0):
    """width in inches of a single line at a given point size.
    `spc` is letter spacing in 1/100 pt, as PowerPoint applies it."""
    f = _pil_font(bold)
    if f is None:
        base = len(s) * size_pt * 0.0072
    else:
        base = f.getlength(s) / 100.0 * size_pt / 72.0
    return base + len(s) * (spc / 100.0) / 72.0


def wrap_count(s, size_pt, w, bold=False, spc=0):
    """how many lines this string needs inside w inches"""
    f = _pil_font(bold)
    if f is None:
        return 1
    per = max(0.10, w)
    total = 0
    for raw in s.split("\n"):
        words, cur = raw.split(" "), ""
        lines = 1
        for word in words:
            trial = word if not cur else cur + " " + word
            if text_width(trial, size_pt, bold, spc) <= per or not cur:
                cur = trial
            else:
                lines += 1
                cur = word
        total += lines
    return total


def fit_size(s, size, w, min_size=16, safety=0.975, spc=0):
    """largest size <= size that puts s on one line inside w inches.
    The safety factor absorbs renderer/rounding differences between DejaVu
    (what we measure with) and Segoe UI (what PowerPoint draws with)."""
    while size > min_size and text_width(s, size, True, spc) > w * safety:
        size -= 0.5
    return size



# --------------------------------------------------------------------- basics
def _noline(sh):
    sh.line.fill.background()
    return sh


def _noshadow(sh):
    try:
        sh.shadow.inherit = False
    except Exception:
        pass
    return sh


def rect(slide, x, y, w, h, fill=PANEL, line=None, lw=1.0, radius=None,
         shape=None):
    if shape is None:
        shape = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    sh = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    _noshadow(sh)
    if radius and shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        try:
            sh.adjustments[0] = radius
        except Exception:
            pass
    if fill is None:
        sh.fill.background()
    else:
        sh.fill.solid()
        sh.fill.fore_color.rgb = fill
    if line is None:
        _noline(sh)
    else:
        sh.line.color.rgb = line
        sh.line.width = Pt(lw)
    sh.text_frame.word_wrap = True
    return sh


def hline(slide, x, y, w, color=LINE, lw=1.0):
    sh = slide.shapes.add_connector(1, Inches(x), Inches(y), Inches(x + w), Inches(y))
    sh.line.color.rgb = color
    sh.line.width = Pt(lw)
    return sh


def vline(slide, x, y, h, color=LINE, lw=1.0):
    sh = slide.shapes.add_connector(1, Inches(x), Inches(y), Inches(x), Inches(y + h))
    sh.line.color.rgb = color
    sh.line.width = Pt(lw)
    return sh


def _spacing(run, spc):
    """letter spacing in 1/100 pt, via raw XML (python-pptx has no API)."""
    if spc:
        run.font._rPr.set("spc", str(int(spc)))


def tb(slide, x, y, w, h, anchor=MSO_ANCHOR.TOP, margins=(0, 0, 0, 0)):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = Inches(margins[0])
    tf.margin_right = Inches(margins[1])
    tf.margin_top = Inches(margins[2])
    tf.margin_bottom = Inches(margins[3])
    return box


def para(tf, text, size=14, color=WHITE, bold=False, italic=False, font=FONT,
         align=PP_ALIGN.LEFT, space_before=0, space_after=0, line=1.25,
         first=False, spc=0, caps=False):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align
    p.space_before = Pt(space_before)
    p.space_after = Pt(space_after)
    p.line_spacing = line
    r = p.add_run()
    r.text = text.upper() if caps else text
    f = r.font
    f.name = font
    f.size = Pt(size)
    f.bold = bold
    f.italic = italic
    f.color.rgb = color
    _spacing(r, spc)
    return p


def rich(tf, parts, size=14, color=WHITE, align=PP_ALIGN.LEFT, space_before=0,
         space_after=0, line=1.25, first=False, font=FONT):
    """parts = [(text, {bold:True, color:RGB, size:12, font:'Consolas'}), ...]"""
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align
    p.space_before = Pt(space_before)
    p.space_after = Pt(space_after)
    p.line_spacing = line
    for text, st in parts:
        r = p.add_run()
        r.text = text
        f = r.font
        f.name = st.get("font", font)
        f.size = Pt(st.get("size", size))
        f.bold = st.get("bold", False)
        f.italic = st.get("italic", False)
        f.color.rgb = st.get("color", color)
    return p


def text(slide, x, y, w, h, s, size=14, color=WHITE, bold=False, italic=False,
         align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, font=FONT, line=1.25,
         caps=False, spc=0):
    box = tb(slide, x, y, w, h, anchor=anchor)
    lines = s.split("\n")
    for i, ln in enumerate(lines):
        para(box.text_frame, ln, size=size, color=color, bold=bold, italic=italic,
             align=align, first=(i == 0), line=line, font=font, caps=caps, spc=spc)
    return box


# ------------------------------------------------------------------ furniture
def bg(slide, color=NAVY):
    r = rect(slide, 0, 0, SW, SH, fill=color)
    r.shadow.inherit = False
    # push to back
    sp = r._element
    sp.getparent().remove(sp)
    slide.shapes._spTree.insert(2, sp)
    return r


def grid_texture(slide, color=RGBColor(0x17, 0x1B, 0x22), step=0.5, alpha=True):
    """faint engineering grid - drawn as thin rules, very low contrast"""
    y = step
    while y < SH:
        hline(slide, 0, round(y, 3), SW, color=color, lw=0.5)
        y += step
    x = step
    while x < SW:
        vline(slide, round(x, 3), 0, SH, color=color, lw=0.5)
        x += step


def slide_new(prs, bgcolor=NAVY):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bg(s, bgcolor)
    return s


def eyebrow(slide, s, x=ML, y=0.44, color=AMBER, w=8.0):
    text(slide, x, y, w, 0.22, s, size=9.5, color=color, bold=True, caps=True, spc=220)


def table_h(rows, col_w, row_h, size=10, head_size=9, min_row=0.0):
    """the height PowerPoint will really give a table: it grows a row when the
    text inside it needs more lines than the nominal row height allows."""
    total = 0.0
    for i, row in enumerate(rows):
        need = row_h
        sz = head_size if i == 0 else size
        for j, val in enumerate(row):
            inner = col_w[j] - 0.16
            n = wrap_count(str(val), sz, inner, bold=(i == 0))
            need = max(need, n * sz / 72.0 * 1.18 + 0.08)
        total += max(need, min_row)
    return total


def title(slide, s, y=0.70, size=30, color=WHITE, w=CW, x=ML):
    # shrink to stay on one line - a wrapped headline is the fastest way to
    # make a deck look amateur
    size = fit_size(s, size, w)
    text(slide, x, y, w, 0.66, s, size=size, color=color, bold=True, line=1.05)


def subtitle(slide, s, y=1.40, size=12.5, color=DIM, w=CW, x=ML):
    text(slide, x, y, w, 0.54, s, size=size, color=color, line=1.30)


def header(slide, kicker, head, sub=None, size=30):
    eyebrow(slide, kicker)
    title(slide, head, size=size)
    if sub:
        subtitle(slide, sub)


def footer(slide, i, total, label=None, color=FAINT):
    hline(slide, ML, 7.06, CW, color=RGBColor(0x20, 0x24, 0x2C), lw=0.75)
    if label:
        text(slide, ML, 7.14, 8.6, 0.22, label, size=8.5, color=color, caps=True, spc=140)
    text(slide, SW - MR - 1.2, 7.14, 1.2, 0.22, f"{i:02d} / {total}", size=8.5,
         color=color, align=PP_ALIGN.RIGHT)
    # progress
    done = max(0.02, i / total)
    hline(slide, ML, 7.06, CW * done, color=AMBER, lw=2.0)


def notes(slide, s):
    slide.notes_slide.notes_text_frame.text = s.strip()


# -------------------------------------------------------------------- widgets
def pill(slide, x, y, w, h, s, fill=None, color=WHITE, size=9, bold=True,
         line=LINE, caps=True, spc=120):
    sh = rect(slide, x, y, w, h, fill=fill, line=line, lw=0.9, radius=0.5)
    tf = sh.text_frame
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    para(tf, s, size=size, color=color, bold=bold, align=PP_ALIGN.CENTER,
         first=True, caps=caps, spc=spc, line=1.0)
    return sh


def kpi(slide, x, y, w, h, value, label, accent=CYAN, vsize=30, lsize=9.5,
        fill=PANEL, foot=None):
    """number + caption card.  The value is auto-fitted to the card width and the
    caption box is derived from the value's own height, so they can never collide."""
    rect(slide, x, y, w, h, fill=fill, line=LINE, lw=0.75, radius=0.06)
    rect(slide, x, y, 0.05, h, fill=accent)
    inner = w - 0.42
    vs = fit_size(value, vsize, inner, min_size=12)
    vh = vs / 72.0 * 1.05
    text(slide, x + 0.22, y + 0.15, inner, vh + 0.04, value, size=vs, color=accent,
         bold=True, line=1.0)
    lab_h = h - 0.19 - vh - 0.10
    text(slide, x + 0.22, y + 0.19 + vh + 0.06, inner, max(0.20, lab_h), label,
         size=lsize, color=DIM, line=1.16, caps=True, spc=100)
    if foot:
        text(slide, x + 0.22, y + h - 0.26, inner, 0.20, foot, size=8.5, color=FAINT)
    return None


def card(slide, x, y, w, h, head, body, accent=CYAN, hsize=12.5, bsize=10.5,
         fill=PANEL, tag=None, num=None):
    rect(slide, x, y, w, h, fill=fill, line=LINE, lw=0.75, radius=0.05)
    rect(slide, x, y, w, 0.035, fill=accent)
    yy = y + 0.19
    if num is not None:
        text(slide, x + 0.20, yy, 0.5, 0.22, num, size=9, color=accent, bold=True, spc=120)
        yy += 0.24
    avail = w - 0.40
    hs = fit_size(head, hsize, avail, min_size=9)
    nlines = max(1, int(text_width(head, hs, True) // max(0.1, avail)) + 1)
    head_h = nlines * hs / 72.0 * 1.16
    text(slide, x + 0.20, yy, avail, head_h + 0.06, head, size=hs, color=WHITE, bold=True,
         line=1.12)
    by = yy + head_h + 0.12
    if body:
        b = tb(slide, x + 0.20, by, avail, max(0.2, y + h - by - 0.24))
        for i, ln in enumerate(body.split("\n")):
            para(b.text_frame, ln, size=bsize, color=SOFT, first=(i == 0), line=1.28,
                 space_after=2)
    if tag:
        text(slide, x + 0.20, y + h - 0.30, avail, 0.22, tag, size=8, color=FAINT,
             caps=True, spc=120)


def bullets(slide, x, y, w, h, items, size=12, gap=0.06, color=SOFT, marker="\u2014",
            mcolor=AMBER, lead_color=WHITE, line=1.30):
    box = tb(slide, x, y, w, h)
    tf = box.text_frame
    for i, it in enumerate(items):
        if isinstance(it, tuple):
            lead, rest = it
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.line_spacing = line
            p.space_after = Pt(gap * 72)
            r = p.add_run(); r.text = marker + "  "
            r.font.name = FONT; r.font.size = Pt(size); r.font.color.rgb = mcolor; r.font.bold = True
            r = p.add_run(); r.text = lead
            r.font.name = FONT; r.font.size = Pt(size); r.font.color.rgb = lead_color; r.font.bold = True
            if rest:
                r = p.add_run(); r.text = "  " + rest
                r.font.name = FONT; r.font.size = Pt(size); r.font.color.rgb = color
        else:
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.line_spacing = line
            p.space_after = Pt(gap * 72)
            r = p.add_run(); r.text = marker + "  "
            r.font.name = FONT; r.font.size = Pt(size); r.font.color.rgb = mcolor; r.font.bold = True
            r = p.add_run(); r.text = it
            r.font.name = FONT; r.font.size = Pt(size); r.font.color.rgb = color
    return box


def table(slide, x, y, w, col_w, rows, size=10, head_size=9, row_h=0.30,
          head_fill=PANEL2, head_color=AMBER, body_fill=None, zebra=True,
          colors=None, align=None, first_bold=False):
    """rows[0] is the header.  col_w in inches, must sum to w."""
    nr, nc = len(rows), len(rows[0])
    shp = slide.shapes.add_table(nr, nc, Inches(x), Inches(y), Inches(w),
                                 Inches(row_h * nr))
    tbl = shp.table
    # kill the default banded style so our own fills are what you see
    try:
        tbl.first_row = False
        tbl.horz_banding = False
        tbl.first_col = False
    except Exception:
        pass
    for j, cw in enumerate(col_w):
        tbl.columns[j].width = Inches(cw)
    for i in range(nr):
        tbl.rows[i].height = Inches(row_h)
        for j in range(nc):
            cell = tbl.cell(i, j)
            cell.margin_left = Inches(0.10)
            cell.margin_right = Inches(0.06)
            cell.margin_top = Inches(0.03)
            cell.margin_bottom = Inches(0.03)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            if i == 0:
                cell.fill.fore_color.rgb = head_fill
            elif body_fill:
                cell.fill.fore_color.rgb = body_fill
            elif zebra and i % 2 == 0:
                cell.fill.fore_color.rgb = PANEL
            else:
                cell.fill.fore_color.rgb = NAVY if zebra else PANEL
            tf = cell.text_frame
            tf.word_wrap = True
            val = rows[i][j]
            colr = head_color if i == 0 else WHITE
            if colors and i > 0 and colors.get((i, j)):
                colr = colors[(i, j)]
            if colors and i > 0 and colors.get(j):
                colr = colors[j]
            p = tf.paragraphs[0]
            p.line_spacing = 1.05
            if align:
                p.alignment = align[j]
            r = p.add_run()
            r.text = str(val)
            r.font.name = FONT
            r.font.size = Pt(head_size if i == 0 else size)
            r.font.bold = (i == 0) or (first_bold and j == 0)
            r.font.color.rgb = colr
    return tbl


def picture(slide, path, x, y, w=None, h=None, frame=True, pad=0.0,
            frame_fill=PANEL, frame_line=LINE):
    if frame:
        pw = (w if w else 0) + pad * 2
        ph = (h if h else 0) + pad * 2
        rect(slide, x - pad, y - pad, pw, ph, fill=frame_fill, line=frame_line,
             lw=0.75, radius=0.03)
    kw = {}
    if w:
        kw["width"] = Inches(w)
    if h:
        kw["height"] = Inches(h)
    return slide.shapes.add_picture(path, Inches(x), Inches(y), **kw)


def fig_light(slide, path, x, y, w, h, caption=None):
    """place a light-background Blender render on a white card so it reads as a
    studio plate rather than a hole in the dark theme"""
    rect(slide, x, y, w, h, fill=RGBColor(0xF2, 0xF3, 0xF6), line=LINE, lw=0.75,
         radius=0.02)
    # fit inside with a small inset
    from PIL import Image
    iw, ih = Image.open(path).size
    inset = 0.10
    aw, ah = w - inset * 2, h - inset * 2
    s = min(aw / iw, ah / ih)
    nw, nh = iw * s, ih * s
    slide.shapes.add_picture(path, Inches(x + (w - nw) / 2), Inches(y + (h - nh) / 2),
                             width=Inches(nw))
    if caption:
        text(slide, x, y + h + 0.07, w, 0.30, caption, size=8.5, color=DIM, line=1.2)


def fig_dark(slide, path, x, y, w, h, caption=None):
    rect(slide, x, y, w, h, fill=RGBColor(0x0A, 0x0B, 0x0F), line=LINE, lw=0.75,
         radius=0.02)
    from PIL import Image
    iw, ih = Image.open(path).size
    inset = 0.08
    aw, ah = w - inset * 2, h - inset * 2
    s = min(aw / iw, ah / ih)
    nw, nh = iw * s, ih * s
    slide.shapes.add_picture(path, Inches(x + (w - nw) / 2), Inches(y + (h - nh) / 2),
                             width=Inches(nw))
    if caption:
        text(slide, x, y + h + 0.07, w, 0.30, caption, size=8.5, color=DIM, line=1.2)


def numbered_row(slide, x, y, w, num, head, body, accent=AMBER, h=0.52):
    text(slide, x, y, 0.46, 0.30, num, size=13, color=accent, bold=True)
    text(slide, x + 0.46, y, w - 0.46, 0.30, head, size=12, color=WHITE, bold=True)
    if body:
        text(slide, x + 0.46, y + 0.27, w - 0.46, h, body, size=10, color=DIM, line=1.25)


def arrow(slide, x, y, w, color=FAINT, lw=1.2):
    sh = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x), Inches(y), Inches(w), Inches(0.16))
    sh.fill.solid()
    sh.fill.fore_color.rgb = color
    _noline(sh)
    _noshadow(sh)
    return sh


def down_arrow(slide, x, y, h, color=FAINT, w=0.16):
    sh = slide.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = color
    _noline(sh)
    _noshadow(sh)
    return sh


def dot(slide, x, y, d=0.09, color=CYAN):
    sh = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    sh.fill.solid()
    sh.fill.fore_color.rgb = color
    _noline(sh)
    _noshadow(sh)
    return sh
