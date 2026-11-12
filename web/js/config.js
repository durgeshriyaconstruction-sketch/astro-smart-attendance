// Deployment settings. The publishable key is designed to sit in a browser:
// it can call the six device RPCs and, once a user signs in, whatever that
// user's RLS policies allow. It cannot read a table on its own.
export const CONFIG = {
  url: 'https://nrjchonjlncamfyzmfye.supabase.co',
  key: 'sb_publishable_9a4vSwLdVz4Yd8wrWcTvXA_aIMmC6H_',
  // refresh the session this long before the token actually expires
  refreshSkewMs: 60_000,
};
