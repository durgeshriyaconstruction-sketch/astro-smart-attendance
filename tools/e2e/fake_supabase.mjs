// An in-memory stand-in for the school's Supabase project, used by test_bridge.mjs.
//
// It answers the handful of Auth and RPC endpoints web/supabase-bridge.js calls,
// with the same response shapes the real database returned when the migrations
// were dry-run against it (see supabase/migrations/20261114000004_...). It is a
// test double, not a re-implementation: just enough rules to prove the bridge
// reads and writes the right things.
import crypto from 'node:crypto';

const uuid = () => crypto.randomUUID();
const schoolToday = () => new Date(Date.now() + 5.5 * 3600e3).toISOString().slice(0, 10);   // Asia/Kolkata
const hhmmNow = () => new Date(Date.now() + 5.5 * 3600e3).toISOString().slice(11, 16);

export function createFake() {
  const db = {
    school: { id: 'b081c8b6-2374-4484-807c-c4156b3791be', name: 'The Aditya Birla Public School, Renukoot', code: 'ABPS-RNK',
              timezone: 'Asia/Kolkata', day_start: '08:00', late_after: '08:20', absent_after: null, day_end: '14:00',
              weekly_off: [0], alert_emails: true },
    classes: [{ id: '9c6d7719-e3d7-4015-ae62-364e962baaed', name: '9', section: 'A', teacher: 'Class Teacher' }],
    students: [],        // {id, roll, name, class_id, g_name, g_email, g_phone, fp, active}
    cards: [],           // {uid, student_id, active}
    attendance: [],      // {id, student_id, date, status, time, method}
    holidays: [], notices: [], leaves: [], messages: [],
    device: { code: 'ASTRO-RNK-01', name: 'Main gate terminal', location: 'Main gate', firmware: '26.11.7', ip: null, rssi: null,
              active: true, last_seen: Date.now() - 4 * 3600e3, last_boot: Date.now() - 4 * 3600e3 - 300e3 },
    users: {
      'astro@gmail.com': { id: '11cc3148-3f84-4c55-8df8-e611e0bc2ba6', password: 'admin123', role: 'admin' },
      'parent@astro-school.test': { id: uuid(), password: 'parent123', role: null }
    },
    access: new Map(), refresh: new Map(), attSeq: 100,
    calls: [],           // every request, for assertions
    tokenLifeMs: 3600e3
  };

  const fail = (status, body) => ({ status, body });
  const raise = (message, code = '22023') => fail(code === '42501' ? 403 : 400, { code, details: null, hint: null, message });

  function issue(email) {
    const a = 'acc_' + uuid(), r = 'ref_' + uuid();
    db.access.set(a, { email, exp: Date.now() + db.tokenLifeMs });
    db.refresh.set(r, email);
    return { access_token: a, token_type: 'bearer', expires_in: Math.round(db.tokenLifeMs / 1000),
             expires_at: Math.floor((Date.now() + db.tokenLifeMs) / 1000), refresh_token: r,
             user: { id: db.users[email].id, email } };
  }

  function bundleData() {
    const today = schoolToday();
    const active = db.students.filter((s) => s.active);
    const cls = (id) => db.classes.find((c) => c.id === id) || {};
    const numeric = db.students.map((s) => s.roll).filter((r) => /^[0-9]{4,9}$/.test(r)).map(Number);
    return {
      school: db.school, role: 'admin', today, from: '2000-01-01',
      next_roll: (numeric.length ? Math.max(...numeric) : 1000) + 1,
      classes: [...db.classes].sort((a, b) => (a.name + a.section).localeCompare(b.name + b.section)),
      students: active.sort((a, b) => a.roll.localeCompare(b.roll)).map((s) => {
        const rows = db.attendance.filter((a) => a.student_id === s.id);
        const n = (...st) => rows.filter((a) => st.includes(a.status)).length;
        const card = db.cards.find((c) => c.student_id === s.id && c.active);
        return { id: s.id, roll: s.roll, name: s.name, class_id: s.class_id, cls: cls(s.class_id).name || null, sec: cls(s.class_id).section || null,
                 g_name: s.g_name, g_email: s.g_email, g_phone: s.g_phone, fp: s.fp, card: card ? card.uid : null,
                 n: { p: n('present'), l: n('late'), a: n('absent'), lv: n('leave', 'excused'), h: n('half_day', 'left') } };
      }),
      attendance: db.attendance.filter((a) => active.some((s) => s.id === a.student_id))
        .sort((a, b) => a.date.localeCompare(b.date) || a.id - b.id)
        .map((a) => [a.id, a.student_id, a.date, a.status, a.time, a.method]),
      holidays: [...db.holidays].sort((a, b) => a.date.localeCompare(b.date)),
      notices: db.notices.map((n) => ({ ...n })).reverse(),
      leaves: db.leaves.map((l) => ({ ...l })).reverse(),
      messages: db.messages.map((m) => ({ ...m })).reverse()
    };
  }
  function devices() {
    const d = db.device;
    return [{ code: d.code, name: d.name, location: d.location, firmware: d.firmware, ip: d.ip, rssi: d.rssi, active: d.active,
              // a device that has never checked in has no times at all (as in the real database)
              last_seen: d.last_seen == null ? null : new Date(d.last_seen).toISOString(),
              last_boot: d.last_boot == null ? null : new Date(d.last_boot).toISOString(),
              age_s: d.last_seen == null ? null : Math.max(0, Math.round((Date.now() - d.last_seen) / 1000)) }];
  }

  const normUid = (u) => (u == null ? null : String(u).toUpperCase().replace(/[^0-9A-Z]/g, '') || null);

  /* Argument names of the real functions: [required, optional]. Copied from the live
     database (pg_proc) on 2026-11-14. PostgREST picks a function by the argument NAMES in
     the request, so a call with an unknown name, or without a required one, is a 404 there.
     The double behaves the same; otherwise a call that can never work would pass here. */
  const SIG = {
    astro_web_bundle: [[], ['p_token', 'p_days']],
    astro_save_class: [['p_name', 'p_section'], ['p_teacher', 'p_class_id', 'p_school_id']],
    astro_save_student: [['p_roll_no', 'p_full_name'], ['p_class_id', 'p_guardian_name', 'p_guardian_email', 'p_guardian_phone',
      'p_card_uid', 'p_fingerprint_slot', 'p_device_code', 'p_student_id', 'p_school_id']],
    astro_web_remove_student: [['p_student_id'], []],
    astro_unassign_card: [['p_card_uid'], ['p_school_id']],
    astro_set_attendance: [['p_student_id', 'p_date', 'p_status'], ['p_note', 'p_school_id']],
    astro_web_update_notice: [['p_notice_id'], ['p_title', 'p_body', 'p_priority', 'p_pinned', 'p_published']],
    astro_post_notice: [['p_title', 'p_body'], ['p_priority', 'p_audience', 'p_class_id', 'p_student_id', 'p_pinned', 'p_expires_at', 'p_school_id']],
    astro_delete_notice: [['p_notice_id'], []],
    astro_decide_leave: [['p_leave_id', 'p_approve'], ['p_note']],
    astro_send_message: [['p_student_id', 'p_subject', 'p_body'], ['p_school_id']],
    astro_delete_message: [['p_message_id'], []],
    astro_update_settings: [[], ['p_late_after', 'p_absent_after', 'p_day_start', 'p_day_end', 'p_alert_emails', 'p_weekly_off',
      'p_timezone', 'p_clear_absent_after', 'p_school_id']],
    astro_set_holiday: [['p_date'], ['p_name', 'p_school_id']],
    astro_remove_holiday: [['p_date'], ['p_school_id']]
  };
  const signatureMatches = (name, args) => {
    const [req, opt] = SIG[name] || [[], []];
    const keys = Object.keys(args || {});
    return req.every((k) => keys.includes(k)) && keys.every((k) => req.includes(k) || opt.includes(k));
  };

  const RPC = {
    astro_web_bundle(a) {
      const data = bundleData();
      const token = crypto.createHash('md5').update(JSON.stringify(data)).digest('hex');
      const base = { ok: true, token, now: new Date().toISOString(), devices: devices() };
      return a.p_token && a.p_token === token ? { ...base, unchanged: true } : { ...base, unchanged: false, data };
    },
    astro_save_class(a) {
      const name = String(a.p_name || '').trim(), section = String(a.p_section || '').trim().toUpperCase();
      if (db.classes.some((c) => c.name.toLowerCase() === name.toLowerCase() && c.section === section)) {
        return { ok: false, name, reason: 'CLASS_EXISTS', section };
      }
      const c = { id: uuid(), name, section, teacher: a.p_teacher || null };
      db.classes.push(c);
      return { ok: true, name, label: name + '-' + section, created: true, section, teacher: c.teacher, class_id: c.id, students: 0 };
    },
    astro_save_student(a) {
      const uid = normUid(a.p_card_uid);
      const name = a.p_full_name ? String(a.p_full_name).trim().replace(/\s+/g, ' ') : null;
      const roll = a.p_roll_no ? String(a.p_roll_no).trim() : null;
      const email = a.p_guardian_email ? String(a.p_guardian_email).trim().toLowerCase() : null;
      if (!a.p_student_id) {
        if (!roll) return raise('ROLL_REQUIRED');
        if (!name) return raise('NAME_REQUIRED');
      }
      if (email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return raise('BAD_EMAIL');
      if (a.p_class_id && !db.classes.some((c) => c.id === a.p_class_id)) return raise('CLASS_NOT_FOUND');
      let card = null;
      if (uid) {
        if (!/^[0-9A-F]{8,20}$/.test(uid)) return raise('BAD_CARD_UID');
        card = db.cards.find((c) => c.uid === uid) || null;
        if (card && card.student_id && card.student_id !== a.p_student_id) {
          const o = db.students.find((s) => s.id === card.student_id);
          return { ok: false, owner: o.name + ' (' + o.roll + ')', reason: 'CARD_IN_USE' };
        }
      }
      let st;
      if (!a.p_student_id) {
        if (db.students.some((s) => s.roll === roll)) return { ok: false, reason: 'ROLL_EXISTS', roll_no: roll };   // archived students keep their roll
        st = { id: uuid(), roll, name, class_id: a.p_class_id || null, g_name: null, g_email: email,
               g_phone: a.p_guardian_phone ? String(a.p_guardian_phone).trim() : null, fp: null, active: true };
        db.students.push(st);
      } else {
        st = db.students.find((s) => s.id === a.p_student_id);
        if (!st) return raise('STUDENT_NOT_FOUND');
        if (roll && db.students.some((s) => s.roll === roll && s.id !== st.id)) return { ok: false, reason: 'ROLL_EXISTS', roll_no: roll };
        if (a.p_class_id) st.class_id = a.p_class_id;
        if (roll) st.roll = roll;
        if (name) st.name = name;
        if (a.p_guardian_email != null) st.g_email = email || null;
        if (a.p_guardian_phone != null) st.g_phone = String(a.p_guardian_phone).trim() || null;
      }
      if (uid) {
        if (card) { card.student_id = st.id; card.active = true; } else db.cards.push({ uid, student_id: st.id, active: true });
      }
      return { ok: true, created: !a.p_student_id,
               student: { id: st.id, roll_no: st.roll, full_name: st.name, class_id: st.class_id, active: st.active,
                          guardian_name: st.g_name, guardian_email: st.g_email, guardian_phone: st.g_phone, fingerprint_id: st.fp },
               cards: db.cards.filter((c) => c.student_id === st.id && c.active).map((c) => c.uid) };
    },
    astro_unassign_card(a) {
      const c = db.cards.find((x) => x.uid === normUid(a.p_card_uid));
      if (c) { c.student_id = null; c.active = false; }
      return { ok: true, card_uid: normUid(a.p_card_uid), released: !!c };
    },
    astro_web_remove_student(a) {
      const st = db.students.find((s) => s.id === a.p_student_id);
      if (!st) return raise('STUDENT_NOT_FOUND');
      const rows = db.attendance.filter((x) => x.student_id === st.id).length;
      if (!rows) {
        db.students = db.students.filter((s) => s !== st);
        db.cards = db.cards.filter((c) => c.student_id !== st.id);
        return { ok: true, mode: 'deleted', student_id: st.id, name: st.name, roll_no: st.roll };
      }
      st.active = false; st.fp = null;
      db.cards.forEach((c) => { if (c.student_id === st.id) { c.student_id = null; c.active = false; } });
      return { ok: true, mode: 'archived', student_id: st.id, name: st.name, roll_no: st.roll, active: false, attendance_rows_kept: rows };
    },
    astro_set_attendance(a) {
      const st = db.students.find((s) => s.id === a.p_student_id);
      if (!st) return raise('STUDENT_NOT_FOUND');
      const status = String(a.p_status || '').toLowerCase(), today = schoolToday();
      const i = db.attendance.findIndex((x) => x.student_id === st.id && x.date === a.p_date);
      if (status === 'clear') {
        if (i >= 0) db.attendance.splice(i, 1);
        return { ok: true, date: a.p_date, status: 'not_marked', cleared: i >= 0 ? 1 : 0 };
      }
      if (!['present', 'late', 'absent', 'leave', 'excused', 'half_day', 'left'].includes(status)) return raise('BAD_STATUS');
      if (a.p_date > today && !['leave', 'excused'].includes(status)) return raise('FUTURE_DATE');
      let row = db.attendance[i];
      if (row) Object.assign(row, { status, method: 'manual', time: hhmmNow() });
      else { row = { id: ++db.attSeq, student_id: st.id, date: a.p_date, status, time: hhmmNow(), method: 'manual' }; db.attendance.push(row); }
      return { ok: true, attendance_id: row.id, date: row.date, status: row.status, student: st.name };
    },
    astro_post_notice(a) {
      const n = { id: uuid(), title: a.p_title, body: a.p_body, priority: a.p_priority || 'normal', audience: a.p_audience || 'all',
                  class_id: a.p_class_id || null, student_id: null, pinned: !!a.p_pinned, date: schoolToday(), published: true };
      db.notices.push(n);
      return { ok: true, audience: n.audience, priority: n.priority, notice_id: n.id, recipients: 0, email_queued: true };
    },
    astro_web_update_notice(a) {
      const n = db.notices.find((x) => x.id === a.p_notice_id);
      if (!n) return raise('NOTICE_NOT_FOUND');
      if (a.p_title) n.title = a.p_title;
      if (a.p_body) n.body = a.p_body;
      if (a.p_priority) n.priority = a.p_priority;
      if (a.p_pinned != null) n.pinned = a.p_pinned;
      if (a.p_published != null) n.published = a.p_published;
      return { ok: true, notice_id: n.id, title: n.title, priority: n.priority, pinned: n.pinned, published: n.published };
    },
    astro_delete_notice(a) {
      const before = db.notices.length;
      db.notices = db.notices.filter((x) => x.id !== a.p_notice_id);
      return { ok: true, deleted: before - db.notices.length, emails_cancelled: 0 };
    },
    astro_set_holiday(a) {
      db.holidays = db.holidays.filter((h) => h.date !== a.p_date).concat({ date: a.p_date, reason: a.p_name || null });
      return { ok: true, date: a.p_date, name: a.p_name || null, auto_absences_removed: 0 };
    },
    astro_remove_holiday(a) {
      const before = db.holidays.length;
      db.holidays = db.holidays.filter((h) => h.date !== a.p_date);
      return { ok: true, date: a.p_date, removed: before - db.holidays.length };
    },
    astro_send_message(a) {
      const st = db.students.find((s) => s.id === a.p_student_id);
      if (!st) return raise('STUDENT_NOT_FOUND');
      const m = { id: uuid(), student_id: st.id, subject: a.p_subject, body: a.p_body, direction: 'to_student', read: false,
                  date: schoolToday(), time: hhmmNow() };
      db.messages.push(m);
      return { ok: true, roll_no: st.roll, student: st.name, message_id: m.id, email_queued: true, guardian_email_on_file: !!st.g_email };
    },
    astro_delete_message(a) {
      db.messages = db.messages.filter((m) => m.id !== a.p_message_id);
      return { ok: true };
    },
    astro_decide_leave(a) {
      const l = db.leaves.find((x) => x.id === a.p_leave_id);
      if (!l) return raise('LEAVE_NOT_FOUND');
      l.status = a.p_approve ? 'approved' : 'rejected';
      return { ok: true, status: l.status };
    },
    astro_update_settings(a) {
      const s = db.school;
      if (a.p_late_after) s.late_after = a.p_late_after;
      if (a.p_absent_after) s.absent_after = a.p_absent_after;
      if (a.p_clear_absent_after) s.absent_after = null;
      if (a.p_day_start) s.day_start = a.p_day_start;
      if (a.p_day_end) s.day_end = a.p_day_end;
      if (a.p_weekly_off) s.weekly_off = a.p_weekly_off;
      return { ok: true, ...s };
    }
  };

  function handle(method, url, headers, bodyText) {
    const u = new URL(url);
    let body = {};
    try { body = bodyText ? JSON.parse(bodyText) : {}; } catch (e) {}
    const entry = { method, path: u.pathname + u.search, body };
    db.calls.push(entry);
    const done = (r) => { entry.status = r.status; return r; };

    if (!headers.apikey) return done(fail(401, { message: 'No API key found in request' }));
    if (u.pathname === '/auth/v1/settings') return done({ status: 200, body: { external: { email: true }, disable_signup: true } });
    if (u.pathname === '/auth/v1/logout') return done({ status: 204, body: null });
    if (u.pathname === '/auth/v1/token') {
      const grant = u.searchParams.get('grant_type');
      if (grant === 'password') {
        const user = db.users[String(body.email || '').toLowerCase()];
        if (!user || user.password !== body.password) {
          return done(fail(400, { code: 400, error_code: 'invalid_credentials', msg: 'Invalid login credentials' }));
        }
        return done({ status: 200, body: issue(String(body.email).toLowerCase()) });
      }
      if (grant === 'refresh_token') {
        const email = db.refresh.get(body.refresh_token);
        if (!email) return done(fail(400, { code: 400, error_code: 'refresh_token_not_found', msg: 'Invalid Refresh Token: Refresh Token Not Found' }));
        db.refresh.delete(body.refresh_token);
        return done({ status: 200, body: issue(email) });
      }
    }
    const m = u.pathname.match(/^\/rest\/v1\/rpc\/([a-z_]+)$/);
    if (m) {
      const tok = String(headers.authorization || '').replace(/^Bearer /, '');
      const sess = db.access.get(tok);
      if (!sess || sess.exp < Date.now()) return done(fail(401, { code: 'PGRST301', details: null, hint: null, message: 'JWT expired' }));
      const user = db.users[sess.email];
      if (!user.role) return done(raise('NOT_A_MEMBER', '42501'));
      if (!RPC[m[1]] || !signatureMatches(m[1], body)) {
        return done(fail(404, { code: 'PGRST202', details: 'Searched for the function public.' + m[1] + ' with parameters ' + Object.keys(body || {}).sort().join(', '),
          hint: null, message: 'Could not find the function public.' + m[1] + '(' + Object.keys(body || {}).sort().join(', ') + ') in the schema cache' }));
      }
      const out = RPC[m[1]](body);
      return done(out && out.status && out.body ? out : { status: 200, body: out });
    }
    return done(fail(404, { message: 'not found' }));
  }

  // what the gate device does when a card is tapped
  function kioskScan(cardUid, status = 'present') {
    const c = db.cards.find((x) => x.uid === cardUid && x.active);
    if (!c) return null;
    const row = { id: ++db.attSeq, student_id: c.student_id, date: schoolToday(), status, time: hhmmNow(), method: 'rfid' };
    db.attendance = db.attendance.filter((a) => !(a.student_id === row.student_id && a.date === row.date)).concat(row);
    db.device.last_seen = Date.now();
    return row;
  }

  return { db, handle, kioskScan, schoolToday };
}
