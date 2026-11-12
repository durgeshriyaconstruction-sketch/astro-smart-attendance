// ============================================================================
//  Astro Smart Attendance — complete reference firmware
//  ESP32 DevKit V1 + RC522 + LCD1602 (I2C) + optional R307/AS608 fingerprint
//
//  This is the whole terminal in one file, written around astro_cloud.h, so you
//  can either:
//     (a) flash this sketch as-is, or
//     (b) copy the marked blocks into your existing main.cpp
//         (see docs/main_cpp_additions.md)
//
//  The pin defaults below match the board the school already runs (the rev2
//  PCB that main.cpp v26.11.7 was written for), so flashing this on that board
//  needs no rewiring: RC522 reset is GPIO 4, the buzzer is GPIO 15, and the
//  fingerprint sensor's power pin is GPIO 13.
//
//  Nothing in loop() calls delay(): the buzzer, the result display, the reader
//  poll and the remote-command poll are all paced with millis(), so a tap never
//  stalls the next tap, the heartbeat or the offline-queue sync.
//
//  Remote commands: the dashboard's Devices tab (and the "Scan a card" /
//  "Enrol fingerprint" buttons when adding a student) queues rows in
//  device_commands. This sketch polls them, does the work, and reports back:
//    lcd_text     show up to 32 characters on the LCD for 5 s
//    rfid_capture wait for a tap, report the UID (the database says who owns it)
//    fp_check     wait for a finger, report the template slot
//    fp_enroll    two touches, store a template, report the slot
//    fp_delete    delete the template in payload.slot
//    refresh      redraw the idle screen
//    reboot       restart the terminal
//
//  Libraries (Library Manager):
//    ArduinoJson >= 7.0        (Benoit Blanchon)
//    MFRC522 >= 1.4.10         (GithubCommunity)
//    LiquidCrystal_I2C >= 1.1.4(Marco Schwartz)
//    Adafruit Fingerprint Sensor Library (only if ASTRO_USE_FINGERPRINT 1)
//
//  Board: "ESP32 Dev Module"  |  Upload speed 921600  |  Partition: Default
// ============================================================================

#include <Wire.h>
#include <SPI.h>
#include <LiquidCrystal_I2C.h>
#include <MFRC522.h>

#include "astro_cloud.h"

#ifndef ASTRO_USE_FINGERPRINT
#define ASTRO_USE_FINGERPRINT 0        // set 1 once the R307/AS608 is wired
#endif

#if ASTRO_USE_FINGERPRINT
#include <Adafruit_Fingerprint.h>
HardwareSerial fingerSerial(2);
Adafruit_Fingerprint finger(&fingerSerial);
#endif

// ---------------------------------------------------------------- pins -----
// Every value can be overridden in astro_config.h without editing this file,
// e.g.  #define PIN_RC522_RST 27   before the first #include.
#ifndef PIN_RC522_SS
#define PIN_RC522_SS   5
#endif
#ifndef PIN_RC522_RST
#define PIN_RC522_RST  4               // 27 belongs to UART2 TX on the rev2 PCB
#endif
#ifndef PIN_I2C_SDA
#define PIN_I2C_SDA    21
#endif
#ifndef PIN_I2C_SCL
#define PIN_I2C_SCL    22
#endif
#ifndef PIN_BUZZER
#define PIN_BUZZER     15
#endif
#ifndef PIN_FINGER_RX
#define PIN_FINGER_RX  16              // ESP32 RX2  <- R307 TX (yellow)
#endif
#ifndef PIN_FINGER_TX
#define PIN_FINGER_TX  17              // ESP32 TX2  -> R307 RX (white)
#endif
#ifndef ASTRO_FP_POWER_PIN
#define ASTRO_FP_POWER_PIN -1          // rev2 PCB: 13 gates the sensor's supply
#endif
#ifndef ASTRO_LCD_ADDR
#define ASTRO_LCD_ADDR 0x27            // some 1602 modules answer at 0x3F
#endif
#ifndef ASTRO_CMD_POLL_MS
#define ASTRO_CMD_POLL_MS 3000         // how often to ask for dashboard commands
#endif
#define ASTRO_CMD_WAIT_MS 30000        // how long to wait for a card / finger

LiquidCrystal_I2C lcd(ASTRO_LCD_ADDR, 16, 2);
MFRC522           rfid(PIN_RC522_SS, PIN_RC522_RST);
AstroCloud        cloud;

// --------------------------------------------------------------- helpers ---
void lcdLine(uint8_t row, const String& text) {
  lcd.setCursor(0, row);
  String t = text;
  while (t.length() < 16) t += ' ';
  lcd.print(t.substring(0, 16));
}

// Non-blocking beep: on/off halves of `ms`, spaced by a 60 ms gap, driven from
// loop(). The old blocking version held the whole terminal for up to ~step ms.
struct Buzzer {
  uint8_t       halvesLeft = 0;
  uint16_t      onMs = 100;
  bool          sounding = false;
  unsigned long dueAt = 0;

  void start(uint8_t times, uint16_t ms) {
    noTone(PIN_BUZZER);
    onMs = ms;
    halvesLeft = times ? (uint8_t)(times * 2 - 1) : 0;
    sounding = times > 0;
    if (sounding) tone(PIN_BUZZER, 2200);
    dueAt = millis() + ms;
  }

  void tick() {
    if (!halvesLeft && !sounding) return;
    if (millis() < dueAt) return;
    if (sounding) {
      noTone(PIN_BUZZER);
      sounding = false;
      dueAt = millis() + 60;
      if (halvesLeft) halvesLeft--;
    } else {
      tone(PIN_BUZZER, 2200);
      sounding = true;
      dueAt = millis() + onMs;
      if (halvesLeft) halvesLeft--;
    }
  }
} buzzer;

String uidToHex(MFRC522::Uid *uid) {
  String s;
  for (byte i = 0; i < uid->size; i++) {
    if (uid->uidByte[i] < 0x10) s += "0";
    s += String(uid->uidByte[i], HEX);
  }
  s.toUpperCase();
  return s;
}

void showIdle() {
  if (cloud.serverOk()) {
    lcdLine(0, "Tap card / finger");
    lcdLine(1, String("Online  Q:") + cloud.pendingEvents());
  } else if (cloud.online()) {
    // Wi-Fi is up but the database did not answer (paused project, firewall)
    lcdLine(0, "SERVER DOWN");
    lcdLine(1, String("Saved: ") + cloud.pendingEvents());
  } else {
    lcdLine(0, "OFFLINE MODE");
    lcdLine(1, String("Saved: ") + cloud.pendingEvents());
  }
}

unsigned long holdUntil = 0;   // loop() returns the LCD to idle after this

// Let a short message stand for `ms`, then showIdle() brings the counter back.
void showMessage(const String& l1, const String& l2, unsigned long ms) {
  lcdLine(0, l1);
  lcdLine(1, l2);
  holdUntil = millis() + ms;
}

// Print any AstroTapResult on the LCD for ~1.8 s, then return to idle.
void showTapResult(const AstroTapResult& r) {
  if (r.offline) {
    buzzer.start(2, 120);
    showMessage("SAVED OFFLINE", "Syncs when online", 1800);
  } else if (r.marked || r.duplicate) {
    buzzer.start(1, 60);
    String line2 = r.status + " " + r.timeText;
    if (r.duplicate) line2 += " dup";
    if (r.className.length()) line2 += " " + r.className;
    showMessage(r.name, line2, 1800);
  } else if (r.code == "UNKNOWN_CARD") {
    buzzer.start(3, 80);
    showMessage("CARD NOT", "REGISTERED", 1800);
  } else {
    buzzer.start(2, 150);
    showMessage("CLOUD ERROR", r.code, 1800);
  }

  Serial.printf("[tap] code=%s status=%s name=%s roll=%s class=%s time=%s msg=%s\n",
                r.code.c_str(), r.status.c_str(), r.name.c_str(), r.roll.c_str(),
                r.className.c_str(), r.timeText.c_str(), r.message.c_str());
}

// ---------------------------------------------------- remote commands ------
AstroCloud::AstroCommand pendingCapture;   // rfid_capture: waiting for a tap
String          pendingFpCheck;            // fp_check: waiting for a finger
unsigned long   pendingCaptureUntil = 0;
unsigned long   pendingFpUntil = 0;
unsigned long   lastCmdPollAt = 0;

void failCommand(const String& id, const char* reason) {
  JsonDocument d;
  d["error"] = reason;
  cloud.commandResult(id, false, d);
  Serial.printf("[cmd] failed: %s\n", reason);
}

#if ASTRO_USE_FINGERPRINT
// Two-touch enrolment without blocking: each pass of loop() advances one step.
struct FpEnroll {
  bool          active = false;
  uint8_t       step = 0;
  String        cmdId;
  int           slot = -1;
  unsigned long startedAt = 0;
  unsigned long stepAt = 0;
} enroll;

void failEnroll(const char* reason) {
  if (!enroll.active) return;
  failCommand(enroll.cmdId, reason);
  buzzer.start(2, 120);
  showMessage("ENROL FAILED", reason, 2500);
  enroll = FpEnroll();
}

void startEnroll(const AstroCloud::AstroCommand& c) {
  int slot = c.slot;
  if (slot < 1) {
    // No slot asked for: take the next free one above the templates in use.
    if (finger.getTemplateCount() == FINGERPRINT_OK) slot = (int)finger.templateCount + 1;
    else slot = 1;
  }
  if (slot < 1 || slot > 999) { failCommand(c.id, "BAD_SLOT"); return; }

  enroll.active = true;
  enroll.step = 0;
  enroll.cmdId = c.id;
  enroll.slot = slot;
  enroll.startedAt = millis();
  enroll.stepAt = millis();
  buzzer.start(1, 60);
  showMessage("ENROL SLOT " + String(slot), "Place finger", ASTRO_CMD_WAIT_MS);
}

void serviceEnroll() {
  if (!enroll.active) return;
  if (millis() - enroll.startedAt > 3UL * ASTRO_CMD_WAIT_MS) { failEnroll("TIMEOUT"); return; }

  switch (enroll.step) {
    case 0:                                  // first impression
      if (finger.getImage() == FINGERPRINT_OK) {
        if (finger.image2Tz(1) == FINGERPRINT_OK) {
          buzzer.start(1, 60);
          showMessage("ENROL SLOT " + String(enroll.slot), "Lift finger", ASTRO_CMD_WAIT_MS);
          enroll.step = 1;
          enroll.stepAt = millis();
        } else {
          failEnroll("BAD_IMAGE");
        }
      } else if (millis() - enroll.stepAt > ASTRO_CMD_WAIT_MS && finger.getImage() == FINGERPRINT_NOFINGER) {
        failEnroll("NO_FINGER");
      }
      break;

    case 1:                                  // wait for the finger to leave
      if (finger.getImage() == FINGERPRINT_NOFINGER) {
        showMessage("ENROL SLOT " + String(enroll.slot), "Place it again", ASTRO_CMD_WAIT_MS);
        enroll.step = 2;
        enroll.stepAt = millis();
      }
      break;

    case 2:                                  // second impression
      if (finger.getImage() == FINGERPRINT_OK) {
        if (finger.image2Tz(2) == FINGERPRINT_OK && finger.createModel() == FINGERPRINT_OK) {
          if (finger.storeModel((uint8_t)enroll.slot) == FINGERPRINT_OK) {
            JsonDocument d;
            d["slot"] = enroll.slot;
            cloud.commandResult(enroll.cmdId, true, d);
            buzzer.start(2, 60);
            showMessage("ENROLLED", "Slot " + String(enroll.slot), 2500);
            Serial.printf("[fp] enrolled slot %d\n", enroll.slot);
            enroll = FpEnroll();
          } else {
            failEnroll("STORE_FAILED");
          }
        } else {
          failEnroll("ENROLL_MISMATCH");
        }
      }
      break;

    default:
      enroll = FpEnroll();
      break;
  }
}
#endif

void handleCommand(const AstroCloud::AstroCommand& c) {
  Serial.printf("[cmd] %s id=%s\n", c.kind.c_str(), c.id.c_str());

  if (c.kind == "lcd_text") {
    // The server has already wrapped the text into two 16-character lines and
    // clamped the hold to 1-30 s, so the LCD just prints what it was given.
    int hold = c.holdSec < 1 ? 1 : (c.holdSec > 30 ? 30 : c.holdSec);
    showMessage(c.line1.length() ? c.line1 : String("HELLO"), c.line2,
                (unsigned long)hold * 1000UL);
    cloud.commandResult(c.id, true);
  } else if (c.kind == "refresh") {
    holdUntil = 0;
    showIdle();
    cloud.commandResult(c.id, true);
  } else if (c.kind == "reboot") {
    cloud.commandResult(c.id, true);
    lcdLine(0, "Rebooting");
    lcdLine(1, "Back in a moment");
    delay(400);          // boot path only: let the LCD finish the write
    ESP.restart();
  } else if (c.kind == "rfid_capture") {
    pendingCapture = c;
    pendingCaptureUntil = millis() + ASTRO_CMD_WAIT_MS;
    buzzer.start(1, 60);
    showMessage("READ A CARD", c.name.length() ? c.name : String("Tap on the reader"),
                ASTRO_CMD_WAIT_MS);
  } else if (c.kind == "fp_check") {
#if ASTRO_USE_FINGERPRINT
    pendingFpCheck = c.id;
    pendingFpUntil = millis() + ASTRO_CMD_WAIT_MS;
    buzzer.start(1, 60);
    showMessage("CHECK A FINGER", "Place on sensor", ASTRO_CMD_WAIT_MS);
#else
    failCommand(c.id, "FP_DISABLED");
#endif
  } else if (c.kind == "fp_enroll") {
#if ASTRO_USE_FINGERPRINT
    startEnroll(c);
#else
    failCommand(c.id, "FP_DISABLED");
#endif
  } else if (c.kind == "fp_delete") {
#if ASTRO_USE_FINGERPRINT
    int slot = c.slot;
    if (slot < 1 || slot > 999) {
      failCommand(c.id, "BAD_SLOT");
    } else if (finger.deleteModel((uint8_t)slot) == FINGERPRINT_OK) {
      JsonDocument d;
      d["slot"] = slot;
      cloud.commandResult(c.id, true, d);
      showMessage("TEMPLATE", "Deleted " + String(slot), 2000);
    } else {
      failCommand(c.id, "DELETE_FAILED");
    }
#else
    failCommand(c.id, "FP_DISABLED");
#endif
  } else {
    failCommand(c.id, "UNKNOWN_KIND");
  }
}

void serviceCommands() {
  if (millis() - lastCmdPollAt < ASTRO_CMD_POLL_MS) return;
  lastCmdPollAt = millis();
  if (!cloud.online()) return;

  AstroCloud::AstroCommand c;
  if (cloud.pollCommand(c) && c.ok) handleCommand(c);

  // A capture that nobody completed still has to be closed out, or the office
  // sits in front of a spinner until the command expires.
  if (pendingCapture.ok && millis() > pendingCaptureUntil) {
    failCommand(pendingCapture.id, "NO_CARD");
    pendingCapture = AstroCloud::AstroCommand();
    holdUntil = 0;
    showIdle();
  }
  if (pendingFpCheck.length() && millis() > pendingFpUntil) {
    failCommand(pendingFpCheck, "NO_FINGER");
    pendingFpCheck = "";
    holdUntil = 0;
    showIdle();
  }
}

// ============================================================================
void setup() {
  Serial.begin(115200);
  delay(150);                       // boot only: let the USB serial settle
  Serial.println("\n=== Astro Smart Attendance ===");

  pinMode(PIN_BUZZER, OUTPUT);
  digitalWrite(PIN_BUZZER, LOW);

#if ASTRO_FP_POWER_PIN >= 0
  // The rev2 PCB switches the fingerprint sensor's supply from a GPIO.
  pinMode(ASTRO_FP_POWER_PIN, OUTPUT);
  digitalWrite(ASTRO_FP_POWER_PIN, HIGH);
  Serial.printf("[fp] power pin %d HIGH\n", ASTRO_FP_POWER_PIN);
#endif

  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
  lcd.init();
  lcd.backlight();
  lcdLine(0, "Astro Attendance");
  lcdLine(1, "Booting...");

  SPI.begin();
  rfid.PCD_Init();
  delay(100);                       // boot only: RC522 needs a moment after reset
  byte rc522Version = rfid.PCD_ReadRegister(MFRC522::VersionReg);
  Serial.printf("[rfid] RC522 version register 0x%02X\n", rc522Version);
  if (rc522Version == 0x00 || rc522Version == 0xFF) {
    Serial.println("[rfid] RC522 NOT responding - check 3V3, GND and the SPI wires");
    lcdLine(0, "RFID ERROR");
    lcdLine(1, "Check RC522");
  }

#if ASTRO_USE_FINGERPRINT
  fingerSerial.setRxBufferSize(2048);            // before begin(), per the sensor's docs
  fingerSerial.begin(57600, SERIAL_8N1, PIN_FINGER_RX, PIN_FINGER_TX);
  finger.begin(57600);
  if (finger.verifyPassword()) {
    finger.getTemplateCount();
    Serial.printf("[fp] R307 OK, %d template(s)\n", finger.templateCount);
  } else {
    Serial.println("[fp] R307 not found");
  }
#endif

  lcdLine(1, "Wi-Fi...");
  bool up = cloud.begin(20000);     // boot only: waits for the first connection

  Serial.printf("[cloud] wifi=%s school=%s late_after=%s\n",
                up ? "UP" : "DOWN", cloud.schoolName().c_str(), cloud.lateAfter().c_str());
  Serial.println("[cmd] polling for dashboard commands every " + String(ASTRO_CMD_POLL_MS) + " ms");
  showMessage(up ? "Connected" : "Offline mode",
              up ? cloud.schoolName().substring(0, 16) : "Will sync later", 1500);
}

// ============================================================================
static unsigned long lastPollAt = 0;

void loop() {
  cloud.loop();                     // heartbeat, queue sync - never blocks
  buzzer.tick();
  serviceCommands();
#if ASTRO_USE_FINGERPRINT
  serviceEnroll();
#endif

  if (holdUntil && millis() > holdUntil) {
    holdUntil = 0;
    showIdle();
  }

  // ------------------------------------------------ serial diagnostics ---
  if (Serial.available()) {
    char c = Serial.read();
    if (c == 'i') {
      Serial.printf("online=%d queue=%d school=%s late_after=%s ip=%s\n",
                    cloud.online(), cloud.pendingEvents(),
                    cloud.schoolName().c_str(), cloud.lateAfter().c_str(),
                    WiFi.localIP().toString().c_str());
    } else if (c == 's') {
      Serial.printf("[cloud] synced %d queued tap(s)\n", cloud.syncQueue());
    } else if (c == 'h') {
      Serial.println(cloud.heartbeat() ? "[cloud] heartbeat OK" : "[cloud] heartbeat FAILED");
    } else if (c == 't') {
      // bench test with the seeded demo card (delete that card before go-live)
      showTapResult(cloud.markRfid("A1B2C3D4"));
    } else if (c == 'c') {
      AstroCloud::AstroCommand cmd;
      if (cloud.pollCommand(cmd) && cmd.ok) handleCommand(cmd);
      else Serial.println("[cmd] nothing queued");
    }
  }

  // Poll the readers on a millis() schedule instead of a delay() at the end of
  // loop(); everything above keeps running while the LCD shows a result.
  const unsigned long now = millis();
  if (now - lastPollAt < 20) return;
  lastPollAt = now;

  // A result is on screen: leave the LCD alone, but keep reading cards.
  const bool showing = holdUntil != 0;

  // ------------------------------------------------------------ RFID -----
  if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
    String uid = uidToHex(&rfid.uid);
    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();

    Serial.println("[rfid] uid=" + uid);
    if (!showing) {
      lcdLine(0, "Checking...");
      lcdLine(1, uid);
    }

    if (pendingCapture.ok) {
      // The office asked for a card to be read; this tap is an enrolment, not
      // attendance, so nothing is marked.
      JsonDocument d;
      d["uid"] = uid;
      bool sent = cloud.commandResult(pendingCapture.id, true, d);
      buzzer.start(sent ? 1 : 2, sent ? 60 : 120);
      showMessage(sent ? "CARD READ" : "SEND FAILED", uid, 2500);
      pendingCapture = AstroCloud::AstroCommand();
    } else {
      showTapResult(cloud.markRfid(uid));
    }
  }

  // ----------------------------------------------------- fingerprint -----
#if ASTRO_USE_FINGERPRINT
  if (!enroll.active && pendingFpCheck.length() == 0 &&
      finger.getImage() == FINGERPRINT_OK &&
      finger.image2Tz() == FINGERPRINT_OK) {
    if (finger.fingerFastSearch() == FINGERPRINT_OK) {
      int id = finger.fingerID;
      Serial.printf("[fp] match id=%d confidence=%d\n", id, finger.confidence);
      if (pendingFpCheck.length()) {
        JsonDocument d;
        d["slot"] = id;
        bool sent = cloud.commandResult(pendingFpCheck, true, d);
        buzzer.start(sent ? 1 : 2, sent ? 60 : 120);
        showMessage(sent ? "FINGER OK" : "SEND FAILED", "Slot " + String(id), 2500);
        pendingFpCheck = "";
      } else {
        if (!showing) {
          lcdLine(0, "Fingerprint OK");
          lcdLine(1, "Checking...");
        }
        showTapResult(cloud.markFingerprint(id));
      }
    } else {
      buzzer.start(2, 90);
      showMessage("Finger not", "registered", 1500);
    }
  }
#else
  // Keep fp_check answers honest when the sensor is not enabled.
  if (pendingFpCheck.length() && millis() > pendingFpUntil) {
    pendingFpCheck = "";
  }
#endif
}
