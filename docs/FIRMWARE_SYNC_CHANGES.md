# main.cpp: keep the device and the website showing the same students

## What was wrong

The gate device showed 18 students and the website showed 0. Two things caused it.

1. **Database (fixed, nothing for you to do).** The function that stores a
   student sent by the device failed for every student
   (`there is no unique or exclusion constraint matching the ON CONFLICT specification`).
   Fixed in `supabase/migrations/20261114000005_fix_device_student_upload.sql`,
   already applied to the live database.
2. **main.cpp.** The cloud answers "200 OK" for a batch even when it refused the
   students inside it. The sketch only looked at the 200, marked the students as
   sent, reported "all records synced" and never tried again. It also never
   removed a student that was deleted on the website, and ignored the class and
   section of students added there.

The 18 students are the demo list built into the sketch (`kSeed` in
`Data::defaults()`: Shaurya Gupta, Aarav Mishra, ...). They are created whenever
the device starts with empty storage.

## What to do

**Easiest:** download the ready file and flash it. Keep your own `astro_config.h`
next to it, unchanged.

<https://github.com/durgeshriyaconstruction-sketch/astro-smart-attendance/raw/arena/5084b081-astro-smart-attendance/firmware/esp32/main.cpp>

**Or patch your own copy** (it must already have the first set of fixes):

```bash
python3 tools/patch_firmware_sync.py path/to/main.cpp
```

The script stops without writing anything if your file differs at a place it
needs. **Or make the six edits by hand**; they are listed at the end of this page.
Every added line carries the tag `ASTRO-SYNC-2`, so you can search for it.

## What changes on the device

| | Before | After |
|---|---|---|
| Student the cloud never stored | marked "sent", never sent again | sent again until the cloud has it |
| Student deleted on the website | stays on the device for ever | removed from the device (with that student's local attendance rows) |
| Card changed on the website | old card keeps working on the device | old card is removed, new card is added |
| Student added on the website | name and roll only, class shown as 9-A | class and section from the website |
| Device's own page | shows cloud changes only after a reload | refreshes by itself |
| Cloud refuses an item | "all records synced" | Serial and cloud status say `Cloud refused N item(s): reason` |
| Device address and Wi-Fi signal | unknown to the website | sent once a minute, shown on the website's device pages |

Safety nets: nothing is removed when the request fails or the reply is cut off;
an empty cloud list must arrive twice in a row (about a minute apart) before it
removes anyone; a student still waiting to be sent is never removed. If the
website removes every student, the device also remembers not to create its
built-in demo list again at the next start.

## After flashing

1. Open Serial Monitor at 115200 and wait for
   `[SUPABASE] Device ASTRO-RNK-01 authenticated`.
2. Within about two minutes the device notices that the cloud does not have its
   students, sends them (6 per batch), and the website shows them.
3. If Serial prints `[SUPABASE] Cloud refused ...`, send that line to whoever
   maintains the database; it is the exact reason.

## How this was checked, and what was not

- `tools/fwcheck/run.sh` compiles the added lines (copied out of the patched
  file) against the real ArduinoJson 6.21.5 with stand-ins for Arduino's
  `String`, `WiFi` and `Serial`, then runs them against made-up cloud replies:
  30 checks pass.
- The database side was run on the live project inside a transaction that was
  rolled back: a batch of three of the demo students is stored, sending one again
  makes no duplicate, the device list and the website both show them, and
  `astro_device_ping` accepts the five names the sketch sends.
- **Not done:** the whole sketch was not compiled with the Arduino IDE / ESP32
  core, and nothing was run on a real ESP32. If the IDE reports an error, it will
  be in one of the six places below.

## Limits that are still there

- The student list is read in one piece. It works up to roughly 150 students;
  beyond that the reply no longer fits in memory and the list is skipped.
- The demo list is still in the sketch: a device that starts with empty storage
  creates those 18 students and, now that the database accepts them, uploads
  them. For a real school, empty the `kSeed` list before the first start, or
  delete the demo students on the website (the device then removes them too).
- A student deleted on the website keeps a fingerprint template in the sensor
  until it is overwritten; the template no longer opens the gate.

## The six edits

### Edit 1. In `pull()`: remember which cards the cloud listed

Find:

```cpp
        for (JsonVariant v : d.as<JsonArray>()) {
          JsonObject o = v.as<JsonObject>();
          String id = upper(jsonStr(o["rfid_uid"], jsonStr(o["rfid"])));
          if (!id.length()) continue;
          if (std::find(Data::deletedStudents.begin(), Data::deletedStudents.end(), id) != Data::deletedStudents.end()) continue;
```

Replace with:

```cpp
        std::vector<String> cloudCards;   // ASTRO-SYNC-2: every card number the cloud just listed
        for (JsonVariant v : d.as<JsonArray>()) {
          JsonObject o = v.as<JsonObject>();
          String id = upper(jsonStr(o["rfid_uid"], jsonStr(o["rfid"])));
          if (!id.length()) continue;
          cloudCards.push_back(id);
          if (std::find(Data::deletedStudents.begin(), Data::deletedStudents.end(), id) != Data::deletedStudents.end()) continue;
```

### Edit 2. In `pull()`: take class and section from the cloud, then make both lists match

Find:

```cpp
          String sid = jsonStr(o["student_id"], x->studentId);
          if (sid.length() && sid != x->studentId) { x->studentId = sid; changed = true; }
          x->clouded = true;
        }
      }
    }
  } else if (current == 2) {
```

Replace with:

```cpp
          String sid = jsonStr(o["student_id"], x->studentId);
          if (sid.length() && sid != x->studentId) { x->studentId = sid; changed = true; }
          // ASTRO-SYNC-2: class and section also come from the cloud (students added on the website)
          String cloudClass = jsonStr(o["class_name"], x->className);
          if (cloudClass != x->className) { x->className = cloudClass; changed = true; }
          String cloudSection = jsonStr(o["section"], x->section);
          if (cloudSection != x->section) { x->section = cloudSection; changed = true; }
          if (!x->displayName.length()) x->displayName = x->name;
          x->clouded = true;
        }
        // ASTRO-SYNC-2: make this device's list match the cloud's list.
        //  - a student the cloud never stored (it has no cloud id yet) is sent again;
        //  - a student the cloud knew and no longer lists was removed, or given a new
        //    card, on the website: it is removed here too.
        // An empty cloud list must be seen twice in a row before it removes anyone.
        static uint8_t emptyCloudLists = 0;
        if (cloudCards.empty()) { if (emptyCloudLists < 2) emptyCloudLists++; } else emptyCloudLists = 0;
        bool mayRemove = !cloudCards.empty() || emptyCloudLists >= 2;
        bool resendStudents = false;
        std::vector<String> goneCards;
        for (auto& s : Data::students) {
          if (!s.clouded) continue;
          if (std::find(cloudCards.begin(), cloudCards.end(), s.rfid) != cloudCards.end()) continue;
          bool cloudKnew = s.studentId.length() == 36 && s.studentId.charAt(8) == '-';
          if (!cloudKnew) { s.clouded = false; resendStudents = true; }
          else if (mayRemove) goneCards.push_back(s.rfid);
        }
        for (auto& gone : goneCards) {
          Data::students.erase(std::remove_if(Data::students.begin(), Data::students.end(), [&](const Student& st) { return st.rfid == gone; }), Data::students.end());
          Data::records.erase(std::remove_if(Data::records.begin(), Data::records.end(), [&](const Record& rc) { return rc.rfid == gone; }), Data::records.end());
          Data::periodMarks.erase(std::remove_if(Data::periodMarks.begin(), Data::periodMarks.end(), [&](const PeriodRecord& pm) { return pm.rfid == gone; }), Data::periodMarks.end());
          Data::leaves.erase(std::remove_if(Data::leaves.begin(), Data::leaves.end(), [&](const Leave& lv) { return lv.rfid == gone; }), Data::leaves.end());
          changed = true;
        }
        if (!goneCards.empty() && Data::students.empty() && !Data::freshWiped) {
          // the website removed every student: do not bring the built-in demo list back at the next start
          Preferences wp;
          wp.begin("astro-wipe", false);
          wp.putBool("freshWipe", true);
          wp.end();
          Data::freshWiped = true;
        }
        if (resendStudents) { changed = true; triggerSyncNow(); }
      }
    }
  } else if (current == 2) {
```

### Edit 3. End of `pull()`: refresh the device's own page, and add `reportDeviceStatus()`

Find:

```cpp
  if (changed) {
    Data::recountAll();
    Data::markCloudAck();
  }
}

static void safePull() {
```

Replace with:

```cpp
  if (changed) {
    Data::recountAll();
    Data::markCloudAck();
    Data::generation++;   // ASTRO-SYNC-2: the device's own page reloads its data
  }
}

// ASTRO-SYNC-2: once a minute tell the cloud this device's address on the school
// Wi-Fi and its signal strength, so the website can show them.
static void reportDeviceStatus() {
  static uint32_t lastReport = 0;
  if (lastReport && millis() - lastReport < 60000UL) return;
  lastReport = millis();
  DynamicJsonDocument q(512);
  q["p_device_code"] = String(ASTRO_DEVICE_CODE);
  q["p_device_secret"] = String(ASTRO_DEVICE_SECRET);
  q["p_rssi"] = (int)WiFi.RSSI();
  q["p_ip"] = WiFi.localIP().toString();
  q["p_firmware"] = String(FW_VERSION);
  rpcCall("astro_device_ping", jsonString(q));
}

static void safePull() {
```

### Edit 4. In `sync()`: read the cloud's answer

Find:

```cpp
  int code = rpcCall("astro_sync_batch", payload);
  if (code < 200 || code >= 300) return false;
```

Replace with:

```cpp
  String syncReply;
  int code = rpcCall("astro_sync_batch", payload, &syncReply);
  if (code < 200 || code >= 300) return false;
  // ASTRO-SYNC-2: the cloud answers 200 even when it refused some items; keep the reason
  String syncRejected = "";
  {
    DynamicJsonDocument rd(1024);
    if (!deserializeJson(rd, syncReply) && rd.is<JsonObject>()) {
      int refused = rd["failed"] | 0;
      if (refused > 0) {
        syncRejected = String("Cloud refused ") + String(refused) + " item(s): " + jsonStr(rd["last_error"], "no reason given");
        Serial.println("[SUPABASE] " + syncRejected);
      }
    }
  }
```

### Edit 5. In `sync()`: keep the reason instead of clearing it

Find:

```cpp
  batchMore = pendingEntities();
  lastError = "";
  lastSuccess = nowEpoch();
```

Replace with:

```cpp
  batchMore = pendingEntities();
  lastError = syncRejected;   // ASTRO-SYNC-2 (was: "")
  lastSuccess = nowEpoch();
```

### Edit 6. In `service()`: report address and signal while online

Find:

```cpp
  state = State::ONLINE;
  message = "Supabase RPC sync active";
  if (millis() - lastPull > 12000UL) pull();
```

Replace with:

```cpp
  state = State::ONLINE;
  message = "Supabase RPC sync active";
  reportDeviceStatus();   // ASTRO-SYNC-2
  if (millis() - lastPull > 12000UL) pull();
```
