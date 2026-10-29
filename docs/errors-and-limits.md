# Errors and pilot limits

```json
{
  "error": {"code": "INVALID_API_KEY", "message": "Supply a valid X-API-Key header."},
  "meta": {"request_id": "synthetic-request-id", "api_version": "1.0.0"}
}
```

| HTTP | Example codes | Action |
|---|---|---|
| 400 | INVALID_JSON, INVALID_REQUEST, INVALID_HOST | Correct request shape/URL |
| 401 | INVALID_API_KEY | Check the privately issued key; rotate a leaked key |
| 404 | NOT_FOUND | Check the endpoint; operator/file routes are not public |
| 405 | METHOD_NOT_ALLOWED | Use the documented method |
| 413 / 415 | PAYLOAD_TOO_LARGE / UNSUPPORTED_MEDIA_TYPE | Reduce JSON/file size; send JSON |
| 422 | INVALID_COUNTRY, INVALID_PRODUCT, INVALID_FEED, CONSENT_REQUIRED, BATCH_LIMIT_EXCEEDED | Correct inputs, authorization or batch size |
| 426 | HTTPS_REQUIRED | Use HTTPS directly |
| 429 | RATE_LIMITED, REQUEST_QUOTA_EXCEEDED, PRODUCT_QUOTA_EXCEEDED, PILOT_EDGE_LIMIT | Inspect usage; respect Retry-After; contact the provider for scope |
| 500 / 503 | INTERNAL_ERROR, SERVER_BUSY, PILOT_UNAVAILABLE, METER_UNAVAILABLE | Save request ID; investigate before retrying |

Some pilot capacity/storage errors are host-level safeguards rather than product validation findings. A gateway/hosting outage may return a non-JSON response; report HTTP status without printing your product body or key.

Free pilot allowances are 100 admitted processing attempts and 500 product units per UTC calendar month, 10 processing requests per trailing minute and 25 products per request. Account limits survive key rotation and restart. The private pilot also has a shared host budget, so available capacity is not an uptime guarantee. Processing errors and retries can consume allowance. Hard limits are enabled; automatic overage charges are disabled. Paid plan prices are not an available checkout offer.

GTIN checksum validity is not GTIN ownership. URL syntax validity is not live image access. A file price format check is not a live price mismatch audit. These limits are part of the service's intended boundary.
