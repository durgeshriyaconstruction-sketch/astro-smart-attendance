#!/usr/bin/env node
// Archive the school's records as plain files, one folder per year, one per
// month, one file per day — the way a school office actually files paper:
//
//   archive/
//     2026/
//       11/
//         2026-11-12.json      everything that happened that day
//         2026-11-12.csv       the attendance sheet for that day (for Excel)
//         ...
//         month-summary.json   per-student present/late/absent for the month
//     index.json
//
// It logs in as a real staff account (no service key on disk) and reads through
// the same row-level security the dashboard uses, so an archive can only ever
// contain the school the account belongs to.
//
//   SUPABASE_URL=https://<project>.supabase.co \
//   SUPABASE_KEY=sb_publishable_... \
//   ARCHIVE_EMAIL=principal@astro-school.example \
//   ARCHIVE_PASSWORD='...' \
//   node tools/archive/archive.mjs --month 2026-11 --out ./archive
//
//   ... --from 2026-11-01 --to 2026-11-30      explicit range
//   ... --skip-empty                            only days that have something
//
// Exit codes: 0 ok, 1 usage/network error, 2 refused (not staff / no school).

import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

// ---------------------------------------------------------------- args -----
const args = process.argv.slice(2);
const flag = (name, fallback = undefined) => {
  const i = args.indexOf(`--${name}`);
  if (i === -1) return fallback;
  const v = args[i + 1];
  return v && !v.startsWith('--') ? v : true;
};

if (args.includes('--help') || args.includes('-h')) {
  console.log(`Archive attendance, notices, messages, e-mails and leave for a period.

  --month YYYY-MM        archive one calendar month (most common)
  --from  YYYY-MM-DD     start of an explicit range
  --to    YYYY-MM-DD     end of the range (inclusive)
  --out   DIR            where to write (default ./archive)
  --skip-empty           do not write day files that would be empty

Environment: SUPABASE_URL, SUPABASE_KEY, ARCHIVE_EMAIL, ARCHIVE_PASSWORD`);
  process.exit(0);
}

const URL_BASE = (process.env.SUPABASE_URL || '').replace(/\/+$/, '');
const KEY = process.env.SUPABASE_KEY || '';
const EMAIL = process.env.ARCHIVE_EMAIL || '';
const PASSWORD = process.env.ARCHIVE_PASSWORD || '';
const outDir = path.resolve(flag('out', './archive'));
const skipEmpty = Boolean(flag('skip-empty', false));

function die(message, code = 1) {
  console.error(`archive: ${message}`);
  process.exit(code);
}

if (!URL_BASE || !KEY) die('SUPABASE_URL and SUPABASE_KEY must be set', 1);
if (!EMAIL || !PASSWORD) die('ARCHIVE_EMAIL and ARCHIVE_PASSWORD must be set', 1);

const pad = (n) => String(n).padStart(2, '0');
const isoDay = (d) => `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}`;
const addDays = (day, n) => {
  const d = new Date(`${day}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return isoDay(d);
};

// Range ---------------------------------------------------------------
let from;
let to;
if (flag('month')) {
  const m = String(flag('month')).match(/^(\d{4})-(\d{2})$/);
  if (!m) die('--month must look like 2026-11');
  const year = Number(m[1]);
  const month = Number(m[2]);
  from = `${year}-${pad(month)}-01`;
  to = isoDay(new Date(Date.UTC(year, month, 0)));
} else if (flag('from') && flag('to')) {
  from = String(flag('from'));
  to = String(flag('to'));
  if (!/^\d{4}-\d{2}-\d{2}$/.test(from) || !/^\d{4}-\d{2}-\d{2}$/.test(to)) die('dates must be YYYY-MM-DD');
  if (to < from) die('--to is before --from');
} else {
  die('give --month 2026-11 or --from/--to');
}
if ((new Date(`${to}T00:00:00Z`) - new Date(`${from}T00:00:00Z`)) / 86400000 > 400) {
  die('refusing to archive more than 400 days in one go');
}

// --------------------------------------------------------------- fetch -----
let token = '';

async function signIn() {
  const res = await fetch(`${URL_BASE}/auth/v1/token?grant_type=password`, {
    method: 'POST',
    headers: { apikey: KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: EMAIL, password: PASSWORD }),
  });
  if (!res.ok) die(`sign-in failed (${res.status}) — check ARCHIVE_EMAIL / ARCHIVE_PASSWORD`, 1);
  const body = await res.json();
  token = body.access_token;
  if (!token) die('sign-in returned no token', 1);
}

const authHeaders = () => ({ apikey: KEY, Authorization: `Bearer ${token}` });

async function get(pathAndQuery) {
  const res = await fetch(`${URL_BASE}/rest/v1/${pathAndQuery}`, { headers: authHeaders() });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    die(`GET ${pathAndQuery.split('?')[0]} -> ${res.status} ${text.slice(0, 200)}`, 1);
  }
  return res.json();
}

async function rpc(name, payload = {}) {
  const res = await fetch(`${URL_BASE}/rest/v1/rpc/${name}`, {
    method: 'POST',
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    die(`rpc ${name} -> ${res.status} ${text.slice(0, 200)}`, 1);
  }
  return res.json();
}

// Timezone helpers: a day belongs to the school, not to UTC.
function localDay(instant, tz) {
  const d = new Date(instant);
  if (Number.isNaN(d.getTime())) return null;
  try {
    return new Intl.DateTimeFormat('en-CA', { timeZone: tz || undefined }).format(d);
  } catch {
    return d.toISOString().slice(0, 10);
  }
}

function zonedMidnightIso(day, tz) {
  const [y, m, d] = day.split('-').map(Number);
  const wall = Date.UTC(y, m - 1, d, 0, 0, 0);
  if (!tz || tz === 'UTC') return new Date(wall).toISOString();
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: tz, hour12: false,
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
  const read = (t) => {
    const p = {};
    for (const x of parts.formatToParts(new Date(t))) if (x.type !== 'literal') p[x.type] = x.value;
    return Date.UTC(+p.year, +p.month - 1, +p.day, (+p.hour) % 24, +p.minute, +p.second);
  };
  let ts = wall;
  for (let i = 0; i < 2; i++) ts = wall - (read(ts) - ts);
  return new Date(ts).toISOString();
}

// ---------------------------------------------------------------- write ----
const csvCell = (v) => {
  const s = v === null || v === undefined ? '' : String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};
const toCsv = (rows, columns) => [
  columns.join(','),
  ...rows.map((r) => columns.map((c) => csvCell(r[c])).join(',')),
].join('\n');

async function writeJson(file, data) {
  await mkdir(path.dirname(file), { recursive: true });
  await writeFile(file, `${JSON.stringify(data, null, 2)}\n`, 'utf8');
}

// ----------------------------------------------------------------- main ----
await signIn();

const who = await rpc('astro_whoami');
if (!who || !who.school) die('this account is not linked to a school', 2);
if (!['admin', 'teacher', 'viewer'].includes(who.role)) die(`role "${who.role}" cannot read the school archive`, 2);

const tz = who.school.timezone || 'UTC';
const rangeStart = zonedMidnightIso(from, tz);
const rangeEnd = zonedMidnightIso(addDays(to, 1), tz);

const select = {
  students: 'id,roll_no,full_name,class_id,active,guardian_name,guardian_email',
  attendance: 'id,student_id,class_id,attendance_date,session,period_no,status,method,marked_at,note',
  notices: 'id,title,body,priority,audience,pinned,created_at,expires_at',
  messages: 'id,student_id,subject,body,direction,read_at,created_at',
  emails: 'id,student_id,kind,to_email,subject,status,attempts,sent_at,last_error,created_at',
  leaves: 'id,student_id,from_date,to_date,reason,status,decision_note,created_at',
};

const [students, attendance, notices, messages, emails, leaves] = await Promise.all([
  get(`students?select=${select.students}&order=roll_no.asc`),
  get(`attendance?select=${select.attendance}&attendance_date=gte.${from}&attendance_date=lte.${to}&order=attendance_date.asc,marked_at.asc`),
  get(`notices?select=${select.notices}&created_at=gte.${rangeStart}&created_at=lt.${rangeEnd}&order=created_at.asc`),
  get(`messages?select=${select.messages}&created_at=gte.${rangeStart}&created_at=lt.${rangeEnd}&order=created_at.asc`),
  get(`alerts?select=${select.emails}&created_at=gte.${rangeStart}&created_at=lt.${rangeEnd}&order=created_at.asc`),
  get(`leave_requests?select=${select.leaves}&from_date=lte.${to}&to_date=gte.${from}&order=from_date.asc`),
]);

const byId = new Map(students.map((s) => [s.id, s]));
const nameOf = (id) => {
  const s = byId.get(id);
  return s ? { roll_no: s.roll_no, name: s.full_name } : { roll_no: '', name: '' };
};

const report = await rpc('astro_attendance_report', { p_from: from, p_to: to }).catch(() => null);

const days = [];
for (let day = from; day <= to; day = addDays(day, 1)) days.push(day);

const index = {
  school: { name: who.school.name, code: who.school.code, timezone: tz },
  from,
  to,
  generated_at: new Date().toISOString(),
  generated_by: EMAIL,
  layout: 'YYYY/MM/YYYY-MM-DD.json — attendance, notices, messages, e-mails, leave for that day',
  days: [],
  totals: { attendance: 0, notices: 0, messages: 0, emails: 0, leave_requests: 0 },
};

let written = 0;

for (const day of days) {
  const dayAttendance = attendance
    .filter((a) => a.attendance_date === day)
    .map((a) => {
      const who = nameOf(a.student_id);
      return {
        roll_no: who.roll_no,
        name: who.name,
        student_id: a.student_id,
        status: a.status,
        method: a.method,
        session: a.session,
        period_no: a.period_no,
        marked_at: a.marked_at,
        note: a.note,
      };
    });

  const dayNotices = notices.filter((n) => localDay(n.created_at, tz) === day);
  const dayMessages = messages.filter((m) => localDay(m.created_at, tz) === day);
  const dayEmails = emails.filter((e) => localDay(e.created_at, tz) === day);
  const dayLeaves = leaves.filter((l) => l.from_date <= day && l.to_date >= day);

  const empty = !dayAttendance.length && !dayNotices.length && !dayMessages.length
    && !dayEmails.length && !dayLeaves.length;
  if (empty && skipEmpty) continue;

  const folder = path.join(outDir, day.slice(0, 4), day.slice(5, 7));
  const file = path.join(folder, `${day}.json`);

  await writeJson(file, {
    date: day,
    school: { code: who.school.code, name: who.school.name, timezone: tz },
    attendance: dayAttendance,
    notices: dayNotices,
    messages: dayMessages.map((m) => ({ ...m, ...nameOf(m.student_id) })),
    emails: dayEmails.map((e) => ({ ...e, ...nameOf(e.student_id) })),
    leave_requests: dayLeaves.map((l) => ({ ...l, ...nameOf(l.student_id) })),
  });

  await writeFile(
    path.join(folder, `${day}.csv`),
    `${toCsv(dayAttendance, ['roll_no', 'name', 'status', 'method', 'marked_at', 'note'])}\n`,
    'utf8',
  );

  index.days.push({
    date: day,
    file: `${day.slice(0, 4)}/${day.slice(5, 7)}/${day}.json`,
    counts: {
      attendance: dayAttendance.length,
      notices: dayNotices.length,
      messages: dayMessages.length,
      emails: dayEmails.length,
      leave_requests: dayLeaves.length,
    },
  });
  index.totals.attendance += dayAttendance.length;
  index.totals.notices += dayNotices.length;
  index.totals.messages += dayMessages.length;
  index.totals.emails += dayEmails.length;
  index.totals.leave_requests += dayLeaves.length;
  written++;
}

// One summary per month folder: the numbers the office is asked for.
if (report && Array.isArray(report.students)) {
  const months = new Set(days.map((d) => d.slice(0, 7)));
  for (const month of months) {
    const folder = path.join(outDir, month.slice(0, 4), month.slice(5, 7));
    await writeJson(path.join(folder, 'month-summary.json'), {
      month,
      from,
      to,
      school: who.school,
      school_days: report.school_days ?? null,
      students: report.students,
      totals: report.totals ?? null,
    });
  }
}

await writeJson(path.join(outDir, 'index.json'), index);

console.log(`archive: ${written} day file(s) for ${from}..${to}`);
console.log(`  attendance ${index.totals.attendance} · notices ${index.totals.notices} · `
  + `messages ${index.totals.messages} · e-mails ${index.totals.emails} · leaves ${index.totals.leave_requests}`);
console.log(`  written to ${outDir}`);
