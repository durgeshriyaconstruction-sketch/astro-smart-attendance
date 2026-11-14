#!/usr/bin/env bash
# Host-side check of the firmware lines added by tools/patch_firmware_sync.py.
# It is NOT a build of the sketch (that needs the Arduino IDE and the ESP32
# core). It compiles the added lines against the real ArduinoJson 6 with
# stand-ins for Arduino's String / WiFi / Serial, then runs them against made-up
# cloud replies.     Usage: tools/fwcheck/run.sh [path/to/main.cpp]
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
main="${1:-$here/../../firmware/esp32/main.cpp}"
work="${TMPDIR:-/tmp}/astro-fwcheck"
mkdir -p "$work/inc"
if [ ! -f "$work/ArduinoJson-6.21.5/src/ArduinoJson.h" ]; then
  curl -fsSL -o "$work/aj.tar.gz" https://codeload.github.com/bblanchon/ArduinoJson/tar.gz/refs/tags/v6.21.5
  tar xzf "$work/aj.tar.gz" -C "$work"
fi
cp "$here/Arduino.h" "$work/inc/Arduino.h"
python3 "$here/make_harness.py" "$main" "$here/harness.template.cpp" "$work/harness.cpp"
g++ -std=gnu++17 -Wall -Wextra -Wno-unused-parameter -Wno-unused-function -Wno-unused-variable \
  -I"$work/inc" -I"$work/ArduinoJson-6.21.5/src" \
  -DARDUINOJSON_ENABLE_ARDUINO_STRING=1 -DARDUINOJSON_ENABLE_STD_STRING=0 -DARDUINOJSON_ENABLE_ARDUINO_STREAM=0 \
  -DARDUINOJSON_ENABLE_ARDUINO_PRINT=0 -DARDUINOJSON_ENABLE_PROGMEM=0 -DARDUINOJSON_ENABLE_STD_STREAM=0 \
  "$work/harness.cpp" -o "$work/harness"
"$work/harness"
