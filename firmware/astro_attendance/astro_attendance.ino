// ============================================================================
//  Astro Smart Attendance — complete reference firmware
//  ESP32 DevKit V1 + RC522 + LCD1602 (I2C) + 3010 fan + optional R307
//
//  This is the whole terminal in one file, written around astro_cloud.h, so you
//  can either:
//     (a) flash this sketch as-is, or
//     (b) copy the marked blocks into your existing main.cpp
//         (see docs/main_cpp_additions.md)
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

#define ASTRO_USE_FINGERPRINT 0        // set 1 once the R307 is wired and enrolled

#if ASTRO_USE_FINGERPRINT
#include <Adafruit_Fingerprint.h>
HardwareSerial fingerSerial(2);
Adafruit_Fingerprint finger(&fingerSerial);
#endif

// ---------------------------------------------------------------- pins -----
// Change these three lines if your wiring differs; everything else follows.
#define PIN_RC522_SS   5
#define PIN_RC522_RST  27
#define PIN_I2C_SDA    21
#define PIN_I2C_SCL    22
#define PIN_BUZZER     25
#define PIN_FINGER_RX  16              // ESP32 RX2  <- R307 TX (yellow)
#define PIN_FINGER_TX  17              // ESP32 TX2  -> R307 RX (white)

LiquidCrystal_I2C lcd(0x27, 16, 2);
MFRC522           rfid(PIN_RC522_SS, PIN_RC522_RST);
AstroCloud        cloud;

// --------------------------------------------------------------- helpers ---
void lcdLine(uint8_t row, const String& text) {
  lcd.setCursor(0, row);
  String t = text;
  while (t.length() < 16) t += ' ';
  lcd.print(t.substring(0, 16));
}

void beep(uint8_t times, uint16_t ms) {
  for (uint8_t i = 0; i < times; i++) {
    tone(PIN_BUZZER, 2200, ms);
    delay(ms + 60);
  }
  noTone(PIN_BUZZER);
}

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
  if (cloud.online()) {
    lcdLine(0, "Tap card / finger");
    lcdLine(1, String("Online  Q:") + cloud.pendingEvents());
  } else {
    lcdLine(0, "OFFLINE MODE");
    lcdLine(1, String("Saved: ") + cloud.pendingEvents());
  }
}

// Print any AstroTapResult on the LCD for ~1.8 s, then return to idle.
void showTapResult(const AstroTapResult& r) {
  if (r.offline) {
    beep(2, 120);
    lcdLine(0, "SAVED OFFLINE");
    lcdLine(1, "Syncs when online");
  } else if (r.marked || r.duplicate) {
    beep(1, 60);
    lcdLine(0, r.name);
    String line2 = r.status + " " + r.timeText;
    if (r.duplicate) line2 += " dup";
    if (r.className.length()) line2 += " " + r.className;
    lcdLine(1, line2);
  } else if (r.code == "UNKNOWN_CARD") {
    beep(3, 80);
    lcdLine(0, "CARD NOT");
    lcdLine(1, "REGISTERED");
  } else {
    beep(2, 150);
    lcdLine(0, "CLOUD ERROR");
    lcdLine(1, r.code);
  }

  Serial.printf("[tap] code=%s status=%s name=%s roll=%s class=%s time=%s msg=%s\n",
                r.code.c_str(), r.status.c_str(), r.name.c_str(), r.roll.c_str(),
                r.className.c_str(), r.timeText.c_str(), r.message.c_str());

  delay(1800);
  showIdle();
}

// ============================================================================
void setup() {
  Serial.begin(115200);
  delay(150);
  Serial.println("\n=== Astro Smart Attendance ===");

  pinMode(PIN_BUZZER, OUTPUT);
  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);

  lcd.init();
  lcd.backlight();
  lcdLine(0, "Astro Attendance");
  lcdLine(1, "Booting...");

  SPI.begin();
  rfid.PCD_Init();
  delay(100);
  byte rc522Version = rfid.PCD_ReadRegister(MFRC522::VersionReg);
  Serial.printf("[rfid] RC522 version register 0x%02X\n", rc522Version);
  if (rc522Version == 0x00 || rc522Version == 0xFF) {
    Serial.println("[rfid] RC522 NOT responding - check 3V3, GND and the SPI wires");
    lcdLine(0, "RFID ERROR");
    lcdLine(1, "Check RC522");
  }

#if ASTRO_USE_FINGERPRINT
  fingerSerial.begin(57600, SERIAL_8N1, PIN_FINGER_RX, PIN_FINGER_TX);
  finger.begin(57600);
  if (finger.verifyPassword()) Serial.println("[fp] R307 OK");
  else                          Serial.println("[fp] R307 not found");
#endif

  lcdLine(1, "Wi-Fi...");
  bool up = cloud.begin(20000);

  lcdLine(0, up ? "Connected" : "Offline mode");
  lcdLine(1, up ? cloud.schoolName().substring(0, 16) : "Will sync later");
  Serial.printf("[cloud] wifi=%s school=%s late_after=%s\n",
                up ? "UP" : "DOWN", cloud.schoolName().c_str(), cloud.lateAfter().c_str());
  delay(1500);
  showIdle();
}

// ============================================================================
void loop() {
  cloud.loop();

  // ------------------------------------------------------------ RFID -----
  if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
    String uid = uidToHex(&rfid.uid);
    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();

    Serial.println("[rfid] uid=" + uid);
    lcdLine(0, "Checking...");
    lcdLine(1, uid);

    AstroTapResult r = cloud.markRfid(uid);
    showTapResult(r);
  }

  // ----------------------------------------------------- fingerprint -----
#if ASTRO_USE_FINGERPRINT
  if (finger.getImage() == FINGERPRINT_OK &&
      finger.image2Tz() == FINGERPRINT_OK) {
    int id = 0;
    if (finger.fingerFastSearch() == FINGERPRINT_OK) {
      id = finger.fingerID;
      Serial.printf("[fp] match id=%d confidence=%d\n", id, finger.confidence);
      lcdLine(0, "Fingerprint OK");
      lcdLine(1, "Checking...");
      showTapResult(cloud.markFingerprint(id));
    } else {
      beep(2, 90);
      lcdLine(0, "Finger not");
      lcdLine(1, "registered");
      delay(1500);
      showIdle();
    }
  }
#endif

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
    }
  }

  delay(40);
}
