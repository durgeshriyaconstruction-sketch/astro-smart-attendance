/**
 * Email providers. Two real ones and one for local testing.
 *
 *   resend  — HTTPS API, no dependencies, free tier 3,000/month, 100/day.
 *             Needs a domain verified in Resend; their test sender
 *             onboarding@resend.dev only delivers to your own address.
 *   smtp    — any SMTP server, including Gmail with an app password
 *             (smtp.gmail.com:465, 2-step verification on, "App passwords").
 *             Requires `npm install` (nodemailer).
 *   console — prints the email and reports success. Development only; it marks
 *             rows 'sent' even though nothing left the machine.
 */

export class FatalProviderError extends Error {}

/** 4xx that will fail identically for every row: bad key, unverified domain. */
const FATAL_STATUS = new Set([401, 403, 422]);

function maskEmail(addr) {
  const [user, domain] = String(addr || '').split('@');
  if (!domain) return addr;
  return `${user.slice(0, 2)}***@${domain}`;
}

async function createResend({ resendKey, from, replyTo }) {
  return {
    name: 'resend',
    async send({ to, subject, html, text }) {
      const res = await fetch('https://api.resend.com/emails', {
        method: 'POST',
        headers: {
          authorization: `Bearer ${resendKey}`,
          'content-type': 'application/json',
        },
        body: JSON.stringify({
          from,
          to: [to],
          subject,
          html,
          text,
          ...(replyTo ? { reply_to: replyTo } : {}),
        }),
      });

      if (res.ok) return;

      const body = await res.text();
      let detail = body;
      try {
        const parsed = JSON.parse(body);
        detail = parsed.message || parsed.name || body;
      } catch {
        /* raw */
      }

      if (FATAL_STATUS.has(res.status)) {
        throw new FatalProviderError(
          `resend ${res.status}: ${detail}. Check RESEND_API_KEY and that the MAIL_FROM domain is verified.`
        );
      }
      throw new Error(`resend ${res.status}: ${detail}`);
    },
  };
}

async function createSmtp({ from, fromName, replyTo, smtp }) {
  let nodemailer;
  try {
    nodemailer = (await import('nodemailer')).default;
  } catch {
    throw new Error(
      'nodemailer is not installed. Run `npm install` in services/mailer (or switch MAIL_PROVIDER=resend).'
    );
  }

  const transport = nodemailer.createTransport({
    host: smtp.host,
    port: smtp.port,
    secure: smtp.secure,
    auth: { user: smtp.user, pass: smtp.pass },
  });

  // Prove the credentials before we start claiming rows.
  try {
    await transport.verify();
  } catch (err) {
    throw new FatalProviderError(
      `SMTP login failed: ${err.message}. For Gmail use smtp.gmail.com:465 with a 16-character app password (2FA must be on).`
    );
  }

  return {
    name: 'smtp',
    async send({ to, subject, html, text }) {
      try {
        await transport.sendMail({
          from: `"${fromName}" <${from}>`,
          to,
          subject,
          html,
          text,
          ...(replyTo ? { replyTo } : {}),
        });
      } catch (err) {
        // 5xx SMTP codes are permanent for that address; 4xx are transient.
        if (/^5\d\d/m.test(err.response || '')) throw err;
        throw err;
      }
    },
  };
}

function createConsole({ from }) {
  return {
    name: 'console',
    async send({ to, subject, text }) {
      console.log(
        `\n----- console provider (nothing was sent) -----\n` +
          `to:      ${maskEmail(to)}\n` +
          `from:    ${from}\n` +
          `subject: ${subject}\n\n${text}\n` +
          `-----------------------------------------------\n`
      );
    },
  };
}

export async function createProvider(opts) {
  switch (opts.provider) {
    case 'resend':
      return createResend(opts);
    case 'smtp':
      return createSmtp(opts);
    case 'console':
      return createConsole(opts);
    default:
      throw new Error(`unknown MAIL_PROVIDER "${opts.provider}"`);
  }
}
