#!/usr/bin/env python3
"""
Generates the hand-drawn accents used by both deliverables.

Everything is drawn as a small transparent PNG with slightly wobbly strokes, so
it reads as a real pen doodle rather than clip art. Both the PDF (reportlab) and
the Word file (python-docx) place these same files, which keeps the two
documents visually identical.
"""
import math
import os
import random

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "assets")
FONT_DIR = "/home/user/fonts"
HAND = os.path.join(FONT_DIR, "caveat-latin-700-normal.ttf")
POP = os.path.join(FONT_DIR, "poppins-latin-800-normal.ttf")

NAVY = (11, 31, 74, 255)
SAFFRON = (255, 122, 24, 255)
TEAL = (14, 165, 164, 255)
GOLD = (255, 183, 3, 255)
GREEN = (22, 163, 74, 255)
RED = (220, 38, 38, 255)
PURPLE = (124, 58, 237, 255)
INK = (30, 41, 59, 255)

S = 3  # supersampling


def canvas(w, h):
    im = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def finish(im, w, h, name):
    im = im.resize((w, h), Image.LANCZOS)
    im.save(os.path.join(OUT, name))
    return name


def wobble(points, amp=1.2, seed=1):
    """Nudge a polyline so it looks hand-drawn."""
    rnd = random.Random(seed)
    return [(x + rnd.uniform(-amp, amp), y + rnd.uniform(-amp, amp)) for x, y in points]


def curve(p0, p1, lift=0.18, n=22):
    """Quadratic-ish arc between two points, for swooshy strokes."""
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    cx, cy = mx - dy * lift, my + dx * lift
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * cx + t ** 2 * p1[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * cy + t ** 2 * p1[1])
            for t in (i / n for i in range(n + 1))]


# ---------------------------------------------------------------- doodles
def doodle_arrow(name, w=120, h=54, color=SAFFRON, flip=False):
    im, d = canvas(w, h)
    pts = curve((6, h * 0.62), (w - 16, h * 0.40), lift=(-0.22 if not flip else 0.22))
    d.line(wobble([(x * S, y * S) for x, y in pts], 1.0, 3), fill=color, width=3 * S, joint="curve")
    tipx, tipy = pts[-1]
    for ang in (2.55, 3.75):
        ex = tipx + math.cos(ang) * 13
        ey = tipy + math.sin(ang) * 13
        d.line([(tipx * S, tipy * S), (ex * S, ey * S)], fill=color, width=3 * S)
    return finish(im, w, h, name)


def doodle_underline(name, w=220, h=18, color=GOLD):
    im, d = canvas(w, h)
    pts = curve((4, h * 0.6), (w - 4, h * 0.45), lift=0.12)
    d.line(wobble([(x * S, y * S) for x, y in pts], 0.9, 7), fill=color, width=4 * S, joint="curve")
    return finish(im, w, h, name)


def doodle_star(name, w=46, h=46, color=GOLD):
    im, d = canvas(w, h)
    cx, cy, r = w / 2, h / 2, w * 0.36
    pts = []
    for i in range(11):
        ang = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + math.cos(ang) * rr, cy + math.sin(ang) * rr))
    d.line(wobble([(x * S, y * S) for x, y in pts], 1.4, 11), fill=color, width=3 * S, joint="curve")
    return finish(im, w, h, name)


def doodle_spark(name, w=40, h=40, color=SAFFRON):
    im, d = canvas(w, h)
    cx, cy = w / 2, h / 2
    for ang in (0, math.pi / 2, math.pi, -math.pi / 2, math.pi / 4, 3 * math.pi / 4,
                -math.pi / 4, -3 * math.pi / 4):
        r0, r1 = 4, w * 0.34
        d.line([((cx + math.cos(ang) * r0) * S, (cy + math.sin(ang) * r0) * S),
                ((cx + math.cos(ang) * r1) * S, (cy + math.sin(ang) * r1) * S)],
               fill=color, width=2 * S)
    return finish(im, w, h, name)


def doodle_bulb(name, w=64, h=64, color=GOLD):
    im, d = canvas(w, h)
    cx, cy = w / 2, h * 0.42
    r = w * 0.26
    d.ellipse([((cx - r) * S), ((cy - r) * S), ((cx + r) * S), ((cy + r) * S)],
              outline=color, width=3 * S)
    d.line([(cx * S, (cy + r) * S), (cx * S, (cy + r + h * 0.22) * S)], fill=color, width=3 * S)
    d.line([((cx - r * 0.45) * S, (cy + r + h * 0.24) * S),
            ((cx + r * 0.45) * S, (cy + r + h * 0.24) * S)], fill=color, width=3 * S)
    for ang in (-2.4, -1.2, 0, 1.2, 2.4):
        d.line([((cx + math.cos(ang) * (r + 6)) * S, (cy + math.sin(ang) * (r + 6)) * S),
                ((cx + math.cos(ang) * (r + 13)) * S, (cy + math.sin(ang) * (r + 13)) * S)],
               fill=color, width=2 * S)
    return finish(im, w, h, name)


def doodle_cross(name, w=40, h=40, color=RED):
    im, d = canvas(w, h)
    d.line([(7 * S, 7 * S), ((w - 7) * S, (h - 7) * S)], fill=color, width=4 * S)
    d.line([((w - 7) * S, 7 * S), (7 * S, (h - 7) * S)], fill=color, width=4 * S)
    return finish(im, w, h, name)


def doodle_tick(name, w=40, h=40, color=GREEN):
    im, d = canvas(w, h)
    pts = [(8, h * 0.55), (w * 0.4, h * 0.78), (w - 7, h * 0.22)]
    d.line(wobble([(x * S, y * S) for x, y in pts], 1.0, 5), fill=color, width=4 * S, joint="curve")
    return finish(im, w, h, name)


def doodle_finger(name, w=64, h=64, color=TEAL):
    """Concentric fingerprint whorls with a ridge tail — reads as a finger, not wifi."""
    im, d = canvas(w, h)
    cx, cy = w * 0.5, h * 0.46
    for i, r in enumerate((0.10, 0.18, 0.26, 0.33)):
        rr = w * r
        start_a = 300 + i * 18
        end_a = 240 - i * 12
        d.arc([((cx - rr) * S), ((cy - rr) * S), ((cx + rr) * S), ((cy + rr) * S)],
              start=start_a, end=end_a if end_a > start_a else end_a + 360,
              fill=color, width=3 * S)
    # the little ridge that runs off the bottom, as on a real print
    d.line([((cx - 2) * S, (cy + w * 0.30) * S), ((cx - 10) * S, (h * 0.90) * S)],
           fill=color, width=3 * S)
    d.line([((cx + 6) * S, (cy + w * 0.26) * S), ((cx + 2) * S, (h * 0.86) * S)],
           fill=color, width=2 * S)
    return finish(im, w, h, name)


def doodle_card(name, w=64, h=64, color=SAFFRON):
    im, d = canvas(w, h)
    d.rounded_rectangle([(9 * S), (16 * S), ((w - 9) * S), ((h - 16) * S)], radius=6 * S,
                        outline=color, width=3 * S)
    d.line([(9 * S, (h * 0.42) * S), ((w - 9) * S, (h * 0.42) * S)], fill=color, width=3 * S)
    return finish(im, w, h, name)


def doodle_cloud(name, w=70, h=46, color=TEAL):
    im, d = canvas(w, h)
    for (cx, cy, r) in ((w * 0.3, h * 0.55, h * 0.3), (w * 0.5, h * 0.42, h * 0.38),
                        (w * 0.72, h * 0.56, h * 0.29)):
        d.ellipse([((cx - r) * S), ((cy - r) * S), ((cx + r) * S), ((cy + r) * S)],
                  outline=color, width=3 * S)
    d.line([(w * 0.3 * S, (h * 0.85) * S), (w * 0.72 * S, (h * 0.85) * S)],
           fill=color, width=3 * S)
    return finish(im, w, h, name)


def doodle_wave(name, w=90, h=30, color=PURPLE):
    im, d = canvas(w, h)
    pts = [(x, h * 0.5 + math.sin(x / w * 4 * math.pi) * h * 0.22) for x in range(3, w - 2, 2)]
    d.line(wobble([(x * S, y * S) for x, y in pts], 0.5, 2), fill=color, width=2 * S, joint="curve")
    return finish(im, w, h, name)


def doodle_tape(name, w=110, h=34, color=(255, 214, 122, 190)):
    im, d = canvas(w, h)
    d.polygon([(4 * S, 8 * S), ((w - 6) * S, 4 * S), ((w - 3) * S, (h - 8) * S), (6 * S, (h - 4) * S)],
              fill=color)
    return finish(im, w, h, name)


def note(name, text, w=260, h=132, fill=(255, 240, 150, 255), ink=INK, angle=0):
    im, d = canvas(w, h)
    d.rounded_rectangle([(6 * S), (6 * S), ((w - 6) * S), ((h - 6) * S)], radius=4 * S, fill=fill)
    # a sticky-note fold in the corner
    d.polygon([((w - 30) * S, (h - 6) * S), ((w - 6) * S, (h - 30) * S), ((w - 6) * S, (h - 6) * S)],
              fill=(0, 0, 0, 18))
    f = ImageFont.truetype(HAND, 27 * S)
    lines, cur = [], ""
    for word in text.split():
        probe = (cur + " " + word).strip()
        if d.textlength(probe, font=f) > (w - 34) * S:
            lines.append(cur)
            cur = word
        else:
            cur = probe
    lines.append(cur)
    y = 26 * S
    for ln in lines:
        d.text((20 * S, y), ln, font=f, fill=ink)
        y += 31 * S
    if angle:
        im = im.rotate(angle, expand=True, resample=Image.BICUBIC)
    im = im.resize((int(im.width / S), int(im.height / S)), Image.LANCZOS)
    im.save(os.path.join(OUT, name))
    return name


def badge(name, label, fill=SAFFRON, text=(255, 255, 255, 255), w=180, h=48):
    im, d = canvas(w, h)
    d.rounded_rectangle([(3 * S), (3 * S), ((w - 3) * S), ((h - 3) * S)], radius=(h / 2) * S, fill=fill)
    f = ImageFont.truetype(POP, 17 * S)
    tw = d.textlength(label, font=f)
    d.text(((w * S - tw) / 2, (h * S - 17 * S) / 2 - 2 * S), label, font=f, fill=text)
    return finish(im, w, h, name)


def stamp(name, text, color=RED, w=210, h=76):
    im, d = canvas(w, h)
    d.rounded_rectangle([(5 * S), (5 * S), ((w - 5) * S), ((h - 5) * S)], radius=10 * S,
                        outline=color, width=3 * S)
    d.rounded_rectangle([(12 * S), (12 * S), ((w - 12) * S), ((h - 12) * S)], radius=7 * S,
                        outline=color, width=1 * S)
    f = ImageFont.truetype(POP, 20 * S)
    tw = d.textlength(text, font=f)
    d.text(((w * S - tw) / 2, (h * S - 20 * S) / 2 - 3 * S), text, font=f, fill=color)
    im = im.rotate(-7, expand=True, resample=Image.BICUBIC)
    im = im.resize((int(im.width / S), int(im.height / S)), Image.LANCZOS)
    im.save(os.path.join(OUT, name))
    return name


def circle_swoosh(name, w=240, h=110, color=SAFFRON):
    """A hand-drawn ellipse around something, with an arrow tail."""
    im, d = canvas(w, h)
    d.arc([(8 * S), (10 * S), ((w - 20) * S), ((h - 18) * S)], start=200, end=150,
          fill=color, width=3 * S)
    tail = curve((w - 60, h - 12), (w - 8, h - 26), lift=0.3)
    d.line([(x * S, y * S) for x, y in tail], fill=color, width=3 * S, joint="curve")
    return finish(im, w, h, name)


def build():
    os.makedirs(OUT, exist_ok=True)
    made = []
    made.append(doodle_arrow("arrow-saffron.png"))
    made.append(doodle_arrow("arrow-teal.png", color=TEAL))
    made.append(doodle_arrow("arrow-navy.png", color=NAVY))
    made.append(doodle_underline("underline-gold.png"))
    made.append(doodle_underline("underline-teal.png", color=TEAL))
    made.append(doodle_star("star-gold.png"))
    made.append(doodle_spark("spark-saffron.png"))
    made.append(doodle_bulb("bulb.png"))
    made.append(doodle_tick("tick.png"))
    made.append(doodle_cross("cross.png"))
    made.append(doodle_finger("finger.png"))
    made.append(doodle_card("card.png"))
    made.append(doodle_cloud("cloud.png"))
    made.append(doodle_wave("wave-purple.png"))
    made.append(doodle_tape("tape.png"))
    made.append(circle_swoosh("swoosh.png"))
    made.append(badge("badge-chosen.png", "CHOSEN", SAFFRON))
    made.append(badge("badge-idea.png", "OUR IDEA", TEAL))
    made.append(badge("badge-live.png", "WORKING PROTOTYPE", GREEN))
    made.append(stamp("stamp-rejected.png", "REJECTED", RED))
    made.append(note("note-1.png", "Two factors, one tap. No proxy.", fill=(255, 240, 150, 255), angle=-4))
    made.append(note("note-2.png", "Buffer first, cloud second.", fill=(198, 243, 240, 255), angle=3))
    made.append(note("note-3.png", "Parents hear it the same period.", fill=(255, 226, 199, 255), angle=-3))
    print(f"{len(made)} accents -> {OUT}")
    for m in made:
        p = os.path.join(OUT, m)
        print(f"  {m:26s} {os.path.getsize(p):>6} bytes  {Image.open(p).size}")


if __name__ == "__main__":
    build()
