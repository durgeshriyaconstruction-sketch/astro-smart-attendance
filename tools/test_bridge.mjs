// Offline contract test for web/supabase-bridge.js
// Runs the bridge in a stubbed browser and asserts the shapes the UI expects.
//   node tools/test_bridge.mjs

import fs from 'fs';
import vm from 'vm';

const src = fs.readFileSync('/home/user/astro-smart-attendance/web/supabase-bridge.js', 'utf8');

const STUDENTS = [
  { id:'u1', roll_no:'01', full_name:'Aarav Sharma', guardian_email:'g1@x.com', guardian_phone:'999',
    fingerprint_id:null, active:true, class_id:'c1', classes:{ name:'Class 9', section:'A' } },
  { id:'u2', roll_no:'02', full_name:'Diya Verma', guardian_email:null, guardian_phone:null,
    fingerprint_id:5, active:true, class_id:'c1', classes:{ name:'Class 9', section:'A' } },
];
const CARDS = [ { student_id:'u1', card_uid:'04a3b2c1' }, { student_id:'u2', card_uid:'AABBCCDD' } ];
const today = new Date().toLocaleDateString('en-CA', { timeZone:'Asia/Kolkata' });
const ATT = [
  { student_id:'u1', attendance_date:today, status:'present', marked_at:today+'T08:42:00+05:30', method:'rfid' },
  { student_id:'u1', attendance_date:'2026-11-10', status:'late', marked_at:'2026-11-10T09:12:00+05:30', method:'rfid' },
  { student_id:'u2', attendance_date:'2026-11-10', status:'absent', marked_at:null, method:'auto' },
];
const NOTICES = [ { id:'9d1f0a2c-1111-2222-3333-444455556666', title:'Sports Day', body:'Ground at 8 AM',
  priority:'important', audience:'all', pinned:true, created_at:'2026-11-12T04:00:00Z' } ];
const DEV = [ { device_code:'ASTRO-ESP32-01', firmware:'26.11.7', last_seen:new Date().toISOString(),
  ip:'192.168.1.42', wifi_rssi:-54, active:true } ];

const calls = [];
function fakeFetch(url, opts = {}) {
  calls.push((opts.method || 'GET') + ' ' + url);
  const json = (v) => Promise.resolve({ ok:true, status:200, text:()=>Promise.resolve(JSON.stringify(v)) });
  if (url.includes('/auth/v1/token')) return Promise.resolve({ ok:true, status:200,
    json: () => Promise.resolve({ access_token:'tok', user:{ id:'uid-1' } }) });
  if (url.includes('/rest/v1/students')) return json(STUDENTS);
  if (url.includes('/rest/v1/rfid_cards')) return json(CARDS);
  if (url.includes('/rest/v1/attendance')) return json(ATT);
  if (url.includes('/rest/v1/notices')) return json(NOTICES);
  if (url.includes('/rest/v1/school_holidays')) return json([{ holiday_date:'2026-11-08' }]);
  if (url.includes('/rest/v1/devices')) return json(DEV);
  if (url.includes('/rest/v1/members')) return json([{ role:'admin' }]);
  if (url.includes('/rest/v1/schools')) return json([{ id:'sch-1', name:'Test School' }]);
  if (url.includes('/rest/v1/leave_requests')) return json([]);
  return json([]);
}

const store = {};
const el = () => ({ style:{}, value:'', classList:{ add(){}, remove(){} }, textContent:'',
  disabled:false, innerHTML:'', appendChild(){}, remove(){}, querySelector:()=>null,
  addEventListener(){}, closest:()=>null, onclick:null, dataset:{} });

const sandbox = {
  console: { log(){}, error(){}, warn(){} },
  setTimeout, clearTimeout, Promise, JSON, Date, Math, Number, String, Object, Array, Error, RegExp,
  fetch: fakeFetch,
  localStorage: { getItem: k => store[k] ?? null, setItem: (k,v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; } },
};
sandbox.window = sandbox;
sandbox.document = {
  readyState:'complete',
  getElementById: (id) => {
    const e = el();
    if (id === 'login-id') e.value = 'astro@gmail.com';
    if (id === 'login-pw') e.value = 'admin123';
    return e;
  },
  createElement: () => el(),
  addEventListener(){},
  body: { appendChild(){} },
  querySelector: () => null,
  querySelectorAll: () => [],
};
sandbox.window.loginError = () => {};
sandbox.window.toast = () => {};
sandbox.window.startSession = () => { sandbox.__sessionStarted = true; };
sandbox.window.syncAll = () => { sandbox.__synced = true; };
sandbox.window.api = function originalApi(){ return Promise.resolve({ ok:true, original:true }); };
sandbox.window.localApiFallback = function originalFallback(){ return Promise.resolve({ ok:true, original:true }); };

vm.createContext(sandbox);
vm.runInContext(src, sandbox, { filename:'supabase-bridge.js' });

const out = [];
const check = (name, cond, extra='') => out.push(`${cond ? 'PASS' : 'FAIL'}  ${name}${extra ? '  ' + extra : ''}`);

// reads
const stu = await sandbox.window.api('/api/students?token=x');
check('students count = 2', stu.items.length === 2, JSON.stringify(stu.items.length));
const a = stu.items[0];
check('name mapped', a.name === 'Aarav Sharma');
check('rfid uppercased from card', a.rfid === '04A3B2C1', a.rfid);
check('class+section joined', a.className === 'Class 9' && a.section === 'A');
check('today status present', a.status === 'present', a.status);
check('counts present=1 late=1', a.present === 1 && a.late === 1, `${a.present}/${a.late}`);
check('percentage computed (2 marked, 0 absent)', a.percentage === 100, String(a.percentage));
check('lastTime is HH:MM', /^\d{2}:\d{2}$/.test(a.lastTime), a.lastTime);
const b = stu.items[1];
check('fingerprint flag', b.fingerprint === true && b.fingerprintId === 5);
check('absent counted', b.absent === 1);

const cal = await sandbox.window.api('/api/calendar');
check('calendar items = 3', cal.items.length === 3);
check('calendar carries rfid', cal.items[0].rfid === '04A3B2C1');
check('holidays passed through', cal.holidays[0] === '2026-11-08');

const nt = await sandbox.window.api('/api/notices');
check('notice mapped', nt.items[0].title === 'Sports Day');
check('notice id is numeric+stable', Number.isFinite(nt.items[0].id) && nt.items[0].id !== 0, String(nt.items[0].id));

const cloud = await sandbox.window.api('/api/cloud');
check('cloud online (device fresh)', cloud.state === 'online', cloud.state);
check('cloud host real', cloud.databaseHost.includes('supabase.co'));

const health = await sandbox.window.api('/api/health');
check('health reports 2 students', health.students === 2, String(health.students));
check('health marks hardware unknown', health.heap === 0);

// unknown route must delegate to the original
const unk = await sandbox.window.api('/api/wifi/scan');
check('unknown route delegates', unk && unk.original === true);

// login
await sandbox.window.doLogin();
await new Promise(r => setTimeout(r, 30));
check('login reached session', sandbox.__sessionStarted === true);
check('token stored', !!store['sb_token']);

// add student
const saved = await sandbox.astroBridge.saveStudent({ name:'Meera Pandey', roll:'03', className:'Class 9', section:'B', rfid:'deadbeef' });
check('saveStudent ok', saved && saved.ok === true || saved === null, JSON.stringify(saved));
check('POST students issued', calls.some(c => c.startsWith('POST') && c.includes('/rest/v1/students')));

console.log(out.join('\n'));
console.log('\nfailures:', out.filter(l => l.startsWith('FAIL')).length);
console.log('\nrequests made:\n  ' + [...new Set(calls)].join('\n  '));
