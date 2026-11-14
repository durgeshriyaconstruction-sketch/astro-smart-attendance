// Opens the PUBLISHED website in a real (headless) browser and checks that it
// works against the real Supabase project:
//
//   1. the page is the Supabase-connected edition (supabase-bridge.js loaded),
//   2. Supabase answers this browser (sign-in endpoint, CORS, public key),
//   3. when the sign-in page still offers "Fill Admin": an admin signs in, the
//      dashboard loads its data from the database, and sign-out works.
//
// It is read-only: nothing is added, changed or deleted. It never prints
// passwords or tokens, only request paths and status codes.
//
//   cd tools/e2e && npm install
//   SITE_URL=https://astro-smart-attendence.web.app node live_check.mjs
//
// FAKE_SUPABASE=1 answers *.supabase.co from fake_supabase.mjs instead, so the
// script itself can be tried where Supabase is not reachable.
import { launchBrowser, report as say } from './browser.mjs';

const SITE = (process.env.SITE_URL || 'https://astro-smart-attendence.web.app').replace(/\/+$/, '');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let browser;
try { browser = await launchBrowser(); } catch (e) {
  say('error', 'Live check could not start a browser: ' + String((e && e.message) || e).slice(0, 500));
  process.exit(1);
}
const page = await browser.newPage();
await page.setViewport({ width: 1280, height: 860 });

const cloud = [];          // every call the page made to Supabase: "POST /auth/v1/token -> 200"
const hostApi = [];        // /api/... requests that reached the web host (there must be none)
const pageErrors = [];
const isCloud = (u) => u.hostname.endsWith('supabase.co');
page.on('pageerror', (e) => pageErrors.push(String(e.message || e).slice(0, 200)));
page.on('response', (res) => {
  const u = new URL(res.url());
  if (isCloud(u) && res.request().method() !== 'OPTIONS') cloud.push(res.request().method() + ' ' + u.pathname + ' -> ' + res.status());
});
page.on('requestfailed', (req) => {
  const u = new URL(req.url());
  if (isCloud(u)) cloud.push(req.method() + ' ' + u.pathname + ' -> FAILED ' + ((req.failure() || {}).errorText || ''));
});

if (process.env.FAKE_SUPABASE) {
  const { createFake } = await import('./fake_supabase.mjs');
  const fake = createFake();
  await page.setRequestInterception(true);
  page.on('request', (req) => {
    const u = new URL(req.url());
    if (!isCloud(u)) return req.continue();
    const cors = { 'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': '*' };
    if (req.method() === 'OPTIONS') return req.respond({ status: 204, headers: cors });
    const r = fake.handle(req.method(), req.url(), req.headers(), req.postData());
    req.respond({ status: r.status, headers: { ...cors, 'content-type': 'application/json' }, body: r.body == null ? '' : JSON.stringify(r.body) });
  });
}
page.on('request', (req) => {
  const u = new URL(req.url());
  if (u.origin === SITE && (u.pathname.startsWith('/api/') || u.pathname === '/addStudent' || u.pathname === '/login')) hostApi.push(req.method() + ' ' + u.pathname);
});

const ev = (fn, ...a) => page.evaluate(fn, ...a);
const until = async (fn, ms, ...a) => {
  const end = Date.now() + ms;
  for (;;) {
    const v = await ev(fn, ...a).catch(() => false);
    if (v || Date.now() > end) return v;
    await sleep(250);
  }
};
class Problem extends Error {}
const need = (cond, text) => { if (!cond) throw new Problem(text); };

let code = 0;
try {
  const first = await page.goto(SITE + '/', { waitUntil: 'domcontentloaded', timeout: 45000 });
  need(first && first.ok(), SITE + ' answered HTTP ' + (first ? first.status() : 'nothing') + '.');
  need(await ev(() => typeof window.AstroWeb === 'object'),
    'The published page is not the Supabase-connected edition: supabase-bridge.js did not load.');
  need(await until(() => document.querySelector('#login') && document.querySelector('#login').classList.contains('on'), 15000),
    'The sign-in screen never appeared.');
  const version = await ev(() => document.title);

  // Sign in the way a person would. "Fill Admin" types the login the page itself
  // advertises; without it we knock with a login that cannot exist, which still
  // shows whether Supabase answers this browser.
  const canFill = await ev(() => Array.from(document.querySelectorAll('#login a')).some((a) => /Fill Admin/i.test(a.textContent)));
  if (canFill) {
    await ev(() => Array.from(document.querySelectorAll('#login a')).find((a) => /Fill Admin/i.test(a.textContent)).click());
  } else {
    await ev(() => {
      const set = (sel, v) => { const el = document.querySelector(sel); el.value = v; el.dispatchEvent(new Event('input', { bubbles: true })); };
      set('#login-id', 'live-check@astro-check.invalid'); set('#login-pw', 'not-a-real-password');
    });
  }
  await sleep(300);
  await page.click('#login-btn');

  const loginError = () => ev(() => { const e = document.querySelector('#login-err'); return e && !e.classList.contains('hidden') ? e.textContent.trim() : ''; });
  const end = Date.now() + 40000;
  let signedIn = false, refused = '';
  while (Date.now() < end) {
    signedIn = await ev(() => !document.querySelector('#login').classList.contains('on') && window.AstroWeb.state().signedIn).catch(() => false);
    if (signedIn) break;
    refused = await loginError().catch(() => '');
    if (refused) break;
    await sleep(250);
  }
  const answered = cloud.find((c) => /\/auth\/v1\/token -> \d/.test(c));
  need(answered, 'Supabase did not answer the browser\'s sign-in request' + (refused ? ' (the page said: "' + refused + '")' : '') + '.');

  if (!signedIn) {
    need(refused, 'Sign-in neither finished nor showed an error within 40 seconds.');
    need(/-> 400$/.test(answered), 'Sign-in failed: "' + refused + '"');
    say('notice', 'Live check (' + version + '): the site reaches Supabase from a real browser. ' +
      (canFill ? 'The admin login printed on the sign-in page was refused ("' + refused + '"), so that password no longer works'
               : 'The sign-in page no longer prints an admin login') +
      '; the dashboard behind the login was not checked.');
  } else {
    const loaded = await until(() => fetch('/api/students').then((r) => r.json()).then((j) => (j && j.ok && Array.isArray(j.items)) ? { n: j.items.length } : false, () => false), 25000);
    need(loaded, 'Signed in, but the dashboard could not load students from Supabase.');
    const state = await ev(() => window.AstroWeb.state());
    need(!state.error, 'Signed in, but the cloud connection reports: ' + state.error);
    need(cloud.some((c) => /\/rest\/v1\/rpc\/astro_web_bundle -> 200$/.test(c)), 'Signed in, but the dashboard data call did not succeed.');

    await ev(() => window.logout());                       // opens the app's "Sign out?" dialog
    need(await until(() => { const b = Array.from(document.querySelectorAll('#modals button')).find((x) => /Sign out/.test(x.textContent)); if (b) b.click(); return !!b; }, 5000),
      'The sign-out dialog did not open.');
    need(await until(() => document.querySelector('#login').classList.contains('on'), 10000), 'Sign-out did not return to the sign-in screen.');
    // the bridge ends the Supabase session a few seconds after the app signs out
    need(await until(() => !localStorage.getItem('astro.cloud.session.v1'), 25000), 'Signed out, but the Supabase session was kept in the browser.');
    const end2 = Date.now() + 10000;
    while (Date.now() < end2 && !cloud.some((c) => /\/auth\/v1\/logout -> /.test(c))) await sleep(250);
    need(cloud.some((c) => /\/auth\/v1\/logout -> 2\d\d$/.test(c)), 'Signed out, but Supabase did not confirm the end of the session.');
    say('notice', 'Live check (' + version + '): signed in on ' + SITE + ' as admin from a real browser, the dashboard loaded ' +
      loaded.n + ' student' + (loaded.n === 1 ? '' : 's') + ' from Supabase, and sign-out worked.');
  }
  need(hostApi.length === 0, 'The page asked the web host for data instead of Supabase: ' + hostApi.slice(0, 4).join(', '));
  need(pageErrors.length === 0, 'Script errors on the page: ' + pageErrors.slice(0, 3).join(' | '));
} catch (e) {
  code = 1;
  const where = await ev(() => ({ cloud: (document.querySelector('#sys-cloud') || {}).textContent || '', err: (document.querySelector('#login-err') || {}).textContent || '' })).catch(() => ({}));
  say('error', 'Live check failed: ' + (e instanceof Problem ? e.message : String((e && e.stack) || e).slice(0, 600)) +
    '\nCalls to Supabase: ' + (cloud.length ? cloud.slice(0, 12).join('; ') : 'none') +
    '\nPage: ' + JSON.stringify(where) + (pageErrors.length ? '\nScript errors: ' + pageErrors.slice(0, 3).join(' | ') : ''));
}
console.log('Calls to Supabase: ' + (cloud.join('; ') || 'none'));
await browser.close();
process.exit(code);
