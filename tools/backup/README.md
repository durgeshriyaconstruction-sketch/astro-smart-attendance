# Backup the school's data to Google Drive or OneDrive

Supabase holds the live database; it does **not** write into Google Drive or
OneDrive by itself. This folder closes that gap: one script takes a full
`pg_dump` plus the year → month → day archive files, and copies them into a
folder of your own drive with [rclone](https://rclone.org). Both Google Drive
and OneDrive are supported — rclone speaks to either one.

```
tools/backup/
├── backup.sh   dump + archive + upload, one command
└── README.md   this file
```

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
3. **Tools** — `pg_dump` (Postgres client 15/16), `node` 18+, `rclone`, `gzip`.
   ```bash
   sudo apt install postgresql-client-16 gzip
   ```

## Run it

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

**Windows (Task Scheduler → Create Basic Task → Daily):** start a program
`powershell.exe`, arguments:
```
-NoProfile -Command "cd C:\astro-smart-attendance; $env:SUPABASE_DB_URL='…'; $env:RCLONE_REMOTE='onedrive:astro-smart-attendance'; $env:ARCHIVE_EMAIL='principal@astro-school.test'; $env:ARCHIVE_PASSWORD='…'; bash tools/backup/backup.sh"
```
(Git for Windows ships `bash`; or run the same script in WSL.)

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
