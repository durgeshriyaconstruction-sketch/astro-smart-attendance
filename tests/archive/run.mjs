// Tests tools/archive/archive.mjs without touching the real project: a tiny
// HTTP server answers the handful of Supabase endpoints the script uses, the
// script runs as a child process, and the resulting folder tree is inspected.
//
//   cd tests/archive && npm test        (or: node run.mjs)
import { createServer } from 'node:http';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { mkdtemp, readFile, rm, stat } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const run = promisify(execFile);
const here = path.dirname(fileURLToPath(import.meta.url));
const script = path.resolve(here, '../../tools/archive/archive.mjs');

let pass = 0;
const failures = [];
const check = (name, cond, extra = '') => {
  if (cond) { pass++; return; }
  failures.push(`${name}${extra ? ` — ${extra}` : ''}`);
};

// ------------------------------------------------------------- fixtures ----
const STUDENT = { id: 's1', roll_no: 'DEMO-01', full_name: 'Demo Student', class_id: 'c1', active: true };

const responses = {
  students: [STUDENT],
  attendance: [{
    id: 1, student_id: 's1', class_id: 'c1', attendance_date: '2026-11-02',
    session: 'daily', period_no: null, status: 'present', method: 'fingerprint',
    marked_at: '2026-11-02T02:34:00+00:00', note: null,
  }],
  notices: [{
    id: 'n1', title: 'PTM on Saturday', body: 'Hall, 10 AM', priority: 'normal',
    audience: 'all', pinned: true, created_at: '2026-11-12T05:20:32+00:00', expires_at: null,
  }],
  messages: [
    // 00:30 IST on the 13th is 19:00 UTC on the 12th: it must be filed under the 13th.
    { id: 'm1', student_id: 's1', subject: 'Late again', body: 'Reach by 8:20',
      direction: 'to_student', read_at: null, created_at: '2026-11-12T19:00:00+00:00' },
  ],
  alerts: [{
    id: 7, student_id: 's1', kind: 'absent', to_email: 'demo.parent@example.com',
    subject: 'Absent today', status: 'sent', attempts: 1, sent_at: '2026-11-12T06:11:00+00:00',
    last_error: null, created_at: '2026-11-12T06:10:00+00:00',
  }],
  leave_requests: [{
    id: 'l1', student_id: 's1', from_date: '2026-11-05', to_date: '2026-11-06',
    reason: 'Family function', status: 'approved', decision_note: 'OK',
    created_at: '2026-11-04T10:35:00+00:00',
  }],
};

const rpcBodies = [];
const server = createServer(async (req, res) => {
  const url = new URL(req.url, 'http://localhost');
  const send = (obj, code = 200) => {
    res.writeHead(code, { 'content-type': 'application/json' });
    res.end(JSON.stringify(obj));
  };

  if (url.pathname === '/auth/v1/token') {
    if (req.method !== 'POST') return send({ message: 'nope' }, 405);
    return send({ access_token: 'token-for-tests', refresh_token: 'r', expires_in: 3600 });
  }

  if (url.pathname.startsWith('/rest/v1/rpc/')) {
    const name = url.pathname.split('/').pop();
    let body = '';
    for await (const chunk of req) body += chunk;
    rpcBodies.push({ name, body: body ? JSON.parse(body) : {} });
    if (name === 'astro_whoami') {
      return send({
        user_id: 'u1', role: 'admin',
        school: { id: 'sch1', name: 'The Aditya Birla Public School, Renukoot', code: 'ABPS-RNK', timezone: 'Asia/Kolkata' },
      });
    }
    if (name === 'astro_attendance_report') {
      return send({
        ok: true, from: '2026-11-01', to: '2026-11-30', school_days: 8,
        totals: { present: 1, late: 0, absent: 0, leave: 2, percent: 100 },
        students: [{ student_id: 's1', roll_no: 'DEMO-01', name: 'Demo Student',
          class: '9-A', present: 1, late: 0, absent: 0, leave: 2, other: 0, percent: 100 }],
      });
    }
    return send({ ok: true });
  }

  if (url.pathname.startsWith('/rest/v1/')) {
    const table = url.pathname.split('/')[3];
    if (!(table in responses)) return send({ message: 'unknown table' }, 404);
    return send(responses[table]);
  }

  send({ message: 'not found' }, 404);
});

await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const port = server.address().port;
const base = `http://127.0.0.1:${port}`;

const env = {
  ...process.env,
  SUPABASE_URL: base,
  SUPABASE_KEY: 'sb_publishable_TEST',
  ARCHIVE_EMAIL: 'principal@astro-school.test',
  ARCHIVE_PASSWORD: 'Astro-Principal-2026',
};

let dir = '';
try {
  // ---------------------------------------------------------- full month --
  dir = await mkdtemp(path.join(tmpdir(), 'astro-archive-'));
  const { stdout } = await run(process.execPath, [script, '--month', '2026-11', '--out', dir], { env });
  check('the script reports what it wrote', /30 day file\(s\) for 2026-11-01\.\.2026-11-30/.test(stdout), stdout.trim());

  const read = async (rel) => JSON.parse(await readFile(path.join(dir, rel), 'utf8'));
  const exists = async (rel) => stat(path.join(dir, rel)).then(() => true, () => false);

  check('a year folder holds a month folder', await exists('2026/11'));
  const day2 = await read('2026/11/2026-11-02.json');
  check('the day file carries the attendance', day2.attendance.length === 1
    && day2.attendance[0].roll_no === 'DEMO-01' && day2.attendance[0].name === 'Demo Student');
  check('the attendance keeps its status and method',
    day2.attendance[0].status === 'present' && day2.attendance[0].method === 'fingerprint');

  const csv = await readFile(path.join(dir, '2026/11/2026-11-02.csv'), 'utf8');
  check('the day also gets a spreadsheet sheet', csv.split('\n')[0] === 'roll_no,name,status,method,marked_at,note'
    && csv.includes('DEMO-01,Demo Student,present,fingerprint'));

  const empty = await read('2026/11/2026-11-03.json');
  check('a day with nothing still gets a file', empty.attendance.length === 0
    && empty.notices.length === 0 && empty.messages.length === 0);

  check('a notice is filed on the day it was published',
    (await read('2026/11/2026-11-12.json')).notices.length === 1);
  check('a message sent at 00:30 IST is filed on the next day, not the UTC day',
    (await read('2026/11/2026-11-13.json')).messages.length === 1
    && (await read('2026/11/2026-11-12.json')).messages.length === 0);
  check('the e-mail log is filed with the day it was written',
    (await read('2026/11/2026-11-12.json')).emails.length === 1);
  check('an approved leave shows on both of its days',
    (await read('2026/11/2026-11-05.json')).leave_requests.length === 1
    && (await read('2026/11/2026-11-06.json')).leave_requests.length === 1);

  const summary = await read('2026/11/month-summary.json');
  check('the month folder carries the report', summary.school_days === 8
    && summary.students[0].percent === 100);

  const index = await read('index.json');
  check('the index names the school and the range',
    index.school.code === 'ABPS-RNK' && index.from === '2026-11-01' && index.days.length === 30);
  check('the index totals match the files',
    index.totals.attendance === 1 && index.totals.messages === 1 && index.totals.emails === 1);

  check('the report was asked for the same range',
    rpcBodies.some((r) => r.name === 'astro_attendance_report'
      && r.body.p_from === '2026-11-01' && r.body.p_to === '2026-11-30'));

  // ---------------------------------------------------------- skip empty --
  const dir2 = await mkdtemp(path.join(tmpdir(), 'astro-archive-skip-'));
  await run(process.execPath, [script, '--month', '2026-11', '--out', dir2, '--skip-empty'], { env });
  check('--skip-empty leaves out quiet days',
    await stat(path.join(dir2, '2026/11/2026-11-02.json')).then(() => true, () => false)
    && !(await stat(path.join(dir2, '2026/11/2026-11-03.json')).then(() => true, () => false)));
  await rm(dir2, { recursive: true, force: true });

  // ------------------------------------------------------------- refusals --
  const refuse = await run(process.execPath, [script, '--from', '2026-11-09', '--to', '2026-11-01'], { env })
    .then(() => ({ code: 0 }), (e) => ({ code: e.code, stderr: e.stderr }));
  check('a backwards range is refused', refuse.code === 1 && /before/.test(refuse.stderr || ''));

  const noAuth = await run(process.execPath, [script, '--month', '2026-11'], {
    env: { ...env, ARCHIVE_PASSWORD: '' },
  }).then(() => ({ code: 0 }), (e) => ({ code: e.code }));
  check('missing credentials stop before any request', noAuth.code === 1);
} finally {
  server.close();
  if (dir) await rm(dir, { recursive: true, force: true });
}

console.log(`\n  archive tool: ${pass} passed, ${failures.length} failed`);
if (failures.length) {
  for (const f of failures) console.log(`  FAIL: ${f}`);
  process.exitCode = 1;
} else {
  console.log('  all assertions passed\n');
}
