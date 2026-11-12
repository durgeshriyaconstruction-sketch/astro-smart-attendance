# Automatic Drive backup — no PC, no chat

`Code.gs` here is a Google Apps Script. Google runs it on its own servers every
day, pulls the month from Supabase, and rewrites the files in Drive. Nothing on
your side has to be switched on.

```
Supabase                         Google
┌─────────────────────┐   https  ┌──────────────────────────┐
│ astro_drive_month() │◄─────────│ Apps Script (Code.gs)    │
│   = one month, JSON │  secret  │  daily 9pm Asia/Kolkata  │
└─────────────────────┘          │  ↓ writes                │
      ▲ astro-export             │ Drive/astro-smart-…/2026/11│
      │ Edge Function            └──────────────────────────┘
      └── called by the script
```

| piece | where it lives | who made it |
|---|---|---|
| `public.astro_drive_month(p_month, p_school_code)` | migration `0031_drive_export.sql` | me — applied |
| `astro-export` Edge Function | Supabase, `verify_jwt: false` | me — deployed (v1) |
| `DRIVE_SYNC_SECRET` (48 hex) | Supabase → Edge Functions → Secrets | me — stored |
| `Code.gs` | script.google.com | **you paste it once** |

## Set it up (about 5 minutes, once)

1. Go to <https://script.google.com> → **New project**.
2. Delete the sample `function myFunction()` and paste the whole of `Code.gs`.
3. Put the secret in `CONFIG.SECRET`. Get it from me (or from Supabase →
   Project Settings → Edge Functions → Secrets → `DRIVE_SYNC_SECRET`).
4. **Run** → choose `ping` → first time it asks for permission → **Review
   permissions** → pick your Google account → **Advanced** → *Go to project
   (unsafe)* → **Allow**. It only asks for Drive; it never touches Gmail.
   The log should show `200 {"ok":true,...}`.
5. Run `syncMonth` once by hand. Log shows e.g. `2026-11: 10 days, 22 files`.
6. **Triggers** (clock icon, left) → **Add trigger** →
   function `syncMonth`, event source *Time-driven*, type *Day timer*,
   time of day *9pm to 10pm* → **Save**.

That's it. Every night Google writes the current month; a new month creates its
own folder on the first run of that month.

## Checking it worked

- Drive: `astro-smart-attendance/2026/11/` — today's `.json` and `.csv` have a
  new modified time, `index.json` at the root has today's counts.
- Apps Script: **Executions** (left icon) lists every run with its duration;
  a red one carries the error text. Google e-mails you when a run fails.
- From this side: `select * from net._http_response order by id desc limit 5;`
  is **not** useful here — the script calls Supabase, not the other way round.

## Limits worth knowing

- Apps Script free quota: 90 minutes of runtime per day, and `UrlFetchApp`
  20,000 calls/day. One run per day uses a fraction of that.
- The export is a whole month each time (currently ~8 KB), so a re-run always
  repairs a missed night. Nothing is incremental, nothing can drift.
- `month-summary.json` counts only `attendance` rows, matching the sheet:
  present + late + absent + leave + other = days marked. Approved leave
  requests that never got an attendance row still appear in the day files.
