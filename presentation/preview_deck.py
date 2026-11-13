"""
Approximate renderer for .pptx -> PNG, used only for layout QA.

It is NOT a PowerPoint clone. It re-draws every shape in z-order using
PIL with DejaVu (deliberately a little wider than Segoe UI, so anything that
fits here fits in PowerPoint), and — importantly — it lets text spill out of
its box the way PowerPoint does, and grows table rows the way PowerPoint does.
That makes overflow and collision visible in a still image.
"""
import io
import os
import sys

from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.enum.dml import MSO_FILL
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Emu

PX = 96.0
EMU_PER_PX = 914400.0 / PX


def px(v):
    return float(v) / EMU_PER_PX


FONT_DIR = "/usr/share/fonts/truetype/dejavu"
_fcache = {}


def font(name, size_pt, bold=False, italic=False):
    key = (bold, italic, round(size_pt, 2))
    if key in _fcache:
        return _fcache[key]
    f = "DejaVuSans"
    if bold and italic:
        f = "DejaVuSans-BoldOblique"
    elif bold:
        f = "DejaVuSans-Bold"
    elif italic:
        f = "DejaVuSans-Oblique"
    path = os.path.join(FONT_DIR, f + ".ttf")
    if not os.path.exists(path):
        path = os.path.join(FONT_DIR, "DejaVuSans.ttf")
    try:
        ft = ImageFont.truetype(path, max(1, int(round(size_pt * PX / 72.0))))
    except Exception:
        ft = ImageFont.load_default()
    _fcache[key] = ft
    return ft


def rgb(color):
    try:
        return tuple(color.rgb)
    except Exception:
        return (255, 255, 255)


def shape_fill(sh):
    try:
        if sh.fill.type == MSO_FILL.SOLID:
            return rgb(sh.fill.fore_color), 255
    except Exception:
        pass
    return None, 0


def shape_line(sh):
    try:
        if sh.line.fill.type == MSO_FILL.SOLID and sh.line.width:
            return rgb(sh.line.color), max(1, int(round(px(sh.line.width))))
    except Exception:
        pass
    return None, 0


def wrap_lines(text, ft, maxw):
    out = []
    for raw in text.split("\n"):
        if raw == "":
            out.append(("", 0))
            continue
        words = raw.split(" ")
        cur = ""
        for w in words:
            trial = w if not cur else cur + " " + w
            if ft.getlength(trial) <= maxw or not cur:
                cur = trial
            else:
                out.append((cur, ft.getlength(cur)))
                cur = w
        out.append((cur, ft.getlength(cur)))
    return out


def para_metrics(p, default_size=18):
    runs = p.runs
    if not runs:
        return default_size, False, False, (255, 255, 255), 0
    sizes, bolds, itals, colors, spc = [], [], [], [], 0
    for r in runs:
        f = r.font
        sizes.append(f.size.pt if f.size else default_size)
        bolds.append(bool(f.bold))
        itals.append(bool(f.italic))
        try:
            colors.append(rgb(f.color) if f.color and f.color.rgb else (255, 255, 255))
        except Exception:
            colors.append((255, 255, 255))
    return max(sizes), any(bolds), itals[0] if itals else False, colors[0], spc


def draw_textframe(draw, img, tf, x, y, w, h, anchor_top=True, valign=None):
    """returns the height actually used (may exceed h)"""
    ml = px(tf.margin_left or 0)
    mr = px(tf.margin_right or 0)
    mt = px(tf.margin_top or 0)
    mb = px(tf.margin_bottom or 0)
    inner_w = max(4.0, w - ml - mr)
    wrap = tf.word_wrap is not False

    laid = []   # (text, font, color, x_off, baseline_y_within_para, paraspace)
    total = 0.0
    for p in tf.paragraphs:
        size, bold, ital, colr, _ = para_metrics(p)
        ft = font(None, size, bold, ital)
        spacing = p.line_spacing if p.line_spacing else 1.0
        if isinstance(spacing, float) and spacing <= 0:
            spacing = 1.0
        lh = size * PX / 72.0 * 1.22 * (spacing if isinstance(spacing, float) else 1.0)
        sb = (p.space_before.pt if p.space_before else 0) * PX / 72.0
        sa = (p.space_after.pt if p.space_after else 0) * PX / 72.0
        text = "".join(r.text for r in p.runs)
        align = p.alignment
        lines = wrap_lines(text, ft, inner_w) if wrap else [(ln, ft.getlength(ln)) for ln in text.split("\n")]
        total += sb
        for ln, lnw in lines:
            laid.append((ln, ft, colr, lnw, align, size, lh))
            total += lh
        total += sa

    used = total + mt + mb
    if valign == MSO_ANCHOR.MIDDLE:
        cy = y + (h - used) / 2.0 + mt
    elif valign == MSO_ANCHOR.BOTTOM:
        cy = y + h - used + mt
    else:
        cy = y + mt
    for ln, ft, colr, lnw, align, size, lh in laid:
        if not ln.strip():
            cy += lh
            continue
        if align == PP_ALIGN.CENTER:
            tx = x + ml + (inner_w - lnw) / 2.0
        elif align == PP_ALIGN.RIGHT:
            tx = x + ml + (inner_w - lnw)
        else:
            tx = x + ml
        asc, desc = ft.getmetrics()
        draw.text((tx, cy + (lh - (asc + desc)) / 2.0), ln, font=ft, fill=colr)
        cy += lh
    return used


def draw_rect_shape(draw, sh, x, y, w, h):
    fill, _ = shape_fill(sh)
    line, lw = shape_line(sh)
    if fill is None and line is None:
        return
    st = str(sh.shape_type)
    is_oval = "OVAL" in str(getattr(sh, "name", "")) or False
    try:
        from pptx.enum.shapes import MSO_SHAPE
        is_oval = sh.auto_shape_type == MSO_SHAPE.OVAL
    except Exception:
        pass
    if is_oval:
        draw.ellipse([x, y, x + w, y + h], fill=fill, outline=line, width=lw or 0)
        return
    rad = 0
    try:
        if sh.auto_shape_type is not None and "ROUNDED" in str(sh.auto_shape_type):
            try:
                adj = sh.adjustments[0]
            except Exception:
                adj = 0.16
            rad = min(w, h) * max(0.0, min(0.5, adj))
    except Exception:
        pass
    if rad > 0.5:
        draw.rounded_rectangle([x, y, x + w, y + h], radius=rad, fill=fill,
                               outline=line, width=lw or 0)
    else:
        draw.rectangle([x, y, x + w, y + h], fill=fill, outline=line, width=lw or 0)


def render(path, outdir, scale=1.0):
    prs = Presentation(path)
    W = int(round(px(prs.slide_width) * scale))
    H = int(round(px(prs.slide_height) * scale))
    os.makedirs(outdir, exist_ok=True)
    reports = []
    for idx, slide in enumerate(prs.slides, start=1):
        img = Image.new("RGB", (W, H), (14, 16, 20))
        draw = ImageDraw.Draw(img)
        problems = []
        occupied = []
        for sh in slide.shapes:
            try:
                x, y = px(sh.left) * scale, px(sh.top) * scale
                w, h = px(sh.width) * scale, px(sh.height) * scale
            except Exception:
                continue
            t = sh.shape_type
            if t == MSO_SHAPE_TYPE.PICTURE:
                try:
                    pic = Image.open(io.BytesIO(sh.image.blob)).convert("RGB")
                    nw = max(1, int(w)); nh = max(1, int(h))
                    pic = pic.resize((nw, nh), Image.LANCZOS)
                    img.paste(pic, (int(x), int(y)))
                except Exception:
                    draw.rectangle([x, y, x + w, y + h], outline=(255, 0, 255), width=2)
                continue
            if t == MSO_SHAPE_TYPE.LINE or "CONNECTOR" in str(t):
                line, lw = shape_line(sh)
                if line:
                    draw.line([x, y, x + w, y + h], fill=line, width=lw)
                continue
            if t == MSO_SHAPE_TYPE.TABLE:
                tbl = sh.table
                cols = [px(c.width) * scale for c in tbl.columns]
                # PowerPoint grows rows to fit; emulate that
                rows_h = []
                cell_text = []
                for r_i, row in enumerate(tbl.rows):
                    need = px(row.height) * scale
                    cells = []
                    for c_i, cell in enumerate(row.cells):
                        cw = cols[c_i] - px(cell.margin_left or 0) * scale - px(cell.margin_right or 0) * scale
                        tf = cell.text_frame
                        hh = 0.0
                        for p in tf.paragraphs:
                            size, bold, ital, colr, _ = para_metrics(p, 9)
                            ft = font(None, size, bold, ital)
                            txt = "".join(rn.text for rn in p.runs)
                            hh += len(wrap_lines(txt, ft, max(4, cw))) * (size * PX / 72.0 * 1.22 * (p.line_spacing if isinstance(p.line_spacing, float) else 1.0))
                        hh += px(cell.margin_top or 0) * scale + px(cell.margin_bottom or 0) * scale
                        cells.append((cell, cw, hh))
                        need = max(need, hh)
                    rows_h.append(need)
                    cell_text.append(cells)
                yy = y
                for r_i, row in enumerate(tbl.rows):
                    xx = x
                    for c_i, cell in enumerate(row.cells):
                        f2, _ = (None, 0)
                        try:
                            f2 = rgb(cell.fill.fore_color)
                        except Exception:
                            f2 = (30, 34, 43)
                        draw.rectangle([xx, yy, xx + cols[c_i], yy + rows_h[r_i]], fill=f2)
                        draw_textframe(draw, img, cell.text_frame, xx, yy, cols[c_i], rows_h[r_i],
                                       valign=cell.vertical_anchor)
                        xx += cols[c_i]
                    yy += rows_h[r_i]
                bottom = y + sum(rows_h)
                if abs(sum(rows_h) - h) > 2:
                    problems.append(("TABLE-GROWS", round(sum(rows_h) - h, 1), round(y, 1), round(bottom, 1)))
                occupied.append((x, y, x + w, bottom, "table"))
                continue
            if t == MSO_SHAPE_TYPE.AUTO_SHAPE:
                draw_rect_shape(draw, sh, x, y, w, h)
            if sh.has_text_frame and sh.text_frame.text.strip():
                used = draw_textframe(draw, img, sh.text_frame, x, y, w, h,
                                      valign=sh.text_frame.vertical_anchor)
                if used > h + 1.0:
                    problems.append(("TEXT-OVERFLOW", round(used - h, 1), round(y, 1), round(y + used, 1)))
                occupied.append((x, y, x + w, y + max(h, used), "text"))
            elif t == MSO_SHAPE_TYPE.AUTO_SHAPE:
                occupied.append((x, y, x + w, y + h, "shape"))
            if sh.has_text_frame and sh.text_frame.text.strip() and w < SW_LIMIT:
                pass
        # crude collision check on text blocks that grew
        grew = [o for o in occupied if o[4] == "text"]
        for a in range(len(grew)):
            for b in range(a + 1, len(grew)):
                A, B = grew[a], grew[b]
                ox = min(A[2], B[2]) - max(A[0], B[0])
                oy = min(A[3], B[3]) - max(A[1], B[1])
                if ox > 6 and oy > 6:
                    problems.append(("TEXT-COLLIDE", round(ox, 1), round(A[1], 1), round(A[3], 1)))
        out = os.path.join(outdir, f"slide_{idx:02d}.png")
        img.save(out)
        if problems:
            seen, uniq = set(), []
            for p in problems:
                k = (p[0], round(p[1]))
                if k in seen:
                    continue
                seen.add(k); uniq.append(p)
            reports.append((idx, uniq))
    return reports


SW_LIMIT = 5000

if __name__ == "__main__":
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "/tmp/preview"
    reps = render(src, out, scale=1.0)
    print(f"rendered to {out}")
    if not reps:
        print("no layout problems detected")
    for idx, probs in reps:
        print(f"slide {idx:02d}: " + "; ".join(f"{p[0]} {p[1]}px{y1}" for p in probs for y1 in [f" @y={p[2]}"]))
