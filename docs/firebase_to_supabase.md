# Moving the backend from Firebase to Supabase

You said you want Supabase as *the* backend. It already is, for everything that
has been built here: the terminal, the staff dashboard, the parent dashboard, the
email outbox, the cron. Firebase is not used by any of it — no Firebase project
id, no RTDB URL, no Firebase key appears in `firmware/`, `web/` or `services/`.

What still speaks Firebase is your existing `main.cpp`. This page is the map from
every path that file uses to the thing that replaces it, so the cut-over is a
list of decisions rather than a rewrite.

## What the current firmware does on Firebase

| Firebase path | Used for | Supabase replacement | State |
|---|---|---|---|
| `PATCH /` (attendance, events, tombstones) | uploading taps and edits | `astro_mark_attendance`, `astro_sync_batch` (10 events a call, idempotent by `event_uid`) | ✅ live, replayed in tests |
| `GET /settings` | late/absent cut-offs, weekly off, hardware flags, e-mail on/off | `astro_heartbeat` returns the school's settings; the school row is edited from the dashboard's Settings tab | ✅ live |
| `PATCH /` (`settings`, `timetable`) | device pushes its own settings *up* | not needed: settings are edited once, server-side, and the device reads them on every heartbeat | ✅ becomes read-only |
| `GET /students` | local roster mirror (name, roll, class, parent contacts, `fingerprintId`, `active`, `goalPct`, per-student password) | no mirror. `astro_lookup_card` / `astro_mark_attendance` answer who a card belongs to; the dashboard owns the roster | 🔁 dropped on purpose |
| `GET /notices` | notice board | `astro_student_feed` (parents) and the dashboard's Notices tab | ✅ live |
| `GET /messages` | staff ↔ family messages | `astro_send_message`, `astro_student_send_message`, `astro_inbox`, `astro_student_feed` | ✅ live |
| `GET /leaves` | leave requests | `astro_request_leave`, `astro_pending_leaves`, `astro_decide_leave` | ✅ live |
| `GET /holidays` | holiday calendar | `school_holidays` + `astro_set_holiday` / `astro_remove_holiday`, already reflected in the parent calendar | ✅ live |
| `GET /notifications` | the device's own event log | `device_events` (per tap, per command) and the `alerts` outbox for anything a guardian must see | ✅ live |
| `GET /firmwareUpdate` | OTA campaign (chunks in RTDB or an https URL) | **nothing yet** — ArduinoOTA over the LAN, or a future `firmware_releases` table + signed URL | ❌ not built |
| `GET /timetable` | period timetable (start, periods, length, lunch) | **nothing yet** — the schema can store period attendance (`attendance.session = 'period'`, `period_no`) but there is no timetable table | ❌ not built |
| `GET /studentPasswordRequests`, `PATCH /studentAuth/<id>` | creates a Firebase Auth account per student alias so pupils can log in to the on-device portal | Supabase Auth: real accounts, `student_links` ties a parent to a child, the parent dashboard replaces the portal | 🔁 replaced by something better |

Three of those are gaps, and only one of them matters for a working school:
OTA (you can flash over USB, and ArduinoOTA works on the same Wi-Fi) and the
timetable (only needed if you want per-period attendance rather than one daily
mark). The third — pupils logging in with a per-student password — is gone by
design: parents get a real account instead.

## Why this is the better backend for this project

Not "newer is better" — these are properties this system actually uses:

1. **The rules live in the database, not the client.** Every write is a
   `security definer` RPC that re-checks `auth.uid()`, the school and the role.
   The terminal only carries a publishable key; it cannot read a single table.
   Firebase RTDB rules are per-path JSON with no joins — a parent's "only my
   child" rule needs a copy of the roster in the rules file.
2. **One transaction.** "Mark present, cancel the queued absence e-mail, write
   the audit row" is one function call. RTDB multi-path updates cannot express
   a conditional on a different tree.
3. **SQL for the things schools ask for.** The monthly report is a single
   `astro_attendance_report` over `attendance`; a percentage, a leave count and
   a class comparison come out of the same query. In RTDB that is a client-side
   loop over every record.
4. **The outbox retries.** `alerts` has status, attempts, last_error, and
   `astro_claim_emails` hands rows to the mailer with `for update skip locked`.
   Losing the network mid-send cannot duplicate an e-mail.
5. **Time is the database's job.** `pg_cron` closes the day every 30 minutes and
   marks the no-shows; the terminal does not have to be awake or correct.
6. **No secret on the terminal.** Today the terminal holds `smtpUser` and
   `smtpPass` in NVS *and pushes them to the database* (`pushSettings()`). One
   stolen ₹1,500 box is a stolen Gmail app password. In the Supabase design the
   terminal holds only a device code + secret, and mail goes out from
   `services/mailer`.
7. **Idempotent replay.** Every tap carries an `event_uid`; re-uploading the
   offline queue is a no-op instead of a duplicate.
8. **Remote commands with a TTL.** `device_commands` + `astro_poll_commands` is
   how the Devices tab makes the LCD print, reads a card or enrols a finger.
   There is no equivalent in RTDB without inventing one.
9. **Free tier is a database, not a read counter.** RTDB bills per download;
   a dashboard that polls a screen every few seconds consumes that budget. The
   REST/RPC model here does not.

## The cut-over, in order

**Step 1 — run both for a week (optional but recommended).** Keep Firebase
running, add the Supabase calls next to it. Your `main.cpp` already treats the
cloud as a mirror of local state, so dual-writing is safe. Both paths are
idempotent, so a double upload cannot double-count.

**Step 2 — stop pushing secrets.** Delete the `smtpUser` / `smtpPass` fields from
`pushSettings()` and from the local config, then remove the credentials from the
Firebase tree (`settings/smtpPass`). Until you do, the password is in two places.

**Step 3 — flash the Supabase terminal.** Either:

* **fast**: flash `firmware/astro_attendance/astro_attendance.ino` — same pins as
  your rev2 board, same LCD messages, offline queue in NVS, command loop;
* **surgical**: follow `docs/main_cpp_additions.md` and paste the six blocks into
  `main.cpp`, keeping your web portal. In that case keep your local roster and
  drop `pullStudents()`, `serviceStudentAuth()`, `pushSettings()` and
  `pullLiveSettings()` — the heartbeat now carries the settings.

**Step 4 — point the dashboards at Supabase.** `web/` already does; the old
Firebase-hosted dashboard becomes a redirect or is deleted.

**Step 5 — delete Firebase.** Once a week of taps has gone through both and the
counts match, remove the Firebase project. Nothing in this repository will miss
it.

## If you need the two gaps closed

* **Timetable / period attendance.** A `timetables` table (school, class,
  weekday, period_no, start/end, subject) plus a `astro_timetable(class)` read
  would let the terminal mark a tap against a period. The attendance table
  already accepts `session='period'` and `period_no`, so this is additive.
* **OTA from the cloud.** A `firmware_releases` table (version, sha256, size,
  storage path) and an `astro_device_firmware(device_code)` RPC could tell the
  terminal "there is a newer build, here is a 10-minute signed URL", reusing the
  command channel you already have (`reboot` is there).

Both are small, but neither is needed to run a school tomorrow, which is why
they are not built yet. Say the word and they go in.
