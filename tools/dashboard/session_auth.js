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
  return {token, parse, apply};
})();
if (typeof module !== 'undefined') module.exports = SmelterAuth;
