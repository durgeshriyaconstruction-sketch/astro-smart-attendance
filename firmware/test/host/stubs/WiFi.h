#pragma once
#include <Arduino.h>
#define WL_CONNECTED 3
#define WL_IDLE_STATUS 0
#define WIFI_STA 1
#define WIFI_OFF 0

extern int g_wifiStatus;   // test control

class IPAddress {
 public:
  String toString() const { return String("192.168.1.50"); }
};

class WiFiClass {
 public:
  void persistent(bool) {}
  void mode(int) {}
  void setAutoReconnect(bool) {}
  int begin(const char*, const char*) { return 0; }
  int status() { return g_wifiStatus; }
  bool disconnect(bool = false, bool = false) { return true; }
  IPAddress localIP() { return IPAddress(); }
  int8_t RSSI() { return -55; }
};
extern WiFiClass WiFi;
