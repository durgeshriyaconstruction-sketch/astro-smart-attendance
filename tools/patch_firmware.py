#!/usr/bin/env python3
"""
Reproducible patcher for firmware/esp32/main.cpp (Astro Smart Attendance v26.11.7).

Every replacement below is asserted to match EXACTLY ONCE, so running this twice is
harmless (it will refuse rather than corrupt the file) and any upstream drift fails loudly.

Usage:
    python3 tools/patch_firmware.py firmware/esp32/main.cpp

What it fixes (the 5 reasons the ESP32 looked "connected" but never reached Supabase):
  1. ASTRO_SUPABASE_KEY was the placeholder "sb_publishable_astro_public_key" -> every
     request answered 401 Invalid API key.
  2. rpcCall() never sent X-Astro-Secret -> astro_* bridge functions answer 401
     DEVICE_SECRET_REQUIRED.
  3. authenticate() treated HTTP 404 as SUCCESS -> a totally broken cloud looked online.
  4. cloudWorker() retried bootLoadInitialState() every 10 ms -> request storm when offline.
  5. Boot banner printed no credential diagnostics, so the failure was invisible.
"""

import sys

ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5yamNob25qbG5jYW1meXptZnllIiwicm9sZSI6ImFub24i"
    "LCJpYXQiOjE3OTQ0NzUwNDUsImV4cCI6MjExMDA1MTA0NX0."
    "MtiRrja_PYMWauT-ORzcOcdKHRAIXh3HtjyKeE5AoVM"
)

CRLF = "\r\n"

REPLACEMENTS = [
    # ---------------------------------------------------------------- 1. API key
    (
        "PLACEHOLDER API KEY -> real project key",
        '#define ASTRO_SUPABASE_KEY "sb_publishable_astro_public_key"',
        '#define ASTRO_SUPABASE_KEY "' + ANON_KEY + '"',
    ),
    # ------------------------------------------------- 1b. document the secret macro
    (
        "DOCUMENT ASTRO_DEVICE_SECRET",
        '#ifndef ASTRO_DEVICE_SECRET' + CRLF + '#define ASTRO_DEVICE_SECRET ""' + CRLF + '#endif',
        '#ifndef ASTRO_DEVICE_SECRET' + CRLF
        + '// REQUIRED. Must match devices.secret_hash on Supabase for ASTRO_DEVICE_CODE.' + CRLF
        + '// Keep the real value in astro_config.h (git-ignored), never in this file.' + CRLF
        + '#define ASTRO_DEVICE_SECRET ""' + CRLF
        + '#endif',
    ),
    # --------------------------------------------------- 2. send the device secret
    (
        "SEND X-Astro-Secret HEADER",
        '    h.addHeader("X-Astro-Device", String(ASTRO_DEVICE_CODE));' + CRLF
        + '    code = h.POST(',
        '    h.addHeader("X-Astro-Device", String(ASTRO_DEVICE_CODE));' + CRLF
        + '    // REQUIRED: every astro_* bridge function authenticates each call with this' + CRLF
        + '    // header. Without it Supabase answers 401 DEVICE_SECRET_REQUIRED and nothing' + CRLF
        + '    // is ever written to the database.' + CRLF
        + '    if (strlen(ASTRO_DEVICE_SECRET) > 0) h.addHeader("X-Astro-Secret", String(ASTRO_DEVICE_SECRET));' + CRLF
        + '    code = h.POST(',
    ),
    # ------------------------------------------- 3. remove the 404 == success lie
    (
        "NO 404 FALLBACK IN authenticate()",
        '  // If astro_device_handshake returns 404 (when publishable key calls stateless astro_* RPCs directly), use publishable key session' + CRLF
        + '  if (code == 404) {' + CRLF
        + '    token = String(ASTRO_SUPABASE_KEY);' + CRLF
        + '    tokenUntil = millis() + 3600000UL;' + CRLF
        + '    authFails = 0;' + CRLF
        + '    lastError = "";' + CRLF
        + '    return true;' + CRLF
        + '  }' + CRLF
        + '  authFails++;',
        '  // NO 404 FALLBACK. A 404 here means astro_device_handshake is missing from the' + CRLF
        + '  // database or ASTRO_DEVICE_SECRET is wrong. Faking success used to leave the' + CRLF
        + '  // device reporting "online" while every single write was silently dropped.' + CRLF
        + '  token = "";' + CRLF
        + '  tokenUntil = 0;' + CRLF
        + '  Serial.println("[SUPABASE] Handshake FAILED (HTTP " + String(code) + ") :: " + lastError);' + CRLF
        + '  if (strlen(ASTRO_DEVICE_SECRET) == 0)' + CRLF
        + '    Serial.println("[SUPABASE] ASTRO_DEVICE_SECRET is empty - put it in astro_config.h");' + CRLF
        + '  authFails++;',
    ),
    # ------------------------------------------------- 3b. accurate success message
    (
        "LOG REAL DEVICE CODE",
        'Serial.println("[SUPABASE] Device ASTRO-RNK-01 authenticated via astro_device_handshake");',
        'Serial.println("[SUPABASE] Device " + String(ASTRO_DEVICE_CODE) + " authenticated via astro_device_handshake @ " + String(ASTRO_SUPABASE_HOST));',
    ),
    # --------------------------------- 4. stop the 10 ms boot-load retry storm
    (
        "THROTTLE bootLoadInitialState RETRY",
        '    if (!gInitialBootLoadDone && Network::connected && !Hardware::interactiveBusy() && !gOtaLock) {' + CRLF
        + '      CoreLock lock;' + CRLF
        + '      if (Cloud::bootLoadInitialState()) {' + CRLF
        + '        gInitialBootLoadDone = true;' + CRLF
        + '      }' + CRLF
        + '    }',
        '    static uint32_t nextInitialTry = 0;' + CRLF
        + '    if (!gInitialBootLoadDone && Network::connected && !Hardware::interactiveBusy() && !gOtaLock &&' + CRLF
        + '        (int32_t)(millis() - nextInitialTry) >= 0) {' + CRLF
        + '      // Retry at most every 15 s. This used to fire on every 10 ms tick, which' + CRLF
        + '      // hammered Supabase with hundreds of handshakes per second while offline.' + CRLF
        + '      nextInitialTry = millis() + 15000UL;' + CRLF
        + '      CoreLock lock;' + CRLF
        + '      if (Cloud::bootLoadInitialState()) {' + CRLF
        + '        gInitialBootLoadDone = true;' + CRLF
        + '      }' + CRLF
        + '    }',
    ),
    # ------------------------------------------- 5. print the credential diagnostics
    (
        "BOOT CREDENTIAL DIAGNOSTICS",
        '  Serial.println("[BOOT] Supabase RPC Host: " + String(ASTRO_SUPABASE_HOST) + " | RPC Reachable: " + String(gInitialBootLoadDone ? "YES (settings/counts/holidays loaded)" : "PENDING_WIFI (IST defaults 09:00 / 09:30 active)"));',
        '  Serial.println("[BOOT] Supabase RPC Host: " + String(ASTRO_SUPABASE_HOST) + " | RPC Reachable: " + String(gInitialBootLoadDone ? "YES (settings/counts/holidays loaded)" : "PENDING_WIFI (IST defaults 09:00 / 09:30 active)"));' + CRLF
        + '  Serial.println("[BOOT] Supabase Key: " + String(ASTRO_SUPABASE_KEY).substring(0, 18) + "... (len " + String(strlen(ASTRO_SUPABASE_KEY)) + ")");' + CRLF
        + '  Serial.println("[BOOT] Device Secret: " + String(strlen(ASTRO_DEVICE_SECRET) > 0 ? "SET (len " + String(strlen(ASTRO_DEVICE_SECRET)) + ")" : String("MISSING -> cloud writes will 401. Add astro_config.h")));',
    ),
]


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    with open(path, "r", encoding="utf-8", newline="") as fh:
        src = fh.read()

    failures = 0
    for name, old, new in REPLACEMENTS:
        count = src.count(old)
        if count == 0 and src.count(new) == 1:
            print(f"[skip] {name}: already applied")
            continue
        if count != 1:
            print(f"[FAIL] {name}: expected exactly 1 match, found {count}")
            failures += 1
            continue
        src = src.replace(old, new, 1)
        print(f"[ok]   {name}")

    if failures:
        print(f"\n{failures} patch(es) failed - file NOT written.")
        return 1

    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(src)
    print("\nAll patches applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
