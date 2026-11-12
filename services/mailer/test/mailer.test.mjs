import test from 'node:test';
import assert from 'node:assert/strict';

import { renderEmail } from '../template.mjs';
import { runPass, shortError } from '../worker.mjs';
import { FatalProviderError } from '../providers.mjs';

const notice = {
  id: 7,
  kind: 'notice',
  title: 'PTM on Saturday',
  subject: 'PTM on Saturday',
  body: 'Parent-teacher meeting this Saturday at 10 AM.\n\nPlease bring the report card.',
  to_email: 'parent@example.com',
};

// ------------------------------------------------------------------ template

test('subject falls back through subject, title, kind default', () => {
  assert.equal(renderEmail(notice, { schoolName: 'S' }).subject, 'PTM on Saturday');
  assert.equal(
    renderEmail({ kind: 'absent', body: 'x' }, { schoolName: 'S' }).subject,
    'Absence recorded today'
  );
  assert.equal(
    renderEmail({ kind: 'late', title: 'Late again' }, { schoolName: 'S' }).subject,
    'Late again'
  );
});

test('html escapes user-supplied text, in title and body', () => {
  const mail = renderEmail(
    { kind: 'message', title: '<script>alert(1)</script>', body: '5 > 3 & "quoted" <b>no</b>' },
    { schoolName: 'S' }
  );
  assert.ok(!mail.html.includes('<script>'));
  assert.ok(mail.html.includes('&lt;script&gt;'));
  assert.ok(mail.html.includes('5 &gt; 3 &amp; &quot;quoted&quot; &lt;b&gt;no&lt;/b&gt;'));
});

test('body keeps paragraph breaks and blank lines never render empty <p>', () => {
  const mail = renderEmail({ kind: 'notice', title: 'T', body: 'one\n\ntwo\n\n\n' }, { schoolName: 'S' });
  assert.equal((mail.html.match(/<p style/g) || []).length, 2);
  assert.ok(mail.text.includes('one'));
  assert.ok(mail.text.includes('two'));
});

test('text part carries school name, body and the do-not-reply footer', () => {
  const mail = renderEmail(notice, { schoolName: 'Sunrise Public School', fromName: 'Office' });
  assert.ok(mail.text.startsWith('Sunrise Public School'));
  assert.ok(mail.text.includes('Please bring the report card.'));
  assert.ok(mail.text.includes('not monitored'));
});

test('every alert kind renders a label and an accent colour', () => {
  for (const kind of ['notice', 'message', 'absent', 'late', 'unknown_card', 'low_attendance']) {
    const mail = renderEmail({ kind, title: 't', body: 'b' }, { schoolName: 'S' });
    assert.match(mail.html, /background:#[0-9a-f]{6}/i, kind);
    assert.ok(mail.subject.length > 0, kind);
  }
});

test('missing body still produces a valid email', () => {
  const mail = renderEmail({ kind: 'notice', title: 'Only a title' }, { schoolName: 'S' });
  assert.ok(mail.html.includes('Only a title'));
  assert.ok(!mail.html.includes('undefined'));
});

// -------------------------------------------------------------------- worker

function fakeDb(rows) {
  const calls = { claim: [], finish: [] };
  return {
    calls,
    claim: async (limit) => {
      calls.claim.push(limit);
      return rows;
    },
    finish: async (id, ok, error) => {
      calls.finish.push({ id, ok, error });
      return { ok: true, id, status: ok ? 'sent' : 'failed', attempts: 1 };
    },
  };
}

test('a pass sends every claimed row and records success', async () => {
  const rows = [notice, { ...notice, id: 8, to_email: 'two@example.com' }];
  const db = fakeDb(rows);
  const sent = [];
  const res = await runPass({
    claim: db.claim,
    finish: db.finish,
    provider: { send: async (mail) => sent.push(mail) },
    options: { batch: 5, schoolName: 'S' },
  });

  assert.deepEqual(res, { claimed: 2, sent: 2, failed: 0 });
  assert.equal(sent.length, 2);
  assert.equal(sent[0].to, 'parent@example.com');
  assert.equal(sent[0].subject, 'PTM on Saturday');
  assert.deepEqual(db.calls.claim, [5]);
  assert.deepEqual(db.calls.finish, [
    { id: 7, ok: true, error: null },
    { id: 8, ok: true, error: null },
  ]);
});

test('an empty queue does not touch the provider', async () => {
  const db = fakeDb([]);
  let called = 0;
  const res = await runPass({
    claim: db.claim,
    finish: db.finish,
    provider: { send: async () => called++ },
  });
  assert.deepEqual(res, { claimed: 0, sent: 0, failed: 0 });
  assert.equal(called, 0);
});

test('a per-row failure is recorded and the pass carries on', async () => {
  const rows = [notice, { ...notice, id: 8 }];
  const db = fakeDb(rows);
  let attempt = 0;
  const res = await runPass({
    claim: db.claim,
    finish: db.finish,
    provider: {
      send: async () => {
        attempt += 1;
        if (attempt === 1) throw new Error('mailbox full');
      },
    },
    options: { log: () => {}, warn: () => {} },
  });

  assert.equal(res.sent, 1);
  assert.equal(res.failed, 1);
  assert.deepEqual(db.calls.finish, [
    { id: 7, ok: false, error: 'mailbox full' },
    { id: 8, ok: true, error: null },
  ]);
});

test('a fatal provider error stops the pass and leaves the rest claimed', async () => {
  const rows = [notice, { ...notice, id: 8 }, { ...notice, id: 9 }];
  const db = fakeDb(rows);
  await assert.rejects(
    runPass({
      claim: db.claim,
      finish: db.finish,
      provider: {
        send: async () => {
          throw new FatalProviderError('resend 401: invalid api key');
        },
      },
      options: { log: () => {}, warn: () => {} },
    }),
    /invalid api key/
  );
  assert.deepEqual(db.calls.finish, [], 'nothing should be marked sent or failed');
});

test('the error string stored on a row is bounded', async () => {
  const db = fakeDb([notice]);
  const long = 'x'.repeat(2000);
  await runPass({
    claim: db.claim,
    finish: db.finish,
    provider: {
      send: async () => {
        throw new Error(long);
      },
    },
    options: { warn: () => {} },
  });
  const stored = db.calls.finish[0].error;
  assert.ok(stored.length <= 480);
  assert.ok(stored.endsWith('...'));
});

test('shortError survives non-Error throws', () => {
  assert.equal(shortError('plain string'), 'plain string');
  assert.equal(shortError(undefined), 'undefined');
  assert.equal(shortError({ message: 'obj' }), 'obj');
});
