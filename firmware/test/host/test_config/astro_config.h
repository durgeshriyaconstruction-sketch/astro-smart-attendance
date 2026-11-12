// Test-only copy of astro_config.h for the host test suite (firmware/test/host/run.sh).
// No real credentials: placeholder device secret, the publishable key is public by design.
// run.sh passes -I firmware/test/host/test_config so this file is picked up instead of
// your git-ignored firmware/astro_attendance/astro_config.h.

//  astro_config.example.h  —  copy to astro_config.h and fill in
//  (astro_config.h is git-ignored: it holds your Wi-Fi password and the device
//   secret, which must never be committed.)
//
//  PlatformIO:  lib_deps =
//                 bblanchon/ArduinoJson @ ^7.0.0
//                 miguelbalboa/MFRC522 @ ^1.4.10
//                 marcoschwartz/LiquidCrystal_I2C @ ^1.1.4
//                 adafruit/Adafruit Fingerprint Sensor Library @ ^2.1.2
//  Arduino IDE: install the same four libraries from Library Manager.
// ============================================================================
#pragma once

// ---------------------------------------------------------------- Wi-Fi -----
#define ASTRO_WIFI_SSID   "YOUR_WIFI_NAME"
#define ASTRO_WIFI_PASS   "YOUR_WIFI_PASSWORD"
// optional second network (school router / phone hotspot) — leave "" to disable
#define ASTRO_WIFI_SSID2  ""
#define ASTRO_WIFI_PASS2  ""

// ------------------------------------------------------------- Supabase -----
// Settings -> API -> Project URL host (no https://, no trailing slash)
#define ASTRO_SUPABASE_HOST "nrjchonjlncamfyzmfye.supabase.co"
// Settings -> API Keys -> publishable key (safe on a device: it can only call
// the astro_* RPCs, it cannot read a single table)
#define ASTRO_SUPABASE_KEY  "sb_publishable_TEST"   // the suite asserts on this literal

// --------------------------------------------------------------- device -----
// devices.device_code in the database
#define ASTRO_DEVICE_CODE   "ASTRO-RNK-01"
// the secret returned once by astro_provision_device() / astro_rotate_device_secret()
// (48 hex chars). It is NOT stored in the database in clear - if you lose it,
// rotate:  select public.astro_rotate_device_secret('ASTRO-RNK-01');
#define ASTRO_DEVICE_SECRET "PASTE_YOUR_DEVICE_SECRET_HERE"

// ------------------------------------------------------------ behaviour -----
#define ASTRO_FIRMWARE      "astro-1.0.0"
#define ASTRO_TIMEZONE_OFFSET_SEC 19800      // +05:30 IST
#define ASTRO_NTP_SERVER1   "pool.ntp.org"
#define ASTRO_NTP_SERVER2   "time.google.com"

// 1 = skip certificate validation (bench testing only, never ship like this)
#define ASTRO_TLS_INSECURE  0        // set 1 only for local debugging

#define ASTRO_QUEUE_MAX          50   // offline taps kept in NVS
#define ASTRO_HTTP_TIMEOUT_MS  6000
#define ASTRO_SYNC_EVERY_MS   30000   // retry the offline queue
#define ASTRO_PING_EVERY_MS  300000   // heartbeat / clock refresh (5 min)
