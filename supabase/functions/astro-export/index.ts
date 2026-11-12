// astro-export — hands one month of school records to the Google Drive backup.
//
// Called by tools/drive_sync/Code.gs (Google Apps Script, runs on Google's
// servers, no PC involved) once a day. It does no work of its own: it checks a
// shared secret, then calls the SQL function public.astro_drive_month(), which
// builds exactly the JSON that tools/archive writes.
//
//   GET ?ping=1                      health check, no data
//   GET ?month=2026-11               that month (default: current month, school tz)
//   GET ?month=2026-11&school=ABPS-RNK
//
// Secret: header `x-drive-secret` or `?secret=` — env DRIVE_SYNC_SECRET.
// Verify JWT is off: Apps Script has no Supabase session; the secret is the
// only key, so it must be long and never pasted anywhere public.

const CORS: Record<string, string> = {
  "access-control-allow-origin": "*",
  "access-control-allow-headers": "content-type, x-drive-secret",
  "access-control-allow-methods": "GET, OPTIONS",
};

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...CORS, "content-type": "application/json" },
  });
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });

  const url = new URL(req.url);
  const expected = Deno.env.get("DRIVE_SYNC_SECRET") ?? "";
  const given = req.headers.get("x-drive-secret") ?? url.searchParams.get("secret") ?? "";

  if (!expected) {
    return json({ ok: false, error: "DRIVE_SYNC_SECRET is not set on this function" }, 500);
  }
  if (given !== expected) {
    return json({ ok: false, error: "bad or missing secret" }, 401);
  }

  if (url.searchParams.get("ping")) {
    return json({ ok: true, function: "astro-export", hasSecret: true, version: 1 });
  }

  const month = url.searchParams.get("month");
  if (month && !/^\d{4}-(0[1-9]|1[0-2])$/.test(month)) {
    return json({ ok: false, error: "month must look like 2026-11" }, 400);
  }
  const school = url.searchParams.get("school");

  const supaUrl = Deno.env.get("SUPABASE_URL");
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  if (!supaUrl || !serviceKey) {
    return json({ ok: false, error: "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing" }, 500);
  }

  const rpc = await fetch(`${supaUrl}/rest/v1/rpc/astro_drive_month`, {
    method: "POST",
    headers: {
      apikey: serviceKey,
      authorization: `Bearer ${serviceKey}`,
      "content-type": "application/json",
    },
    body: JSON.stringify({ p_month: month ?? null, p_school_code: school ?? null }),
  });

  if (!rpc.ok) {
    return json({ ok: false, error: `rpc failed (${rpc.status})`, detail: await rpc.text() }, 502);
  }

  // astro_drive_month returns jsonb; PostgREST wraps a scalar in a JSON string
  // or returns it raw depending on version, so normalise both.
  const raw = await rpc.json();
  const data = typeof raw === "string" ? JSON.parse(raw) : raw;

  return new Response(JSON.stringify(data), {
    status: 200,
    headers: { ...CORS, "content-type": "application/json" },
  });
});
