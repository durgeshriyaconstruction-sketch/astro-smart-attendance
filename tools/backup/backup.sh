#!/usr/bin/env bash
# ============================================================================
#  tools/backup/backup.sh — copy the school's data into YOUR own cloud drive
#
#  Supabase keeps the live database. This script takes a copy of it — plus the
#  year/month/day archive files — and pushes them to Google Drive or OneDrive
#  through rclone. Nothing is "synced": a copy is written, the newest N are
#  kept, and you can open them in the drive's web page.
#
#  Needs on the machine that runs it:
#    pg_dump      (Postgres 15/16 client — e.g. `apt install postgresql-client-16`)
#    gzip, rclone (https://rclone.org/install/)
#    node 18+     (only for the archive step)
#
#  Usage:
#    export SUPABASE_DB_URL='postgresql://postgres:<PASSWORD>@db.nrjchonjlncamfyzmfye.supabase.co:5432/postgres'
#    export RCLONE_REMOTE='gdrive:astro-smart-attendance'
#    ./tools/backup/backup.sh
#
#  Optional:
#    BACKUP_DIR=./backups        where the copies land before upload
#    KEEP_LOCAL=14               how many local dumps to keep
#    SKIP_ARCHIVE=1              database-only backup
#    SKIP_UPLOAD=1               write the files, upload nothing
#    RCLONE_EXTRA='--drive-...'  passed straight to rclone
# ============================================================================
set -euo pipefail

cd "$(dirname "$0")/../.."

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
KEEP_LOCAL="${KEEP_LOCAL:-14}"
RCLONE_REMOTE="${RCLONE_REMOTE:-}"
SKIP_ARCHIVE="${SKIP_ARCHIVE:-0}"
SKIP_DB="${SKIP_DB:-0}"
SKIP_UPLOAD="${SKIP_UPLOAD:-0}"

say()  { printf '%s\n' "$*"; }
fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

command -v gzip >/dev/null || fail "gzip is not installed"
if [ "$SKIP_UPLOAD" != "1" ]; then
  [ -n "$RCLONE_REMOTE" ] || fail "RCLONE_REMOTE is not set (e.g. gdrive:astro-smart-attendance)"
  command -v rclone >/dev/null || fail "rclone is not installed — see https://rclone.org/install/"
  rclone listremotes | grep -q "^${RCLONE_REMOTE%%:*}:$" \
    || fail "rclone has no remote named '${RCLONE_REMOTE%%:*}'. Configure it with: rclone config"
fi

mkdir -p "$BACKUP_DIR"
DUMP="$BACKUP_DIR/astro-$STAMP.sql.gz"

say "== database dump =="
if [ "$SKIP_DB" = "1" ]; then
  say "   skipped (SKIP_DB=1)"
elif ! command -v pg_dump >/dev/null; then
  say "   skipped — pg_dump is not installed (the day archive still runs)"
else
  [ -n "${SUPABASE_DB_URL:-}" ] || fail "SUPABASE_DB_URL is not set (Supabase dashboard -> Project Settings -> Database -> Connection string -> URI, then replace [YOUR-PASSWORD])"
  # Schema + data, no ownership/ACL noise, compressed as it streams.
  pg_dump --no-owner --no-privileges --clean --if-exists "$SUPABASE_DB_URL" \
    | gzip -9 > "$DUMP"
  say "   $DUMP  ($(du -h "$DUMP" | cut -f1))"
fi

say "== year/month/day archive =="
if [ "$SKIP_ARCHIVE" = "1" ]; then
  say "   skipped (SKIP_ARCHIVE=1)"
else
  [ -n "${ARCHIVE_EMAIL:-}" ] && [ -n "${ARCHIVE_PASSWORD:-}" ] \
    || fail "ARCHIVE_EMAIL / ARCHIVE_PASSWORD are not set (a staff login; the archive tool signs in as that user)"
  export SUPABASE_URL="${SUPABASE_URL:-https://nrjchonjlncamfyzmfye.supabase.co}"
  export SUPABASE_KEY="${SUPABASE_KEY:-sb_publishable_9a4vSwLdVz4Yd8wrWcTvXA_aIMmC6H_}"
  ARCHIVE_MONTH="$(date -u -d 'yesterday' +%Y-%m 2>/dev/null || date -u -v-1d +%Y-%m)"
  node tools/archive/archive.mjs --month "$ARCHIVE_MONTH" --out "$BACKUP_DIR/archive" --skip-empty
fi

if [ "$SKIP_UPLOAD" = "1" ]; then
  say "== upload skipped (SKIP_UPLOAD=1) =="
  exit 0
fi

say "== upload to $RCLONE_REMOTE =="
# shellcheck disable=SC2086
rclone copy "$DUMP" "$RCLONE_REMOTE/database" ${RCLONE_EXTRA:-} --stats-one-line
if [ -d "$BACKUP_DIR/archive" ]; then
  # shellcheck disable=SC2086
  rclone copy "$BACKUP_DIR/archive" "$RCLONE_REMOTE/archive" ${RCLONE_EXTRA:-} --stats-one-line
fi

# The drive is not a scrapbook: drop dumps older than 90 days there, keep the
# newest KEEP_LOCAL locally.
rclone delete "$RCLONE_REMOTE/database" --min-age 90d 2>/dev/null || true
ls -1t "$BACKUP_DIR"/astro-*.sql.gz 2>/dev/null | tail -n "+$((KEEP_LOCAL + 1))" | xargs -r rm -f

say "done. Latest copy: $RCLONE_REMOTE/database/$(basename "$DUMP")"
