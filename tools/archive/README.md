# Archive the school's records as files

Supabase holds the live data; this writes it out as ordinary folders and files,
in the order a school office keeps paper — **year → month → day**:

```
archive/
  index.json                     what is in here, school, range, totals
  2026/
    11/
      2026-11-02.json            everything that happened that day
      2026-11-02.csv             the attendance sheet for that day (opens in Excel)
      2026-11-03.json
      ...
      month-summary.json         per-student present/late/absent for the month
```

Every day file looks like this:

```json
{
  "date": "2026-11-12",
  "school": { "code": "ABPS-RNK", "name": "…", "timezone": "Asia/Kolkata" },
  "attendance":   [ { "roll_no": "DEMO-01", "name": "Demo Student", "status": "absent", "method": "fingerprint", "marked_at": "…", "note": null } ],
  "notices":      [ { "title": "PTM on Saturday", "body": "…", "priority": "normal", "audience": "all" } ],
  "messages":     [ { "roll_no": "DEMO-01", "subject": "Your attendance this month", "body": "…", "direction": "to_student" } ],
  "emails":       [ { "to_email": "demo.parent@example.com", "subject": "Absent today: Demo Student", "status": "sent", "attempts": 1 } ],
  "leave_requests": [ { "from_date": "2026-11-05", "to_date": "2026-11-06", "reason": "Family function", "status": "approved" } ]
}
```

So the message that went to a parent, the notice you posted and the e-mail the
child's guardian received all sit in the same folder as the attendance for that
day — which is what you asked for.

## Run it

It signs in as a staff account, so it needs no service key sitting on a disk:

```bash
export SUPABASE_URL=https://nrjchonjlncamfyzmfye.supabase.co
export SUPABASE_KEY=sb_publishable_9a4vSwLdVz4Yd8wrWcTvXA_aIMmC6H_   # public by design
export ARCHIVE_EMAIL=principal@astro-school.test
export ARCHIVE_PASSWORD='Astro-Principal-2026'

node tools/archive/archive.mjs --month 2026-11 --out ./archive
```

| Flag | Meaning |
|---|---|
| `--month 2026-11` | archive one calendar month (clamped to real dates) |
| `--from 2026-11-01 --to 2026-11-30` | an explicit range, up to 400 days |
| `--out DIR` | where to write (default `./archive`) |
| `--skip-empty` | skip days that have nothing at all |
| `--help` | the same list |

Needs Node 18+ and nothing else — no packages, no build.

## Keep it running — put it on a daily timer

On the office PC (Linux/macOS, `crontab -e`), just after midnight:

```
5 0 * * *  cd /srv/astro && /usr/bin/env node tools/archive/archive.mjs --month "$(date -d yesterday +\%Y-\%m)" --out /srv/astro/archive >> /var/log/astro-archive.log 2>&1
```

Point `/srv/astro/archive` at a Google Drive or OneDrive folder and the year/month/day
tree is backed up off the machine without any extra software. On Windows, Task
Scheduler with the same command line.

Because it re-reads the whole month each run and overwrites those files, running
it twice is harmless and it repairs a month that was written badly.

## What it will not do

* It does not delete anything in Supabase — read-only, through the same
  row-level security the dashboard uses, so an account for one school cannot
  archive another.
* A `teacher` or `viewer` account can run it; a `student` (parent) account is
  refused, since a parent's view is one child, not the school.
* It is not a database backup. It is the *school's record* in a form a human can
  read, hand to an inspector, or open in Excel. Real backups are the Supabase
  dashboard's job (Project ▸ Database ▸ Backups).

## Tests

```bash
cd tests/archive && npm test
```

17 assertions run the script against a fake Supabase: the folder tree, the day
CSV, the month summary, the index totals, the 400-day guard, the refusal when
credentials are missing — and that a message sent at 00:30 IST lands in the
*next* day's file rather than the previous UTC day.
