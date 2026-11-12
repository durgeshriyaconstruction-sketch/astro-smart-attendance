#!/usr/bin/env node
/**
 * Astro Smart Attendance — outbox mailer.
 *
 * Every admin action that needs to reach a family writes a row into
 * public.alerts (status 'queued'): attendance alerts, notices, and direct
 * messages. Nothing in the database sends email. This worker drains that queue.
 *
 *   POST /rest/v1/rpc/astro_claim_emails   queued -> sending (attempts + 1)
 *   provider send
 *   POST /rest/v1/rpc/astro_finish_email   sending -> sent | failed
 *
 * It talks to PostgREST with the secret key, so it must run somewhere trusted —
 * your laptop, a Raspberry Pi, or a small always-on server. Never ship the
 * secret key to the ESP32 or to a browser.
 *
 *   node index.mjs            # loop forever, poll every INTERVAL_MS
 *   node index.mjs --once     # single pass, then exit (good for cron)
 *   node index.mjs --check    # validate config and print queue depth
 */

import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { createProvider } from './providers.mjs';
import { createRpc } from './postgrest.mjs';
import { runPass, shortError } from './worker.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));

// ---------------------------------------------------------------- .env ------

/** Minimal .env reader: no dependency, no surprises, never overrides real env. */
function loadEnv() {
  for (const file of [join(HERE, '.env'), join(HERE, '.env.local')]) {
    if (!existsSync(file)) continue;
    for (const raw of readFileSync(file, 'utf8').split('\n')) {
      const line = raw.trim();
      if (!line || line.startsWith('#')) continue;
      const eq = line.indexOf('=');
      if (eq < 0) continue;
      const key = line.slice(0, eq).trim();
      let value = line.slice(eq + 1).trim();
      if (
        (value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))
      ) {
        value = value.slice(1, -1);
      }
      if (!(key in process.env)) process.env[key] = value;
    }
  }
}

loadEnv();

// ---------------------------------------------------------------- config ----

const cfg = {
  supabaseUrl: (process.env.SUPABASE_URL || '').replace(/\/+$/, ''),
  secretKey: process.env.SUPABASE_SECRET_KEY || '',
  provider: (process.env.MAIL_PROVIDER || 'resend').toLowerCase(),
  from: process.env.MAIL_FROM || '',
  fromName: process.env.MAIL_FROM_NAME || 'School Office',
  replyTo: process.env.MAIL_REPLY_TO || '',
  schoolName: process.env.SCHOOL_NAME || 'School',
  batch: Number(process.env.BATCH_SIZE || 20),
  intervalMs: Number(process.env.INTERVAL_MS || 30000),
  resendKey: process.env.RESEND_API_KEY || '',
  smtp: {
    host: process.env.SMTP_HOST || '',
    port: Number(process.env.SMTP_PORT || 465),
    secure: (process.env.SMTP_SECURE || 'true') !== 'false',
    user: process.env.SMTP_USER || '',
    pass: process.env.SMTP_PASS || '',
  },
};

function validateConfig() {
  const problems = [];
  const isLocal = /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(cfg.supabaseUrl);
  if (!/^https:\/\/[a-z0-9-]+\.supabase\.co$/.test(cfg.supabaseUrl) && !isLocal) {
    problems.push('SUPABASE_URL must be https://<project-ref>.supabase.co');
  }
  if (!cfg.secretKey) {
    problems.push('SUPABASE_SECRET_KEY is missing (Project Settings > API > secret key)');
  } else if (/^(eyJ|sb_publishable_)/.test(cfg.secretKey)) {
    problems.push(
      'SUPABASE_SECRET_KEY looks like a publishable/anon key — the worker needs the secret key'
    );
  }
  if (!cfg.from) problems.push('MAIL_FROM is missing (e.g. "Notices <notices@yourschool.in>")');
  if (!['resend', 'smtp', 'console'].includes(cfg.provider)) {
    problems.push(`MAIL_PROVIDER must be resend | smtp | console (got "${cfg.provider}")`);
  }
  if (cfg.provider === 'resend' && !cfg.resendKey) {
    problems.push('RESEND_API_KEY is missing for MAIL_PROVIDER=resend');
  }
  if (cfg.provider === 'smtp') {
    if (!cfg.smtp.host) problems.push('SMTP_HOST is missing for MAIL_PROVIDER=smtp');
    if (!cfg.smtp.user || !cfg.smtp.pass) problems.push('SMTP_USER / SMTP_PASS are missing');
  }
  return problems;
}

// ---------------------------------------------------------------- postgrest -

const rpc = createRpc({ url: cfg.supabaseUrl, key: cfg.secretKey });

const claimEmails = (limit) => rpc('astro_claim_emails', { p_limit: limit });
const finishEmail = (id, ok, error) =>
  rpc('astro_finish_email', { p_id: id, p_ok: ok, p_error: error || null });
const releaseStale = (minutes) => rpc('astro_release_stale_sending', { p_minutes: minutes });
const outboxStats = () => rpc('astro_outbox_stats');

// ---------------------------------------------------------------- helpers ---

const now = () => new Date().toISOString().slice(11, 19);
const log = (...a) => console.log(now(), ...a);
const warn = (...a) => console.warn(now(), ...a);

async function main() {
  const mode = process.argv.includes('--check')
    ? 'check'
    : process.argv.includes('--once')
      ? 'once'
      : 'loop';

  const problems = validateConfig();
  if (problems.length) {
    console.error('\nConfiguration problem(s):');
    for (const p of problems) console.error(`  - ${p}`);
    console.error('\nCopy .env.example to .env and fill it in. See README.md.\n');
    process.exit(1);
  }

  if (mode === 'check') {
    log(`config ok — provider=${cfg.provider} from="${cfg.from}" url=${cfg.supabaseUrl}`);
    try {
      const stats = await outboxStats();
      log(`queue: ${JSON.stringify(stats)}`);
    } catch (err) {
      warn(
        `could not read the queue from ${cfg.supabaseUrl}: ${shortError(err)}\n` +
          '  - is the project URL right, and is this machine online?'
      );
      process.exitCode = 2;
    }
    return;
  }

  const provider = await createProvider({
    provider: cfg.provider,
    from: cfg.from,
    fromName: cfg.fromName,
    replyTo: cfg.replyTo,
    resendKey: cfg.resendKey,
    smtp: cfg.smtp,
  });
  log(`mailer up — provider=${cfg.provider} from="${cfg.from}"`);

  const options = {
    batch: cfg.batch,
    schoolName: cfg.schoolName,
    fromName: cfg.fromName,
    delayMs: Number(process.env.SEND_DELAY_MS || 0),
    log,
    warn,
  };

  if (mode === 'once') {
    await releaseStale(15);
    const res = await runPass({ claim: claimEmails, finish: finishEmail, provider, options });
    log(
      res.claimed === 0
        ? 'queue empty'
        : `pass done — sent ${res.sent}, failed ${res.failed}, claimed ${res.claimed}`
    );
    return;
  }

  let stopping = false;
  for (const sig of ['SIGINT', 'SIGTERM']) {
    process.on(sig, () => {
      stopping = true;
      log('shutting down after this pass');
    });
  }

  let passes = 0;
  while (!stopping) {
    try {
      if (passes % 10 === 0) await releaseStale(15);
      const res = await runPass({ claim: claimEmails, finish: finishEmail, provider, options });
      if (res.claimed === 0) await new Promise((r) => setTimeout(r, cfg.intervalMs));
    } catch (err) {
      warn(`pass failed: ${shortError(err)}`);
      await new Promise((r) => setTimeout(r, Math.max(cfg.intervalMs, 60000)));
    }
    passes += 1;
  }
  log('stopped');
}

main().catch((err) => {
  console.error(err?.stack || String(err));
  process.exit(1);
});
