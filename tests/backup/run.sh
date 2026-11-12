#!/usr/bin/env bash
# ============================================================================
#  tests/backup/run.sh — the backup script, with pg_dump and rclone stubbed.
#  Proves the wiring (what is dumped, where it is uploaded, what is pruned)
#  without a database or a cloud account.
#
#    bash tests/backup/run.sh
# ============================================================================
set -uo pipefail
cd "$(dirname "$0")/../.."
ROOT="$PWD"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass=0; fail=0
check() { # name, condition (0 = passed)
  if [ "$2" = "0" ]; then pass=$((pass+1)); printf 'ok   %s\n' "$1"
  else fail=$((fail+1)); printf 'FAIL %s\n' "$1"; fi
}
check_eq() { # name, expected, actual
  if [ "$2" = "$3" ]; then pass=$((pass+1)); printf 'ok   %s\n' "$1"
  else fail=$((fail+1)); printf 'FAIL %s — expected [%s] got [%s]\n' "$1" "$2" "$3"; fi
}
status() { if "$@" >/dev/null 2>&1; then echo 0; else echo 1; fi; }   # 0 = ok
has() { if grep -q -F -e "$1" "$2"; then echo 0; else echo 1; fi; }    # 0 = found
has_re() { if grep -q -E -e "$1" "$2"; then echo 0; else echo 1; fi; } # 0 = found
lacks() { if grep -q -F -e "$1" "$2"; then echo 1; else echo 0; fi; }  # 0 = absent
count() { ls "$@" 2>/dev/null | wc -l | tr -d ' '; }

mkdir -p "$TMP/bin" "$TMP/work"

# --- fake pg_dump: prints a recognisable "dump", records its arguments ------
cat > "$TMP/bin/pg_dump" <<'EOF'
#!/usr/bin/env bash
printf 'PGDUMP %s\n' "$*" >> "$STUB_LOG"
echo '-- fake dump'
EOF

# --- fake rclone: records every call, answers listremotes -------------------
cat > "$TMP/bin/rclone" <<'EOF'
#!/usr/bin/env bash
if [ "${1:-}" = "listremotes" ]; then
  echo "gdrive:"; echo "onedrive:"; exit 0
fi
printf 'RCLONE %s\n' "$*" >> "$STUB_LOG"
EOF

chmod +x "$TMP/bin/pg_dump" "$TMP/bin/rclone"
export PATH="$TMP/bin:$PATH"
export STUB_LOG="$TMP/calls.log"
: > "$STUB_LOG"

# run the real script with the stubs on PATH; extra args are env(1) settings,
# so the variables really reach the child process.
run() { ( cd "$ROOT" && env "$@" ./tools/backup/backup.sh ) > "$TMP/last.log" 2>&1; }

# --- 1. database-only run ---------------------------------------------------
run SUPABASE_DB_URL='postgresql://postgres:pw@db.example.co:5432/postgres' \
  RCLONE_REMOTE='gdrive:astro-smart-attendance' BACKUP_DIR="$TMP/work" \
  SKIP_ARCHIVE=1
check "the run succeeds" $?
check_eq "one compressed dump is written" 1 "$(count "$TMP"/work/astro-*.sql.gz)"
check "pg_dump gets the connection string" "$(has 'postgresql://postgres:pw@db.example.co:5432/postgres' "$STUB_LOG")"
check "pg_dump leaves ownership and ACLs out" "$(has '--no-owner --no-privileges' "$STUB_LOG")"
gunzip -c "$TMP"/work/astro-*.sql.gz > "$TMP/unzipped.sql" 2>/dev/null
check "the dump is valid gzip" "$(has 'fake dump' "$TMP/unzipped.sql")"
check "the dump is uploaded into <remote>/database" \
  "$(has_re "copy .*astro-.*\.sql\.gz gdrive:astro-smart-attendance/database" "$STUB_LOG")"
check "old dumps on the drive are pruned" \
  "$(has 'RCLONE delete gdrive:astro-smart-attendance/database --min-age 90d' "$STUB_LOG")"

# --- 2. local pruning -------------------------------------------------------
for i in $(seq -w 1 16); do : > "$TMP/work/astro-20200101T0000${i}Z.sql.gz"; done
run SUPABASE_DB_URL='postgresql://postgres:pw@db.example.co:5432/postgres' \
  RCLONE_REMOTE='gdrive:x' BACKUP_DIR="$TMP/work" KEEP_LOCAL=5 SKIP_ARCHIVE=1
check_eq "KEEP_LOCAL keeps exactly that many local dumps" 5 "$(count "$TMP"/work/astro-*.sql.gz)"

# --- 3. refusals ------------------------------------------------------------
run -u SUPABASE_DB_URL RCLONE_REMOTE='gdrive:x'
check "no connection string is refused" $([ $? -ne 0 ] && echo 0 || echo 1)
check "and says which variable is missing" "$(has 'SUPABASE_DB_URL is not set' "$TMP/last.log")"

run SUPABASE_DB_URL='postgresql://x' RCLONE_REMOTE='nope:folder'
check "an unconfigured rclone remote is refused" $([ $? -ne 0 ] && echo 0 || echo 1)
check "and names the remote" "$(has "rclone has no remote named 'nope'" "$TMP/last.log")"

# --- 4. upload can be switched off -----------------------------------------
: > "$STUB_LOG"
run SUPABASE_DB_URL='postgresql://postgres:pw@db.example.co:5432/postgres' \
  BACKUP_DIR="$TMP/work" SKIP_ARCHIVE=1 SKIP_UPLOAD=1
check "SKIP_UPLOAD needs no remote at all" $?
check "and writes the dump anyway" "$(has 'PGDUMP' "$STUB_LOG")"
check "but makes no rclone call" "$(lacks 'RCLONE' "$STUB_LOG")" 

# --- 4b. a machine without pg_dump still gets the day archive --------------
run SUPABASE_DB_URL='postgresql://x' BACKUP_DIR="$TMP/work" SKIP_ARCHIVE=1 SKIP_UPLOAD=1 PATH='/usr/bin:/bin'
check "no pg_dump is a skip, not a failure" $?
check "and it says so plainly" "$(has 'pg_dump is not installed' "$TMP/last.log")"

run BACKUP_DIR="$TMP/work" SKIP_DB=1 SKIP_ARCHIVE=1 SKIP_UPLOAD=1
st=$?
check "SKIP_DB skips the dump on request" $st
[ "$st" = "0" ] || sed -n 1,20p "$TMP/last.log"
check "and names the switch" "$(has 'skipped (SKIP_DB=1)' "$TMP/last.log")"

check "the Windows script exists beside the shell one" \
  "$([ -f "$ROOT/tools/backup/backup.ps1" ] && echo 0 || echo 1)"
check "the Windows script writes the same archive call" \
  "$(has 'tools/archive/archive.mjs --month' "$ROOT/tools/backup/backup.ps1")"
check "the Windows script uploads into <remote>/database" \
  "$(has 'rclone copy $dump "$remote/database"' "$ROOT/tools/backup/backup.ps1")"

# --- 5. the archive step is wired in ---------------------------------------
check "the archive tool is called with a month" \
  "$(has 'node tools/archive/archive.mjs --month' "$ROOT/tools/backup/backup.sh")"
check "a missing staff login is refused, not silently skipped" \
  "$(has 'ARCHIVE_EMAIL / ARCHIVE_PASSWORD are not set' "$ROOT/tools/backup/backup.sh")"

printf '\n  backup script: %d passed, %d failed\n' "$pass" "$fail"
[ "$fail" = "0" ] || exit 1
