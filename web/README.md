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

> **The data on screen is demo data baked into the file — not your Supabase
> database.** Students, attendance, device telemetry and cloud status are all
> seeded from constants inside `index.html`. Nothing is read from or written to
> Supabase in this build.

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

## Making it show real data

`localApiFallback(path, method, body)` is the single seam between the UI and its
data source. Replacing its answers with Supabase/PostgREST calls would light up
the same screens from the real database (`students`, `attendance`, `notices`,
`devices`, …) without touching any of the UI code.

That is a deliberate next step, not something this file does today.
