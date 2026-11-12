// ============================================================================
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
#define ASTRO_SUPABASE_KEY  "sb_publishable_9a4vSwLdVz4Yd8wrWcTvXA_aIMmC6H_"

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

// ---------------------------------------------------------------- pins -----
// Optional. The sketch defaults to the school's rev2 PCB, so you normally
// leave these commented out. Uncomment to move a signal on a different board.
//
// #define PIN_RC522_SS      5
// #define PIN_RC522_RST     4     // NOT 27: 27 is UART2 TX on the rev2 PCB
// #define PIN_I2C_SDA       21
// #define PIN_I2C_SCL       22
// #define PIN_BUZZER        15
// #define PIN_FINGER_RX     16    // ESP32 RX2 <- R307 TX
// #define PIN_FINGER_TX     17    // ESP32 TX2 -> R307 RX
// #define ASTRO_FP_POWER_PIN 13   // rev2: GPIO that switches the sensor's supply
// #define ASTRO_LCD_ADDR    0x27  // use 0x3F if the 16x2 screen stays blank
