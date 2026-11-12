# Outbox mailer

The database records every message a family should receive; **nothing in
Postgres can send email by itself.** This worker closes that gap.

```
admin posts a notice ─┐
admin messages one ───┼─▶ notices / messages  ──trigger──▶  alerts (status=queued)
attendance recorded ──┘                                            │
                                                                   ▼
                                          this worker claims 20 ◀──┘
                                                 │
                                          Resend / Gmail SMTP
                                                 │
                                    sent ─▶ alerts.status='sent'
                                    error ─▶ 'failed' + last_error
```

One row per guardian per message. A class notice to 40 students with an email on
file creates 40 rows; the worker walks them in batches.

## 1. Configure

```bash
cd services/mailer
cp .env.example .env
```

Fill in `SUPABASE_URL` and `SUPABASE_SECRET_KEY` (Project Settings → API →
secret key), then pick a provider.

### Resend (recommended)

Free tier: 3,000 emails/month, 100/day. Good enough for one school and it is a
single HTTPS call — no dependencies.

1. Create an account at <https://resend.com>, add and verify your domain
   (`resend.com/domains`). Without a verified domain you can only send **to your
   own address**, using `onboarding@resend.dev` as the sender.
2. Create an API key (Sending access) and put it in `RESEND_API_KEY`.
3. `MAIL_PROVIDER=resend`, `MAIL_FROM=notices@your-verified-domain`.

### Gmail / Google Workspace (no new service)

Free, ~500 recipients/day, and parents see a familiar address. Needs
**2-Step Verification** on the account, then <https://myaccount.google.com/apppasswords>
to create a 16-character app password (this replaced "less secure app access").

```ini
MAIL_PROVIDER=smtp
MAIL_FROM=your.school@gmail.com          # the same account you log in with
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_SECURE=true
SMTP_USER=your.school@gmail.com
SMTP_PASS=abcd efgh ijkl mnop            # the app password, spaces are fine
```

Gmail rewrites the From header to the authenticated account, so use that address.
Bulk sending from Gmail gets rate-limited or suspended; for a whole school, use
Resend or a transactional provider.

### Any other SMTP

Brevo, SendGrid, Amazon SES, Zoho, your host's mail server: set `SMTP_HOST` /
`SMTP_PORT` / `SMTP_SECURE` / `SMTP_USER` / `SMTP_PASS`. `npm install` once, which
pulls `nodemailer`.

## 2. Check, then run

```bash
npm install            # only needed for MAIL_PROVIDER=smtp
npm run check          # validates config, prints queue depth
npm run once           # one pass, exits — ideal for cron
npm start              # loop forever, poll every INTERVAL_MS
```

`npm run check` with a valid setup prints something like:

```
10:31:02 config ok — provider=resend from="Notices <notices@yourschool.in>" url=https://xxxx.supabase.co
10:31:03 queue: {"queued":6,"sent":0,"failed":0,"skipped":0,"oldest_queued":"2026-11-12T10:44:31.058Z"}
```

Then, from the admin side, post a notice and watch the pass:

```
10:32:11 mailer up — provider=resend from="Notices <notices@yourschool.in>"
10:32:11 claimed 2 email(s)
10:32:12 sent    notice#12 -> demo.parent@example.com
10:32:12 sent    notice#13 -> temp.two@example.com
```

## 3. Keep it running

**cron every minute** (simplest, no daemon):

```cron
* * * * * cd /home/you/astro-smart-attendance/services/mailer && /usr/bin/node index.mjs --once >> mailer.log 2>&1
```

**systemd** (better error handling, restarts on crash):

```ini
# /etc/systemd/system/astro-mailer.service
[Unit]
Description=Astro Smart Attendance mailer
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=you
WorkingDirectory=/home/you/astro-smart-attendance/services/mailer
ExecStart=/usr/bin/node index.mjs
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now astro-mailer
journalctl -u astro-mailer -f
```

Any always-on machine works: a Raspberry Pi in the school office, a ₹300/month
VPS, or an old laptop. It only needs outbound HTTPS.

## 4. What the worker promises

| Situation | Behaviour |
|---|---|
| Queue empty | sleeps `INTERVAL_MS`, no provider call |
| One bad address | that row → `failed` + `last_error`, rest keep sending |
| Provider rejects the key / sender | pass stops immediately, rows stay `sending`; `astro_release_stale_sending` returns them after 15 min instead of burning retries |
| Worker killed mid-send | same 15-minute release puts the row back in the queue |
| Row failed 6 times | `astro_claim_emails` parks it as `failed` (`max_attempts_reached`) |
| Two workers running | claim uses `FOR UPDATE SKIP LOCKED`; no double sends |
| Admin wants a retry | `select public.astro_requeue_failed();` resets failed rows to `queued` |

Rows are claimed in `created_at` order, so an old notice is never starved by a
burst of new ones.

## 5. Database contract

The worker only calls these; it never writes tables directly. All three are
`SECURITY DEFINER`, revoked from `anon`/`authenticated`, granted to
`service_role` only.

| RPC | Effect |
|---|---|
| `astro_claim_emails(p_limit int default 20)` | `queued → sending`, `attempts + 1`, returns the claimed rows |
| `astro_finish_email(p_id bigint, p_ok bool, p_error text default null)` | `sending → sent` (sets `sent_at`) or `failed` (sets `last_error`, truncated to 500) |
| `astro_release_stale_sending(p_minutes int default 15)` | `sending → queued` for rows older than the window |

Admin-side helpers (called from the app, not from here):
`astro_post_notice`, `astro_send_message`, `astro_mark_message_read`,
`astro_student_feed`, `astro_outbox_stats`, `astro_requeue_failed`.

## 6. Troubleshooting

| Symptom | Cause |
|---|---|
| `SUPABASE_SECRET_KEY looks like a publishable/anon key` | copy the **secret** key, not the publishable one |
| `rpc astro_claim_emails failed (401)` | key is wrong or was rotated — regenerate it |
| `resend 403: domain is not verified` | finish DNS verification, or send from `onboarding@resend.dev` to your own address first |
| `queue: {"queued":0,…}` but no mail | the notice found no guardian with an email on file; check `select roll_no, guardian_email from public.students where guardian_email is not null;` |
| `SMTP login failed: Username and Password not accepted` | Gmail needs a 16-character **app password** with 2FA on, not the account password |
| Everything is `failed` with `max_attempts_reached` | fix the cause, then `select public.astro_requeue_failed();` |
| `npm start` exits immediately | run `npm run check` — it names the missing variable |

## 7. Tests

```bash
npm test     # 16 tests: rendering, escaping, queue semantics, HTTP layer
```

No network, no database, no key: the HTTP tests run against a local stand-in for
PostgREST. (`node --version` must be 18 or newer.)
