# Supabase backend — what exists in `nrjchonjlncamfyzmfye`

Applied **2026-11-12**, region `ap-southeast-2`, Postgres 17. Every migration below
has been executed against the live project and verified; the SQL is replayable on
a fresh project (or on Neon later).

```
supabase/migrations/0001_schema.sql                tables, RLS, views
supabase/migrations/0002_device_api.sql            the four device RPCs
supabase/migrations/0003_seed.sql                  school + device + demo row
supabase/migrations/0004_automation.sql            pg_cron end-of-day closure
supabase/migrations/0005_hardening.sql             staff guard, timestamp clamp, updated_at
supabase/migrations/0006_revoke_anon_helpers.sql   anon grant fix + fail-closed defaults
supabase/migrations/0007_audit_fixes.sql           RLS recursion, holidays, fingerprints, indexes
supabase/migrations/0008_late_arrival_upgrade.sql  late arrival after auto-close
supabase/migrations/0009_provision_device_fix.sql  provisioning INSERT fix
supabase/migrations/0010_tighten_rls_helpers.sql   anon whitelist = 4 functions
supabase/migrations/0011_notices_messages_outbox.sql  notices, messages, unified alerts outbox
supabase/migrations/0012_outbox_visibility_and_read_guard.sql  outbox privacy, mark-read guard, student feed
supabase/migrations/0013_shrink_executable_surface.sql internal helpers no longer executable
supabase/migrations/0014_outbox_worker_contract.sql  claim / finish / release for the mailer
supabase/migrations/0015_fix_claim_ambiguity.sql     qualify columns in astro_claim_emails
supabase/migrations/0022_school_scoped_identity.sql  roles scoped to a school, deterministic current_school
supabase/migrations/0023_student_lifecycle.sql       save_student keeps guardian data, archive not delete
supabase/migrations/0024_admin_insights_and_maintenance.sql  report, outbox list, leaves, device health, prune
supabase/migrations/0025_grant_surface.sql           internal helpers + views no longer executable/writable
supabase/migrations/0026_leave_outbox_sync.sql       cancelling a leave withdraws its queued email
```

Migrations **0016-0021** (`astro_access_and_identity`, `astro_timing_settings`,
`astro_holidays_leave_calendar`, `astro_notice_priority_two_way_messages`,
`astro_device_commands_and_enrolment`, `astro_realtime`) were applied from an
earlier working session and their `.sql` files are not in this checkout yet.
Their exact text is stored in the live project, and
`tools/export_live_schema.sql` prints it so the files can be written back;
until then, 0022+ are written to be additive and idempotent on top of them.

---

## 1. Connection facts

| Item | Value |
|---|---|
| Project URL | `https://nrjchonjlncamfyzmfye.supabase.co` |
| REST endpoint | `https://nrjchonjlncamfyzmfye.supabase.co/rest/v1` |
| Publishable key (device + browser) | `sb_publishable_9a4vSwLdVz4Yd8wrWcTvXA_aIMmC6H_` |
| Legacy `anon` key | Settings ▸ API Keys (same role, older format) |
| Secret / `service_role` key | **server only** — never in firmware, never in a browser |
| Direct Postgres | `db.nrjchonjlncamfyzmfye.supabase.co:5432`, pooler `:6543` |

## 2. Tables (17, all with RLS)

| Table | Holds |
|---|---|
| `schools` | timezone, `day_start`, `late_after`, `day_end`, `alert_emails` |
| `classes` | class + section + teacher (`9/A`) |
| `students` | roll no, name, guardian email/phone, `fingerprint_id` (legacy) |
| `rfid_cards` | card UID → student, `active`, label |
| `devices` | terminal: `device_code`, `secret_hash`, firmware, `last_seen`, `last_boot`, RSSI |
| `attendance` | one row per student per day (`session='daily'`) or per period |
| `device_events` | every raw tap incl. replays; `event_uid` unique → idempotent sync |
| `alerts` | **the outbox**: one row per family per message (`late`, `absent`, `notice`, `message`, …) with `status`, `attempts`, `last_error`. Attendance alerts point home with `attendance_id` (bigint); notices and messages with `ref_kind` + `ref_id` (uuid) |
| `notices` | admin announcements: audience `all` / `class` / `student`, pinned, `publish_at`, `expires_at` |
| `messages` | one-to-one notes to a single student, with `read_at` |
| `members` | dashboard users → school + role (`admin`/`teacher`/`viewer`) |
| `student_links` | student/guardian self-service view of their own rows |
| `school_holidays` | dates the cron must not mark absent |
| `fingerprints` | `(device_id, slot)` → student — R307 slots are per-terminal |
| `leave_requests` | pending / approved / rejected / cancelled; one row per request, ranges cannot overlap per student |
| `device_commands` | queued work for one terminal (LCD text, RFID capture, fingerprint enrol/check/delete, reboot) with a TTL |
| `notice_dismissals` | per-user "hide this notice" rows — the student side of the trash icon |

Views: `v_attendance_feed`, `v_daily_attendance` (both `security_invoker`).

**Uniqueness that protects the data**

* `attendance (student_id, attendance_date, session, coalesce(period_no,0))` — a
  second tap can never create a second row for the same slot.
* `device_events.event_uid` — replaying the offline queue 100× writes once.
* `rfid_cards.card_uid` — one card cannot belong to two students.
* `fingerprints (device_id, slot)` and `(device_id, student_id)`.

## 3. The four RPCs the terminal may call

`SECURITY DEFINER`, device authenticated by `device_code` + `sha256(secret)`.
`anon` may execute **only these four** (see §6).

| Function | Purpose |
|---|---|
| `astro_heartbeat` | school name, late cut-off, server clock, updates `last_seen` |
| `astro_mark_attendance` | one tap → present/late, `ALREADY_MARKED`, `UNKNOWN_CARD` |
| `astro_sync_batch` | offline replay, per-event isolation, honest counters |
| `astro_lookup_card` | read-only "is this card registered?" |

### Example (verified against the live project)

```bash
curl -s -X POST https://nrjchonjlncamfyzmfye.supabase.co/rest/v1/rpc/astro_mark_attendance \
  -H "apikey: sb_publishable_9a4vSwLdVz4Yd8wrWcTvXA_aIMmC6H_" \
  -H "Content-Type: application/json" \
  -d '{"p_device_code":"ASTRO-RNK-01",
       "p_device_secret":"<your device secret>",
       "p_card_uid":"a1:b2:c3:d4",
       "p_event_uid":"11111111-1111-1111-1111-111111111111"}'
```
```json
{"ok":true,"code":"MARKED","action":"marked","status":"late","time":"08:42",
 "date":"2026-11-12","method":"rfid","period_no":null,
 "upgraded_from_absent":false,
 "student":{"roll_no":"DEMO-01","name":"Demo Student","class":"9-A"}}
```

| Situation | Response |
|---|---|
| first tap of the day | `code: MARKED`, `status: present` or `late` |
| tap again same day | `code: ALREADY_MARKED` (HTTP 200, no second row) |
| replayed `event_uid` | last result + `"duplicate": true` |
| card not registered | `code: UNKNOWN_CARD`, `ok: false` |
| arriving after the 14:45 auto-close | `MARKED` + `"upgraded_from_absent": true` |

### Errors (HTTP 400/401, JSON body)

| `message` | Meaning |
|---|---|
| `DEVICE_NOT_FOUND` / `DEVICE_DISABLED` | unknown or switched-off terminal |
| `BAD_DEVICE_SECRET` | secret does not match `secret_hash` |
| `BAD_METHOD` / `BAD_SESSION` / `PERIOD_NO_REQUIRED` / `NO_CREDENTIAL` | bad request |
| `EVENTS_MUST_BE_ARRAY` | malformed batch payload |
| `NOT_STAFF` / `SCHOOL_FORBIDDEN` | dashboard user without rights |

> The SQLSTATE in `code` (`28P01`, `22023`, …) is noise on a 16×2 LCD; the
> firmware promotes `message` to the displayed code. See `astro_cloud.h`.

## 4. Batch response

```json
{"ok":true,"code":"BATCH_DONE","accepted":3,
 "marked":1,"duplicates":1,"unknown":1,"failed":0,"results":[…]}
```

Each event is processed independently — one bad card cannot lose the rest of the
queue. Events carry the **tap time** from the terminal, so a queue uploaded at
16:00 still records the 08:05 arrival (clamped to `[now-30d, now+5min]`).

## 5. Notices, messages and email delivery

Admin writes once, families see it everywhere, because there is only one copy:
`notices` and `messages` are the source of truth and the triggers copy them into
the `alerts` outbox for delivery. No sync step, no second database.

```
admin UI ─ astro_post_notice / astro_send_message ─▶ notices | messages
                                                          │ trigger
                                                          ▼
                                             alerts (one row per guardian)
                                                    │            │
                        parent app reads notices,   │            │  worker claims
                        messages, own alerts        │            ▼
                                                    │      Resend / Gmail SMTP
```

| RPC | Caller | Returns |
|---|---|---|
| `astro_post_notice(title, body, audience, class_id, student_id, pinned, school_id, expires_at)` | admin | `{ok, notice_id, recipients, email_queued}` |
| `astro_send_message(student_id, subject, body, school_id)` | admin | `{ok, message_id, student, roll_no, email_queued, guardian_email_on_file}` |
| `astro_mark_message_read(message_id)` | student/parent, admin | `{ok, message_id, read_at, newly_read}` |
| `astro_student_feed(student_id, limit)` | student/parent, admin | `{student, unread_messages, notices[], messages[], count}` |
| `astro_outbox_stats()` | admin | `{queued, sent, failed, skipped, oldest_queued}` |
| `astro_requeue_failed()` | admin | `{ok, requeued}` — resets failed rows to `queued` |

**Fan-out rule** — an email row is written only for students that are `active`
**and** have `guardian_email` on file. `audience='all'` → whole school,
`'class'` → that class, `'student'` → that one student. A family with no email
still sees the notice in the app; it simply produces no email row, and
`recipients: 0` in the reply tells the admin that nobody would be emailed.

**Delivery** is a separate process (`services/mailer`, see its README). It calls
three server-only RPCs — `astro_claim_emails`, `astro_finish_email`,
`astro_release_stale_sending` — and needs the **secret key**, so it never runs in
the browser or on the ESP32. Until it is configured with a provider, rows simply
sit at `status='queued'`; nothing breaks and nothing is lost.

**Who can read what** (enforced by RLS *and* by the RPCs):

* admin/teacher of the school: everything in that school;
* a guardian/self via `student_links`: notices addressed to `all`, their own
  class or their own child; their child's messages; and only their child's outbox
  rows (so other families' addresses and bodies are never exposed);
* `anon`: nothing — all of the above is revoked.

### Example (verified against the live project)

```sql
-- admin, in the SQL editor or from the app
select public.astro_post_notice('PTM on Saturday',
  'Parent-teacher meeting this Saturday at 10 AM in the school hall.',
  'all', null, null, true);

{"ok": true, "notice_id": "5db82b87-…", "recipients": 2, "email_queued": true}

select public.astro_send_message(
  (select id from public.students where roll_no = 'DEMO-01'),
  'Your attendance this month',
  'You were late 3 times this month. Please reach school by 8:20 AM.');

{"ok": true, "message_id": "26d0be7d-…", "student": "Demo Student",
 "roll_no": "DEMO-01", "email_queued": true, "guardian_email_on_file": true}

-- parent app, signed in and linked to that student
select public.astro_student_feed((select id from public.students where roll_no = 'DEMO-01'));
{"ok": true, "unread_messages": 1, "count": 4, "notices": [ …3… ], "messages": [ …1… ]}
```

## 6. Security model (verified, not assumed)

* `anon` has **no privilege on any table or view** — `has_table_privilege` is
  false for all 17 tables; `GET /rest/v1/students` returns `permission denied`.
* `anon` may execute exactly six functions, all of which require a device
  secret: `astro_heartbeat`, `astro_lookup_card`, `astro_mark_attendance`,
  `astro_sync_batch`, `astro_poll_commands`, `astro_command_result`.
* `authenticated` cannot execute any internal helper: `astro_verify_device`
  (which returns the stored `secret_hash` row), `astro_ctx_school`,
  `astro_norm_uid`, `astro_sha256_hex`, `astro_try_*`, the fan-out / clean /
  guard trigger functions, `astro_maintenance`, `astro_prune_events` or the
  mailer's claim/finish RPCs. The two reporting views are `SELECT`-only.
* Role helpers answer **for one school**: `is_staff()` / `is_admin()` only
  count a membership in `current_school_id()`, and `current_school_id()` is
  ordered (`created_at, school_id`) instead of "whichever row the planner
  found first". `members` is keyed on `user_id`, so one person cannot hold two
  schools today — this closes the hazard before that ever changes.
* `astro_prune_events()` had no authorization check at all and was executable
  by `authenticated`: any signed-in parent could have deleted 30 days of
  `device_commands` and every `device_events` row older than a week, for every
  school. It is now `service_role` only (cron calls it through
  `astro_maintenance()`).
* Device secrets are stored as `sha256(secret)` only.
* Dashboard: a signed-in `admin` sees their school (verified: 1 school, 1
  student, 1 device, own membership row, `is_staff=true`, `is_admin=true`); a
  `viewer` **cannot insert** (`42501 new row violates row-level security
  policy`); a signed-in user with no membership row sees 0 rows everywhere.

**Two Supabase-specific traps that bit this project** (both now closed):

1. `ALTER DEFAULT PRIVILEGES` grants `EXECUTE` on every new function to `anon`
   *explicitly*. `revoke … from public` does **not** remove it — you must
   `revoke … from anon`. Before migration 0006 the publishable key could call
   `astro_close_day()`.
2. A policy on `members` that queries `members` inside its `USING` clause makes
   PostgreSQL raise `42P17 infinite recursion detected in policy for relation
   "members"`. Use a `SECURITY DEFINER` helper (`is_admin()`) instead.

If you add a function later: `revoke all … from public, anon;` then grant it to
the role that needs it.

## 7. Verified test matrix

| Test | Result |
|---|---|
| heartbeat with valid device | ✅ `HELLO` + school + `late_after` |
| heartbeat with wrong secret | ✅ `28P01 BAD_DEVICE_SECRET` |
| tap → present / late | ✅ `MARKED` |
| same `event_uid` replayed | ✅ `duplicate:true`, one row |
| second tap, new `event_uid` | ✅ `ALREADY_MARKED` |
| unknown card | ✅ `UNKNOWN_CARD`, no row |
| batch: good + duplicate + unknown | ✅ `marked 1, duplicates 1, unknown 1` |
| offline replay keeps tap time | ✅ row dated 2026-11-05 from a batched event |
| card UID normalisation `a1:b2:c3:d4` | ✅ → `A1B2C3D4` |
| fingerprint slot 7 (mapped) | ✅ `MARKED`, method `fingerprint` |
| fingerprint slot 999 (unmapped) | ✅ `UNKNOWN_CARD` |
| daily tap carrying `period_no` | ✅ stored as `NULL` |
| invalid method | ✅ `BAD_METHOD` |
| forged 2020 timestamp | ✅ clamped to `now - 30 days` |
| close-day on a holiday | ✅ `holidays_skipped 1`, 0 absent |
| close-day, period-only student | ✅ not marked absent |
| close-day, no taps | ✅ absent + alert queued |
| close-day run twice | ✅ idempotent |
| arrive after auto-close | ✅ `upgraded_from_absent`, queued absent alert withdrawn |
| manual absent row | ✅ never overwritten |
| provisioning a 2nd terminal | ✅ returns secret once |
| RLS: admin read + write | ✅ |
| RLS: viewer write | ✅ blocked `42501` |
| RLS: non-member read | ✅ 0 rows, no error |
| notice, audience `all` | ✅ `recipients 2` (3 active students, 1 without email) |
| notice, audience `class` | ✅ `recipients 2` — only that class |
| notice, audience `student` | ✅ `recipients 1` |
| message to one student | ✅ 1 outbox row, `email_queued true` |
| guardian sees own notices only | ✅ 3 of 3 matching; another class's/another child's not returned |
| guardian sees own messages only | ✅ 1 message for its child, 0 for a sibling account |
| guardian reads outbox directly | ✅ 4 rows (own child) instead of 6 (whole school) |
| guardian calls `astro_post_notice` | ✅ `42501 NOT_STAFF` |
| guardian marks another child's message read | ✅ `42501 NOT_ALLOWED` |
| student marks own message read twice | ✅ `newly_read true` then `false`, same `read_at` |
| `astro_student_feed` as guardian | ✅ notices + messages, `unread_messages 1` |
| worker: claim 3 | ✅ 3 rows → `sending`, `attempts 1` |
| worker: finish ok / fail | ✅ `sent` + `sent_at`; `failed` + `last_error` |
| worker: requeue failed | ✅ back to `queued`, `attempts 0` |
| worker: stale `sending` row | ✅ released to `queued` after the window |
| `anon` execute on 0011–0014 RPCs | ✅ all false |
| trigger helpers execute as `authenticated` | ✅ all false after 0013 |
| grant split across the 9 notice/message/worker RPCs | ✅ `service_role` all 9; `authenticated` the 6 admin/parent ones; `anon` none |
| `astro_save_student` edit without guardian fields | ✅ email/phone/name preserved (was: wiped) |
| `astro_save_student` bad email / blank roll | ✅ `BAD_EMAIL` / `ROLL_REQUIRED` |
| `astro_save_class` create, duplicate, delete empty | ✅ created, `CLASS_EXISTS`, deleted |
| `astro_delete_class` on 9-A (1 student) | ✅ `CLASS_NOT_EMPTY`, class kept |
| `astro_unassign_card` twice / unknown UID | ✅ idempotent / `CARD_NOT_FOUND` |
| delete a student that has attendance | ✅ `STUDENT_HAS_ATTENDANCE` (FK is `ON DELETE RESTRICT`) |
| `astro_archive_student` / reactivate | ✅ card released, fingerprints cleared, 1 queued email cancelled / active again |
| `astro_remove_member` self as last admin | ✅ `LAST_ADMIN` |
| `astro_attendance_report` normal / reversed / > 1 year | ✅ per-student %, `BAD_DATES`, `RANGE_TOO_LONG` |
| leave request → approve | ✅ 2 `leave` attendance rows, queued email, report counts them |
| duplicate approve / overlapping request | ✅ `ALREADY_DECIDED` / `LEAVE_OVERLAP` |
| leave approve → cancel | ✅ attendance cleared, **queued email withdrawn** (0026) |
| leave reject | ✅ rejection email still queued with its own subject |
| `astro_outbox_list` / `astro_requeue_alert` | ✅ lists 2 rows; skipped→queued, queued→`NOT_REQUEUEABLE` |
| `astro_device_health` | ✅ 1 terminal, `online false`, 4445 s since seen, 0 taps |
| `astro_maintenance` | ✅ `events_pruned 0`, `alerts_pruned 0`; cron re-pointed |
| fingerprint insert with null slot | ✅ `BAD_SLOT` (was a raw 23502) |
| admin posts a notice / views overview+report | ✅ `NOT_STAFF` never hit, `recipients 1` |
| viewer posts notice / saves student / inserts row | ✅ `NOT_STAFF`, `NOT_STAFF`, RLS `42501` |
| viewer reads overview / report | ✅ allowed (member) / `NOT_STAFF` |
| guardian: own feed vs sibling's feed | ✅ `count 3` / `NOT_ALLOWED` |
| guardian sees only their own student | ✅ 1 of 2 rows |
| guardian requests leave for own child / another child | ✅ pending / `NOT_ALLOWED` |
| guardian calls report, outbox, prune | ✅ `NOT_A_MEMBER` / `NOT_A_MEMBER` / `denied` |
| deleting a notice with queued mail | ✅ 0 queued rows left pointing at it |
| `authenticated` on the two views | ✅ `SELECT` only |
| SECURITY DEFINER functions without a pinned `search_path` | ✅ none |

## 8. Automation (pg_cron, UTC)

| Job | Cron | What it does |
|---|---|---|
| `astro-close-day` | `15 9 * * 1-6` (14:45 IST, Mon–Sat) | marks active students with no row as `absent`, queues guardian emails, skips holidays |
| `astro-maintenance` | `30 20 * * 0` (02:00 IST Sun) | `device_events` older than 90 days, `device_commands` older than 30, outbox rows older than 180, and any `sending` row stuck for 15 minutes |

Manual run: `select public.astro_close_day('2026-11-12');`

## 9. Day-to-day operations

**Add a student + card**
```sql
with s as (select id from public.students
           where school_id = (select id from public.schools where code='ABPS-RNK')
             and roll_no = '9A-14')
insert into public.rfid_cards (school_id, student_id, card_uid, label)
select (select id from public.schools where code='ABPS-RNK'), s.id, '04A2B3C4', 'Anant - new card'
from s;
```
(Or Dashboard ▸ Table Editor ▸ `students` ▸ *Import CSV*.)

**Register a second terminal**
```sql
select public.astro_provision_device('ABPS-RNK', 'ASTRO-RNK-02', 'Library terminal');
-- returns device_code + device_secret ONCE → put them in astro_config.h
```
Works from the SQL editor (service side) and from a signed-in staff account for
its own school only.

**Add a holiday** (the cron will skip it)
```sql
insert into public.school_holidays (school_id, holiday_date, reason)
select id, '2026-11-14', 'Diwali break' from public.schools where code='ABPS-RNK';
```

**Map an R307 fingerprint slot**
```sql
insert into public.fingerprints (device_id, school_id, slot, student_id)
select d.id, d.school_id, 12, st.id
from public.devices d, public.students st
where d.device_code = 'ASTRO-RNK-01' and st.roll_no = '9A-14';
```

**Rotate a lost terminal's secret**
```sql
select public.astro_rotate_device_secret('ASTRO-RNK-01');
```

**Give a teacher dashboard access** — Auth ▸ Users ▸ *Add user*, then:
```sql
insert into public.members (user_id, school_id, role)
select u.id, s.id, 'admin'
from auth.users u, public.schools s
where u.email = 'teacher@school.com' and s.code = 'ABPS-RNK'
on conflict (user_id) do update set role = excluded.role;
```

**Post a notice / message one student** (this is what the admin screen calls)
```sql
-- whole school
select public.astro_post_notice('Holiday on Friday',
  'School will remain closed on Friday for Guru Nanak Jayanti.', 'all', null, null, true);

-- one class (class_id from public.classes)
select public.astro_post_notice('Maths test Monday',
  'Chapter 7 test for 9-A on Monday.', 'class',
  (select id from public.classes where name='9' and section='A'));

-- one student
select public.astro_send_message(
  (select id from public.students where roll_no='DEMO-01'),
  'Fee reminder', 'Term 2 fees are due on 30 Nov.');
```
`recipients` in the reply is the number of guardians with an email on file; `0`
means everyone in that audience sees it in the app but nobody gets mail.

**Watch / drain the email queue**
```sql
select public.astro_outbox_stats();     -- queued / sent / failed / skipped
select public.astro_requeue_failed();   -- retry everything that failed
select id, kind, to_email, status, attempts, last_error
from public.alerts where status <> 'sent' order by created_at desc limit 20;
```
Delivery itself is `services/mailer` (`npm run check`, `npm run once`, or `npm start`).

**Add a class, then a student, then a card** (what the admin screen calls)
```sql
select public.astro_save_class('9', 'B', 'Mrs Iyer');          -- -> class_id
select public.astro_save_student('9B-01', 'Anant Verma',
  (select id from public.classes where name='9' and section='B'),
  'Rakesh Verma', 'rakesh@example.com', '9876500000',
  'A1B2C3D4');                                                  -- card attached
-- edit later: only the fields you pass change
select public.astro_save_student(null, 'Anant V.', null, null, null, null, null, null, null,
  (select id from public.students where roll_no='9B-01'));
```
A blank string (`''`) clears a field; `null` leaves it alone.

**Remove a student without losing history**
```sql
select public.astro_archive_student((select id from public.students where roll_no='9B-01'));
-- card released, fingerprints cleared, queued mail cancelled, attendance kept.
-- Deleting the row itself is refused once any attendance exists.
```

**Approve leave** (the parent app calls `astro_request_leave`)
```sql
select * from public.astro_pending_leaves();
select public.astro_decide_leave('<leave id>', true, 'Approved by class teacher');
-- approval writes status='leave' for each school day in the range (skipping
-- weekly-offs and holidays), withdraws any queued absence email, and queues a
-- decision email to the guardian.  astro_cancel_leave() undoes it.
```

**Monthly report for a class**
```sql
select public.astro_attendance_report('2026-11-01', '2026-11-30',
  (select id from public.classes where name='9' and section='A'));
-- {school_days, totals, students:[{present, late, absent, leave, percent}]}
```

**See what the mailer is doing**
```sql
select public.astro_outbox_list('failed');           -- or queued / sent / skipped
select public.astro_requeue_alert(53);               -- retry one row
select public.astro_device_health();                 -- terminals, last seen, queue depth
```

**Remove the demo row before go-live**
```sql
delete from public.alerts where student_id in (select id from public.students where roll_no='DEMO-01');
delete from public.notices;     -- old notices are visible to every family
delete from public.messages;
delete from public.attendance where student_id in (select id from public.students where roll_no='DEMO-01');
delete from public.rfid_cards where card_uid = 'A1B2C3D4';
delete from public.students   where roll_no = 'DEMO-01';
```

## 10. Still open (needs your decisions)

| Item | Why it matters |
|---|---|
| `late_after` `08:20`, `day_end` `14:00` | guessed values — set the school's real timings |
| ~~`site_url`, redirect list, open signups~~ | fixed 2026-11-12: `site_url` = the Firebase host, both hosts + localhost allowed, signups **disabled** (accounts are provisioned by an admin, then `members` / `student_links` grants access) |
| No mail provider configured | rows reach `status='queued'` and stop there until `services/mailer` has a Resend key or a Gmail app password |
| Screens built, not yet used on a real browser | `web/` now carries the staff and parent dashboards and `tests/web` boots them headlessly against a fake Supabase (77 assertions). Nothing in the build sandbox can reach `*.supabase.co`, so the first real sign-in is still to happen — see `web/README.md` |
| Region `ap-southeast-2` | chosen at creation, not changeable; ~90–140 ms from Renukoot |
| Free tier | no point-in-time backups; pauses after ~7 days idle (cron keeps it warm) |


## 11. Second audit pass — 2026-11-12

Everything below was found by reading the live definitions, then fixed,
applied, and re-tested against the project. Each item says how it was proved.

| # | Finding | Why it mattered | Fix / proof |
|---|---|---|---|
| 1 | `astro_prune_events()` had **no authorization check** and was executable by `authenticated` | any signed-in parent could delete `device_commands` younger than 30 days and every `device_events` older than a week, in every school — a one-line audit wipe | revoked to `service_role` (0025); `authenticated` now gets `permission denied for function astro_prune_events` |
| 2 | Cancelling or deleting an approved leave left its "Leave approved" email queued | parent is told a leave is approved *after* the school withdrew it. Two orphaned rows were sitting in the live queue | `leave_requests_outbox` trigger (0026). Proved: approve → 1 queued, cancel → 0 queued, reject → rejection email still queued |
| 3 | `astro_save_student()` overwrote `guardian_email/phone/name` with `NULL` on every partial edit | renaming a student or moving them to another class silently deleted the only contact the school has | NULL now means "keep", `''` means "clear" (0023). Proved: email survives a name-only edit |
| 4 | `students → attendance` was `ON DELETE CASCADE` | one click in the table editor destroyed a student's entire attendance history — the record the school must keep for years | FK is `ON DELETE RESTRICT` + `students_guard_delete` trigger + `astro_archive_student()` (0023). Proved: `STUDENT_HAS_ATTENDANCE`, history intact |
| 5 | `astro_verify_device()` returns the whole `devices` row (including `secret_hash`) and was executable by `authenticated`; `astro_ctx_school`, `astro_norm_uid`, `astro_sha256_hex`, `astro_try_*`, the fan-out/clean/guard triggers were reachable too | internal plumbing on a public REST surface; a leaked `secret_hash` turns a device secret into an offline cracking target | revoked in 0025. Proved: `anon` can execute exactly the 6 device RPCs; `authenticated` none of the internals |
| 6 | `authenticated` held INSERT/UPDATE/DELETE on `v_attendance_feed` and `v_daily_attendance` | reads-only views advertising write privileges; RLS still applied, but a grant mistake is one policy away from a hole | `SELECT` only (0025) |
| 7 | `is_staff()` / `is_admin()` counted a membership in *any* school, and `current_school_id()` had no `ORDER BY` | harmless today only because `members` is keyed on `user_id`; the day a teacher covers two schools it becomes an admin-in-A/viewer-in-B escalation | role helpers now answer for one school, resolution is deterministic, `is_staff(uuid)` / `is_admin(uuid)` overloads added (0022) |
| 8 | No admin reporting or diagnostics existed at all | "who was absent last month", "did the email go out", "is the terminal alive", "retry that one email" were all SQL-editor-only | `astro_attendance_report`, `astro_outbox_list`, `astro_requeue_alert`, `astro_pending_leaves`, `astro_device_health`, `astro_prune_alerts`, `astro_maintenance` (0024) |
| 9 | Classes could only be created in SQL; a lost card could not be released; a dashboard member could not be removed | the admin screen would have had to poke tables directly, bypassing every validation | `astro_save_class`, `astro_delete_class` (refuses a non-empty class), `astro_unassign_card`, `astro_remove_member` (0023) |
| 10 | Inserting a fingerprint with a null slot raised a raw `23502 not-null violation` | an unhelpful error surfacing on the enrolment screen | `fingerprints_guard` trigger answers `BAD_SLOT` |
| 11 | Auth was configured for `http://localhost:3000`, redirects empty, signups open | hosted login at the Firebase URL would have failed, and anyone could create an account | `site_url` = `https://astro-smart-attendence.web.app`, both Firebase hosts + localhost allowed, **signups disabled** (accounts are provisioned: add the user in Auth, then a `members` or `student_links` row) |

**Also fixed outside the database**

`firmware/test/host/run.sh` — the documented firmware test command — did not
run on a fresh clone: it compiles against `firmware/test/host/test_config/astro_config.h`,
which had never been committed because `.gitignore` excludes every
`firmware/**/astro_config.h` (correctly — that is where Wi-Fi passwords live).
The credential-free test config is now committed, with an explicit
`!firmware/test/host/test_config/astro_config.h` exception, and the suite is
green again: **45 passed, 0 failed**, plus a clean `astro_attendance.ino`
syntax check. The mailer is at **17 passed**.

**Left alone on purpose**

* Notices have no scheduled publishing (`publish_at` exists, but `astro_post_notice`
  fans out immediately and does not accept it) — a scheduled notice needs a cron
  sweep, and nothing has asked for one yet.
* A guardian's leave request does not email staff: there is no staff email
  address, and the admin screen gets it instantly through Realtime.
* `astro_attendance_report` clamps the end date to today and refuses ranges over
  a year; asking for a future range returns `school_days: 0` rather than
  pretending those days happened.
* `members` is one school per user (`PRIMARY KEY (user_id)`). Supporting staff
  who work at two schools is a `(user_id, school_id)` primary key away — the
  role helpers and every RLS policy are already school-scoped for it.

**Check the state yourself**

```sql
select public.astro_outbox_stats();          -- queue depth by status
select public.astro_device_health();         -- terminals
select * from public.astro_pending_leaves(); -- leave approvals waiting
select public.astro_attendance_report(current_date - 30, current_date);
```

## 12. The web dashboard — 2026-11-12

`web/` is a static dashboard that speaks to this project with plain `fetch`
(password grant, silent refresh, `/rest/v1/rpc/*`). No SDK, no build step:
`index.html` + `styles.css` + `js/`, deployed to any static host.

* staff (`admin` / `teacher` / `viewer`): today's attendance, date-range report
  with CSV, students + classes + cards + fingerprints, notices, message inbox,
  leave approvals, school timings, holidays, terminal check, email queue
* parent (`student`): colour-coded month calendar, notices, thread with the
  school, leave request form
* every write goes through an RPC — the dashboard never inserts into a table
* `tests/web` boots the real modules in jsdom against a fake Supabase:
  `cd tests/web && npm install && npm test` → `77 passed, 0 failed`

Contracts were checked against the live project, not assumed: every RPC name
and argument list was read from `pg_proc`, and `astro_update_settings`,
`astro_student_calendar`, `astro_inbox` and friends were called as the demo
`admin` and demo guardian (JWT claims set inside a transaction) to confirm the
JSON they return matches what the screens read.

Two client bugs found this way and fixed:

| Bug | Effect | Fix |
|---|---|---|
| a notice expiry was sent as `new Date(local).toISOString()`, i.e. read in the *browser's* timezone | a laptop set to UTC expired notices 5 h 30 m late | `zonedToIso()` reads the digits as the school's wall clock (`Asia/Kolkata`), tested for IST and UTC |
| `astro_update_settings` has `p_clear_absent_after`, and the screen never sent it | the auto-absent cut-off could be set once and never removed | Settings has a "No automatic absent marking" switch wired to that flag |

Demo history so the screens have something to show (`tools/demo_seed.sql`,
idempotent, safe to re-run): DEMO-01 joins on 1 Apr, then 2–12 Nov of mixed
attendance, one approved leave (5–6 Nov) and a holiday on 19 Nov. As the
guardian the calendar now reads present 5 · late 1 · absent 2 · leave 2 ·
holiday 1 · weekly off 5 · **75%**.

### The device-command channel, proved 2026-11-12

The dashboard's Devices tab and the student form's *Scan a card* / *Enrol
fingerprint* buttons write into `device_commands`; nothing was ever going to
consume those rows, because the terminal firmware had no command loop. It has
one now (`astro_poll_commands` every 3 s → do the work → `astro_command_result`),
and the channel was exercised against this project with a throwaway device:

```sql
select public.astro_provision_device('ABPS-RNK','TEMP-BENCH-01','Bench',  '<secret>');
-- as the demo admin: lcd_text "HELLO 9A" + rfid_capture queued
set local role anon;                       -- what a real terminal is
select public.astro_poll_commands('TEMP-BENCH-01','<secret>', 3);
select public.astro_command_result('TEMP-BENCH-01','<secret>','<id>', true, '{"uid":"A1B2C3D4"}');
```

Results: the poll returned both commands with the payloads the firmware reads
(`{line1, line2, hold_seconds}` — the server normalises `text` itself), the
capture came back `status:'done'` with `known:true` and
`owner:{name:'Demo Student', roll_no:'DEMO-01', active:true}`, and replaying the
same result returned `ALREADY_RECORDED` instead of writing twice. The bench
device and its commands were deleted; `ASTRO-RNK-01` was not modified.

Two firmware bugs fell out of that test: it read `payload.text` (which the
server never stores) and it ignored the server-chosen `slot`. Both fixed.
