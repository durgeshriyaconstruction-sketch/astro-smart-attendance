# Astro Smart Attendance — web front end

A single page that reads your data straight from Supabase. No build step, no
`npm install`, no framework. Three files:

| File | What it is |
|---|---|
| `index.html` | markup + logic (≈26 KB) |
| `astro-ui.css` | the **exact** design system the ESP32 serves at `192.168.4.1`, extracted verbatim from the firmware's gzipped `UI_GZ` blob |
| `icons.js` | the device's **logo + all 136 SVG icons**, same source — exported as `ic(name, size)` and `LOGO_SVG(size)` |

Those last two are why the cloud page and the device page look identical — it is
literally the device's stylesheet and icon set, not a re-creation of them.
Regenerate both any time with `python3 tools/extract_esp_ui.py
firmware/esp32/main.cpp web/`.

This is the "Supabase = brain, Firebase = front end" split, implemented:

```
browser ──► Firebase Hosting   (serves index.html)
   └─────► Supabase           (login + students + attendance + notices)
```

Firebase and Supabase never talk to each other. The browser does both.

---

## Signing in

| Who | Credentials |
|---|---|
| Admin | `astro@gmail.com` / `admin123` — created for this project, `members.role = admin` |
| Admin (test) | `principal@astro-school.test` |
| Student | their full name + password (the login form resolves the name to that student's email via `public.resolve_login_email`) |

`admin123` is the password used by the currently deployed v26.9.12 site. It is
fine for a review build but should be changed before this goes in front of a
real school — see the note about the published password further down.

---

## Before you deploy — read this

Your existing site lives at the **same** Firebase Hosting site
(`astro-smart-attendence.web.app`). Deploying this will **replace** what is
there now.

To try it without touching the live site, use a preview channel:

```bash
npm i -g firebase-tools
firebase login
firebase use --add                 # pick your existing project
firebase hosting:channel:deploy test
```

That prints a temporary URL like
`https://<project>--test-abc123.web.app`. Open it, log in, check the data
appears. When you're happy:

```bash
firebase deploy --only hosting
```

---

## Logging in

Use an account that is linked to the school — check `members` in Supabase.

Right now in this project:

| Account | Linked to school? | Sees data? |
|---|---|---|
| `principal@astro-school.test` | ✅ admin | ✅ yes |
| `parent@astro-school.test` | ❌ missing `members` row | ❌ always empty |

That second row is a real bug, not a permission setting. Row Level Security
requires a `members` row to resolve `current_school_id()` and `is_staff()`.
Until one exists, that account is authenticated but belongs to no school, so
every query correctly returns zero rows.

---

## How the data is protected

`index.html` contains a Supabase URL and the **anon** key. That is safe and
normal — those two values are shipped to every visitor of every Supabase app.
They grant nothing on their own; Row Level Security decides what each logged-in
user can read:

```sql
-- students / attendance
(school_id = current_school_id()) AND is_staff()
```

So a visitor without a valid login sees nothing at all, and a parent sees only
their linked child. **Never** put the `service_role` key in this file — that one
does bypass RLS.

---

## Changing the project

The only lines you normally edit are at the top of the `<script>`:

```js
const SUPABASE_URL = 'https://nrjchonjlncamfyzmfye.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOi...';
const TZ = 'Asia/Kolkata';
```

---

## What this page shows

- Students for the signed-in user's school
- Today's attendance (date computed in `Asia/Kolkata`, not the browser's zone)
- Present / Late / Absent counts
- Latest notices
- Auto-refresh every 10 seconds

## What it deliberately does not do

- **No camera.** The firmware contains no camera code (`esp_camera`, `mjpeg`,
  `/stream` — zero matches) and a plain ESP32 has no camera connector.
- **No `192.168.4.1` content.** That address only exists on the ESP32's own
  hotspot and cannot be reached from the internet.
- **No Firebase database.** Firebase Hosting only serves this file.
