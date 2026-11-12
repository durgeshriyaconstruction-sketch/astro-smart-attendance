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

These are the pins the school's own board (the rev2 PCB that `main.cpp` runs on)
already uses, so flashing this sketch onto that hardware needs no rewiring:

| Signal | ESP32 pin | Module pin |
|---|---|---|
| RC522 SDA/SS | GPIO 5 | SDA |
| RC522 SCK | GPIO 18 | SCK |
| RC522 MOSI | GPIO 23 | MOSI |
| RC522 MISO | GPIO 19 | MISO |
| RC522 RST | GPIO 4 | RST |
| RC522 3V3 | 3V3 | 3.3V (**never 5 V**) |
| LCD SDA | GPIO 21 | SDA |
| LCD SCL | GPIO 22 | SCL |
| R307 TX → ESP32 RX2 | GPIO 16 | TX (yellow) |
| R307 RX ← ESP32 TX2 | GPIO 17 | RX (white) |
| Fingerprint power gate | GPIO 13 | the sensor's VCC switch (`ASTRO_FP_POWER_PIN`) |
| Buzzer | GPIO 15 | + |

Two traps worth knowing, both taken from the working `main.cpp`:

* **GPIO 27 is UART2 TX on the rev2 PCB** — the old table put RC522 `RST` there,
  which fights the fingerprint sensor. `RST` is GPIO 4; `27` belongs to the R307.
* Some 16×2 LCD modules answer at `0x3F` rather than `0x27`. If the screen stays
  blank, set `#define ASTRO_LCD_ADDR 0x3F` in `astro_config.h`.

Every pin above is an `#ifndef` default, so you can override any of them in
`astro_config.h` without touching the sketch — useful if you build a second
board. The enclosure in `cad/v3` was designed around this stack; only the pins
are firmware-side, so nothing in the model changes if you move them.

`loop()` never calls `delay()`: the buzzer pattern, the 1.8 s result display and
the 20 ms reader poll are all `millis()` gates, so a second card can be read
while the first result is still on screen and the heartbeat keeps ticking. The
only waits left are in `setup()` (USB serial settling, RC522 reset, the first
Wi-Fi connect).

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

## Remote commands from the dashboard

The Devices tab (and the *Scan a card* / *Enrol fingerprint* buttons when adding
a student) does not talk to the terminal directly: it writes a row into
`device_commands`. The sketch polls that queue every 3 s and reports back, so
the office can press a button and watch the answer appear:

| Kind | The terminal does | Payload it receives | Result it sends |
|---|---|---|---|
| `lcd_text` | shows the text for 5 s (the server already wrapped it to two 16-character lines) | `{line1, line2, hold_seconds}` | — |
| `rfid_capture` | buzzes, waits up to 30 s for a card, **does not mark attendance** | `{student_id?, name?}` | `{uid}` |
| `fp_check` | waits for a finger, reports which template matched | — | `{slot}` |
| `fp_enroll` | two touches, stores a template in the slot the server picked | `{slot, student_id?, name?}` | `{slot}` |
| `fp_delete` | deletes that template | `{slot}` | `{slot}` |
| `refresh` | redraws the idle screen | — | — |
| `reboot` | restarts (admin only) | — | — |

The terminal only reports `{uid}` / `{slot}`; the database decides who owns the
card, links the template to the student and stores the enriched answer. A lost
answer is harmless: re-sending the same result gets `ALREADY_RECORDED`, and a
command that expires first is reported by the dashboard as "no answer".

Things the server does that surprise people, all of them deliberate:

* queueing a command of the same kind cancels the previous one (status
  `cancelled`, reason `superseded`) — you cannot stack five LCD messages;
* `fp_enroll` refuses a slot that already belongs to someone else
  (`FINGERPRINT_SLOT_IN_USE`) and otherwise picks the lowest free one;
* a terminal that has not phoned home for 90 s still gets the command, but the
  response carries the warning the dashboard shows immediately;
* more than 10 queued commands → `TOO_MANY_QUEUED`.

Type `c` in the serial monitor to poll once by hand; the firmware prints
`[cmd] <kind> id=<uuid>` when it picks something up.

**Verified against the live project** (2026-11-12): a temporary bench device was
provisioned, an `lcd_text` and an `rfid_capture` queued as the demo admin, then
polled **as `anon`** (the same credentials a real terminal uses) and answered.
The capture came back `known: true, owner: Demo Student (DEMO-01)`, and
re-sending the same result returned `ALREADY_RECORDED`. The bench device was
deleted afterwards; `ASTRO-RNK-01` was never touched.

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
