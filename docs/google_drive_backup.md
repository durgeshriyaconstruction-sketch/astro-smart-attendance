# The school's records in Google Drive

**Chosen layout (2026-11-12): year → month → class → section → one Excel per day.**

```
astro-smart-attendance/            ← folder in Drive
└── 2026/
    └── 11/
        ├── 9/
        │   ├── A/
        │   │   ├── 2026-11-12.xlsx    col A = name(s), col B = Present/Absent
        │   │   ├── 2026-11-13.xlsx
        │   │   └── ...
        │   └── B/
        │       └── 2026-11-12.xlsx
        └── 10/
            └── A/
                └── 2026-11-12.xlsx
```

One workbook per class + section per day, named by the date. Row 1 says which
class and date it is, row 2 is the header (`Name`, `Status`), then one row per
child in roll order. The run rewrites that day's file, so a second run repairs
it instead of adding `(1)` copies.

Driven by:

| piece | what it does |
|---|---|
| `public.astro_drive_day(date)` | one day, grouped by class + section (`0032_drive_day_sheets.sql`) |
| `astro-export?date=YYYY-MM-DD` | Edge Function endpoint the script calls (v2) |
| `tools/drive_sync/Code.gs` → `syncDay()` | builds the Sheet, exports real `.xlsx`, files it by folder |
| Drive folder ids | `2026` `1U57eeN7NJPs9o9_RCKIs9viKrKutULyI` · `11` `162iWPgrF53bjQxvtS0kk9GHzu5k5VJ_p` · `9` `1xpXjO2x5iXjKW5raFOsolnTP8toYeFQL` · `A` `1wiOZjSlLesG0hh0eZiLBGbGI_obHHP5m` |

Proven 2026-11-12: `?date=2026-11-12` → `200`, 356 bytes, path `2026/11/9/A`,
status `Absent`; the same day then written to Drive by hand as
`2026/11/9/A/2026-11-12.xlsx` (5,067 bytes) so the target shape is visible
before the script exists.

`archiveMonth()` in the same script is the optional old-style day-by-day JSON
archive (not scheduled). The 21 JSON/CSV files written earlier still sit at the
`2026/11/` root until you decide to delete them.

## What is already in there (done 2026-11-12)

Written by the assistant through the **Google Drive connection**, reading the
live database:

| item | value |
|---|---|
| folder | `astro-smart-attendance` — id `1QAN2ra0HyUsQJpS9m8VXduR5H2b8Uxz8` |
| year folder | `2026` — id `1U57eeN7NJPs9o9_RCKIs9viKrKutULyI` |
| month folder | `11` — id `162iWPgrF53bjQxvtS0kk9GHzu5k5VJ_p` |
| files | 21 — 10 day `.json` + 10 day `.csv` + `month-summary.json`, plus `index.json` at the root |
| range | 2026-11-01 … 2026-11-30, school timezone Asia/Kolkata |
| content | 10 attendance rows, 1 notice, 1 message, 1 queued e-mail, 2 leave days |
| generated_by | `agent via Google Drive (chat), same layout as tools/archive` |

Open it: <https://drive.google.com/drive/folders/1QAN2ra0HyUsQJpS9m8VXduR5H2b8Uxz8>

This is the *same JSON shape* `tools/archive` writes, so the two can be mixed:
a night run from a PC just overwrites the same files.

## Option D — automatic, no PC (set up 2026-11-12)

Supabase builds the month, a Google Apps Script writes it to Drive every night.
Nothing on your side stays switched on, and a chat does not have to run.

```
Supabase: astro_drive_month()  ←  astro-export Edge Function  ←  Apps Script (Google)
                                                    writes →  astro-smart-attendance/2026/11/…
```

Live state:

| piece | value |
|---|---|
| SQL function | `public.astro_drive_month(p_month, p_school_code)` — migration `0031_drive_export.sql`, service role only |
| Edge Function | `astro-export`, `verify_jwt: false`, `v1` — <https://nrjchonjlncamfyzmfye.supabase.co/functions/v1/astro-export> |
| secret | `DRIVE_SYNC_SECRET` (48 hex) in Supabase secrets; sent as `x-drive-secret` or `?secret=` |
| script | `tools/drive_sync/Code.gs` — paste into <https://script.google.com>, run once, add a daily 9pm trigger |
| proven | ping → `200 {"ok":true,...}`; `?month=2026-11` → `200`, 7,757 bytes, 10 days, class `9-A`, 75 % |
| not yet proven | the Apps Script half, until it is pasted and run on your side |

Checks that need no browser:

```sql
-- what the function produces for a month (same bytes the script writes)
select jsonb_pretty(public.astro_drive_month('2026-11')->'summary');

-- what the HTTP call returned last time
select id, status_code, length(content) as bytes
  from net._http_response where id > 0 order by id desc limit 5;
```

## Option A — say "do the backup" in chat

With the Google Drive app connected, the assistant reads the database through
Supabase and writes the files into that folder. Nothing to install.

- good for: a copy right now, a specific month, a re-do
- not for: unattended nightly runs (a chat cannot wake itself up)
- limit: Google Drive only; the OneDrive account is not reachable this way

## Option B — rclone on your PC (nightly, unattended)

Your PC already has `gdrive:` connected (it listed `Astro STL`, `Google Meet`,
`Images`), so this works today with no wizard:

```powershell
cd "C:\path\to\astro-smart-attendance"
$env:ARCHIVE_EMAIL    = 'principal@astro-school.test'
$env:ARCHIVE_PASSWORD = 'Astro-Principal-2026'
$env:RCLONE_REMOTE    = 'gdrive:astro-smart-attendance'
.\tools\backup\backup.ps1
```

The first run creates `astro-smart-attendance/archive/2026/11/...` in Drive
(note: the script writes under `archive/`, the chat route writes at the folder
root — both are valid, pick one convention per school).

**Caveat, said plainly:** rclone's shared Google client ID is being retired
during 2026. If `gdrive:` stops authenticating one day, either
`rclone config reconnect gdrive:` or make your own client ID
(<https://rclone.org/drive/#making-your-own-client-id>, ~10 minutes in Google
Cloud console) and paste it into the remote's `client_id` / `client_secret`.

## Option C — OneDrive instead

`onedrive:` on that PC is half-configured (`unable to get drive_id and
drive_type`). Fix it with `rclone config` → new remote → type `onedrive` →
browser sign-in, or use the token-paste route
(`rclone authorize "onedrive"`). Then set `RCLONE_REMOTE='onedrive:astro-smart-attendance'`.

## Everything needed to wire this up from scratch

| value | where it comes from | used by |
|---|---|---|
| Supabase URL `https://nrjchonjlncamfyzmfye.supabase.co` | Supabase → Project Settings → API | web page, archive, backup script |
| publishable key `sb_publishable_9a4vSwLdVz4Yd8wrWcTvXA_aIMmC6H_` | same page | web page, archive, firmware |
| database password / `SUPABASE_DB_URL` | Supabase → Project Settings → Database → Connection string (URI) | `pg_dump` in backup.ps1 |
| staff login for the archive | a real `admin`/`teacher` account, e.g. `principal@astro-school.test` / `Astro-Principal-2026` (demo) | `ARCHIVE_EMAIL` / `ARCHIVE_PASSWORD` |
| device code | `devices.device_code`, currently `ASTRO-RNK-01` | firmware |
| device secret | `select public.astro_rotate_device_secret('ASTRO-RNK-01');` — shown once | firmware `ASTRO_DEVICE_SECRET` |
| drive remote | `rclone listremotes` → `gdrive:` or `onedrive:` | `RCLONE_REMOTE` |
| Drive folder id | the `astro-smart-attendance` folder above | connector route only |

Nothing here is stored in the repository except the publishable key, which is
public by design — it can only call the `astro_*` device functions and cannot
read a single table.
