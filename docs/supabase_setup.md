# Supabase setup — what was built in `nrjchonjlncamfyzmfye`

Applied on **2026-11-12** directly to the project (region `ap-southeast-2`,
Postgres 17). SQL is kept in `supabase/migrations/` so it can be replayed on a
fresh project or moved to Neon later.

```
supabase/migrations/0001_schema.sql          tables, RLS, views
supabase/migrations/0002_device_api.sql      the four device RPCs
supabase/migrations/0003_seed.sql            school + device + demo row
supabase/migrations/0004_automation.sql      pg_cron end-of-day closure
```

---

## 1. Connection facts

| Item | Value |
|---|---|
| Project URL | `https://nrjchonjlncamfyzmfye.supabase.co` |
| REST endpoint | `https://nrjchonjlncamfyzmfye.supabase.co/rest/v1` |
| Publishable key (device + browser) | `sb_publishable_9a4vSwLdVz4Yd8wrWcTvXA_aIMmC6H_` |
| Legacy `anon` key (same role, older format) | in **Settings ▸ API Keys** — also fine |
| Secret / `service_role` key | **server only** — never in firmware, never in a browser |
| Direct Postgres | `db.nrjchonjlncamfyzmfye.supabase.co:5432` (pooler on `:6543`) |

> The publishable key is not a password. It is only useful if a row-level
> security policy or a granted function lets it do something — here that is
> exactly four functions and nothing else.

## 2. Tables

| Table | Holds |
|---|---|
| `schools` | one row per school: timezone, `day_start`, `late_after`, `day_end` |
| `classes` | class + section + teacher (`9/A`) |
| `students` | roll number, name, guardian email/phone, `fingerprint_id` (R307 slot) |
| `rfid_cards` | card UID → student, `active` flag, label |
| `devices` | terminals: `device_code`, `secret_hash`, firmware, last seen, RSSI |
| `attendance` | one row per student per day (`session='daily'`) or per period |
| `device_events` | every raw tap incl. replays, `event_uid` unique → idempotent sync |
| `alerts` | queued parent emails (`late`, `absent`, …) with `status` |
| `members` | dashboard users → school + role (`admin` / `teacher` / `viewer`) |
| `student_links` | student/guardian self-service view of their own rows |

Views for the dashboard: `v_attendance_feed` (readable feed) and
`v_daily_attendance` (present/late/absent counts per day).

**Uniqueness that protects the data**

* `attendance (student_id, attendance_date, session, coalesce(period_no,0))` —
  a second tap can never create a second row for the same slot.
* `device_events.event_uid` — replaying the offline queue 100 times writes once.
* `rfid_cards.card_uid` — one card cannot belong to two students.

## 3. The four RPCs the terminal uses

All are `SECURITY DEFINER`, validate `device_code` + `device_secret`
(sha256 check), and are the **only** thing `anon` may execute.

### `astro_heartbeat`
```bash
curl -s -X POST https://nrjchonjlncamfyzmfye.supabase.co/rest/v1/rpc/astro_heartbeat \
  -H "apikey: sb_publishable_9a4vSwLdVz4Yd8wrWcTvXA_aIMmC6H_" \
  -H "Authorization: Bearer sb_publishable_9a4vSwLdVz4Yd8wrWcTvXA_aIMmC6H_" \
  -H "Content-Type: application/json" \
  -d '{"p_device_code":"ASTRO-RNK-01","p_device_secret":"<your device secret>","p_firmware":"astro-1.0.0"}'
```
```json
{"ok":true,"code":"HELLO","school":"The Aditya Birla Public School, Renukoot",
 "late_after":"08:20","day_start":"08:00","day_end":"14:00",
 "server_time":"2026-11-12T15:47:36","local_date":"2026-11-12","local_time":"15:47:36",
 "server_epoch":1794478657}
```

### `astro_mark_attendance`
```bash
curl -s -X POST https://nrjchonjlncamfyzmfye.supabase.co/rest/v1/rpc/astro_mark_attendance \
  -H "apikey: sb_publishable_9a4vSwLdVz4Yd8wrWcTvXA_aIMmC6H_" \
  -H "Content-Type: application/json" \
  -d '{"p_device_code":"ASTRO-RNK-01",
       "p_device_secret":"<your device secret>",
       "p_card_uid":"A1:B2:C3:D4",
       "p_event_uid":"11111111-1111-1111-1111-111111111111"}'
```
```json
{"ok":true,"code":"MARKED","action":"marked","status":"late","time":"15:47",
 "student":{"id":"…","roll_no":"DEMO-01","name":"Demo Student","class":"9-A"}}
```
Same request again (same or new `event_uid`):
```json
{"ok":true,"code":"ALREADY_MARKED","action":"already_marked","status":"late",…}
{"ok":true,"code":"MARKED","duplicate":true,…}
```
Unknown card: `{"ok":false,"code":"UNKNOWN_CARD"}` — HTTP 200, no row written.

### `astro_sync_batch`
```json
{"p_device_code":"ASTRO-RNK-01","p_device_secret":"…",
 "p_events":[{"card_uid":"A1B2C3D4","event_uid":"…","event_ts":"2026-11-12T03:10:00Z"},
             {"card_uid":"BAD","event_uid":"…"}]}
```
→ `{"code":"BATCH_DONE","accepted":2,"failed":0,"results":[…]}`

Each event is processed independently, so one bad card cannot lose the rest of
the queue. Events are timestamped **at tap time** on the terminal, so a queue that
uploads at 16:00 still records the 08:05 arrival.

### `astro_lookup_card`
Read-only "is this card registered?" for the enrol screen.

**Errors** come back as HTTP 400 with a JSON body:

| `message` | Meaning |
|---|---|
| `DEVICE_NOT_FOUND` | unknown `device_code` |
| `DEVICE_DISABLED` | `devices.active = false` |
| `BAD_DEVICE_SECRET` | secret does not match `secret_hash` |
| `EVENTS_MUST_BE_ARRAY` | malformed batch payload |
| `NO_CREDENTIAL` / `BAD_SESSION` / `PERIOD_NO_REQUIRED` | bad request parameters |

## 4. Security model

* `anon` (the key in the firmware) has **no privileges on any table**. Direct
  `GET /rest/v1/students` returns `401 / permission denied`. Verified.
* RLS is enabled on all ten tables; dashboard users see only their own school
  (`members.school_id`), students/guardians only their own rows
  (`student_links`).
* Device secrets are stored as `sha256(secret)`; the plain secret exists only in
  the firmware and in your records. A leaked database backup does not leak them.
* `service_role` bypasses RLS: server-side only (edge functions, admin scripts).

## 5. Automation already scheduled (`pg_cron`, UTC)

| Job | Cron | What it does |
|---|---|---|
| `astro-close-day` | `15 9 * * 1-6` (14:45 IST, Mon–Sat) | marks every active student with no tap as `absent`, queues a guardian email for each |
| `astro-prune-events` | `30 20 * * 0` (02:00 IST, Sun) | deletes `device_events` older than 90 days |

Manual run: `select public.astro_close_day('2026-11-12');`

## 6. Day-to-day operations

**Add a student + card**

```sql
with s as (select id from public.students
           where school_id = (select id from public.schools where code='ABPS-RNK')
             and roll_no = '9A-14')
insert into public.rfid_cards (school_id, student_id, card_uid, label)
select (select id from public.schools where code='ABPS-RNK'), s.id, '04A2B3C4', 'Anant - new card'
from s;
```

**Bulk import students** — Dashboard ▸ Table Editor ▸ `students` ▸ *Import CSV*
(columns: `school_id`, `class_id`, `roll_no`, `full_name`, `guardian_email`).

**Register a new terminal**

```sql
select public.astro_provision_device('ABPS-RNK', 'ASTRO-RNK-02', 'Library terminal');
-- returns device_code + device_secret ONCE -> put them in astro_config.h
```
(Run it from the dashboard SQL editor or as a signed-in `admin` — it refuses
anonymous callers.)

**Rotate a lost terminal's secret**

```sql
select public.astro_rotate_device_secret('ASTRO-RNK-01');
```

**Give a teacher dashboard access**

1. Authentication ▸ Users ▸ *Add user* (email + password).
2. Then, once:
```sql
insert into public.members (user_id, school_id, role)
select u.id, s.id, 'admin'
from auth.users u, public.schools s
where u.email = 'teacher@school.com' and s.code = 'ABPS-RNK'
on conflict (user_id) do update set role = excluded.role;
```
The web dashboard then calls `/rest/v1/v_attendance_feed` with that user's JWT and
sees only the school's data.

**Demo data to remove before go-live**

```sql
delete from public.attendance where student_id in
  (select id from public.students where roll_no = 'DEMO-01');
delete from public.rfid_cards where card_uid = 'A1B2C3D4';
delete from public.students   where roll_no = 'DEMO-01';
```

## 7. Things worth knowing

* **Region** is `ap-southeast-2` (Sydney) — chosen at project creation and not
  changeable afterwards. Round-trip from Renukoot is ~90–140 ms, which is fine
  for one tap per student and is why the terminal shows its own local result
  first. If you ever want Mumbai (`ap-south-1`), create a new project and replay
  the four files in `supabase/migrations/`.
* **Free-tier pause**: a free project pauses after ~7 days with no activity. The
  nightly cron keeps the database warm, but check the project is `ACTIVE_HEALTHY`
  before a demo.
* **Parent emails** are *queued* in `alerts`, not sent yet — sending needs an SMTP
  provider (Resend / Gmail app password). The Gmail app is currently switched off
  for this conversation; turn it on and the dispatcher can be wired next.
* **Neon**: nothing here blocks it. The schema uses standard Postgres
  (`pgcrypto`, `pg_cron`, `uuid`), so `pg_dump` / migration replay works when you
  want the Neon connection strings set up.
