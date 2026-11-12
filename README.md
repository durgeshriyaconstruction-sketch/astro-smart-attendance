# 🎯 Astro Smart Attendance

### AI + IoT + Cloud Smart School Attendance System

**Built by Team Sun Rises India | Class 9 | Renukoot, Uttar Pradesh, India**

---

## The Problem
Indian schools waste 10-15 minutes per class on manual attendance. 
Over 15 Lakh schools in India face this problem daily. Records, 
parent alerts and reports remain disconnected.

## Our Solution
A compact ESP32-based RFID attendance terminal with AI self-healing, 
Firebase Cloud dashboard, and automatic parent email alerts. 
Cost: Only 1,500 Rupees per unit.

## Technologies Used
- ESP32 DevKit V1
- RC522 RFID Module
- LCD1602 I2C Display
- Supabase (Postgres + Auth + REST) — live
- Firebase (legacy device firmware + old dashboard, being retired — see
  [docs/firebase_to_supabase.md](docs/firebase_to_supabase.md))
- Astro AI 2.0 (Self-healing diagnostics)
- 3D Printed Enclosure (Blender)
- Arduino C++ and HTML/CSS/JavaScript

## Filing everything as year → month → day

Attendance, notices, messages, the e-mails a guardian received and the leave
records can be written out as ordinary folders — `2026/11/2026-11-12.json` plus a
`.csv` sheet per day — with one command that reads through the same security the
dashboard uses:
[`tools/archive`](tools/archive/README.md). Those files — plus a full `pg_dump`
of the database — can be pushed every night into your own Google Drive or
OneDrive with [`tools/backup`](tools/backup/README.md); Supabase itself has no
link to either drive. A live copy also sits in Google Drive, written through the
Drive connection — see [`docs/google_drive_backup.md`](docs/google_drive_backup.md).

## Cloud backend (Supabase)
The attendance terminal talks to Postgres through four locked-down functions
(`astro_heartbeat`, `astro_mark_attendance`, `astro_sync_batch`,
`astro_lookup_card`). It carries only the publishable key, which cannot read a
single table, and every tap is idempotent so an offline queue can be replayed
safely.

Notices and one-to-one messages are posted by staff
(`astro_post_notice`, `astro_send_message`) and land instantly in the student's
app because both read the same tables; the same trigger writes one row per
guardian into the `alerts` outbox, which [`services/mailer`](services/mailer/README.md)
delivers by email.

- Backend design + operations: [`docs/supabase_setup.md`](docs/supabase_setup.md)
- Email delivery worker: [`services/mailer/README.md`](services/mailer/README.md)
- Firmware: [`firmware/README.md`](firmware/README.md)
- What to paste into `main.cpp`: [`docs/main_cpp_additions.md`](docs/main_cpp_additions.md)
- Schema/migrations: [`supabase/migrations/`](supabase/migrations/)

## Live Demo
Cloud Dashboard: https://astro-smart-attendence.web.app

## Validation
- 140 out of 140 Feature Tests Passing
- 10,000,000 Stress Test Cases Verified
- 0 Warnings, 0 Errors
- Working Prototype Ready

## Cost
1,500 Rupees per unit (95% cheaper than commercial systems)

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
3. Tejash Upadhyaye - Hardware Integration and Circuit Testing
4. Diwakar Singh - Product Design and 3D Enclosure
5. Devansh Dakard - Testing, Documentation and Presentation

## Mentor
Dr. Jayesh Shinde - The Aditya Birla Public School, Renukoot

## Contact
Location: Renukoot, Sonbhadra, Uttar Pradesh, India

---
Made in Renukoot, India
Team Sun Rises India - STEM 2026-27
