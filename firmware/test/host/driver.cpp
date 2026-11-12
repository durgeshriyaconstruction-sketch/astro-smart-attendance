#include "astro_cloud.h"
#include <cstdio>
#include <cstring>

static int g_fail = 0, g_pass = 0;
#define CHECK(cond, msg) do { if (cond) { g_pass++; } else { g_fail++; \
  std::printf("  FAIL: %s  (line %d)\n", msg, __LINE__); } } while (0)

// Responses captured from the live project on 2026-11-12.
static const char* HEARTBEAT_JSON =
  R"({"ok":true,"code":"HELLO","school":"The Aditya Birla Public School, Renukoot","school_code":"ABPS-RNK","timezone":"Asia/Kolkata","late_after":"08:20","day_start":"08:00","day_end":"14:00","server_time":"2026-11-12T15:47:36","server_epoch":1794478657,"local_time":"15:47:36","local_date":"2026-11-12"})";

static const char* MARKED_JSON =
  R"({"ok":true,"code":"MARKED","action":"marked","uid":"A1B2C3D4","status":"late","date":"2026-11-12","time":"08:42","action":"marked","method":"rfid","session":"daily","period_no":null,"marked_at":"2026-11-12T03:12:00+00:00","student":{"id":"95cb2529","roll_no":"DEMO-01","name":"Demo Student","class":"9-A"}})";

static const char* ALREADY_JSON =
  R"({"ok":true,"code":"ALREADY_MARKED","action":"already_marked","uid":"A1B2C3D4","status":"present","date":"2026-11-12","time":"08:05","marked_at":"2026-11-12T02:35:00+00:00","student":{"id":"95cb2529","roll_no":"DEMO-01","name":"Demo Student","class":"9-A"}})";

static const char* UNKNOWN_JSON =
  R"({"ok":false,"code":"UNKNOWN_CARD","uid":"DEADBEEF","fingerprint_id":null,"message":"Card not registered for this school"})";

static const char* BATCH_JSON =
  R"({"ok":true,"code":"BATCH_DONE","accepted":1,"marked":1,"duplicates":0,"unknown":0,"failed":0,"results":[]})";

int main() {
  std::printf("== astro_cloud.h host test ==\n");

  // ---- 1. boot + heartbeat ------------------------------------------------
  HttpStub::nextCode = 200;
  HttpStub::nextBody = HEARTBEAT_JSON;
  AstroCloud cloud;
  bool up = cloud.begin(5000);
  CHECK(up, "begin() reports Wi-Fi up");
  CHECK(cloud.online(), "online() true");
  CHECK(cloud.schoolName() == "The Aditya Birla Public School, Renukoot", "school name parsed");
  CHECK(cloud.lateAfter() == "08:20", "late_after parsed");
  CHECK(HttpStub::lastUrl == String("https://nrjchonjlncamfyzmfye.supabase.co/rest/v1/rpc/astro_heartbeat"),
        "heartbeat URL correct");

  // ---- 2. a normal tap ----------------------------------------------------
  HttpStub::nextBody = MARKED_JSON;
  HttpStub::lastHeaders = "";
  AstroTapResult r = cloud.markRfid("A1B2C3D4");
  CHECK(r.ok && r.marked && !r.duplicate && !r.offline, "tap -> marked");
  CHECK(r.code == "MARKED", "code MARKED");
  CHECK(r.name == "Demo Student", "student name parsed");
  CHECK(r.roll == "DEMO-01", "roll parsed");
  CHECK(r.className == "9-A", "class parsed");
  CHECK(r.status == "late", "status parsed");
  CHECK(r.timeText == "08:42", "time parsed");
  CHECK(HttpStub::lastUrl == String("https://nrjchonjlncamfyzmfye.supabase.co/rest/v1/rpc/astro_mark_attendance"),
        "mark URL correct");
  CHECK(HttpStub::lastHeaders == String("Content-Type: application/json\napikey: sb_publishable_TEST\n"
                                        "Authorization: Bearer sb_publishable_TEST\n"), "headers sent");
  {
    JsonDocument sent;
    CHECK(deserializeJson(sent, HttpStub::lastBody) == DeserializationError::Ok, "request body is valid JSON");
    CHECK(String((const char*)(sent["p_device_code"] | "")) == "ASTRO-RNK-01", "p_device_code sent");
    CHECK(String((const char*)(sent["p_card_uid"] | "")) == "A1B2C3D4", "p_card_uid sent");
    CHECK(sent["p_event_uid"].is<const char*>(), "p_event_uid sent");
    CHECK(String((const char*)(sent["p_event_ts"] | "")).endsWith("Z"), "p_event_ts is ISO-8601 Z");
  }

  // ---- 3. duplicate -------------------------------------------------------
  HttpStub::nextBody = ALREADY_JSON;
  r = cloud.markRfid("A1B2C3D4");
  CHECK(r.ok && r.duplicate && !r.marked, "replay -> duplicate");
  CHECK(r.code == "ALREADY_MARKED", "code ALREADY_MARKED");

  // ---- 4. unknown card ----------------------------------------------------
  HttpStub::nextBody = UNKNOWN_JSON;
  r = cloud.markRfid("DEADBEEF");
  CHECK(!r.ok && r.code == "UNKNOWN_CARD", "unknown card code");
  CHECK(!r.marked && !r.offline, "unknown card is not marked/offline");

  // ---- 5. server-side error body (bad secret) -----------------------------
  HttpStub::nextCode = 401;
  HttpStub::nextBody = R"({"code":"28P01","message":"BAD_DEVICE_SECRET"})";
  r = cloud.markRfid("A1B2C3D4");
  CHECK(!r.ok, "401 is a failure");
  CHECK(r.code == "BAD_DEVICE_SECRET", "error code parsed from body");
  CHECK(!r.offline, "a 401 must NOT be queued as offline");

  // ---- 6. offline: tap stored in NVS --------------------------------------
  HttpStub::nextCode = 200;
  g_wifiStatus = WL_IDLE_STATUS;          // Wi-Fi lost
  r = cloud.markRfid("A1B2C3D4");
  CHECK(r.offline && r.code == "OFFLINE", "offline tap reported");
  CHECK(cloud.pendingEvents() == 1, "one event queued");

  {
    HttpStub::nextBody = HEARTBEAT_JSON;   // begin() fires a heartbeat
    AstroCloud reborn;                    // simulate a power cycle
    reborn.begin(2000);
    CHECK(reborn.pendingEvents() == 1, "queue survives reboot (NVS)");
  }

  // ---- 7. back online: batch replay --------------------------------------
  g_wifiStatus = WL_CONNECTED;
  HttpStub::nextBody = BATCH_JSON;
  int synced = cloud.syncQueue();
  CHECK(synced == 1, "one queued tap synced");
  CHECK(cloud.pendingEvents() == 0, "queue empty after sync");
  CHECK(HttpStub::lastUrl == String("https://nrjchonjlncamfyzmfye.supabase.co/rest/v1/rpc/astro_sync_batch"),
        "batch URL correct");
  {
    JsonDocument sent;
    CHECK(deserializeJson(sent, HttpStub::lastBody) == DeserializationError::Ok, "batch body is valid JSON");
    JsonArray ev = sent["p_events"];
    CHECK(ev.size() == 1, "batch carries one event");
    CHECK(String((const char*)(ev[0]["card_uid"] | "")) == "A1B2C3D4", "queued card_uid preserved");
    CHECK(ev[0]["event_uid"].is<const char*>(), "queued event_uid preserved");
    CHECK(String((const char*)(ev[0]["event_ts"] | "")).endsWith("Z"), "queued event_ts preserved");
  }

  // ---- 8. failed sync must keep the queue --------------------------------
  g_wifiStatus = WL_IDLE_STATUS;
  cloud.markRfid("A1B2C3D4");
  CHECK(cloud.pendingEvents() == 1, "second offline tap queued");
  g_wifiStatus = WL_CONNECTED;
  HttpStub::nextCode = 500;
  HttpStub::nextBody = R"({"message":"boom"})";
  CHECK(cloud.syncQueue() == 0, "failed batch returns 0");
  CHECK(cloud.pendingEvents() == 1, "failed batch keeps the event");

  // ---- 9. lookup ---------------------------------------------------------
  HttpStub::nextCode = 200;
  HttpStub::nextBody = R"({"ok":true,"code":"KNOWN_CARD","uid":"A1B2C3D4","card_active":true,"student":{"id":"1","roll_no":"DEMO-01","name":"Demo Student","class":"9-A"}})";
  AstroTapResult lk = cloud.lookupCard("A1B2C3D4");
  CHECK(lk.ok && lk.code == "KNOWN_CARD" && lk.name == "Demo Student", "lookup parses student");

  // ---- 10. transient 5xx must be queued, not lost -----------------------
  {
    int before = cloud.pendingEvents();
    HttpStub::nextCode = 503;
    HttpStub::nextBody = R"({"message":"upstream unavailable"})";
    AstroTapResult q = cloud.markRfid("A1B2C3D4");
    CHECK(q.offline && q.code == "QUEUED", "503 tap is queued for replay");
    CHECK(cloud.pendingEvents() == before + 1, "queue grew by one on 5xx");
  }

  // ---- 11. serverOk() tracks the heartbeat ------------------------------
  HttpStub::nextCode = 500;
  HttpStub::nextBody = R"({"message":"down"})";
  cloud.heartbeat();
  CHECK(!cloud.serverOk(), "serverOk() false after failed heartbeat");
  HttpStub::nextCode = 200;
  HttpStub::nextBody = HEARTBEAT_JSON;
  cloud.heartbeat();
  CHECK(cloud.serverOk(), "serverOk() true after good heartbeat");

  std::printf("\n%d passed, %d failed\n", g_pass, g_fail);
  return g_fail == 0 ? 0 : 1;
}
