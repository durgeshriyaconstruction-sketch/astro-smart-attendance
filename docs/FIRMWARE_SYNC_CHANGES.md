# main.cpp: keep the device and the website showing the same students

## What was wrong

The gate device showed 18 students and the website showed 0. Three things caused it.

0. **The device has never connected to the cloud (this is the one that needs you).**
   Every call the device makes must carry its secret key. The key belongs in a
   file called `astro_config.h` next to `main.cpp`. That file is deliberately
   never stored in this repository, so a sketch built from GitHub alone has an
   empty key, and the cloud answers every call with
   `403 DEVICE_SECRET_REQUIRED`. The database's own statistics show it: since
   the device was registered, not one call from it has ever succeeded. (The
   "last seen" times that used to be on the website came from test calls made
   while setting the database up; they are cleared now, and the website says
   "never connected" until the real device checks in.)
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

**1. Create `astro_config.h` in the same folder as `main.cpp`** with these lines
(copy `astro_config.example.h` if you prefer the long version):

```cpp
#pragma once
#define ASTRO_WIFI_SSID     "your Wi-Fi name"        // 2.4 GHz, with internet
#define ASTRO_WIFI_PASS     "your Wi-Fi password"
#define ASTRO_DEVICE_CODE   "ASTRO-RNK-01"
#define ASTRO_DEVICE_SECRET "the 48-character device secret"
```

**Where exactly does the file go?** In a PlatformIO project it goes in `src/`,
right next to `main.cpp` - not in the project root, and not in `include/`:

```text
C:\Users\<you>\Documents\PlatformIO\Projects\<project>\src\main.cpp
C:\Users\<you>\Documents\PlatformIO\Projects\<project>\src\astro_config.h
```

Create it with **File > New File** inside PlatformIO/VS Code, or in Explorer:
right-click the `src` folder > New > Text Document, then rename it to
`astro_config.h`. Explorer hides extensions by default, so check the real name
is not `astro_config.h.txt` (View > Show > File name extensions).

`main.cpp` picks the file up with `#if __has_include("astro_config.h")`. A wrong
name or a wrong folder is therefore ignored silently and the secret stays empty
- the boot line then reads `Device Secret: MISSING` instead of `SET (len 48)`.

**Is your `main.cpp` new enough to use it?** Open it and search (Ctrl+F) for
`astro_config.h`. Found: nothing more to do, create the config file and flash.
Not found: your copy predates the fix, so replace it with the ready file below
(or run `tools/patch_firmware.py` on it first).

Only the two Wi-Fi lines need typing. `main.cpp` already carries working
defaults for `ASTRO_SUPABASE_HOST`, `ASTRO_SUPABASE_KEY` and
`ASTRO_DEVICE_CODE`, so leave those out of `astro_config.h` rather than
pasting older values over them.

- The device secret is not written anywhere in this repository (the repository
  is public). It was given to the owner directly on 14 Nov 2026. If it is lost,
  make a new one in the Supabase SQL editor; the old one stops working at once:
  `select public.astro_rotate_device_secret('ASTRO-RNK-01');`
- The two Wi-Fi lines are only used when the device has no Wi-Fi saved yet.
  A Wi-Fi saved on the device's own WiFi Manager page wins.
- Do not upload `astro_config.h` to GitHub.

**2. Flash `main.cpp`.** Easiest: download the ready file.

<https://github.com/durgeshriyaconstruction-sketch/astro-smart-attendance/raw/arena/bd629373-astro-smart-attendance/firmware/esp32/main.cpp>

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
| Device address and Wi-Fi signal | unknown to the website | sent once a minute, shown on the website's device pages - even while a sync is failing |

### Online / Offline on the website (`ASTRO-HEARTBEAT-1`)

The website counts the device as **Online** when it has reported within the last
90 seconds (`ONLINE_S` in `web/supabase-bridge.js`). The device reports every 60
seconds, so a healthy connection shows Online within about a minute of booting,
and flips to Offline roughly 90 seconds after the Wi-Fi goes away.

That report used to run only on the "nothing left to sync" path of
`Cloud::service()`. A device that was authenticated and on Wi-Fi but still
retrying a failed batch therefore never reported itself: the website said
Offline for a device that was in fact working, and `devices.ip` and
`devices.wifi_rssi` stayed empty for ever. The report now runs before the sync
step, so the Online/Offline pill reflects the connection instead of the sync
queue. Every added line carries the tag `ASTRO-HEARTBEAT-1`.

Note that reading data does **not** refresh `devices.last_seen` - only
`astro_device_handshake`, `astro_device_ping` and `astro_sync_batch` do. A
`last_seen` that stops moving therefore means "no handshake, no report and no
batch", not merely "no reads".
Safety nets: nothing is removed when the request fails or the reply is cut off;
an empty cloud list must arrive twice in a row (about a minute apart) before it
removes anyone; a student still waiting to be sent is never removed. If the
website removes every student, the device also remembers not to create its
built-in demo list again at the next start.

## After flashing

1. Open Serial Monitor at 115200. The start-up lines must say
   `[BOOT] Device Secret: SET (len 48)` and, once the Wi-Fi is up,
   `[SUPABASE] Device ASTRO-RNK-01 authenticated`.
2. On the website the note "The gate device has never connected" disappears and
   the device shows as online.
3. Students and scans now travel both ways within a minute or two.
4. If it does not work, the Serial line tells why:

| Serial says | Meaning |
|---|---|
| `Device Secret: MISSING` | `astro_config.h` is not next to `main.cpp`, or the secret line is empty |
| `Handshake FAILED (HTTP 403) :: ... DEVICE_SECRET_REQUIRED` | same as above |
| `Handshake FAILED (HTTP 403) :: ... BAD_DEVICE_SECRET` | the secret is not the current one |
| `Supabase DNS/TLS preflight pending` | the Wi-Fi has no internet, or it blocks `supabase.co` |
| `waiting-wifi` | the device has not joined a Wi-Fi (wrong name or password, or a 5 GHz network) |
| `Cloud refused N item(s): ...` | the cloud answered but refused something; the text is the exact reason |

The 18 demo students of the sketch (Shaurya Gupta ... Aditya Rana) are already
in the cloud: they were sent on 14 Nov 2026 from outside the device, in the same
format the device uses, to prove the path. When the device connects it finds
them there and does not create duplicates. Their made-up parent e-mail addresses
(`parent1@gmail.com` ...) are **not** stored, so the school's absence and arrival
e-mails never go to those strangers (`supabase/migrations/20261114000006`).

## How this was checked, and what was not

- `tools/fwcheck/run.sh` compiles the added lines (copied out of the patched
  file) against the real ArduinoJson 6.21.5 with stand-ins for Arduino's
  `String`, `WiFi` and `Serial`, then runs them against made-up cloud replies:
  30 checks pass.
- The database side was run on the live project inside a transaction that was
  rolled back: a batch of three of the demo students is stored, sending one again
  makes no duplicate, the device list and the website both show them, and
  `astro_device_ping` accepts the five names the sketch sends.
- The cloud side was also exercised over real HTTPS on 14 Nov 2026, with the
  same address, key, headers and JSON the sketch sends: the handshake, three
  student batches of six, the six list calls and the status ping all answered
  200; the same handshake without the secret, or with a wrong one, answered 403.
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
