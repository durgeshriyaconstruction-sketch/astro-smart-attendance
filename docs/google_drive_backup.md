# The school's records in Google Drive

Two ways to get the year → month → day files into Drive. Both produce the same
folder shape; pick one.

```
astro-smart-attendance/            ← folder in Drive
├── index.json                     what is in this archive, day by day
└── 2026/
    └── 11/
        ├── 2026-11-02.json        attendance + notices + messages + e-mail log + leave
        ├── 2026-11-02.csv         the attendance sheet, opens in Excel
        ├── ...
        ├── 2026-11-12.json
        ├── 2026-11-12.csv
        └── month-summary.json     per-student present/late/absent for the month
```

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
