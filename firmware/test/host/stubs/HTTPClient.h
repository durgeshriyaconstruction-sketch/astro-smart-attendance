#pragma once
#include <Arduino.h>
#include <WiFiClientSecure.h>

// Test control: set nextCode / nextBody before a call, inspect last* after it.
struct HttpStub {
  static int    nextCode;
  static String nextBody;
  static String lastBody;
  static String lastUrl;
  static String lastHeaders;
};

class HTTPClient {
 public:
  bool begin(WiFiClient&, const String& url) { HttpStub::lastUrl = url; return true; }
  void addHeader(const String& n, const String& v) { HttpStub::lastHeaders += n + ": " + v + "\n"; }
  int POST(const String& payload) { HttpStub::lastBody = payload; return HttpStub::nextCode; }
  String getString() { return HttpStub::nextBody; }
  void end() {}
  void setConnectTimeout(int) {}
  void setTimeout(int) {}
};
