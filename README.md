# 🎯 Astro Smart Attendance

### AI + IoT + Cloud Smart School Attendance System

**Built by Team Sun Rises India | Class 9 | Renukoot, Uttar Pradesh, India**

---

## The Problem
Indian schools waste 10-15 minutes per class on manual attendance. 
Over 15 Lakh schools in India face this problem daily. Records, 
parent alerts and reports remain disconnected.

## Our Solution
A compact ESP32-based RFID + fingerprint attendance terminal with AI self-healing, 
Firebase Cloud dashboard, and automatic parent email alerts. A student taps a card and 
presses a finger, so a borrowed card alone cannot mark attendance. 
Cost: about 2,450 Rupees per unit, including the fingerprint sensor.

## Technologies Used
- ESP32 DevKit V1
- RC522 RFID Module
- R307 Fingerprint Sensor (second factor)
- LCD1602 I2C Display
- Firebase (Auth + Realtime Database + Hosting)
- Astro AI 2.0 (Self-healing diagnostics)
- 3D Printed Enclosure (Blender)
- Arduino C++ and HTML/CSS/JavaScript

## Live Demo
Cloud Dashboard: https://astro-smart-attendence.web.app

## Validation
- 140 out of 140 Feature Tests Passing
- 10,000,000 Stress Test Cases Verified
- 0 Warnings, 0 Errors
- Working Prototype Ready

## Cost
2,450 Rupees per unit (about 90% cheaper than commercial systems)

## Key Features
- Works OFFLINE and syncs when internet returns
- Astro AI 2.0 with 11 self-healing diagnostic checks
- Daily and Period attendance tracking
- Admin and Student dashboards
- Automatic parent email alerts for late or absent
- Secure OTA firmware updates
- 3D printable product enclosure
- Role-based access (Admin, Student, Guardian)

## Team Sun Rises India
1. Shaurya Gupta - Team Lead, Firmware and Cloud Developer
2. Anant Tiwari - Ideation and User Research Lead
3. Tejas Upadhyay - Hardware Integration and Circuit Testing
4. Diwakar Singh - Product Design and 3D Enclosure
5. Devansh Dhakad - Testing, Documentation and Presentation

## Mentor
Dr. Jayesh Shinde - The Aditya Birla Public School, Renukoot

## Contact
Location: Renukoot, Sonbhadra, Uttar Pradesh, India

---

## Part 1 — Creative Ideation Worksheet

The ideation worksheet for ABG STEM Quest 2026-27 is published in two matching editions,
built from the same design system (navy, saffron, teal, gold, hand script, sticker doodles):

| Edition | File |
| --- | --- |
| Print edition (8 pages, PDF) | `Creative-Ideation-Worksheet-Astro-Smart-Attendance.pdf` |
| Editable edition (10 pages, Word) | `Creative-Ideation-Worksheet-Astro-Smart-Attendance.docx` |
| Format audit (36 checks, both files) | `Format-Compliance-Check.pdf` |

It follows the nine-part format exactly — problem focus, brainstormed possibilities, concept
map, shortlisting matrix, selected concept and reason, initial system sketch, validation plan,
success indicators, risks and safeguards — plus the team reflection prompts.

Everything in it is a **proposal**: costs are estimates, indicator targets are targets, and
every number is labelled as measured or as a hypothesis. No part of it claims the build is done.

### Rebuilding

```
python3 -m venv .venv && .venv/bin/pip install reportlab pypdf pypdfium2 python-docx pillow fonttools brotli
.venv/bin/python scripts/make_stickers.py      # regenerate the hand-drawn accent PNGs
.venv/bin/python scripts/build_worksheet.py    # -> PDF
.venv/bin/python scripts/build_docx.py         # -> DOCX
.venv/bin/python scripts/estimate_docx.py      # page-fit check, exits 1 on overflow
.venv/bin/python scripts/verify_format.py      # 36-requirement audit of both files
.venv/bin/python scripts/build_format_check.py # -> Format-Compliance-Check.pdf
```

---
Made in Renukoot, India
Team Sun Rises India - STEM 2026-27
