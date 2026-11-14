// End-to-end check of the website dashboard: the real web/index.html and the real
// web/supabase-bridge.js run in headless Chromium, with *.supabase.co answered
// by fake_supabase.mjs. Every step drives the app the way a person would (the
// login form, the Add Student form, the edit dialog...) and then looks at what
// actually reached the database.
//
//   cd tools/e2e && npm install && npm test
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createFake } from './fake_supabase.mjs';

import { launchBrowser, report } from './browser.mjs';

const WEB = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../web');
const SHOTS = process.env.SHOTS || '';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ---- static server for web/ (anything under /api/ reaching it is a leak) ----
const leaks = [];
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'application/javascript; charset=utf-8' };
const server = http.createServer((req, res) => {
  const p = new URL(req.url, 'http://x').pathname;
  if (p.startsWith('/api/') || p === '/addStudent' || p === '/login') leaks.push(req.method + ' ' + p);
  const file = path.join(WEB, p === '/' ? '/index.html' : decodeURIComponent(p));
  if (req.method !== 'GET' || !file.startsWith(WEB) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    res.writeHead(404); return res.end('not found');
  }
  res.writeHead(200, { 'content-type': MIME[path.extname(file)] || 'application/octet-stream', 'cache-control': 'no-store' });
  fs.createReadStream(file).pipe(res);
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const ORIGIN = 'http://127.0.0.1:' + server.address().port;

// ---- browser + fake Supabase ----
const fake = createFake();
const db = fake.db;
const browser = await launchBrowser(['--hide-scrollbars']);
const page = await browser.newPage();
await page.setViewport({ width: 1280, height: 860 });
await page.emulateTimezone('Asia/Kolkata');
const pageErrors = [];
page.on('pageerror', (e) => pageErrors.push(String(e.message || e)));
page.on('console', (m) => { if (m.type() === 'error' && /astro cloud/.test(m.text())) pageErrors.push(m.text()); });
await page.setRequestInterception(true);
page.on('request', (req) => {
  const u = new URL(req.url());
  if (!u.hostname.endsWith('supabase.co')) return req.continue();
  const cors = { 'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': '*' };
  if (req.method() === 'OPTIONS') return req.respond({ status: 204, headers: cors });
  const r = fake.handle(req.method(), req.url(), req.headers(), req.postData());
  req.respond({ status: r.status, headers: { ...cors, 'content-type': 'application/json' }, body: r.body == null ? '' : JSON.stringify(r.body) });
});

// ---- helpers ----
let passed = 0, failed = 0;
const check = (name, cond, detail) => {
  if (cond) { passed++; console.log('  ok   ' + name); }
  else {
    failed++; console.log('  FAIL ' + name + (detail !== undefined ? '\n         got: ' + JSON.stringify(detail) : ''));
    if (process.env.GITHUB_ACTIONS) report('error', 'Dashboard test failed: ' + name + (detail !== undefined ? ' (got: ' + JSON.stringify(detail).slice(0, 400) + ')' : ''));
  }
};
const ev = (fn, ...a) => page.evaluate(fn, ...a);
const until = async (fn, ms = 15000, ...a) => {
  const end = Date.now() + ms;
  for (;;) {
    const v = await ev(fn, ...a).catch(() => false);
    if (v || Date.now() > end) return v;
    await sleep(200);
  }
};
const hookToasts = () => ev(() => {
  window.__toasts = [];
  const t0 = window.toast;
  window.toast = function (a, b, c) { window.__toasts.push((a || '') + ' | ' + (b || '') + ' | ' + (c || '')); return t0.apply(this, arguments); };
});
const toasts = () => ev(() => { const t = window.__toasts.slice(); window.__toasts.length = 0; return t; });
const setVal = (sel, v) => ev((s, val) => {
  const el = document.querySelector(s); el.value = val;
  el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true }));
}, sel, v);
const post = (p, body) => ev((url, b) => fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) })
  .then((r) => r.json().then((j) => ({ status: r.status, j }))), p, body);
const get = (p) => ev((url) => fetch(url).then((r) => r.json().then((j) => ({ status: r.status, j }))), p);
const shot = async (name) => { if (SHOTS) await page.screenshot({ path: path.join(SHOTS, name + '.png') }); };
const login = async (id, pw) => {
  await setVal('#login-id', id); await setVal('#login-pw', pw);
  await page.click('#login-btn');
};
const loginError = () => ev(() => { const e = document.querySelector('#login-err'); return e && !e.classList.contains('hidden') ? e.textContent.trim() : ''; });
const addStudent = async (f) => {
  await ev(() => go('addstudent'));
  await sleep(300);
  for (const [sel, v] of Object.entries({ '#ns-rfid': '', ...f })) await setVal(sel, v);   // a card number left over from a refused save stays in the form
  await toasts();
  await page.click('#ns-save-btn');
};
const stu = (name) => db.students.find((s) => s.name === name);
const cardsOf = (name) => db.cards.filter((c) => stu(name) && c.student_id === stu(name).id && c.active).map((c) => c.uid);
const calls = (re) => db.calls.filter((c) => re.test(c.path)).length;

try {
  console.log('\n1. First visit');
  await page.goto(ORIGIN + '/', { waitUntil: 'domcontentloaded' });
  check('bridge is loaded before the app', await ev(() => typeof window.AstroWeb === 'object'));
  check('login screen is showing', await until(() => document.querySelector('#login').classList.contains('on'), 8000));   // after the boot splash
  await sleep(600);
  await hookToasts();
  check('cloud light is honest: "connected" only after Supabase answered', /Cloud: connected/.test(await ev(() => document.querySelector('#sys-cloud').textContent)));
  check('device light does not claim "online" before sign-in', /shown after sign-in/.test(await ev(() => document.querySelector('#sys-dev').textContent)));
  await shot('01-login');
  check('sign-in screen does not offer a student login', await ev(() => { const t = document.querySelector('#login').innerText; return !/Fill Student/.test(t) && !/student name/i.test(t) && /Staff sign in here/.test(t); }));

  console.log('\n2. Sign-in');
  await login('astro@gmail.com', 'nope'); await sleep(900);
  check('wrong password is refused with a clear message', (await loginError()) === 'Wrong email or password.', await loginError());
  await login('admin', 'admin123'); await sleep(600);
  check('the old built-in "admin / admin123" back door is gone', /staff email/.test(await loginError()) && !(await ev(() => document.querySelector('#app').classList.contains('on'))), await loginError());
  await login('parent@astro-school.test', 'parent123'); await sleep(1200);
  check('an account that is not staff cannot open the dashboard', /not on the staff list/.test(await loginError()), await loginError());
  check('...and leaves no session behind', await ev(() => !localStorage.getItem('astro.cloud.session.v1') && !localStorage.getItem('astro_tok')));
  await login('astro@gmail.com', 'admin123');
  check('the real admin signs in', await until(() => document.querySelector('#app').classList.contains('on') && SESSION.role === 'admin'));
  await hookToasts();
  check('dashboard starts from the real (empty) database', await ev(() => DB.students.length === 0));
  check('timing rules come from the database (08:00, late after 20 min)', await ev(() => CFG.start === '08:00' && CFG.lateAfter === 20 && CFG.close === '14:00'), await ev(() => [CFG.start, CFG.lateAfter, CFG.close]));
  check('next roll number offered is 1001', await ev(() => CFG.nextStudentPassword === 1001));
  check('gate device shows OFFLINE (last heartbeat was 4 hours ago)', await ev(() => DEVICE.online === false && DEVICE.state === 'red'), await ev(() => [DEVICE.online, DEVICE.state]));
  check('cloud shows online', await ev(() => CLOUD.mode === 'online'), await ev(() => CLOUD.mode));

  console.log('\n3. Add Student (the form in the app)');
  await ev(() => go('students')); await sleep(300);
  check('Students page offers "Add Student"', /Add Student|Add first student/i.test(await ev(() => document.querySelector('#view, main, #app').innerText)));
  await shot('02-students-empty');
  await ev(() => go('addstudent')); await sleep(300);
  const addText = await ev(() => document.querySelector('#app').innerText);
  check('form explains that card numbers are typed on the website', /Type the card number/.test(addText) && !/Waiting for RFID card tap/.test(addText));
  check('device-only password field is hidden', await ev(() => getComputedStyle(document.querySelector('#ns-pass').closest('.field')).display === 'none'));
  await shot('03-add-form');

  await addStudent({ '#ns-name': 'Meera  Pandey', '#ns-rfid': '04a3b2c1', '#ns-cls': '10', '#ns-sec': 'B', '#ns-pemail': 'Mum@Example.com', '#ns-pphone': '+91 98765 43210' });
  check('student reaches the database', await until(() => CURRENT === 'students' && DB.students.some((s) => s.name === 'Meera Pandey')) && !!stu('Meera Pandey'), db.students);
  check('...with roll 1001, parent contact and class 10-B (class created on demand)',
    stu('Meera Pandey') && stu('Meera Pandey').roll === '1001' && stu('Meera Pandey').g_email === 'mum@example.com' &&
    db.classes.some((c) => c.name === '10' && c.section === 'B' && c.id === stu('Meera Pandey').class_id), stu('Meera Pandey'));
  check('...and the typed card 04A3B2C1 linked', cardsOf('Meera Pandey').join() === '04A3B2C1', db.cards);
  check('roster shows her under that card', await ev(() => DB.students.some((s) => s.rfid === '04A3B2C1' && s.cls === '10' && s.sec === 'B')));
  await sleep(400);
  check('no "share this password" dialog (passwords are device-only)', await ev(() => !/Share this password/.test(document.querySelector('#modals').innerText)));
  check('success toast shown', (await toasts()).some((t) => /Student created/.test(t)));
  check('the roster does not print a made-up student password', await ev(() => {
    const th = [...document.querySelectorAll('table.tbl th')].find((x) => /password/i.test(x.textContent));
    return !!document.querySelector('table.web-stu') && th && getComputedStyle(th).display === 'none';
  }));
  await shot('04-students-one');

  await addStudent({ '#ns-name': 'Rohan Singh' });
  check('blank card -> saved with an auto card (A5......) and roll 1002',
    await until(() => DB.students.some((s) => s.name === 'Rohan Singh')) && stu('Rohan Singh').roll === '1002' && /^A5[0-9A-F]{6}$/.test(cardsOf('Rohan Singh')[0] || ''), [stu('Rohan Singh'), db.cards]);
  const rohanCard = cardsOf('Rohan Singh')[0];

  await addStudent({ '#ns-name': 'Card Thief', '#ns-rfid': '04A3B2C1' }); await sleep(900);
  let t = await toasts();
  check('a card that is already in use is refused', t.some((x) => /already belongs to Meera Pandey/.test(x)) && db.students.length === 2, t);
  check('...and the owner is NOT overwritten', !!stu('Meera Pandey') && !stu('Card Thief'));
  await addStudent({ '#ns-name': 'Bad Card', '#ns-rfid': 'XYZ123' }); await sleep(700);
  t = await toasts();
  check('a malformed card number is refused with help text', t.some((x) => /8 to 20 characters/.test(x)) && db.students.length === 2, t);
  await addStudent({ '#ns-name': 'Sys Card', '#ns-rfid': 'CA4FBE2C' }); await sleep(700);
  t = await toasts();
  check('the device\u2019s own Admin card cannot be given to a student', t.some((x) => /Admin card/.test(x)) && db.students.length === 2, t);
  await addStudent({ '#ns-name': 'Dup Roll', '#ns-roll': '1001' }); await sleep(900);
  t = await toasts();
  check('a roll number that is taken is refused', t.some((x) => /Roll number 1001 is already taken/.test(x)) && db.students.length === 2, t);

  console.log('\n4. Edit, attendance, live gate scans');
  await ev(() => { go('students'); openStudentEdit('04A3B2C1'); }); await sleep(300);
  await setVal('#se-name', 'Meera K Pandey'); await setVal('#se-cls', '9'); await setVal('#se-sec', 'A');
  await page.click('#se-save');
  check('edit dialog saves name and class', await until(() => DB.students.some((s) => s.name === 'Meera K Pandey' && s.cls === '9')) && stu('Meera K Pandey').class_id === db.classes[0].id, db.students);
  check('...without touching her card or roll', cardsOf('Meera K Pandey').join() === '04A3B2C1' && stu('Meera K Pandey').roll === '1001');

  const today = fake.schoolToday();
  let r = await post('/api/attendance/mark', { rfid: '04A3B2C1', date: today, status: 'late' });
  check('manual mark is written', r.j.ok === true && db.attendance.some((a) => a.student_id === stu('Meera K Pandey').id && a.status === 'late'), r);
  check('dashboard picks it up', await until(() => { const s = DB.students.find((x) => x.rfid === '04A3B2C1'); return s && s.status === 'late' && s.counts.late === 1; }, 8000),
    await ev(() => DB.students.map((s) => [s.name, s.status, s.counts])));
  r = await post('/api/attendance/mark', { rfid: '04A3B2C1', date: '2999-01-01', status: 'present' });
  check('a future date is refused, in plain words', r.status === 400 && /future date/.test(r.j.message), r);

  fake.kioskScan(rohanCard, 'present');
  check('a card tapped at the gate appears by itself (within ~10 s)', await until((c) => { const s = DB.students.find((x) => x.rfid === c); return s && s.status === 'present'; }, 14000, rohanCard),
    await ev(() => DB.students.map((s) => [s.name, s.status])));
  check('...the device light turns ONLINE with its heartbeat', await until(() => DEVICE.online === true && DEVICE.state === 'green', 6000), await ev(() => [DEVICE.online, DEVICE.state]));
  check('...and a notification is raised', await until(() => DB.notifications.some((n) => /Rohan Singh/.test(n.title)), 6000), await ev(() => DB.notifications.map((n) => n.title)));
  await ev(() => go('home')); await sleep(400); await shot('05-home-live');
  check('Home raises no made-up hardware alert', await ev(() => !/health attention items/.test(document.querySelector('#main, main, body').innerText)),
    await ev(() => Object.entries(HW).filter(([, v]) => v.state !== 'ok').map(([k, v]) => k + ':' + v.state)));
  check('Home does not claim "all hardware checks pass" or a Wi-Fi strength it cannot see',
    await ev(() => { const t = document.body.innerText; return !/all hardware checks pass/.test(t) && !/0 dBm\s*Strong/.test(t) && /checked on the gate device/.test(t); }));
  await ev(() => go('health')); await sleep(400); await shot('06-health');
  check('Health page says its readings live on the device', await ev(() => {
    const t = document.body.innerText;
    return /This page belongs to the gate device/.test(t) && /online now/.test(t) && !/\d+\/\d+ pass/.test(t) &&
      /CHIP TEMP\s*—/i.test(t) && /FREE HEAP\s*—/i.test(t) && /SIGNAL\s*— dBm/i.test(t) && !/\b0 dBm/.test(t) && !/R307/.test(t);
  }), await ev(() => document.querySelector('.web-note').parentElement.innerText.slice(0, 2500)));

  console.log('\n5. Session refresh');
  db.access.forEach((v) => { v.exp = 0; });
  const refreshesBefore = calls(/grant_type=refresh_token/);
  r = await post('/api/holidays', { date: '2026-12-25' });
  check('expired token is refreshed silently and the write still lands', r.j.ok === true && db.holidays.some((h) => h.date === '2026-12-25') && calls(/grant_type=refresh_token/) === refreshesBefore + 1, [r, calls(/grant_type=refresh_token/)]);
  check('holiday shows in the app', await until(() => DB.holidays.indexOf('2026-12-25') >= 0, 6000));
  r = await post('/api/holiday/delete', { date: '2026-12-25' });
  check('holiday can be removed', r.j.ok === true && db.holidays.length === 0);

  console.log('\n6. Notices, messages, settings');
  r = await post('/api/notices', { id: 0, title: 'Sports Day', body: 'Ground at 8 AM', priority: 'important', audience: 'All', pinned: true, status: 'published' });
  check('notice is published', r.j.ok === true && db.notices.length === 1 && db.notices[0].pinned === true && db.notices[0].priority === 'important', db.notices);
  check('...and listed in the app', await until(() => DB.notices.some((n) => n.title === 'Sports Day' && n.pinned && typeof n.id === 'number'), 6000), await ev(() => DB.notices));
  await ev(() => noticeAct(DB.notices[0].id, 'unpin'));
  check('unpin from the notice board updates the same notice', await until(() => true, 10) && (await (async () => { await sleep(900); return db.notices.length === 1 && db.notices[0].pinned === false; })()), db.notices);
  r = await post('/api/notice/delete', { id: await ev(() => DB.notices[0].id) });
  check('notice can be deleted', r.j.ok === true && db.notices.length === 0, r);

  r = await post('/api/dm', { rfids: ['04A3B2C1', rohanCard], subject: 'Fees', body: 'Please pay by Friday' });
  check('a message to two students creates two messages', r.j.ok === true && r.j.sent === 2 && db.messages.length === 2, r);

  r = await post('/api/settings', { start: '08:00', close: '14:00', lateAfter: 30, lateAfterMin: 30, absentAfter: 60, absentAfterMin: 60, autoAbsent: false, weeklyOff: true, weeklyOffDay: 0, messagePresent: 'x' });
  check('timing rule change is saved (late after 30 min -> 08:30)', r.j.ok === true && db.school.late_after === '08:30', [r, db.school]);
  check('...untouched rules stay untouched', db.school.absent_after === null && db.school.weekly_off.join() === '0' && db.school.day_start === '08:00', db.school);
  r = await post('/api/settings', { fingerConfirm: true });
  check('a device-only setting is refused honestly instead of faking success', r.status === 400 && /school device/.test(r.j.message), r);
  r = await post('/api/wifi/connect', { ssid: 'x', password: 'y' });
  check('Wi-Fi control says it lives on the device', r.status === 400 && /school device/.test(r.j.message), r);
  r = await get('/api/wifi/scan');
  check('device-only pages still open (empty, not broken)', r.status === 200 && r.j.ok === true && Array.isArray(r.j.items), r);

  console.log('\n7. Change card, delete');
  await ev((c) => { go('students'); bindRfidFlow(c); }, rohanCard); await sleep(300);
  await setVal('#cb-card', '0a:1b:2c:3d'); await page.click('#cb-save');
  check('typed replacement card is saved', await until(() => DB.students.some((s) => s.rfid === '0A1B2C3D'), 8000) && cardsOf('Rohan Singh').join() === '0A1B2C3D', db.cards);
  check('...and the old card stops working', db.cards.some((c) => c.uid === rohanCard && !c.active && !c.student_id), db.cards);

  await ev(() => delStuDo('04A3B2C1'));
  check('deleting a student WITH attendance archives her (history kept)', await until(() => !DB.students.some((s) => s.rfid === '04A3B2C1'), 8000) &&
    stu('Meera K Pandey').active === false && db.attendance.some((a) => a.student_id === stu('Meera K Pandey').id), db.students);
  await addStudent({ '#ns-name': 'No History' });
  await until(() => DB.students.some((s) => s.name === 'No History'));
  const nh = await ev(() => DB.students.find((s) => s.name === 'No History').rfid);
  await ev((c) => delStuDo(c), nh);
  check('deleting a student WITHOUT attendance removes them completely', await until(() => !DB.students.some((s) => s.name === 'No History'), 8000) && !stu('No History'), db.students);

  console.log('\n8. Reload, sign out, dead session');
  await page.reload({ waitUntil: 'domcontentloaded' });
  check('reload keeps you signed in', await until(() => document.querySelector('#app').classList.contains('on') && SESSION.role === 'admin' && DB.students.length === 1, 10000),
    await ev(() => [document.querySelector('#app').className, DB.students.length]));
  await hookToasts();
  await ev(() => logout()); await sleep(300);
  await ev(() => { const b = [...document.querySelectorAll('#modals button')].find((x) => /Sign out/.test(x.textContent)); b.click(); });
  check('sign out returns to the login screen', await until(() => document.querySelector('#login').classList.contains('on')));
  check('...and the cloud session is revoked and forgotten', await until(() => !localStorage.getItem('astro.cloud.session.v1'), 16000) && calls(/auth\/v1\/logout/) === 1, calls(/auth\/v1\/logout/));
  r = await get('/api/students');
  check('signed out: data requests are refused', r.status === 401, r);

  await login('astro@gmail.com', 'admin123');
  await until(() => document.querySelector('#app').classList.contains('on') && SESSION.role === 'admin');
  db.access.clear(); db.refresh.clear();                       // e.g. the password was changed elsewhere
  await page.reload({ waitUntil: 'domcontentloaded' });
  check('a session that is no longer valid lands back on the login screen', await until(() => document.querySelector('#login') && document.querySelector('#login').classList.contains('on') && !localStorage.getItem('astro_tok') && SESSION.role === null, 12000),
    await ev(() => [document.querySelector('#login').className, localStorage.getItem('astro_tok')]).catch(String));

  console.log('\n9. Nothing leaked, nothing crashed');
  check('no /api request ever reached the web host (the pretend database never ran)', leaks.length === 0, leaks.slice(0, 5));
  check('no script errors', pageErrors.length === 0, pageErrors.slice(0, 5));
} catch (e) {
  failed++;
  console.log('  FAIL test crashed: ' + (e && e.stack || e));
  if (process.env.GITHUB_ACTIONS) report('error', 'Dashboard test crashed: ' + String((e && e.stack) || e).slice(0, 600));
  await shot('crash');
}

console.log('\n' + passed + ' passed, ' + failed + ' failed');
await browser.close(); server.close();
process.exit(failed ? 1 : 0);
