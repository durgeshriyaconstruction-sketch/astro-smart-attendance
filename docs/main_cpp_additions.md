# What to add to `main.cpp` — Supabase connection

Everything below is designed to be pasted into your existing `main.cpp` in six
small edits. If you would rather start from a known-good file, flash
`firmware/astro_attendance/astro_attendance.ino` — it is the same logic, complete.

**Time needed: ~10 minutes. No changes to your wiring required.**

---

## 1. Copy three files next to `main.cpp`

| File | From | What it is |
|---|---|---|
| `astro_cloud.h` | `firmware/astro_attendance/astro_cloud.h` | the Supabase client (Wi-Fi, HTTPS, offline queue) |
| `astro_certs.h` | `firmware/astro_attendance/astro_certs.h` | the root CAs for `*.supabase.co` (public certs, not secrets) |
| `astro_config.h` | copy `firmware/astro_attendance/astro_config.example.h` and rename | your Wi-Fi + device credentials |

`astro_config.h` must **not** be committed — it holds your Wi-Fi password and the
device secret. `.gitignore` already excludes it.

Fill these five lines in `astro_config.h`:

```cpp
#define ASTRO_WIFI_SSID     "YourSchoolWiFi"
#define ASTRO_WIFI_PASS     "your-wifi-password"
#define ASTRO_SUPABASE_HOST "nrjchonjlncamfyzmfye.supabase.co"
#define ASTRO_SUPABASE_KEY  "sb_publishable_9a4vSwLdVz4Yd8wrWcTvXA_aIMmC6H_"
#define ASTRO_DEVICE_CODE   "ASTRO-RNK-01"
#define ASTRO_DEVICE_SECRET "the 48-character secret given to you when the device was provisioned"
```

## 2. Install the libraries

Arduino IDE → **Sketch ▸ Include Library ▸ Manage Libraries**:

* `ArduinoJson` (Benoit Blanchon) — version **7.x**
* `MFRC522` (GithubCommunity) — you already have this
* `LiquidCrystal_I2C` (Frank de Brabander / Marco Schwartz) — you already have this

PlatformIO `platformio.ini`:

```ini
lib_deps =
    bblanchon/ArduinoJson@^7.0.0
    miguelbalboa/MFRC522@^1.4.10
    marcoschwartz/LiquidCrystal_I2C@^1.1.4
```

## 3. Add the includes (top of `main.cpp`)

```cpp
#include "astro_cloud.h"     // pulls in astro_config.h + astro_certs.h
```

## 4. Add the global object (next to your `MFRC522` / `LiquidCrystal_I2C` objects)

```cpp
AstroCloud cloud;
```

## 5. Add three lines in `setup()`

Put them **after** the LCD, RC522 and Serial are initialised, and before the
"ready" screen:

```cpp
  lcd.clear();
  lcd.setCursor(0, 0); lcd.print("Connecting...");

  bool cloudUp = cloud.begin(20000);          // joins Wi-Fi + heartbeat (20 s max)

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(cloudUp ? "Wi-Fi OK" : "OFFLINE MODE");
  lcd.setCursor(0, 1);
  if (cloudUp) lcd.print(cloud.schoolName().substring(0, 16));
  else         lcd.print("syncs when online");
  delay(1500);
```

`cloud.begin()` never blocks forever: with no Wi-Fi the terminal simply runs in
offline mode and every tap is stored in flash.

## 6. Add one line in `loop()`

```cpp
void loop() {
  cloud.loop();      // retries the offline queue + refreshes the clock
  ...
}
```

## 7. Replace your "card read" block with the cloud call

Wherever you currently do `Serial.print(uid)` / display the UID, call the
handler instead. Typical existing code:

```cpp
if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
  String uid = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    uid += String(rfid.uid.uidByte[i] < 0x10 ? "0" : "");
    uid += String(rfid.uid.uidByte[i], HEX);
  }
  uid.toUpperCase();
  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
  // ... your old LCD / relay / serial code ...
}
```

becomes:

```cpp
if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
  String uid = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    uid += String(rfid.uid.uidByte[i] < 0x10 ? "0" : "");
    uid += String(rfid.uid.uidByte[i], HEX);
  }
  uid.toUpperCase();
  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();

  lcd.setCursor(0, 0); lcd.print("Checking...      ");
  lcd.setCursor(0, 1); lcd.print(uid + "          ");

  AstroTapResult r = cloud.markRfid(uid);   // <-- the only new line that matters
  showTapResult(r);                         // <-- paste the helper below
}
```

## 8. Paste these two helper functions (anywhere above `setup()`)

```cpp
// ---------------------------------------------------------------- display ---
void lcdWrap(uint8_t row, const String& text) {
  lcd.setCursor(0, row);
  String t = text;
  while (t.length() < 16) t += ' ';
  lcd.print(t.substring(0, 16));
}

void showTapResult(const AstroTapResult& r) {
  if (r.offline) {
    lcdWrap(0, "SAVED OFFLINE");
    lcdWrap(1, "Syncs when online");
  } else if (r.marked || r.duplicate) {           // present or late
    lcdWrap(0, r.name);
    String line2 = r.status + " " + r.timeText;
    if (r.duplicate) line2 += " DUP";
    lcdWrap(1, line2);
  } else if (r.code == "UNKNOWN_CARD") {
    lcdWrap(0, "CARD NOT");
    lcdWrap(1, "REGISTERED");
  } else {
    lcdWrap(0, "CLOUD ERROR");
    lcdWrap(1, r.code);
  }
  delay(1800);
  lcdWrap(0, "Tap your card");
  lcdWrap(1, "Astro Attendance");
}
```

**LCD meanings**

| Screen | Meaning |
|---|---|
| `ARIJIT DAS` / `present 08:07` | new attendance row written |
| `... DUP` | this card was already marked today — nothing was double-counted |
| `CARD NOT / REGISTERED` | UID is not in the school's `rfid_cards` table |
| `SAVED OFFLINE` | no internet (or server 5xx); tap is in flash and will upload itself |
| `CLOUD ERROR / BAD_DEVICE_SECRET` | the terminal's secret no longer matches the database |
| `CLOUD ERROR / DEVICE_DISABLED` | the device was switched off in the dashboard |
| `SERVER DOWN` on the idle screen | Wi-Fi works but the database did not answer the last heartbeat |

The client promotes PostgREST's `message` field to the code, because the raw
SQLSTATE (`28P01`, `22023`) is unreadable on a 16×2 display.

Server-side 5xx responses (project restarting, paused, gateway hiccup) are
**queued**, not lost — they replay like an offline tap. Only 4xx responses are
final, because those never succeed on retry.

## 9. Fingerprint (R307) — optional, same pattern

```cpp
if (finger.fingerFastSearch() == FINGERPRINT_OK) {
  AstroTapResult r = cloud.markFingerprint(finger.fingerID);   // template slot 0..999
  showTapResult(r);
}
```

`students.fingerprint_id` in the database is the R307 template slot, so enrol the
finger in the module exactly as before and store the same slot number in the row.

## 10. Period attendance (optional)

```cpp
// period 3 of the timetable
AstroTapResult r = cloud.markRfid(uid, "period", 3);
```

`session = "period"` + `period_no` writes a separate row per period; the default
`"daily"` keeps the first-tap-of-the-day behaviour.

## 11. Serial test commands

With the sketch/flash above, the serial monitor (115200) accepts:

| Key | Action |
|---|---|
| `i` | show online state, queue length, school, IP |
| `s` | force a sync of the offline queue |
| `h` | heartbeat (also re-syncs the clock) |
| `t` | bench-test tap using the seeded demo card `A1B2C3D4` |

## 12. Check it before you flash

```bash
./firmware/test/host/run.sh
```

That compiles `astro_cloud.h` and the sketch with `g++` against the **real
ArduinoJson v7** (cloned by the script) and runs 45 assertions covering
heartbeat, taps, duplicates, unknown cards, offline queue + reboot, batch
replay, 5xx queueing and error mapping. Expected: `45 passed, 0 failed` and
`sketch OK`. It does not replace flashing on the real board.

## 13. Compile and flash

1. Select **ESP32 Dev Module**.
2. Verify — the only warnings you should see are from the MFRC522 library.
3. Flash, open the serial monitor, tap a registered card.
4. Row appears in Supabase → `attendance` table (and the dashboard view
   `v_attendance_feed`).

---

## Troubleshooting

| `r.code` / symptom | Cause | Fix |
|---|---|---|
| `HTTP 401` / `401` | wrong publishable key | re-copy `sb_publishable_...` from Settings ▸ API Keys |
| `BAD_DEVICE_SECRET` | `ASTRO_DEVICE_SECRET` ≠ hashed secret | rotate: `select public.astro_rotate_device_secret('ASTRO-RNK-01');` and put the new value in `astro_config.h` |
| `DEVICE_NOT_FOUND` | `ASTRO_DEVICE_CODE` typo, or device row deleted | check `select * from devices;` |
| `DEVICE_DISABLED` | `devices.active = false` | `update devices set active = true where device_code='ASTRO-RNK-01';` |
| `UNKNOWN_CARD` | card not registered | insert into `rfid_cards` (see `docs/supabase_setup.md`) |
| `HTTP 404` | function name typo / migration not applied | check the four `astro_*` functions exist |
| `HTTP 400 EVENTS_MUST_BE_ARRAY` | queue payload corrupted in NVS | erase flash (`esptool.py erase_flash`) |
| hangs ~10 s then `OFFLINE` | Wi-Fi reachable but no internet, or TLS root mismatch | set `ASTRO_TLS_INSECURE 1` for a bench test to confirm it is TLS |
| `-1` in `r.httpCode` | DNS/TCP failure | check `WiFi.localIP()` and that the school firewall allows 443 |
| idle screen says `SERVER DOWN` but Wi-Fi is fine | no route to `*.supabase.co`, project paused, or wrong `ASTRO_SUPABASE_HOST` | open the project URL in a browser on the same network |
| compile error: `astro_config.h is missing` | the config file was not copied next to the sketch | copy `astro_config.example.h` → `astro_config.h` |

## Security rules (please keep them)

1. The terminal carries the **publishable** key only. Never paste the
   `service_role` / `sb_secret_...` key into firmware — anyone with a USB cable
   could read it and own the whole database.
2. The publishable key cannot read a table: `anon` has zero table privileges, it
   may only `EXECUTE` the four `astro_*` functions.
3. The device secret is hashed in the database (`sha256`). If a terminal is lost,
   rotate that device's secret — the old one stops working instantly.
4. `astro_config.h` stays out of Git.
