# Astro Smart Attendance — web front end

This folder is what Firebase Hosting serves. It currently holds **one file**:

| File | What it is |
|---|---|
| `index.html` | the full Astro app, v26.11.7 · UI v3.3R — 717 KB, completely self-contained (no CDN, no build step, no external assets) |

It is the same application the ESP32 serves at `192.168.4.1`, packaged so it runs
in a normal browser. Uploaded by the project owner and installed verbatim.

## How it works without the ESP32

The app talks to `/api/...` endpoints. On the device those are answered by the
firmware. On a static host they would 404 — so the file carries its own
`localApiFallback()`, which answers every one of those routes in the browser from
an in-memory database, persisted to `localStorage`.

That is why the deployed site works with no hardware attached. It also means:

> **The data on screen is browser-local — not your Supabase database.**
> Students, attendance, notices and device telemetry are held in `localStorage`.
> Nothing is read from or written to Supabase in this build.
>
> The demo seed (18 students, 35 days of attendance, sample notices/leaves/
> messages) has been **emptied** (`NAMES=[]` and friends), so the app now starts
> with a genuinely empty school. Adding a student in the app writes to this
> browser only — it is not yet visible to the ESP32 or to other devices.

## Signing in

| Role | Credentials |
|---|---|
| Admin | `astro@gmail.com` / `admin123` |
| Student | any seeded name, e.g. `Shaurya Gupta` / `1001` (1001–1018) |

Both are checked in the browser (`doLogin()` / `localApiFallback('/api/login')`),
not against a server.

## Deploying

```bash
npm i -g firebase-tools
firebase login
firebase use --add          # pick the existing project
firebase deploy --only hosting
```

To preview without touching the live site:

```bash
firebase hosting:channel:deploy test
```

## Real data: `supabase-bridge.js`

The app asks `/api/...` for everything. `supabase-bridge.js` (loaded after the
app) replaces those answers with the live Supabase database, and replaces the
fake login with real Supabase Auth.

| Route | Now served by |
|---|---|
| `POST /api/login` | Supabase Auth — email + password, or a student's full name via `resolve_login_email` |
| `GET /api/students` | `students` + `classes` + `rfid_cards` + `attendance` |
| `GET /api/calendar` | `attendance` history + `school_holidays` |
| `GET /api/notices` | `notices` |
| `GET /api/leaves` | `leave_requests` |
| `GET /api/cloud` | `devices.last_seen` — the pill is **offline** unless the ESP32 checked in within 15 minutes |
| `GET /api/health` | `devices` row + live counts; hardware sensors report 0 rather than inventing numbers |
| `POST /api/student/save` | inserts into `students` (+ `rfid_cards`), creating the class if needed |
| `POST /api/attendance/mark` | select-then-write on `attendance` (the unique index is an expression index, so no `ON CONFLICT`) |
| `POST /api/notice` | inserts into `notices` |

Everything else (Wi-Fi, fingerprint, OTA, LCD…) still falls through to the app's
own simulated layer — those are physical hardware, and a website cannot reach it.

A floating **“+ Add student (cloud)”** button opens a plain form (name, roll,
class, section, optional card UID) so students can be added from the browser
without the RC522 reader that the app's own registration screen requires.

### Testing it without a browser

```bash
node tools/test_bridge.mjs      # 24 assertions, stubbed fetch, no network
```

## Deploying

```bash
npm i -g firebase-tools
firebase login
firebase use --add
firebase deploy --only hosting
```

`firebase.json` deliberately has **no catch-all rewrite**: `/api/**` must 404 so
the app reaches its fallback, which the bridge intercepts. A rewrite would return
`index.html` with status 200 and every screen would stay empty.
