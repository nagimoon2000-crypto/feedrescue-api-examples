// Anonymous Node 24+ preflight. Never reads API keys or sends product data.
import { pathToFileURL } from 'node:url';

const ORIGIN = 'https://gimoon.pythonanywhere.com';
const operations = ['/v1/products/validate', '/v1/products/batch-validate', '/v1/feeds/validate', '/v1/products/suggest-fixes'];

export async function checkConnection(origin = ORIGIN) {
  const url = new URL(origin);
  const local = ['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname);
  if (url.username || url.password || url.search || url.hash || url.pathname !== '/' ||
      !(url.protocol === 'https:' || (local && url.protocol === 'http:'))) {
    throw new Error('Use a bare HTTPS origin or HTTP localhost, without credentials or query.');
  }
  const checks = [];
  for (const [path, expected] of [['/v1/health', 200], ['/v1/openapi.json', 200], ['/v1/usage', 401]]) {
    let status = null, passed = false;
    try {
      const response = await fetch(`${url.origin}${path}`, {
        method: 'GET', headers: { Accept: 'application/json' },
        redirect: 'manual', signal: AbortSignal.timeout(10000)
      });
      status = response.status;
      // Bound upstream response size; never print its body or headers.
      const reader = response.body?.getReader();
      let bytes = 0; const chunks = [];
      if (!reader) throw new Error('Missing response body');
      try {
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          bytes += value.byteLength;
          if (bytes > 1048576) throw new Error('Oversized response');
          chunks.push(Buffer.from(value));
        }
      } finally { await reader.cancel(); }
      const payload = JSON.parse(Buffer.concat(chunks).toString('utf8'));
      passed = status === expected;
      if (path === '/v1/health') passed &&= payload?.ok === true;
      else if (path === '/v1/openapi.json') passed &&= operations.every(p => Object.hasOwn(payload?.paths?.[p] ?? {}, 'post'));
      else passed &&= payload?.error?.code === 'INVALID_API_KEY';
    } catch { passed = false; }
    checks.push({ path, status, passed });
  }
  const ready = checks.every(check => check.passed);
  return {
    ready_for_key_request: ready, checks, api_key_sent: false, product_data_sent: false,
    next_step: ready ? 'Request a manual free pilot key using the README contact instructions.' :
      'Read docs/errors-and-limits.md; report only status codes and a synthetic reproduction.',
    limits: 'Anonymous origin preflight only. Not a product diagnosis, RapidAPI gateway test, or uptime guarantee.'
  };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const args = process.argv.slice(2);
  if (args.length && !(args.length === 2 && args[0] === '--origin')) {
    console.error('Usage: node clients/check-connection.mjs [--origin https://host]');
    process.exitCode = 2;
  } else {
    try {
      const result = await checkConnection(args[1]);
      console.log(JSON.stringify(result, null, 2));
      process.exitCode = result.ready_for_key_request ? 0 : 1;
    } catch {
      console.error('Invalid origin. Use a bare HTTPS origin or HTTP localhost; no credentials or query.');
      process.exitCode = 2;
    }
  }
}
