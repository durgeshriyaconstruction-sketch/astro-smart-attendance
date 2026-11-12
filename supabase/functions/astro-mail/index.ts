// astro-mail — sends the alerts queue from inside Supabase, so the school does
// not need a PC kept switched on.
//
// Called by pg_cron once a minute (job 'astro-mail'). Claims up to 20 queued
// e-mails, sends each through Brevo or Resend, then marks it sent or failed in
// the same `alerts` table the dashboard already shows.
//
// Secrets (Project Settings -> Edge Functions -> Secrets):
//   MAIL_PROVIDER    brevo | resend        (default brevo)
//   MAIL_API_KEY     the provider's API key  <-- until this exists nothing is sent
//   MAIL_FROM        the verified sender, e.g. astro@gmail.com
//   MAIL_FROM_NAME   e.g. The Aditya Birla Public School
//   MAIL_CRON_SECRET shared secret the cron job sends as x-cron-secret
//
// Nothing is claimed until MAIL_API_KEY exists, so the queue cannot get stuck in
// 'sending' while the school is still setting the provider up.

type Alert = {
  id: number;
  to_email: string;
  subject: string;
  body: string;
  kind: string;
  attempts: number;
};

const SUPABASE_URL = Deno.env.get("SUPABASE_URL") ?? "";
const SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
const CRON_SECRET = Deno.env.get("MAIL_CRON_SECRET") ?? "";
const PROVIDER = (Deno.env.get("MAIL_PROVIDER") ?? "brevo").toLowerCase();
const API_KEY = Deno.env.get("MAIL_API_KEY") ?? "";
const FROM = Deno.env.get("MAIL_FROM") ?? "";
const FROM_NAME = Deno.env.get("MAIL_FROM_NAME") ?? "School Office";
const DRY_RUN = (Deno.env.get("MAIL_DRY_RUN") ?? "0") === "1";
const BATCH = Number(Deno.env.get("MAIL_BATCH") ?? "20");

// The provider refused for a reason that belongs to the setup, not to this
// message: out of quota (Brevo free = 300/day), or the key/IP is rejected
// (401/403 — e.g. Brevo's "authorised IPs" list). None of that is the mail's
// fault, so it must not count against the six attempts a real error is allowed,
// and the row stays queued until the setup is fixed.
class RateLimited extends Error {}

const limited = (res: Response, text: string) =>
  res.status === 429 ||
  res.status === 402 ||
  res.status === 401 ||
  res.status === 403 ||
  /quota|daily limit|too many|rate.?limit|unauthori[sz]ed|api.?key|authorised ip|authorized ip/i.test(text);

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });

const esc = (v: unknown) =>
  String(v ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");

// Plain paragraphs, inline styles only — survives Gmail, Outlook and old phones.
function toHtml(text: string): string {
  const parts = String(text ?? "")
    .replace(/\r\n/g, "\n")
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter(Boolean);
  const body = parts.length
    ? parts
        .map(
          (p) =>
            `<p style="margin:0 0 14px;line-height:1.55;">${esc(p).replace(/\n/g, "<br>")}</p>`,
        )
        .join("")
    : "";
  return `<div style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#111827;max-width:560px">${body}<hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0 10px"><p style="margin:0;color:#6b7280;font-size:12px;line-height:1.5">Sent by ${esc(FROM_NAME)} via Astro Smart Attendance. This mailbox is not monitored — please contact the school office for anything urgent.</p></div>`;
}

async function rpc(name: string, payload: unknown) {
  const res = await fetch(`${SUPABASE_URL}/rest/v1/rpc/${name}`, {
    method: "POST",
    headers: {
      apikey: SERVICE_KEY,
      Authorization: `Bearer ${SERVICE_KEY}`,
      "content-type": "application/json",
    },
    body: JSON.stringify(payload ?? {}),
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`${name} -> ${res.status} ${text.slice(0, 300)}`);
  return text ? JSON.parse(text) : null;
}

async function send(alert: Alert): Promise<void> {
  const html = toHtml(alert.body);
  if (DRY_RUN) {
    console.log(`dry-run ${alert.id} -> ${alert.to_email} :: ${alert.subject}`);
    return;
  }
  if (PROVIDER === "resend") {
    const res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: { Authorization: `Bearer ${API_KEY}`, "content-type": "application/json" },
      body: JSON.stringify({
        from: `${FROM_NAME} <${FROM}>`,
        to: [alert.to_email],
        subject: alert.subject,
        html,
        text: alert.body,
      }),
    });
    if (!res.ok) {
      const text = (await res.text()).slice(0, 300);
      if (limited(res, text)) throw new RateLimited(`resend ${res.status} ${text}`);
      throw new Error(`resend ${res.status} ${text}`);
    }
    return;
  }
  // Brevo (ex Sendinblue): your own address can be a single verified sender, so
  // no domain and no DNS records are needed.
  const res = await fetch("https://api.brevo.com/v3/smtp/email", {
    method: "POST",
    headers: {
      "api-key": API_KEY,
      "content-type": "application/json",
      accept: "application/json",
    },
    body: JSON.stringify({
      sender: { email: FROM, name: FROM_NAME },
      to: [{ email: alert.to_email }],
      subject: alert.subject,
      htmlContent: html,
      textContent: alert.body,
    }),
  });
  if (!res.ok) {
    const text = (await res.text()).slice(0, 300);
    if (limited(res, text)) throw new RateLimited(`brevo ${res.status} ${text}`);
    throw new Error(`brevo ${res.status} ${text}`);
  }
}

Deno.serve(async (req) => {
  if (req.method !== "POST") return json({ ok: false, error: "POST only" }, 405);

  // The cron job proves itself with a shared secret; nobody else may trigger a
  // send pass, so the queue cannot be drained by a stranger with the URL.
  if (CRON_SECRET) {
    const sent = req.headers.get("x-cron-secret") ?? "";
    const bearer = (req.headers.get("authorization") ?? "").replace(/^Bearer\s+/i, "");
    if (sent !== CRON_SECRET && bearer !== SERVICE_KEY) {
      return json({ ok: false, error: "forbidden" }, 403);
    }
  }

  // Health check the dashboard can call without sending anything.
  const url = new URL(req.url);
  if (url.searchParams.get("ping") === "1") {
    return json({
      ok: true,
      version: 3,
      provider: PROVIDER,
      from: FROM || null,
      api_key: Boolean(API_KEY),
      dry_run: DRY_RUN,
    });
  }

  if (!API_KEY) {
    return json({
      ok: true,
      skipped: "no MAIL_API_KEY yet — the queue keeps waiting, nothing is marked sending",
      provider: PROVIDER,
      from: FROM || null,
    });
  }

  let claimed: Alert[] = [];
  try {
    claimed = (await rpc("astro_claim_emails", { p_limit: BATCH })) ?? [];
  } catch (err) {
    return json({ ok: false, error: String(err) }, 500);
  }

  let sent = 0;
  let failed = 0;
  let deferred = 0;
  const errors: string[] = [];

  for (const alert of claimed) {
    try {
      await send(alert);
      await rpc("astro_finish_email", { p_id: alert.id, p_ok: true, p_error: null });
      sent++;
    } catch (err) {
      if (err instanceof RateLimited) {
        // Out of quota for today: hand the row back untouched and stop this
        // pass — the next cron tick will pick it up once the cap resets.
        await rpc("astro_defer_email", { p_id: alert.id, p_reason: String(err).slice(0, 300) })
          .catch(() => {});
        deferred++;
        break;
      }
      failed++;
      const message = String(err).slice(0, 400);
      errors.push(`#${alert.id} ${message}`);
      await rpc("astro_finish_email", { p_id: alert.id, p_ok: false, p_error: message }).catch(
        () => {},
      );
    }
  }

  return json({
    ok: true,
    provider: PROVIDER,
    claimed: claimed.length,
    sent,
    failed,
    deferred,
    errors,
  });
});
