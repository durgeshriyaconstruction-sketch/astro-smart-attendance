// Starts a headless browser for the tests in this folder: the bundled Chromium
// first, then any Chrome already installed on the machine. CHROME_PATH, when
// set, is tried before both.
import fs from 'node:fs';

process.env.AWS_LAMBDA_JS_RUNTIME ??= 'nodejs22.x';      // must be set before the import below
const { default: chromium } = await import('@sparticuz/chromium');
const { default: puppeteer } = await import('puppeteer-core');

export async function launchBrowser(extraArgs = []) {
  const plain = ['--no-sandbox', '--disable-dev-shm-usage', ...extraArgs];
  const tries = [];
  if (process.env.CHROME_PATH) tries.push(() => ({ executablePath: process.env.CHROME_PATH, headless: true, args: plain }));
  tries.push(async () => ({ executablePath: await chromium.executablePath(), headless: 'shell', args: [...chromium.args, ...plain] }));
  for (const p of ['/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/usr/bin/chromium-browser', '/usr/bin/chromium']) {
    if (fs.existsSync(p)) tries.push(() => ({ executablePath: p, headless: true, args: plain }));
  }
  let last;
  for (const t of tries) {
    try { return await puppeteer.launch(await t()); } catch (e) { last = e; }
  }
  throw last;
}

// On GitHub the line becomes a note on the run page; elsewhere it is plain text.
export function report(level, text) {
  if (process.env.GITHUB_ACTIONS) console.log('::' + level + '::' + String(text).replace(/%/g, '%25').replace(/\r/g, '').replace(/\n/g, '%0A'));
  else console.log((level === 'error' ? 'FAIL: ' : 'OK: ') + text);
}
