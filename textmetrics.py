"""
textmetrics.py — glyph-accurate text measurement with per-character fallback.

Calibri (via its metric twin Carlito) lacks a few characters we need: the rupee
sign, check marks, arrows. PowerPoint silently substitutes another font for
those, so we do the same here with DejaVu Sans — which keeps measured widths,
and therefore line breaks, identical between the preview and the real deck.
"""
import os

from fontTools.ttLib import TTFont
from PIL import ImageFont

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts")
FALLBACK = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FALLBACK_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SCALE = 4.0  # px per pt for metric measurement

_missing = {}
_fonts = {}


def _cmap(path):
    if path not in _missing:
        _missing[path] = set(TTFont(path).getBestCmap().keys())
    return _missing[path]


def runs(text, font_key):
    """Split text into [(chunk, use_fallback)] runs."""
    main_path = _font_path(font_key)
    have = _cmap(main_path)
    out = []
    for ch in text:
        fb = ord(ch) not in have and ch != "\n"
        if out and out[-1][1] == fb:
            out[-1][0] += ch
        else:
            out.append([ch, fb])
    return [(c, f) for c, f in out]


def _font_path(key):
    size, bold, italic = key
    name = "carlito-latin-%d%s" % (700 if bold else 400, "-italic" if italic else "-normal")
    return os.path.join(FONT_DIR, name + ".ttf")


def font(size, bold=False, italic=False, fallback=False):
    key = (round(size, 1), bold, italic, fallback)
    if key not in _fonts:
        if fallback:
            path = FALLBACK_BOLD if bold else FALLBACK
        else:
            path = _font_path((size, bold, italic))
        _fonts[key] = ImageFont.truetype(path, max(1, int(round(size * SCALE))))
    return _fonts[key]


def width(text, size, bold=False, italic=False):
    total = 0.0
    for chunk, fb in runs(str(text), (size, bold, italic)):
        total += font(size, bold, italic, fb).getlength(chunk)
    return total


def wrap(text, size, bold, italic, max_px):
    out = []
    for raw in str(text).split("\n"):
        if not raw:
            out.append("")
            continue
        cur = ""
        for word in raw.split(" "):
            cand = (cur + " " + word) if cur else word
            if width(cand, size, bold, italic) <= max_px or not cur:
                cur = cand
            else:
                out.append(cur)
                cur = word
        out.append(cur)
    return out
