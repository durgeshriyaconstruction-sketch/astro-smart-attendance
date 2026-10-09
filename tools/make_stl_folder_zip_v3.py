#!/usr/bin/env python3
"""
make_stl_folder_zip_v3.py - the friendly-name download: the four shipped STLs in one folder, renamed
for a person and a slicer instead of for a repository.

    01_MAIN_SHELL_v3.stl     ->  MAIN BODY.stl
    02_REAR_PLATE_v3.stl     ->  BACK PLATE.stl
    03_R307_BRACKET_v3.stl   ->  FINGER SENSOR HOLDER.stl
    04_RC522_RING_v3.stl     ->  CARD READER RING.stl

Renaming is a copy job, so the one thing that can go wrong is a changed byte.  This script therefore
gates itself on it: every file that goes into the archive must hash identically to the file in
cad/v3/, and cad/v3/ itself must still hash identically when the script finishes.  The orientation
notes are read from tools/orient_v3.py - the same table the pack was built with - and the print
settings are taken from the shipped README, so nothing here is retyped by hand.

Run:  python3 tools/make_stl_folder_zip_v3.py
"""
import hashlib
import io
import os
import shutil
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAD = os.path.join(ROOT, "cad", "v3")
OUT = os.path.join(ROOT, "exports", "ASTRO_SMART_ATTENDANCE_STL.zip")
REPORT = os.path.join(ROOT, "docs", "v3_stl_folder_zip.txt")
FOLDER = "ASTRO_SMART_ATTENDANCE"
STAGE = os.path.join(ROOT, "exports", ".stl_folder_stage")

RENAMES = [
    ("01_MAIN_SHELL_v3.stl", "MAIN BODY.stl"),
    ("02_REAR_PLATE_v3.stl", "BACK PLATE.stl"),
    ("03_R307_BRACKET_v3.stl", "FINGER SENSOR HOLDER.stl"),
    ("04_RC522_RING_v3.stl", "CARD READER RING.stl"),
]

L, F = [], []


def say(t=""):
    L.append(t)
    print(t, flush=True)


def chk(cond, what):
    say(f"   {what:<74} {'PASS' if cond else 'FAIL'}")
    if not cond:
        F.append(what)
    return bool(cond)


def sha(path):
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


say("ASTRO SMART ATTENDANCE v3 - friendly-name STL folder")
say("=" * 80)

# the source of truth for how each part sits on the bed, and for what the pack already promises
import orient_v3 as O                                          # noqa: E402

readme = io.open(os.path.join(ROOT, "exports", "README_PRINT_ORDER_v3.txt"),
                 encoding="utf-8").read().splitlines()
settings = next((ln for ln in readme if ln.startswith("PRINT  (")), "PRINT  (see PRINT ORDER.txt)")
sizes = {src: os.path.getsize(os.path.join(CAD, src)) for src, _ in RENAMES}
before = {src: sha(os.path.join(CAD, src)) for src, _ in RENAMES}

say("")
say("1. THE FOUR STLs, COPIED AND RENAMED (not converted, not re-meshed, not re-scaled)")
say("-" * 80)
for src, dst in RENAMES:
    dz, note = O.ORIENT[src]
    say(f"   {src:24} -> {dst:24} {sizes[src]:>9,} B   {note}")
say(f"   {settings.strip()}")

# ---------------------------------------------------------------- build
shutil.rmtree(STAGE, ignore_errors=True)
inner = os.path.join(STAGE, FOLDER)
os.makedirs(inner)

names_txt = [
    "FILE NAMES IN THIS FOLDER",
    "=" * 78,
    "These are the same four files the engineering pack ships, renamed so they read plainly on a",
    "shop PC.  Nothing was converted, re-meshed or scaled: each .stl below is byte-identical to its",
    "repo file, sha256 included in SHA256SUMS.txt.",
    "",
]
for src, dst in RENAMES:
    dz, note = O.ORIENT[src]
    shutil.copyfile(os.path.join(CAD, src), os.path.join(inner, dst))
    names_txt += [f"   {dst:24} = {src}",
                  f"   {'':24}   print it: {note}",
                  f"   {'':24}   sha256 {sha(os.path.join(CAD, src))}",
                  ""]
names_txt += [
    "HOW TO SET THE SLICER UP",
    "-" * 78,
    f"   {settings.strip()}",
    "   Every file is already lying flat on its first layer exactly as it should be printed, so in",
    "   the slicer do not rotate anything - just move them apart.  Bed: 180 x 180 mm is enough for",
    "   all four together.",
    "   Supports: off.  The only overhangs are under 3 mm of bridge (0.30 % of the shell).",
    "   Material: PLA is fine indoors.  If the box hangs in sun or in a closed room, use PETG or",
    "   anneal the parts - PLA softens around 60 C and an unshaded wall was modelled at 65 C.",
    "",
    "SCREWS (22 total, self-tapping for plastic, length measured under the head)",
    "-" * 78,
    "   4 x M3   x 10 mm  countersunk   back plate onto the shell",
    "   4 x M2.5 x  8 mm  pan           LCD1602 + I2C backpack",
    "   2 x M3   x  8 mm  pan or flat   fingerprint sensor bracket",
    "   4 x M2.5 x  4 mm  pan (small)   card reader ring",
    "   4 x M3   x 12 mm  pan           3010 fan  (x 20 if the fan holes go through its whole frame)",
    "   4 x M2.2 x  8 mm  pan           ESP32 board  (M2 x 8 if M2.2 is not stocked; never M2.5/M3)",
    "   + 4 cable ties 100 x 2.5 mm.  No nuts, no washers, no standoffs, no heat-set inserts.",
    "",
    "The full pack (proof reports, the 3D model, the parametric source, 10 figures) is",
    "ASTRO_SMART_ATTENDANCE_v3.zip in the same exports/ folder.  PRINT ORDER.txt is the long version",
    "of every instruction above, and it is the authority if the two ever disagree.",
    "",
]
io.open(os.path.join(inner, "FILE NAMES.txt"), "w", encoding="utf-8").write("\n".join(names_txt))
shutil.copyfile(os.path.join(ROOT, "exports", "README_PRINT_ORDER_v3.txt"),
                os.path.join(inner, "PRINT ORDER.txt"))

built = {}
for fn in sorted(os.listdir(inner)):
    built[fn] = os.path.join(inner, fn)
sums = ["sha256 of every file in this folder, so a download can be checked",
        f"written by tools/make_stl_folder_zip_v3.py ({len(built)} files)"]
for fn in sorted(built):
    sums.append(f"{sha(built[fn])}  {fn}")
io.open(os.path.join(inner, "SHA256SUMS.txt"), "w", encoding="utf-8").write("\n".join(sums) + "\n")
built["SHA256SUMS.txt"] = os.path.join(inner, "SHA256SUMS.txt")

if os.path.exists(OUT):
    os.remove(OUT)
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for fn in sorted(built):
        z.write(built[fn], f"{FOLDER}/{fn}")

# ---------------------------------------------------------------- gate
say("")
say("2. GATE - the archive must be the shipped bytes, and the shipped bytes must be untouched")
say("-" * 80)
with zipfile.ZipFile(OUT) as z:
    got = z.namelist()
    want = sorted(f"{FOLDER}/{f}" for f in built)
    chk(sorted(got) == want, f"the zip holds exactly {len(want)} files: 4 STLs, PRINT ORDER.txt,")
    if sorted(got) != want:
        say(f"      got: {got}")
    for src, dst in RENAMES:
        data = z.read(f"{FOLDER}/{dst}")
        chk(sha_bytes(data) == before[src],
            f"{dst:22} in the zip is byte-identical to cad/v3/{src}")
        chk(len(data) == sizes[src], f"{dst:22} is the same size ({sizes[src]:,} B), not re-written")
    chk(all(c.startswith(FOLDER + "/") for c in got),
        "everything unzips into one folder, not into loose files")
# the six condensed screw lines above were written by a person, so check them against the
# document they summarise: every qty / thread / length has to appear in the README's SCREWS section
import re                                                # noqa: E402
cond = re.findall(r"^   (\d) x (M[\d.]+)\s+x\s+(\d+) mm", "\n".join(names_txt), re.M)
chk(len(cond) == 6, f"{len(cond)} screw rows in FILE NAMES.txt (expected 6)")
i0 = next(i for i, ln in enumerate(readme) if ln.startswith("SCREWS"))
body = "\n".join(readme[i0:])
for q, th, ln in cond:
    tok = f"{q} x {th} x {ln}"
    chk(tok in body, f"'{tok}' is the length the shipped print order also recommends")
whole = "\n".join(readme)
for src, dst in RENAMES:
    chk(src in whole, f"{dst:22} is the README's {src} - same part, two names, both documents agree")
after = {src: sha(os.path.join(CAD, src)) for src, _ in RENAMES}
chk(after == before, "cad/v3/*.stl were not modified by this script (same four sha256 at exit)")
sz = os.path.getsize(OUT)
chk(150_000 < sz < 25_000_000, f"{os.path.basename(OUT)} is {sz:,} bytes - the four meshes, no padding")
say("")
say(f"   {os.path.basename(OUT)}  {sz:,} bytes, {len(built)} files")
say("   " + "\n   ".join(sums[2:]))
say("   " + f"{sha(built['SHA256SUMS.txt'])}  SHA256SUMS.txt   (this list, so it cannot contain itself)")
say("")
say("STL FOLDER ZIP: " + ("ALL CHECKS PASS" if not F else f"{len(F)} FAILURE(S)"))
shutil.rmtree(STAGE, ignore_errors=True)
io.open(REPORT, "w", encoding="utf-8").write("\n".join(L) + "\n")
raise SystemExit(1 if F else 0)
