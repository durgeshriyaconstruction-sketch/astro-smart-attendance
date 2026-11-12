// Small DOM + formatting helpers. Everything is built with createElement and
// text nodes, so a student name or notice body is never parsed as HTML.

export function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k === 'dataset') Object.assign(el.dataset, v);
    else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
    else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2).toLowerCase(), v);
    else if (v === true) el.setAttribute(k, '');
    else el.setAttribute(k, String(v));
  }
  for (const kid of kids.flat(4)) {
    if (kid === null || kid === undefined || kid === false) continue;
    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return el;
}

export const clear = (node) => {
  while (node.firstChild) node.removeChild(node.firstChild);
  return node;
};

export const frag = (...kids) => h('div', { class: 'frag' }, ...kids);

export function button(label, onClick, cls = 'btn') {
  return h('button', { class: cls, type: 'button', onclick: onClick }, label);
}

export function field(labelText, input, hint) {
  return h('label', { class: 'field' }, h('span', { class: 'field-label' }, labelText), input,
    hint ? h('span', { class: 'field-hint' }, hint) : null);
}

export function input(attrs = {}) {
  return h('input', { type: 'text', ...attrs });
}

export function selectEl(options, value, onChange, attrs = {}) {
  const el = h('select', { ...attrs, onchange: (e) => onChange?.(e.target.value) });
  for (const opt of options) {
    const o = h('option', { value: opt.value }, opt.label);
    if (String(opt.value) === String(value ?? '')) o.selected = true;
    el.append(o);
  }
  return el;
}

export function chip(text, cls = '') {
  return h('span', { class: `chip ${cls}`.trim() }, text);
}

export function card(title, ...body) {
  return h('section', { class: 'card' },
    title ? h('h2', { class: 'card-title' }, title) : null,
    ...body);
}

export function emptyState(text) {
  return h('p', { class: 'empty' }, text);
}

export function table(headers, rows, cls = '') {
  return h('div', { class: `table-wrap ${cls}`.trim() },
    h('table', {},
      h('thead', {}, h('tr', {}, headers.map((x) => h('th', {}, x)))),
      h('tbody', {}, rows.map((cells) => h('tr', {},
        cells.map((c) => h('td', {}, c)))))));
}

let toastTimer = null;
export function toast(message, kind = 'info') {
  let box = document.querySelector('.toast');
  if (!box) {
    box = h('div', { class: 'toast', role: 'status' });
    document.body.append(box);
  }
  box.className = `toast toast-${kind} show`;
  clear(box).append(document.createTextNode(String(message)));
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (box.className = 'toast'), kind === 'error' ? 6000 : 3500);
}

export function flashError(err) {
  const detail = err?.detail ? ` — ${err.detail}` : '';
  toast(`${err?.message || err}${detail}`, 'error');
}

// --------------------------------------------------------------- dates ----

export function todayIn(tz) {
  try {
    return new Intl.DateTimeFormat('en-CA', { timeZone: tz || undefined }).format(new Date());
  } catch {
    return new Date().toISOString().slice(0, 10);
  }
}

// Convert what a <input type="datetime-local"> gives us ("2026-11-13T10:00")
// into a real instant, reading those digits as wall-clock time in the school's
// timezone rather than in whatever timezone the browser happens to be set to.
export function zonedToIso(local, tz) {
  if (!local) return null;
  const m = String(local).match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?/);
  if (!m) return null;
  const y = +m[1], mo = +m[2], d = +m[3], hh = +m[4], mm = +m[5], ss = +(m[6] ?? 0);
  const wall = Date.UTC(y, mo - 1, d, hh, mm, ss);
  if (!tz || tz === 'UTC') return new Date(wall).toISOString();
  let ts = wall;
  try {
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
    // Two passes so a DST boundary between the guess and the answer settles.
    for (let i = 0; i < 2; i++) ts = wall - (read(ts) - ts);
  } catch {
    return new Date(wall).toISOString();
  }
  return new Date(ts).toISOString();
}

export function monthStart(iso) {
  return `${(iso || todayIn()).slice(0, 7)}-01`;
}

export function addMonths(iso, delta) {
  const [y, m] = iso.slice(0, 7).split('-').map(Number);
  const d = new Date(Date.UTC(y, m - 1 + delta, 1));
  return d.toISOString().slice(0, 10);
}

export function fmtDate(iso) {
  if (!iso) return '';
  const [y, m, d] = String(iso).slice(0, 10).split('-').map(Number);
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  if (!y || !m || !d) return String(iso);
  return `${d} ${months[m - 1]} ${y}`;
}

export function fmtMonth(iso) {
  const [y, m] = String(iso).slice(0, 7).split('-').map(Number);
  const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
    'August', 'September', 'October', 'November', 'December'];
  return `${months[m - 1]} ${y}`;
}

export function fmtTime(iso, tz) {
  if (!iso) return '';
  try {
    return new Intl.DateTimeFormat('en-GB', {
      timeZone: tz || undefined, hour: '2-digit', minute: '2-digit', hour12: false,
    }).format(new Date(iso));
  } catch {
    return String(iso).slice(11, 16);
  }
}

export function fmtDateTime(iso, tz) {
  if (!iso) return '';
  return `${fmtDate(iso)} ${fmtTime(iso, tz)}`;
}

export const STATUS = {
  present: { label: 'Present', cls: 'ok' },
  late: { label: 'Late', cls: 'warn' },
  absent: { label: 'Absent', cls: 'bad' },
  leave: { label: 'Leave', cls: 'leave' },
  excused: { label: 'Excused', cls: 'leave' },
  half_day: { label: 'Half day', cls: 'warn' },
  left: { label: 'Left early', cls: 'warn' },
  holiday: { label: 'Holiday', cls: 'off' },
  weekly_off: { label: 'Weekly off', cls: 'off' },
  upcoming: { label: 'Upcoming', cls: 'muted' },
  not_marked: { label: 'Not marked', cls: 'muted' },
  not_enrolled: { label: 'Before joining', cls: 'muted' },
  cleared: { label: 'Clear', cls: 'muted' },
};

export const statusMeta = (s) => STATUS[s] || { label: s || 'Unknown', cls: 'muted' };

export const downloadCsv = (filename, rows) => {
  const csv = rows
    .map((r) => r.map((cell) => {
      const v = cell === null || cell === undefined ? '' : String(cell);
      return /[",\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v;
    }).join(','))
    .join('\n');
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
  const a = h('a', { href: url, download: filename });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};
