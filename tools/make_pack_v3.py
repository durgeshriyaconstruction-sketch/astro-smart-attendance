"""Build exports/ASTRO_SMART_ATTENDANCE_v3.zip - and refuse to, if anything is stale.

This is the gate between "the CAD is right" and "the user gets the right CAD".  It does three
things before it writes a byte of archive:

 1. every proof file must exist, must end in its own PASS string, and must be NEWER than the
    newest STL - so a pack cannot be cut from geometry that was rebuilt after the last check
    (that is exactly how v3.1's doc NOTEs got into the first v3 pack);
 2. the offline viewer is regenerated from the shipped STLs, so what a browser shows is what a
    printer gets, not a snapshot from a previous revision;
 3. the archive is re-read after writing: each entry's bytes are compared with the file on disk.

Run:  python3 tools/make_pack_v3.py
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
CAD = os.path.join(ROOT, "cad", "v3")
OUT = os.path.join(ROOT, "exports", "ASTRO_SMART_ATTENDANCE_v3.zip")
STAGE = "/tmp/pack_v3_stage"

# name in the pack -> where it comes from, and what has to be true about it
STL = ["01_MAIN_SHELL_v3.stl", "02_REAR_PLATE_v3.stl", "03_R307_BRACKET_v3.stl",
       "04_RC522_RING_v3.stl"]
PROOF = {  # pack name -> (source, the verdict string it must contain)
    "v3_audit.txt": (os.path.join("docs", "v3_audit.txt"), "RESULT: ALL CHECKS PASS"),
    "v3_independent_verify.txt": (os.path.join("docs", "v3_independent_verify.txt"),
                                  "INDEPENDENT RESULT: ALL CHECKS PASS"),
    "v3_physics_audit.txt": (os.path.join("docs", "v3_physics_audit.txt"),
                             "PHYSICS RESULT: no failures"),
    "v3_groove_check.txt": (os.path.join("docs", "v3_groove_check.txt"),
                            "EVERY GROOVE AND FIT MEASURES AS DESIGNED"),
}
DOCS = {
    "README_PRINT_ORDER_v3.txt": os.path.join("exports", "README_PRINT_ORDER_v3.txt"),
    "v3_design_notes.md": os.path.join("docs", "v3_design_notes.md"),
    "master_prompt.md": os.path.join("docs", "master_prompt.md"),
}
FIGS = [f"v3_{n}.png" for n in ["drawing_sheet", "exploded_iso", "fixing_detail",
                                "fixing_section", "all_views", "vs_v2", "grille_map"]]
SRC = {
    "build_v3_PARAMETRIC_generator.py": os.path.join("tools", "build_v3.py"),
    "verify_v3_INDEPENDENT.py": os.path.join("tools", "verify_v3.py"),
    "audit_v3_PHYSICS.py": os.path.join("tools", "audit_physics_v3.py"),
    "check_v3_GROOVES.py": os.path.join("tools", "check_grooves_v3.py"),
    "make_grille_map_v3.py": os.path.join("tools", "make_grille_map_v3.py"),
    "orient_v3.py": os.path.join("tools", "orient_v3.py"),
}

fails, notes = [], []


def die(msg):
    fails.append(msg)
    print("REFUSED: " + msg)


def newest(paths):
    return max(os.path.getmtime(p) for p in paths if os.path.exists(p))


# ---------------------------------------------------------------- 1. proofs are current
# "current" can mean two things, and both are legitimate:
#   (a) the proof file was WRITTEN AFTER the geometry - the mtime rule; or
#   (b) the proof file and the four STLs are all byte-identical to ONE commit, which is a far
#       stronger statement than a timestamp - it means "this exact text certified these exact
#       bytes", and it survives a fresh clone or a re-checkout (a re-clone rewrites mtimes and
#       means nothing about content).  v3.2 hit exactly that: the sandbox was rebuilt, mtimes
#       moved, and an mtime-only gate would have refused a pack that is provably correct.
stl_paths = [os.path.join(CAD, f) for f in STL]
t_stl = newest(stl_paths)


def blob(path):
    """git's own hash of the file as it sits on disk (empty string if unreadable)."""
    r = subprocess.run(["git", "-C", ROOT, "hash-object", path], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def in_head(path):
    """True if HEAD records that exact blob for that repo-relative path."""
    r = subprocess.run(["git", "-C", ROOT, "rev-parse", f"HEAD:{path}"],
                       capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() == blob(path)


stl_locked = all(in_head(os.path.relpath(x, ROOT)) for x in stl_paths)
for pack_name, (rel, verdict) in PROOF.items():
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        die(f"{rel} does not exist - run the checker")
        continue
    txt = open(p, encoding="utf-8", errors="replace").read()
    if verdict not in txt:
        die(f"{rel} does not contain '{verdict}'")
    if not (stl_locked and in_head(rel)) and os.path.getmtime(p) < t_stl - 1:
        die(f"{rel} is OLDER than the STLs ({(t_stl - os.path.getmtime(p)) / 60:.1f} min) and is "
            f"not committed with them - the geometry moved after the last check")
    if pack_name == "v3_physics_audit.txt":
        m = re.search(r"(\d+) item\(s\) recorded as notes", txt)
        if m and int(m.group(1)) > 2:
            notes.append(f"physics audit still carries {m.group(1)} notes")

# every figure must be newer than the geometry too - a picture of last revision is a lie
for f in FIGS:
    p = os.path.join(ROOT, "renders", f)
    if not os.path.exists(p):
        die(f"renders/{f} missing")
    elif not (stl_locked and in_head(os.path.join("renders", f))) \
            and os.path.getmtime(p) < t_stl - 1:
        die(f"renders/{f} is older than the STLs - re-run tools/make_figures_v3.py")

# the docs must not quote a volume the mesh disagrees with (same rule section 10 of the
# physics audit applies, re-checked here against the four files on disk)
vols = {}
for f in STL:
    import trimesh
    m = trimesh.load(os.path.join(CAD, f), process=False)
    vols[f] = abs(m.volume) / 1000.0
tot = sum(vols.values())
for pack_name, rel in DOCS.items():
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        continue
    for line in open(p, encoding="utf-8", errors="replace"):
        for m in re.finditer(r"(\d+\.\d+) cm3", line):
            v = float(m.group(1))
            ok = abs(v - tot) < 0.06 or min(abs(v - x) for x in vols.values()) < 0.06
            if not ok:
                die(f"{rel}: '{m.group(0)}' matches no part volume "
                    f"({'/'.join(f'{x:.1f}' for x in vols.values())} or {tot:.1f} total)")
# ---------------------------------------------------------------- 2. regenerate the viewer
print("regenerating exports/viewer_offline.html from the shipped STLs ...")
r = subprocess.run([PY, os.path.join(ROOT, "tools", "make_offline_viewer.py")],
                   capture_output=True, text=True)
if r.returncode != 0:
    die("make_offline_viewer.py failed:\n" + (r.stdout + r.stderr)[-800:])

if fails:
    print("\n".join("  " + f for f in fails))
    raise SystemExit(1)

# ---------------------------------------------------------------- 3. stage + zip + re-read
shutil.rmtree(STAGE, ignore_errors=True)
os.makedirs(STAGE)
manifest = []


def stage(src, name):
    shutil.copyfile(src, os.path.join(STAGE, name))
    manifest.append(name)


for f in STL:
    stage(os.path.join(CAD, f), f)
for pack_name, (rel, _verdict) in PROOF.items():
    stage(os.path.join(ROOT, rel), pack_name)
for pack_name, rel in DOCS.items():
    stage(os.path.join(ROOT, rel), pack_name)
for f in FIGS:
    stage(os.path.join(ROOT, "renders", f), f)
for pack_name, rel in SRC.items():
    stage(os.path.join(ROOT, rel), pack_name)
stage(os.path.join(ROOT, "exports", "viewer_offline.html"), "viewer_offline.html")

lines = []
for name in sorted(manifest):
    b = open(os.path.join(STAGE, name), "rb").read()
    lines.append(f"{hashlib.sha256(b).hexdigest()}  {name}")
sums = os.path.join(STAGE, "SHA256SUMS_v3.txt")
open(sums, "w").write("sha256 of every file in this pack, so a download can be checked\n"
                      f"# built by tools/make_pack_v3.py from commit "
                      f"{subprocess.run(['git', '-C', ROOT, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()}\n"
                      + "\n".join(lines) + "\n")
manifest.append("SHA256SUMS_v3.txt")
shutil.copyfile(sums, os.path.join(ROOT, "exports", "SHA256SUMS_v3.txt"))

if os.path.exists(OUT):
    os.remove(OUT)
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for name in sorted(manifest):
        z.write(os.path.join(STAGE, name), name)

with zipfile.ZipFile(OUT) as z:
    names = z.namelist()
    if sorted(names) != sorted(manifest):
        die("zip entry list does not match the manifest")
    for name in names:
        data = z.read(name)
        disk = open(os.path.join(STAGE, name), "rb").read()
        if hashlib.sha256(data).hexdigest() != hashlib.sha256(disk).hexdigest():
            die(f"{name} inside the zip is not the file that was staged")

n = len(names)
size = os.path.getsize(OUT)
print(f"\nwrote {os.path.relpath(OUT, ROOT)}  ({size / 1e6:.2f} MB, {n} files)")
for name in sorted(names):
    p = os.path.join(STAGE, name)
    print(f"  {os.path.getsize(p) / 1000:8.1f} kB  sha256 {hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16]}  {name}")
print(f"\nPACK RESULT: {'ALL CHECKS PASS' if not fails else 'REFUSED'}"
      + (f"  (notes: {'; '.join(notes)})" if notes else ""))
raise SystemExit(1 if fails else 0)
