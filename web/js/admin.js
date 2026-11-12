// Staff screens: today, reports, students, notices, inbox, leave approvals,
// settings, terminals and the email queue. Every write goes through an RPC, so
// the database — not this file — decides who may do what.
import { rpc, rest, q } from './api.js';
import {
  h, clear, card, chip, button, field, input, selectEl, emptyState, toast,
  flashError, fmtDate, fmtTime, fmtDateTime, todayIn, zonedToIso, statusMeta, table, downloadCsv,
} from './ui.js';

const TABS = [
  ['today', 'Today'],
  ['report', 'Report'],
  ['students', 'Students'],
  ['notices', 'Notices'],
  ['inbox', 'Inbox'],
  ['leaves', 'Leaves'],
  ['settings', 'Settings'],
  ['devices', 'Devices'],
  ['outbox', 'Emails'],
];

const errLine = (err) => h('p', { class: 'muted' }, err?.message || String(err));

export function renderAdmin(root, state) {
  const school = state.whoami.school || {};
  const tz = school.timezone || 'Asia/Kolkata';
  const isAdmin = state.whoami.role === 'admin';
  const readOnly = state.whoami.role === 'viewer';

  let tab = 'today';
  let devices = [];
  let classes = [];
  let students = [];

  const nav = h('nav', { class: 'tabs' });
  const body = h('main', { class: 'content' });
  const banner = readOnly
    ? h('p', { class: 'banner' },
      'Read-only view — you can see attendance, notices and settings, but not change them.')
    : null;
  root.append(nav, ...(banner ? [banner] : []), body);

  const views = {
    today: () => todayTab(body),
    report: () => reportTab(body),
    students: () => studentsTab(body),
    notices: () => noticesTab(body),
    inbox: () => inboxTab(body),
    leaves: () => leavesTab(body),
    settings: () => settingsTab(body),
    devices: () => devicesTab(body),
    outbox: () => outboxTab(body),
  };

  function draw() {
    clear(nav);
    for (const [key, label] of TABS) {
      nav.append(h('button', {
        class: `tab ${tab === key ? 'active' : ''}`,
        type: 'button',
        onclick: () => { tab = key; draw(); },
      }, label));
    }
    clear(body);
    views[tab]();
  }

  const busy = (host, text = 'Loading…') => clear(host).append(h('p', { class: 'empty' }, text));
  const fail = (host, title, err) => clear(host).append(card(title, errLine(err)));

  // ------------------------------------------------------------- today ----
  async function todayTab(host) {
    let date = todayIn(tz);
    const draw = async () => {
      busy(host);
      let ov;
      try {
        ov = await rpc('astro_day_overview', { p_date: date });
      } catch (err) { return fail(host, 'Today', err); }

      const c = ov.counts || {};
      const toolbar = h('div', { class: 'row toolbar' },
        h('input', { type: 'date', value: date, onchange: (e) => { date = e.target.value; draw(); } }),
        button('Refresh', draw, 'btn ghost small'),
        readOnly ? null : button('Set holiday', async () => {
          const name = prompt('Holiday name', 'Holiday');
          if (name === null) return;
          try {
            const r = await rpc('astro_set_holiday', { p_date: date, p_name: name });
            toast(`Holiday saved${r.auto_absences_removed ? `, ${r.auto_absences_removed} auto-absence(s) cleared` : ''}`);
            draw();
          } catch (err) { flashError(err); }
        }, 'btn ghost small'),
        readOnly ? null : button('Remove holiday', async () => {
          try {
            await rpc('astro_remove_holiday', { p_date: date });
            toast('Holiday removed');
            draw();
          } catch (err) { flashError(err); }
        }, 'btn ghost small'),
        readOnly ? null : button('Close the day', async () => {
          if (!confirm(`Mark every active student without a tap on ${date} as absent and email their guardians?`)) return;
          try {
            const r = await rpc('astro_close_day', { p_date: date });
            toast(`${r.absent_marked} marked absent · ${r.alerts_queued} email(s) queued`);
            draw();
          } catch (err) { flashError(err); }
        }, 'btn small'));

      const banner = [];
      if (ov.is_holiday) banner.push(h('div', { class: 'banner off' }, `Holiday · ${ov.holiday || 'Declared'}`));
      if (ov.is_weekly_off) banner.push(h('div', { class: 'banner off' }, 'Weekly off'));
      if (ov.absent_after) banner.push(h('div', { class: 'banner' }, `After ${ov.absent_after} arrivals are recorded absent`));

      const chips = h('div', { class: 'chips' },
        chip(`Total ${c.total ?? 0}`, 'strong'),
        chip(`Present ${c.present ?? 0}`, 'ok'),
        chip(`Late ${c.late ?? 0}`, 'warn'),
        chip(`Absent ${c.absent ?? 0}`, 'bad'),
        chip(`Leave ${c.leave ?? 0}`, 'leave'),
        chip(`Not marked ${c.not_marked ?? 0}`, 'muted'));

      const rows = (ov.students || []).map((s) => {
        const meta = statusMeta(s.status);
        const setter = readOnly ? meta.label : selectEl(
          [
            { value: '', label: '—' },
            { value: 'present', label: 'Present' },
            { value: 'late', label: 'Late' },
            { value: 'absent', label: 'Absent' },
            { value: 'leave', label: 'Leave' },
            { value: 'clear', label: 'Clear' },
          ],
          '',
          async (v) => {
            if (!v) return;
            try {
              const r = await rpc('astro_set_attendance', {
                p_student_id: s.student_id, p_date: date, p_status: v,
              });
              toast(`${s.name} → ${v === 'clear' ? 'not marked' : v}`);
              if (r?.status === 'leave') toast('Recorded as leave', 'info');
              draw();
            } catch (err) { flashError(err); }
          },
          { class: 'status-select' },
        );
        return [s.roll_no, s.name, s.class, chip(meta.label, meta.cls), s.time || '', setter];
      });

      clear(host).append(
        h('div', { class: 'card' }, toolbar, ...banner, chips),
        (ov.students || []).length
          ? table(['Roll', 'Student', 'Class', 'Status', 'Marked at', readOnly ? '' : 'Change'], rows)
          : card(null, emptyState('No active students yet. Add one under Students.')),
      );
    };
    draw();
  }

  // ------------------------------------------------------------ report ----
  async function reportTab(host) {
    const first = `${todayIn(tz).slice(0, 7)}-01`;
    let from = first;
    let to = todayIn(tz);
    let classId = '';

    const draw = async () => {
      busy(host);
      try {
        if (!classes.length) {
          classes = await rest(`classes?${q({ select: 'id,name,section,teacher', order: 'name.asc,section.asc' })}`) || [];
        }
        const rep = await rpc('astro_attendance_report', {
          p_from: from, p_to: to, p_class_id: classId || null,
        });
        const head = h('div', { class: 'row toolbar' },
          field('From', h('input', { type: 'date', value: from, onchange: (e) => { from = e.target.value; draw(); } })),
          field('To', h('input', { type: 'date', value: to, onchange: (e) => { to = e.target.value; draw(); } })),
          field('Class', selectEl(
            [{ value: '', label: 'All classes' },
              ...classes.map((c) => ({ value: c.id, label: `${c.name}-${c.section}` }))],
            classId, (v) => { classId = v; draw(); })),
          button('Download CSV', () => {
            const rows = [['Roll', 'Student', 'Class', 'Present', 'Late', 'Absent', 'Leave', 'Attendance %']];
            for (const s of rep.students || []) {
              rows.push([s.roll_no, s.name, s.class || '', s.present, s.late, s.absent, s.leave, s.percent ?? '']);
            }
            downloadCsv(`attendance-${from}-to-${to}.csv`, rows);
          }, 'btn ghost small'));

        const t = rep.totals || {};
        const chips = h('div', { class: 'chips' },
          chip(`${rep.school_days ?? 0} school days`, 'muted'),
          chip(`${t.students ?? 0} students`, 'strong'),
          chip(`${t.present ?? 0} present`, 'ok'),
          chip(`${t.late ?? 0} late`, 'warn'),
          chip(`${t.absent ?? 0} absent`, 'bad'),
          chip(`${t.leave ?? 0} leave`, 'leave'));

        const rows = (rep.students || []).map((s) => [
          s.roll_no, s.name, s.class || '—',
          String(s.present), String(s.late), String(s.absent), String(s.leave),
          s.percent === null || s.percent === undefined
            ? '—'
            : chip(`${s.percent}%`, s.percent >= 90 ? 'ok' : s.percent >= 75 ? 'warn' : 'bad'),
        ]);

        clear(host).append(
          card(null, head, chips),
          rows.length ? table(['Roll', 'Student', 'Class', 'P', 'L', 'A', 'Leave', '%'], rows)
            : card(null, emptyState('No students in that range.')));
      } catch (err) { fail(host, 'Report', err); }
    };
    draw();
  }

  // ---------------------------------------------------------- students ----
  async function studentsTab(host) {
    busy(host);
    try {
      if (!classes.length) {
        classes = await rest(`classes?${q({ select: 'id,name,section,teacher', order: 'name.asc,section.asc' })}`) || [];
      }
      students = await rest(`students?${q({
        select: 'id,roll_no,full_name,class_id,guardian_name,guardian_email,guardian_phone,active,fingerprint_id',
        order: 'roll_no.asc',
      })}`) || [];
      if (!devices.length) {
        const dh = await rpc('astro_device_health');
        devices = dh.devices || [];
      }
    } catch (err) { return fail(host, 'Students', err); }

    const search = h('input', { type: 'search', placeholder: 'Search name or roll…', class: 'search' });
    const listBox = h('div', {});
    let editing = null;

    const classLabel = (id) => {
      const c = classes.find((x) => x.id === id);
      return c ? `${c.name}-${c.section}` : '—';
    };

    const drawList = () => {
      const term = search.value.trim().toLowerCase();
      const shown = students.filter((s) => !term
        || s.full_name.toLowerCase().includes(term)
        || s.roll_no.toLowerCase().includes(term));
      clear(listBox);
      if (!shown.length) {
        listBox.append(card(null, emptyState(students.length ? 'No match.' : 'No students yet — add the first one below.')));
        return;
      }
      listBox.append(table(
        ['Roll', 'Student', 'Class', 'Guardian email', 'Fingerprint', 'Active', ''],
        shown.map((s) => [
          s.roll_no, s.full_name, classLabel(s.class_id),
          s.guardian_email || h('span', { class: 'muted' }, 'none'),
          s.fingerprint_id ? `slot ${s.fingerprint_id}` : '—',
          s.active ? chip('active', 'ok') : chip('archived', 'muted'),
          h('div', { class: 'row end' },
            readOnly ? null : button('Edit', () => openForm(s), 'btn ghost small'),
            readOnly ? null : button(s.active ? 'Archive' : 'Restore', async () => {
              if (s.active && !confirm(`Archive ${s.full_name}? Attendance history is kept.`)) return;
              try {
                await rpc('astro_archive_student', { p_student_id: s.id, p_active: !s.active });
                toast(s.active ? 'Archived' : 'Restored');
                studentsTab(host);
              } catch (err) { flashError(err); }
            }, 'btn ghost small'),
          ),
        ]),
      ));
    };

    const formHost = h('div', {});
    const openForm = (student) => {
      editing = student || null;
      clear(formHost);
      const cls = selectEl(
        [{ value: '', label: '— no class —' },
          ...classes.map((c) => ({ value: c.id, label: `${c.name}-${c.section}` }))],
        student?.class_id || '');
      const roll = h('input', { type: 'text', value: student?.roll_no || '', placeholder: 'e.g. 9A-14' });
      const name = h('input', { type: 'text', value: student?.full_name || '', placeholder: 'Full name' });
      const gname = h('input', { type: 'text', value: student?.guardian_name || '' });
      const gmail = h('input', { type: 'email', value: student?.guardian_email || '' });
      const gphone = h('input', { type: 'tel', value: student?.guardian_phone || '' });
      const cardUid = h('input', { type: 'text', placeholder: 'Card UID (tap a card or type it)' });
      const slot = h('input', { type: 'number', min: '1', max: '999', placeholder: 'Fingerprint slot' });
      const device = selectEl(
        [{ value: '', label: '— terminal (only for fingerprints) —' },
          ...devices.map((d) => ({ value: d.device_code, label: d.device_code }))],
        devices[0]?.device_code || '');

      const status = h('div', { class: 'muted small' });
      const save = button(student ? 'Save changes' : 'Add student', async () => {
        save.disabled = true;
        status.textContent = 'Saving…';
        try {
          const res = await rpc('astro_save_student', {
            p_roll_no: roll.value.trim() || null,
            p_full_name: name.value.trim() || null,
            p_class_id: cls.value || null,
            p_guardian_name: gname.value,
            p_guardian_email: gmail.value,
            p_guardian_phone: gphone.value,
            p_card_uid: cardUid.value.trim() || null,
            p_fingerprint_slot: slot.value ? Number(slot.value) : null,
            p_device_code: device.value || null,
            p_student_id: student?.id || null,
          });
          if (res && res.ok === false) {
            status.textContent = `${res.reason}${res.owner ? ` — held by ${res.owner}` : ''}`;
            toast(res.reason, 'error');
          } else {
            toast(student ? 'Saved' : `${res.student.full_name} added`);
            studentsTab(host);
          }
        } catch (err) {
          flashError(err);
          status.textContent = err.message;
        } finally {
          save.disabled = false;
        }
      }, 'btn primary');

      const scan = button('Scan a card', async () => {
        const code = device.value;
        if (!code) { toast('Pick a terminal first', 'error'); return; }
        status.textContent = 'Waiting for a card tap at the terminal…';
        try {
          const cmd = await rpc('astro_queue_command', { p_device_code: code, p_kind: 'rfid_capture' });
          if (cmd.device_online === false) status.textContent = `${cmd.hint || 'Terminal offline'} · waiting…`;
          const done = await pollCommand(cmd.command_id, status);
          if (done?.result?.uid) {
            cardUid.value = done.result.uid;
            status.textContent = done.result.known
              ? `Card ${done.result.uid} already belongs to ${done.result.owner?.name} (${done.result.owner?.roll_no})`
              : `Card ${done.result.uid} ready to assign`;
          } else {
            status.textContent = done ? `No card read (${done.status})` : 'Timed out — try again';
          }
        } catch (err) { flashError(err); }
      }, 'btn ghost small');

      const enroll = button('Enrol fingerprint', async () => {
        if (!code2()) return;
        status.textContent = 'Place the same finger twice on the sensor…';
        try {
          const cmd = await rpc('astro_queue_command', {
            p_device_code: device.value,
            p_kind: 'fp_enroll',
            p_payload: student ? { student_id: student.id } : {},
          });
          if (cmd.device_online === false) status.textContent = `${cmd.hint || 'Terminal offline'} · waiting…`;
          const done = await pollCommand(cmd.command_id, status);
          if (done && done.status === 'done' && done.result?.slot) {
            slot.value = done.result.slot;
            status.textContent = `Fingerprint stored in slot ${done.result.slot}`;
          } else {
            status.textContent = done ? `Enrolment ${done.status}` : 'Timed out';
          }
        } catch (err) { flashError(err); }
      }, 'btn ghost small');
      const code2 = () => device.value ? true : (toast('Pick a terminal first', 'error'), false);

      if (student) {
        cardUid.placeholder = 'New card UID (optional)';
      }

      formHost.append(card(student ? `Edit ${student.full_name}` : 'Add a student',
        h('div', { class: 'grid-2' }, field('Roll number', roll), field('Full name', name)),
        h('div', { class: 'grid-2' }, field('Class', cls), field('Guardian name', gname)),
        h('div', { class: 'grid-2' }, field('Guardian email', gmail), field('Guardian phone', gphone)),
        h('div', { class: 'grid-2' },
          field('Card UID', cardUid, 'Leave blank to keep the current card'),
          field('Fingerprint slot', slot, '1–999, unique per school')),
        field('Terminal', device, 'Needed for card scan and fingerprint enrolment'),
        h('div', { class: 'row end' }, isAdmin ? scan : null, isAdmin ? enroll : null, save),
        status,
        student ? h('div', { class: 'row end' },
          button('Release card', async () => {
            const uid = prompt('Card UID to release');
            if (!uid) return;
            try {
              await rpc('astro_unassign_card', { p_card_uid: uid });
              toast('Card released');
            } catch (err) { flashError(err); }
          }, 'btn ghost small'),
          button('Close', () => { clear(formHost); }, 'btn ghost small')) : null));
    };

    const classBox = h('div', {});
    const drawClasses = () => {
      clear(classBox);
      const name = h('input', { type: 'text', placeholder: '9', class: 'tiny-input' });
      const section = h('input', { type: 'text', placeholder: 'B', class: 'tiny-input' });
      const teacher = h('input', { type: 'text', placeholder: 'Class teacher (optional)' });
      classBox.append(card('Classes',
        h('div', { class: 'row wrap' },
          ...classes.map((c) => h('span', { class: 'tag' },
            `${c.name}-${c.section}`,
            readOnly ? null : h('button', {
              class: 'icon-btn tiny', type: 'button', title: 'Delete class',
              onclick: async () => {
                if (!confirm(`Delete class ${c.name}-${c.section}?`)) return;
                try {
                  await rpc('astro_delete_class', { p_class_id: c.id });
                  classes = [];
                  toast('Class deleted');
                  studentsTab(host);
                } catch (err) { flashError(err); }
              },
            }, '×'))),
          classes.length ? null : h('span', { class: 'muted small' }, 'No classes yet.')),
        readOnly ? null : h('div', { class: 'row wrap' },
          name, section, teacher,
          button('Add class', async () => {
            try {
              const r = await rpc('astro_save_class', {
                p_name: name.value.trim(), p_section: section.value.trim(), p_teacher: teacher.value.trim() || null,
              });
              if (r.ok === false) toast(r.reason, 'error');
              else { toast(`Class ${r.label} added`); classes = []; studentsTab(host); }
            } catch (err) { flashError(err); }
          }, 'btn small'))));
    };

    search.addEventListener('input', drawList);
    clear(host).append(
      formHost,
      h('div', { class: 'row between' },
        h('h2', { class: 'section-title' }, 'Students'),
        readOnly ? null : button('+ New student', () => openForm(null), 'btn primary small')),
      search,
      listBox,
      classBox);
    drawList();
    drawClasses();
  }

  // ----------------------------------------------------------- notices ----
  async function noticesTab(host) {
    busy(host);
    if (!classes.length) {
      classes = await rest(`classes?${q({ select: 'id,name,section,teacher', order: 'name.asc,section.asc' })}`) || [];
    }
    if (!students.length) {
      students = await rest(`students?${q({
        select: 'id,roll_no,full_name,class_id,guardian_name,guardian_email,guardian_phone,active,fingerprint_id',
        order: 'roll_no.asc',
      })}`) || [];
    }
    let notices = [];
    try {
      notices = await rest(`notices?${q({
        select: 'id,title,body,priority,audience,pinned,created_at,expires_at,class_id,student_id',
        order: 'created_at.desc',
        limit: 50,
      })}`) || [];
    } catch (err) { return fail(host, 'Notices', err); }

    const title = h('input', { type: 'text', placeholder: 'Title' });
    const bodyText = h('textarea', { rows: '4', placeholder: 'What do you want to tell the families?' });
    const priority = selectEl([
      { value: 'normal', label: 'Normal' },
      { value: 'important', label: 'Important' },
      { value: 'critical', label: 'Urgent' },
    ], 'normal');
    const audience = selectEl([
      { value: 'all', label: 'Everyone' },
      { value: 'class', label: 'One class' },
      { value: 'student', label: 'One student' },
      { value: 'students', label: 'Students only' },
      { value: 'staff', label: 'Staff only' },
    ], 'all');
    const classPick = selectEl([{ value: '', label: '— class —' },
      ...classes.map((c) => ({ value: c.id, label: `${c.name}-${c.section}` }))], '');
    const studentPick = selectEl([{ value: '', label: '— student —' },
      ...students.map((s) => ({ value: s.id, label: `${s.full_name} (${s.roll_no})` }))], '');
    const pinned = h('input', { type: 'checkbox' });
    const expires = h('input', { type: 'datetime-local' });
    const status = h('div', { class: 'muted small' });

    const classField = field('Class', classPick);
    const studentField = field('Student', studentPick);
    const syncAudience = () => {
      classField.style.display = audience.value === 'class' ? '' : 'none';
      studentField.style.display = audience.value === 'student' ? '' : 'none';
    };
    audience.addEventListener('change', syncAudience);

    const post = button('Publish notice', async () => {
      post.disabled = true;
      status.textContent = 'Publishing…';
      try {
        const r = await rpc('astro_post_notice', {
          p_title: title.value.trim(),
          p_body: bodyText.value.trim(),
          p_priority: priority.value,
          p_audience: audience.value,
          p_class_id: audience.value === 'class' ? classPick.value : null,
          p_student_id: audience.value === 'student' ? studentPick.value : null,
          p_pinned: pinned.checked,
          p_expires_at: zonedToIso(expires.value, tz),
        });
        toast(`Published · ${r.recipients} guardian email(s) queued`);
        noticesTab(host);
      } catch (err) { flashError(err); status.textContent = err.message; }
      finally { post.disabled = false; }
    }, 'btn primary');

    const list = h('div', {});
    if (!notices.length) list.append(emptyState('No notices yet.'));
    for (const n of notices) {
      list.append(h('div', { class: `notice ${n.priority === 'critical' ? 'notice-critical' : n.priority === 'important' ? 'notice-important' : 'notice-normal'}` },
        h('div', { class: 'notice-head' },
          h('h3', {}, n.title),
          chip(n.audience, 'muted'),
          n.pinned ? chip('pinned', 'strong') : null,
          readOnly ? null : h('button', {
            class: 'icon-btn', type: 'button', title: 'Delete notice',
            onclick: async () => {
              if (!confirm('Delete this notice and cancel unsent emails?')) return;
              try {
                await rpc('astro_delete_notice', { p_notice_id: n.id });
                toast('Notice deleted');
                noticesTab(host);
              } catch (err) { flashError(err); }
            },
          }, '🗑')),
        h('p', { class: 'notice-body' }, n.body),
        h('div', { class: 'muted small' }, fmtDate(n.created_at),
          n.expires_at ? ` · until ${fmtDate(n.expires_at)}` : '')));
    }

    clear(host).append(
      readOnly ? null : card('New notice',
        field('Title', title),
        field('Message', bodyText),
        h('div', { class: 'grid-2' }, field('Priority', priority), field('Audience', audience),
          classField, studentField),
        h('div', { class: 'row wrap' },
          h('label', { class: 'check' }, pinned, ' Pin to top'),
          field('Expires', expires)),
        h('div', { class: 'row end' }, post), status),
      h('h2', { class: 'section-title' }, 'Published'),
      list);

    syncAudience();
  }

  // ------------------------------------------------------------- inbox ----
  async function inboxTab(host) {
    busy(host);
    let inbox;
    try {
      inbox = await rpc('astro_inbox', { p_limit: 100 });
    } catch (err) { return fail(host, 'Inbox', err); }

    const convs = inbox.conversations || [];
    const threadBox = h('div', { class: 'card thread-host' },
      emptyState('Pick a conversation.'));

    const openThread = async (studentId, name) => {
      busy(threadBox, 'Loading…');
      try {
        const feed = await rpc('astro_student_feed', { p_student_id: studentId, p_limit: 100 });
        const msgs = (feed.messages || []).slice().reverse();
        const thread = h('div', { class: 'thread' });
        if (!msgs.length) thread.append(emptyState('No messages yet.'));
        for (const m of msgs) {
          const mine = m.direction === 'to_student';
          thread.append(h('div', { class: `bubble ${mine ? 'bubble-school' : 'bubble-mine'}` },
            h('div', { class: 'bubble-meta' }, mine ? 'School' : name, ' · ', fmtDateTime(m.created_at, tz),
              mine && m.read_at ? ' · read' : ''),
            h('div', { class: 'bubble-body' }, m.body),
            isAdmin ? h('button', {
              class: 'icon-btn tiny', type: 'button', title: 'Delete message',
              onclick: async () => {
                if (!confirm('Delete this message from the thread?')) return;
                try {
                  await rpc('astro_delete_message', { p_message_id: m.id });
                  toast('Message deleted');
                  openThread(studentId, name);
                } catch (err) { flashError(err); }
              },
            }, '🗑') : null));
        }
        const subject = h('input', { type: 'text', placeholder: 'Subject', value: 'Message from school' });
        const text = h('textarea', { rows: '3', placeholder: 'Reply…' });
        const send = button('Send', async () => {
          if (!text.value.trim()) return;
          send.disabled = true;
          try {
            const sent = await rpc('astro_send_message', {
              p_student_id: studentId, p_subject: subject.value.trim() || 'Message from school',
              p_body: text.value.trim(),
            });
            if (sent && sent.email_queued === false) {
              toast(sent.guardian_email_on_file === false
                ? 'Saved in the inbox — this family has no guardian email, so no email went out'
                : 'Saved in the inbox — the email was not queued', 'error');
            } else {
              toast('Sent · email queued for the guardian');
            }
            openThread(studentId, name);
          } catch (err) { flashError(err); }
          finally { send.disabled = false; }
        }, 'btn primary small');
        clear(threadBox).append(
          h('h2', { class: 'card-title' }, name),
          thread,
          readOnly ? null : h('div', { class: 'composer' }, subject, text, h('div', { class: 'row end' }, send)));
        rpc('astro_mark_thread_read', { p_student_id: studentId }).catch(() => {});
      } catch (err) {
        clear(threadBox).append(card('Thread', errLine(err)));
      }
    };

    const list = h('div', { class: 'conv-list' });
    if (!convs.length) list.append(emptyState('Nobody has written yet.'));
    for (const c of convs) {
      list.append(h('button', {
        class: 'conv', type: 'button', onclick: () => openThread(c.student_id, c.name),
      },
        h('div', { class: 'conv-name' }, c.name, c.unread ? chip(String(c.unread), 'bad') : null),
        h('div', { class: 'muted small' }, `${c.roll_no} · ${c.class || ''}`),
        h('div', { class: 'conv-last' }, String(c.last_message || '').slice(0, 90))));
    }

    clear(host).append(
      h('div', { class: 'chips' }, chip(`${inbox.unread_total ?? 0} unread from families`, 'strong')),
      h('div', { class: 'split' }, list, threadBox));
  }

  // ------------------------------------------------------------ leaves ----
  async function leavesTab(host) {
    busy(host);
    try {
      const res = await rpc('astro_pending_leaves', { p_limit: 100 });
      const rows = (res.leaves || []).map((l) => [
        l.student, l.roll_no, l.class || '—',
        `${fmtDate(l.from_date)}${l.to_date !== l.from_date ? ` → ${fmtDate(l.to_date)}` : ''}`,
        String(l.days), l.reason || '',
        readOnly ? '' : h('div', { class: 'row end' },
          button('Approve', async () => {
            const note = prompt('Note to the parent (optional)') || null;
            try {
              const r = await rpc('astro_decide_leave', { p_leave_id: l.id, p_approve: true, p_note: note });
              toast(`Approved · ${r.days_marked_leave} day(s) marked leave`);
              leavesTab(host);
            } catch (err) { flashError(err); }
          }, 'btn primary small'),
          button('Decline', async () => {
            const note = prompt('Reason shown to the parent (optional)') || null;
            try {
              await rpc('astro_decide_leave', { p_leave_id: l.id, p_approve: false, p_note: note });
              toast('Declined');
              leavesTab(host);
            } catch (err) { flashError(err); }
          }, 'btn ghost small')),
      ]);
      clear(host).append(card('Waiting for a decision',
        h('p', { class: 'muted small' }, `${rows.length} request(s)`),
        rows.length ? table(['Student', 'Roll', 'Class', 'Dates', 'Days', 'Reason', ''], rows)
          : emptyState('Nothing waiting.')));
    } catch (err) { fail(host, 'Leaves', err); }
  }

  // ---------------------------------------------------------- settings ----
  async function settingsTab(host) {
    busy(host);
    try {
      const [row] = await rest('schools?select=*&limit=1') || [];
      if (!row) return fail(host, 'Settings', new Error('No school row'));
      let holidays = await rest(`school_holidays?${q({
        select: 'holiday_date,reason', order: 'holiday_date.desc', limit: 40,
      })}`) || [];

      const t = (v) => (v ? String(v).slice(0, 5) : '');
      const dayStart = h('input', { type: 'time', value: t(row.day_start) });
      const late = h('input', { type: 'time', value: t(row.late_after) });
      const absent = h('input', { type: 'time', value: t(row.absent_after) });
      const noAbsent = h('input', { type: 'checkbox' });
      noAbsent.checked = !row.absent_after;
      absent.disabled = noAbsent.checked;
      noAbsent.addEventListener('change', () => { absent.disabled = noAbsent.checked; });
      const dayEnd = h('input', { type: 'time', value: t(row.day_end) });
      const tzInput = h('input', { type: 'text', value: row.timezone });
      const alerts = h('input', { type: 'checkbox' });
      alerts.checked = row.alert_emails !== false;
      const offBoxes = [0, 1, 2, 3, 4, 5, 6].map((d) => {
        const cb = h('input', { type: 'checkbox' });
        cb.checked = (row.weekly_off || []).includes(d);
        return { d, cb };
      });
      const status = h('div', { class: 'muted small' });
      const save = button('Save timings', async () => {
        const weekly = offBoxes.filter((x) => x.cb.checked).map((x) => x.d);
        try {
          const r = await rpc('astro_update_settings', {
            p_day_start: dayStart.value || null,
            p_late_after: late.value || null,
            p_absent_after: noAbsent.checked ? null : (absent.value || null),
            p_clear_absent_after: noAbsent.checked,
            p_day_end: dayEnd.value || null,
            p_alert_emails: alerts.checked,
            p_weekly_off: weekly,
            p_timezone: tzInput.value.trim() || null,
          });
          status.textContent = `Saved · version ${r.settings_version}`;
          toast('Settings saved — terminals pick this up on their next heartbeat');
        } catch (err) { flashError(err); status.textContent = err.message; }
      }, 'btn primary');

      const hDate = h('input', { type: 'date', value: todayIn(tz) });
      const hName = h('input', { type: 'text', placeholder: 'Reason (optional)' });
      const hList = h('div', {});
      const drawHolidays = () => {
        clear(hList);
        if (!holidays.length) { hList.append(emptyState('No holidays declared.')); return; }
        hList.append(table(['Date', 'Reason', ''], holidays.map((x) => [
          fmtDate(x.holiday_date), x.reason || '—',
          readOnly || !isAdmin ? '' : button('Remove', async () => {
            try {
              await rpc('astro_remove_holiday', { p_date: x.holiday_date });
              holidays = holidays.filter((y) => y.holiday_date !== x.holiday_date);
              drawHolidays();
              toast('Removed');
            } catch (err) { flashError(err); }
          }, 'btn ghost small'),
        ])));
      };

      clear(host).append(
        card('School timings',
          h('div', { class: 'grid-2' },
            field('Day starts', dayStart), field('Late after', late),
            field('Absent after', absent, 'Arrivals after this count as absent.'),
            field('Day ends', dayEnd, 'The cron marks missing students absent after this time.')),
          field('Timezone', tzInput),
          h('label', { class: 'check' }, noAbsent, ' No automatic absent marking (no cut-off time)'),
          h('div', { class: 'row wrap' }, h('label', { class: 'check' }, alerts, ' Email guardians on absence and late arrival')),
          h('div', { class: 'row wrap' }, h('span', { class: 'field-label' }, 'Weekly off:'),
            ...offBoxes.map(({ d, cb }) => h('label', { class: 'check' },
              cb, ` ${['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][d]}`))),
          readOnly || !isAdmin ? h('p', { class: 'muted small' },
            'Only an administrator can change school timings.') : h('div', { class: 'row end' }, save), status),
        card('Holidays',
          readOnly || !isAdmin ? null : h('div', { class: 'row wrap' }, hDate, hName,
            button('Declare holiday', async () => {
              try {
                await rpc('astro_set_holiday', { p_date: hDate.value, p_name: hName.value || null });
                holidays = await rest(`school_holidays?${q({ select: 'holiday_date,reason', order: 'holiday_date.desc', limit: 40 })}`) || [];
                drawHolidays();
                toast('Holiday declared');
              } catch (err) { flashError(err); }
            }, 'btn small')),
          hList));
      drawHolidays();
    } catch (err) { fail(host, 'Settings', err); }
  }

  // ----------------------------------------------------------- devices ----
  async function devicesTab(host) {
    busy(host);
    try {
      const dh = await rpc('astro_device_health');
      devices = dh.devices || [];
      const events = (await rest(`device_events?${q({
        select: 'event_ts,card_uid,fingerprint_id,method,status,result',
        order: 'received_at.desc', limit: 15,
      })}`)) || [];

      const cardFor = (d) => {
        const out = h('div', { class: 'muted small' });
        const run = async (kind, payload) => {
          out.textContent = 'Sending…';
          try {
            const cmd = await rpc('astro_queue_command', { p_device_code: d.device_code, p_kind: kind, p_payload: payload || {} });
            if (cmd.ok === false) { out.textContent = cmd.reason; return; }
            out.textContent = cmd.device_online === false
              ? `${cmd.hint || 'Terminal offline'} · waiting up to 2 min…`
              : `${kind} sent · waiting…`;
            const done = await pollCommand(cmd.command_id, out);
            out.textContent = done
              ? `${done.status}${done.result ? ` · ${JSON.stringify(done.result).slice(0, 160)}` : ''}`
              : 'No answer — the terminal is offline or the command expired';
          } catch (err) { flashError(err); out.textContent = err.message; }
        };

        const lcdText = h('input', { type: 'text', placeholder: 'LCD text, e.g. HELLO 9A', maxlength: '32' });
        return h('div', { class: 'device' },
          h('div', { class: 'row between' },
            h('div', {},
              h('b', {}, d.name || d.device_code),
              h('div', { class: 'muted small' }, `${d.device_code} · ${d.location || '—'}`)),
            chip(d.online ? 'online' : 'offline', d.online ? 'ok' : 'bad')),
          h('div', { class: 'muted small' },
            `last seen ${d.last_seen ? fmtDateTime(d.last_seen, tz) : 'never'}`,
            ` · ${d.taps_today ?? 0} tap(s) today`,
            ` · firmware ${d.firmware || 'unknown'}`,
            d.wifi_rssi ? ` · RSSI ${d.wifi_rssi} dBm` : '',
            d.pending_commands ? ` · ${d.pending_commands} command(s) queued` : ''),
          readOnly ? null
            : !isAdmin ? h('p', { class: 'muted small' },
              'Only an administrator can send test commands to a terminal.')
            : h('div', { class: 'row wrap' },
            lcdText,
            button('Show on LCD', () => run('lcd_text', { text: lcdText.value }), 'btn ghost small'),
            button('Read a card', () => run('rfid_capture'), 'btn ghost small'),
            button('Check finger', () => run('fp_check'), 'btn ghost small'),
            button('Refresh screens', () => run('refresh'), 'btn ghost small'),
            button('Reboot', () => {
              if (!confirm('Reboot this terminal?')) return;
              run('reboot');
            }, 'btn ghost small danger')),
          out);
      };

      clear(host).append(
        card('Terminals', devices.length ? h('div', { class: 'device-list' }, ...devices.map(cardFor))
          : emptyState('No terminals registered.')),
        card('Recent taps', events.length
          ? table(['When', 'Card', 'Method', 'Result'], events.map((e) => [
            fmtDateTime(e.event_ts, tz),
            e.card_uid || (e.fingerprint_id ? `fp ${e.fingerprint_id}` : '—'),
            e.method || '—',
            chip(e.status || '—', e.status === 'MARKED' ? 'ok' : e.status === 'ALREADY_MARKED' ? 'warn' : 'muted'),
          ]))
          : emptyState('Nothing yet today.')));
    } catch (err) { fail(host, 'Devices', err); }
  }

  // ------------------------------------------------------------ outbox ----
  async function outboxTab(host) {
    busy(host);
    try {
      const stats = await rpc('astro_outbox_stats');
      let filter = 'queued';
      const list = h('div', {});

      const drawList = async () => {
        busy(list, 'Loading queue…');
        try {
          const res = await rpc('astro_outbox_list', { p_status: filter, p_limit: 100 });
          const rows = (res.rows || []).map((r) => [
            fmtDateTime(r.created_at, tz), r.student || '—', r.kind, r.to_email || '—',
            String(r.subject || '').slice(0, 46), chip(r.status, r.status === 'sent' ? 'ok' : r.status === 'failed' ? 'bad' : r.status === 'queued' ? 'warn' : 'muted'),
            String(r.attempts), String(r.last_error || '').slice(0, 40),
            readOnly ? '' : (r.status === 'failed' || r.status === 'skipped')
              ? button('Retry', async () => {
                try {
                  const x = await rpc('astro_requeue_alert', { p_alert_id: r.id });
                  if (x.ok === false) toast(x.hint || x.reason, 'error'); else toast('Queued again');
                  drawList();
                } catch (err) { flashError(err); }
              }, 'btn ghost small')
              : '',
          ]);
          clear(list).append(rows.length
            ? table(['Queued', 'Student', 'Kind', 'To', 'Subject', 'Status', 'Tries', 'Last error', ''], rows)
            : emptyState(`Nothing ${filter}.`));
        } catch (err) {
          clear(list).append(card(null, errLine(err)));
        }
      };

      const chips = h('div', { class: 'chips' });
      const redrawChips = () => {
        for (const k of ['queued', 'sent', 'failed', 'skipped']) {
          chips.append(h('button', {
            class: `chip chip-btn ${filter === k ? 'strong' : ''}`,
            type: 'button',
            onclick: () => { filter = k; clear(chips); redrawChips(); drawList(); },
          }, `${k} ${stats[k] ?? 0}`));
        }
      };

      clear(host).append(
        card('Email queue',
          h('p', { class: 'muted small' },
            `${stats.queued ?? 0} waiting · ${stats.sent ?? 0} sent · ${stats.failed ?? 0} failed`,
            stats.oldest_queued ? ` · oldest waiting since ${fmtDateTime(stats.oldest_queued, tz)}` : ''),
          chips,
          h('p', { class: 'muted small' },
            'Sending needs services/mailer running with a provider key. Until then rows stay queued — nothing is lost.')),
        list);
      redrawChips();
      drawList();
    } catch (err) { fail(host, 'Emails', err); }
  }

  draw();
}

// Queue a terminal command and wait for the device to report back.
async function pollCommand(commandId, statusEl, { timeoutMs = 120000, everyMs = 2500 } = {}) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    try {
      const rows = await rest(`device_commands?${q({ id: `eq.${commandId}`, select: 'id,status,result' })}`);
      const row = rows && rows[0];
      if (row && ['done', 'failed', 'expired', 'cancelled'].includes(row.status)) return row;
      if (statusEl) statusEl.textContent = `waiting · ${row?.status || 'queued'}`;
    } catch {
      /* keep waiting */
    }
    await new Promise((r) => setTimeout(r, everyMs));
  }
  return null;
}
