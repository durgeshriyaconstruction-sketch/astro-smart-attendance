#pragma once
#include <cstdint>
uint32_t esp_random();

struct EspClass {
  void restart();
};
extern EspClass ESP;
