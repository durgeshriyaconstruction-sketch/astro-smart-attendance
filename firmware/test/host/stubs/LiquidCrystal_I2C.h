#pragma once
#include <Arduino.h>
class LiquidCrystal_I2C {
 public:
  LiquidCrystal_I2C(uint8_t addr, uint8_t cols, uint8_t rows) { (void)addr; (void)cols; (void)rows; }
  void init() {}
  void begin() {}
  void backlight() {}
  void clear() {}
  void setCursor(uint8_t, uint8_t) {}
  void print(const String&) {}
  void print(const char*) {}
  void print(int) {}
};
