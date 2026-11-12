#pragma once
#include <Arduino.h>

#ifndef SERIAL_8N1
#define SERIAL_8N1 0x800001c
#endif

// Mirrors the ESP32 core's HardwareSerial closely enough to type-check a sketch.
class HardwareSerial : public Stream {
 public:
  explicit HardwareSerial(int uart) { (void)uart; }
  void setRxBufferSize(size_t) {}
  void begin(unsigned long, uint32_t = SERIAL_8N1, int8_t = -1, int8_t = -1) {}
  void end() {}
  int available() override { return 0; }
  int read() override { return -1; }
  size_t write(uint8_t b) override { (void)b; return 1; }
  using Print::write;
};
