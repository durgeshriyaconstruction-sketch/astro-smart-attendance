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
```

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

## 2. Tables (14, all with RLS)

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
  false for all 14 tables; `GET /rest/v1/students` returns `permission denied`.
* `anon` may execute exactly four functions: `astro_heartbeat`,
  `astro_lookup_card`, `astro_mark_attendance`, `astro_sync_batch`. It cannot
  execute `astro_close_day`, `astro_prune_events`, `astro_provision_device`,
  `astro_rotate_device_secret`, `astro_verify_device`, the notice/message RPCs,
  the outbox worker RPCs or the internal helpers (migration 0013 revoked the
  trigger and utility functions from `authenticated` too).
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

## 8. Automation (pg_cron, UTC)

| Job | Cron | What it does |
|---|---|---|
| `astro-close-day` | `15 9 * * 1-6` (14:45 IST, Mon–Sat) | marks active students with no row as `absent`, queues guardian emails, skips holidays |
| `astro-prune-events` | `30 20 * * 0` (02:00 IST Sun) | deletes `device_events` older than 90 days |

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
| `site_url = http://localhost:3000`, empty redirect allow-list | hosted dashboard login will fail |
| Signups enabled | anyone can create an account (sees nothing, but noise) |
| No mail provider configured | rows reach `status='queued'` and stop there until `services/mailer` has a Resend key or a Gmail app password |
| No admin/student screens yet | the RPCs and RLS are live; the dashboards that call them are not built |
| Region `ap-southeast-2` | chosen at creation, not changeable; ~90–140 ms from Renukoot |
| Free tier | no point-in-time backups; pauses after ~7 days idle (cron keeps it warm) |
