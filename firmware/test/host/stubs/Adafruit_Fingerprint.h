#pragma once
#include <Arduino.h>
#include <HardwareSerial.h>

// The real library defines these; the sketch only needs the handful it uses.
#ifndef FINGERPRINT_OK
#define FINGERPRINT_OK 0x00
#endif
#ifndef FINGERPRINT_NOFINGER
#define FINGERPRINT_NOFINGER 0x02
#endif
#ifndef FINGERPRINT_NOTFOUND
#define FINGERPRINT_NOTFOUND 0x09
#endif
#ifndef FINGERPRINT_ENROLLMISMATCH
#define FINGERPRINT_ENROLLMISMATCH 0x0A
#endif

class Adafruit_Fingerprint {
 public:
  explicit Adafruit_Fingerprint(Stream* serial) { (void)serial; }

  bool    begin(uint32_t baud) { (void)baud; return true; }
  bool    verifyPassword() { return true; }
  uint8_t getImage() { return FINGERPRINT_NOFINGER; }
  uint8_t image2Tz(uint8_t slot = 1) { (void)slot; return FINGERPRINT_OK; }
  uint8_t createModel() { return FINGERPRINT_OK; }
  uint8_t storeModel(uint16_t location) { (void)location; return FINGERPRINT_OK; }
  uint8_t deleteModel(uint16_t location) { (void)location; return FINGERPRINT_OK; }
  uint8_t getTemplateCount() { return FINGERPRINT_OK; }
  uint8_t fingerFastSearch() { return FINGERPRINT_OK; }

  uint16_t fingerID = 0;
  uint16_t confidence = 0;
  uint16_t templateCount = 0;
};
