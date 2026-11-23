// Build: src/index.html  →  inline Lucide icons  →  headless Chromium  →  PDF (+ optional PNG previews)
// Usage:  npm install && node build.mjs [--preview]
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import puppeteer from 'puppeteer-core';

const here = path.dirname(fileURLToPath(import.meta.url));
const SRC = path.join(here, 'src', 'index.html');
const BUILT = path.join(here, 'src', '.built.html');
const OUT = path.join(here, 'AttendSure_Creative_Ideation_Worksheet.pdf');
const preview = process.argv.includes('--preview');

// 1 ── inline icons:  {{i:icon-name}}  or  {{i:icon-name:extra-class}}
const iconDir = path.join(here, 'node_modules', 'lucide-static', 'icons');
let html = fs.readFileSync(SRC, 'utf8').replace(/\{\{i:([a-z0-9-]+)(?::([a-z0-9- ]+))?\}\}/g, (_, name, cls) => {
  const f = path.join(iconDir, `${name}.svg`);
  if (!fs.existsSync(f)) throw new Error(`Missing icon: ${name}`);
  return fs.readFileSync(f, 'utf8')
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace('class="lucide', `class="ico ${cls ?? ''} lucide`)
    .replace(/\s(width|height)="24"/g, '');
});
fs.writeFileSync(BUILT, html);

// 2 ── locate a Chromium
async function chromePath() {
  if (process.env.CHROME_PATH) return { exe: process.env.CHROME_PATH, env: process.env, args: [] };
  const chromium = (await import('@sparticuz/chromium')).default;
  const exe = await chromium.executablePath();
  // Debian sandboxes lack NSS; @sparticuz ships it inside al2023.tar.br — unpack once.
  const libDir = '/tmp/al/lib';
  if (!fs.existsSync(path.join(libDir, 'libnss3.so'))) {
    const br = path.join(here, 'node_modules', '@sparticuz', 'chromium', 'bin', 'al2023.tar.br');
    fs.writeFileSync('/tmp/al2023.tar', zlib.brotliDecompressSync(fs.readFileSync(br)));
    fs.mkdirSync('/tmp/al', { recursive: true });
    execSync('tar -xf /tmp/al2023.tar -C /tmp/al');
  }
  return { exe, env: { ...process.env, LD_LIBRARY_PATH: libDir }, args: chromium.args };
}

const { exe, env, args } = await chromePath();
const browser = await puppeteer.launch({ executablePath: exe, env, args: [...args, '--allow-file-access-from-files'], headless: true });
const page = await browser.newPage();
await page.setViewport({ width: 794, height: 1123, deviceScaleFactor: 1 });
await page.goto('file://' + BUILT, { waitUntil: 'networkidle0' });
await page.evaluateHandle('document.fonts.ready');

// 3 ── layout guard: every A4 sheet must contain its content
const problems = await page.evaluate(() => {
  const out = [];
  document.querySelectorAll('.page').forEach((p, i) => {
    const inner = p.querySelector('.inner') || p;
    if (inner.scrollHeight > inner.clientHeight + 1) out.push(`page ${i + 1}: overflow ${inner.scrollHeight - inner.clientHeight}px`);
    // flex children may silently shrink — flag any direct child whose content is clipped
    [...inner.children].forEach((c, k) => {
      if (!c.classList.contains('band') && c.scrollHeight > c.clientHeight + 2 && getComputedStyle(c).overflow !== 'visible')
        out.push(`page ${i + 1}: child #${k + 1} <${c.tagName.toLowerCase()} class="${c.className}"> clipped ${c.scrollHeight - c.clientHeight}px`);
      const r = c.getBoundingClientRect(), ir = inner.getBoundingClientRect();
      const pb = parseFloat(getComputedStyle(inner).paddingBottom);
      if (r.bottom > ir.bottom - pb + 1) out.push(`page ${i + 1}: child #${k + 1} extends ${Math.round(r.bottom - (ir.bottom - pb))}px past margin`);
    });
    // any element whose content exceeds its box while flex-shrunk
    inner.querySelectorAll('.card, figure, .tbl-wrap, .cstage, .risk').forEach(el => {
      if (el.scrollHeight > el.clientHeight + 2) out.push(`page ${i + 1}: .${el.className.split(' ').join('.')} content overflow ${el.scrollHeight - el.clientHeight}px`);
    });
    p.querySelectorAll('[data-fit]').forEach(el => {
      if (el.scrollHeight > el.clientHeight + 1) out.push(`page ${i + 1}: [data-fit=${el.dataset.fit}] overflow ${el.scrollHeight - el.clientHeight}px`);
    });
  });
  return out;
});
if (problems.length) console.warn('⚠ Layout warnings:\n  ' + problems.join('\n  '));
else console.log('✓ All pages fit');

await page.pdf({ path: OUT, format: 'A4', printBackground: true, preferCSSPageSize: true });
console.log('✓ PDF →', path.relative(process.cwd(), OUT));

if (preview) {
  const dir = path.join(here, '.preview');
  fs.mkdirSync(dir, { recursive: true });
  await page.setViewport({ width: 794, height: 1123, deviceScaleFactor: 1.6 });
  const pages = await page.$$('.page');
  for (let i = 0; i < pages.length; i++) await pages[i].screenshot({ path: path.join(dir, `p${String(i + 1).padStart(2, '0')}.png`) });
  console.log(`✓ ${pages.length} previews → .preview/`);
}
await browser.close();
