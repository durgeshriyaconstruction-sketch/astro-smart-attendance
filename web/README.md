# Astro Smart Attendance — web dashboard

Static, dependency-free dashboard for the school that owns the fingerprint/RFID
terminal. Plain ES modules and `fetch`; no build step, no Supabase SDK, no bundler.

```
web/
  index.html      entry point (loads js/app.js as a module)
  styles.css      the only stylesheet
  js/config.js    project URL + publishable key
  js/api.js       password sign-in, silent token refresh, rpc()/rest() helpers
  js/ui.js        DOM builders (createElement only), toasts, date + CSV helpers
  js/app.js       boot, login, session expiry, role routing, password change
  js/student.js   parent/student view: calendar, notices, messages, leave
  js/admin.js     staff view: today, report, students, notices, inbox,
                  leaves, settings, devices, email queue
```

## Deploy

Copy the three items below to any static host (Firebase Hosting, Netlify,
GitHub Pages, nginx, S3) with `index.html` at the root:

```
index.html
styles.css
js/
```

There is nothing to compile and no environment variables — the Supabase project
URL and publishable key are baked into `js/config.js`. That key is **public by
design**; every table is protected by row-level security and every write goes
through a `security definer` RPC that re-checks the caller's membership and role.
Rotating the key means editing `js/config.js` and redeploying.

Serve over **https** (or `localhost`): the browser sends `Authorization` headers
and stores the session in `localStorage`.

### Run locally

```bash
cd web
python3 -m http.server 8000     # then open http://localhost:8000
```

Opening `index.html` from the filesystem (`file://`) will not work — ES modules
need an HTTP origin.

## Demo accounts

These exist on the live project only while the demo users are present:

| Email                        | Password             | Role on `ABPS-RNK` | Lands on |
| ---------------------------- | -------------------- | ------------------ | -------- |
| `principal@astro-school.test`| `Astro-Principal-2026` | `admin`           | staff dashboard (all 9 tabs) |
| `parent@astro-school.test`   | `Astro-Parent-2026`    | `student` (guardian of `DEMO-01`) | student dashboard |

Remove them before handing the system to a real school, and change the password
of any other account created for testing:

```sql
-- demo users only: @astro-school.test
delete from auth.identities
 where user_id in (select id from auth.users where email like '%@astro-school.test');
delete from auth.users where email like '%@astro-school.test';
```

Their `members` / `student_links` rows disappear with them (`on delete cascade`).
Attendance, notices and messages already recorded stay, because they belong to
the school, not to the login.

## The demo data on the project

`tools/demo_seed.sql` fills the sample school with something worth looking at:
DEMO-01 joins on 1 April, then has a fortnight of attendance (5 present, 1 late,
2 absent, 2 on an approved leave) plus a holiday on 19 November. Run it once on a
demo project — never on a real school — and the parent calendar reads 75%.

Without it the calendar is honest but dull: a student created today shows every
earlier day as "before joining", which is why the first version of this page read
0% attendance.

## What each role sees

* `admin` / `teacher` — the full staff dashboard. Only `admin` may change school
  timings, declare holidays and manage classes; `teacher` can mark attendance,
  post notices, message families and decide leave.
* `viewer` — the same read-only views with a banner, no write buttons.
* `student` — the child's own calendar, notices addressed to them, the message
  thread with the school, and a leave request form. A guardian with more than
  one child gets a picker at the top. No other student's data is reachable: the
  RPCs take a `p_student_id` and verify the caller's link themselves.
* anyone else — a "No access yet" card that names the account and tells them to
  ask the office for a role.

## Behaviour that matters

* **Colour code** — Present `#22c55e`, Absent `#ef4444`, Late `#f59e0b`,
  Leave `#8b5cf6`, Holiday `#64748b`, weekly off in grey.
* **Notices** — ordered by the server (Critical → Important → Normal, then
  newest first), rendered with `createElement`/text nodes only, so a notice body
  containing markup is shown literally. Empty state reads "No notices right now."
* **Messages** — grouped into one thread per student, sent optimistically and
  marked read on open.
* **Settings** — present/late boundary and absent cut-off are stored per school
  and re-read whenever the Settings tab opens; the same numbers decide the
  Present/Late/Absent verdict computed by the database.
* **Device check** — the Devices tab can queue an LCD, RFID or fingerprint test
  and polls `device_commands` until the terminal reports back (2.5 s interval,
  120 s cap, then it tells you to check the terminal).
* **Email queue** — count per status, the last 50 attempts, and a requeue action
  for failed alerts. Sending itself is the mailer's job; nothing is sent while
  no provider key is configured.

## Tests

The dashboard is covered by a headless suite that boots the real modules in
jsdom against a fake Supabase (auth, PostgREST and every RPC). It asserts the
login flow, all nine staff tabs, the read-only variant, every student tab,
notice XSS safety, empty states, error surfaces and sign-out.

```bash
cd tests/web
npm install     # jsdom, once
npm test
```

Expected: `web dashboard: 77 passed, 0 failed`.

## Known limits

* Nothing here has been exercised against the live project from a browser
  inside the build sandbox — it has no outbound route to `*.supabase.co`. The
  suite proves request shapes and rendering, not network reachability. What *was*
  checked live: every RPC name and argument list (`pg_proc`), and the JSON of
  `astro_whoami`, `astro_student_calendar`, `astro_student_feed`, `astro_inbox`,
  `astro_day_overview`, `astro_attendance_report`, `astro_pending_leaves`,
  `astro_device_health`, `astro_outbox_stats` and `astro_outbox_list` called as
  the demo admin and the demo guardian.
* Email delivery needs `services/mailer` deployed with a provider key; until
  then rows sit in the `alerts` outbox as `queued`.
* The terminal firmware is built and host-tested, but no physical reader has
  been wired up in this environment.
