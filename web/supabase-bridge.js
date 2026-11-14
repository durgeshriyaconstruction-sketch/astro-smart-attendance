/* ============================================================================
   ASTRO SMART ATTENDANCE — SUPABASE BRIDGE
   ----------------------------------------------------------------------------
   The app in index.html was built for the ESP32: every screen asks /api/...
   for data, and the firmware answers. On a website nobody answers, so the file
   falls back to a fake in-browser database (localApiFallback).

   This file replaces that fallback with the real Supabase database:

     1. Login  -> Supabase Auth (email + password, or a student's full name)
     2. Reads  -> students, attendance, notices, leaves, device health
     3. Writes -> add a student, mark attendance, publish a notice
     4. Honesty-> the "Cloud" pill reflects the ESP32's real last_seen, and
                  hardware numbers the cloud genuinely cannot know show as 0

   Loaded AFTER the app so it can replace the app's globals. Every route is
   wrapped so that a database error degrades to an empty result instead of a
   broken screen.
   ========================================================================== */
(function () {
  'use strict';

  var BASE  = 'https://nrjchonjlncamfyzmfye.supabase.co';
  var KEY   = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5yamNob25qbG5jYW1meXptZnllIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTQ0NzUwNDUsImV4cCI6MjExMDA1MTA0NX0.MtiRrja_PYMWauT-ORzcOcdKHRAIXh3HtjyKeE5AoVM';
  var TZ    = 'Asia/Kolkata';

  var TOKEN = safeGet('sb_token') || '';
  var UID   = safeGet('sb_uid')   || '';
  var schoolId = null;
  var byRfid = {};          // card UID  -> { id, name }
  var byName = {};          // full name -> { id, name, rfid }

  function safeGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function safeSet(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function log() {
    if (!window.console) return;
    var a = ['%c[bridge]', 'color:#3FCBF5'].concat([].slice.call(arguments));
    console.log.apply(console, a);
  }

  /* ---------------------------------------------------------------- helpers */
  function todayISO() {
    return new Date().toLocaleDateString('en-CA', { timeZone: TZ });
  }
  function hhmm(iso) {
    if (!iso) return null;
    return new Date(iso).toLocaleTimeString('en-GB',
      { timeZone: TZ, hour: '2-digit', minute: '2-digit' });
  }
  /* stable small integer from a uuid, so the UI's Number(id) keys stay unique */
  function hashInt(s) {
    s = String(s || '');
    var h = 0;
    for (var i = 0; i < s.length; i++) { h = (h * 31 + s.charCodeAt(i)) | 0; }
    return Math.abs(h);
  }

  function headers(extra) {
    var h = { apikey: KEY, Authorization: 'Bearer ' + (TOKEN || KEY) };
    if (extra) for (var k in extra) h[k] = extra[k];
    return h;
  }

  /* ------------------------------------------------------------- REST + auth */
  function rest(path, opts) {
    opts = opts || {};
    var h = headers(opts.headers);
    if (opts.prefer) h.Prefer = opts.prefer;
    if (opts.body)   h['Content-Type'] = 'application/json';
    return fetch(BASE + '/rest/v1/' + path, {
      method: opts.method || 'GET',
      headers: h,
      body: opts.body,
      cache: 'no-store'
    }).then(function (r) {
      if (!r.ok) {
        return r.text().then(function (t) {
          throw new Error('REST ' + r.status + ' — ' + t.slice(0, 240));
        });
      }
      if (r.status === 204) return null;
      return r.text().then(function (t) { return t ? JSON.parse(t) : null; });
    });
  }

  function rpc(name, args) {
    return rest('rpc/' + name, { method: 'POST', body: JSON.stringify(args || {}) });
  }

  function signIn(email, password) {
    return fetch(BASE + '/auth/v1/token?grant_type=password', {
      method: 'POST',
      headers: { apikey: KEY, 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email, password: password })
    }).then(function (r) {
      return r.json().then(function (j) {
        if (!r.ok) {
          throw new Error(j.error_description || j.error || j.msg || 'Invalid login credentials');
        }
        return j;
      });
    }).then(function (j) {
      TOKEN = j.access_token;
      UID   = (j.user && j.user.id) || '';
      safeSet('sb_token', TOKEN);
      safeSet('sb_uid', UID);
      safeSet('astro_tok', TOKEN);          // the app's own session key
      try { window.TOKEN = TOKEN; } catch (e) {}
      return j;
    });
  }

  function whoAmI() {
    return rest('members?select=role&limit=1').then(function (rows) {
      return (rows && rows[0] && rows[0].role) || null;
    }).catch(function () { return null; });
  }

  function ensureSchool() {
    if (schoolId) return Promise.resolve(schoolId);
    return rest('schools?select=id,name&limit=1').then(function (rows) {
      schoolId = (rows && rows[0] && rows[0].id) || null;
      return schoolId;
    }).catch(function () { return null; });
  }

  /* ------------------------------------------------------------------ reads */
  function studentsPayload() {
    var today = todayISO();
    return Promise.all([
      rest('students?select=id,roll_no,full_name,guardian_name,guardian_email,' +
           'guardian_phone,fingerprint_id,active,class_id,classes(name,section)' +
           '&order=roll_no.asc'),
      rest('rfid_cards?select=student_id,card_uid'),
      rest('attendance?select=student_id,attendance_date,status,marked_at,method' +
           '&order=attendance_date.desc')
    ]).then(function (res) {
      var stu = res[0] || [], cards = res[1] || [], att = res[2] || [];

      var cardOf = {};
      cards.forEach(function (c) {
        var uid = String(c.card_uid || '').toUpperCase();
        if (uid && !cardOf[c.student_id]) cardOf[c.student_id] = uid;
      });

      var rowsOf = {};
      att.forEach(function (a) {
        (rowsOf[a.student_id] = rowsOf[a.student_id] || []).push(a);
      });

      byRfid = {}; byName = {};

      var items = stu.map(function (s) {
        var rows = rowsOf[s.id] || [];
        var counts = { present: 0, late: 0, absent: 0, leave: 0, half: 0 };
        rows.forEach(function (r) {
          var k = r.status === 'half_day' ? 'half' : r.status;
          if (counts[k] !== undefined) counts[k]++;
        });
        var marked = counts.present + counts.late + counts.half;
        var total  = marked + counts.absent + counts.leave;
        var pct    = total ? Math.round((marked * 100) / total) : 0;
        var todayRow = null, last = rows[0] || null;
        for (var i = 0; i < rows.length; i++) {
          if (rows[i].attendance_date === today) { todayRow = rows[i]; break; }
        }

        var uid = cardOf[s.id] || '';
        byRfid[uid] = { id: s.id, name: s.full_name };
        byName[s.full_name] = { id: s.id, name: s.full_name, rfid: uid };

        return {
          rfid: uid,
          studentId: s.full_name,
          displayName: s.full_name,
          name: s.full_name,
          roll: s.roll_no || '—',
          className: s.classes ? s.classes.name : '—',
          section: s.classes ? s.classes.section : '—',
          email: s.guardian_email || '',
          phone: s.guardian_phone || '—',
          parentEmail: s.guardian_email || '',
          parentPhone: s.guardian_phone || '',
          active: s.active !== false,
          present: counts.present, late: counts.late, absent: counts.absent,
          leave: counts.leave, half: counts.half,
          percentage: pct,
          status: todayRow ? todayRow.status : 'none',
          lastDate: last ? last.attendance_date : '',
          lastTime: last ? hhmm(last.marked_at) : '',
          fingerprint: !!s.fingerprint_id,
          fingerprintId: s.fingerprint_id || 0
        };
      });

      log('students', items.length);
      return { ok: true, items: items };
    });
  }

  function calendarPayload() {
    return Promise.all([
      rest('attendance?select=student_id,attendance_date,status,marked_at&order=attendance_date.desc&limit=2000'),
      rest('rfid_cards?select=student_id,card_uid'),
      rest('school_holidays?select=holiday_date')
    ]).then(function (res) {
      var att = res[0] || [], cards = res[1] || [], hol = res[2] || [];
      var cardOf = {};
      cards.forEach(function (c) {
        var uid = String(c.card_uid || '').toUpperCase();
        if (uid && !cardOf[c.student_id]) cardOf[c.student_id] = uid;
      });
      var items = att.map(function (a) {
        return {
          date: a.attendance_date,
          rfid: cardOf[a.student_id] || '',
          status: a.status,
          time: hhmm(a.marked_at)
        };
      });
      return {
        ok: true,
        items: items,
        holidays: hol.map(function (h) { return h.holiday_date; })
      };
    });
  }

  function noticesPayload() {
    return rest('notices?select=id,title,body,priority,audience,pinned,created_at' +
                '&order=created_at.desc&limit=50')
      .then(function (rows) {
        return {
          ok: true,
          items: (rows || []).map(function (n) {
            return {
              id: hashInt(n.id),
              title: n.title || 'Notice',
              body: n.body || '',
              priority: n.priority || 'normal',
              audience: n.audience || 'All',
              pinned: !!n.pinned,
              date: (n.created_at || '').slice(0, 10) || todayISO(),
              by: 'Admin',
              status: 'published'
            };
          })
        };
      });
  }

  function leavesPayload() {
    return rest('leave_requests?select=id,from_date,to_date,reason,status,students(full_name,rfid_cards(card_uid))' +
                '&order=created_at.desc&limit=200')
      .then(function (rows) {
        return {
          ok: true,
          items: (rows || []).map(function (l) {
            var s = l.students || {};
            var card = (s.rfid_cards && s.rfid_cards[0] && s.rfid_cards[0].card_uid) || '';
            return {
              id: hashInt(l.id),
              rfid: String(card).toUpperCase(),
              name: s.full_name || '—',
              from: l.from_date,
              to: l.to_date,
              reason: l.reason || '',
              status: l.status || 'pending'
            };
          })
        };
      });
  }

  function deviceRow() {
    return rest('devices?select=device_code,firmware,last_seen,ip,wifi_rssi,active&limit=1')
      .then(function (rows) { return (rows && rows[0]) || null; });
  }

  function cloudPayload() {
    return deviceRow().then(function (d) {
      var last = d && d.last_seen ? new Date(d.last_seen).getTime() : 0;
      var fresh = last && (Date.now() - last) < 15 * 60 * 1000;
      return {
        ok: true,
        /* honest: the device is "online" only if it checked in recently */
        state: fresh ? 'online' : 'offline',
        authenticated: !!TOKEN,
        wifiConnected: !!fresh,
        databaseHost: 'nrjchonjlncamfyzmfye.supabase.co',
        lastSuccess: Math.floor(last / 1000),
        pendingDailyRecords: 0, pendingPeriodRecords: 0, pendingScanEvents: 0,
        pendingStudents: 0, pendingLeaves: 0, pendingNotifications: 0
      };
    });
  }

  function healthPayload() {
    var today = todayISO();
    return Promise.all([
      deviceRow(),
      rest('students?select=id'),
      rest('attendance?select=id&attendance_date=eq.' + today)
    ]).then(function (res) {
      var d = res[0] || {};
      return {
        ok: true,
        firmware: d.firmware || '—',
        chipId: d.device_code || '—',
        rssi: d.wifi_rssi || 0,
        students: (res[1] || []).length,
        records: (res[2] || []).length,
        /* these are hardware sensors — the cloud genuinely cannot read them */
        heap: 0, uptime: 0, temperature: 0, storageUsed: 0, storageTotal: 0,
        rfid: null, lcd: null, buzzer: null, fingerprint: null,
        fingerprintPower: null, fingerprintEnrolled: 0, queued: 0
      };
    });
  }

  function statusPayload() {
    return deviceRow().then(function (d) {
      return {
        ok: true,
        version: (d && d.firmware) || '26.11.7',
        firmware: (d && d.firmware) || '26.11.7',
        wifi: !!(d && d.last_seen && (Date.now() - new Date(d.last_seen).getTime()) < 15 * 60 * 1000),
        staIp: (d && d.ip) || '',
        apIp: '192.168.4.1',
        rssi: (d && d.wifi_rssi) || 0,
        clockSynced: true, fp: false, uptime: 0
      };
    });
  }

  function devicePayload() {
    return deviceRow().then(function (d) {
      return {
        ok: true,
        apSsid: 'Attendance_System',
        apIp: '192.168.4.1',
        stationIp: (d && d.ip) || '',
        pins: {}
      };
    });
  }

  /* ----------------------------------------------------------------- writes */
  function saveStudent(b) {
    b = b || {};
    var name = String(b.name || '').trim();
    if (!name) return Promise.reject(new Error('Student name is required'));

    return ensureSchool().then(function (sid) {
      if (!sid) throw new Error('No school linked to this account');

      var clsName = String(b.className || '').trim();
      var section = String(b.section || '').trim();
      if (section === '—') section = '';

      return rest('classes?select=id,name,section').then(function (classes) {
        var hit = (classes || []).filter(function (c) {
          return c.name === clsName && (c.section || '') === section;
        })[0];
        if (hit) return hit.id;
        if (!clsName) return null;
        return rest('classes', {
          method: 'POST', prefer: 'return=representation',
          body: JSON.stringify({ school_id: sid, name: clsName, section: section })
        }).then(function (rows) { return rows && rows[0] && rows[0].id; })
          .catch(function (e) { log('class create failed (student still saved):', e.message); return null; });
      }).then(function (classId) {
        return rest('students', {
          method: 'POST', prefer: 'return=representation',
          body: JSON.stringify({
            school_id: sid,
            class_id: classId || null,
            roll_no: String(b.roll || '').trim() || null,
            full_name: name,
            guardian_name: b.guardianName || null,
            guardian_email: b.parentEmail || b.email || null,
            guardian_phone: b.parentPhone || b.phone || null
          })
        });
      }).then(function (rows) {
        var id = rows && rows[0] && rows[0].id;
        var uid = String(b.rfid || '').toUpperCase().trim();
        if (!id || !uid) return { ok: true, id: id };
        return rest('rfid_cards', {
          method: 'POST', prefer: 'return=representation',
          body: JSON.stringify({ school_id: sid, student_id: id, card_uid: uid })
        }).then(function () { return { ok: true, id: id }; });
      });
    });
  }

  function markAttendance(b) {
    b = b || {};
    var uid = String(b.rfid || b.uid || '').toUpperCase();
    var status = String(b.status || 'present').toLowerCase();
    var date = b.date || todayISO();
    var who = byRfid[uid];
    if (!who) return Promise.reject(new Error('That card is not linked to a student'));

    return ensureSchool().then(function (sid) {
      return rest('attendance?select=id&student_id=eq.' + who.id +
                  '&attendance_date=eq.' + date + '&session=eq.daily')
        .then(function (rows) {
          if (rows && rows.length) {
            return rest('attendance?id=eq.' + rows[0].id, {
              method: 'PATCH',
              body: JSON.stringify({ status: status, marked_at: new Date().toISOString(), method: 'manual' })
            });
          }
          return rest('attendance', {
            method: 'POST',
            body: JSON.stringify({
              school_id: sid, student_id: who.id, attendance_date: date,
              session: 'daily', status: status, method: 'manual',
              marked_at: new Date().toISOString(), note: b.note || null
            })
          });
        });
    }).then(function () { return { ok: true }; });
  }

  function postNotice(b) {
    b = b || {};
    return ensureSchool().then(function (sid) {
      return rest('notices', {
        method: 'POST',
        body: JSON.stringify({
          school_id: sid,
          title: b.title || 'Notice',
          body: b.body || b.message || '',
          priority: b.priority || 'normal',
          audience: b.audience || 'All',
          pinned: !!b.pinned,
          created_by: UID || null
        })
      });
    }).then(function () { return { ok: true }; });
  }

  /* ---------------------------------------------------------------- routing */
  function route(path, method, body) {
    var clean = String(path || '').split('?')[0];
    var m = String(method || 'GET').toUpperCase();

    if (clean === '/api/login' && m === 'POST') {
      return signIn(body.email, body.password).then(function () {
        return { ok: true, token: TOKEN, type: 'admin', name: 'Administrator' };
      });
    }
    if (clean === '/api/students'    && m === 'GET')  return studentsPayload();
    if (clean === '/api/calendar'    && m === 'GET')  return calendarPayload();
    if (clean === '/api/notices'     && m === 'GET')  return noticesPayload();
    if (clean === '/api/leaves'      && m === 'GET')  return leavesPayload();
    if (clean === '/api/cloud'       && m === 'GET')  return cloudPayload();
    if (clean === '/api/health'      && m === 'GET')  return healthPayload();
    if (clean === '/api/status'      && m === 'GET')  return statusPayload();
    if (clean === '/version'         && m === 'GET')  return statusPayload();
    if (clean === '/api/device'      && m === 'GET')  return devicePayload();
    if (clean === '/api/student/save' && m === 'POST') return saveStudent(body);
    if (clean === '/api/notice'      && m === 'POST') return postNotice(body);
    if (clean === '/api/attendance/mark' && m === 'POST') return markAttendance(body);

    /* no card reader in a browser — never pretend one is listening */
    if (clean === '/api/registration/status' && m === 'GET') {
      return Promise.resolve({ ok: true, captured: false, rfid: null });
    }
    if (clean === '/api/registration/start' && m === 'POST') {
      return Promise.reject(new Error('The card reader lives on the ESP32. Use “Add student” in the cloud panel to type the card number instead.'));
    }
    return null;
  }

  function wrapped(original, name) {
    return function (path, method, body) {
      var res;
      try { res = route(path, method, body); }
      catch (e) { log(name, 'route threw', e && e.message); res = null; }

      if (!res) return original.apply(this, arguments);

      return Promise.resolve(res).catch(function (e) {
        log(name, String(path), 'failed:', e && e.message);
        /* degrade to an empty result so a screen never breaks */
        var clean = String(path || '').split('?')[0];
        if (clean === '/api/students' || clean === '/api/notices' ||
            clean === '/api/leaves'   || clean === '/api/calendar') {
          return { ok: true, items: [] };
        }
        throw e;
      });
    };
  }

  /* ------------------------------------------------------------------ login */
  window.doLogin = function () {
    var btn = document.getElementById('login-btn');
    var err = document.getElementById('login-err');
    var idEl = document.getElementById('login-id');
    var pwEl = document.getElementById('login-pw');
    if (!idEl || !pwEl) return;

    var id = idEl.value.trim(), pw = pwEl.value;
    var fail = function (msgRaw, msgHtml) {
      if (btn) { btn.innerHTML = 'Sign in'; btn.disabled = false; }
      if (typeof window.loginError === 'function') window.loginError(msgHtml || msgRaw);
      else if (err) { err.innerHTML = msgHtml || msgRaw; err.classList.remove('hidden'); }
    };

    if (err) err.classList.add('hidden');
    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spin"></span>Verifying…'; }
    if (!id) return fail('Enter your email, or a student\u2019s full name.');
    if (!pw) return fail('Enter your password.');

    var email = id;
    var lookup = id.indexOf('@') >= 0
      ? Promise.resolve(id)
      : rpc('resolve_login_email', { p_name: id }).then(function (found) {
          if (!found) throw new Error('No student account is linked to “' + id + '”.');
          return found;
        });

    lookup
      .then(function (mail) { return signIn(mail, pw); })
      .then(function () { return whoAmI(); })
      .then(function (role) {
        if (!role) throw new Error('Signed in, but this account is not linked to a school yet.');
        if (btn) { btn.disabled = false; btn.innerHTML = 'Sign in'; }
        window.startSession('admin');
        if (typeof window.syncAll === 'function') window.syncAll(true);
      })
      .catch(function (e) {
        var m = (e && e.message) || 'Could not sign in';
        fail(m, m === 'Invalid login credentials'
          ? 'Wrong email or password.'
          : String(m).replace(/[<>]/g, ''));
      });
  };

  /* ------------------------------------------------------- replace the paths */
  if (typeof window.api === 'function') {
    window.api = wrapped(window.api, 'api');
    log('api() now reads Supabase');
  }
  if (typeof window.localApiFallback === 'function') {
    window.localApiFallback = wrapped(window.localApiFallback, 'fallback');
    log('localApiFallback() now prefers Supabase');
  }

  /* ------------------------------------------------- cloud add-student panel */
  function ensureAddButton() {
    if (document.getElementById('sb-add-student')) return;
    var b = document.createElement('button');
    b.id = 'sb-add-student';
    b.className = 'btn btn-pri';
    b.textContent = '+ Add student (cloud)';
    b.style.cssText = 'position:fixed;right:18px;bottom:18px;z-index:9998;' +
                      'border-radius:999px;padding:12px 18px;box-shadow:0 10px 30px -8px rgba(63,203,245,.6)';
    b.onclick = openAddStudent;
    document.body.appendChild(b);
  }

  function openAddStudent() {
    var ov = document.createElement('div');
    ov.style.cssText = 'position:fixed;inset:0;z-index:9999;background:rgba(3,6,12,.72);' +
                       'backdrop-filter:blur(3px);display:flex;align-items:center;justify-content:center;padding:18px';
    ov.innerHTML =
      '<div class="card" style="width:100%;max-width:440px;padding:22px">' +
        '<div class="card-t" style="font-size:16px">Add a student</div>' +
        '<div class="card-s" style="margin-bottom:14px">Saved straight to the database. ' +
          'Leave the card number blank if they have no RFID card yet.</div>' +
        '<div class="field"><label>Full name</label>' +
          '<input class="inp" id="sb-name" placeholder="e.g. Aarav Sharma"></div>' +
        '<div style="display:flex;gap:10px">' +
          '<div class="field" style="flex:1"><label>Roll no</label>' +
            '<input class="inp" id="sb-roll" placeholder="01"></div>' +
          '<div class="field" style="flex:1"><label>Class</label>' +
            '<input class="inp" id="sb-class" placeholder="Class 9"></div>' +
          '<div class="field" style="width:80px"><label>Section</label>' +
            '<input class="inp" id="sb-sec" placeholder="A"></div>' +
        '</div>' +
        '<div class="field"><label>Card UID (optional)</label>' +
          '<input class="inp mono" id="sb-rfid" placeholder="04A3B2C1"></div>' +
        '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:6px">' +
          '<button class="btn" id="sb-cancel">Cancel</button>' +
          '<button class="btn btn-pri" id="sb-save">Save student</button>' +
        '</div>' +
        '<div id="sb-msg" class="tiny" style="margin-top:10px;color:var(--c-err)"></div>' +
      '</div>';
    document.body.appendChild(ov);

    var close = function () { ov.remove(); };
    ov.querySelector('#sb-cancel').onclick = close;
    ov.addEventListener('click', function (e) { if (e.target === ov) close(); });

    ov.querySelector('#sb-save').onclick = function () {
      var btn = ov.querySelector('#sb-save');
      var msg = ov.querySelector('#sb-msg');
      btn.disabled = true; btn.textContent = 'Saving…';
      msg.textContent = '';
      saveStudent({
        name:   ov.querySelector('#sb-name').value,
        roll:   ov.querySelector('#sb-roll').value,
        className: ov.querySelector('#sb-class').value,
        section:   ov.querySelector('#sb-sec').value,
        rfid:   ov.querySelector('#sb-rfid').value
      }).then(function () {
        close();
        if (typeof window.toast === 'function') {
          window.toast('Student added', 'Saved to the database.', 'ok');
        }
        if (typeof window.syncAll === 'function') window.syncAll(true);
      }).catch(function (e) {
        btn.disabled = false; btn.textContent = 'Save student';
        msg.textContent = (e && e.message) || 'Could not save';
      });
    };
  }

  function boot() {
    if (TOKEN) { try { window.TOKEN = TOKEN; } catch (e) {} }
    ensureAddButton();
    document.addEventListener('click', function (e) {
      var t = e.target;
      if (t && t.closest && t.closest('#logout-btn, .logout, [onclick*="logout"]')) return;
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else { boot(); }

  window.astroBridge = {
    rest: rest, rpc: rpc, signIn: signIn,
    students: studentsPayload, calendar: calendarPayload,
    cloud: cloudPayload, saveStudent: saveStudent,
    get token() { return TOKEN; }
  };
  log('bridge ready — database', BASE.replace('https://', ''));
})();
