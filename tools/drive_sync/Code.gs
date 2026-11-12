/**
 * drive_sync — one Excel sheet per section per day, in Google Drive.
 * Runs on Google's servers; no PC, no chat.
 *
 * LAYOUT (what you asked for):
 *
 *   astro-smart-attendance/
 *   └── 2026/
 *       └── 11/
 *           └── 9/
 *               └── A/
 *                   └── 2026-11-12.xlsx      <- col A: name, col B: Present/Absent
 *
 * One workbook per class + section per day. Year -> month -> class -> section.
 * Each run rewrites that day's file (same name), so a re-run repairs it and
 * never creates a duplicate.
 *
 * SETUP, ONCE:
 *   1. script.google.com -> New project
 *   2. paste this whole file
 *   3. put the secret in CONFIG.SECRET
 *   4. Run -> syncDay -> allow Drive + Sheets access
 *   5. Triggers -> Add trigger -> syncDay, Time-driven, Day timer, 9pm-10pm
 */

var CONFIG = {
  FUNCTION_URL: 'https://nrjchonjlncamfyzmfye.supabase.co/functions/v1/astro-export',

  // 48 hex characters — treat it like a password, it can read every table
  SECRET: 'PASTE_DRIVE_SYNC_SECRET_HERE',

  // the Drive folder "astro-smart-attendance"
  ROOT_FOLDER_ID: '1QAN2ra0HyUsQJpS9m8VXduR5H2b8Uxz8',

  TIMEZONE: 'Asia/Kolkata',

  // '' = today. '2026-11-12' re-does one day on demand.
  DATE: ''
};

// ---------------------------------------------------------------- main -----

/** Writes today's sheet for every class + section. Entry point for the trigger. */
function syncDay() {
  var date = CONFIG.DATE || Utilities.formatDate(new Date(), CONFIG.TIMEZONE, 'yyyy-MM-dd');
  var data = fetchJson(CONFIG.FUNCTION_URL + '?date=' + encodeURIComponent(date) +
                       '&secret=' + encodeURIComponent(CONFIG.SECRET));

  var parts = date.split('-');           // [2026, 11, 12]
  var root = DriveApp.getFolderById(CONFIG.ROOT_FOLDER_ID);
  var yearFolder = ensureFolder(root, parts[0]);
  var monthFolder = ensureFolder(yearFolder, parts[1]);

  var made = [];
  for (var i = 0; i < data.classes.length; i++) {
    var cls = data.classes[i];
    if (!cls.students || cls.students.length === 0) continue;   // no children, no file

    var classFolder = ensureFolder(monthFolder, String(cls.class));
    var sectionFolder = ensureFolder(classFolder, String(cls.section || '-'));

    var fileName = date + '.xlsx';
    var blob = buildSheetBlob(fileName, cls, date);
    writeFile(sectionFolder, fileName, blob);
    made.push(cls.label + ' ' + fileName);
  }

  Logger.log('%s written: %s', date, made.join(', ') || 'nothing (no active students)');
  return made;
}

/** Optional: the day-by-day JSON archive as well. Off unless you trigger it. */
function archiveMonth() {
  var month = CONFIG.DATE
    ? CONFIG.DATE.substring(0, 7)
    : Utilities.formatDate(new Date(), CONFIG.TIMEZONE, 'yyyy-MM');
  var data = fetchJson(CONFIG.FUNCTION_URL + '?month=' + encodeURIComponent(month) +
                       '&secret=' + encodeURIComponent(CONFIG.SECRET));
  var parts = month.split('-');
  var root = DriveApp.getFolderById(CONFIG.ROOT_FOLDER_ID);
  var folder = ensureFolder(ensureFolder(root, parts[0]), parts[1]);
  for (var i = 0; i < data.days.length; i++) {
    var d = data.days[i];
    writeFile(folder, d.date + '.json', Utilities.newBlob(JSON.stringify(d.data, null, 2), 'application/json'));
  }
  Logger.log('%s: %s day files', month, data.days.length);
}

/** Health check: proves URL + secret, writes nothing. */
function ping() {
  var res = UrlFetchApp.fetch(CONFIG.FUNCTION_URL + '?ping=1&secret=' +
                              encodeURIComponent(CONFIG.SECRET), { muteHttpExceptions: true });
  Logger.log('%s %s', res.getResponseCode(), res.getContentText());
}

// -------------------------------------------------------------- helpers ----

function fetchJson(url) {
  var res = UrlFetchApp.fetch(url, { muteHttpExceptions: true, followRedirects: true });
  if (res.getResponseCode() !== 200) {
    throw new Error('astro-export returned ' + res.getResponseCode() + ': ' + res.getContentText());
  }
  var data = JSON.parse(res.getContentText());
  if (!data || !data.classes) throw new Error('unexpected export: ' + res.getContentText().substring(0, 200));
  return data;
}

/**
 * Builds a real .xlsx: column A name, column B Present/Absent, with the date and
 * class-section on the first row so a printed page still says what it is.
 *
 * Google Sheets has no "save as xlsx" call, so: build a temporary Sheet, export
 * it through Google's own converter, throw the Sheet away.
 */
function buildSheetBlob(fileName, cls, date) {
  var name = 'tmp ' + cls.label + ' ' + date + ' ' + Date.now();
  var ss = SpreadsheetApp.create(name);
  var sh = ss.getActiveSheet();
  sh.setName(cls.label + ' ' + date);

  sh.getRange(1, 1).setValue(cls.label + '  —  ' + date)
    .setFontWeight('bold').setFontSize(12);
  sh.getRange(2, 1, 1, 2).setValues([['Name', 'Status']]).setFontWeight('bold');
  sh.setFrozenRows(2);

  var rows = [];
  for (var i = 0; i < cls.students.length; i++) {
    var s = cls.students[i];
    rows.push([s.name, s.status]);            // col A name, col B Present/Absent
  }
  if (rows.length) sh.getRange(3, 1, rows.length, 2).setValues(rows);

  sh.setColumnWidth(1, 260);
  sh.setColumnWidth(2, 110);
  sh.getRange(3, 2, Math.max(rows.length, 1), 1).setHorizontalAlignment('center');

  SpreadsheetApp.flush();

  var url = 'https://docs.google.com/spreadsheets/d/' + ss.getId() + '/export?format=xlsx';
  var res = UrlFetchApp.fetch(url, {
    headers: { Authorization: 'Bearer ' + ScriptApp.getOAuthToken() },
    muteHttpExceptions: true
  });
  if (res.getResponseCode() !== 200) {
    throw new Error('xlsx export failed (' + res.getResponseCode() + ')');
  }
  var blob = res.getBlob().setName(fileName).setContentType(
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');

  DriveApp.getFileById(ss.getId()).setTrashed(true);   // the temp Sheet is not needed
  return blob;
}

function ensureFolder(parent, name) {
  var it = parent.getFoldersByName(name);
  return it.hasNext() ? it.next() : parent.createFolder(name);
}

/**
 * One file per name: any file already carrying that name is moved to the bin and
 * a fresh one is created. Trashing first is deliberate — writing binary content
 * into an existing blob corrupts it, and this way there is never a duplicate
 * "2026-11-12 (1).xlsx" cluttering the folder.
 */
function writeFile(folder, name, blobOrText) {
  var blob = (typeof blobOrText === 'string') ? Utilities.newBlob(blobOrText) : blobOrText;
  var it = folder.getFilesByName(name);
  while (it.hasNext()) it.next().setTrashed(true);
  folder.createFile(blob);
}
