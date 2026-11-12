#!/usr/bin/env bash
# Host-side check for astro_cloud.h and the reference sketch.
# Compiles the firmware logic against the REAL ArduinoJson v7 on a normal PC,
# with small stand-ins for the ESP32 runtime (Wi-Fi, HTTPClient, NVS, String).
#
#   ./firmware/test/host/run.sh
#
# Needs: g++ (C++17), git. Set ARDUINOJSON_PATH to reuse a local checkout.
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
fw="$here/../../astro_attendance"
json="${ARDUINOJSON_PATH:-/tmp/ArduinoJson}"

if [ ! -d "$json/src" ]; then
  echo "cloning ArduinoJson v7 ..."
  git clone --depth 1 https://github.com/bblanchon/ArduinoJson.git "$json" >/dev/null 2>&1
fi

common=(-std=gnu++17 -Wall -Wextra -Wno-unused-parameter -Wno-deprecated-copy
        -I"$here/stubs" -I"$json/src" -I"$here/test_config" -I"$fw")

echo "== host tests: astro_cloud.h =="
g++ "${common[@]}" "$here/driver.cpp" "$here/stubs/runtime.cpp" -o /tmp/astro_fw_test
/tmp/astro_fw_test

echo
echo "== syntax check: astro_attendance.ino =="
g++ "${common[@]}" -x c++ -fsyntax-only "$fw/astro_attendance.ino"
echo "sketch OK"

echo
echo "== syntax check: astro_attendance.ino with the fingerprint sensor enabled =="
g++ "${common[@]}" -DASTRO_USE_FINGERPRINT=1 -x c++ -fsyntax-only "$fw/astro_attendance.ino"
echo "sketch OK (fingerprint path)"
