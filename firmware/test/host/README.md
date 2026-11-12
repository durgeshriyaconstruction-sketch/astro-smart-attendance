# Host-side firmware tests

These run the real firmware logic on a laptop — no ESP32 required.

* `driver.cpp` — 45 assertions covering the Supabase client: heartbeat parsing,
  a normal tap, duplicate replay, unknown card, error-body mapping
  (`28P01` → `BAD_DEVICE_SECRET`), offline queue + NVS persistence across a
  reboot, batch replay, failed-batch retention, lookup, 5xx queueing and
  `serverOk()`.
* `stubs/` — stand-ins for the ESP32 runtime (`String`, `WiFi`, `HTTPClient`,
  `Preferences`, `MFRC522`, `LiquidCrystal_I2C`, …), written to match the
  documented signatures of the real headers.
* **ArduinoJson is the real library** (v7, cloned at build time), so every
  `JsonDocument` / `operator|` / `as<>` usage is compiled against the same code
  the ESP32 build will use.

Run:

```bash
./firmware/test/host/run.sh
```

Expected tail:

```
45 passed, 0 failed
sketch OK
```

What this does **not** cover: the ESP32 toolchain itself (Wi-Fi/TLS behaviour on
silicon) and hardware. Flash the sketch and tap a card before a live demo.
