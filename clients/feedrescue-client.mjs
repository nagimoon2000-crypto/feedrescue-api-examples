// Dependency-free Node 24+ client. Set FEEDRESCUE_API_KEY; never put keys in browser code.
export class FeedRescueAPIError extends Error {
  constructor(status, code, requestId = null, retryAfter = null) {
    super(`${status ?? 'transport'}: ${code}; request_id=${requestId ?? 'unavailable'}`);
    this.name = 'FeedRescueAPIError'; this.status = status; this.code = code;
    this.requestId = requestId; this.retryAfter = retryAfter;
  }
}
export class FeedRescueClient {
  constructor(key, baseUrl = 'http://127.0.0.1:8000') {
    const url = new URL(baseUrl);
    if (typeof key !== 'string' || !key) throw new Error('Supply a private API key');
    if (url.username || url.password || url.search || url.hash) throw new Error('Base URL must not contain credentials, query or fragment');
    if (url.protocol !== 'https:' && !(['127.0.0.1', 'localhost'].includes(url.hostname) && url.protocol === 'http:')) throw new Error('Use HTTPS outside loopback');
    this.key = key; this.baseUrl = baseUrl.replace(/\/$/, '');
  }
  async call(operation, payload) {
    if (!['products/validate', 'products/batch-validate', 'products/suggest-fixes', 'feeds/validate', 'usage'].includes(operation)) throw new Error('Unsupported operation');
    if ((operation === 'usage' && payload !== undefined) || (operation !== 'usage' && (!payload || typeof payload !== 'object' || Array.isArray(payload)))) throw new Error('Use no body for usage and a JSON object for processing');
    let response;
    try { response = await fetch(`${this.baseUrl}/v1/${operation}`, {
      method: payload === undefined ? 'GET' : 'POST',
      headers: { 'X-API-Key': this.key, 'Content-Type': 'application/json' },
      body: payload === undefined ? undefined : JSON.stringify(payload), signal: AbortSignal.timeout(30000), redirect: 'error'
    }); } catch { throw new FeedRescueAPIError(null, 'NETWORK_ERROR'); }
    let result;
    try { result = await response.json(); }
    catch { throw new FeedRescueAPIError(response.status, 'INVALID_RESPONSE', response.headers.get('X-Request-ID')); }
    if (!response.ok) throw new FeedRescueAPIError(response.status, result?.error?.code ?? 'HTTP_ERROR', result?.meta?.request_id ?? response.headers.get('X-Request-ID'), response.headers.get('Retry-After'));
    if (!result || typeof result.data !== 'object' || Array.isArray(result.data) || result.data === null) throw new FeedRescueAPIError(response.status, 'INVALID_RESPONSE', response.headers.get('X-Request-ID'));
    return result; // No automatic retries: each processing attempt consumes allowance.
  }
}
