// ============================================================================
// astro_config.example.h
// ============================================================================
// Copy this file to "astro_config.h" in the same folder as main.cpp and fill in
// the blanks. astro_config.h is git-ignored so your Wi-Fi password and device
// secret never end up in the repository.
//
//   cp firmware/esp32/astro_config.example.h firmware/esp32/astro_config.h
//
// ============================================================================
#pragma once

// ----------------------------------------------------- Wi-Fi (2.4 GHz ONLY)
// The ESP32 has no 5 GHz radio. If your router publishes both, use the 2.4 GHz
// SSID - pointing it at the 5 GHz one is one of the most common reasons the
// board "connects to Wi-Fi" on your phone but never on the device.
#ifndef ASTRO_WIFI_SSID
#define ASTRO_WIFI_SSID "YOUR_WIFI_NAME"
#endif
#ifndef ASTRO_WIFI_PASS
#define ASTRO_WIFI_PASS "YOUR_WIFI_PASSWORD"
#endif

// --------------------------------------------------------- Supabase project
#ifndef ASTRO_SUPABASE_HOST
#define ASTRO_SUPABASE_HOST "nrjchonjlncamfyzmfye.supabase.co"
#endif

// Public client key. Either the legacy "anon" JWT (recommended: PostgREST
// expects a real JWT in Authorization: Bearer) or the newer
// sb_publishable_... key.
#ifndef ASTRO_SUPABASE_KEY
#define ASTRO_SUPABASE_KEY "PASTE_THE_ANON_KEY_HERE"
#endif

// ----------------------------------------------------------------- identity
#ifndef ASTRO_DEVICE_CODE
#define ASTRO_DEVICE_CODE "ASTRO-RNK-01"
#endif

// Shown only once when you rotate it:
//   select public.astro_rotate_device_secret('ASTRO-RNK-01');
//
// Every astro_* RPC call is authenticated with this value. Leave it empty and
// the device will get 403 DEVICE_SECRET_REQUIRED on every single call.
#ifndef ASTRO_DEVICE_SECRET
#define ASTRO_DEVICE_SECRET ""
#endif
