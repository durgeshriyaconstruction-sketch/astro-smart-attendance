# Astro Smart Attendance — website

This folder is what the web host serves (Firebase Hosting, `firebase.json` → `web/`).

| File | What it is |
|---|---|
| `index.html` | the Astro dashboard (v26.11.7 · UI v3.3R), the same app the ESP32 serves, plus a handful of small edits made by `tools/patch_web_index.py` |
| `supabase-bridge.js` | makes that dashboard read and write the school's Supabase database |

No build step, no CDN, no other assets.

## How it works

The dashboard asks `/api/...` for everything. On the gate device the firmware
answers. On the website `supabase-bridge.js` answers instead: it is loaded
before the app, intercepts the app's own `fetch` calls to `/api/*`, and serves
them from Supabase in the JSON shapes the firmware uses. No `/api` request
reaches the web host, and the app's built-in pretend database is never used.

- **Sign in** — Supabase Auth, staff email + password. The account must be a
  staff member of the school (`members` table). Student sign-in exists on the
  device only; the database holds no student passwords.
- **Reading** — one call, `astro_web_bundle`, returns the school, classes,
  students, cards, about 100 days of attendance, holidays, notices, leave
  requests and messages. It is polled every 8 seconds while the tab is visible
  and returns "unchanged" when nothing moved, so a card tapped at the gate
  shows up on the dashboard within about 10 seconds.
- **Writing** — the staff functions already in the database:
  `astro_save_student`, `astro_save_class`, `astro_web_remove_student`,
  `astro_unassign_card`, `astro_set_attendance`, `astro_post_notice`,
  `astro_web_update_notice`, `astro_delete_notice`, `astro_set_holiday`,
  `astro_remove_holiday`, `astro_decide_leave`, `astro_send_message`,
  `astro_delete_message`, `astro_update_settings`.

The three `astro_web_*` functions come from
`supabase/migrations/20261114000004_web_dashboard_rpc.sql`. All of them are for
signed-in staff only; the public key in `supabase-bridge.js` cannot call them
(`20261114000003_lock_down_anon_rpc.sql`).

## What works on the website

| In the app | What happens |
|---|---|
| Students → **Add Student** | saved to `students` (+ `rfid_cards`). The card number is typed; leave it blank or press **Auto** for a placeholder card (`A5……`) and replace it later. Roll numbers start at 1001. A class that does not exist yet is created. |
| Student → edit / change card / delete | edit and card change are saved. Delete removes a student who has no attendance; one with attendance is archived so the history stays. |
| Attendance → manual marks | `astro_set_attendance` |
| Notices, holidays, leave decisions, messages | saved |
| Settings → timings and weekly off | saved to the school row |

## What stays on the device

The website cannot reach the hardware, and says so instead of pretending:

- scanning a card to read its number, fingerprint enrolment, LCD/buzzer tests,
  Wi-Fi setup, firmware update, backups — these answer "use the school device"
- student sign-in names and passwords
- hardware readings (heap, temperature, storage, signal). The cloud only knows
  when the device last checked in; the device light is **online** when that was
  within the last 90 seconds.

## Updating `index.html` from a new device build

```bash
cp Astro.html web/index.html
python3 tools/patch_web_index.py web/index.html     # safe to run twice
```

The script stops with an error if a place it needs to edit is not found.

## Testing

```bash
cd tools/e2e
npm install
npm test                      # SHOTS=/tmp/shots npm test  also saves screenshots
```

This opens the real page in headless Chromium and drives it against
`fake_supabase.mjs`, an in-memory stand-in for the Supabase project: sign-in,
add / edit / delete student, card rules, attendance, a simulated gate scan,
token refresh, notices, messages, settings, sign-out. The stand-in refuses
calls whose argument names do not match the real database functions.

It does not talk to the real project. After changing a database function,
check the real thing as well.

## Publishing to https://astro-smart-attendence.web.app

**Automatic.** `.github/workflows/deploy-website.yml` publishes `web/` on every
push to `main` and to the working branch `arena/5084b081-astro-smart-attendance`,
then checks that the live site really serves the new files. It needs one
repository secret, added once:

- name: `FIREBASE_SERVICE_ACCOUNT`
- value: the whole JSON key file from Firebase console → Project settings →
  Service accounts → **Generate new private key**
- where: GitHub → Settings → Secrets and variables → Actions → New repository secret

Without the secret the run stops with "Not published" and changes nothing.

**By hand**, from a computer with Node.js:

```bash
npx firebase-tools login
npx firebase-tools deploy --only hosting
```

`firebase.json` names the Hosting site (`astro-smart-attendence`) and has no
rewrites on purpose: the dashboard's `/api/...` calls are answered in the browser
by `supabase-bridge.js`, and a catch-all rewrite to `index.html` would hide a
missing `supabase-bridge.js` behind a 200 OK page.

## Before real student data goes in

The sign-in page prints the admin email and password (`astro@gmail.com` /
`admin123`), and this repository is public. That login now opens the real
database. Change the password in Supabase (Authentication → Users) and remove
the hint from `index.html`.
