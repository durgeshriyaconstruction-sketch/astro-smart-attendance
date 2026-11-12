/**
 * The pass loop, extracted from the CLI so it can be tested without a network,
 * a database, or a mail provider.
 *
 * A pass is: claim up to N rows, send each one, record the outcome. The claim
 * RPC already flipped them to 'sending', so every claimed row must end sent or
 * failed — except when the provider rejects the request outright (bad key, bad
 * sender), which is not row-specific. Then we stop and leave the rest claimed;
 * astro_release_stale_sending() puts them back after 15 minutes instead of
 * burning an attempt per row.
 */

import { FatalProviderError } from './providers.mjs';
import { renderEmail } from './template.mjs';

export function shortError(err) {
  const msg = err?.message || String(err);
  return msg.length > 480 ? `${msg.slice(0, 477)}...` : msg;
}

/**
 * @param {object} deps
 * @param {(limit:number)=>Promise<Array>} deps.claim
 * @param {(id:number, ok:boolean, error?:string)=>Promise<object>} deps.finish
 * @param {{send:Function}} deps.provider
 * @param {object} deps.options  { batch, schoolName, fromName, delayMs, log, warn }
 * @returns {Promise<{claimed:number, sent:number, failed:number}>}
 */
export async function runPass({ claim, finish, provider, options = {} }) {
  const {
    batch = 20,
    schoolName = 'School',
    fromName = 'School Office',
    delayMs = 0,
    log = () => {},
    warn = () => {},
  } = options;

  const rows = (await claim(batch)) || [];
  const result = { claimed: rows.length, sent: 0, failed: 0 };
  if (rows.length === 0) return result;

  log(`claimed ${rows.length} email(s)`);

  for (const alert of rows) {
    const mail = renderEmail(alert, { schoolName, fromName });

    try {
      await provider.send({ to: alert.to_email, ...mail });
    } catch (err) {
      if (err instanceof FatalProviderError) {
        warn(`provider rejected the request, stopping this pass: ${err.message}`);
        result.stopped = true;
        throw err;
      }
      result.failed += 1;
      const message = shortError(err);
      warn(`failed  ${alert.kind}#${alert.id} -> ${alert.to_email} — ${message}`);
      await finish(alert.id, false, message);
      continue;
    }

    result.sent += 1;
    log(`sent    ${alert.kind}#${alert.id} -> ${alert.to_email}`);
    const done = await finish(alert.id, true, null);
    if (done && done.attempts >= 6 && done.status !== 'sent') {
      warn(`        ${alert.id} has exhausted its retries`);
    }

    if (delayMs > 0) await new Promise((r) => setTimeout(r, delayMs));
  }

  return result;
}
