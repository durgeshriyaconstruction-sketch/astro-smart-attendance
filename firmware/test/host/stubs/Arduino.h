#pragma once
// Minimal host-side stand-ins for the ESP32 Arduino core, written to match the
// documented signatures of the real headers. Used only to type-check our code.
#include <cstdint>
#include <cstddef>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <cmath>
#include <string>

#ifndef ARDUINO
#define ARDUINO 100
#endif
#define PROGMEM
#define PSTR(s) (s)
#define FPSTR(p) (p)
typedef const char* PGM_P;
static inline unsigned char pgm_read_byte(const void* a) { return *static_cast<const unsigned char*>(a); }

typedef uint8_t byte;
typedef bool boolean;

#define HEX 16
#define DEC 10
#define OCT 8
#define BIN 2
#define OUTPUT 0x03
#define INPUT 0x01
#define INPUT_PULLUP 0x05
#define HIGH 1
#define LOW 0

class __FlashStringHelper;
#define F(s) (reinterpret_cast<const __FlashStringHelper*>(s))
#ifndef strlen_P
#define strlen_P strlen
#endif
#ifndef pgm_read_ptr
#define pgm_read_ptr(a) (*(void* const*)(a))
#endif

class Print {
 public:
  virtual size_t write(uint8_t) = 0;
  virtual size_t write(const uint8_t* b, size_t n) { for (size_t i = 0; i < n; i++) write(b[i]); return n; }
  int print(const char* s) { while (*s) write((uint8_t)*s++); return 0; }
  int println(const char* s = "") { print(s); write('\n'); return 0; }
  virtual ~Print() {}
};

class Stream : public Print {
 public:
  virtual int available() = 0;
  virtual int read() = 0;
  size_t readBytes(uint8_t* buf, size_t len) {
    size_t n = 0;
    while (n < len && available()) { int c = read(); if (c < 0) break; buf[n++] = (uint8_t)c; }
    return n;
  }
  size_t readBytes(char* buf, size_t len) { return readBytes(reinterpret_cast<uint8_t*>(buf), len); }
};

class Printable {
 public:
  virtual size_t printTo(Print& p) const = 0;
  virtual ~Printable() {}
};

class String {
 public:
  String() {}
  String(const char* s) : s_(s ? s : "") {}
  String(const std::string& s) : s_(s) {}
  String(char c) : s_(1, c) {}
  String(int v) : s_(std::to_string(v)) {}
  String(unsigned int v) : s_(std::to_string(v)) {}
  String(long v) : s_(std::to_string(v)) {}
  String(unsigned long v) : s_(std::to_string(v)) {}
  String(int v, int base) { char b[34]; snprintf(b, sizeof b, base == 16 ? "%x" : "%d", v); s_ = b; }

  const char* c_str() const { return s_.c_str(); }
  const char* data() const { return s_.data(); }
  unsigned int length() const { return (unsigned int)s_.size(); }
  bool concat(const char* s) { s_ += (s ? s : ""); return true; }
  bool concat(const String& s) { s_ += s.s_; return true; }

  String& operator=(const char* s) { s_ = s ? s : ""; return *this; }
  String& operator=(const String& s) { s_ = s.s_; return *this; }
  String& operator+=(const char* s) { s_ += (s ? s : ""); return *this; }
  String& operator+=(const String& s) { s_ += s.s_; return *this; }
  String& operator+=(char c) { s_ += c; return *this; }
  String& operator+=(int v) { s_ += std::to_string(v); return *this; }

  bool operator==(const char* s) const { return s_ == (s ? s : ""); }
  bool operator==(const String& s) const { return s_ == s.s_; }
  bool operator!=(const char* s) const { return !(*this == s); }

  String substring(unsigned int from, unsigned int to) const {
    if (from > s_.size()) return String();
    if (to > s_.size()) to = (unsigned int)s_.size();
    if (to < from) to = from;
    return String(s_.substr(from, to - from));
  }
  String substring(unsigned int from) const { return substring(from, (unsigned int)s_.size()); }
  void toUpperCase() { for (auto& c : s_) c = (char)toupper((unsigned char)c); }
  void toLowerCase() { for (auto& c : s_) c = (char)tolower((unsigned char)c); }
  bool endsWith(const char* suffix) const {
    size_t n = strlen(suffix ? suffix : "");
    return s_.size() >= n && s_.compare(s_.size() - n, n, suffix ? suffix : "") == 0;
  }
  bool startsWith(const char* prefix) const { return s_.rfind(prefix ? prefix : "", 0) == 0; }
  char operator[](unsigned int i) const { return i < s_.size() ? s_[i] : '\0'; }
  char& operator[](unsigned int i) { return s_[i]; }

 private:
  std::string s_;
};

inline String operator+(const String& a, const String& b) { String r(a); r += b; return r; }
inline String operator+(const String& a, const char* b) { String r(a); r += b; return r; }
inline String operator+(const char* a, const String& b) { String r(a); r += b; return r; }
inline String operator+(const String& a, char b) { String r(a); r += b; return r; }
inline String operator+(const String& a, int b) { String r(a); r += b; return r; }

struct SerialStub {
  void begin(unsigned long) {}
  int available() { return 0; }
  int read() { return -1; }
  void print(const String&) {}
  void print(const char*) {}
  void println(const String&) {}
  void println(const char*) {}
  void println() {}
  int printf(const char*, ...) { return 0; }
};
extern SerialStub Serial;

unsigned long millis();
void delay(unsigned long ms);
void pinMode(uint8_t pin, uint8_t mode);
void tone(uint8_t pin, unsigned int freq, unsigned long duration = 0);
void noTone(uint8_t pin);
void configTime(long gmtOffsetSec, int daylightOffsetSec, const char* s1, const char* s2 = nullptr, const char* s3 = nullptr);
