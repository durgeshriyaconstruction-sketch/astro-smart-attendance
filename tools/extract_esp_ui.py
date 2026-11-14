#!/usr/bin/env python3
"""
Regenerate web/astro-ui.css from the UI embedded in the firmware.

main.cpp ships its entire dashboard as a gzipped byte array (UI_GZ) in PROGMEM.
This pulls those bytes out, gunzips them, and extracts the <style> block so the
cloud page uses the *same* stylesheet as the device page instead of a lookalike.

Usage:
    python3 tools/extract_esp_ui.py firmware/esp32/main.cpp web/astro-ui.css

It also writes the full decompressed UI to /tmp/esp_ui.html for reference.
"""

import gzip
import re
import sys
from pathlib import Path


def extract(main_cpp: Path) -> bytes:
    src = main_cpp.read_text(encoding="utf-8", errors="replace")
    start = src.index("const uint8_t UI_GZ[] PROGMEM")
    end = src.index("};", start)
    hexes = re.findall(r"0x([0-9A-Fa-f]{2})", src[start:end])
    if not hexes:
        raise SystemExit("no bytes found in UI_GZ")
    return bytes(int(h, 16) for h in hexes)


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2

    main_cpp = Path(sys.argv[1])
    out_css = Path(sys.argv[2])

    raw = gzip.decompress(extract(main_cpp))
    html = raw.decode("utf-8", errors="replace")
    Path("/tmp/esp_ui.html").write_text(html, encoding="utf-8")

    m = re.search(r"<style>(.*?)</style>", html, re.S)
    if not m:
        raise SystemExit("<style> block not found in the decompressed UI")

    out_css.write_text(
        "/* Astro Smart Attendance - design system extracted verbatim from the\n"
        "   ESP32 firmware UI blob (UI_GZ) so the cloud page matches the device page. */\n"
        + m.group(1),
        encoding="utf-8",
    )
    print(f"decompressed UI : {len(raw):,} bytes -> /tmp/esp_ui.html")
    print(f"stylesheet      : {len(m.group(1)):,} bytes -> {out_css}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
