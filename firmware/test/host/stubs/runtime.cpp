#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <esp_system.h>
#include <Preferences.h>
#include <map>
#include <string>

SerialStub Serial;
WiFiClass WiFi;
int g_wifiStatus = WL_CONNECTED;
int HttpStub::nextCode = 200;
String HttpStub::nextBody;
String HttpStub::lastBody;
String HttpStub::lastUrl;
String HttpStub::lastHeaders;

std::map<std::string, std::map<std::string, std::string>>& PrefStore::strs() {
  static std::map<std::string, std::map<std::string, std::string>> m;
  return m;
}

unsigned long millis() { static unsigned long t = 0; return t += 1000; }
void delay(unsigned long) {}
void pinMode(uint8_t, uint8_t) {}
void tone(uint8_t, unsigned int, unsigned long) {}
void noTone(uint8_t) {}
void configTime(long, int, const char*, const char*, const char*) {}
uint32_t esp_random() { static uint32_t x = 0x12345678; x ^= x << 13; x ^= x >> 17; x ^= x << 5; return x; }
