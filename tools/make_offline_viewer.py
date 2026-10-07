"""Build a fully self-contained offline viewer: viewer.html + the STLs embedded as base64.

The result (exports/viewer_offline.html) opens by double-clicking - no web server, no
internet, no sandbox. It is the same viewer as the live preview, only with the part data
carried inside the file.
"""
import base64
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "viewer.html")
OUT = os.path.join(ROOT, "exports", "viewer_offline.html")

FILES = ["cad/v2/01_MAIN_SHELL_v2.stl", "cad/v2/02_REAR_PLATE_v2.stl",
         "cad/v2/03_R307_BRACKET_v2.stl", "cad/v2/04_RC522_CLAMP_v2.stl",
         "cad/01_MAIN_SHELL.stl", "cad/02_DETACHABLE_WALL_PLATE.stl",
         "cad/03_R307_RETENTION.stl", "cad/04_RC522_RETENTION.stl",
         "cad/05_ESP32_RETENTION.stl"]

html = open(SRC, encoding="utf-8").read()

# 1. embed the data
chunks = ["const EMBEDDED = {"]
for f in FILES:
    p = os.path.join(ROOT, f)
    if not os.path.exists(p):
        continue
    b64 = base64.b64encode(open(p, "rb").read()).decode("ascii")
    chunks.append(f'  "{f}": "{b64}",')
chunks.append("};")
embedded = "\n".join(chunks)

# 2. decode helper + route the loader through it
helper = """
function b64ToBuf(b64){
  const bin = atob(b64);
  const u8 = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
  return u8.buffer;
}
"""
old_load = """    const r = await fetch(def.file);
    if (!r.ok){ console.warn('missing', def.file); continue; }
    const flat = parseSTL(await r.arrayBuffer());"""
new_load = """    let buf;
    if (typeof EMBEDDED !== 'undefined' && EMBEDDED[def.file]) buf = b64ToBuf(EMBEDDED[def.file]);
    else { const r = await fetch(def.file); if (!r.ok){ console.warn('missing', def.file); continue; } buf = await r.arrayBuffer(); }
    const flat = parseSTL(buf);"""
assert old_load in html
html = html.replace(old_load, new_load, 1)
html = html.replace("<script>\nconst PART_DEFS", "<script>\n" + embedded + "\n" + helper + "\nconst PART_DEFS", 1)

# 3. cosmetics
html = html.replace("<title>Astro Smart Attendance — Enclosure Viewer</title>",
                    "<title>Astro Smart Attendance — Enclosure v2 (offline viewer)</title>", 1)
html = html.replace("Drag = rotate · Wheel = zoom · Shift-drag = pan · Double-click = reset",
                    "OFFLINE FILE — all parts embedded, works without a server<br/>"
                    "Drag = rotate · Wheel = zoom · Shift-drag = pan · Double-click = reset", 1)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w", encoding="utf-8").write(html)
print(f"wrote {OUT}  ({os.path.getsize(OUT)/1e6:.2f} MB, {len(FILES)} parts embedded)")
