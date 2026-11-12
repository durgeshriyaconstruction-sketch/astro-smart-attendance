// ============================================================================
//  astro_cloud.h — Supabase link for the Astro Smart Attendance terminal
//
//  What it does
//    * joins Wi-Fi (with an optional backup network), syncs the clock from NTP
//    * calls the SECURITY DEFINER RPCs of the Supabase project
//        astro_heartbeat        -> school name, late cut-off, server time
//        astro_mark_attendance  -> one tap, idempotent by event_uid
//        astro_sync_batch       -> replays the offline queue
//        astro_lookup_card      -> "is this card registered?"
//    * keeps every tap that could not be sent in NVS and replays it later, so
//      attendance still works with the internet down
//
//  The terminal only holds the publishable key, which may EXECUTE those four
//  functions and nothing else. It cannot read or write a single table, so a
//  stolen terminal cannot dump the school's student list.
//
//  Requires: ArduinoJson >= 7.0, ESP32 Arduino core >= 2.0
// ============================================================================
#pragma once

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <esp_system.h>
#include <time.h>
#include <sys/time.h>
#include <math.h>
#include <string.h>
#include <vector>

#include "astro_config.h"
#include "astro_certs.h"

// --------------------------------------------------------------- results ---
struct AstroTapResult {
  bool   ok        = false;   // the server understood the request
  bool   marked    = false;   // a NEW attendance row was created
  bool   duplicate = false;   // tap was already recorded (safe replay)
  bool   offline   = false;   // stored on the device, will sync later
  int    httpCode  = 0;
  String code;                // MARKED / ALREADY_MARKED / UNKNOWN_CARD / OFFLINE / ...
  String message;             // human-readable reason on failure
  String name;                // student name
  String roll;                // roll number
  String className;           // "9-A"
  String status;              // present / late / absent / ...
  String timeText;            // HH:MM of the recorded tap
};

// ------------------------------------------------------- small helpers -----
static inline String astroNewUuid() {
  uint32_t a = esp_random(), b = esp_random(), c = esp_random(), d = esp_random();
  char buf[40];
  snprintf(buf, sizeof(buf), "%08x-%04x-%04x-%04x-%08x%04x",
           a, (unsigned)(b >> 16), (unsigned)(b & 0xFFFF),
           (unsigned)(c >> 16), (unsigned)(c & 0xFFFF), (unsigned)(d & 0xFFFF));
  return String(buf);
}

static inline String astroNowIso() {
  time_t t = time(nullptr);
  if (t < 1600000000) return String();          // clock not set: let the server stamp it
  struct tm tmv;
  gmtime_r(&t, &tmv);
  char buf[24];
  strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &tmv);
  return String(buf);
}

// ============================================================================
class AstroCloud {
 public:
  AstroCloud() {}

  // ---- lifecycle ---------------------------------------------------------
  bool begin(uint32_t wifiTimeoutMs = 15000) {
    _prefs.begin("astro_q", false);
    queueLoad();

    WiFi.persistent(false);
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    connectWifi(wifiTimeoutMs);

    // Local clock in IST (gmtime() stays UTC, which is what event_ts wants)
    configTime(ASTRO_TIMEZONE_OFFSET_SEC, 0, ASTRO_NTP_SERVER1, ASTRO_NTP_SERVER2);

    if (online()) heartbeat();
    return online();
  }

  bool online() { return WiFi.status() == WL_CONNECTED; }

  // ---- heartbeat ---------------------------------------------------------
  bool heartbeat() {
    if (!online()) return false;

    JsonDocument req;
    req["p_device_code"]   = ASTRO_DEVICE_CODE;
    req["p_device_secret"] = ASTRO_DEVICE_SECRET;
    req["p_firmware"]      = ASTRO_FIRMWARE;
    req["p_rssi"]          = WiFi.RSSI();
    req["p_ip"]            = WiFi.localIP().toString();

    JsonDocument res;
    int httpCode = 0;
    if (!postRpc("astro_heartbeat", req, res, httpCode)) return false;

    _school    = String((const char*)(res["school"] | ""));
    _lateAfter = String((const char*)(res["late_after"] | "08:20"));

    long long serverEpoch = res["server_epoch"].as<long long>();
    if (serverEpoch > 1600000000LL) {
      time_t local = time(nullptr);
      if (local < 1600000000 || fabs((double)local - (double)serverEpoch) > 120.0) {
        struct timeval tv;
        tv.tv_sec  = (time_t)serverEpoch;
        tv.tv_usec = 0;
        settimeofday(&tv, nullptr);
      }
    }
    return true;
  }

  // ---- one RFID tap ------------------------------------------------------
  AstroTapResult markRfid(const String& uid, const char* session = "daily", int periodNo = -1) {
    return submit(uid, -1, "rfid", session, periodNo);
  }

  // ---- one fingerprint tap ----------------------------------------------
  AstroTapResult markFingerprint(int fingerprintId, const char* session = "daily", int periodNo = -1) {
    return submit(String(), fingerprintId, "fingerprint", session, periodNo);
  }

  // ---- read-only card check (enrol / diagnostics screen) ----------------
  AstroTapResult lookupCard(const String& uid) {
    AstroTapResult r;
    if (!ensureWifi()) { r.code = "OFFLINE"; r.message = "No Wi-Fi"; return r; }

    JsonDocument req;
    req["p_device_code"]   = ASTRO_DEVICE_CODE;
    req["p_device_secret"] = ASTRO_DEVICE_SECRET;
    req["p_card_uid"]      = uid;

    JsonDocument res;
    if (!postRpc("astro_lookup_card", req, res, r.httpCode)) {
      r.code = "OFFLINE";
      r.message = "Network error";
      return r;
    }
    r.ok      = res["ok"] | false;
    r.code    = String((const char*)(res["code"] | "UNKNOWN"));
    r.message = String((const char*)(res["message"] | ""));

    JsonObject st = res["student"];
    if (!st.isNull()) {
      r.name      = String((const char*)(st["name"] | ""));
      r.roll      = String((const char*)(st["roll_no"] | ""));
      r.className = String((const char*)(st["class"] | ""));
    }
    return r;
  }

  // ---- offline queue -----------------------------------------------------
  int pendingEvents() { return (int)_queue.size(); }

  // Call from loop(): retries the queue and refreshes the clock.
  void loop() {
    uint32_t nowMs = millis();

    if (!online() && (nowMs - _lastWifiTry > 15000)) {
      _lastWifiTry = nowMs;
      connectWifi(0);                        // non-blocking retry
    }

    if (online() && !_queue.empty() && (nowMs - _lastSync > ASTRO_SYNC_EVERY_MS)) {
      _lastSync = nowMs;
      syncQueue();
    }

    if (online() && (nowMs - _lastPing > ASTRO_PING_EVERY_MS)) {
      _lastPing = nowMs;
      heartbeat();
    }
  }

  // Returns how many queued taps were sent this round (0 on failure).
  int syncQueue() {
    if (_queue.empty() || !ensureWifi()) return 0;

    int chunk = (int)_queue.size();
    if (chunk > 10) chunk = 10;

    // Built by hand: the queued entries are already JSON objects and this keeps
    // RAM use flat on a 50-entry queue.
    String payload = String("{\"p_device_code\":\"") + ASTRO_DEVICE_CODE +
                     "\",\"p_device_secret\":\"" + ASTRO_DEVICE_SECRET +
                     "\",\"p_events\":[";
    for (int i = 0; i < chunk; i++) {
      if (i) payload += ",";
      payload += _queue[i];
    }
    payload += "]}";

    JsonDocument res;
    int httpCode = 0;
    if (!postRaw("astro_sync_batch", payload, res, httpCode)) return 0;

    const char* code = res["code"] | "";
    if (strcmp(code, "BATCH_DONE") != 0) {
      Serial.printf("[cloud] batch rejected: %s %s\n", code,
                    (const char*)(res["message"] | ""));
      return 0;
    }

    // Everything in the chunk has now been seen by the server. Even rejected
    // events (unknown card, bad session) will never pass on retry, so dropping
    // them keeps the queue from blocking forever.
    _queue.erase(_queue.begin(), _queue.begin() + chunk);
    queueSave();
    return chunk;
  }

  // Diagnostics for the LCD / serial monitor
  String schoolName() { return _school; }
  String lateAfter()  { return _lateAfter; }

 private:
  Preferences         _prefs;
  std::vector<String> _queue;
  String   _school;
  String   _lateAfter;
  uint32_t _lastWifiTry = 0;
  uint32_t _lastSync    = 0;
  uint32_t _lastPing    = 0;

  // ------------------------------------------------------------ network ---
  bool connectWifi(uint32_t timeoutMs) {
    if (online()) return true;
    if (strlen(ASTRO_WIFI_SSID) == 0) return false;

    WiFi.begin(ASTRO_WIFI_SSID, ASTRO_WIFI_PASS);
    uint32_t start = millis();
    bool triedBackup = false;

    while (WiFi.status() != WL_CONNECTED) {
      delay(200);
      if (timeoutMs == 0) break;                        // non-blocking retry
      if (millis() - start > timeoutMs) break;

      // switch to the backup network once, halfway through the wait
      if (!triedBackup && strlen(ASTRO_WIFI_SSID2) > 0 &&
          millis() - start > timeoutMs / 2) {
        triedBackup = true;
        WiFi.disconnect(false, false);
        WiFi.begin(ASTRO_WIFI_SSID2, ASTRO_WIFI_PASS2);
      }
    }
    return online();
  }

  bool ensureWifi() {
    if (online()) return true;
    if (millis() - _lastWifiTry < 3000) return false;   // never block the LCD twice in a row
    _lastWifiTry = millis();
    return connectWifi(4000);                            // one quick attempt
  }

  bool postRpc(const char* fn, JsonDocument& req, JsonDocument& res, int& httpCode) {
    String payload;
    serializeJson(req, payload);
    return postRaw(fn, payload, res, httpCode);
  }

  bool postRaw(const char* fn, const String& payload, JsonDocument& res, int& httpCode) {
    httpCode = 0;
    String url = String("https://") + ASTRO_SUPABASE_HOST + "/rest/v1/rpc/" + fn;

    WiFiClientSecure client;
#if ASTRO_TLS_INSECURE
    client.setInsecure();
#else
    client.setCACert(ASTRO_CA_BUNDLE);
#endif
    client.setTimeout(8);

    HTTPClient http;
    http.setConnectTimeout(ASTRO_HTTP_TIMEOUT_MS);
    http.setTimeout(ASTRO_HTTP_TIMEOUT_MS);
    if (!http.begin(client, url)) return false;

    http.addHeader("Content-Type", "application/json");
    http.addHeader("apikey", ASTRO_SUPABASE_KEY);
    http.addHeader("Authorization", String("Bearer ") + ASTRO_SUPABASE_KEY);

    httpCode = http.POST(payload);
    bool transportOk = (httpCode > 0);

    if (transportOk) {
      String body = http.getString();
      if (body.length()) {
        if (deserializeJson(res, body) != DeserializationError::Ok) {
          res.clear();
          res["message"] = body.substring(0, 120);
        }
      }
    }
    http.end();

    if (!transportOk) {
      Serial.printf("[cloud] %s transport failure: %d\n", fn, httpCode);
      return false;
    }

    if (httpCode >= 400) {
      res["ok"] = false;
      const char* c = res["code"] | "";
      if (c[0] == '\0') res["code"] = "HTTP_ERROR";
      const char* m = res["message"] | "";
      if (m[0] == '\0') res["message"] = String("HTTP ") + httpCode;
      Serial.printf("[cloud] %s -> %d %s\n", fn, httpCode, (const char*)(res["message"] | ""));
      return true;                     // the server answered, just not with 2xx
    }
    return true;
  }

  // ---------------------------------------------------------- one tap ----
  AstroTapResult submit(const String& uid, int fingerprintId, const char* method,
                        const char* session, int periodNo) {
    AstroTapResult r;
    String eventUid = astroNewUuid();
    String eventTs  = astroNowIso();

    if (!ensureWifi()) {
      queueAdd(uid, fingerprintId, method, session, periodNo, eventUid, eventTs);
      r.offline = true;
      r.code    = "OFFLINE";
      r.message = "No internet - saved on device";
      return r;
    }

    JsonDocument req;
    req["p_device_code"]   = ASTRO_DEVICE_CODE;
    req["p_device_secret"] = ASTRO_DEVICE_SECRET;
    if (uid.length())       req["p_card_uid"]       = uid;
    if (fingerprintId >= 0) req["p_fingerprint_id"] = fingerprintId;
    req["p_method"]  = method;
    req["p_session"] = session;
    if (periodNo > 0)       req["p_period_no"]      = periodNo;
    req["p_event_uid"] = eventUid;
    if (eventTs.length())   req["p_event_ts"]       = eventTs;

    JsonDocument res;
    if (!postRpc("astro_mark_attendance", req, res, r.httpCode)) {
      // the network died mid-request: keep the tap, replay later (idempotent)
      queueAdd(uid, fingerprintId, method, session, periodNo, eventUid, eventTs);
      r.offline = true;
      r.code    = "OFFLINE";
      r.message = "Network error - saved on device";
      return r;
    }

    parseMark(res, r);

    if (r.code == "DEVICE_NOT_FOUND" || r.code == "BAD_DEVICE_SECRET" ||
        r.code == "DEVICE_DISABLED") {
      Serial.println("[cloud] credentials rejected - check ASTRO_DEVICE_SECRET");
    }
    return r;
  }

  void parseMark(JsonDocument& res, AstroTapResult& r) {
    r.ok        = res["ok"] | false;
    r.code      = String((const char*)(res["code"] | "UNKNOWN"));
    r.message   = String((const char*)(res["message"] | ""));
    r.marked    = (r.code == "MARKED");
    r.duplicate = (r.code == "ALREADY_MARKED") || (res["duplicate"] | false);
    r.status    = String((const char*)(res["status"] | ""));
    r.timeText  = String((const char*)(res["time"] | ""));

    JsonObject st = res["student"];
    if (!st.isNull()) {
      r.name      = String((const char*)(st["name"] | ""));
      r.roll      = String((const char*)(st["roll_no"] | ""));
      r.className = String((const char*)(st["class"] | ""));
    }
  }

  // -------------------------------------------------------- NVS queue ----
  void queueAdd(const String& uid, int fingerprintId, const char* method,
                const char* session, int periodNo, const String& eventUid,
                const String& eventTs) {
    JsonDocument e;
    if (uid.length())       e["card_uid"]       = uid;
    if (fingerprintId >= 0) e["fingerprint_id"]  = fingerprintId;
    e["method"]  = method;
    e["session"] = session;
    if (periodNo > 0)       e["period_no"]      = periodNo;
    e["event_uid"] = eventUid;
    if (eventTs.length())   e["event_ts"]       = eventTs;

    String s;
    serializeJson(e, s);

    if ((int)_queue.size() >= ASTRO_QUEUE_MAX) _queue.erase(_queue.begin());
    _queue.push_back(s);
    queueSave();
  }

  void queueLoad() {
    _queue.clear();
    int n = _prefs.getInt("n", 0);
    for (int i = 0; i < n && i < ASTRO_QUEUE_MAX; i++) {
      char key[8];
      snprintf(key, sizeof(key), "e%d", i);
      String v = _prefs.getString(key, "");
      if (v.length()) _queue.push_back(v);
    }
  }

  void queueSave() {
    int n = (int)_queue.size();
    for (int i = 0; i < n; i++) {
      char key[8];
      snprintf(key, sizeof(key), "e%d", i);
      _prefs.putString(key, _queue[i]);
    }
    for (int i = n; i < ASTRO_QUEUE_MAX; i++) {
      char key[8];
      snprintf(key, sizeof(key), "e%d", i);
      if (_prefs.isKey(key)) _prefs.remove(key);
    }
    _prefs.putInt("n", n);
  }
};
