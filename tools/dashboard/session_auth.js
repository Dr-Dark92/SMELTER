/* The launch token stays in the URL fragment; it is never fetched from an open endpoint. */
const SmelterAuth = (() => {
  function token(location = window.location) {
    return new URLSearchParams(location.hash.slice(1)).get('token') || '';
  }
  function parse(value, origin) {
    value = value.trim();
    if (/^https?:\/\//i.test(value)) {
      let url;
      try { url = new URL(value); } catch { throw Error('Paste the complete launch URL printed in the dashboard terminal.'); }
      if (url.origin !== origin || url.pathname !== '/' || url.username || url.password) {
        throw Error('This launch URL uses a different address or port. Open that complete URL in a new tab.');
      }
      value = token(url);
    }
    if (!/^[A-Za-z0-9_-]{8,128}$/.test(value)) throw Error('Paste the current launch URL or its token from the dashboard terminal.');
    return value;
  }
  function apply(value, location = window.location) {
    const current = parse(value, location.origin);
    location.hash = '#' + new URLSearchParams({token: current}).toString();
  }
  // A token the server rejected stays rejected: pollers stop hitting the network with it
  // until a new launch URL changes the fragment, and the shell is told once.
  const rejected = new Set();
  function guard(fetchImpl, notify) {
    return async (input, init = {}) => {
      const headers = new Headers(init.headers || (input instanceof Request ? input.headers : undefined));
      const sent = headers.get('X-Smelter-Token');
      if (sent && rejected.has(sent)) {
        return new Response(JSON.stringify({error: 'Unauthorized'}), {status: 403, headers: {'Content-Type': 'application/json'}});
      }
      const response = await fetchImpl(input, init);
      if (sent && (response.status === 401 || response.status === 403) && !rejected.has(sent)) {
        rejected.add(sent);
        notify?.();
      }
      return response;
    };
  }
  const isRejected = value => rejected.has(value);
  if (typeof window !== 'undefined' && window.fetch) {
    window.fetch = guard(window.fetch.bind(window), () => window.dispatchEvent(new Event('smelter-auth-rejected')));
  }
  return {token, parse, apply, guard, isRejected};
})();
if (typeof module !== 'undefined') module.exports = SmelterAuth;
