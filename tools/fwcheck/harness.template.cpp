
// Host-side check of the lines tools/patch_firmware_sync.py adds to main.cpp.
// The blocks between the "---- from main.cpp" markers are copied out of the
// patched file byte for byte; everything else is a stand-in.
#include <Arduino.h>
#include <ArduinoJson.h>
#include <vector>
#include <algorithm>
#include <cassert>
SerialStub Serial; WiFiStub WiFi;
static unsigned long fakeNow = 100000; unsigned long millis() { return fakeNow; }
#define MAX_STUDENTS 1024
#define ASTRO_DEVICE_CODE "ASTRO-RNK-01"
#define ASTRO_DEVICE_SECRET "secret"
#define FW_VERSION "26.11.7"
struct Student { String rfid, name, roll; String studentId = ""; String displayName = ""; String className = "9", section = "A"; bool active = true; bool clouded = false; };
struct Record { String rfid, date; bool clouded = false; };
struct PeriodRecord { String rfid, date; bool clouded = false; };
struct Leave { String rfid; bool clouded = false; };
static bool savedFreshWipe = false;   // what the stand-in for the ESP32's Preferences storage holds
struct Preferences { void begin(const char*, bool) {} void putBool(const char* key, bool v) { if (String(key) == "freshWipe") savedFreshWipe = v; } void end() {} };
namespace Data {
  std::vector<Student> students; std::vector<Record> records; std::vector<PeriodRecord> periodMarks; std::vector<Leave> leaves;
  std::vector<String> deletedStudents; uint32_t generation = 1; int recounts = 0, acks = 0; bool freshWiped = false;
  static Student* student(const String& rfid) { for (auto& s : students) if (s.rfid == rfid) return &s; return nullptr; }
  static void recountAll() { recounts++; }
  static void markCloudAck() { acks++; }
}
@@UPPER@@
@@JSONSTR@@

static String jsonString(const JsonDocument& doc) { String out; serializeJson(doc, out); return out; }
static size_t safeJsonCap(size_t a, size_t) { return a; }
namespace Cloud {
static String lastError = "", fakeReply = "", lastRpc = "", lastPayload = "";
static int fakeCode = 200, syncTriggers = 0;
static uint32_t lastSuccess = 0, lastPull = 0;
static bool batchMore = false;
static uint32_t nowEpoch() { return 1; }
static bool pendingEntities() { return false; }
void triggerSyncNow() { syncTriggers++; }
static int rpcCall(const char* rpcName, const String& jsonPayload, String* out = nullptr) { lastRpc = rpcName; lastPayload = jsonPayload; if (out) *out = fakeReply; return fakeCode; }

static void pullStudentsStep() {
  uint8_t current = 1; String raw; bool changed = false; String reqBody = "{}";
  if (current == 0) {
// ---- from main.cpp (student step of pull) ----
@@STEP@@
// ---- end ----
  } else if (current == 2) {
  }
// ---- from main.cpp (end of pull) ----
@@TAIL@@
}
// ---- end ----

// ---- from main.cpp ----
@@REPORT@@
// ---- end ----

static bool syncTail(const String& payload) {
// ---- from main.cpp (sync) ----
@@SYNC@@
// ---- end ----
  batchMore = pendingEntities();
  lastError = syncRejected;   // ASTRO-SYNC-2 (was: "")
  lastSuccess = nowEpoch();
  return true;
}
}  // namespace Cloud

static int fails = 0;
#define CHECK(name, cond) do { if (cond) printf("  ok   %s\n", name); else { printf("  FAIL %s\n", name); fails++; } } while (0)
static Student mk(const char* rfid, const char* name, const char* id, bool clouded) { Student s; s.rfid = rfid; s.name = name; s.roll = "r"; s.studentId = id; s.clouded = clouded; return s; }
static size_t count() { return Data::students.size(); }

int main() {
  using namespace Cloud;
  printf("1. Device thinks 3 demo students are in the cloud; the cloud has none\n");
  Data::students = { mk("04A3B2C1", "Shaurya Gupta", "Shaurya Gupta", true), mk("13D7F9AA", "Aarav Mishra", "Aarav Mishra", true), mk("7C21E4B8", "Ishita Verma", "Ishita Verma", true) };
  fakeReply = "[]"; syncTriggers = 0; uint32_t g = Data::generation;
  pullStudentsStep();
  CHECK("nobody is removed", count() == 3);
  CHECK("all three are queued to be sent again", !Data::students[0].clouded && !Data::students[1].clouded && !Data::students[2].clouded);
  CHECK("a sync is requested", syncTriggers == 1 && Data::generation == g + 1);

  printf("2. After the upload the cloud lists them with its own ids, plus one student added on the website\n");
  for (auto& s : Data::students) s.clouded = true;
  fakeReply = "[{\"name\":\"Shaurya Gupta\",\"roll\":\"9A-01\",\"section\":\"A\",\"rfid_uid\":\"04A3B2C1\",\"class_name\":\"9\",\"student_id\":\"d5063ab0-7548-422c-a156-1b802f90bcd0\",\"fingerprint_id\":null},"
              "{\"name\":\"Aarav Mishra\",\"roll\":\"9A-02\",\"section\":\"A\",\"rfid_uid\":\"13d7f9aa\",\"class_name\":\"9\",\"student_id\":\"e1063ab0-7548-422c-a156-1b802f90bcd1\",\"fingerprint_id\":null},"
              "{\"name\":\"Ishita Verma\",\"roll\":\"9A-03\",\"section\":\"A\",\"rfid_uid\":\"7C21E4B8\",\"class_name\":\"9\",\"student_id\":\"f2063ab0-7548-422c-a156-1b802f90bcd2\",\"fingerprint_id\":null},"
              "{\"name\":\"Web Student\",\"roll\":\"1001\",\"section\":\"B\",\"rfid_uid\":\"A5112233\",\"class_name\":\"10\",\"student_id\":\"a3063ab0-7548-422c-a156-1b802f90bcd3\",\"fingerprint_id\":null}]";
  syncTriggers = 0;
  pullStudentsStep();
  Student* w = Data::student("A5112233");
  CHECK("the website student is added", count() == 4 && w);
  CHECK("...with name, roll, class 10 and section B", w && w->name == "Web Student" && w->roll == "1001" && w->className == "10" && w->section == "B");
  CHECK("device students now carry the cloud's id", Data::student("04A3B2C1")->studentId == "d5063ab0-7548-422c-a156-1b802f90bcd0" && Data::student("13D7F9AA")->studentId.length() == 36);
  CHECK("roll numbers follow the cloud", Data::student("04A3B2C1")->roll == "9A-01");
  CHECK("nothing is sent again", syncTriggers == 0 && Data::students[0].clouded);

  printf("3. One student is deleted on the website and another gets a new card there\n");
  Data::records = { Record{ "13D7F9AA", "2026-11-14", true }, Record{ "04A3B2C1", "2026-11-14", true } };
  Data::leaves = { Leave{ "13D7F9AA", true } };
  fakeReply = "[{\"name\":\"Shaurya Gupta\",\"roll\":\"9A-01\",\"section\":\"A\",\"rfid_uid\":\"04A3B2C1\",\"class_name\":\"9\",\"student_id\":\"d5063ab0-7548-422c-a156-1b802f90bcd0\"},"
              "{\"name\":\"Ishita Verma\",\"roll\":\"9A-03\",\"section\":\"A\",\"rfid_uid\":\"99AABBCC\",\"class_name\":\"9\",\"student_id\":\"f2063ab0-7548-422c-a156-1b802f90bcd2\"},"
              "{\"name\":\"Web Student\",\"roll\":\"1001\",\"section\":\"B\",\"rfid_uid\":\"A5112233\",\"class_name\":\"10\",\"student_id\":\"a3063ab0-7548-422c-a156-1b802f90bcd3\"}]";
  pullStudentsStep();
  CHECK("the deleted student is gone from the device", !Data::student("13D7F9AA"));
  CHECK("...with her attendance and leave rows", Data::records.size() == 1 && Data::records[0].rfid == "04A3B2C1" && Data::leaves.empty());
  CHECK("the old card no longer exists on the device", !Data::student("7C21E4B8"));
  CHECK("the new card belongs to the same student", Data::student("99AABBCC") && Data::student("99AABBCC")->name == "Ishita Verma");
  CHECK("device and cloud list the same 3 students", count() == 3);

  printf("4. Safety nets\n");
  fakeReply = "[]"; pullStudentsStep();
  CHECK("one empty cloud list removes nobody", count() == 3);
  fakeReply = "{\"message\":\"upstream error\"}"; pullStudentsStep();
  CHECK("a reply that is not a list changes nothing", count() == 3);
  fakeReply = "[{\"name\":\"Shaurya Gupta\",\"rfid_uid\":\"04A3B2C1\",\"student_id\":\"d5063ab0-7548-422c-a156-1b802f90bcd0\"}"; pullStudentsStep();
  CHECK("a cut-off reply changes nothing", count() == 3);
  fakeCode = 500; fakeReply = "[]"; pullStudentsStep(); fakeCode = 200;
  CHECK("a failed request changes nothing", count() == 3);
  Data::students.push_back(mk("ABCDEF01", "New On Device", "New On Device", false));
  fakeReply = "[{\"name\":\"Shaurya Gupta\",\"rfid_uid\":\"04A3B2C1\",\"student_id\":\"d5063ab0-7548-422c-a156-1b802f90bcd0\",\"class_name\":\"9\",\"section\":\"A\"}]"; pullStudentsStep();
  CHECK("a student still waiting to be sent is never removed", Data::student("ABCDEF01") && !Data::student("ABCDEF01")->clouded);

  printf("4b. Every student is deleted on the website\n");
  for (auto& st : Data::students) st.clouded = true;
  Data::student("ABCDEF01")->studentId = "b4063ab0-7548-422c-a156-1b802f90bcd4";
  fakeReply = "[{\"name\":\"Shaurya Gupta\",\"rfid_uid\":\"04A3B2C1\",\"student_id\":\"d5063ab0-7548-422c-a156-1b802f90bcd0\",\"class_name\":\"9\",\"section\":\"A\"}]"; pullStudentsStep();
  CHECK("a non-empty list removes the ones it no longer has", count() == 1 && Data::student("04A3B2C1"));
  fakeReply = "[]"; pullStudentsStep();
  CHECK("first empty list: the last student stays", count() == 1 && !Data::freshWiped);
  pullStudentsStep();
  CHECK("second empty list in a row: the device is empty too", count() == 0);
  CHECK("...and the demo list will not come back at the next start", Data::freshWiped && savedFreshWipe);

  printf("5. Cloud refuses items in a batch\n");
  fakeReply = "{\"ok\":true,\"code\":\"BATCH_DONE\",\"failed\":3,\"students\":0,\"last_error\":\"there is no unique or exclusion constraint matching the ON CONFLICT specification\"}";
  CHECK("the batch still counts as delivered", syncTail("{}"));
  CHECK("...but the reason is kept for the status page", lastError == "Cloud refused 3 item(s): there is no unique or exclusion constraint matching the ON CONFLICT specification");
  fakeReply = "{\"ok\":true,\"code\":\"BATCH_DONE\",\"failed\":0,\"students\":6,\"last_error\":null}";
  syncTail("{}");
  CHECK("a clean batch clears the message", lastError == "");
  fakeCode = 503; CHECK("an HTTP error is still a failed batch", !syncTail("{}")); fakeCode = 200;

  printf("6. Address and signal report\n");
  lastRpc = ""; reportDeviceStatus();
  CHECK("calls astro_device_ping", lastRpc == "astro_device_ping");
  CHECK("...with the five names the database function has", lastPayload == "{\"p_device_code\":\"ASTRO-RNK-01\",\"p_device_secret\":\"secret\",\"p_rssi\":-61,\"p_ip\":\"192.168.1.37\",\"p_firmware\":\"26.11.7\"}");
  lastRpc = ""; fakeNow += 30000; reportDeviceStatus();
  CHECK("not again within a minute", lastRpc == "");
  fakeNow += 31000; reportDeviceStatus();
  CHECK("again after a minute", lastRpc == "astro_device_ping");

  printf("\n%s (%d failed)\n", fails ? "FAILED" : "all checks passed", fails);
  return fails ? 1 : 0;
}
