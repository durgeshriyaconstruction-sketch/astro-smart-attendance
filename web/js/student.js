// Student / guardian screens: calendar, notices, direct messages, leave.
import { rpc, rest, q } from './api.js';
import {
  h, clear, card, chip, button, field, input, emptyState, toast, flashError,
  fmtDate, fmtMonth, fmtTime, monthStart, addMonths, todayIn, statusMeta, table,
} from './ui.js';

const TABS = [
  ['attendance', 'Attendance'],
  ['notices', 'Notices'],
  ['messages', 'Messages'],
  ['leave', 'Leave'],
];

export function renderStudent(root, state) {
  const kids = state.whoami.students || [];
  if (!kids.length) {
    root.append(card('No student linked',
      h('p', {}, 'Your account is signed in but is not linked to a student yet.',
        ' Ask the school office to link your child to ', h('b', {}, state.whoami.user_id), '.')));
    return;
  }

  const tz = state.whoami.school?.timezone;
  let current = kids[0];
  let tab = 'attendance';
  let month = monthStart(todayIn(tz));

  const picker = h('div', { class: 'child-picker' });
  const nav = h('nav', { class: 'tabs' });
  const body = h('main', { class: 'content' });
  root.append(picker, nav, body);

  function drawPicker() {
    clear(picker);
    if (kids.length > 1) {
      const sel = h('select', {
        class: 'child-select',
        onchange: (e) => {
          current = kids.find((k) => k.id === e.target.value) || kids[0];
          drawPicker();
          draw();
        },
      });
      for (const k of kids) {
        const o = h('option', { value: k.id }, `${k.full_name} · ${k.roll_no}`);
        if (k.id === current.id) o.selected = true;
        sel.append(o);
      }
      picker.append(h('span', { class: 'muted small' }, 'Child'), sel);
    } else {
      picker.append(h('div', { class: 'who' },
        h('div', { class: 'who-name' }, current.full_name),
        h('div', { class: 'muted small' },
          `${current.roll_no}${current.class ? ` · ${current.class}` : ''}`)));
    }
  }

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
    const views = { attendance: attendanceTab, notices: noticesTab, messages: messagesTab, leave: leaveTab };
    views[tab](body);
  }

  drawPicker();
  draw();

  // ------------------------------------------------------------ calendar --
  async function attendanceTab(host) {
    clear(host).append(h('p', { class: 'empty' }, 'Loading attendance…'));
    let data;
    try {
      data = await rpc('astro_student_calendar', { p_student_id: current.id, p_month: month });
    } catch (err) {
      clear(host).append(card('Could not load attendance', h('p', { class: 'muted' }, err.message)));
      return;
    }

    const s = data.summary || {};
    const toolbar = h('div', { class: 'row toolbar' },
      button('‹', () => { month = addMonths(month, -1); attendanceTab(host); }, 'btn ghost'),
      h('div', { class: 'month-label' }, fmtMonth(data.month)),
      button('›', () => { month = addMonths(month, 1); attendanceTab(host); }, 'btn ghost'),
      button('This month', () => { month = monthStart(todayIn(tz)); attendanceTab(host); }, 'btn ghost small'));

    const chips = h('div', { class: 'chips' },
      chip(`Present ${s.present ?? 0}`, 'ok'),
      chip(`Late ${s.late ?? 0}`, 'warn'),
      chip(`Absent ${s.absent ?? 0}`, 'bad'),
      chip(`Leave ${s.leave ?? 0}`, 'leave'),
      chip(s.attendance_percent === null || s.attendance_percent === undefined
        ? 'No marked days yet'
        : `${s.attendance_percent}% attendance`, 'strong'));

    const legend = h('div', { class: 'legend' },
      ['present', 'late', 'absent', 'leave', 'holiday', 'weekly_off'].map((k) =>
        h('span', { class: 'legend-item' }, h('i', { class: `dot ${statusMeta(k).cls}` }), statusMeta(k).label)));

    const detail = h('div', { class: 'day-detail muted' }, 'Tap a day to see the time it was marked.');

    const grid = h('div', { class: 'calendar' });
    for (const d of ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']) {
      grid.append(h('div', { class: 'cal-head' }, d));
    }
    const days = data.days || [];
    if (days.length) {
      const firstDow = new Date(`${days[0].date}T00:00:00Z`).getUTCDay();
      for (let i = 0; i < (firstDow + 6) % 7; i++) grid.append(h('div', { class: 'cal-blank' }));
    }
    for (const day of days) {
      const meta = statusMeta(day.status);
      const cell = h('button', {
        class: `cal-day ${meta.cls}`,
        type: 'button',
        title: `${fmtDate(day.date)} · ${meta.label}`,
        onclick: () => {
          clear(detail).className = 'day-detail';
          detail.append(h('b', {}, fmtDate(day.date)), ' · ', meta.label,
            day.time ? ` · marked ${day.time}` : '',
            day.method ? ` (${day.method})` : '',
            day.holiday ? ` · ${day.holiday}` : '');
        },
      },
        h('span', { class: 'cal-num' }, String(Number(day.date.slice(8, 10)))),
        h('i', { class: `dot ${meta.cls}` }),
        day.time ? h('span', { class: 'cal-time' }, day.time) : null);
      grid.append(cell);
    }

    clear(host).append(
      card(null, toolbar, chips, legend),
      h('div', { class: 'card' }, grid, detail));
  }

  // ------------------------------------------------------------- notices --
  async function noticesTab(host) {
    clear(host).append(h('p', { class: 'empty' }, 'Loading notices…'));
    let feed;
    try {
      feed = await rpc('astro_student_feed', { p_student_id: current.id, p_limit: 50 });
    } catch (err) {
      clear(host).append(card('Could not load notices', h('p', { class: 'muted' }, err.message)));
      return;
    }
    const notices = feed.notices || [];
    clear(host);
    if (!notices.length) {
      host.append(card('Notices', emptyState('No notices right now. New ones appear here automatically.')));
      return;
    }
    host.append(card('Notices', h('p', { class: 'muted small' }, `${notices.length} notice(s)`)));
    for (const n of notices) {
      const cls = n.priority === 'critical' ? 'notice-critical'
        : n.priority === 'important' ? 'notice-important' : 'notice-normal';
      host.append(h('article', { class: `notice ${cls}` },
        h('div', { class: 'notice-head' },
          h('h3', {}, n.title),
          n.pinned ? chip('Pinned', 'strong') : null,
          n.priority === 'critical' || n.priority === 'important'
            ? chip(n.priority === 'critical' ? 'Urgent' : 'Important', n.priority === 'critical' ? 'bad' : 'warn')
            : null,
          h('button', {
            class: 'icon-btn', type: 'button', title: 'Remove from my feed',
            onclick: async (e) => {
              e.stopPropagation();
              if (!confirm('Remove this notice from your feed?')) return;
              try {
                await rpc('astro_dismiss_notice', { p_notice_id: n.id });
                toast('Notice removed');
                noticesTab(host);
              } catch (err) { flashError(err); }
            },
          }, '🗑')),
        h('p', { class: 'notice-body' }, n.body),
        h('div', { class: 'muted small' }, fmtDate(n.published_at),
          n.expires_at ? ` · until ${fmtDate(n.expires_at)}` : '')));
    }
  }

  // ------------------------------------------------------------ messages --
  async function messagesTab(host) {
    clear(host).append(h('p', { class: 'empty' }, 'Loading messages…'));
    let feed;
    try {
      feed = await rpc('astro_student_feed', { p_student_id: current.id, p_limit: 100 });
    } catch (err) {
      clear(host).append(card('Could not load messages', h('p', { class: 'muted' }, err.message)));
      return;
    }
    const msgs = (feed.messages || []).slice().reverse(); // oldest first in the thread

    const thread = h('div', { class: 'thread' });
    if (!msgs.length) thread.append(emptyState('No messages yet. Write to the school below.'));
    for (const m of msgs) {
      const mine = m.direction === 'from_student';
      thread.append(h('div', { class: `bubble ${mine ? 'bubble-mine' : 'bubble-school'}` },
        h('div', { class: 'bubble-meta' },
          mine ? 'You' : 'School', ' · ', fmtDateTimeShort(m.created_at, tz),
          !mine && m.read_at ? ' · read' : ''),
        h('div', { class: 'bubble-body' }, m.body),
        h('button', {
          class: 'icon-btn tiny', type: 'button', title: 'Delete message',
          onclick: async () => {
            if (!confirm('Delete this message?')) return;
            try {
              await rpc('astro_delete_message', { p_message_id: m.id });
              toast('Message deleted');
              messagesTab(host);
            } catch (err) { flashError(err); }
          },
        }, '🗑')));
    }

    const textarea = h('textarea', { rows: '3', placeholder: 'Write a message to the school…' });
    const send = button('Send', async () => {
      const body = textarea.value.trim();
      if (!body) return;
      send.disabled = true;
      // Show it straight away; the server call decides whether it stays.
      const placeholder = thread.querySelector('.empty');
      if (placeholder) placeholder.remove();
      const pending = h('div', { class: 'bubble bubble-mine pending' },
        h('div', { class: 'bubble-meta' }, 'You · sending…'),
        h('div', { class: 'bubble-body' }, body));
      thread.append(pending);
      textarea.value = '';
      try {
        await rpc('astro_student_send_message', {
          p_student_id: current.id,
          p_body: body,
          p_client_id: (crypto.randomUUID ? crypto.randomUUID() : String(Date.now())),
        });
        toast('Message sent');
        messagesTab(host);
      } catch (err) {
        pending.remove();
        textarea.value = body;   // hand the text back so nothing is lost
        flashError(err);
      } finally {
        send.disabled = false;
      }
    }, 'btn primary');

    clear(host).append(
      h('div', { class: 'card' }, thread),
      h('div', { class: 'card composer' }, textarea, h('div', { class: 'row end' }, send)));

    if ((feed.unread_messages || 0) > 0) {
      rpc('astro_mark_thread_read', { p_student_id: current.id }).catch(() => {});
    }
  }

  // --------------------------------------------------------------- leave --
  async function leaveTab(host) {
    clear(host).append(h('p', { class: 'empty' }, 'Loading leave requests…'));
    let rows = [];
    try {
      rows = await rest(`leave_requests?${q({
        student_id: `eq.${current.id}`,
        select: 'id,from_date,to_date,reason,status,decision_note,created_at',
        order: 'created_at.desc',
        limit: 20,
      })}`) || [];
    } catch (err) {
      clear(host).append(card('Could not load leave requests', h('p', { class: 'muted' }, err.message)));
      return;
    }

    const from = h('input', { type: 'date', value: todayIn(tz) });
    const to = h('input', { type: 'date', value: todayIn(tz) });
    const reason = h('textarea', { rows: '2', placeholder: 'Reason (optional, e.g. doctor visit)' });
    const submit = button('Request leave', async () => {
      submit.disabled = true;
      try {
        const res = await rpc('astro_request_leave', {
          p_student_id: current.id, p_from: from.value, p_to: to.value, p_reason: reason.value,
        });
        if (res && res.ok === false) {
          toast(res.hint || res.reason || 'Could not request leave', 'error');
        } else {
          toast('Leave requested — the school will review it');
          leaveTab(host);
        }
      } catch (err) {
        flashError(err);
      } finally {
        submit.disabled = false;
      }
    }, 'btn primary');

    const list = h('div', {});
    if (!rows.length) list.append(emptyState('No leave requests yet.'));
    for (const r of rows) {
      list.append(h('div', { class: 'list-row' },
        h('div', {},
          h('b', {}, `${fmtDate(r.from_date)}${r.to_date !== r.from_date ? ` → ${fmtDate(r.to_date)}` : ''}`),
          h('div', { class: 'muted small' }, r.reason || 'No reason given',
            r.decision_note ? ` · ${r.decision_note}` : '')),
        h('div', { class: 'row end' },
          chip(r.status, r.status === 'approved' ? 'ok' : r.status === 'pending' ? 'warn'
            : r.status === 'rejected' ? 'bad' : 'muted'),
          r.status === 'pending' ? button('Cancel', async () => {
            if (!confirm('Cancel this leave request?')) return;
            try {
              await rpc('astro_cancel_leave', { p_leave_id: r.id });
              toast('Cancelled');
              leaveTab(host);
            } catch (err) { flashError(err); }
          }, 'btn ghost small') : null)));
    }

    clear(host).append(
      card('Ask for leave', h('div', { class: 'grid-2' },
        field('From', from), field('To', to)),
      field('Reason', reason), h('div', { class: 'row end' }, submit)),
      card('Your requests', list));
  }
}

function fmtDateTimeShort(iso, tz) {
  try {
    return new Intl.DateTimeFormat('en-GB', {
      timeZone: tz || undefined, day: '2-digit', month: 'short',
      hour: '2-digit', minute: '2-digit', hour12: false,
    }).format(new Date(iso));
  } catch {
    return String(iso).slice(0, 16).replace('T', ' ');
  }
}
