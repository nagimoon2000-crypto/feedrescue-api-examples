# FeedRescue API examples

Python and JavaScript clients for **Google Merchant Center product feed diagnosis**. Check Google Shopping product data from Shopify, WooCommerce or your own feed importer without sharing store credentials.

**Status:** key-protected free developer pilot, deployed 2026-10-29. Access is manually arranged, not instant signup. Automated payments, paid API subscriptions and a RapidAPI listing are not available. This repository contains integration examples and documentation; the hosted validation engine is not included.

- [Live readiness endpoint](https://gimoon.pythonanywhere.com/v1/health)
- [Live OpenAPI 3.1 specification](https://gimoon.pythonanywhere.com/v1/openapi.json)
- [Integration guide](docs/integration.md)
- [Errors and quotas](docs/errors-and-limits.md)
- [Product-data QA tutorial](docs/shopify-feed-qa.md)

## What the API checks

Required fields, duplicate IDs within a submitted batch, GTIN syntax/check digits, price formats, URL syntax and submitted variant consistency. Suggestions preserve source facts: for example, trimming surrounding title whitespace. Suggestions are not applied automatically.

The API does not verify GTIN ownership, live page prices/stock, brand authenticity or image accessibility. It does not connect to a store, resolve account suspensions or guarantee Google product approval. Synthetic examples are not client results.

## Quickstart

Ask for a free pilot key before sending product data. Contact the provider through the [Upwork profile](https://www.upwork.com/freelancers/~0169e4dcdc3c4f3f65), mentioning “FeedRescue API pilot,” your platform and approximate SKU count. Do not buy a file-service package expecting API access; scope and access must be agreed separately. Never post API keys, feed files, private store data or customer information in public issues.

Keep `FEEDRESCUE_API_KEY` in a secret manager or local environment. Never put it in browser code, a URL or a committed file.

Python 3.11+, no third-party dependencies:

```python
import os
from clients.feedrescue_client import FeedRescueClient

api = FeedRescueClient(
    os.environ['FEEDRESCUE_API_KEY'],
    'https://gimoon.pythonanywhere.com'
)
result = api.call('products/validate', {
    'country': 'US',
    'processing_consent': True,
    'product': {'id': 'synthetic-1', 'title': ' Canvas bag ', 'price': '29.00 USD'}
})
issues = result['data']['issues']  # Missing fields remain findings; facts are never invented.
proposals = result['data']['proposals']
```

JavaScript, Node 24+:

```javascript
import { FeedRescueClient } from './clients/feedrescue-client.mjs';

const api = new FeedRescueClient(
  process.env.FEEDRESCUE_API_KEY,
  'https://gimoon.pythonanywhere.com'
);
const result = await api.call('products/validate', {
  country: 'US', processing_consent: true,
  product: { id: 'synthetic-1', title: ' Canvas bag ', price: '29.00 USD' }
});
// Review result.data.issues and result.data.proposals; avoid logging real product data.
```

These are source clients, not published pip/npm packages. They reject credential-bearing URLs and cross-origin redirects, use a timeout and do not automatically retry processing requests.

Run `python -m unittest discover -s tests -v` from this repository with Python 3.11+ and Node 24+. Tests use local synthetic HTTP servers only; no API key or hosted quota is required. The included GitHub Actions workflow runs the same checks after publication.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/products/validate` | One product |
| POST | `/v1/products/batch-validate` | Products checked together |
| POST | `/v1/feeds/validate` | Base64 CSV/TSV/Google RSS or Atom XML |
| POST | `/v1/products/suggest-fixes` | Source-backed suggestions for one product |
| GET | `/v1/usage` | Own account's limits and counters |

Use `X-API-Key` and `Content-Type: application/json`. Include `processing_consent: true` only when you are authorized to share/process the product data. Product attributes are strings, including GTINs and prices. US and GB targets only. Product errors return HTTP 200 with findings; authentication/transport/limit failures return standardized error responses.

Free pilot: 100 processing attempts and 500 products per UTC month, 10 processing requests/minute, up to 25 products per request. All keys for an account share limits. Retries consume allowance; no automatic overage charge. Shared host safeguards can reject traffic earlier. This is a limited pilot with monthly host renewal and no production SLA.

## Privacy and reporting a problem

Product bodies are processed in memory and are not saved as feed files. Redacted call metadata is retained up to 30 days while cleanup runs; monthly usage counters and account credentials remain for account administration. Hosting/proxy logs and filesystem protections are separate operational controls. Use synthetic data during the pilot and get agreed processing terms before real catalog submissions.

For a bug, open an issue with the endpoint, HTTP/error code, client version and a synthetic reproduction. Never include your key or real customer data. Report access/security concerns privately through the provider profile. Read [SECURITY.md](SECURITY.md).

## License

Client examples, documentation and synthetic fixtures in this repository are under the MIT license. This grants no rights to the hosted engine, trademarks, Google/Shopify/WooCommerce systems, or service access beyond agreed pilot terms. No platform affiliation is claimed. See [LICENSE](LICENSE).
