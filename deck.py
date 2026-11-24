"""
deck.py — a tiny deterministic slide engine.

Every drawing call is (a) applied to a python-pptx slide and (b) recorded as a
primitive in inches, so render_preview.py can repaint the exact same slide as a
PNG. That lets us see the deck before delivering it, and catch overflow.

Units: inches everywhere. Fonts: Calibri in the pptx; Carlito (metric-compatible
with Calibri) in the preview renderer, so wrap points match.
"""
import json
import os

import textmetrics as TM
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts")

# ---------------------------------------------------------------- primitives

class Deck:
    def __init__(self, w=13.333, h=7.5):
        self.w, self.h = w, h
        self.prs = Presentation()
        self.prs.slide_width = Inches(w)
        self.prs.slide_height = Inches(h)
        self.blank = self.prs.slide_layouts[6]
        self.slides = []          # list of dict(bg=..., prims=[...])
        self.warnings = []
        self._cur = None
        self._fonts = {}

    # -- lifecycle ---------------------------------------------------
    def add_slide(self, bg="#F4F6FB", dark=False):
        s = self.prs.slides.add_slide(self.blank)
        # Keep the native background too, but ALSO paint an opaque full-bleed
        # rectangle: viewers that drop <p:bg> would otherwise show white.
        fill = s.background.fill
        fill.solid()
        fill.fore_color.rgb = _rgb(bg)
        self._cur = {"bg": bg, "dark": dark, "prims": [], "slide": s}
        self.slides.append(self._cur)
        self.rect(0, 0, self.w, self.h, bg)
        return s

    def notes(self, text):
        self._cur["slide"].notes_slide.notes_text_frame.text = text

    # -- recording ---------------------------------------------------
    def _rec(self, d):
        self._cur["prims"].append(d)
        return d

    def measure(self, text, size, bold=False, italic=False, width_in=None, ls=1.0):
        """Return (n_lines, height_in) for text in a box of width_in."""
        lines = TM.wrap(text, size, bold, italic, width_in * 288 if width_in else 1e9)
        lh = size * 1.205 * ls
        return len(lines), len(lines) * lh / 72.0

    # -- drawing -----------------------------------------------------
    def rect(self, x, y, w, h, fill="#FFFFFF", line=None, lw=1.0, radius=0.0,
             alpha=None, shadow=False):
        s = self._cur["slide"]
        kind = MSO_SHAPE.ROUNDED_RECTANGLE if radius > 0 else MSO_SHAPE.RECTANGLE
        shp = s.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
        self._fill(shp, fill, alpha)
        if line is None:
            shp.line.fill.background()
        else:
            shp.line.color.rgb = _rgb(line)
            shp.line.width = Pt(lw)
        if radius > 0:
            try:
                shp.adjustments[0] = min(0.5, radius / min(w, h))
            except Exception:
                pass
        shp.shadow.inherit = bool(shadow)
        self._rec({"t": "rect", "x": x, "y": y, "w": w, "h": h, "fill": fill,
                   "line": line, "lw": lw, "r": radius, "alpha": alpha, "shadow": shadow})
        return shp

    def oval(self, x, y, w, h, fill="#FFFFFF", line=None, lw=1.0, alpha=None):
        s = self._cur["slide"]
        shp = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(w), Inches(h))
        self._fill(shp, fill, alpha)
        if line is None:
            shp.line.fill.background()
        else:
            shp.line.color.rgb = _rgb(line)
            shp.line.width = Pt(lw)
        shp.shadow.inherit = False
        self._rec({"t": "oval", "x": x, "y": y, "w": w, "h": h, "fill": fill,
                   "line": line, "lw": lw, "alpha": alpha})
        return shp

    def line(self, x1, y1, x2, y2, color="#0F1E3D", lw=1.0, arrow=False, dash=None):
        s = self._cur["slide"]
        c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1),
                                   Inches(x2), Inches(y2))
        c.line.color.rgb = _rgb(color)
        c.line.width = Pt(lw)
        if dash:
            c.line.dash_style = dash
        if arrow:
            ln = c.line._get_or_add_ln()
            tail = ln.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"})
            ln.append(tail)
        self._rec({"t": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                   "color": color, "lw": lw, "arrow": arrow})

    def text(self, x, y, w, h, s, size=12, bold=False, color="#334155", align="l",
             italic=False, anchor="t", ls=1.0, sp_after=0, sp_before=0, caps=False, spc=None):
        """Single-style text block. `s` may contain \n."""
        self.rich(x, y, w, h, [{"t": s, "size": size, "b": bold, "c": color, "i": italic,
                                "a": align, "ls": ls, "sa": sp_after, "sb": sp_before,
                                "caps": caps, "spc": spc}], anchor=anchor)
        return self._cur["prims"][-1]

    def rich(self, x, y, w, h, items, anchor="t", wrap_=True):
        s = self._cur["slide"]
        tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = tb.text_frame
        tf.word_wrap = wrap_
        tf.margin_left = 0
        tf.margin_right = 0
        tf.margin_top = 0
        tf.margin_bottom = 0
        tf.auto_size = None            # no spAutoFit / normAutofit
        tf.vertical_anchor = {"t": MSO_ANCHOR.TOP, "m": MSO_ANCHOR.MIDDLE,
                              "b": MSO_ANCHOR.BOTTOM}[anchor]
        total = 0.0
        for i, it in enumerate(items):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER,
                           "r": PP_ALIGN.RIGHT, "j": PP_ALIGN.JUSTIFY}[it.get("a", "l")]
            p.line_spacing = it.get("ls", 1.0)
            p.space_after = Pt(it.get("sa", 0))
            p.space_before = Pt(it.get("sb", 0))
            txt_ = it["t"]
            if it.get("caps"):
                txt_ = txt_.upper()
            run = p.add_run()
            run.text = txt_
            f = run.font
            f.name = "Calibri"
            f.size = Pt(it.get("size", 12))
            f.bold = it.get("b", False)
            f.italic = it.get("i", False)
            f.color.rgb = _rgb(it.get("c", "#334155"))
            # Letter-spacing (`spc`) is deliberately NOT written: several
            # viewers scatter tracking runs into one letter per line-width.
            # `caps` is baked into the string instead of using cap="all".
            nl, th = self.measure(it["t"], it.get("size", 12), it.get("b", False), it.get("i", False), w,
                                  it.get("ls", 1.0))
            total += th + it.get("sa", 0) / 72.0 + it.get("sb", 0) / 72.0
        if total > h + 0.02:
            self.warnings.append(
                "OVERFLOW %.2f>%.2f :: %s" % (total, h, items[0]["t"][:46].replace("\n", " ")))
        self._rec({"t": "text", "x": x, "y": y, "w": w, "h": h, "items": items,
                   "anchor": anchor, "wrap": wrap_})
        return tb

    def pic(self, path, x, y, w, h):
        s = self._cur["slide"]
        s.shapes.add_picture(path, Inches(x), Inches(y), Inches(w), Inches(h))
        self._rec({"t": "pic", "x": x, "y": y, "w": w, "h": h, "path": path})

    def _fill(self, shp, fill, alpha):
        if fill is None:
            shp.fill.background()
            return
        shp.fill.solid()
        shp.fill.fore_color.rgb = _rgb(fill)
        if alpha is not None:
            try:
                srgb = shp.fill.fore_color._xFill.srgbClr
                el = srgb.makeelement(qn("a:alpha"), {"val": str(int(alpha * 100000))})
                srgb.append(el)
            except Exception:
                pass

    # -- output ------------------------------------------------------
    def save(self, pptx_path, json_path=None):
        self.prs.core_properties.title = "Astro Smart Attendance — Team Sun Rises India"
        self.prs.core_properties.subject = "AI + IoT + Cloud Smart School Attendance System"
        self.prs.core_properties.author = "Team Sun Rises India"
        self.prs.core_properties.category = "ABG STEM Quest 2026-27"
        self.prs.save(pptx_path)
        if json_path:
            with open(json_path, "w") as fh:
                json.dump({"w": self.w, "h": self.h,
                           "slides": [{"bg": s["bg"], "dark": s["dark"], "prims": s["prims"]}
                                      for s in self.slides]}, fh)


def _rgb(h):
    h = h.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def wrap(text, font, max_px):
    out = []
    for raw in str(text).split("\n"):
        if not raw:
            out.append("")
            continue
        cur = ""
        for word in raw.split(" "):
            cand = (cur + " " + word) if cur else word
            if font.getlength(cand) <= max_px or not cur:
                cur = cand
            else:
                out.append(cur)
                cur = word
        out.append(cur)
    return out
