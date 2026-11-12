/**
 * Email rendering. Plain, table-based HTML with inline styles so it survives
 * Gmail, Outlook and Indian school-payment-era Android clients; plus a text
 * part for everything else. No images, no web fonts, no tracking pixels.
 */

const KIND_LABEL = {
  notice: 'Notice',
  message: 'Message for you',
  absent: 'Absence alert',
  late: 'Late arrival',
  unknown_card: 'Unrecognised card',
  low_attendance: 'Attendance warning',
};

const DEFAULT_SUBJECT = {
  notice: 'School notice',
  message: 'Message from the school',
  absent: 'Absence recorded today',
  late: 'Late arrival recorded today',
  unknown_card: 'Unrecognised card at the gate',
  low_attendance: 'Attendance is below the required level',
};

const ACCENT = {
  notice: '#1d4ed8',
  message: '#0f766e',
  absent: '#b91c1c',
  late: '#b45309',
  unknown_card: '#7c3aed',
  low_attendance: '#b91c1c',
};

function esc(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/** Body text may be multi-line: keep paragraph breaks, collapse the rest. */
function paragraphs(text) {
  return String(text ?? '')
    .replace(/\r\n/g, '\n')
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter(Boolean);
}

export function renderEmail(alert, { schoolName, fromName }) {
  const kind = alert.kind || 'notice';
  const title = (alert.title || alert.subject || DEFAULT_SUBJECT[kind] || 'School update').trim();
  const subject = (alert.subject || alert.title || DEFAULT_SUBJECT[kind] || 'School update')
    .replace(/\s+/g, ' ')
    .trim();
  const label = KIND_LABEL[kind] || 'School update';
  const accent = ACCENT[kind] || '#1d4ed8';
  const bodyParts = paragraphs(alert.body);

  const text = [
    schoolName,
    '',
    title,
    label,
    '',
    ...(bodyParts.length ? bodyParts.flatMap((p) => [p, '']) : ['']),
    '--',
    `Sent by ${schoolName} via Astro Smart Attendance.`,
    'This mailbox is not monitored — please contact the school office for anything urgent.',
  ].join('\n');

  const bodyHtml = bodyParts.length
    ? bodyParts.map((p) => `<p style="margin:0 0 14px;line-height:1.55;">${esc(p).replace(/\n/g, '<br>')}</p>`).join('')
    : '';

  const html = `<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(subject)}</title></head>
<body style="margin:0;padding:0;background:#f1f5f9;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:24px 12px;">
  <tr><td align="center">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#ffffff;border-radius:12px;overflow:hidden;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;">
      <tr><td style="background:${accent};padding:18px 24px;color:#ffffff;">
        <div style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;opacity:.85;">${esc(label)}</div>
        <div style="font-size:16px;font-weight:600;margin-top:6px;">${esc(schoolName)}</div>
      </td></tr>
      <tr><td style="padding:24px;color:#0f172a;font-size:15px;">
        <h1 style="margin:0 0 16px;font-size:19px;line-height:1.35;color:#0f172a;">${esc(title)}</h1>
        ${bodyHtml}
      </td></tr>
      <tr><td style="padding:0 24px 24px;">
        <div style="border-top:1px solid #e2e8f0;padding-top:14px;color:#64748b;font-size:12px;line-height:1.5;">
          Sent by ${esc(schoolName)}${fromName ? ` (${esc(fromName)})` : ''} through Astro Smart Attendance.<br>
          This mailbox is not monitored — please contact the school office for anything urgent.
        </div>
      </td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>`;

  return { subject, html, text };
}
