# Terminal firmware — Supabase edition

```
firmware/astro_attendance/
├── astro_attendance.ino        complete reference sketch (RC522 + LCD + buzzer, R307 optional)
├── astro_cloud.h               Supabase client: heartbeat, tap, batch sync, offline queue
├── astro_certs.h               root CAs for *.supabase.co (public certs)
├── astro_config.example.h      copy -> astro_config.h, fill in Wi-Fi + device secret
```

`astro_config.h` is git-ignored. Keep it that way.

## Wiring used by the reference sketch

| Signal | ESP32 pin | Module pin |
|---|---|---|
| RC522 SDA/SS | GPIO 5 | SDA |
| RC522 SCK | GPIO 18 | SCK |
| RC522 MOSI | GPIO 23 | MOSI |
| RC522 MISO | GPIO 19 | MISO |
| RC522 RST | GPIO 27 | RST |
| RC522 3V3 | 3V3 | 3.3V (**never 5 V**) |
| LCD SDA | GPIO 21 | SDA |
| LCD SCL | GPIO 22 | SCL |
| R307 TX → ESP32 RX2 | GPIO 16 | TX (yellow) |
| R307 RX ← ESP32 TX2 | GPIO 17 | RX (white) |
| Buzzer | GPIO 25 | + |

The enclosure in `cad/v3` was designed around this stack; only the pins are
firmware-side, so nothing in the model changes if you move them.

## Flash it

1. Arduino IDE → Libraries: `ArduinoJson 7.x`, `MFRC522`, `LiquidCrystal_I2C`
   (+ `Adafruit Fingerprint Sensor Library` only if you enable the R307).
2. Copy `astro_config.example.h` → `astro_config.h`, fill in Wi-Fi, the
   publishable key, `ASTRO_DEVICE_CODE` and `ASTRO_DEVICE_SECRET`.
3. Open `astro_attendance.ino`, board **ESP32 Dev Module**, upload.
4. Serial monitor @ 115200. You should see:

```
=== Astro Smart Attendance ===
[rfid] RC522 self-test OK
[cloud] wifi=UP school=The Aditya Birla Public School, Renukoot late_after=08:20
```

5. Tap a card that exists in `rfid_cards`. Press `t` in the serial monitor to
   simulate a tap with the seeded bench card `A1B2C3D4`.

## Test the offline queue (the feature that wins marks)

1. Power up with Wi-Fi **off** (or unplug the router after boot).
2. Tap three different registered cards → LCD shows `SAVED OFFLINE`, the counter
   `Saved: 3` increases.
3. Power-cycle the ESP32 — the queue survives (stored in NVS).
4. Bring Wi-Fi back. Within 30 s the LCD counter returns to 0 and the three rows
   appear in Supabase with their **original tap times**.

Nothing is double-counted if the same queue is uploaded twice: every tap carries
an `event_uid` that the database de-duplicates.

## Host tests (no board needed)

```bash
./firmware/test/host/run.sh
```

Compiles `astro_cloud.h` + the sketch with `g++` against the real ArduinoJson v7
and runs 45 assertions (heartbeat, tap, duplicate, unknown card, error mapping,
offline queue across a reboot, batch replay, 5xx queueing, `serverOk()`).
See `firmware/test/host/README.md`. It covers the logic, not the silicon.

## Security

* Firmware carries the **publishable** key only (cannot read tables).
* Device secret is a 48-char hex string, stored server-side as sha256.
* Lost terminal? `select public.astro_rotate_device_secret('ASTRO-RNK-01');`
  and re-flash the new secret; the old one is dead immediately.
