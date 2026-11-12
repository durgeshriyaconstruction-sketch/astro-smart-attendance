# The mail API key — what it is, and a prompt that reproduces it

Everything below describes the **only** third-party API this project uses for
e-mail. Nothing else (no SMTP login, no Gmail password, no OAuth) is involved.

## 1. What `MAIL_API_KEY` is

A Brevo API key. It authorises one thing: handing a finished message to Brevo,
who deliver it and report success or failure. It is **not** the thing that
decides who gets mail — the database does that (triggers write rows into
`alerts`; the Edge Function just drains that queue).

| | |
|---|---|
| Provider | Brevo (ex Sendinblue) |
| Endpoint | `POST https://api.brevo.com/v3/smtp/email` |
| Auth header | `api-key: xkeysib-…` |
| Key shape | `xkeysib-<64 hex>-<16 chars>` |
| Free quota | 300 e-mails/day, 300/hour |
| Sender rule | `sender.email` must be a **verified single sender** on the account (a Gmail address is allowed) |
| Stored as | Supabase → Project Settings → Edge Functions → Secrets → `MAIL_API_KEY` |

Request body the function sends:

```json
{
  "sender": { "email": "astro.official.attendance@gmail.com", "name": "The Aditya Birla Public School" },
  "to": [{ "email": "parent@example.com" }],
  "subject": "Arrived at school: Demo Student (13 Nov)",
  "htmlContent": "<div style=\"font-family:Arial…\">…</div>",
  "textContent": "Dear Parent,\n\n…"
}
```

Answers that matter: `201` = accepted, `400` = bad request (unverified sender,
bad address), `401` = key or IP refused, `429` = quota.

## 2. The rules the code already follows

- **Never in the repo, never in chat.** Only in Supabase secrets.
- **Restricted key**: *Transactional email → All*, everything else None.
- **No IP allowlist.** Brevo's "Authorised IPs" must be off — Supabase egress
  addresses change, and a stale allowlist returns `401 unrecognised IP address`.
- `402 / 429` and any quota wording → the row goes **back to queued** and the
  pass stops (a cap is not the message's fault).
- `401 / 403` and auth wording → also **deferred**, because that is a setup
  problem, not a bad message.
- Anything else → `attempts + 1`; only after **6** real failures does the row
  become `failed` with the reason in `last_error`.
- `skipped` rows are never sent (used for demo/placeholder addresses).

## 3. Copy-paste prompt (for an AI agent)

> **Task:** wire transactional e-mail for the "Astro Smart Attendance" Supabase
> project (`nrjchonjlncamfyzmfye`) using Brevo, and prove it.
>
> **Context:** the project already has an Edge Function `astro-mail` (Deno,
> `verify_jwt:false`), a `pg_cron` job named `astro-mail` that POSTs to it every
> minute with header `x-cron-secret`, and an `alerts` table with statuses
> `queued | sending | sent | failed | skipped` plus `attempts`, `sent_at`,
> `last_error`. Triggers fill `alerts` when attendance is marked. Do not rewrite
> that pipeline; only configure the provider and verify it.
>
> **Provider:** Brevo. Endpoint `POST https://api.brevo.com/v3/smtp/email`,
> header `api-key`. Sender is a verified single sender (Gmail address allowed).
> Free quota 300/day.
>
> **Steps:**
> 1. If secrets are missing, ask the operator for the Brevo key, then store it as
>    Supabase Edge Function secrets: `MAIL_PROVIDER=brevo`, `MAIL_API_KEY=xkeysib-…`,
>    `MAIL_FROM=<verified sender>`, `MAIL_FROM_NAME=<school name>`. Keep the
>    existing `MAIL_CRON_SECRET`.
> 2. Ensure the Brevo account has **IP restriction disabled**
>    (<https://app.brevo.com/security/authorised_ips>) and the sender is **Valid**.
> 3. Health check: POST `…/functions/v1/astro-mail?ping=1` with the cron secret;
>    expect `{"ok":true,"api_key":true,"from":"<sender>"}`.
> 4. End-to-end: point one student's `guardian_email` at a mailbox you can read,
>    insert one `present` attendance row, trigger a send pass, then assert
>    `alerts.status='sent'`, `sent_at` not null, `last_error` null — and read the
>    mailbox to confirm the message, including whether it landed in spam.
> 5. On failure read `alerts.last_error`; map `401` → key/IP, `400` → sender or
>    recipient, `429` → quota. Never mark a row `failed` for those; defer instead.
>
> **Do not:** store the key in git, put it in the browser, use a Gmail app
> password, or send through a domain the school does not own.

## 4. Known limits, said plainly

- Sending **From a `gmail.com` address** through a third party fails Gmail's own
  DMARC alignment, so some recipients may see it in spam. A domain (~₹700/year)
  removes that risk; until then, test before a real rollout.
- 300/day ≈ 230 children with arrival mails on. Beyond that, switch
  `schools.alert_arrivals` off (≈1,000 children) or move to a paid plan.
