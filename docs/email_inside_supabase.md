# Automatic e-mail, straight from Supabase

No PC, no Raspberry Pi, no cron on your side. The chain, all inside Supabase:

```
card tapped 08:05
      │  astro_mark_attendance (status=present)
      ▼
attendance row ──trigger──▶ alerts (status=queued)        <- astro_fanout_arrival
      │                                        │
      │                             pg_cron 'astro-mail', every minute
      │                                        ▼
      │                        net.http_post ─▶ Edge Function astro-mail
      │                                        │  claims 20 rows
      │                                        ▼
      │                                 Brevo / Resend  (HTTPS)
      │                                        │
      └──────────── dashboard shows sent/failed ┘
```

## What is already live (2026-11-12)

| piece | state |
|---|---|
| Edge Function `astro-mail` | deployed, `verify_jwt: false`, guarded by `x-cron-secret` |
| `pg_net` extension | installed (0.20.4) |
| cron job `astro-mail` | `* * * * *` — every minute |
| arrival trigger | `attendance_arrival_fanout` on `attendance` — queues a `present` alert |
| `schools.alert_arrivals` | new column, default `true`, checked together with `alert_emails` |
| secret `MAIL_CRON_SECRET` | set (random, 48 hex) |
| **`MAIL_API_KEY`** | **missing — this is the only thing blocking real mail** |

Proved, without a provider key:

- `?ping=1` returns `{"ok":true,"provider":"brevo","from":null,"api_key":false}` — so
  cron reaches the function and the function answers;
- a normal call returns `{"ok":true,"skipped":"no MAIL_API_KEY yet…"}` and left
  the queue untouched (`queued = 1`, `sending = 0`) — nothing is stranded;
- inserting a `present` attendance row queued exactly one arrival e-mail:
  > **Arrived at school: Demo Student (13 Nov)**
  > Dear Parent,
  > Demo Student (Roll DEMO-01) reached school at **08:05** on 13 Nov 2026.
  > - The Aditya Birla Public School, Renukoot / Astro Smart Attendance
  (rolled back afterwards; 08:05 is correct for 02:35 UTC in Asia/Kolkata).

## The one step left: a sending address

Parents should see a real address, and Supabase cannot send mail itself — it has
to hand it to a provider over HTTPS. Cheapest route that keeps a *Gmail* From
address without owning a domain: **Brevo** (free 300/day, 300 mails/hour).

1. Create the mailbox you want parents to see — e.g. `astro@gmail.com`.
2. Sign up at <https://brevo.com> → **Senders & IP → Senders → Add a sender**,
   enter `astro@gmail.com`, then click the confirmation link Brevo sends to it.
3. **SMTP & API → API Keys → Create a new API key** (v3). Copy it once.
4. Supabase → **Project Settings → Edge Functions → Secrets**, add:

   | name | value |
   |---|---|
   | `MAIL_PROVIDER` | `brevo` |
   | `MAIL_API_KEY` | `xkeysib-…` (from step 3) |
   | `MAIL_FROM` | `astro@gmail.com` |
   | `MAIL_FROM_NAME` | `The Aditya Birla Public School` |

5. Wait a minute, then check:

   ```sql
   select status, count(*) from public.alerts group by 1;
   ```
   The one queued row should flip to `sent` on its own.

**Prefer Resend?** Same shape: `MAIL_PROVIDER=resend`, `MAIL_API_KEY=re_…`, and
`MAIL_FROM` must be on a domain you have verified in Resend (or
`onboarding@resend.dev` for tests to your own address only).

## Volume maths — is 300/day enough?

Free Brevo = 300 e-mails/day (and 300/hour). One arrival mail per child per day,
plus late and absent mails:

| students | arrival mails/day | + late/absent | verdict |
|---|---|---|---|
| 40 | 40 | ~10 | comfortable |
| 100 | 100 | ~20 | comfortable |
| 200 | 200 | ~40 | fine |
| 250 | 250 | ~50 | at the edge — turn `alert_arrivals` off, or upgrade |
| 400 | 400 | ~80 | no — paid tier, or Resend with a verified domain |

Rule of thumb: **300 ÷ 1.3 ≈ 230 children** with arrivals on; about **1,000**
with arrivals off (only late/absent).

### What happens when the cap is hit

Nothing is lost and nothing is thrown away. The provider answers 429, the Edge
Function calls `astro_defer_email(id, reason)`, which puts the row back to
`queued`, **hands the attempt back**, writes the reason into `last_error`, and
stops that pass. The next minute's cron tick tries again, and once the daily cap
resets the queue drains in order. A row only ever reaches `failed` for a real
error (bad address, rejected sender) — never for being early. That was migration
`0030_defer_rate_limited.sql`, and `astro-mail` v2 does it.

Turn arrivals off per school with
`update public.schools set alert_arrivals = false where code = 'ABPS-RNK';`
without touching the late/absent mails.

## Things that are deliberately not done

- **No mail for a re-scan.** One `present` alert per attendance row; tapping
  twice adds nothing, and the 15-minute `sending` release covers a crash mid-send.
- **No mail for holidays or weekly offs.** The trigger only fires on `present`.
- **Failed rows stay failed after 6 attempts** (`max_attempts_reached`) and show
  in the dashboard's e-mail tab, where they can be requeued.
- **Mail already delivered cannot be recalled** — deleting a message withdraws
  only what has not gone out.
