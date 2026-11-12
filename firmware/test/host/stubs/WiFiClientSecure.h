#pragma once
#include <Arduino.h>
class WiFiClient {};
class WiFiClientSecure : public WiFiClient {
 public:
  void setInsecure() {}
  void setCACert(const char*) {}
  void setTimeout(unsigned long) {}
};
