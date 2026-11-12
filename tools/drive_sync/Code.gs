/**
 * drive_sync — keeps the school's records folder in Google Drive up to date,
 * with no PC and no chat involved.
 *
 * WHERE THIS RUNS: script.google.com (Google's servers). You paste this file
 * there once, press Run once to authorise it, then add a daily trigger. From
 * then on Google pulls the month from Supabase and rewrites the files.
 *
 * WHAT IT WRITES (same shape as tools/archive and the earlier backups):
 *
 *   astro-smart-attendance/            <- ROOT_FOLDER_ID
 *   ├── index.json
 *   ├── YYYY/
 *   │   └── MM/
 *   │       ├── YYYY-MM-DD.json        attendance, notices, messages, e-mails, leave
 *   │       ├── YYYY-MM-DD.csv         the attendance sheet, opens in Excel
 *   │       └── month-summary.json     per-student present / late / absent / leave
 *
 * SETUP, ONCE:
 *   1. script.google.com -> New project
 *   2. replace Code.gs with this file
 *   3. paste your secret into CONFIG.SECRET (Supabase -> Edge Functions -> Secrets
 *      -> DRIVE_SYNC_SECRET; if it is not there, tell the assistant to set it)
 *   4. Run -> syncMonth -> "Review permissions" -> Allow
 *      (it needs Drive access; it never touches Gmail)
 *   5. Triggers (clock icon) -> Add trigger -> syncMonth, Time-driven,
 *      Day timer, 9pm to 10pm. Save.
 *
 * A failed run sends you an e-mail from Apps Script; check Executions for the
 * error text.
 */

var CONFIG = {
  // your project, it never changes
  FUNCTION_URL: 'https://nrjchonjlncamfyzmfye.supabase.co/functions/v1/astro-export',

  // 48 hex characters. Treat it like a password: it can read every table.
  SECRET: 'PASTE_DRIVE_SYNC_SECRET_HERE',

  // the folder in Drive called "astro-smart-attendance"
  ROOT_FOLDER_ID: '1QAN2ra0HyUsQJpS9m8VXduR5H2b8Uxz8',

  TIMEZONE: 'Asia/Kolkata',

  // '' = current month. '2026-11' re-does one month on demand.
  MONTH: ''
};

/** Entry point. Called by the daily trigger, or by hand. */
function syncMonth() {
  var month = CONFIG.MONTH || Utilities.formatDate(new Date(), CONFIG.TIMEZONE, 'yyyy-MM');
  var data = fetchMonth(month);

  var parts = month.split('-');
  var root = DriveApp.getFolderById(CONFIG.ROOT_FOLDER_ID);
  var yearFolder = ensureFolder(root, parts[0]);
  var monthFolder = ensureFolder(yearFolder, parts[1]);

  var written = 0;
  for (var i = 0; i < data.days.length; i++) {
    var day = data.days[i];
    writeFile(monthFolder, day.date + '.json', JSON.stringify(day.data, null, 2), 'application/json');
    writeFile(monthFolder, day.date + '.csv', toCsv(day.data), 'text/csv');
    written += 2;
  }

  writeFile(monthFolder, 'month-summary.json', JSON.stringify(data.summary, null, 2), 'application/json');
  writeFile(root, 'index.json', JSON.stringify(buildIndex(data), null, 2), 'application/json');

  Logger.log('%s: %s days, %s files written/updated', month, data.days.length, written + 2);
  return written + 2;
}

/** Health check: proves the URL + secret work without writing anything. */
function ping() {
  var res = UrlFetchApp.fetch(CONFIG.FUNCTION_URL + '?ping=1&secret=' + encodeURIComponent(CONFIG.SECRET),
                              { muteHttpExceptions: true });
  Logger.log('%s %s', res.getResponseCode(), res.getContentText());
}

function fetchMonth(month) {
  var url = CONFIG.FUNCTION_URL + '?month=' + encodeURIComponent(month) +
            '&secret=' + encodeURIComponent(CONFIG.SECRET);
  var res = UrlFetchApp.fetch(url, { muteHttpExceptions: true, followRedirects: true });
  var code = res.getResponseCode();
  var body = res.getContentText();
  if (code !== 200) {
    throw new Error('astro-export returned ' + code + ': ' + body);
  }
  var data = JSON.parse(body);
  if (!data || !data.days) {
    throw new Error('astro-export returned something unexpected: ' + body.substring(0, 200));
  }
  return data;
}

/** Folder by name under `parent`, created if missing. */
function ensureFolder(parent, name) {
  var it = parent.getFoldersByName(name);
  return it.hasNext() ? it.next() : parent.createFolder(name);
}

/** File by name in `folder`: overwritten if it exists, created if not. */
function writeFile(folder, name, text, mime) {
  var it = folder.getFilesByName(name);
  if (it.hasNext()) {
    var file = it.next();
    file.setContent(text);
    if (mime && file.getMimeType() !== mime) {
      // Drive cannot change a blob's type in place; replace it.
      file.setTrashed(true);
      folder.createFile(name, text, mime);
    }
    return;
  }
  folder.createFile(name, text, mime);
}

/** attendance sheet as CSV — one row per student per session/period. */
function toCsv(day) {
  var cols = ['roll_no', 'name', 'status', 'method', 'session', 'period_no', 'marked_at', 'note'];
  var lines = [cols.join(',')];
  var rows = day.attendance || [];
  for (var i = 0; i < rows.length; i++) {
    var cells = [];
    for (var c = 0; c < cols.length; c++) {
      var v = rows[i][cols[c]];
      v = (v === null || v === undefined) ? '' : String(v);
      if (v.indexOf(',') >= 0 || v.indexOf('"') >= 0 || v.indexOf('\n') >= 0) {
        v = '"' + v.replace(/"/g, '""') + '"';
      }
      cells.push(v);
    }
    lines.push(cells.join(','));
  }
  return lines.join('\r\n') + '\r\n';
}

/** index.json — what is in the archive, day by day. */
function buildIndex(data) {
  var days = [];
  var totals = { attendance: 0, notices: 0, messages: 0, emails: 0, leave_requests: 0 };
  for (var i = 0; i < data.days.length; i++) {
    var d = data.days[i];
    days.push({
      date: d.date,
      file: d.file,
      counts: d.counts
    });
    for (var k in totals) {
      totals[k] += (d.counts && d.counts[k]) || 0;
    }
  }
  return {
    school: data.school,
    from: data.from,
    to: data.to,
    generated_at: data.generated_at,
    generated_by: 'Google Apps Script tools/drive_sync (astro-export -> astro_drive_month)',
    layout: 'YYYY/MM/YYYY-MM-DD.json — attendance, notices, messages, e-mails, leave for that day',
    days: days,
    totals: totals
  };
}
