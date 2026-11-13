// ============================================================================
//  ASTRO SMART ATTENDANCE — device configuration
//  Team Sun Rises India  |  firmware 26.11.7 + 4 line patch
// ============================================================================
//
//  HOW TO USE
//    1. Copy this file next to main.cpp (same folder), keeping the name
//       astro_config.h — main.cpp already does:
//              #if __has_include("astro_config.h")
//              #include "astro_config.h"
//              #endif
//       so no edit to the includes is needed.
//    2. Fill in WIFI SSID/password and ASTRO_DEVICE_SECRET.
//    3. NEVER commit this file. It is already listed in .gitignore.
//
//  This file is read BEFORE the #ifndef fallbacks in main.cpp, so the values
//  here win and main.cpp's placeholder defaults are never used.
// ============================================================================
#pragma once

// ------------------------------------------------------------------ 1. Wi-Fi
// 2.4 GHz only. The ESP32 has no 5 GHz radio at all.
#define ASTRO_WIFI_SSID "YOUR_WIFI_NAME"
#define ASTRO_WIFI_PASS "YOUR_WIFI_PASSWORD"

// ---------------------------------------------------------- 2. Supabase host
// Only the host, no https:// and no trailing slash.
#define ASTRO_SUPABASE_HOST "nrjchonjlncamfyzmfye.supabase.co"

// ------------------------------------------------------------- 3. API key
// Supabase dashboard -> Project Settings -> API Keys -> "publishable" (or the
// legacy "anon" key). Both work with the astro_* RPC layer.
//
// IMPORTANT: main.cpp currently ships the string
//     "sb_publishable_astro_public_key"
// which is a PLACEHOLDER, not a real key. Sending it makes every request fail
// before it even reaches the database. Replace it below.
#define ASTRO_SUPABASE_KEY "PASTE_YOUR_PUBLISHABLE_KEY"

// ------------------------------------------------------- 4. Device identity
#define ASTRO_DEVICE_CODE "ASTRO-RNK-01"

// ------------------------------------------------------- 5. Device secret
// Issued by the database (see docs/FIREBASE_TO_SUPABASE_FIX.md, step 3):
//     select public.astro_rotate_device_secret('ASTRO-RNK-01');
// Paste the 48-character hex string returned.
//
// This is what proves the request comes from your terminal. Without it the
// server rejects every call with DEVICE_SECRET_MISSING.
#define ASTRO_DEVICE_SECRET "PASTE_THE_48_CHAR_HEX_SECRET"
