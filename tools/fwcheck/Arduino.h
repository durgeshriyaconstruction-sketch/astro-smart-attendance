// Minimal stand-in for the parts of Arduino's String / Serial / WiFi that the
// changed firmware lines use. Only for a host-side compile + behaviour check.
#pragma once
#include <string>
#include <cstdint>
#include <cstdio>
#include <cctype>
class String {
  std::string s_;
 public:
  String() {}
  String(const char* c) : s_(c ? c : "") {}
  String(const String& o) : s_(o.s_) {}
  explicit String(int v) : s_(std::to_string(v)) {}
  explicit String(unsigned int v) : s_(std::to_string(v)) {}
  explicit String(long v) : s_(std::to_string(v)) {}
  explicit String(unsigned long v) : s_(std::to_string(v)) {}
  String& operator=(const String& o) { s_ = o.s_; return *this; }
  String& operator=(const char* c) { s_ = c ? c : ""; return *this; }
  size_t length() const { return s_.size(); }   // size_t on this 64-bit host; unsigned int == size_t on the ESP32
  const char* c_str() const { return s_.c_str(); }
  char charAt(unsigned int i) const { return i < s_.size() ? s_[i] : 0; }
  char operator[](unsigned int i) const { return charAt(i); }
  bool operator==(const String& o) const { return s_ == o.s_; }
  bool operator==(const char* c) const { return s_ == (c ? c : ""); }
  bool operator!=(const String& o) const { return s_ != o.s_; }
  bool operator!=(const char* c) const { return s_ != (c ? c : ""); }
  bool concat(const char* c) { if (c) s_ += c; return true; }
  bool concat(const String& o) { s_ += o.s_; return true; }
  bool concat(char c) { s_ += c; return true; }
  bool reserve(unsigned int n) { s_.reserve(n); return true; }
  String& operator+=(const String& o) { s_ += o.s_; return *this; }
  String& operator+=(const char* c) { if (c) s_ += c; return *this; }
  void trim() { size_t a = 0, b = s_.size(); while (a < b && isspace((unsigned char)s_[a])) a++; while (b > a && isspace((unsigned char)s_[b - 1])) b--; s_ = s_.substr(a, b - a); }
  void toUpperCase() { for (auto& ch : s_) ch = (char)toupper((unsigned char)ch); }
  friend String operator+(const String& a, const String& b) { String r(a); r.s_ += b.s_; return r; }
  friend String operator+(const String& a, const char* b) { String r(a); if (b) r.s_ += b; return r; }
  friend String operator+(const char* a, const String& b) { String r(a); r.s_ += b.s_; return r; }
};
struct SerialStub { void println(const String& s) { printf("    [serial] %s\n", s.c_str()); } };
extern SerialStub Serial;
struct IPAddressStub { String toString() const { return String("192.168.1.37"); } };
struct WiFiStub { int8_t RSSI() { return -61; } IPAddressStub localIP() { return IPAddressStub(); } };
extern WiFiStub WiFi;
unsigned long millis();
