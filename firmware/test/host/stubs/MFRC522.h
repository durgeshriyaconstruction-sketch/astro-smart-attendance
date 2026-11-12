#pragma once
#include <Arduino.h>
class MFRC522 {
 public:
  struct Uid { byte size; byte uidByte[10]; };
  enum PCD_Register { VersionReg = 0x37, CommandReg = 0x01 };
  enum StatusCode { STATUS_OK = 1 };
  MFRC522(byte ss, byte rst) { (void)ss; (void)rst; }
  void PCD_Init() {}
  byte PCD_ReadRegister(byte) { return 0x92; }
  bool PCD_PerformSelfTest() { return true; }
  bool PICC_IsNewCardPresent() { return false; }
  bool PICC_ReadCardSerial() { return false; }
  void PICC_HaltA() {}
  void PCD_StopCrypto1() {}
  Uid uid;
};
