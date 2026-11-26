#!/usr/bin/env python3
"""
Builds the print-ready Creative Ideation Worksheet PDF for Astro Smart Attendance.
Design: navy / saffron / teal editorial worksheet, A4, 8 pages.
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import Color, HexColor
from fontTools.ttLib import TTFont as FTFont

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.environ.get("WS_FONT_DIR", "/home/user/fonts")
OUT = os.path.join(HERE, "Creative-Ideation-Worksheet-Astro-Smart-Attendance.pdf")

PAGE_W, PAGE_H = A4
M = 34.0
CW = PAGE_W - 2 * M

# ---------------------------------------------------------------- colours
NAVY = HexColor("#0B1F4A")
NAVY2 = HexColor("#122B63")
NAVY3 = HexColor("#1E3A8A")
SAFFRON = HexColor("#FF7A18")
SAFFRON_L = HexColor("#FFF7ED")
SAFFRON_B = HexColor("#FED7AA")
TEAL = HexColor("#0EA5A4")
TEAL_L = HexColor("#F0FDFA")
TEAL_B = HexColor("#99F6E4")
GOLD = HexColor("#FFB703")
INK = HexColor("#1E293B")
BODY = HexColor("#334155")
MUTED = HexColor("#64748B")
LINE = HexColor("#E2E8F0")
SOFT = HexColor("#F8FAFC")
BLUE_L = HexColor("#EFF6FF")
CREAM = HexColor("#FFFCF5")
GREEN = HexColor("#16A34A")
GREEN_L = HexColor("#ECFDF5")
AMBER_L = HexColor("#FFFBEB")
AMBER_B = HexColor("#F59E0B")
RED_L = HexColor("#FEE2E2")
RED_D = HexColor("#991B1B")

# ---------------------------------------------------------------- fonts
_FILES = {
    "Pop6": "poppins-latin-600-normal.ttf",
    "Pop7": "poppins-latin-700-normal.ttf",
    "Pop8": "poppins-latin-800-normal.ttf",
    "Pop9": "poppins-latin-900-normal.ttf",
    "Int4": "inter-latin-400-normal.ttf",
    "Int5": "inter-latin-500-normal.ttf",
    "Int6": "inter-latin-600-normal.ttf",
    "Int7": "inter-latin-700-normal.ttf",
    "Caveat": "caveat-latin-700-normal.ttf",
    "Mono": "jetbrains-mono-latin-500-normal.ttf",
}
for name, fn in _FILES.items():
    pdfmetrics.registerFont(TTFont(name, os.path.join(FONT_DIR, fn)))

pdfmetrics.registerFont(TTFont("DJV", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DJVB", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
FALLBACK = {"DJVB", "DJV"}


def _cmap(path):
    f = FTFont(path)
    s = set()
    for t in f["cmap"].tables:
        s |= set(t.cmap.keys())
    return s


_COVER = {
    "Pop6": _cmap(os.path.join(FONT_DIR, _FILES["Pop6"])),
    "Pop7": _cmap(os.path.join(FONT_DIR, _FILES["Pop7"])),
    "Pop8": _cmap(os.path.join(FONT_DIR, _FILES["Pop8"])),
    "Pop9": _cmap(os.path.join(FONT_DIR, _FILES["Pop9"])),
    "Int4": _cmap(os.path.join(FONT_DIR, _FILES["Int4"])),
    "Int5": _cmap(os.path.join(FONT_DIR, _FILES["Int5"])),
    "Int6": _cmap(os.path.join(FONT_DIR, _FILES["Int6"])),
    "Int7": _cmap(os.path.join(FONT_DIR, _FILES["Int7"])),
    "Caveat": _cmap(os.path.join(FONT_DIR, _FILES["Caveat"])),
    "Mono": _cmap(os.path.join(FONT_DIR, _FILES["Mono"])),
    "DJV": _cmap("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    "DJVB": _cmap("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
}
_W = {}


def pick(ch, font):
    if ord(ch) in _COVER[font]:
        return font
    alt = "DJVB" if font in ("Pop6", "Pop7", "Pop8", "Pop9", "Int6", "Int7") else "DJV"
    if ord(ch) in _COVER[alt]:
        return alt
    return "DJV" if ord(ch) in _COVER["DJV"] else None


def cw(ch, font, size):
    key = (ch, font, size)
    if key in _W:
        return _W[key]
    f = pick(ch, font)
    w = pdfmetrics.stringWidth(ch, f, size) if f else 0.0
    _W[key] = w
    return w


def tw(text, font, size):
    return sum(cw(ch, font, size) for ch in text)


def draw_text(c, x, y, text, font, size, color=INK):
    c.setFillColor(color)
    run, runf = "", None
    for ch in text:
        f = pick(ch, font)
        if f is None:
            continue
        if f != runf:
            if run:
                c.setFont(runf, size)
                c.drawString(x, y, run)
                x += pdfmetrics.stringWidth(run, runf, size)
            runf, run = f, ch
        else:
            run += ch
    if run:
        c.setFont(runf, size)
        c.drawString(x, y, run)
        x += pdfmetrics.stringWidth(run, runf, size)
    return x


def tracked(c, x, y, text, font, size, color, track=0.8):
    c.setFillColor(color)
    for ch in text:
        x = draw_text(c, x, y, ch, font, size, color) + track
    return x


def tracked_width(text, font, size, track=0.8):
    return sum(tw(ch, font, size) + track for ch in text) - track


# ---------------------------------------------------------------- rich text
def parse_rich(text):
    """split on ** for bold; returns [(chunk, is_bold)]"""
    out, bold = [], False
    for i, part in enumerate(text.split("**")):
        if part:
            out.append((part, bold))
        bold = not bold
    return out


def wrap_rich(text, width, size, font, bold_font):
    words = []  # (word, bold) with spaces attached
    for chunk, bold in parse_rich(text):
        parts = chunk.split(" ")
        for j, p in enumerate(parts):
            if j < len(parts) - 1:
                words.append((p + " ", bold))
            elif p:
                words.append((p, bold))
    lines, cur, curw = [], [], 0.0
    for w, bold in words:
        f = bold_font if bold else font
        ww = tw(w, f, size)
        if curw + ww > width and cur:
            lines.append(cur)
            cur, curw = [(w.lstrip(" "), bold)], tw(w.lstrip(" "), f, size)
        else:
            cur.append((w, bold))
            curw += ww
    if cur:
        lines.append(cur)
    return lines


def para(c, x, top, width, text, size=8.6, font="Int4", bold_font="Int7",
         color=BODY, leading=None, align="left", first_indent=0.0):
    leading = leading or size * 1.55
    lines = wrap_rich(text, width - first_indent, size, font, bold_font)
    yy = top - size
    for i, line in enumerate(lines):
        wsum = sum(tw(t, bold_font if b else font, size) for t, b in line)
        xx = x + (first_indent if i == 0 else 0)
        if align == "center":
            xx = x + (width - wsum) / 2.0
        for t, b in line:
            xx = draw_text(c, xx, yy, t, bold_font if b else font, size, color)
        yy -= leading
    return top - len(lines) * leading


def para_height(text, width, size=8.6, font="Int4", bold_font="Int7", leading=None):
    leading = leading or size * 1.55
    return len(wrap_rich(text, width, size, font, bold_font)) * leading


def bullets(c, x, top, width, items, size=8.4, leading=None, gap=3.0,
            mark="sq", mark_color=TEAL, color=BODY):
    leading = leading or size * 1.62
    y = top
    for it in items:
        lines = wrap_rich(it, width - 14, size, "Int4", "Int7")
        if mark == "sq":
            c.setFillColor(mark_color)
            c.roundRect(x + 1, y - size + 0.6, 4.2, 4.2, 1.2, stroke=0, fill=1)
        elif mark == "circle":
            c.setFillColor(mark_color)
            c.circle(x + 3.2, y - size + 2.6, 2.1, stroke=0, fill=1)
        elif mark == "check":
            draw_text(c, x, y - size, "✓", "DJV", size, mark_color)
        yy = y - size
        for ln in lines:
            xx = x + 12
            for t, b in ln:
                xx = draw_text(c, xx, yy, t, "Int7" if b else "Int4", size, color)
            yy -= leading
        y = yy + leading - size - gap
    return y


def bullets_height(items, width, size=8.4, leading=None, gap=3.0):
    leading = leading or size * 1.62
    h = 0
    for it in items:
        h += len(wrap_rich(it, width - 14, size, "Int4", "Int7")) * leading + gap
    return h - gap


# ---------------------------------------------------------------- shapes
def rrect(c, x, y, w, h, r=6, fill=None, stroke=None, lw=1):
    if fill is not None:
        c.setFillColor(fill)
    if stroke is not None:
        c.setStrokeColor(stroke)
        c.setLineWidth(lw)
    c.roundRect(x, y, w, h, r, stroke=1 if stroke is not None else 0,
                fill=1 if fill is not None else 0)


def gradient(c, x, y, w, h, r, colors, positions=None, horizontal=True):
    c.saveState()
    p = c.beginPath()
    p.roundRect(x, y, w, h, r)
    c.clipPath(p, stroke=0, fill=0)
    if horizontal:
        c.linearGradient(x, y, x + w, y, colors, positions, extend=True)
    else:
        c.linearGradient(x, y, x, y + h, colors, positions, extend=True)
    c.restoreState()


def set_dash(c, dash=3, gap=2, color=None, lw=1):
    c.setDash([dash, gap])
    c.setLineWidth(lw)
    if color is not None:
        c.setStrokeColor(color)


def arrow(c, x1, y1, x2, y2, color=SAFFRON, lw=1.4, head=4.2):
    import math
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(lw)
    c.line(x1, y1, x2, y2)
    ang = math.atan2(y2 - y1, x2 - x1)
    for s in (-0.5, 0.5):
        c.line(x2, y2, x2 - head * math.cos(ang - s), y2 - head * math.sin(ang - s))


def chip(c, x, y, label, font="Pop8", size=7.2, padx=7, h=14, fill=NAVY,
         color=Color(1, 1, 1), r=7, stroke=None):
    w = tw(label, font, size) + 2 * padx
    rrect(c, x, y, w, h, r, fill=fill, stroke=stroke, lw=0.8)
    draw_text(c, x + padx, y + (h - size) / 2 + 0.8, label, font, size, color)
    return w


def num_badge(c, x, y, size, num, fill, radius=None, fsize=None, color=Color(1, 1, 1)):
    r = radius if radius is not None else 4
    rrect(c, x, y, size, size, r, fill=fill)
    fsize = fsize or size * 0.46
    lab = str(num)
    w = tw(lab, "Pop9", fsize)
    draw_text(c, x + (size - w) / 2, y + (size - fsize) / 2 + fsize * 0.06, lab, "Pop9", fsize, color)


# ---------------------------------------------------------------- glyph icons
def glyph(c, kind, cx, cy, s=12, color=NAVY, lw=1.1, bg=None):
    """Small vector icon, drawn inside a circle of diameter s."""
    c.saveState()
    c.setLineWidth(lw)
    c.setStrokeColor(color)
    c.setFillColor(color)
    if bg is not None:
        c.setFillColor(bg)
        c.circle(cx, cy, s * 0.78, stroke=0, fill=1)
        c.setFillColor(color)
        c.setStrokeColor(color)
    u = s / 2.0
    if kind == "card":
        rrect(c, cx - u * 0.85, cy - u * 0.52, u * 1.7, u * 1.04, 1.6, fill=None, stroke=color, lw=lw)
        c.line(cx - u * 0.85, cy + u * 0.28, cx + u * 0.85, cy + u * 0.28)
    elif kind == "chip":
        rrect(c, cx - u * 0.45, cy - u * 0.45, u * 0.9, u * 0.9, 1.6, fill=None, stroke=color, lw=lw)
        for i in (-1, 1):
            for k in (-0.2, 0.2):
                c.line(cx + i * u * 0.45, cy + k * u, cx + i * u * 0.78, cy + k * u)
                c.line(cx + k * u, cy + i * u * 0.45, cx + k * u, cy + i * u * 0.78)
    elif kind == "screen":
        rrect(c, cx - u * 0.85, cy - u * 0.45, u * 1.7, u * 0.9, 1.4, fill=None, stroke=color, lw=lw)
        c.line(cx - u * 0.35, cy - u * 0.72, cx + u * 0.35, cy - u * 0.72)
        for i, xx in enumerate((-0.45, 0.0, 0.45)):
            c.line(cx + xx * u, cy + u * 0.05, cx + xx * u, cy + u * 0.35)
    elif kind == "cloud":
        c.circle(cx - u * 0.42, cy - u * 0.1, u * 0.34, stroke=0, fill=1)
        c.circle(cx + u * 0.02, cy + u * 0.16, u * 0.45, stroke=0, fill=1)
        c.circle(cx + u * 0.48, cy - u * 0.12, u * 0.32, stroke=0, fill=1)
        c.rect(cx - u * 0.78, cy - u * 0.42, u * 1.5, u * 0.32, stroke=0, fill=1)
    elif kind == "mail":
        rrect(c, cx - u * 0.85, cy - u * 0.6, u * 1.7, u * 1.2, 1.6, fill=None, stroke=color, lw=lw)
        c.line(cx - u * 0.85, cy + u * 0.55, cx, cy - u * 0.12)
        c.line(cx + u * 0.85, cy + u * 0.55, cx, cy - u * 0.12)
    elif kind == "person":
        c.circle(cx, cy + u * 0.34, u * 0.3, stroke=0, fill=1)
        p = c.beginPath()
        p.moveTo(cx - u * 0.55, cy - u * 0.62)
        p.curveTo(cx - u * 0.55, cy - u * 0.02, cx + u * 0.55, cy - u * 0.02, cx + u * 0.55, cy - u * 0.62)
        p.close()
        c.drawPath(p, stroke=0, fill=1)
    elif kind == "teacher":
        c.circle(cx, cy + u * 0.42, u * 0.24, stroke=0, fill=1)
        p = c.beginPath()
        p.moveTo(cx - u * 0.72, cy - u * 0.66)
        p.curveTo(cx - u * 0.62, cy - u * 0.1, cx + u * 0.62, cy - u * 0.1, cx + u * 0.72, cy - u * 0.66)
        p.close()
        c.drawPath(p, stroke=0, fill=1)
    elif kind == "chart":
        c.line(cx - u * 0.7, cy - u * 0.62, cx + u * 0.72, cy - u * 0.62)
        for i, (xx, hh) in enumerate(((-0.44, 0.55), (0.0, 1.0), (0.44, 0.76))):
            c.rect(cx + xx * u - u * 0.13, cy - u * 0.62, u * 0.26, hh * u, stroke=0, fill=1)
    elif kind == "lock":
        rrect(c, cx - u * 0.66, cy - u * 0.72, u * 1.32, u * 0.78, 1.8, fill=color, stroke=None)
        c.setStrokeColor(color)
        c.setLineWidth(lw + 0.8)
        c.line(cx - u * 0.34, cy + u * 0.02, cx - u * 0.34, cy + u * 0.38)
        c.line(cx + u * 0.34, cy + u * 0.02, cx + u * 0.34, cy + u * 0.38)
        ar = u * 0.34
        c.arc(cx - ar, cy + u * 0.38 - ar, cx + ar, cy + u * 0.38 + ar, 0, 180)
        c.setFillColor(Color(1, 1, 1, 0.85))
        c.circle(cx, cy - u * 0.34, u * 0.13, stroke=0, fill=1)
    elif kind == "star":
        import math as _m
        p = c.beginPath()
        for i in range(10):
            ang = -_m.pi / 2 + i * _m.pi / 5
            rad = u * (0.9 if i % 2 == 0 else 0.38)
            xx, yy = cx + rad * _m.cos(ang), cy + rad * _m.sin(ang)
            (p.moveTo if i == 0 else p.lineTo)(xx, yy)
        p.close()
        c.drawPath(p, stroke=0, fill=1)
    elif kind == "clock":
        c.circle(cx, cy, u * 0.75, stroke=1, fill=0)
        c.line(cx, cy, cx, cy + u * 0.42)
        c.line(cx, cy, cx + u * 0.34, cy - u * 0.18)
    elif kind == "check":
        c.setLineWidth(lw + 0.7)
        c.line(cx - u * 0.55, cy + u * 0.02, cx - u * 0.12, cy - u * 0.45)
        c.line(cx - u * 0.12, cy - u * 0.45, cx + u * 0.62, cy + u * 0.5)
    elif kind == "bolt":
        p = c.beginPath()
        p.moveTo(cx + u * 0.12, cy + u * 0.8)
        p.lineTo(cx - u * 0.5, cy - u * 0.12)
        p.lineTo(cx - u * 0.02, cy - u * 0.12)
        p.lineTo(cx - u * 0.18, cy - u * 0.8)
        p.lineTo(cx + u * 0.52, cy + u * 0.1)
        p.lineTo(cx + u * 0.02, cy + u * 0.1)
        p.close()
        c.drawPath(p, stroke=0, fill=1)
    elif kind == "battery":
        rrect(c, cx - u * 0.8, cy - u * 0.42, u * 1.45, u * 0.84, 1.6, fill=None, stroke=color, lw=lw)
        c.rect(cx + u * 0.7, cy - u * 0.18, u * 0.14, u * 0.36, stroke=0, fill=1)
        c.rect(cx - u * 0.68, cy - u * 0.3, u * 0.62, u * 0.6, stroke=0, fill=1)
    elif kind == "wifi":
        for i, rr in enumerate((0.3, 0.62, 0.94)):
            c.arc(cx - u * rr, cy - u * rr, cx + u * rr, cy + u * rr, 35, 110)
        c.circle(cx, cy - u * 0.5, u * 0.12, stroke=0, fill=1)
    elif kind == "gear":
        import math as _m
        c.circle(cx, cy, u * 0.34, stroke=1, fill=0)
        for i in range(8):
            a = i * _m.pi / 4
            c.line(cx + u * 0.42 * _m.cos(a), cy + u * 0.42 * _m.sin(a),
                   cx + u * 0.78 * _m.cos(a), cy + u * 0.78 * _m.sin(a))
    elif kind == "search":
        c.circle(cx - u * 0.16, cy + u * 0.16, u * 0.48, stroke=1, fill=0)
        c.setLineWidth(lw + 0.6)
        c.line(cx + u * 0.2, cy - u * 0.22, cx + u * 0.68, cy - u * 0.68)
    elif kind == "people":
        c.circle(cx - u * 0.34, cy + u * 0.36, u * 0.22, stroke=0, fill=1)
        c.circle(cx + u * 0.38, cy + u * 0.3, u * 0.19, stroke=0, fill=1)
        p = c.beginPath()
        p.moveTo(cx - u * 0.78, cy - u * 0.62)
        p.curveTo(cx - u * 0.7, cy - u * 0.1, cx + u * 0.02, cy - u * 0.1, cx + u * 0.08, cy - u * 0.62)
        p.close()
        c.drawPath(p, stroke=0, fill=1)
        p = c.beginPath()
        p.moveTo(cx + u * 0.16, cy - u * 0.62)
        p.curveTo(cx + u * 0.22, cy - u * 0.18, cx + u * 0.78, cy - u * 0.18, cx + u * 0.84, cy - u * 0.62)
        p.close()
        c.drawPath(p, stroke=0, fill=1)
    elif kind == "phone":
        rrect(c, cx - u * 0.4, cy - u * 0.78, u * 0.8, u * 1.56, 2.2, fill=None, stroke=color, lw=lw)
        c.line(cx - u * 0.14, cy - u * 0.6, cx + u * 0.14, cy - u * 0.6)
    elif kind == "book":
        rrect(c, cx - u * 0.75, cy - u * 0.66, u * 1.5, u * 1.32, 1.6, fill=None, stroke=color, lw=lw)
        c.line(cx, cy - u * 0.66, cx, cy + u * 0.66)
        c.line(cx - u * 0.55, cy + u * 0.3, cx - u * 0.2, cy + u * 0.3)
        c.line(cx + u * 0.2, cy + u * 0.3, cx + u * 0.55, cy + u * 0.3)
    elif kind == "flag":
        c.line(cx - u * 0.55, cy - u * 0.8, cx - u * 0.55, cy + u * 0.8)
        p = c.beginPath()
        p.moveTo(cx - u * 0.5, cy + u * 0.76)
        p.lineTo(cx + u * 0.66, cy + u * 0.42)
        p.lineTo(cx - u * 0.5, cy + u * 0.06)
        p.close()
        c.drawPath(p, stroke=0, fill=1)
    elif kind == "save":
        rrect(c, cx - u * 0.72, cy - u * 0.72, u * 1.44, u * 1.44, 1.6, fill=None, stroke=color, lw=lw)
        c.rect(cx - u * 0.36, cy + u * 0.2, u * 0.72, u * 0.5, stroke=0, fill=1)
    elif kind == "spark":
        import math as _m
        for i in range(4):
            a = i * _m.pi / 2
            c.line(cx + u * 0.18 * _m.cos(a), cy + u * 0.18 * _m.sin(a),
                   cx + u * 0.85 * _m.cos(a), cy + u * 0.85 * _m.sin(a))
    elif kind == "layers":
        for i, dy in enumerate((0.42, 0.0, -0.42)):
            p = c.beginPath()
            p.moveTo(cx, cy + (dy + 0.24) * u)
            p.lineTo(cx + u * 0.78, cy + dy * u)
            p.lineTo(cx, cy + (dy - 0.24) * u)
            p.lineTo(cx - u * 0.78, cy + dy * u)
            p.close()
            if i == 1:
                c.drawPath(p, stroke=0, fill=color)
            else:
                c.drawPath(p, stroke=0, fill=None)
                c.drawPath(p, stroke=1, fill=0)
    c.restoreState()


# ---------------------------------------------------------------- page furniture
def page_header(c, page_no):
    gradient(c, 0, PAGE_H - 30, PAGE_W, 30, 0, [NAVY, NAVY2, NAVY3], [0, 0.55, 1])
    tracked(c, M, PAGE_H - 20.5, "ABG STEM QUEST", "Pop8", 8.4, Color(1, 1, 1), 1.55)
    x0 = M + tracked_width("ABG STEM QUEST", "Pop8", 8.4, 1.55)
    tracked(c, x0 + 4, PAGE_H - 20.5, "2026–27", "Pop8", 8.4, GOLD, 1.55)
    lab = "PART 1 ·  CREATIVE IDEATION WORKSHEET"
    w = tracked_width(lab, "Pop7", 6.4, 1.0) + 16
    rrect(c, PAGE_W - M - w, PAGE_H - 23.5, w, 16, 8, fill=Color(1, 1, 1, 0.13),
          stroke=Color(1, 1, 1, 0.35), lw=0.7)
    tracked(c, PAGE_W - M - w + 8, PAGE_H - 19, lab, "Pop7", 6.4, Color(1, 1, 1), 1.0)


def page_footer(c, total):
    pass  # drawn by NumberedCanvas


class NumberedCanvas(pdfcanvas.Canvas):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._saved = []

    def showPage(self):
        self._saved.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        n = len(self._saved)
        for i, state in enumerate(self._saved):
            self.__dict__.update(state)
            self._footer(i + 1, n)
            super().showPage()
        super().save()

    def _footer(self, i, n):
        y = 26
        self.setStrokeColor(LINE)
        self.setLineWidth(0.7)
        self.line(M, y + 12, PAGE_W - M, y + 12)
        tracked(self, M, y, "ASTRO SMART ATTENDANCE", "Pop8", 6.6, NAVY, 1.2)
        x = M + tracked_width("ASTRO SMART ATTENDANCE", "Pop8", 6.6, 1.2) + 6
        draw_text(self, x, y, "·  Sun Rises India ·  ABPS Renukoot ·  SDG 9", "Int5", 6.6, MUTED)
        draw_text(self, PAGE_W - M - 40, y, "Page %d of %d" % (i, n), "Pop7", 6.6, NAVY)


# ---------------------------------------------------------------- section header
def section(c, y, num, title, sub, accent=SAFFRON):
    size = 26
    c.saveState()
    gradient(c, M, y - size, size, size, 7, [accent, NAVY] if accent == SAFFRON else [accent, TEAL], [0, 1])
    c.restoreState()
    lab = str(num).zfill(2) if num else ""
    w = tw(lab, "Pop9", 10.5)
    draw_text(c, M + (size - w) / 2, y - size + 9.2, lab, "Pop9", 10.5, Color(1, 1, 1))
    draw_text(c, M + size + 11, y - 12, title.upper(), "Pop8", 11.6, NAVY)
    if sub:
        draw_text(c, M + size + 11, y - 23.2, sub, "Int5", 7.6, MUTED)
    return y - size - 12


def label(c, x, y, text, color=SAFFRON, size=6.8, font="Pop8", track=1.1):
    tracked(c, x, y, text.upper(), font, size, color, track)


def draw_table(c, x, top, col_w, header, rows, size=7.9, header_h=20, pad=5.5,
               align=None, min_row=None, row_fills=None, header_fill=None,
               header_color=None, leading_k=1.42, round_r=8):
    """Rounded, banded table with wrapped cells. Returns total height."""
    header_fill = header_fill if header_fill is not None else NAVY
    header_color = header_color if header_color is not None else Color(1, 1, 1)
    total_w = sum(col_w)
    leading = size * leading_k
    align = align or ["left"] + ["center"] * (len(col_w) - 1)
    heights = []
    for row in rows:
        mx = 1
        for i, cell in enumerate(row):
            mx = max(mx, len(wrap_rich(str(cell), col_w[i] - 2 * pad, size, "Int5", "Int7")))
        heights.append(max(mx * leading + 2 * pad + 1.0, min_row or 0))
    total_h = sum(heights) + header_h

    c.saveState()
    p = c.beginPath()
    p.roundRect(x, top - total_h, total_w, total_h, round_r)
    c.clipPath(p, stroke=0, fill=0)
    c.setFillColor(header_fill)
    c.rect(x, top - header_h, total_w, header_h, stroke=0, fill=1)
    yy = top - header_h
    for i, hh in enumerate(heights):
        if row_fills and i < len(row_fills) and row_fills[i] is not None:
            fill = row_fills[i]
        else:
            fill = SOFT if i % 2 == 1 else Color(1, 1, 1)
        c.setFillColor(fill)
        c.rect(x, yy - hh, total_w, hh, stroke=0, fill=1)
        yy -= hh
    c.setStrokeColor(LINE)
    c.setLineWidth(0.6)
    yy = top - header_h
    for hh in heights:
        c.line(x, yy, x + total_w, yy)
        yy -= hh
    c.restoreState()

    xx = x
    for i, htxt in enumerate(header):
        wsum = tw(htxt, "Pop7", size - 0.6)
        tx = xx + pad if align[i] == "left" else xx + (col_w[i] - wsum) / 2
        draw_text(c, tx, top - header_h / 2 - (size - 0.6) / 2 + 1, htxt, "Pop7", size - 0.6, header_color)
        xx += col_w[i]

    yy = top - header_h
    for i, row in enumerate(rows):
        hh = heights[i]
        xx = x
        for j, cell in enumerate(row):
            lines = wrap_rich(str(cell), col_w[j] - 2 * pad, size, "Int5", "Int7")
            ty = yy - (hh - len(lines) * leading) / 2 - size * 0.86
            for ln in lines:
                wsum = sum(tw(t, "Int7" if b else "Int5", size) for t, b in ln)
                tx = xx + pad if align[j] == "left" else xx + (col_w[j] - wsum) / 2
                for t, b in ln:
                    tx = draw_text(c, tx, ty, t, "Int7" if b else "Int5", size, NAVY if b else BODY)
                ty -= leading
            xx += col_w[j]
        yy -= hh

    rrect(c, x, top - total_h, total_w, total_h, round_r, fill=None, stroke=LINE, lw=1)
    return total_h
