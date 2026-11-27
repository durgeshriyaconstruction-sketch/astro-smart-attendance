# Supabase → Firebase sync (`astro-firebase-sync`)

The ESP32 terminal and the web dashboard both read Firebase RTDB. Supabase is the
system of record. This edge function is the only thing that writes into Firebase,
so Firebase can stay on the Spark (free) plan and no browser ever holds a
Firebase credential.

```
ESP32 ──RFID scans──► Supabase (Postgres + RPCs)
                        │
                        └─ pg trigger ──► astro-firebase-sync ──► Firebase RTDB
                                          (service account)        students/
                                                                   history/
                                                                   scans/<date>/
                                                                   devices/
                                                                   notices/
                                                                   holidays/
                                                                   settings
                                                                   meta/lastSync
```

Live project: `nrjchonjlncamfyzmfye` (ap-southeast-2).
Firebase RTDB: `https://astro-smart-attendence-default-rtdb.asia-southeast1.firebasedatabase.app`

---

## Current status (verified 2026-11-27)

| Check | Result |
| --- | --- |
| `astro-firebase-sync` deployed | version 9, `verify_jwt = false` |
| Manual full sync | `200` — 20 students, 224 attendance rows, 12 days, 1 device, 4 notices |
| Trigger path (`update public.devices ...`) | `200`, same payload |
| `meta/lastSync` stored in RTDB | yes |
| Anonymous RTDB read | `401 Permission denied` — security rules are active |

---

## What was broken

Three separate faults, all of which had to be fixed before a single row reached
Firebase:

1. **`verify_jwt = true` on the function.** The caller is a Postgres trigger
   firing through `pg_net`, which has no Supabase JWT. Every trigger call was
   answered with
   `401 UNAUTHORIZED_NO_AUTH_HEADER: Missing authorization header`
   (see `net._http_response` id 21362). The function is now deployed with
   `verify_jwt = false` and authorises on the `X-Bridge-Secret` header instead,
   which is checked against `BRIDGE_WEBHOOK_SECRET` / `ASTRO_FIREBASE_SYNC_TOKEN`.

2. **Column names that do not exist.** The old body mapped `students.rfid_uid`,
   `students.display_name`, `students.class_name`, `students.parent_contact`,
   `attendance.date`, `attendance.time`, `classes.class_name` and
   `devices.device_code`/`devices.rssi`. None of those are in the live schema, so
   attendance resolved to 0 rows and every student field came out blank. The
   current body reads the real schema:

   | Firebase field | Supabase source |
   | --- | --- |
   | `/students/<RFID>` key | `rfid_cards.card_uid` (fallback `students.roll_no`) |
   | `name`, `roll` | `students.full_name`, `students.roll_no` |
   | `className`, `section` | `classes.name`, `classes.section` |
   | `parentEmail`, `parentPhone` | `students.guardian_email`, `students.guardian_phone` |
   | `/history/<RFID>/<date>` | `attendance.status` (`daily` session) |
   | `/scans/<date>/<RFID>` | `attendance` rows with IST time from `marked_at` |
   | `/devices/<code>` | `devices.device_code`, `firmware`, `ip`, `wifi_rssi` |
   | `/holidays` | `school_holidays.holiday_date` → reason |
   | `/notices/current` | newest live `notices` row, as the firmware's plain string |
   | `/settings` | `schools.day_start`, `day_end`, `late_after`, `weekly_off` |

3. **`BOOT_ERROR` on deploy (503).** Two causes, both now removed:
   - `supabase-js` / `deno.land/std` remote imports. The working functions in
     this project (`astro-export`, `astro-mail`) import nothing, and any remote
     import that fails to resolve kills the isolate before the handler runs.
     The function now uses `Deno.serve` and plain `fetch` against PostgREST.
   - The stored `FIREBASE_SERVICE_ACCOUNT_JSON` secret contains a raw newline
     inside a string literal, which is illegal JSON. `parseServiceAccount()`
     now retries after stripping raw whitespace and re-expanding escaped `\n`.

---

## Deploying again

Source of truth: `supabase/functions/astro-firebase-sync/index.ts`.
The file deliberately contains no backslash escape sequences, so it can be sent
as a JSON string body without a second round of escaping.

```bash
# 1. type-check and compile (stub Deno globals; no network import needed)
tsc --noEmit --strict --target ESNext --module ESNext \
    --moduleResolution bundler --lib ESNext,DOM \
    supabase/functions/astro-firebase-sync/index.ts

# 2. deploy (keeps verify_jwt = false)
supabase functions deploy astro-firebase-sync --no-verify-jwt \
  --project-ref nrjchonjlncamfyzmfye
```

Deploying from the dashboard editor works too: paste the file, then confirm
**Enforce JWT verification is OFF** in the function settings.

## Running a sync by hand

```sql
-- queues the request through pg_net, returns the request id
select public.astro_trigger_firebase_full_sync();

-- what came back (pg_net keeps responses for ~2 days)
select id, status_code, content
  from net._http_response
 order by id desc
 limit 5;
```

Expected body:

```json
{"ok":true,"source":"supabase-edge-bridge","mode":"full_sync",
 "studentCount":20,"attendanceRows":224,"dayCount":12,
 "deviceCount":1,"noticeCount":4,"holidayCount":0,
 "syncedAt":"2026-11-27T12:09:43.957Z"}
```

## Failure codes

| Body | Meaning |
| --- | --- |
| `UNAUTHORIZED` (401) | `X-Bridge-Secret` missing or does not match the secret |
| `BRIDGE_SECRET_NOT_CONFIGURED` (500) | neither secret env var is set |
| `FIREBASE_CONFIG_MISSING` (500) | `FIREBASE_DB_URL` or `FIREBASE_SERVICE_ACCOUNT_JSON` unset |
| `SERVICE_ACCOUNT_INVALID` (500) | JSON parsed but has no `client_email` / `private_key` |
| `SUPABASE_ENV_MISSING` (500) | `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` not injected |
| `Google OAuth2 exchange failed` | the service-account key was revoked, or the system clock is off |
| `Firebase RTDB PUT /x failed (401)` | RTDB rules reject the service account (check `database.rules.json`) |
| `BOOT_ERROR` from the platform | the module did not load — look for a remote import or a syntax error |

## Related pieces

- `public.astro_notify_firebase_sync()` — statement-level trigger on `students`,
  `attendance`, `devices`, `notices`. Posts `{type, table, schema, mode:"statement"}`
  to the function URL stored in `private_bridge_config.firebase_sync_url` with the
  secret from `private_bridge_config.bridge_webhook_secret`.
- `public.astro_trigger_firebase_full_sync()` — manual full sync, returns the
  pg_net request id, raises `BRIDGE_CONFIG_NOT_SET` if the config rows are blank.
- `public.private_bridge_config` — the two config rows above. Not readable by
  `anon`/`authenticated`; `postgres` and `service_role` only.

## Known limitations

- Full sync only. Every trigger call rebuilds the whole mirror, so a busy scan
  day means several full rebuilds per minute. Fine for one terminal; if a second
  device is added, switch the trigger to pass the changed student id and write a
  single `/students/<rfid>` node instead.
- `/scans` is additive: days present in Supabase are written, old days are never
  pruned from Firebase.
- `email` on the student mirror is blank on purpose. Student login is an Auth
  concern and is not mirrored into the public RTDB.
- The terminal's own `/students` pull is capped at 45 000 bytes (firmware
  guard), so the mirror must stay lean. Adding large fields will break the
  device pull before it breaks the dashboard.
