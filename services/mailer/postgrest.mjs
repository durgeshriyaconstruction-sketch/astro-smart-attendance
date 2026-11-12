/**
 * Tiny PostgREST client — just enough for the three outbox RPCs.
 *
 * Every call goes to POST /rest/v1/rpc/<name> with the secret key in both
 * `apikey` and `Authorization`, which is how Supabase expects server-side calls.
 * Errors are surfaced with the Postgres message when the body is JSON.
 */

export function createRpc({ url, key, fetchImpl = fetch }) {
  const base = String(url || '').replace(/\/+$/, '');

  return async function rpc(name, args = {}) {
    const res = await fetchImpl(`${base}/rest/v1/rpc/${name}`, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        accept: 'application/json',
        apikey: key,
        authorization: `Bearer ${key}`,
      },
      body: JSON.stringify(args),
    });

    const text = await res.text();
    if (!res.ok) {
      let detail = text;
      try {
        const parsed = JSON.parse(text);
        detail = parsed.message || parsed.error_description || parsed.hint || text;
      } catch {
        /* keep raw text */
      }
      throw new Error(`rpc ${name} failed (${res.status}): ${detail}`);
    }
    return text ? JSON.parse(text) : null;
  };
}
