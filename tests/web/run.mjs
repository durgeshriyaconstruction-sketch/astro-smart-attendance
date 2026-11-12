// Headless DOM tests for web/. Boots the real modules against a fake Supabase,
// so the dashboard's request shapes stay honest even without a browser.
//
//   cd tests/web && npm install && npm test
import { JSDOM } from 'jsdom';
import * as F from './fixtures.mjs';

// --------------------------------------------------------------- harness ---
let pass = 0;
const failures = [];
const calls = [];
const consoleErrors = [];

function check(name, cond, extra = '') {
  if (cond) { pass++; return; }
  failures.push(`${name}${extra ? ` — ${extra}` : ''}`);
}

const tick = (ms = 25) => new Promise((r) => setTimeout(r, ms));
const settle = async (rounds = 4) => { for (let i = 0; i < rounds; i++) await tick(); };

const json = (data, status = 200) => new Response(JSON.stringify(data), {
  status, headers: { 'content-type': 'application/json' },
});

let role = 'admin';
let failRpc = null;
let messageReply = { ok: true, message_id: 'm1', email_queued: true, guardian_email_on_file: true };
const rpcCalls = [];

async function fakeFetch(input, init = {}) {
  const url = String(input);
  const method = (init.method || 'GET').toUpperCase();
  const body = init.body ? JSON.parse(init.body) : undefined;
  calls.push({ url, method, body, headers: init.headers || {} });

  if (url.includes('/auth/v1/token')) {
    return json({
      access_token: 'access-token-for-tests',
      refresh_token: 'refresh-token-for-tests',
      expires_in: 3600,
      user: { id: 'bbbbbbbb-0000-0000-0000-000000000001', email: 'principal@astro-school.test' },
    });
  }
  if (url.includes('/auth/v1/logout')) return new Response('', { status: 204 });
  if (url.includes('/auth/v1/user')) return json({ id: 'u1' });

  if (url.includes('/rest/v1/rpc/')) {
    const fn = url.split('/rest/v1/rpc/')[1].split('?')[0];
    rpcCalls.push({ fn, body });
    if (failRpc === fn) return json({ message: 'BOOM', code: 'P0001' }, 400);
    switch (fn) {
      case 'astro_whoami': return json(role === 'admin' ? F.ADMIN_WHOAMI : F.PARENT_WHOAMI);
      case 'astro_day_overview': return json(F.DAY_OVERVIEW);
      case 'astro_student_feed': return json(F.FEED);
      case 'astro_student_calendar': return json(F.CALENDAR);
      case 'astro_attendance_report': return json(F.REPORT);
      case 'astro_inbox': return json(F.INBOX);
      case 'astro_pending_leaves': return json(F.PENDING_LEAVES);
      case 'astro_device_health': return json(F.DEVICE_HEALTH);
      case 'astro_outbox_stats': return json(F.OUTBOX_STATS);
      case 'astro_outbox_list': return json(F.OUTBOX_LIST);
      case 'astro_mark_thread_read': return json({ ok: true, marked_read: 1 });
      case 'astro_send_message': return json(messageReply);
      case 'astro_update_settings': return json({ ok: true, settings_version: 7 });
      case 'astro_save_student': return json({ ok: true, student: { id: F.STUDENT.id, full_name: 'New Kid' } });
      default: return json({ ok: true });
    }
  }

  if (url.includes('/rest/v1/students')) return json([F.STUDENT]);
  if (url.includes('/rest/v1/classes')) return json(F.CLASSES);
  if (url.includes('/rest/v1/schools')) return json([F.SCHOOL]);
  if (url.includes('/rest/v1/school_holidays')) return json([]);
  if (url.includes('/rest/v1/leave_requests')) return json([]);
  if (url.includes('/rest/v1/notices')) return json([]);
  if (url.includes('/rest/v1/device_events')) return json(F.DEVICE_EVENTS);
  if (url.includes('/rest/v1/device_commands')) {
    return json([{ id: 'c1', status: 'done', result: { uid: 'A1B2C3D4', slot: 12 } }]);
  }
  return json([]);
}

// ------------------------------------------------------------------ dom ----
const dom = new JSDOM(
  '<!doctype html><html><body><div id="app"></div></body></html>',
  { url: 'https://astro.test/', pretendToBeVisual: true },
);

globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.localStorage = dom.window.localStorage;
globalThis.HTMLElement = dom.window.HTMLElement;
globalThis.Node = dom.window.Node;
globalThis.location = dom.window.location;
globalThis.fetch = fakeFetch;

dom.window.fetch = fakeFetch;
globalThis.confirm = dom.window.confirm = () => true;
globalThis.prompt = dom.window.prompt = () => 'test note';
globalThis.alert = dom.window.alert = () => {};
dom.window.addEventListener('error', (e) => consoleErrors.push(String(e.message || e.error)));
dom.window.addEventListener('unhandledrejection', (e) => consoleErrors.push(String(e.reason?.message || e.reason)));
dom.window.document.getElementById('app').innerHTML = '<div class="boot"></div>';

const text = () => document.body.textContent.replace(/\s+/g, ' ');
const tab = (label) => [...document.querySelectorAll('nav.tabs button')]
  .find((b) => b.textContent.trim() === label);

// ------------------------------------------------------------ login flow ---
const { zonedToIso } = await import('../../web/js/ui.js');
check('a local time is stored in the school timezone, not the browser timezone',
  zonedToIso('2026-11-13T10:00', 'Asia/Kolkata') === '2026-11-13T04:30:00.000Z');
check('UTC input passes straight through', zonedToIso('2026-11-13T10:00', 'UTC') === '2026-11-13T10:00:00.000Z');
check('an empty expiry stays empty', zonedToIso('', 'Asia/Kolkata') === null);

const app = await import('../../web/js/app.js');
await settle();

check('app boots to the sign-in form', Boolean(document.querySelector('input[type="email"]')));
check('login form has a password field', Boolean(document.querySelector('input[type="password"]')));

const emailField = document.querySelector('input[type="email"]');
emailField.value = 'principal@astro-school.test';
document.querySelector('input[type="password"]').value = 'Astro-Principal-2026';
document.querySelector('form.login').dispatchEvent(new dom.window.Event('submit', { cancelable: true, bubbles: true }));
await settle(8);

check('after sign-in the shell renders', Boolean(document.querySelector('.topbar')));
check('school name is shown in the header', text().includes('The Aditya Birla Public School'));
check('role badge is shown', text().includes('admin'));
check('first tab is Today', Boolean(tab('Today')));
check('sign-in sent the publishable apikey', calls.some((c) => c.headers?.apikey));
check('sign-in used the password grant', calls.some((c) => c.url.includes('grant_type=password')));
check('session was persisted to localStorage', Boolean(localStorage.getItem('astro.session.v1')));

// ------------------------------------------------------------ admin tabs ---
const expectTab = {
  Today: ['Present 1', 'Demo Student'],
  Report: ['88.9%', 'school days'],
  Students: ['DEMO-01', 'Classes'],
  Notices: ['New notice'],
  Inbox: ['unread from families', 'Demo Student'],
  Leaves: ['Family function', 'Approve'],
  Settings: ['School timings', 'Weekly off'],
  Devices: ['ASTRO-RNK-01', 'Main gate terminal'],
  Emails: ['queued 1', 'Email queue'],
};

for (const [label, needles] of Object.entries(expectTab)) {
  const b = tab(label);
  check(`tab ${label} exists`, Boolean(b));
  if (!b) continue;
  b.click();
  await settle(6);
  const missing = needles.filter((n) => !text().includes(n));
  check(`tab ${label} renders its content`, missing.length === 0, `missing: ${missing.join(', ')}`);
}

check('no console/rejection errors during the admin walk', consoleErrors.length === 0, consoleErrors.join(' | '));

// ------------------------------------------------------------ dm send ---
tab('Inbox').click();
await settle(6);
document.querySelector('button.conv').click();
await settle(6);
const composer = document.querySelector('.composer textarea');
check('a conversation opens with its history',
  document.querySelector('.thread')?.textContent.includes('You were late 3 times'));
messageReply = { ok: false };
if (composer) {
  composer.value = 'Please send the fee receipt';
  messageReply = { ok: true, message_id: 'm9', email_queued: false, guardian_email_on_file: false };
  [...document.querySelectorAll('.composer button')].find((b) => b.textContent.trim() === 'Send').click();
  await settle(8);
  check('the message is sent with its body',
    rpcCalls.some((c) => c.fn === 'astro_send_message' && c.body?.p_body === 'Please send the fee receipt'));
  check('a family with no guardian email is told so instead of a false "sent"',
    document.querySelector('.toast')?.textContent.includes('no guardian email'));
  messageReply = { ok: true, message_id: 'm9', email_queued: true, guardian_email_on_file: true };
}

await settle(6);
const delBtn = [...document.querySelectorAll('.thread button.icon-btn')]
  .find((b) => b.title === 'Delete message');
check('an admin can delete a message from a thread', Boolean(delBtn));
if (delBtn) {
  delBtn.click();
  await settle(6);
  check('deleting a message calls the server',
    rpcCalls.some((c) => c.fn === 'astro_delete_message'));
}

// ------------------------------------------------------ settings round-trip ---
tab('Settings').click();
await settle(6);
const labelFor = (needle) => [...document.querySelectorAll('label.check')]
  .find((l) => l.textContent.includes(needle));
const btnNamed = (name) => [...document.querySelectorAll('button')]
  .find((b) => b.textContent.trim() === name);

check('settings offers the no-cut-off switch', Boolean(labelFor('No automatic absent marking')));
const noAbsentBox = labelFor('No automatic absent marking')?.querySelector('input');
const absentInput = [...document.querySelectorAll('label.field')]
  .find((l) => l.textContent.includes('Absent after'))?.querySelector('input[type="time"]');
check('no absent cut-off in the school row leaves the switch on and the field disabled',
  noAbsentBox?.checked === true && absentInput?.disabled === true);

if (noAbsentBox && absentInput) {
  noAbsentBox.click();
  absentInput.value = '09:45';
  btnNamed('Save timings').click();
  await settle(6);
  let body = rpcCalls.filter((c) => c.fn === 'astro_update_settings').pop()?.body;
  check('saving timings sends the cut-off and clears the clear-flag',
    body?.p_absent_after === '09:45' && body?.p_clear_absent_after === false);
  check('saving timings sends the weekly-off days',
    Array.isArray(body?.p_weekly_off) && body.p_weekly_off.includes(0));

  noAbsentBox.click();
  btnNamed('Save timings').click();
  await settle(6);
  body = rpcCalls.filter((c) => c.fn === 'astro_update_settings').pop()?.body;
  check('a school with no cut-off clears it instead of keeping the old time',
    body?.p_clear_absent_after === true && body?.p_absent_after === null);
  check('the timing save is reported back to the office',
    document.body.textContent.includes('version'));
}

// ------------------------------------------------------------- student ----
const studentHost = document.createElement('div');
document.body.append(studentHost);
const { renderStudent } = await import('../../web/js/student.js');
renderStudent(studentHost, { whoami: F.PARENT_WHOAMI });
await settle(6);

check('parent view renders the child header', studentHost.textContent.includes('Demo Student'));
check('calendar draws one cell per day', studentHost.querySelectorAll('.cal-day').length === F.CALENDAR.days.length);
check('calendar shows the attendance percentage', studentHost.textContent.includes('88.9% attendance'));
check('calendar legend covers every status',
  ['Present', 'Late', 'Absent', 'Leave', 'Holiday', 'Weekly off']
    .every((x) => studentHost.textContent.includes(x)));

const studentTab = (label) => [...studentHost.querySelectorAll('nav.tabs button')]
  .find((b) => b.textContent.trim() === label);

studentTab('Notices').click();
await settle(6);
check('notice tab shows the notice', studentHost.textContent.includes('PTM on Saturday'));
check('critical notices are visually flagged', Boolean(studentHost.querySelector('.notice-critical')));
check('dismiss button exists on each notice', studentHost.querySelectorAll('.notice .icon-btn').length >= 1);

studentTab('Messages').click();
await settle(6);
check('message thread shows the school message', studentHost.textContent.includes('You were late 3 times'));
check('message thread has a composer', Boolean(studentHost.querySelector('textarea')));
check('opening the thread marks it read', rpcCalls.some((c) => c.fn === 'astro_mark_thread_read'));

const writer = studentHost.querySelector('textarea');
const sendBtn = () => [...studentHost.querySelectorAll('.composer button')]
  .find((b) => b.textContent.trim() === 'Send');
writer.value = 'The bus will be late today';
failRpc = 'astro_student_send_message';
sendBtn().click();
check('a message shows up immediately, before the server answers',
  studentHost.querySelector('.bubble.pending')?.textContent.includes('The bus will be late today'));
await settle(6);
check('a rejected message is withdrawn and the text handed back',
  !studentHost.querySelector('.bubble.pending')
  && studentHost.querySelector('textarea')?.value === 'The bus will be late today');
failRpc = null;

studentHost.querySelector('textarea').value = 'Thank you';
sendBtn().click();
await settle(8);
check('a sent message carries a body and an idempotency key',
  rpcCalls.some((c) => c.fn === 'astro_student_send_message'
    && c.body?.p_body === 'Thank you' && Boolean(c.body?.p_client_id)));

studentTab('Leave').click();
await settle(6);
check('leave tab has the request form', studentHost.textContent.includes('Ask for leave'));
check('leave tab lists existing requests', studentHost.textContent.includes('Your requests'));

// --------------------------------------------------------- error surface ---
const errHost = document.createElement('div');
document.body.append(errHost);
failRpc = 'astro_student_calendar';
renderStudent(errHost, { whoami: F.PARENT_WHOAMI });
await settle(6);
check('a failing RPC is shown, not swallowed', errHost.textContent.includes('Could not load attendance'));
failRpc = null;

// ------------------------------------------------------ teacher (writes) ---
const { renderAdmin } = await import('../../web/js/admin.js');
const teacherHost = document.createElement('div');
document.body.append(teacherHost);
renderAdmin(teacherHost, { whoami: { ...F.ADMIN_WHOAMI, role: 'teacher' } });
await settle(6);
check('a teacher can see the day overview', teacherHost.textContent.includes('Demo Student'));
[...teacherHost.querySelectorAll('nav.tabs button')].find((b) => b.textContent.trim() === 'Settings').click();
await settle(6);
check('a teacher is not offered timing edits',
  !teacherHost.textContent.includes('Save timings')
  && teacherHost.textContent.includes('Only an administrator can change school timings'));
[...teacherHost.querySelectorAll('nav.tabs button')].find((b) => b.textContent.trim() === 'Devices').click();
await settle(6);
check('a teacher can see the terminal but cannot command it',
  teacherHost.textContent.includes('ASTRO-RNK-01')
  && teacherHost.textContent.includes('Only an administrator can send test commands'));

// ------------------------------------------------------------ xss safety ---
const hostile = '<img src=x onerror="window.__pwned=1">';
const originalNotices = F.FEED.notices;
F.FEED.notices = [
  { ...originalNotices[0], id: 'n-critical', title: 'Critical: holiday tomorrow', priority: 'critical' },
  { ...originalNotices[0], id: 'n-normal', title: 'Plain notice', priority: null, body: hostile, pinned: false },
];
const xssHost = document.createElement('div');
document.body.append(xssHost);
renderStudent(xssHost, { whoami: F.PARENT_WHOAMI });
await settle(6);
[...xssHost.querySelectorAll('nav.tabs button')].find((b) => b.textContent.trim() === 'Notices').click();
await settle(6);
check('notice markup is rendered as text, not parsed',
  xssHost.textContent.includes('onerror="window.__pwned=1"'));
check('no element is injected from notice content', xssHost.querySelectorAll('img').length === 0);
check('a missing priority still renders as a normal notice', Boolean(xssHost.querySelector('.notice-normal')));
check('a missing priority shows no urgency chip',
  !['Urgent', 'Important'].some((t) => xssHost.querySelector('.notice-normal')?.textContent.includes(t)));

F.FEED.notices = [];
const emptyHost = document.createElement('div');
document.body.append(emptyHost);
renderStudent(emptyHost, { whoami: F.PARENT_WHOAMI });
await settle(6);
[...emptyHost.querySelectorAll('nav.tabs button')].find((b) => b.textContent.trim() === 'Notices').click();
await settle(6);
check('an empty notice feed shows the empty state', emptyHost.textContent.includes('No notices right now'));
F.FEED.notices = originalNotices;

// ------------------------------------------------------------- sign out ---
const out = [...document.querySelectorAll('.topbar button')].find((b) => b.textContent.includes('Sign out'));
check('sign-out button exists', Boolean(out));
if (out) {
  out.click();
  await settle(8);
  check('signing out returns to the login form', Boolean(document.querySelector('input[type="email"]')));
  check('signing out clears the stored session', localStorage.getItem('astro.session.v1') === null);
}

// -------------------------------------------------------- viewer (read) ---
const viewerHost = document.createElement('div');
document.body.append(viewerHost);
renderAdmin(viewerHost, { whoami: { ...F.ADMIN_WHOAMI, role: 'viewer' } });
await settle(6);
check('viewer still sees the day overview', viewerHost.textContent.includes('Demo Student'));
check('viewer is told the account is read-only', /Read-only view/.test(viewerHost.textContent));
check('viewer gets no write controls', !viewerHost.textContent.includes('Set holiday'));
check('viewer cannot open the add-student form', !viewerHost.textContent.includes('+ New student'));

// --------------------------------------------------------------- report ---
check('no console/rejection errors in the whole run', consoleErrors.length === 0, consoleErrors.join(' | '));
console.log(`\n  web dashboard: ${pass} passed, ${failures.length} failed`);
if (failures.length) {
  for (const f of failures) console.log(`  FAIL: ${f}`);
  process.exitCode = 1;
} else {
  console.log('  all assertions passed\n');
}
