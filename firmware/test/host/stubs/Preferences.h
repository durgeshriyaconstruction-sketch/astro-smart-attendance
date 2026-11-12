#pragma once
#include <Arduino.h>
#include <map>
#include <string>

// Backed by a real map so queue persistence can be exercised across instances.
struct PrefStore {
  static std::map<std::string, std::map<std::string, std::string>>& strs();
};

class Preferences {
 public:
  bool begin(const char* name, bool = false) { ns_ = name; return true; }
  int getInt(const char* key, int def = 0) {
    auto& m = PrefStore::strs()[ns_];
    auto it = m.find(key);
    return it == m.end() ? def : atoi(it->second.c_str());
  }
  String getString(const char* key, const String& def = String()) {
    auto& m = PrefStore::strs()[ns_];
    auto it = m.find(key);
    return it == m.end() ? def : String(it->second.c_str());
  }
  size_t putInt(const char* key, int v) { PrefStore::strs()[ns_][key] = std::to_string(v); return 1; }
  size_t putString(const char* key, const String& v) { PrefStore::strs()[ns_][key] = v.c_str(); return 1; }
  bool isKey(const char* key) { auto& m = PrefStore::strs()[ns_]; return m.count(key) > 0; }
  bool remove(const char* key) { PrefStore::strs()[ns_].erase(key); return true; }
 private:
  std::string ns_ = "default";
};
