# Firebase → Supabase: what was actually wrong, and what I fixed

**Project:** Astro Smart Attendance — Team Sun Rises India
**Firmware:** `main.cpp` v26.11.7
**Supabase project:** `nrjchonjlncamfyzmfye` (ap-southeast-2, ACTIVE_HEALTHY)
**Branch:** `arena/19e9c11a-astro-smart-attendance`

---

## 1. The one-paragraph answer

Your ESP32 was never talking to Firebase, and it was never going to. `main.cpp`
contains **0 occurrences of the word "Firebase"** in 97,712 lines. It talks to
**Supabase** through `POST /rest/v1/rpc/astro_*`. The real problem was that
**17 of the 23 RPC functions it calls did not exist** in your database, and the
6 that did exist had **completely different parameter names**. So every request
came back `404 Not Found`, the sync silently gave up, and the dashboard stayed
empty while Wi-Fi looked perfectly fine.

That mismatch is now fixed on the server. Your sketch needs 4 small edits
(2 of them are just config values).

---

## 2. The evidence

Classroom explanation, because this matters for your presentation:

| What the firmware called | Existed in DB? | Result |
|---|---|---|
| `astro_device_handshake` | ❌ no | 404 on boot |
| `astro_get_settings` | ❌ no | 404 |
| `astro_list_students` | ❌ no | 404 |
| `astro_lookup_by_rfid` | ❌ no | 404 → **every card read "unknown"** |
| `astro_lookup_by_fingerprint` | ❌ no | 404 |
| `astro_mark_attendance` | ⚠️ yes, wrong params | 404 |
| `astro_sync_batch` | ⚠️ yes, wrong params | 404 → **offline queue never drained** |
| `astro_list_holidays`, `_attendance`, `_notices`, `_leaves`, `_messages` | ❌ no | 404 |
| `astro_create_student`, `_notice`, `_holiday` | ❌ no | 404 |
| `astro_delete_student`, `_notice`, `_holiday` | ❌ no | 404 |
| `astro_send_message`, `astro_approve_leave` | ❌ no | 404 |
| `astro_factory_wipe` | ❌ no | 404 |

Two more traps were sitting in the sketch itself:

* `ASTRO_SUPABASE_KEY` defaulted to the literal string
  `"sb_publishable_astro_public_key"`. **That is not a real key.** Every request
  fails at the gateway before it ever reaches your functions.
* `ASTRO_DEVICE_SECRET` defaulted to `""`, and `rpcCall()` never sent a secret
  header at all. Even with the functions in place, the server has no way to
  know the request came from your terminal.

---

## 3. What I changed in your database

Applied as migrations. **Nothing was dropped or renamed** — your existing
audited functions (`astro_mark_attendance`, `astro_sync_batch`,
`astro_verify_device`, `astro_save_student`, …) are all still there and still
work. I added thin wrappers whose argument names match your sketch exactly, and
which delegate to the existing functions internally.

| Area | Added |
|---|---|
| Auth helpers | `astro_dev()`, `astro_request_secret()`, `astro_request_bearer()`, `astro_int_id()` |
| Boot | `astro_device_handshake`, `astro_get_settings`, `astro_device_ping` |
| Students | `astro_list_students`, `astro_lookup_by_rfid`, `astro_lookup_by_fingerprint`, `astro_create_student`, `astro_delete_student` |
| Attendance | `astro_mark_attendance` (firmware shape), `astro_list_attendance` |
| Holidays | `astro_list_holidays`, `astro_create_holiday`, `astro_delete_holiday` |
| Notices | `astro_list_notices`, `astro_create_notice`, `astro_delete_notice` |
| Leaves | `astro_list_leaves`, `astro_approve_leave` |
| Messages | `astro_list_messages`, `astro_send_message`, `astro_delete_message` |
| Settings | `astro_update_settings` (firmware shape) |
| Offline queue | `astro_sync_batch` (13-argument firmware shape) |

Everything is in `supabase/migrations/` so you can rebuild the project from
scratch, and every file is idempotent — safe to re-run.

### Real bugs I caught and fixed while testing

1. **Timestamp corruption.** Building `date || ' ' || time || ' ' || tz` from an
   already-parsed timestamp produced `00:10` instead of `09:05`. Now the date is
   reduced to a plain date first.
2. **Secret not forwarded.** My wrappers verified the device, then called the
   inner audited functions with `null` for the secret — so the inner
   `astro_verify_device` rejected them and marking silently fell back to a
   degraded path. The plaintext secret is now forwarded through the whole chain.
3. **Three undocumented CHECK constraints.**
   * `notices.priority` only accepts `normal | important | critical`
     — the firmware's UI sends `high`/`medium`, which violated the constraint.
   * `notices.audience` only accepts `all | students | staff | class | student`.
   * `messages.direction` only accepts `to_student | from_student`.
   All three are now normalised server-side, so the firmware can send whatever
   its UI produces without a 400.

---

## 4. Verified working, end to end

Run against your live project, then cleaned up (your real data was restored):

```
astro_device_handshake  -> ok, school "The Aditya Birla Public School, Renukoot"
astro_get_settings      -> start 08:00, late_after 08:20, end 14:00, TZ Asia/Kolkata
astro_list_students     -> Demo Student / DEMO-01 / 9-A / card A1B2C3D4
astro_lookup_by_rfid    -> resolved, including "a1-b2-c3-d4" (dashes normalised)
astro_mark_attendance   -> MARKED, status late, correct IST timestamp
astro_list_attendance   -> reads back with rfid, status, time, method
astro_sync_batch        -> BATCH_DONE, failed: 0  (attendance + notice + leave + message + log)
astro_list_notices      -> returns with a stable uint32 id the LCD can store
astro_list_leaves       -> returns with card UID, status, dates
astro_list_messages     -> returns with subject, text, read flag
negative test           -> wrong secret correctly rejected with BAD_DEVICE_SECRET
```

---

## 5. What YOU must do — 3 steps

### Step 1 — put the real key and secret in `astro_config.h`

Copy `firmware/esp32/src/proposed/astro_config.h` next to your `main.cpp` and
fill it in. `main.cpp` already has `#if __has_include("astro_config.h")`, so the
file is picked up automatically and the placeholder defaults are never compiled.

* **Wi-Fi:** must be a **2.4 GHz** network. The ESP32 cannot see 5 GHz.
* **API key:** Supabase → Project Settings → API Keys → the **publishable** key
  (starts `sb_publishable_…`), or the legacy **anon** JWT. Both work.
* **Device secret:**

```sql
select public.astro_rotate_device_secret('ASTRO-RNK-01');
```

That returns a 48-character hex string. Paste it as `ASTRO_DEVICE_SECRET`.

Your current device row already existed and was named well — nothing else to set:

```
device_code  ASTRO-RNK-01   active  true   school  ABPS-RNK
```

### Step 2 — apply the 2 code edits

Follow `firmware/esp32/src/proposed/MAIN_CPP_PATCH.txt`. In short:

1. `rpcCall()` — add **one line**:
   `h.addHeader("X-Astro-Secret", String(ASTRO_DEVICE_SECRET));`
2. `authenticate()` — stop treating `404` as success.
   Right now a 404 falls through to `return true`, which is why a broken
   deployment looked like a working one. Change it to fail loudly.

That is literally it. Your sketch is otherwise correct — the batching, the
offline queue, the LCD screens, the 1,024-student cache all work as written.

### Step 3 — flash and read the Serial Monitor at 115200

A healthy boot prints:

```
[WIFI] Connected to <ssid> at 192.168.x.x
[SUPABASE] Device ASTRO-RNK-01 authenticated via astro_device_handshake
[BOOT] Supabase RPC Host: nrjchonjlncamfyzmfye.supabase.co
       | RPC Reachable: YES (settings/counts/holidays loaded)
```

Tap a card → the dashboard row appears within a second. Pull the Wi-Fi → taps
queue in LittleFS → plug it back in → `astro_sync_batch` drains the queue.

---

## 6. Security notes (please read before your demo)

These are real issues I found in the sketch. None of them block the sync, but a
judge may well ask:

1. **Hard-coded credentials in the sketch.**
   `ADMIN_PASS "admin123"`, `OTA_PASS "admin"`, and
   `UPDATER_PASS "Astro#5211"` are in plain text, in a file you have shared on
   GitHub. Change them, and move them into `astro_config.h` (gitignored).
   `astro.updater@gmail.com` + that password should be rotated immediately, since
   the repo is public.
2. **`c.setInsecure()`** disables TLS certificate checking, so the ESP32 will
   happily talk to anything pretending to be supabase.co. For a school network
   that is acceptable; for a competition, add the root CA and use
   `setCACert()`. Mention it — it shows you know the trade-off.
3. **`astro_factory_wipe` is intentionally non-destructive.** A terminal can
   never erase attendance history. It logs the attempt and returns `WIPE_REFUSED`.
   Deleting a student from the device **archives** them (`active = false`) and
   deactivates their card, so history and reports survive.
4. **The database secret is never in git.** `astro_config.h` is gitignored, and
   `main.cpp` only ever contains the empty-string default.

---

## 7. About Firebase

You do not need Firebase. Your firmware, your schema, and your dashboard are all
Supabase. The `README.md` and `docs/master_prompt.md` still say "Firebase" in
several places (the feature list, the tech list, and the live-demo link is a
`web.app` Firebase Hosting URL).

If you want me to, I can rewrite those sections so the documentation matches
what the project actually runs on — that mismatch is exactly the kind of thing
that trips you up in a viva. Say the word and I'll do it.
