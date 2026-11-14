/* ============================================================================
   ASTRO SMART ATTENDANCE - CLOUD BRIDGE (website mode)
   ----------------------------------------------------------------------------
   The dashboard in index.html was written for the ESP32. Every screen asks the
   device for "/api/...". On a website there is no device behind that address,
   so the app used to fall back to a pretend in-browser database: students you
   added looked saved and then vanished.

   This file sits between the app and the network. It catches every /api/...
   request the app makes and answers it from the school's Supabase database,
   in exactly the JSON shape the ESP32 would have used. The app itself does not
   know the difference, so every existing screen keeps working:

     sign in ........ Supabase Auth (staff email + password)
     read ........... one RPC, astro_web_bundle, polled every 8 s (tiny reply
                      when nothing changed)
     write .......... the staff RPCs: astro_save_student, astro_set_attendance,
                      astro_post_notice, astro_set_holiday, ...
     device only .... Wi-Fi, fingerprint enrolment, OTA, LCD: answered with a
                      clear "use the school device for this" instead of a fake
                      success

   MUST be loaded BEFORE the app's own scripts (the app starts polling 400 ms
   after load). Needs supabase/migrations/20261114000004_web_dashboard_rpc.sql.
   ========================================================================== */
(function () {
  'use strict';

  var SB_URL = 'https://nrjchonjlncamfyzmfye.supabase.co';
  /* The public "anon" key. It is meant to be shipped to browsers: on its own it
     can only sign in and call the device RPCs, which demand the device secret. */
  var SB_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5yamNob25qbG5jYW1meXptZnllIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTQ0NzUwNDUsImV4cCI6MjExMDA1MTA0NX0.MtiRrja_PYMWauT-ORzcOcdKHRAIXh3HtjyKeE5AoVM';

  var STORE = 'astro.cloud.session.v1';   // where the Supabase session lives
  var POLL_MS = 8000;                     // how often to ask "anything new?"
  var HISTORY_DAYS = 100;                 // days of attendance kept in the browser
  var ONLINE_S = 90;                      // kiosk counts as online if seen this recently
  var TIMEOUT_MS = 20000;
  var RESERVED = { CA4FBE2C: 'Admin', BA6ECD2C: 'Guardian', '5A77C22C': 'Delete' };
  var CARD_HELP = 'A card number is 8 to 20 characters using only 0-9 and A-F, for example 04A3B2C1. ' +
                  'Press Auto if the student has no card yet.';
  var DEVICE_ONLY = 'That control lives on the school device. Open the device\u2019s own page on the school Wi-Fi to use it.';

  var realFetch = window.fetch ? window.fetch.bind(window) : null;
  if (!realFetch || !window.Promise || !window.Response || !window.URL) return;

  /* ------------------------------------------------------------------ state */
  var S = {
    token: null,        // change token of the bundle we hold
    data: null,         // the bundle itself
    view: null,         // device-shaped JSON derived from it (rebuilt per change)
    gen: 1,             // "generation" the app compares against
    devices: [], devicesAt: 0,
    okAt: 0, error: '', inflight: null, lastFetch: 0,
    cloudUp: null,      // null = not checked yet
    armedUntil: 0, loginAt: 0, loggingIn: false, reloading: false
  };

  function Fail(message, status, code) { this.message = message; this.status = status || 400; this.code = code || ''; }
  Fail.prototype = Object.create(Error.prototype);

  function now() { return Date.now(); }
  function noop() {}
  function clean(v) { return String(v == null ? '' : v).replace(/\s+/g, ' ').trim(); }
  function blank(v) { var t = clean(v); return !t || t === '-' || t === '\u2014'; }
  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsDel(k) { try { localStorage.removeItem(k); } catch (e) {} }

  /* ---------------------------------------------------------------- session */
  function readSession() {
    try {
      var s = JSON.parse(lsGet(STORE) || 'null');
      return s && s.access_token && s.refresh_token ? s : null;
    } catch (e) { return null; }
  }
  function writeSession(s) {
    try { if (s) localStorage.setItem(STORE, JSON.stringify(s)); else localStorage.removeItem(STORE); } catch (e) {}
  }
  function packSession(j, old) {
    return {
      access_token: j.access_token,
      refresh_token: j.refresh_token,
      expires_at: j.expires_at || Math.floor(now() / 1000) + (j.expires_in || 3600),
      email: (j.user && j.user.email) || (old && old.email) || '',
      uid: (j.user && j.user.id) || (old && old.uid) || ''
    };
  }
  function dropSession() {
    writeSession(null);
    S.token = null; S.data = null; S.view = null; S.devices = []; S.gen++;
  }
  function expired() { return new Fail('Session expired \u2014 sign in again.', 401, 'NO_SESSION'); }

  /* ------------------------------------------------------- Supabase transport */
  function sb(path, opt) {
    var ctl = window.AbortController ? new AbortController() : null;
    var timer = ctl ? setTimeout(function () { ctl.abort(); }, TIMEOUT_MS) : 0;
    var headers = { apikey: SB_KEY, 'Content-Type': 'application/json' };
    if (opt.bearer) headers.Authorization = 'Bearer ' + opt.bearer;
    return realFetch(SB_URL + path, {
      method: opt.method || 'POST', headers: headers, cache: 'no-store',
      body: opt.body === undefined ? undefined : JSON.stringify(opt.body),
      signal: ctl ? ctl.signal : undefined
    }).then(function (r) {
      return r.text().then(function (t) {
        clearTimeout(timer);
        var j = null;
        try { j = t ? JSON.parse(t) : null; } catch (e) {}
        S.cloudUp = true;
        return { status: r.status, ok: r.ok, json: j };
      });
    }, function () {
      clearTimeout(timer);
      S.cloudUp = false;
      throw new Fail('Can\u2019t reach the cloud database. Check the internet connection and try again.', 500, 'NETWORK');
    });
  }

  var refreshing = null;
  function accessToken() {
    var s = readSession();
    if (!s) return Promise.reject(expired());
    if (s.expires_at - 90 > now() / 1000) return Promise.resolve(s.access_token);
    if (!refreshing) {
      refreshing = sb('/auth/v1/token?grant_type=refresh_token', { body: { refresh_token: s.refresh_token } }).then(function (r) {
        if (r.ok && r.json && r.json.access_token) {
          var n = packSession(r.json, s);
          writeSession(n);
          return n.access_token;
        }
        var other = readSession();   // another tab may have rotated the token a moment ago
        if (other && other.refresh_token !== s.refresh_token && other.expires_at - 30 > now() / 1000) return other.access_token;
        if (r.status >= 400 && r.status < 500) { dropSession(); throw expired(); }
        throw new Fail('The cloud database is not answering right now. Try again in a moment.', 500, 'NETWORK');
      });
      var clear = function () { refreshing = null; };
      refreshing.then(clear, clear);
    }
    return refreshing;
  }

  var MSG = {
    NOT_A_MEMBER: 'This account is not on the staff list of any school.',
    NOT_STAFF: 'This account is not a staff account.',
    NOT_ADMIN: 'Only an admin can change this.',
    NAME_REQUIRED: 'Enter the student\u2019s full name.',
    ROLL_REQUIRED: 'Enter a roll number.',
    BAD_EMAIL: 'That email address doesn\u2019t look right.',
    BAD_CARD_UID: CARD_HELP,
    CLASS_NOT_FOUND: 'That class no longer exists \u2014 reload the page.',
    STUDENT_NOT_FOUND: 'That student no longer exists \u2014 reload the page.',
    NOTICE_NOT_FOUND: 'That notice no longer exists \u2014 reload the page.',
    BAD_DATE: 'That date is more than a year old.',
    FUTURE_DATE: 'Attendance can\u2019t be marked for a future date.',
    BAD_STATUS: 'That attendance status isn\u2019t supported.',
    BAD_PRIORITY: 'Pick Normal, Important or Critical.',
    BAD_TIME: 'Times must look like 08:30.'
  };
  function friendly(m) {
    if (MSG[m]) return MSG[m];
    if (/schema cache|does not exist/i.test(m)) {
      return 'The database is missing the web dashboard functions. Apply supabase/migrations/20261114000004_web_dashboard_rpc.sql.';
    }
    return m;
  }

  function rpc(name, args, retried) {
    return accessToken().then(function (tok) {
      return sb('/rest/v1/rpc/' + name, { body: args || {}, bearer: tok });
    }).then(function (r) {
      if (r.ok) return r.json;
      var j = r.json || {};
      var msg = String(j.message || j.msg || j.error_description || j.error || ('HTTP ' + r.status));
      if (r.status === 401) {
        if (retried) { dropSession(); throw expired(); }
        var s = readSession();          // token refused: refresh once and try again
        if (s) { s.expires_at = 0; writeSession(s); }
        return rpc(name, args, true);
      }
      throw new Fail(friendly(msg), r.status >= 500 ? 500 : 400, msg);
    });
  }

  /* ------------------------------------------------------------ bundle cache */
  function refresh(afterWrite) {
    if (S.inflight) {
      if (!afterWrite) return S.inflight;
      return S.inflight.then(noop, noop).then(function () { return refresh(false); });
    }
    S.lastFetch = now();
    S.inflight = rpc('astro_web_bundle', { p_token: S.token, p_days: HISTORY_DAYS }).then(function (r) {
      S.inflight = null;
      S.okAt = now(); S.error = '';
      S.devices = (r && r.devices) || []; S.devicesAt = now();
      if (r && !r.unchanged && r.data) { S.token = r.token; S.data = r.data; S.view = null; S.gen++; }
      paint();
    }, function (e) {
      S.inflight = null;
      S.error = (e && e.message) || 'offline';
      paint();
      throw e;
    });
    return S.inflight;
  }
  function ensureData(maxAgeMs) {
    if (S.data && (!maxAgeMs || now() - S.lastFetch < maxAgeMs)) return Promise.resolve();
    return refresh(false);
  }

  /* -------------------------------------------------------------- the kiosk */
  function kiosk() {
    var d = null;
    (S.devices || []).forEach(function (x) { if (!d && x.active !== false) d = x; });
    if (!d) return { known: false, online: false };
    var age = d.age_s == null ? null : d.age_s + Math.round((now() - S.devicesAt) / 1000);
    return { known: true, online: age != null && age <= ONLINE_S, age: age, code: d.code || '', name: d.name || '',
             firmware: d.firmware || '', ip: d.ip || '', rssi: typeof d.rssi === 'number' ? d.rssi : null, lastBoot: d.last_boot };
  }
  function ago(sec) {
    if (sec == null) return 'never connected';
    if (sec < 90) return 'just now';
    if (sec < 5400) return Math.round(sec / 60) + ' min ago';
    if (sec < 129600) return Math.round(sec / 3600) + ' h ago';
    return Math.round(sec / 86400) + ' days ago';
  }

  /* ----------------------------------------- database rows -> device-shaped JSON */
  var LABEL = { present: 'Present', late: 'Late', absent: 'Absent', leave: 'Leave', excused: 'Leave', half_day: 'Half Day', left: 'Half Day' };
  var TO_DB = { present: 'present', late: 'late', absent: 'absent', leave: 'leave', half: 'half_day', 'half day': 'half_day', half_day: 'half_day', none: 'clear', clear: 'clear', 'not marked': 'clear' };
  function srcLabel(m) { return m === 'rfid' ? 'RFID' : m ? m.charAt(0).toUpperCase() + m.slice(1) : 'Manual'; }
  function numId(u) { return parseInt(String(u).replace(/-/g, '').slice(0, 12), 16); }
  function mins(t) { var p = String(t || '0:0').split(':'); return (+p[0] || 0) * 60 + (+p[1] || 0); }
  function hhmm(m) { m = ((Math.round(m) % 1440) + 1440) % 1440; return ('0' + Math.floor(m / 60)).slice(-2) + ':' + ('0' + (m % 60)).slice(-2); }
  function ymdAdd(d, n) { var t = new Date(d + 'T00:00:00Z'); t.setUTCDate(t.getUTCDate() + n); return t.toISOString().slice(0, 10); }

  function studentJson(V, s) {
    var n = s.n || {}, rows = V.att[s.id] || [], today = S.data.today;
    var last = rows.length ? rows[rows.length - 1] : null;
    var todayRow = last && last[2] === today ? last : null;
    var p = n.p | 0, l = n.l | 0, a = n.a | 0, lv = n.lv | 0, h = n.h | 0, tot = p + l + a + lv + h;
    var pct = tot ? Math.max(0, Math.min(100, Math.floor(((p * 2 + l * 2 + lv * 2 + h) * 100 + tot) / (tot * 2)))) : 0;
    var streak = 0;
    for (var i = rows.length - 1; i >= 0; i--) {
      var st = rows[i][3];
      if (st === 'present' || st === 'late') streak++;
      else if (st !== 'leave' && st !== 'excused') break;
    }
    return {
      rfid: V.keyOf[s.id], studentId: s.name, displayName: s.name, name: s.name,
      roll: s.roll || '', className: s.cls || '', section: s.sec || '',
      email: '', phone: '', parentEmail: s.g_email || '', parentPhone: s.g_phone || '',
      active: true, goal: 90, passwordSeq: /^\d{4,9}$/.test(s.roll || '') ? +s.roll : 0, mustChangePassword: false,
      present: p, late: l, absent: a, leave: lv, half: h, streak: streak, percentage: pct,
      status: todayRow ? LABEL[todayRow[3]] || 'Not marked' : 'Not marked',
      lastDate: last ? last[2] : '', lastTime: last ? last[4] || '' : '',
      fingerprint: s.fp != null, fingerprintId: s.fp || 0, fingerprintDate: '',
      rank: 1, noCard: !s.card
    };
  }

  function view() {
    if (S.view) return S.view;
    var D = S.data, V = { byKey: {}, keyOf: {}, byId: {}, att: {}, ids: { n: {}, l: {}, m: {} } };
    D.students.forEach(function (s) {
      var k = s.card ? String(s.card).toUpperCase() : 'NO-CARD-' + String(s.id).replace(/-/g, '').slice(0, 8).toUpperCase();
      while (V.byKey[k]) k += 'X';
      V.byKey[k] = s; V.keyOf[s.id] = k; V.byId[s.id] = s;
    });
    D.attendance.forEach(function (a) { (V.att[a[1]] = V.att[a[1]] || []).push(a); });

    V.students = D.students.map(function (s) { return studentJson(V, s); });
    V.students.forEach(function (x) {
      V.students.forEach(function (y) { if (y.percentage > x.percentage) x.rank++; });
    });

    var who = function (id) { var s = V.byId[id]; return { rfid: s ? V.keyOf[id] : '', name: s ? s.name : 'Former student' }; };

    V.leaves = D.leaves.filter(function (x) { return x.status !== 'cancelled'; }).map(function (x) {
      var id = numId(x.id), w = who(x.student_id); V.ids.l[id] = x.id;
      return { id: id, rfid: w.rfid, name: w.name, from: x.from, to: x.to, reason: x.reason || '', status: x.status || 'pending' };
    });
    V.calendar = {
      items: D.attendance.filter(function (a) { return V.byId[a[1]]; }).map(function (a) {
        return { rfid: V.keyOf[a[1]], date: a[2], status: LABEL[a[3]] || 'Present', time: a[4] || '', source: srcLabel(a[5]) };
      }),
      holidays: D.holidays.map(function (x) { return x.date; }),
      leaves: V.leaves.filter(function (x) { return x.status === 'approved'; })
    };
    var classLabel = {};
    D.classes.forEach(function (c) { classLabel[c.id] = 'Class ' + c.name + c.section; });
    V.notices = {
      notice: '', noticePriority: 'normal',
      items: D.notices.map(function (x) {
        var id = numId(x.id); V.ids.n[id] = x.id;
        return { id: id, title: x.title || '', body: x.body || '', message: (x.title ? x.title + ' - ' : '') + (x.body || ''),
                 priority: x.priority || 'normal', audience: (x.audience === 'class' && classLabel[x.class_id]) || 'All',
                 pinned: !!x.pinned, date: x.date, by: 'Admin', status: x.published ? 'published' : 'draft' };
      })
    };
    V.dms = D.messages.map(function (x) {
      var id = numId(x.id), w = who(x.student_id); V.ids.m[id] = x.id;
      return { id: id, rfid: w.rfid, name: w.name, from: x.direction === 'to_student' ? 'Admin' : w.name,
               subject: x.subject || 'Message', body: x.body || '', date: x.date, time: x.time || '', read: !!x.read };
    });

    var since = ymdAdd(D.today, -1);
    var recent = D.attendance.filter(function (a) { return a[2] >= since && V.byId[a[1]]; })
                             .sort(function (a, b) { return a[0] - b[0]; }).slice(-30);
    V.events = recent.map(function (a) {
      var lab = LABEL[a[3]] || 'Present';
      return { id: a[0], rfid: V.keyOf[a[1]], name: V.byId[a[1]].name, type: 'attendance', status: lab,
               message: lab + ' \u00b7 ' + srcLabel(a[5]) + (a[4] ? ' \u00b7 ' + a[4] : ''), date: a[2], time: a[4] || '',
               known: true, attendanceMarked: true };
    });
    V.latestEventId = recent.length ? recent[recent.length - 1][0] : 0;
    S.view = V;
    return V;
  }

  function settingsJson() {
    var D = S.data, sc = (D && D.school) || {}, off = sc.weekly_off || [];
    var o = {
      start: sc.day_start || '08:00', close: sc.day_end || '14:00', periodStart: sc.day_start || '08:00',
      threshold: 75, autoAbsent: !!sc.absent_after, weeklyOff: off.length > 0, weeklyOffDay: off.length ? off[0] : 0,
      astroEnabled: false, hwBuzzer: true, hwGreen: true, hwRed: true, hwLcd: true,
      emailEnabled: !!sc.alert_emails, smartRestart: false, fingerConfirm: false, fpPower: true,
      nextStudentPassword: (D && D.next_roll) || 1001, notice: '', noticePriority: 'normal', smtpConfigured: !!sc.alert_emails
    };
    o.lateAfter = o.lateAfterMin = Math.max(0, mins(sc.late_after || o.start) - mins(o.start));
    if (sc.absent_after) o.absentAfter = o.absentAfterMin = Math.max(1, mins(sc.absent_after) - mins(o.start));
    return o;
  }
  function statusJson() {
    var k = kiosk();
    return { ok: true, web: true, version: k.firmware, firmware: k.firmware, deviceCode: k.code,
             uptime: k.online && k.lastBoot ? Math.max(0, Math.round((now() - Date.parse(k.lastBoot)) / 1000)) : 0,
             wifi: k.online, fp: false, rfid: k.online, lcd: k.online, clockSynced: true, ip: k.ip, staIp: k.ip, apIp: '',
             rssi: k.rssi == null ? undefined : k.rssi, cloudState: S.error ? 'offline' : 'online', cloudOnline: !S.error,
             nextStudentPassword: (S.data && S.data.next_roll) || 1001 };
  }
  function cloudJson() {
    var up = !S.error && !!readSession();
    return { ok: true, web: true, state: up ? 'online' : 'offline', authenticated: !!readSession(), wifiConnected: !S.error,
             message: up ? 'Website connected to Supabase' : S.error, lastError: S.error, pending: false,
             lastSuccess: S.okAt ? Math.floor(S.okAt / 1000) : 0, databaseHost: SB_URL.replace('https://', ''),
             pendingDailyRecords: 0, pendingPeriodRecords: 0, pendingScanEvents: 0, pendingStudents: 0, pendingLeaves: 0, pendingNotifications: 0 };
  }
  function healthJson() {
    var k = kiosk(), st = statusJson(), D = S.data;
    return { ok: true, web: true, firmware: k.firmware, uptime: st.uptime, heap: 0, largestHeap: 0, temperature: 0,
             storageUsed: 0, storageTotal: 0, chipId: k.code, rfid: k.online, lcd: k.online, buzzer: k.online,
             fingerprint: false, fingerprintPower: false,
             fingerprintEnrolled: D ? D.students.filter(function (s) { return s.fp != null; }).length : 0,
             wifi: k.online, rssi: k.rssi || 0, cloudState: st.cloudState,
             students: D ? D.students.length : 0, records: D ? D.attendance.length : 0, queued: 0 };
  }
  function deviceJson() {
    var k = kiosk();
    return { ok: true, web: true, chipId: k.code, deviceCode: k.code, apSsid: '', apIp: '', stationIp: k.ip, pins: '' };
  }
  function fingerJson() {
    return { ok: true, web: true, present: false, sensorReady: false, powered: false, capacity: 0, enrolled: healthJson().fingerprintEnrolled,
             hwTemplates: 0, active: false, enrollActive: false, state: 'ENROLL_IDLE', progress: 0, phase: 'idle',
             message: 'Fingerprints are enrolled on the school device', lastResult: '' };
  }
  function wifiJson() {
    var k = kiosk();
    return { ok: true, web: true, connected: k.online, connecting: false, ssid: '', ip: k.ip, apIp: '', rssi: k.rssi || 0,
             message: 'Wi-Fi is set up on the device itself' };
  }
  function bundleJson() {
    var V = view();
    var out = { ok: true, web: true, unchanged: false, generation: S.gen, settings: settingsJson(), students: V.students,
                leaves: V.leaves, calendar: V.calendar, notices: V.notices, dms: V.dms, cloud: cloudJson(), health: healthJson(),
                device: deviceJson(), fingerprint: fingerJson(), wifiStatus: wifiJson() };
    /* The app treats scans that arrive inside a bundle as "already seen" and raises no
       notification for them. So they are handed over once, as the starting point; every
       later scan goes out through /api/scan-events, where the app does announce it. */
    if (!S.baselined) { S.baselined = true; out.scanEvents = { items: V.events, latestId: V.latestEventId }; }
    return out;
  }

  /* ---------------------------------------------------------------- sign in */
  function login(b) {
    var id = clean(b.id), pw = String(b.password == null ? '' : b.password);
    if (!id || !pw) throw new Fail('Enter your email and password.');
    if (id.indexOf('@') < 0) {
      throw new Fail('Sign in with your staff email address. Students use the school device for now.');
    }
    S.loggingIn = true;
    return sb('/auth/v1/token?grant_type=password', { body: { email: id.toLowerCase(), password: pw } }).then(function (r) {
      var j = r.json || {};
      if (!r.ok || !j.access_token) {
        var code = String(j.error_code || j.error || ''), msg = String(j.msg || j.error_description || j.message || '');
        if (r.status === 429) throw new Fail('Too many attempts. Wait a minute and try again.');
        if (/invalid_credentials|invalid_grant/i.test(code) || /invalid login/i.test(msg)) throw new Fail('Wrong email or password.');
        throw new Fail(msg || ('Sign-in failed (HTTP ' + r.status + ').'));
      }
      S.token = null; S.data = null; S.view = null; S.baselined = false;
      writeSession(packSession(j));
      return refresh(true);
    }).then(function () {
      S.loggingIn = false; S.loginAt = now();
      var role = (S.data && S.data.role) || 'admin';
      return { ok: true, web: true, token: 'cloud', type: 'admin', role: role,
               name: role === 'teacher' ? 'Teacher' : 'Administrator', school: S.data.school.name };
    }, function (e) {
      S.loggingIn = false; S.loginAt = now();
      if (e && e.code !== 'NETWORK') writeSession(null);
      throw e;
    });
  }
  function signOut() {
    var s = readSession();
    dropSession();
    if (s) sb('/auth/v1/logout?scope=local', { bearer: s.access_token, body: {} }).then(noop, noop);
    paint();
  }

  /* ----------------------------------------------------------------- writes */
  function findStudent(V, key) {
    var s = V.byKey[String(key == null ? '' : key).trim().toUpperCase()];
    if (!s) throw new Fail(MSG.STUDENT_NOT_FOUND);
    return s;
  }
  function cardOf(raw) {
    var c = String(raw == null ? '' : raw).toUpperCase().replace(/[\s:.\-]/g, '');
    if (!c) return '';
    if (!/^[0-9A-F]{8,20}$/.test(c)) throw new Fail(CARD_HELP);
    if (RESERVED[c]) throw new Fail('That is the device\u2019s ' + RESERVED[c] + ' card. It can\u2019t be given to a student.');
    return c;
  }
  function classId(name, section) {
    if (blank(name)) return Promise.resolve(null);
    var n = clean(name), sec = blank(section) ? 'A' : clean(section);
    var hit = function () {
      var found = null;
      S.data.classes.forEach(function (c) {
        if (String(c.name).toLowerCase() === n.toLowerCase() && String(c.section).toLowerCase() === sec.toLowerCase()) found = c.id;
      });
      return found;
    };
    var id = hit();
    if (id) return Promise.resolve(id);
    return rpc('astro_save_class', { p_name: n, p_section: sec }).then(function (r) {
      if (r && r.class_id) return r.class_id;
      return refresh(true).then(function () {
        var again = hit();
        if (!again) throw new Fail('Could not create class ' + n + '-' + sec + '.');
        return again;
      });
    });
  }
  function contact(primary, fallback, editing) {
    var v = clean(primary) || clean(fallback);
    return v ? v : (editing ? '' : null);       // '' clears on edit, null leaves untouched
  }
  function studentReply(id, created, extra) {
    var V = view(), s = V.byId[id], out = { ok: true, web: true, created: created, message: 'Student saved',
      nextStudentPassword: S.data.next_roll };
    if (s) {
      out.student = V.students[S.data.students.indexOf(s)];
      out.rfid = out.student.rfid; out.name = s.name; out.studentId = s.name;
    }
    if (extra) for (var k in extra) out[k] = extra[k];
    return out;
  }

  function saveStudent(b, adding) {
    return ensureData().then(function () {
      var V = view(), D = S.data;
      var key = String(b.rfid || b.uid || b.card || '').trim().toUpperCase();
      var existing = key ? V.byKey[key] : null;
      var name = clean(b.name || b.fullName || b.studentName);

      if (existing && adding && !b.update) {
        throw new Fail('Card ' + key + ' already belongs to ' + existing.name + ' (roll ' + existing.roll + ').', 409);
      }
      if (existing) {                                             /* ---- edit */
        return classId(b.className || b.cls, b.section || b.sec).then(function (cid) {
          return rpc('astro_save_student', {
            p_student_id: existing.id,
            p_full_name: name || null,
            p_roll_no: blank(b.roll) ? null : clean(b.roll),
            p_class_id: cid,
            p_guardian_email: contact(b.parentEmail, b.email, true),
            p_guardian_phone: contact(b.parentPhone, b.phone, true)
          });
        }).then(function (r) {
          if (r && r.ok === false) throw new Fail(r.reason === 'ROLL_EXISTS'
            ? 'Roll number ' + clean(b.roll) + ' is already used by another student.' : (r.reason || 'Could not save.'));
          return refresh(true).then(function () { return studentReply(existing.id, false); });
        });
      }

      if (!name) throw new Fail(MSG.NAME_REQUIRED);              /* ---- add */
      var card = cardOf(key);
      var autoRoll = blank(b.roll) || clean(b.roll) === String(D.next_roll);
      var tries = 0, bump = 0;
      var attempt = function (cid) {
        var roll = autoRoll ? String(S.data.next_roll + bump) : clean(b.roll);
        return rpc('astro_save_student', {
          p_roll_no: roll, p_full_name: name, p_class_id: cid,
          p_guardian_email: contact(b.parentEmail, b.email, false),
          p_guardian_phone: contact(b.parentPhone, b.phone, false),
          p_card_uid: card || null
        }).then(function (r) {
          if (r && r.ok) return r;
          var why = (r && r.reason) || 'Could not save.';
          if (why === 'ROLL_EXISTS') {
            if (autoRoll && tries < 4) {
              var before = S.data.next_roll;
              tries++;
              return refresh(true).then(function () { bump = S.data.next_roll === before ? bump + 1 : 0; return attempt(cid); });
            }
            throw new Fail('Roll number ' + roll + ' is already taken (possibly by a student who was removed earlier). Use a different roll number.');
          }
          if (why === 'CARD_IN_USE') throw new Fail('Card ' + card + ' already belongs to ' + (r.owner || 'another student') + '.');
          throw new Fail(why);
        });
      };
      return classId(b.className || b.cls || '9', b.section || b.sec || 'A').then(attempt).then(function (r) {
        var id = r.student.id;
        return refresh(true).then(function () {
          return studentReply(id, true, { credentials: { studentId: name, displayName: name } });
        }, function () {
          return { ok: true, web: true, created: true, message: 'Student saved' };   // saved; the list refresh will catch up
        });
      });
    });
  }

  function addStudent(b) { return saveStudent(b, true); }

  function removeStudent(b) {
    return ensureData().then(function () {
      var s = findStudent(view(), b.rfid);
      return rpc('astro_web_remove_student', { p_student_id: s.id });
    }).then(function (r) {
      return refresh(true).then(function () {
        return { ok: true, web: true, mode: r && r.mode,
                 message: r && r.mode === 'archived' ? 'Removed from the roster. Past attendance is kept.' : 'Student deleted.' };
      });
    });
  }

  function replaceCard(key, rawCard) {
    return ensureData().then(function () {
      var s = findStudent(view(), key), card = cardOf(rawCard);
      if (!card) throw new Fail(CARD_HELP);
      if (s.card && String(s.card).toUpperCase() === card) throw new Fail('That is already this student\u2019s card.');
      /* roll and name have no default in the database function, so they must be named
         in the call; null means "leave as it is" for an existing student */
      return rpc('astro_save_student', { p_student_id: s.id, p_roll_no: null, p_full_name: null, p_card_uid: card }).then(function (r) {
        if (r && r.ok === false) {
          throw new Fail(r.reason === 'CARD_IN_USE' ? 'Card ' + card + ' already belongs to ' + (r.owner || 'another student') + '.' : r.reason);
        }
        return s.card ? rpc('astro_unassign_card', { p_card_uid: s.card }).then(noop, noop) : null;
      }).then(function () { return refresh(true); }).then(function () { return { ok: true, card: card, name: s.name }; });
    });
  }

  function markAttendance(b) {
    return ensureData().then(function () {
      var s = findStudent(view(), b.rfid), st = TO_DB[String(b.status || '').toLowerCase()];
      if (String(b.status).toLowerCase() === 'holiday') throw new Fail('Holidays are set for the whole school from Notices & Holidays.');
      if (!st) throw new Fail(MSG.BAD_STATUS);
      return rpc('astro_set_attendance', { p_student_id: s.id, p_date: b.date || S.data.today, p_status: st, p_note: clean(b.reason) || 'web dashboard' });
    }).then(function () { return refresh(true); }).then(ok);
  }

  function saveNotice(b) {
    return ensureData().then(function () {
      var V = view(), uuid = b.id ? V.ids.n[Number(b.id)] : null;
      var pri = String(b.priority || 'normal').toLowerCase();
      if (uuid) {
        return rpc('astro_web_update_notice', { p_notice_id: uuid, p_title: b.title || null, p_body: b.body || null,
          p_priority: pri, p_pinned: !!b.pinned, p_published: String(b.status || 'published') !== 'draft' });
      }
      var title = clean(b.title), body = clean(b.body || b.message);
      if (!body) throw new Fail('Write the notice text first.');
      var aud = String(b.audience || 'All'), cid = null;
      S.data.classes.forEach(function (c) { if (aud === 'Class ' + c.name + c.section) cid = c.id; });
      return rpc('astro_post_notice', { p_title: title || 'Notice', p_body: body, p_priority: pri,
        p_audience: cid ? 'class' : 'all', p_class_id: cid, p_pinned: !!b.pinned });
    }).then(function () { return refresh(true); }).then(ok);
  }
  function quickNotice(b) {
    var text = clean(b.notice);
    if (!text) return Promise.resolve(ok());
    var cut = text.indexOf(' \u2014 ');
    return saveNotice({ title: cut > 0 && cut < 60 ? text.slice(0, cut) : 'Notice', body: cut > 0 && cut < 60 ? text.slice(cut + 3) : text,
                        priority: b.priority, pinned: true });
  }
  function deleteNotice(b) {
    if (!b.id) return Promise.resolve(ok());
    return ensureData().then(function () {
      var uuid = view().ids.n[Number(b.id)];
      if (!uuid) throw new Fail(MSG.NOTICE_NOT_FOUND);
      return rpc('astro_delete_notice', { p_notice_id: uuid });
    }).then(function () { return refresh(true); }).then(ok);
  }

  function decideLeave(b) {
    return ensureData().then(function () {
      var uuid = view().ids.l[Number(b.id)];
      if (!uuid) throw new Fail('That leave request no longer exists \u2014 reload the page.');
      return rpc('astro_decide_leave', { p_leave_id: uuid, p_approve: String(b.action || b.decision) !== 'reject' && String(b.action) !== 'rejected' });
    }).then(function () { return refresh(true); }).then(ok);
  }

  function sendMessages(b) {
    return ensureData().then(function () {
      var V = view();
      var keys = Array.isArray(b.rfids) ? b.rfids : String(b.to || b.rfid || '').split(',');
      var ids = [];
      keys.forEach(function (k) { var s = V.byKey[String(k).trim().toUpperCase()]; if (s && ids.indexOf(s.id) < 0) ids.push(s.id); });
      if (!ids.length) throw new Fail('Pick at least one student.');
      var body = clean(b.body || b.text) || String(b.message || '').trim();
      if (!body) throw new Fail('Write a message first.');
      var subject = clean(b.subject) || 'Message', first = null, i = 0;
      var next = function () {
        if (i >= ids.length) return null;
        return rpc('astro_send_message', { p_student_id: ids[i++], p_subject: subject, p_body: body }).then(function (r) {
          if (!first && r && r.message_id) first = numId(r.message_id);
          return next();
        });
      };
      return Promise.all([next(), next(), next(), next()]).then(function () { return refresh(true); }).then(function () {
        return { ok: true, web: true, id: first, sent: ids.length };
      });
    });
  }
  function deleteMessage(b) {
    return ensureData().then(function () {
      var uuid = view().ids.m[Number(b.id)];
      if (!uuid) return null;
      return rpc('astro_delete_message', { p_message_id: uuid });
    }).then(function () { return refresh(true); }).then(ok);
  }

  function saveSettings(b) {
    var cloudKeys = ['start', 'close', 'lateAfter', 'lateAfterMin', 'absentAfter', 'absentAfterMin', 'autoAbsent', 'weeklyOff', 'weeklyOffDay'];
    if (!cloudKeys.some(function (k) { return b[k] !== undefined; })) {
      throw new Fail('That setting is stored on the school device, not in the cloud. Change it from the device\u2019s own page.');
    }
    return ensureData().then(function () {
      var cur = settingsJson(), a = {};
      var start = /^\d{1,2}:\d{2}$/.test(b.start || '') ? hhmm(mins(b.start)) : cur.start;
      var close = /^\d{1,2}:\d{2}$/.test(b.close || '') ? hhmm(mins(b.close)) : cur.close;
      var num = function (x, y) { var v = x !== undefined ? x : y; v = v === undefined || v === '' ? NaN : Number(v); return isNaN(v) ? null : v; };
      var late = num(b.lateAfterMin, b.lateAfter), absent = num(b.absentAfterMin, b.absentAfter);
      if (start !== cur.start) a.p_day_start = start;
      if (close !== cur.close) a.p_day_end = close;
      if (late != null && (late !== cur.lateAfter || a.p_day_start)) a.p_late_after = hhmm(mins(start) + late);
      if (b.autoAbsent === false) { if (cur.autoAbsent) a.p_clear_absent_after = true; }
      else if (absent != null && (b.autoAbsent === true || cur.autoAbsent) && (absent !== cur.absentAfter || a.p_day_start)) {
        a.p_absent_after = hhmm(mins(start) + absent);
      }
      if (typeof b.weeklyOff === 'boolean') {
        var day = num(b.weeklyOffDay, cur.weeklyOffDay) || 0;
        if (b.weeklyOff !== cur.weeklyOff || (b.weeklyOff && day !== cur.weeklyOffDay)) a.p_weekly_off = b.weeklyOff ? [day] : [];
      }
      if (!Object.keys(a).length) return null;
      return rpc('astro_update_settings', a).then(function () { return refresh(true); });
    }).then(ok);
  }

  /* ----------------------------------------------------------------- router */
  function ok(extra) {
    var o = { ok: true, web: true };
    if (extra && typeof extra === 'object') for (var k in extra) o[k] = extra[k];
    return o;
  }
  function deviceOnly() { throw new Fail(DEVICE_ONLY); }

  var POST = {
    '/addStudent': addStudent, '/api/addStudent': addStudent, '/api/student': addStudent,
    '/api/student/save': function (b) { return saveStudent(b, false); },
    '/api/student/delete': removeStudent,
    '/api/attendance/mark': markAttendance,
    '/api/notices': saveNotice, '/api/notice': quickNotice, '/api/notice/delete': deleteNotice,
    '/api/holidays': function (b) {
      if (!/^\d{4}-\d{2}-\d{2}$/.test(b.date || '')) throw new Fail('Pick a date first.');
      return rpc('astro_set_holiday', { p_date: b.date, p_name: clean(b.name || b.reason) || null }).then(function () { return refresh(true); }).then(ok);
    },
    '/api/holiday/delete': function (b) {
      return rpc('astro_remove_holiday', { p_date: b.date }).then(function () { return refresh(true); }).then(ok);
    },
    '/api/leaves/decide': decideLeave,
    '/api/dm': sendMessages, '/api/dm/delete': deleteMessage, '/api/dm/read': ok,
    '/api/settings': saveSettings,
    '/api/cloud/retry': function () { return refresh(true).then(ok); },
    '/api/time': ok, '/api/notification/resolve': ok, '/api/notifications/resolve-all': ok,
    '/api/registration/start': function (b) { S.armedUntil = now() + (Number(b.seconds) || 60) * 1000; return ok(); },
    '/api/registration/cancel': function () { S.armedUntil = 0; return ok(); },
    '/api/student/password': function () { throw new Fail('Student passwords are kept on the school device, not in the cloud.'); },
    '/api/clear-today': function () { throw new Fail('Clearing a whole day is not available on the website. Correct individual marks from Records instead.'); }
  };

  var GET = {
    '/api/students': function () { return { ok: true, items: view().students }; },
    '/api/calendar': function () { var c = view().calendar; return { ok: true, items: c.items, holidays: c.holidays, leaves: c.leaves }; },
    '/api/leaves': function () { return { ok: true, items: view().leaves }; },
    '/api/notices': function () { var n = view().notices; return { ok: true, items: n.items, notice: n.notice, noticePriority: n.noticePriority }; },
    '/api/dm': function () { return { ok: true, items: view().dms }; },
    '/api/settings': function () { return ok(settingsJson()); },
    '/api/cloud': cloudJson, '/api/health': healthJson, '/api/device': deviceJson,
    '/api/fingerprint': fingerJson, '/api/fingerprint/status': fingerJson, '/api/enroll/status': fingerJson,
    '/api/wifi/status': wifiJson,
    '/api/wifi/scan': function () { return { ok: true, scanning: false, count: 0, items: [] }; },
    '/api/wifi/saved': function () { return { ok: true, slots: [] }; },
    '/api/secstate': function () { return { ok: true, phase: 'idle', left: 0 }; },
    '/api/esp-lock': function () { return { ok: true, locked: false }; },
    '/api/registration/status': function () {
      var left = Math.max(0, Math.round((S.armedUntil - now()) / 1000));
      return { ok: true, web: true, active: left > 0, captured: false, rfid: '', lastUnknownUid: '', rejectedRfid: '',
               remainingSeconds: left, message: 'Type the card number, or press Auto' };
    }
  };

  function route(path, method, body, query) {
    if (path === '/api/login' || path === '/login') return login(body);
    if (path === '/api/status' || path === '/version' || path === '/status') return statusJson();
    if (path === '/api/time') return ok();
    if (!readSession()) throw expired();

    if (path === '/api/live-sync') {
      var gen = parseInt(query.gen, 10) || 0;
      if (gen && S.data && gen === S.gen) {
        return { ok: true, unchanged: true, generation: S.gen, latestEventId: view().latestEventId };
      }
      return ensureData(gen ? 0 : 4000).then(bundleJson);
    }
    if (path === '/api/scan-events') {
      return ensureData().then(function () {
        var V = view(), after = parseInt(query.after, 10) || 0;
        if (!S.baselined) return { ok: true, items: [], latestId: V.latestEventId };   // not before the starting point is set
        return { ok: true, items: V.events.filter(function (e) { return e.id > after; }), latestId: V.latestEventId };
      });
    }
    if (method === 'GET') {
      if (GET[path]) return ensureData().then(GET[path]);
      return { ok: true, web: true, items: [] };          // device-only read: nothing to show
    }
    if (POST[path]) return POST[path](body || {});
    return deviceOnly();
  }

  function reply(status, obj) {
    return new Response(JSON.stringify(obj), { status: status, headers: { 'Content-Type': 'application/json' } });
  }
  function ours(path) {
    return path.indexOf('/api/') === 0 || path === '/addStudent' || path === '/login' || path === '/version' || path === '/status';
  }

  window.fetch = function (input, init) {
    var u, method, raw;
    try {
      u = new URL(typeof input === 'string' ? input : (input && input.url) || String(input), location.href);
      if (u.origin !== location.origin || !ours(u.pathname)) return realFetch(input, init);
      method = String((init && init.method) || (input && input.method) || 'GET').toUpperCase();
      raw = init && typeof init.body === 'string' ? init.body : '';
    } catch (e) { return realFetch(input, init); }

    var body = {}, query = {};
    try { if (raw) body = JSON.parse(raw) || {}; } catch (e) {}
    u.searchParams.forEach(function (v, k) { query[k] = v; });

    return new Promise(function (resolve) { resolve(route(u.pathname, method, body, query)); }).then(function (out) {
      return reply(200, out == null ? { ok: true } : out);
    }, function (e) {
      var status = e instanceof Fail ? e.status : 500;
      if (!(e instanceof Fail) && window.console) console.error('[astro cloud]', u.pathname, e);
      if (status === 401 && !S.okAt && !S.reloading && lsGet('astro_tok')) {
        S.reloading = true;                       // restored a session that is no longer valid
        lsDel('astro_tok'); lsDel('astro_role'); lsDel('astro_name');
        location.reload();
      }
      return reply(status, { ok: false, web: true, message: (e && e.message) || 'Something went wrong.', code: (e && e.code) || '' });
    });
  };

  /* -------------------------------------------- honest status lights + tidy UI */
  function pill(id, cls, text, pulse) {
    var el = document.getElementById(id);
    if (!el) return;
    var html = '<span class="dt' + (pulse ? ' pulse-dot' : '') + '"></span>' + text;
    if (el.className !== 'pill ' + cls) el.className = 'pill ' + cls;
    if (el.innerHTML !== html) el.innerHTML = html;
  }
  function paint() {
    var k = kiosk();
    try {
      /* DEVICE, SESSION, renderTopbar... are the app's own globals (top-level const/let) */
      var was = DEVICE.online, wasState = DEVICE.state;
      DEVICE.online = k.online;
      DEVICE.state = k.online ? 'green' : 'red';
      DEVICE.ip = DEVICE.stationIp = k.known ? (k.ip || k.code) : '\u2014';
      DEVICE.wifiSsid = k.online ? 'gate device online' : 'gate device offline';   // the network name stays on the device
      if (k.rssi == null) DEVICE.rssi = '\u2014';             // signal strength: only if the device reported one
      if (k.firmware) { DEVICE.fw = k.firmware; DEVICE.fwNew = k.firmware; }
      /* The cloud only hears "the device checked in". Heap, temperature, storage and the
         state of each part are known on the device alone, so nothing is made up here:
         readings show a dash and every row keeps the app's neutral starting state. */
      DEVICE.heap = DEVICE.temp = DEVICE.storage = '\u2014';
      delete HW.fingerprint;
      Object.keys(HW).forEach(function (key) { HW[key].state = 'ok'; });
      HW.ram.detail = HW.temp.detail = HW.wifi.detail = 'live reading from the device';
      if ((was !== DEVICE.online || wasState !== DEVICE.state) && SESSION.role) { renderTopbar(); renderSidebar(); }
    } catch (e) {}
    if (S.cloudUp === false) pill('sys-cloud', 'p-err', 'Cloud: unreachable');
    else if (S.cloudUp) pill('sys-cloud', 'p-ok', 'Cloud: connected', true);
    else pill('sys-cloud', 'p-idle', 'Cloud: checking\u2026');
    if (!k.known) pill('sys-dev', 'p-idle', 'Device: shown after sign-in');
    else if (k.online) pill('sys-dev', 'p-ok', 'Device: online', true);
    else pill('sys-dev', 'p-idle', 'Device: offline \u00b7 seen ' + ago(k.age));
    var lc = document.getElementById('lg-cloud'), ld = document.getElementById('lg-device');
    if (lc) lc.className = 'pill ' + (S.cloudUp === false ? 'p-err' : 'p-ok');
    if (ld) ld.className = 'pill ' + (k.online ? 'p-ok' : 'p-idle');
  }

  function swap(html, pairs) {
    for (var i = 0; i < pairs.length; i += 2) html = html.split(pairs[i]).join(pairs[i + 1]);
    return html;
  }
  function tidyUi() {
    var css = document.createElement('style');
    /* fields that only mean something on the device: student sign-in passwords */
    css.textContent = '.field:has(#ns-pass),.field:has(#se-pass){display:none}' +
      '.web-stu th:nth-child(2),.web-stu td:nth-child(2){display:none}.kv:empty{display:none}' +
      '.web-note{margin:0 0 14px;padding:11px 14px;border:1px solid rgba(127,127,127,.28);border-radius:12px;' +
      'font-size:12.5px;line-height:1.55;color:var(--txt2)}.web-note b{color:var(--txt)}';
    document.head.appendChild(css);

    /* Student sign-in names and passwords are kept by the device. The website has none,
       so it does not print one (the app would otherwise show a made-up "1001"). */
    try {
      var kv0 = window.kvI;
      window.kvI = function (icon, label) {
        return /^(Password|Login password|Student ID \(Login\)|Login ID \(Name\))$/.test(label) ? '' : kv0.apply(this, arguments);
      };
      var stu0 = VIEWS.students;
      VIEWS.students = function () {
        return swap(stu0.apply(this, arguments), [
          '<table class="tbl"><thead><tr><th>Student (Login ID)</th><th>Password</th>',
          '<table class="tbl web-stu"><thead><tr><th>Student</th><th>Password</th>',
          ' \u00b7 roster synced with device', ' \u00b7 saved in the school database'
        ]);
      };
    } catch (e) {}

    /* Pages that show or control the device's own hardware say so, instead of
       looking live. The website knows one thing: when the device last checked in. */
    try {
      var home0 = VIEWS.home;
      VIEWS.home = function () {
        var html = swap(home0.apply(this, arguments), [
          'Health<small>all hardware checks pass</small></div><div class="sv" style="color:var(--c-ok)">Good</div>',
          'Health<small>checked on the gate device</small></div><div class="sv" style="color:var(--txt3)">On device</div>'
        ]);
        if (kiosk().rssi == null) {               // the app prints "Strong" whatever the signal is
          html = html.replace(/WiFi<small>[^<]*<\/small><\/div><div class="sv" style="color:var\(--c-ok\)">Strong<\/div>/,
            'WiFi<small>the gate device\u2019s own network</small></div><div class="sv" style="color:var(--txt3)">On device</div>');
        }
        return html;
      };
      ['device', 'devicecheck', 'health', 'wifi', 'updater', 'fingerprint'].forEach(function (name) {
        var v0 = VIEWS[name];
        if (typeof v0 !== 'function') return;
        VIEWS[name] = function () {
          var k = kiosk(), html = v0.apply(this, arguments);
          if (name === 'health') html = html.replace(/\d+\/\d+ pass/, 'On device').replace('0 warnings', 'not sent to the website');
          return '<div class="web-note"><b>This page belongs to the gate device.</b> Its hardware readings and controls ' +
                 '(Wi-Fi, fingerprint, firmware update, reader tests) work on the device\u2019s own page, opened on the school Wi-Fi. ' +
                 'The website only knows when the device last checked in: <b>' +
                 (!k.known ? 'no device registered' : k.online ? 'online now' : ago(k.age)) + '</b>.</div>' + html;
        };
      });
    } catch (e) {}
    try {
      var add0 = VIEWS.addstudent;
      VIEWS.addstudent = function () {
        return swap(add0.apply(this, arguments), [
          'Scan-first or direct UID registration \u2014 non-blocking RC522 capture & instant Supabase RPC sync',
          'Saved straight to the school database \u00b7 the gate device picks the student up on its next sync',
          'RC522 non-blocking capture \u00b7 1ms loop', 'On the website the card number is typed, not scanned',
          'Waiting for RFID card tap\u2026', 'Type the card number \u2192',
          'Tap any unregistered RFID card on the RC522 reader (or enter/generate UID on the right)',
          'Enter it in the form, or press Auto to add the student now and give them a card later',
          'Tap a card on the RC522 reader or enter the 8-hex RFID UID below', 'Type the card number below, or press Auto',
          'Tap card on RC522 or type UID', 'e.g. 04A3B2C1',
          '(auto-filled on card tap)', '(printed on the card, or Auto)'
        ]);
      };
    } catch (e) {}

    /* Replace a card: on the device this waits for a tap; here the number is typed. */
    window.bindRfidFlow = function (rfid) {
      var s = studentByRfid(rfid);
      if (!s) return;
      modal({
        title: 'Change RFID card', sub: esc(s.name) + ' \u00b7 currently ' + esc(s.rfid), icon: 'nfc', narrow: true,
        body: '<div class="field"><label>New card number</label><input class="inp mono" id="cb-card" placeholder="e.g. 04A3B2C1" ' +
              'oninput="this.value=this.value.toUpperCase()"></div>' +
              '<div class="tiny muted3" style="margin-top:8px;line-height:1.6">The old card stops working as soon as you save. ' +
              'Attendance history stays with the student.</div>',
        footer: '<button class="btn btn-ghost" data-close>Cancel</button><button class="btn btn-pri" id="cb-save">Save card</button>',
        onOpen: function (ov) {
          var inp = ov.querySelector('#cb-card'), btn = ov.querySelector('#cb-save');
          if (inp) inp.focus();
          btn.onclick = function () {
            btn.disabled = true;
            replaceCard(rfid, inp.value).then(function (r) {
              closeModal(ov);
              toast('Card changed', r.name + ' now scans with ' + r.card + '.', 'ok');
              go(CURRENT);
            }, function (e) {
              btn.disabled = false;
              toast('Could not change the card', (e && e.message) || 'Try again', 'err');
            });
          };
        }
      });
    };
  }

  /* ------------------------------------------------------------------- boot */
  /* A dashboard token without a cloud session (left over from the old pretend
     mode) must not open the dashboard: clear it before the app reads it. */
  if (!readSession()) { lsDel('astro_tok'); lsDel('astro_role'); lsDel('astro_name'); }
  else if (!lsGet('astro_tok')) writeSession(null);

  window.AstroWeb = { paint: paint, refresh: function () { return refresh(true); }, replaceCard: replaceCard,
                      state: function () { return { gen: S.gen, error: S.error, kiosk: kiosk(), signedIn: !!readSession() }; } };

  function tick() {
    if (!readSession()) return;
    if (!lsGet('astro_tok')) {                      // the app signed out
      if (!S.loggingIn && now() - S.loginAt > 6000) signOut();
      return;
    }
    if (document.hidden) return;
    refresh(false).then(noop, noop);
  }
  setInterval(tick, POLL_MS);
  setInterval(paint, 15000);
  document.addEventListener('visibilitychange', function () { if (!document.hidden) tick(); });

  function ready() {
    tidyUi();
    setTimeout(paint, 1600);                        // after the app's own start-up paints
    if (!readSession()) {                           // lets the login page say honestly whether the cloud answers
      sb('/auth/v1/settings', { method: 'GET' }).then(paint, paint);
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', ready);
  else ready();
})();
