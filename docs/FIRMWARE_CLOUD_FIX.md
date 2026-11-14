# Why the ESP32 never reached the cloud — and what was fixed

**Short version:** the sketch was never talking to Firebase. It talks to **Supabase**.
And even against Supabase it was failing, because PostgREST resolves an RPC by
matching your JSON keys to the function's **parameter names** one-for-one.
The functions in the database used `p_device_code`; the sketch sends `device_code`.
Every single call was rejected before it reached your logic.

That is the "different versions" you were seeing: two halves of the project that
agreed on the *names* of the functions but not on their *contracts*.

---

## 1. Firebase was never in the picture

```
$ grep -c "Firebase" firmware/esp32/main.cpp
0
```

97,712 lines, zero occurrences. There is no Firebase URL, no `Firebase_ESP_Client.h`,
no `FirebaseData`, no `Firebase.begin()`. The sketch only does:

```
POST https://nrjchonjlncamfyzmfye.supabase.co/rest/v1/rpc/astro_*
```

So there was never a Firebase↔ESP32 link to repair. If you were looking at the
Firebase console, it was empty because nothing has ever written to it.

`README.md` still advertises Firebase and links a Firebase Hosting demo. That is
out of date and will cost you marks in a viva — see the note at the end.

---

## 2. The five real defects

| # | Defect | Effect |
|---|--------|--------|
| 1 | `ASTRO_SUPABASE_KEY` was `"sb_publishable_astro_public_key"` — a placeholder, not a real key | 401 on every request |
| 2 | `rpcCall()` never sent the device secret | 401 `DEVICE_SECRET_REQUIRED` |
| 3 | `authenticate()` treated **HTTP 404 as success** | a completely broken cloud reported "online" |
| 4 | `cloudWorker()` retried `bootLoadInitialState()` every **10 ms** | request storm at Supabase while offline |
| 5 | RPC parameters were `p_device_code` while the sketch sends `device_code` | `PGRST202` function-not-found on all 23 calls |

Defect 3 is why this was invisible: Wi-Fi connected, the LCD said "cloud", Serial
showed no error, and the dashboard stayed empty.

---

## 3. What changed in the firmware

Only surgical edits were made. The file is still your sketch; `tools/patch_firmware.py`
performs them reproducibly and refuses to run twice.

| Location | Change |
|----------|--------|
| config block | real anon JWT key (a signed JWT, because PostgREST validates `Authorization: Bearer` as a JWT) |
| `rpcCall()` | added `X-Astro-Secret` header |
| `authenticate()` | **removed** the 404-succeeds fallback; failures now print the HTTP code |
| `cloudWorker()` | boot-load retry throttled to once every 15 s |
| boot banner | prints the key prefix, its length, and whether the secret is present |

---

## 4. What changed in Supabase

Applied as real migrations, all additive — **no existing function was dropped**
apart from the abandoned `p_`-named bridge that nothing called.

```
supabase/migrations/20261114000001_astro_firmware_bridge_v2.sql
supabase/migrations/20261114000002_bridge_hotfix.sql
```

* 23 firmware-facing functions whose parameter names match the sketch exactly
* `astro_fw_auth()` verifies every call against `devices.secret_hash`
* `astro_fw_id_map` keeps the sketch's uint32 ids stable for notices/messages/leaves
* `device_events.event_uid` got a `gen_random_uuid()` default

### Verified end-to-end against the live database

| Path | Result |
|------|--------|
| `astro_device_handshake` | `HANDSHAKE_OK`, school + timezone returned |
| `astro_get_settings` | start 08:00, late 08:20, tz Asia/Kolkata |
| `astro_list_students` | Demo Student / A1B2C3D4 / roll DEMO-01 |
| `astro_lookup_by_rfid` | correct student record |
| `astro_mark_attendance` 08:10 | `MARKED` → Present |
| `astro_mark_attendance` 09:10 | `MARKED` → **Late** (cut-off 08:20) |
| `astro_list_attendance` | reads back what was written |
| `astro_sync_batch` | `failed: 0`, notices/messages/logs accepted |
| bad secret | rejected with `BAD_DEVICE_SECRET` |

All test rows were removed afterwards.

---

## 5. What you must do

1. **Put `astro_config.h` next to `main.cpp`.** The file is already in
   `firmware/esp32/astro_config.h` and is git-ignored. Fill in your 2.4 GHz Wi-Fi.
2. **Flash `firmware/esp32/main.cpp`.**
3. Open Serial Monitor at **115200** and check the banner:

```
[BOOT] Supabase Key: eyJhbGciOiJIUzI1N... (len 219)
[BOOT] Device Secret: SET (len 48)
[SUPABASE] Device ASTRO-RNK-01 authenticated via astro_device_handshake @ nrjchonjlncamfyzmfye.supabase.co
```

4. Tap a card. The row must appear in the Supabase `attendance` table within a
   few seconds.

### If it still fails

| Serial message | Meaning |
|---|---|
| `DEVICE_SECRET_REQUIRED` | `astro_config.h` not found, or the secret macro is empty |
| `BAD_DEVICE_SECRET` | secret does not match `devices.secret_hash` — rotate it |
| `auth-backoff` | check the 2.4 GHz SSID |
| `PGRST202` | the migrations were not applied |

Rotate the secret any time with:

```sql
select public.astro_rotate_device_secret('ASTRO-RNK-01');
```

---

## 6. Still outstanding

* `README.md` describes Firebase; the code runs Supabase.
* The repo contains real passwords in the sketch (`ADMIN_PASS "admin123"`,
  `OTA_PASS "admin"`, `UPDATER_PASS "Astro#5211"`) and a Gmail address. If this
  repo is public, rotate that Gmail password and move the strings into
  `astro_config.h`.
* TLS uses `setInsecure()`, so the certificate is not validated. Fine for a
  school prototype; not fine for a real deployment.
