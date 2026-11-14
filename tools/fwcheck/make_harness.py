#!/usr/bin/env python3
"""Builds harness.cpp: the lines tools/patch_firmware_sync.py added to main.cpp,
copied out of the patched file byte for byte, inside stand-ins for the rest of
the firmware. Usage: make_harness.py <patched main.cpp> <harness.template.cpp> <out.cpp>"""
import sys

src = open(sys.argv[1], encoding="utf-8", newline="").read().replace("\r\n", "\n")
template = open(sys.argv[2], encoding="utf-8").read()


def between(start, end, include_end=False):
    i = src.index(start)
    j = src.index(end, i)
    return src[i:j + (len(end) if include_end else 0)]


parts = {
    "STEP": between("  } else if (current == 1) {\n", "  } else if (current == 2) {\n"),
    "TAIL": between("  if (changed) {\n    Data::recountAll();\n    Data::markCloudAck();\n    Data::generation++;",
                    "}\n\n// ASTRO-SYNC-2: once a minute"),
    "REPORT": between("// ASTRO-SYNC-2: once a minute tell the cloud", "static void safePull() {"),
    "SYNC": between("  String syncReply;\n", "  for (auto& t : sentTombs)"),
    "JSONSTR": between('static String jsonStr(JsonVariantConst v, const String& def = "") {', "}\n", True),
    "UPPER": between("static String upper(String s) {", "}\n", True),
}
for must in ("lastError = syncRejected;   // ASTRO-SYNC-2", "reportDeviceStatus();   // ASTRO-SYNC-2"):
    if must not in src:
        sys.exit("not a patched main.cpp: missing " + must)
for key, text in parts.items():
    template = template.replace("@@" + key + "@@\n", text)
open(sys.argv[3], "w", encoding="utf-8").write(template)
