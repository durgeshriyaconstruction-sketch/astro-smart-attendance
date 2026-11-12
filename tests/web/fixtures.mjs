// Canned Supabase responses. Shapes are copied from the live project
// (2026-11-12) so the dashboard is exercised against the real contract.

export const SCHOOL = {
  id: 'b081c8b6-2374-4484-807c-c4156b3791be',
  name: 'The Aditya Birla Public School, Renukoot',
  code: 'ABPS-RNK',
  timezone: 'Asia/Kolkata',
  day_start: '08:00:00',
  late_after: '08:20:00',
  absent_after: null,
  day_end: '14:00:00',
  alert_emails: true,
  weekly_off: [0],
};

export const STUDENT = {
  id: '95cb2529-0be1-4a43-bc2f-1bab6368a57d',
  roll_no: 'DEMO-01',
  full_name: 'Demo Student',
  class_id: '9c6d7719-e3d7-4015-ae62-364e962baaed',
  guardian_name: 'Demo Parent',
  guardian_email: 'demo.parent@example.com',
  guardian_phone: '9876500000',
  active: true,
  fingerprint_id: null,
};

export const ADMIN_WHOAMI = {
  user_id: 'bbbbbbbb-0000-0000-0000-000000000001',
  role: 'admin',
  school: SCHOOL,
  students: [],
};

export const PARENT_WHOAMI = {
  user_id: 'bbbbbbbb-0000-0000-0000-000000000002',
  role: 'student',
  school: SCHOOL,
  students: [{
    id: STUDENT.id, roll_no: STUDENT.roll_no, full_name: STUDENT.full_name,
    relation: 'guardian', class: '9-A',
  }],
};

export const DAY_OVERVIEW = {
  ok: true,
  date: '2026-11-12',
  is_holiday: false,
  holiday: null,
  is_weekly_off: false,
  counts: { total: 1, present: 1, late: 0, absent: 0, leave: 0, other: 0, not_marked: 0 },
  students: [{
    student_id: STUDENT.id, roll_no: STUDENT.roll_no, name: STUDENT.full_name,
    class: '9-A', status: 'present', time: '08:05', method: 'rfid', note: null,
  }],
};

export const FEED = {
  ok: true,
  student: { id: STUDENT.id, roll_no: STUDENT.roll_no, full_name: STUDENT.full_name },
  class_id: STUDENT.class_id,
  unread_messages: 1,
  count: 2,
  notices: [{
    id: '0df8f757-3cb1-4133-bb8b-fbb4b165eb3d',
    title: 'PTM on Saturday',
    body: 'Parent-teacher meeting this Saturday at 10 AM.\n\nPlease bring the report card.',
    priority: 'critical',
    audience: 'all',
    pinned: true,
    published_at: '2026-11-12T10:50:32.342149+00:00',
    expires_at: null,
    kind: 'notice',
  }],
  messages: [{
    id: 'a30c111d-a951-44f3-bd40-83bf6faba9ac',
    direction: 'to_student',
    subject: 'Your attendance this month',
    body: 'You were late 3 times this month.',
    read_at: null,
    created_at: '2026-11-12T10:50:32.342149+00:00',
    kind: 'message',
  }],
};

const day = (date, status, extra = {}) => ({ date, status, time: null, method: null, holiday: null, ...extra });

export const CALENDAR = {
  ok: true,
  student: { id: STUDENT.id, roll_no: STUDENT.roll_no, full_name: STUDENT.full_name },
  month: '2026-11',
  today: '2026-11-12',
  days: [
    day('2026-11-01', 'weekly_off'),
    day('2026-11-02', 'present', { time: '08:01', method: 'rfid' }),
    day('2026-11-03', 'late', { time: '08:42', method: 'rfid' }),
    day('2026-11-04', 'absent'),
    day('2026-11-05', 'leave'),
    day('2026-11-06', 'present', { time: '07:58', method: 'fingerprint' }),
    day('2026-11-07', 'present', { time: '08:03', method: 'rfid' }),
    day('2026-11-08', 'weekly_off'),
    day('2026-11-09', 'present', { time: '08:00', method: 'rfid' }),
    day('2026-11-10', 'present', { time: '08:02', method: 'rfid' }),
    day('2026-11-11', 'late', { time: '08:31', method: 'rfid' }),
    day('2026-11-12', 'present', { time: '08:05', method: 'rfid' }),
    day('2026-11-13', 'upcoming'),
    day('2026-11-14', 'holiday', { holiday: 'Diwali break' }),
  ],
  summary: {
    present: 6, late: 2, absent: 1, leave: 1, holiday: 1,
    weekly_off: 2, not_marked: 0, attendance_percent: 88.9,
  },
};

export const REPORT = {
  ok: true,
  from: '2026-11-01',
  to: '2026-11-12',
  school_days: 10,
  class_id: null,
  totals: { students: 1, present: 6, late: 2, absent: 1, leave: 1, other: 0 },
  students: [{
    student_id: STUDENT.id, roll_no: STUDENT.roll_no, name: STUDENT.full_name, class: '9-A',
    present: 6, late: 2, absent: 1, leave: 1, other: 0, percent: 88.9,
  }],
};

export const INBOX = {
  ok: true,
  unread_total: 1,
  conversations: [{
    student_id: STUDENT.id, roll_no: STUDENT.roll_no, name: STUDENT.full_name, class: '9-A',
    last_message: 'You were late 3 times this month.', last_direction: 'to_student',
    last_at: '2026-11-12T10:50:32.342149+00:00', unread: 1, total: 1,
  }],
};

export const PENDING_LEAVES = {
  ok: true,
  count: 1,
  leaves: [{
    id: 'e0f5f12e-ee5b-47e6-9ca5-53bb1cf6edb8', student_id: STUDENT.id,
    student: STUDENT.full_name, roll_no: STUDENT.roll_no, class: '9-A',
    from_date: '2026-11-16', to_date: '2026-11-17', days: 2,
    reason: 'Family function', requested_by: null, created_at: '2026-11-12T09:00:00+00:00',
  }],
};

export const DEVICE_HEALTH = {
  ok: true,
  date: '2026-11-12',
  devices: [{
    device_id: '8edbdae8-3957-475b-8f7d-94499c905f99', device_code: 'ASTRO-RNK-01',
    name: 'Main gate terminal', location: 'Main gate', active: true,
    firmware: 'astro-1.0.0', ip: '10.0.0.7', wifi_rssi: -61,
    last_seen: '2026-11-12T11:55:00+00:00', seconds_since_seen: 12, online: true,
    last_boot: null, taps_today: 1, pending_commands: 0,
  }],
};

export const OUTBOX_STATS = {
  queued: 1, sent: 0, failed: 0, skipped: 0, oldest_queued: '2026-11-12T11:48:29+00:00',
};

export const OUTBOX_LIST = {
  ok: true, status: 'queued', count: 1,
  rows: [{
    id: 53, kind: 'absent', student_id: STUDENT.id, roll_no: STUDENT.roll_no,
    student: STUDENT.full_name, to_email: 'demo.parent@example.com',
    subject: 'Absent today: Demo Student (12 Nov)', status: 'queued', attempts: 0,
    last_error: null, created_at: '2026-11-12T11:48:29+00:00', sent_at: null,
    ref_kind: null, ref_id: null,
  }],
};

export const CLASSES = [{
  id: '9c6d7719-e3d7-4015-ae62-364e962baaed', name: '9', section: 'A', teacher: 'Mrs Iyer',
}];

export const DEVICE_EVENTS = [{
  event_ts: '2026-11-12T08:05:00+00:00', card_uid: 'A1B2C3D4', fingerprint_id: null,
  method: 'rfid', status: 'MARKED', result: { status: 'present' },
}];
