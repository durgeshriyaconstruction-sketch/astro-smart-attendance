# Worksheet build

`Creative-Ideation-Worksheet-Astro-Smart-Attendance.pdf` is generated with ReportLab.

```bash
pip install reportlab fonttools
python3 scripts/build_worksheet.py
```

Fonts (Poppins, Inter, Caveat, JetBrains Mono) are read from `WS_FONT_DIR` (default `/home/user/fonts`)
as `.ttf` files converted from the Fontsource packages. Missing glyphs fall back to DejaVu Sans.
