# Backup the school's data to Google Drive or OneDrive

Supabase holds the live database; it does **not** write into Google Drive or
OneDrive by itself. This folder closes that gap: one script takes a full
`pg_dump` plus the year → month → day archive files, and copies them into a
folder of your own drive with [rclone](https://rclone.org). Both Google Drive
and OneDrive are supported — rclone speaks to either one.

```
tools/backup/
├── backup.sh    Linux/macOS/WSL/Git-Bash version
├── backup.ps1   Windows PowerShell version (same job, no bash needed)
└── README.md    this file
```

Both do the same three things: `pg_dump` (when installed), the year → month →
day archive, then `rclone copy` into your drive. Neither is a live sync — it is
a copy, taken when you run it.

## What you need once

1. **The database password** — Supabase dashboard → *Project Settings →
   Database → Connection string → URI*. Replace `[YOUR-PASSWORD]`. That whole
   string is `SUPABASE_DB_URL`.
   ```
   postgresql://postgres:<PASSWORD>@db.nrjchonjlncamfyzmfye.supabase.co:5432/postgres
   ```
2. **A drive remote** — install rclone, then:
   ```bash
   rclone config            # n → name it "gdrive" (or "onedrive") → pick the provider
   ```
   * Google Drive: choose `drive`, leave client_id blank, say **yes** to
     "Use auto config?", tick *root folder = the whole drive* or enter a folder
     id. A browser opens; sign in as `durgesh@…` and allow it.
   * OneDrive: choose `onedrive`, then *Microsoft OneDrive*, same browser flow
     with your Microsoft account.
   * On a headless server add `--auth-no-open-browser` and paste the returned
     code into the provider's page.
3. **Tools** — `node` 18+ and `rclone` are enough to start. `pg_dump`
   (Postgres client 15/16) only adds the full database dump; the day archive
   works without it, and the script says so instead of failing.
   ```bash
   sudo apt install postgresql-client-16 gzip     # Debian/Ubuntu
   winget install PostgreSQL.PostgreSQL.17        # Windows (optional)
   ```

## Run it — Windows PowerShell

```powershell
cd "C:\path\to\astro-smart-attendance"
$env:ARCHIVE_EMAIL    = 'principal@astro-school.test'
$env:ARCHIVE_PASSWORD = 'Astro-Principal-2026'
$env:RCLONE_REMOTE    = 'onedrive:astro-smart-attendance'

# 1. dry run: writes the files locally, uploads nothing
.\tools\backup\backup.ps1 -NoUpload

# 2. real run: writes and uploads
.\tools\backup\backup.ps1

# full database dump as well (needs pg_dump + the DB password)
$env:SUPABASE_DB_URL = 'postgresql://postgres:<PASSWORD>@db.nrjchonjlncamfyzmfye.supabase.co:5432/postgres'
.\tools\backup\backup.ps1
```

If PowerShell refuses to run the script (`running scripts is disabled`), allow it
for that window only:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\backup\backup.ps1 -NoUpload
```

Switches: `-NoUpload`, `-SkipDb`, `-SkipArchive`. Environment: `BACKUP_DIR`,
`KEEP_LOCAL`, `SUPABASE_URL`, `SUPABASE_KEY` (both default to this project).

## Run it — Linux / macOS / WSL / Git Bash

```bash
cd astro-smart-attendance
export SUPABASE_DB_URL='postgresql://postgres:<PASSWORD>@db.nrjchonjlncamfyzmfye.supabase.co:5432/postgres'
export RCLONE_REMOTE='gdrive:astro-smart-attendance'     # or onedrive:astro-smart-attendance
export ARCHIVE_EMAIL='principal@astro-school.test'
export ARCHIVE_PASSWORD='Astro-Principal-2026'
./tools/backup/backup.sh
```

That writes, and then uploads:

```
gdrive:astro-smart-attendance/
├── database/astro-20261112T183000Z.sql.gz     full database, restorable with psql
└── archive/2026/11/2026-11-12.json            the day file (attendance, notices,
              2026/11/2026-11-12.csv            messages, e-mail log, leave)
              2026/11/month-summary.json
              index.json
```

Useful switches: `SKIP_UPLOAD=1` (write the files, upload nothing),
`SKIP_ARCHIVE=1` (database only), `KEEP_LOCAL=14`, `BACKUP_DIR=…`,
`RCLONE_EXTRA='--bwlimit 2M'`.

## Make it automatic

**Linux / macOS (cron, every night at 00:20):**
```cron
20 0 * * * cd /path/to/astro-smart-attendance && SUPABASE_DB_URL='…' RCLONE_REMOTE='gdrive:astro-smart-attendance' ARCHIVE_EMAIL='principal@astro-school.test' ARCHIVE_PASSWORD='…' ./tools/backup/backup.sh >> /var/log/astro-backup.log 2>&1
```

**Windows (Task Scheduler):** create a task, *Trigger* = Daily 00:20, *Action* =
start a program `powershell.exe` with arguments:
```
-NoProfile -ExecutionPolicy Bypass -File "C:\path\to\astro-smart-attendance\tools\backup\backup.ps1"
```
and set the four environment variables in that user's profile first (System
Properties → Environment Variables), so the task inherits them:

```
ARCHIVE_EMAIL     principal@astro-school.test
ARCHIVE_PASSWORD  Astro-Principal-2026
RCLONE_REMOTE     onedrive:astro-smart-attendance
SUPABASE_DB_URL   postgresql://postgres:<PASSWORD>@db.nrjchonjlncamfyzmfye.supabase.co:5432/postgres
```

## Restoring a dump

```bash
gunzip -c astro-20261112T183000Z.sql.gz | psql "$SUPABASE_DB_URL"
```

Restore into a fresh project, never over the live one on a school day. The dump
contains `auth.users` rows, so demo accounts come back too — that is
intentional: a restore should be complete.

## Two honest limits

* **The dump is a snapshot, not replication.** Anything written after it ran is
  not in it; nightly is usually enough for a school, hourly is possible by
  shortening the cron line.
* **The device secret and the publishable key are not secret in a dump** — they
  are in there. Treat the drive folder as sensitive: share it with the school's
  own account only, and never make it public.
