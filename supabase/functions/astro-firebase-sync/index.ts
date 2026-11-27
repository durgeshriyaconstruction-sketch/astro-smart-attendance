// Supabase Edge Function: astro-firebase-sync
//
// Topology:
//   ESP32 (RFID terminal) -> Supabase (system of record) -> Firebase RTDB (mirror)
//   Firebase stays read-only for the terminal/dashboard; every write lands in
//   Supabase first. This function is the only thing with a Firebase credential,
//   so the project works on the Firebase Spark (free) plan.
//
// Secrets required (Dashboard -> Edge Functions -> Secrets, or `supabase secrets set`):
//   FIREBASE_DB_URL                https://<project>-default-rtdb.<region>.firebasedatabase.app
//   FIREBASE_SERVICE_ACCOUNT_JSON  full service-account key JSON, one line
//   BRIDGE_WEBHOOK_SECRET          shared secret, must equal
//                                  private_bridge_config.bridge_webhook_secret
//   ASTRO_FIREBASE_SYNC_TOKEN      optional second accepted value for the same header
//
// Auto-injected: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
//
// Deployed with verify_jwt = false because the caller is a Postgres trigger
// (pg_net), which has no Supabase JWT. Authorisation is the X-Bridge-Secret
// header check below, which rejects every request when the secret is unset.
//
// No remote imports on purpose. supabase-js and the std http server were both
// removed after the deployed runtime answered BOOT_ERROR ("Function failed to
// start") before any handler code ran. This uses Deno.serve and talks to
// PostgREST directly with the service-role key.
//
// Column names here are taken from the live schema. The previous revision
// (edge function version 4) mapped columns that do not exist --
// students.rfid_uid, students.display_name, students.class_name,
// attendance.date, attendance.time, devices.device_code on the wrong table
// and classes.class_name -- so attendance silently mapped to 0 rows and every
// student field came out blank.
//
// Written without backslash escape sequences so the file survives being pasted
// into the dashboard editor or sent as a JSON API body.

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type, x-bridge-secret",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
};

const ATTENDANCE_LIMIT = 5000;

// ---------------------------------------------------------------- utilities

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
  });
}

/**
 * Firebase RTDB keys may not contain . $ # [ ] / and may not be blank.
 * Written as a split/join loop on purpose: a slash inside a regex character
 * class is easy to mangle when this file is pasted into a dashboard editor.
 */
const FORBIDDEN_RTDB_CHARS = [".", "$", "#", "[", "]", "/"];
function rtdbKey(raw: unknown, fallbackPrefix = "ID"): string {
  let key = String(raw ?? "").trim();
  for (const ch of FORBIDDEN_RTDB_CHARS) key = key.split(ch).join("_");
  return key.length > 0 ? key : `${fallbackPrefix}_UNKNOWN`;
}

/** Device/UI wording for a Supabase status value. */
function statusLabel(status: unknown): string {
  switch (String(status ?? "").toLowerCase()) {
    case "present":
      return "Present";
    case "late":
      return "Late";
    case "absent":
      return "Absent";
    case "leave":
    case "excused":
      return "Leave";
    case "half_day":
      return "Half Day";
    case "left":
      return "Left";
    default:
      return String(status ?? "");
  }
}

/** IST calendar date + time, because the school is in Renukoot (UTC+5:30). */
const IST_OFFSET_MS = 5.5 * 60 * 60 * 1000;
function istDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const ms = Date.parse(iso);
  if (Number.isNaN(ms)) return String(iso).slice(0, 10);
  return new Date(ms + IST_OFFSET_MS).toISOString().slice(0, 10);
}
function istTime(iso: string | null | undefined): string {
  if (!iso) return "";
  const ms = Date.parse(iso);
  if (Number.isNaN(ms)) return "";
  return new Date(ms + IST_OFFSET_MS).toISOString().slice(11, 16);
}

function base64UrlEncode(input: string | Uint8Array): string {
  const bytes = typeof input === "string" ? new TextEncoder().encode(input) : input;
  let binary = "";
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
  return btoa(binary).split("+").join("-").split("/").join("_").replace(/=+$/, "");
}

/** Drop spaces, tabs and line breaks without writing escape sequences. */
function stripWhitespace(value: string): string {
  let out = value;
  for (const code of [9, 10, 13, 32]) out = out.split(String.fromCharCode(code)).join("");
  return out;
}

function pemToArrayBuffer(pem: string): ArrayBuffer {
  const b64 = stripWhitespace(
    pem
      .split("-----BEGIN PRIVATE KEY-----").join("")
      .split("-----END PRIVATE KEY-----").join(""),
  );
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes.buffer;
}

// ------------------------------------------------- Firebase authentication

type ServiceAccount = {
  client_email: string;
  private_key: string;
  token_uri?: string;
};

let cachedToken: { token: string; expiresAt: number } | null = null;

/** Mint a Google OAuth2 access token with the service account (RS256, no deps). */
async function getFirebaseAccessToken(sa: ServiceAccount): Promise<string> {
  const nowSec = Math.floor(Date.now() / 1000);
  if (cachedToken && cachedToken.expiresAt > nowSec + 60) return cachedToken.token;

  const tokenUri = sa.token_uri || "https://oauth2.googleapis.com/token";
  const header = base64UrlEncode(JSON.stringify({ alg: "RS256", typ: "JWT" }));
  const claims = base64UrlEncode(
    JSON.stringify({
      iss: sa.client_email,
      scope:
        "https://www.googleapis.com/auth/firebase.database https://www.googleapis.com/auth/userinfo.email",
      aud: tokenUri,
      iat: nowSec,
      exp: nowSec + 3600,
    }),
  );
  const signingInput = `${header}.${claims}`;
  const key = await crypto.subtle.importKey(
    "pkcs8",
    pemToArrayBuffer(sa.private_key),
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5",
    key,
    new TextEncoder().encode(signingInput),
  );
  const assertion = `${signingInput}.${base64UrlEncode(new Uint8Array(sig))}`;

  const res = await fetch(tokenUri, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
      assertion,
    }),
  });
  if (!res.ok) {
    throw new Error(`Google OAuth2 exchange failed (${res.status}): ${await res.text()}`);
  }
  const body = await res.json();
  cachedToken = {
    token: body.access_token,
    expiresAt: nowSec + Number(body.expires_in ?? 3500),
  };
  return cachedToken.token;
}

/** Parse the service-account secret, tolerating escaped or raw newlines. */
function parseServiceAccount(raw: string): ServiceAccount {
  try {
    return JSON.parse(raw) as ServiceAccount;
  } catch {
    // fall through to recovery
  }
  // The stored secret is often damaged in one of two ways: the private key's
  // newlines are escaped, or real newlines/tabs ended up inside the string
  // literals (which is illegal JSON). pemToArrayBuffer strips whitespace, so
  // dropping them here keeps the key valid.
  let cleaned = raw;
  for (const code of [9, 10, 13]) cleaned = cleaned.split(String.fromCharCode(code)).join("");
  const backslashN = String.fromCharCode(92) + "n";
  cleaned = cleaned.split(backslashN).join(String.fromCharCode(10));
  return JSON.parse(cleaned) as ServiceAccount;
}

// --------------------------------------------------------- Firebase writes

async function rtdbWrite(
  dbUrl: string,
  accessToken: string,
  path: string,
  method: "PUT" | "PATCH",
  body: unknown,
): Promise<void> {
  let base = dbUrl;
  while (base.endsWith("/")) base = base.slice(0, -1);
  let cleanPath = path;
  while (cleanPath.startsWith("/")) cleanPath = cleanPath.slice(1);
  const url = `${base}/${cleanPath}.json?access_token=${encodeURIComponent(accessToken)}`;
  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`Firebase RTDB ${method} /${cleanPath} failed (${res.status}): ${await res.text()}`);
  }
}

// ------------------------------------------------------------- row mapping

type Row = Record<string, unknown>;

type StudentRow = Row & { id: string; roll_no?: string; full_name?: string };
type CardRow = Row & { student_id: string; card_uid: string };
type ClassRow = Row & { id: string; name?: string; section?: string };
type AttendanceRow = Row & {
  student_id: string;
  attendance_date?: string;
  status?: string;
  method?: string;
  marked_at?: string;
  session?: string;
  period_no?: number | null;
};

type StudentMirror = {
  rfid: string;
  studentId: string;
  roll: string;
  name: string;
  nameLower: string;
  className: string;
  section: string;
  email: string;
  phone: string;
  parentEmail: string;
  parentPhone: string;
  guardianName: string;
  fingerprintId: number;
  active: boolean;
  presentCount: number;
  lateCount: number;
  absentCount: number;
  leaveCount: number;
  halfCount: number;
  streak: number;
  attendancePct: number;
  status: string;
  lastDate: string;
  lastScan: string;
  updatedAt: string;
};

/**
 * Build one mirror record per student, keyed by RFID card UID because that is
 * the key the ESP32 firmware reads (/students/<RFID>) and writes scans against.
 * Students with no card still appear, keyed by their roll number, so the
 * dashboard's "students without a card" list stays truthful.
 */
function buildStudentMirror(
  students: StudentRow[],
  cards: CardRow[],
  classes: ClassRow[],
): Record<string, StudentMirror> {
  const classById = new Map<string, ClassRow>();
  for (const c of classes) classById.set(String(c.id), c);

  const cardByStudent = new Map<string, string>();
  for (const card of cards) {
    if (card.active === false) continue;
    cardByStudent.set(String(card.student_id), String(card.card_uid ?? "").trim().toUpperCase());
  }

  const studentsMap: Record<string, StudentMirror> = {};
  for (const s of students) {
    const rfid = cardByStudent.get(String(s.id)) ?? "";
    const roll = String(s.roll_no ?? "");
    const cls = s.class_id ? classById.get(String(s.class_id)) : undefined;
    const name = String(s.full_name ?? "");
    studentsMap[rtdbKey(rfid || roll, "STU")] = {
      rfid,
      studentId: String(s.id),
      roll,
      name,
      nameLower: name.toLowerCase(),
      className: String(cls?.name ?? ""),
      section: String(cls?.section ?? ""),
      email: "",
      phone: String(s.guardian_phone ?? ""),
      parentEmail: String(s.guardian_email ?? ""),
      parentPhone: String(s.guardian_phone ?? ""),
      guardianName: String(s.guardian_name ?? ""),
      fingerprintId: Number(s.fingerprint_id ?? 0),
      active: s.active !== false,
      presentCount: 0,
      lateCount: 0,
      absentCount: 0,
      leaveCount: 0,
      halfCount: 0,
      streak: 0,
      attendancePct: 0,
      status: "",
      lastDate: "",
      lastScan: "",
      updatedAt: String(s.updated_at ?? s.created_at ?? ""),
    };
  }
  return studentsMap;
}

// ------------------------------------------------------- Supabase (PostgREST)

/**
 * Minimal PostgREST reader. Deliberately no supabase-js import: remote module
 * imports are the one thing this function cannot depend on, because the
 * deployed runtime reports BOOT_ERROR before any handler code runs when a
 * remote import cannot be resolved.
 */
type SbEnv = { url: string; key: string };

async function sbSelect(
  env: SbEnv,
  table: string,
  query: string,
): Promise<Row[]> {
  const res = await fetch(`${env.url}/rest/v1/${table}?${query}`, {
    headers: {
      apikey: env.key,
      Authorization: `Bearer ${env.key}`,
      "Accept-Profile": "public",
    },
  });
  if (!res.ok) {
    throw new Error(`${table} query failed (${res.status}): ${await res.text()}`);
  }
  return (await res.json()) as Row[];
}

// --------------------------------------------------------------- main sync

async function runFullSync(env: SbEnv, dbUrl: string, accessToken: string) {
  const [students, cards, classes, attendance, devices, notices, holidays, schools] =
    await Promise.all([
      sbSelect(env, "students", "select=*"),
      sbSelect(env, "rfid_cards", "select=*"),
      sbSelect(env, "classes", "select=*"),
      sbSelect(
        env,
        "attendance",
        `select=*&order=attendance_date.desc,marked_at.desc&limit=${ATTENDANCE_LIMIT}`,
      ),
      sbSelect(env, "devices", "select=*"),
      sbSelect(env, "notices", "select=*&order=created_at.desc&limit=50"),
      sbSelect(env, "school_holidays", "select=*"),
      sbSelect(env, "schools", "select=*&limit=1"),
    ]);

  const studentRows = students as StudentRow[];
  const cardRows = cards as CardRow[];
  const classRows = classes as ClassRow[];
  const attendanceRows = attendance as AttendanceRow[];

  // ---- index students by RFID / roll so attendance can be resolved
  const studentsMap = buildStudentMirror(studentRows, cardRows, classRows);
  const byStudentId = new Map<string, StudentMirror>();
  for (const mirror of Object.values(studentsMap)) byStudentId.set(mirror.studentId, mirror);

  const scansByDate: Record<string, Record<string, Row>> = {};
  const history: Record<string, Record<string, string>> = {};
  const lastSeen = new Map<string, { date: string; time: string; status: string }>();

  for (const row of attendanceRows) {
    const mirror = byStudentId.get(String(row.student_id));
    if (!mirror) continue; // attendance for a student that is no longer present
    const date = String(row.attendance_date ?? "").slice(0, 10);
    if (!date) continue;
    const label = statusLabel(row.status);
    const key = rtdbKey(mirror.rfid || mirror.roll, "STU");

    // Counters: daily session only, so periods do not inflate the totals.
    if (String(row.session ?? "daily") === "daily") {
      switch (String(row.status ?? "").toLowerCase()) {
        case "present":
          mirror.presentCount++;
          break;
        case "late":
          mirror.lateCount++;
          break;
        case "absent":
          mirror.absentCount++;
          break;
        case "leave":
        case "excused":
          mirror.leaveCount++;
          break;
        case "half_day":
          mirror.halfCount++;
          break;
      }
      const prev = lastSeen.get(mirror.studentId);
      if (!prev || date > prev.date) {
        lastSeen.set(mirror.studentId, {
          date,
          time: istTime(row.marked_at),
          status: label,
        });
      }
    }

    history[key] ??= {};
    // A present scan outranks the auto-generated absent row for the same day.
    if (history[key][date] !== "Present" && history[key][date] !== "Late") {
      history[key][date] = label;
    }

    scansByDate[date] ??= {};
    const scanKey = rtdbKey(mirror.rfid || mirror.roll, "STU");
    if (!scansByDate[date][scanKey] || String(row.marked_at ?? "") > String(scansByDate[date][scanKey].epoch ?? "")) {
      scansByDate[date][scanKey] = {
        rfid: mirror.rfid,
        studentId: mirror.studentId,
        name: mirror.name,
        roll: mirror.roll,
        className: mirror.className,
        status: label,
        session: String(row.session ?? "daily"),
        period: row.period_no ?? 0,
        time: istTime(row.marked_at),
        source: String(row.method ?? ""),
        epoch: String(row.marked_at ?? ""),
      };
    }
  }

  // Percentages, streaks and today's status, computed from the same rows.
  for (const mirror of Object.values(studentsMap)) {
    const marked =
      mirror.presentCount + mirror.lateCount + mirror.absentCount + mirror.leaveCount + mirror.halfCount;
    const attended = mirror.presentCount + mirror.lateCount + mirror.halfCount * 0.5;
    mirror.attendancePct = marked > 0 ? Math.round((attended / marked) * 100) : 0;
    const last = lastSeen.get(mirror.studentId);
    if (last) {
      mirror.lastDate = last.date;
      mirror.lastScan = last.time;
      mirror.status = last.status;
    }
  }

  // ---- devices
  const devicesMap: Record<string, Row> = {};
  for (const d of devices) {
    const code = rtdbKey(d.device_code, "DEV");
    devicesMap[code] = {
      deviceCode: code,
      name: String(d.name ?? ""),
      version: String(d.firmware ?? ""),
      firmware: String(d.firmware ?? ""),
      ip: String(d.ip ?? ""),
      rssi: Number(d.wifi_rssi ?? 0),
      online: d.active !== false,
      lastSeen: String(d.last_seen ?? ""),
      updatedAt: String(d.last_seen ?? d.created_at ?? ""),
    };
  }

  // ---- holidays: firmware reads a { "YYYY-MM-DD": "reason" } object
  const holidaysMap: Record<string, string> = {};
  for (const h of holidays) {
    const date = String(h.holiday_date ?? "").slice(0, 10);
    if (date) holidaysMap[rtdbKey(date, "DAY")] = String(h.reason ?? "Holiday");
  }

  // ---- notices: firmware polls /notices/current as a plain string
  const today = istDate(new Date().toISOString());
  const liveNotices = notices.filter((n) => {
    const publish = n.publish_at ? String(n.publish_at).slice(0, 10) : "";
    const expires = n.expires_at ? String(n.expires_at).slice(0, 10) : "";
    if (publish && publish > today) return false;
    if (expires && expires < today) return false;
    return true;
  });
  const noticesList = liveNotices.map((n) => ({
    id: String(n.id),
    title: String(n.title ?? ""),
    body: String(n.body ?? ""),
    audience: String(n.audience ?? ""),
    priority: String(n.priority ?? "normal"),
    pinned: n.pinned === true,
    publishAt: String(n.publish_at ?? ""),
    expiresAt: String(n.expires_at ?? ""),
  }));
  const currentNotice = noticesList.length
    ? noticesList
        .map((n) => `${n.title}${n.body ? `: ${n.body}` : ""}`)
        .join(" | ")
        .slice(0, 900)
    : "";

  // ---- school settings, in the shape the firmware's applyCloudSettings() reads
  const school = schools[0];
  const hhmm = (value: unknown) => String(value ?? "").slice(0, 5);
  const settings = school
    ? {
        start: hhmm(school.day_start),
        close: hhmm(school.day_end),
        periodStart: hhmm(school.day_start),
        lateAfter: Math.max(
          0,
          Math.round(
            (Date.parse(`1970-01-01T${hhmm(school.late_after) || "00:00"}:00Z`) -
              Date.parse(`1970-01-01T${hhmm(school.day_start) || "00:00"}:00Z`)) /
              60000,
          ),
        ),
        weeklyOff: Array.isArray(school.weekly_off) ? school.weekly_off.join(",") : "",
        updatedBy: "supabase-bridge",
        updatedAt: new Date().toISOString(),
      }
    : null;

  // ---- push. PUT replaces each subtree so deletes in Supabase delete in Firebase.
  await rtdbWrite(dbUrl, accessToken, "students", "PUT", studentsMap);
  await rtdbWrite(dbUrl, accessToken, "history", "PUT", history);
  await rtdbWrite(dbUrl, accessToken, "devices", "PUT", devicesMap);
  await rtdbWrite(dbUrl, accessToken, "holidays", "PUT", holidaysMap);
  await rtdbWrite(dbUrl, accessToken, "notices", "PUT", {
    current: currentNotice,
    list: noticesList,
    updatedAt: new Date().toISOString(),
  });
  if (settings) await rtdbWrite(dbUrl, accessToken, "settings", "PATCH", settings);

  // /scans only grows; write the days we actually have rather than wiping old days.
  for (const [date, entries] of Object.entries(scansByDate)) {
    await rtdbWrite(dbUrl, accessToken, `scans/${date}`, "PUT", entries);
  }

  const meta = {
    source: "supabase-edge-bridge",
    mode: "full_sync",
    studentCount: Object.keys(studentsMap).length,
    attendanceRows: attendanceRows.length,
    dayCount: Object.keys(scansByDate).length,
    deviceCount: Object.keys(devicesMap).length,
    noticeCount: noticesList.length,
    holidayCount: Object.keys(holidaysMap).length,
    syncedAt: new Date().toISOString(),
  };
  await rtdbWrite(dbUrl, accessToken, "meta/lastSync", "PUT", meta);

  return meta;
}

// ------------------------------------------------------------------ server

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS_HEADERS });

  try {
    // -------- authorisation
    const expectedSecrets = [
      Deno.env.get("BRIDGE_WEBHOOK_SECRET") ?? "",
      Deno.env.get("ASTRO_FIREBASE_SYNC_TOKEN") ?? "",
    ].filter((s) => s.length > 0);

    if (expectedSecrets.length === 0) {
      return json({ ok: false, error: "BRIDGE_SECRET_NOT_CONFIGURED" }, 500);
    }

    const authHeader = req.headers.get("authorization") ?? "";
    const bearer = authHeader.toLowerCase().startsWith("bearer ")
      ? authHeader.slice(7).trim()
      : "";
    const headerSecret = req.headers.get("x-bridge-secret") ?? bearer;

    if (!headerSecret || !expectedSecrets.includes(headerSecret)) {
      return json({ ok: false, error: "UNAUTHORIZED" }, 401);
    }

    // -------- config
    const dbUrl = Deno.env.get("FIREBASE_DB_URL");
    const saRaw = Deno.env.get("FIREBASE_SERVICE_ACCOUNT_JSON");
    if (!dbUrl || !saRaw) {
      return json({ ok: false, error: "FIREBASE_CONFIG_MISSING" }, 500);
    }

    const sa = parseServiceAccount(saRaw);
    if (!sa.client_email || !sa.private_key) {
      return json({ ok: false, error: "SERVICE_ACCOUNT_INVALID" }, 500);
    }

    const env: SbEnv = {
      url: Deno.env.get("SUPABASE_URL") ?? "",
      key: Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "",
    };
    if (!env.url || !env.key) {
      return json({ ok: false, error: "SUPABASE_ENV_MISSING" }, 500);
    }

    const accessToken = await getFirebaseAccessToken(sa);
    const meta = await runFullSync(env, dbUrl, accessToken);

    return json({ ok: true, ...meta });
  } catch (err) {
    console.error("astro-firebase-sync failed:", err);
    return json(
      { ok: false, error: err instanceof Error ? err.message : String(err) },
      500,
    );
  }
});
