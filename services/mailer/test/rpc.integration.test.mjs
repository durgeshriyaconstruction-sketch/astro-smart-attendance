/**
 * Exercises the real HTTP path against a stand-in PostgREST. No Supabase
 * project, key or network needed — but every request the worker makes is a
 * genuine fetch(), so header shape, JSON encoding and error parsing are covered.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';

import { createRpc } from '../postgrest.mjs';
import { runPass } from '../worker.mjs';

const QUEUED = {
  id: 41,
  school_id: 'b081c8b6-2374-4484-807c-c4156b3791be',
  student_id: '95cb2529-0be1-4a43-bc2f-1bab6368a57d',
  to_email: 'parent@example.com',
  subject: 'PTM on Saturday',
  body: 'Meeting at 10 AM.',
  title: 'PTM on Saturday',
  kind: 'notice',
  ref_kind: 'notice',
  ref_id: '5db82b87-8df8-4830-92f7-3eaf9515f08e',
  attempts: 1,
};

async function startFakePostgrest() {
  const seen = [];

  const server = createServer((req, res) => {
    let body = '';
    req.on('data', (c) => (body += c));
    req.on('end', () => {
      const name = req.url.replace('/rest/v1/rpc/', '');
      seen.push({
        name,
        method: req.method,
        apikey: req.headers.apikey,
        auth: req.headers.authorization,
        contentType: req.headers['content-type'],
        body: body ? JSON.parse(body) : null,
      });

      const send = (status, payload) => {
        res.writeHead(status, { 'content-type': 'application/json' });
        res.end(payload === undefined ? '' : JSON.stringify(payload));
      };

      switch (name) {
        case 'astro_claim_emails':
          return send(200, [QUEUED]);
        case 'astro_finish_email':
          return send(200, { ok: true, id: 41, status: 'sent', attempts: 1 });
        case 'astro_release_stale_sending':
          return send(200, { ok: true, released: 0 });
        case 'astro_boom':
          return send(400, { message: 'STUDENT_NOT_FOUND', code: '22023' });
        case 'astro_nobody':
          res.writeHead(204);
          return res.end();
        default:
          return send(404, { message: 'no such function' });
      }
    });
  });

  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const { port } = server.address();
  return {
    url: `http://127.0.0.1:${port}`,
    seen,
    close: () => new Promise((resolve) => server.close(resolve)),
  };
}

test('a full pass runs over HTTP with the secret key on every call', async () => {
  const fake = await startFakePostgrest();
  try {
    const rpc = createRpc({ url: fake.url, key: 'sb_secret_test' });
    const delivered = [];

    const res = await runPass({
      claim: (limit) => rpc('astro_claim_emails', { p_limit: limit }),
      finish: (id, ok, error) => rpc('astro_finish_email', { p_id: id, p_ok: ok, p_error: error }),
      provider: { send: async (mail) => delivered.push(mail) },
      options: { batch: 3, schoolName: 'Sunrise Public School', log: () => {} },
    });

    assert.deepEqual(res, { claimed: 1, sent: 1, failed: 0 });
    assert.equal(delivered.length, 1);
    assert.equal(delivered[0].to, 'parent@example.com');
    assert.match(delivered[0].text, /Sunrise Public School/);
    assert.match(delivered[0].html, /Meeting at 10 AM/);

    assert.deepEqual(
      fake.seen.map((r) => r.name),
      ['astro_claim_emails', 'astro_finish_email']
    );
    assert.deepEqual(fake.seen[0].body, { p_limit: 3 });
    assert.deepEqual(fake.seen[1].body, { p_id: 41, p_ok: true, p_error: null });

    for (const call of fake.seen) {
      assert.equal(call.method, 'POST');
      assert.equal(call.apikey, 'sb_secret_test');
      assert.equal(call.auth, 'Bearer sb_secret_test');
      assert.equal(call.contentType, 'application/json');
    }
  } finally {
    await fake.close();
  }
});

test('a Postgres error message is surfaced, not swallowed', async () => {
  const fake = await startFakePostgrest();
  try {
    const rpc = createRpc({ url: fake.url, key: 'k' });
    await assert.rejects(rpc('astro_boom'), /rpc astro_boom failed \(400\): STUDENT_NOT_FOUND/);
  } finally {
    await fake.close();
  }
});

test('an empty 204 body resolves to null instead of throwing', async () => {
  const fake = await startFakePostgrest();
  try {
    const rpc = createRpc({ url: fake.url, key: 'k' });
    assert.equal(await rpc('astro_nobody'), null);
  } finally {
    await fake.close();
  }
});

test('the base url keeps working when it ends in a slash', async () => {
  const fake = await startFakePostgrest();
  try {
    const rpc = createRpc({ url: `${fake.url}/`, key: 'k' });
    assert.equal((await rpc('astro_release_stale_sending', { p_minutes: 15 })).released, 0);
    assert.equal(fake.seen[0].name, 'astro_release_stale_sending');
  } finally {
    await fake.close();
  }
});
