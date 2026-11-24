"""
render_preview.py — repaint deck.json as PNGs so the deck can be reviewed
before delivery. Carlito (metric-compatible with Calibri) is used for text so
line breaks in the preview match PowerPoint exactly.
"""
import json
import os
import sys

import textmetrics as TM
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
# 288 px per inch == 4 px per pt, exactly matching textmetrics.SCALE, so text
# drawn here has the same width it was measured with.
PX = 288.0
SS = 2                # then downsample by this factor
FONT_DIR = os.path.join(HERE, "assets", "fonts")
_cache = {}
_imgcache = {}


def font(pt, bold=False, italic=False, fallback=False):
    return TM.font(pt, bold, italic, fallback)


def parse(c):
    c = c.lstrip("#")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))


def blend(c, alpha, bg):
    if alpha is None:
        return c
    return tuple(int(c[i] * alpha + bg[i] * (1 - alpha)) for i in range(3))


def rrect(d, box, r, fill=None, outline=None, width=0):
    if r <= 0:
        d.rectangle(box, fill=fill, outline=outline, width=width)
    else:
        d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def cover(path, w, h):
    key = (path, w, h)
    if key in _imgcache:
        return _imgcache[key]
    im = Image.open(path).convert("RGB")
    tw, th = max(1, int(w * PX)), max(1, int(h * PX))
    sr, tr = im.width / im.height, tw / th
    if sr > tr:
        nw = int(im.height * tr)
        im = im.crop(((im.width - nw) // 2, 0, (im.width + nw) // 2, im.height))
    else:
        nh = int(im.width / tr)
        im = im.crop((0, (im.height - nh) // 2, im.width, (im.height + nh) // 2))
    im = im.resize((tw, th), Image.LANCZOS)
    _imgcache[key] = im
    return im


def render(deck, outdir):
    os.makedirs(outdir, exist_ok=True)
    W, H = int(deck["w"] * PX), int(deck["h"] * PX)
    made = []
    for idx, sl in enumerate(deck["slides"], 1):
        bg = parse(sl["bg"])
        img = Image.new("RGB", (W, H), bg)
        d = ImageDraw.Draw(img, "RGBA")
        for p in sl["prims"]:
            t = p["t"]
            if t == "rect":
                x, y, w, h = (p[k] * PX for k in ("x", "y", "w", "h"))
                fill = blend(parse(p["fill"]), p["alpha"], bg) if p["fill"] else None
                out = blend(parse(p["line"]), None, bg) if p["line"] else None
                rrect(d, (x, y, x + w, y + h), p["r"] * PX,
                      fill=fill, outline=out, width=int(p["lw"] * PX / 72))
            elif t == "oval":
                x, y, w, h = (p[k] * PX for k in ("x", "y", "w", "h"))
                fill = blend(parse(p["fill"]), p["alpha"], bg) if p["fill"] else None
                out = parse(p["line"]) if p["line"] else None
                d.ellipse((x, y, x + w, y + h), fill=fill, outline=out,
                          width=int(p["lw"] * PX / 72))
            elif t == "line":
                x1, y1, x2, y2 = (p[k] * PX for k in ("x1", "y1", "x2", "y2"))
                col = parse(p["color"])
                lw = max(1, int(p["lw"] * PX / 72))
                d.line((x1, y1, x2, y2), fill=col, width=lw)
                if p["arrow"]:
                    import math
                    ang = math.atan2(y2 - y1, x2 - x1)
                    L, Wd = 0.10 * PX, 0.055 * PX
                    p1 = (x2, y2)
                    p2 = (x2 - L * math.cos(ang) + Wd * math.sin(ang),
                          y2 - L * math.sin(ang) - Wd * math.cos(ang))
                    p3 = (x2 - L * math.cos(ang) - Wd * math.sin(ang),
                          y2 - L * math.sin(ang) + Wd * math.cos(ang))
                    d.polygon([p1, p2, p3], fill=col)
            elif t == "pic":
                x, y, w, h = (p[k] * PX for k in ("x", "y", "w", "h"))
                img.paste(cover(os.path.join(HERE, p["path"]), p["w"], p["h"]),
                          (int(x), int(y)))
            elif t == "text":
                _text(d, p)
        img = img.resize((W // SS, H // SS), Image.LANCZOS)
        fp = os.path.join(outdir, "slide-%02d.png" % idx)
        img.save(fp)
        made.append(fp)
    return made


def _draw_run(d, xy, text, pt, bold, italic, col, anchor="la", spc=0):
    """Draw text honouring per-glyph font fallback AND letter tracking.

    spc is hundredths of a point, exactly as OOXML stores it. This must be
    honoured or the preview will happily show a layout that PowerPoint
    destroys via runaway tracking."""
    x, y = xy
    extra = (spc / 100.0) * PX / 72.0 if spc else 0.0
    for chunk, fb in TM.runs(text, (pt, bold, italic)):
        f = font(pt, bold, italic, fb)
        if not extra:
            d.text((x, y), chunk, font=f, fill=col, anchor=anchor)
            x += f.getlength(chunk)
        else:
            for ch in chunk:
                d.text((x, y), ch, font=f, fill=col, anchor=anchor)
                x += f.getlength(ch) + extra


def _run_width(text, pt, bold, italic, spc=0):
    extra = (spc / 100.0) * PX / 72.0 * len(text) if spc else 0.0
    return TM.width(text, pt, bold, italic) + extra


def wrap_tracked(text, pt, b, i, maxpx, spc):
    """Word-wrap that accounts for letter tracking."""
    extra = (spc / 100.0) * PX / 72.0 if spc else 0.0
    out = []
    for raw in str(text).split("\n"):
        if not raw:
            out.append("")
            continue
        cur = ""
        for word in raw.split(" "):
            cand = (cur + " " + word) if cur else word
            if TM.width(cand, pt, b, i) + extra * len(cand) <= maxpx or not cur:
                cur = cand
            else:
                out.append(cur)
                cur = word
        out.append(cur)
    return out


def _text(d, p):
    x, y, w, h = (p[k] * PX for k in ("x", "y", "w", "h"))
    blocks = []
    total = 0.0
    for it in p["items"]:
        pt = it.get("size", 12)
        b, i = it.get("b", False), it.get("i", False)
        spc = it.get("spc") or 0
        if p.get("wrap", True):
            lines = wrap_tracked(it["t"], pt, b, i, w, spc)
        else:
            lines = str(it["t"]).split("\n")
        lh = pt * 1.215 * PX / 72.0
        sb = it.get("sb", 0) * PX / 72.0
        sa = it.get("sa", 0) * PX / 72.0
        total += sb + len(lines) * lh * it.get("ls", 1.0) + sa
        blocks.append((it, lines, lh, sb, sa, pt, b, i))
    if p["anchor"] == "m":
        cy = y + (h - total) / 2.0
    elif p["anchor"] == "b":
        cy = y + h - total
    else:
        cy = y
    for it, lines, lh, sb, sa, pt, b, i in blocks:
        cy += sb
        align = it.get("a", "l")
        col = parse(it.get("c", "#334155"))
        for ln in lines:
            lw_ = _run_width(ln, pt, b, i, it.get("spc") or 0)
            if align == "c":
                lx = x + (w - lw_) / 2.0
            elif align == "r":
                lx = x + w - lw_
            else:
                lx = x
            _draw_run(d, (lx, cy), ln, pt, b, i, col, spc=it.get("spc") or 0)
            cy += lh * it.get("ls", 1.0)
        cy += sa


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "deck.json"
    out = sys.argv[2] if len(sys.argv) > 2 else "preview"
    with open(os.path.join(HERE, src)) as fh:
        deck = json.load(fh)
    for f in render(deck, os.path.join(HERE, out)):
        print("wrote", f)
