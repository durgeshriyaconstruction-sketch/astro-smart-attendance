#!/usr/bin/env python3
"""
Second set of edits for firmware/esp32/main.cpp (Astro Smart Attendance v26.11.7):
keep the gate device and the cloud database showing the same students.

    python3 tools/patch_firmware_sync.py firmware/esp32/main.cpp

Run it on a main.cpp that already has the first set (tools/patch_firmware.py).
Safe to run twice: it says "already patched" and changes nothing. If a place it
needs is not found exactly once it stops without writing the file.

What it changes (every added line is tagged ASTRO-SYNC-2 in the file):

  1. pull(), student list from the cloud
       - a student the cloud never stored is sent again (it used to stay marked
         "sent" for ever, so the device showed students the cloud did not have)
       - a student removed on the website, or given a new card there, is removed
         from the device too (an empty cloud list must be seen twice in a row
         first; if that empties the device, the built-in demo list is not
         created again at the next start)
       - class and section of students added on the website are taken over
  2. pull(), end: the device's own page refreshes when the cloud changed something
  3. sync(): when the cloud refuses items it says why (Serial + cloud status)
     instead of reporting "all records synced"
  4. new reportDeviceStatus(): once a minute the device tells the cloud its
     address on the school Wi-Fi and its signal strength (shown on the website)
"""
import sys

MARK = "ASTRO-SYNC-2"


def edits(nl):
    def L(*lines):
        return nl.join(lines) + nl

    return [
        # ------------------------------------------------------------------ 1a
        ("pull(): remember which cards the cloud listed",
         L('        for (JsonVariant v : d.as<JsonArray>()) {',
           '          JsonObject o = v.as<JsonObject>();',
           '          String id = upper(jsonStr(o["rfid_uid"], jsonStr(o["rfid"])));',
           '          if (!id.length()) continue;',
           '          if (std::find(Data::deletedStudents.begin(), Data::deletedStudents.end(), id) != Data::deletedStudents.end()) continue;'),
         L('        std::vector<String> cloudCards;   // ASTRO-SYNC-2: every card number the cloud just listed',
           '        for (JsonVariant v : d.as<JsonArray>()) {',
           '          JsonObject o = v.as<JsonObject>();',
           '          String id = upper(jsonStr(o["rfid_uid"], jsonStr(o["rfid"])));',
           '          if (!id.length()) continue;',
           '          cloudCards.push_back(id);',
           '          if (std::find(Data::deletedStudents.begin(), Data::deletedStudents.end(), id) != Data::deletedStudents.end()) continue;')),
        # ------------------------------------------------------------------ 1b
        ("pull(): class/section from the cloud, then make both lists match",
         L('          String sid = jsonStr(o["student_id"], x->studentId);',
           '          if (sid.length() && sid != x->studentId) { x->studentId = sid; changed = true; }',
           '          x->clouded = true;',
           '        }',
           '      }',
           '    }',
           '  } else if (current == 2) {'),
         L('          String sid = jsonStr(o["student_id"], x->studentId);',
           '          if (sid.length() && sid != x->studentId) { x->studentId = sid; changed = true; }',
           '          // ASTRO-SYNC-2: class and section also come from the cloud (students added on the website)',
           '          String cloudClass = jsonStr(o["class_name"], x->className);',
           '          if (cloudClass != x->className) { x->className = cloudClass; changed = true; }',
           '          String cloudSection = jsonStr(o["section"], x->section);',
           '          if (cloudSection != x->section) { x->section = cloudSection; changed = true; }',
           '          if (!x->displayName.length()) x->displayName = x->name;',
           '          x->clouded = true;',
           '        }',
           '        // ASTRO-SYNC-2: make this device\'s list match the cloud\'s list.',
           '        //  - a student the cloud never stored (it has no cloud id yet) is sent again;',
           '        //  - a student the cloud knew and no longer lists was removed, or given a new',
           '        //    card, on the website: it is removed here too.',
           '        // An empty cloud list must be seen twice in a row before it removes anyone.',
           '        static uint8_t emptyCloudLists = 0;',
           '        if (cloudCards.empty()) { if (emptyCloudLists < 2) emptyCloudLists++; } else emptyCloudLists = 0;',
           '        bool mayRemove = !cloudCards.empty() || emptyCloudLists >= 2;',
           '        bool resendStudents = false;',
           '        std::vector<String> goneCards;',
           '        for (auto& s : Data::students) {',
           '          if (!s.clouded) continue;',
           '          if (std::find(cloudCards.begin(), cloudCards.end(), s.rfid) != cloudCards.end()) continue;',
           '          bool cloudKnew = s.studentId.length() == 36 && s.studentId.charAt(8) == \'-\';',
           '          if (!cloudKnew) { s.clouded = false; resendStudents = true; }',
           '          else if (mayRemove) goneCards.push_back(s.rfid);',
           '        }',
           '        for (auto& gone : goneCards) {',
           '          Data::students.erase(std::remove_if(Data::students.begin(), Data::students.end(), [&](const Student& st) { return st.rfid == gone; }), Data::students.end());',
           '          Data::records.erase(std::remove_if(Data::records.begin(), Data::records.end(), [&](const Record& rc) { return rc.rfid == gone; }), Data::records.end());',
           '          Data::periodMarks.erase(std::remove_if(Data::periodMarks.begin(), Data::periodMarks.end(), [&](const PeriodRecord& pm) { return pm.rfid == gone; }), Data::periodMarks.end());',
           '          Data::leaves.erase(std::remove_if(Data::leaves.begin(), Data::leaves.end(), [&](const Leave& lv) { return lv.rfid == gone; }), Data::leaves.end());',
           '          changed = true;',
           '        }',
           '        if (!goneCards.empty() && Data::students.empty() && !Data::freshWiped) {',
           '          // the website removed every student: do not bring the built-in demo list back at the next start',
           '          Preferences wp;',
           '          wp.begin("astro-wipe", false);',
           '          wp.putBool("freshWipe", true);',
           '          wp.end();',
           '          Data::freshWiped = true;',
           '        }',
           '        if (resendStudents) { changed = true; triggerSyncNow(); }',
           '      }',
           '    }',
           '  } else if (current == 2) {')),
        # ------------------------------------------------------------------- 2
        ("pull(): tell the device's own page that something changed; add reportDeviceStatus()",
         L('  if (changed) {',
           '    Data::recountAll();',
           '    Data::markCloudAck();',
           '  }',
           '}',
           '',
           'static void safePull() {'),
         L('  if (changed) {',
           '    Data::recountAll();',
           '    Data::markCloudAck();',
           '    Data::generation++;   // ASTRO-SYNC-2: the device\'s own page reloads its data',
           '  }',
           '}',
           '',
           '// ASTRO-SYNC-2: once a minute tell the cloud this device\'s address on the school',
           '// Wi-Fi and its signal strength, so the website can show them.',
           'static void reportDeviceStatus() {',
           '  static uint32_t lastReport = 0;',
           '  if (lastReport && millis() - lastReport < 60000UL) return;',
           '  lastReport = millis();',
           '  DynamicJsonDocument q(512);',
           '  q["p_device_code"] = String(ASTRO_DEVICE_CODE);',
           '  q["p_device_secret"] = String(ASTRO_DEVICE_SECRET);',
           '  q["p_rssi"] = (int)WiFi.RSSI();',
           '  q["p_ip"] = WiFi.localIP().toString();',
           '  q["p_firmware"] = String(FW_VERSION);',
           '  rpcCall("astro_device_ping", jsonString(q));',
           '}',
           '',
           'static void safePull() {')),
        # ------------------------------------------------------------------ 3a
        ("sync(): read the cloud's answer",
         L('  int code = rpcCall("astro_sync_batch", payload);',
           '  if (code < 200 || code >= 300) return false;'),
         L('  String syncReply;',
           '  int code = rpcCall("astro_sync_batch", payload, &syncReply);',
           '  if (code < 200 || code >= 300) return false;',
           '  // ASTRO-SYNC-2: the cloud answers 200 even when it refused some items; keep the reason',
           '  String syncRejected = "";',
           '  {',
           '    DynamicJsonDocument rd(1024);',
           '    if (!deserializeJson(rd, syncReply) && rd.is<JsonObject>()) {',
           '      int refused = rd["failed"] | 0;',
           '      if (refused > 0) {',
           '        syncRejected = String("Cloud refused ") + String(refused) + " item(s): " + jsonStr(rd["last_error"], "no reason given");',
           '        Serial.println("[SUPABASE] " + syncRejected);',
           '      }',
           '    }',
           '  }')),
        # ------------------------------------------------------------------ 3b
        ("sync(): show the reason instead of clearing it",
         L('  batchMore = pendingEntities();',
           '  lastError = "";',
           '  lastSuccess = nowEpoch();'),
         L('  batchMore = pendingEntities();',
           '  lastError = syncRejected;   // ASTRO-SYNC-2 (was: "")',
           '  lastSuccess = nowEpoch();')),
        # ------------------------------------------------------------------- 4
        ("service(): report address and signal while online",
         L('  state = State::ONLINE;',
           '  message = "Supabase RPC sync active";',
           '  if (millis() - lastPull > 12000UL) pull();'),
         L('  state = State::ONLINE;',
           '  message = "Supabase RPC sync active";',
           '  reportDeviceStatus();   // ASTRO-SYNC-2',
           '  if (millis() - lastPull > 12000UL) pull();')),
    ]


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    path = sys.argv[1]
    with open(path, "r", encoding="utf-8", newline="") as f:
        text = f.read()
    if MARK in text:
        print("already patched, nothing to do")
        return
    nl = "\r\n" if "\r\n" in text else "\n"
    todo = edits(nl)
    for name, old, new in todo:
        n = text.count(old)
        if n != 1:
            sys.exit("STOP, nothing written. Expected exactly one place for: %s (found %d)" % (name, n))
    for name, old, new in todo:
        text = text.replace(old, new)
        print("ok  " + name)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print("done: %d edits written to %s" % (len(todo), path))


if __name__ == "__main__":
    main()
