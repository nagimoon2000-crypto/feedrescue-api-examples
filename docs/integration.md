# Integrating product feed diagnosis

Base URL: `https://gimoon.pythonanywhere.com`. Use HTTPS directly; do not send secrets to an HTTP URL and rely on a redirect.

## Product values and result handling

Send canonical lowercase attributes with string values. A leading-zero GTIN must remain a string. Choose `country: "US"` or `"GB"`. Missing factual attributes are findings, not invitations to generate replacement identifiers, stock or brand names.

`data` contains engine diagnostics: issues, proposals, product counts and verification checklist. `meta` includes `request_id`, `api_version`, effective plan, units and `google_approval_verified: false`. A successful diagnostic request can contain severe product errors; HTTP 200 means the API processed the request, not that Google approved the products.

## Batch example

```python
result = api.call('products/batch-validate', {
    'products': [
        {'id': 'synthetic-shared-id', 'title': 'Small example bag', 'size': 'S'},
        {'id': 'synthetic-shared-id', 'title': 'Large example bag', 'size': 'L'}
    ],
    'country': 'US', 'processing_consent': True
})
# Both duplicate IDs are flagged. No IDs are automatically renamed.
```

Single-product requests cannot detect conflicts with products not submitted. Include the relevant variants in the same batch. Limits reject oversized batches rather than silently dropping rows.

## File example

```python
import base64
from pathlib import Path

source = Path('samples/synthetic-feed.csv')
result = api.call('feeds/validate', {
    'filename': source.name,
    'data_base64': base64.b64encode(source.read_bytes()).decode('ascii'),
    'country': 'US', 'processing_consent': True
})
```

The JSON request is capped at 8 MiB including base64 and JSON overhead; the effective file cap is smaller. Free batch/file calls allow at most 25 products. DTD/entity XML and malformed feeds are rejected. Inputs are never fetched from arbitrary URLs.

## Suggestions

```python
result = api.call('products/suggest-fixes', {
    'product': {'id': 'synthetic-1', 'title': '  Canvas bag  ', 'gtin': '4006381333932'},
    'processing_consent': True
})
```

The title can have a surrounding-whitespace proposal. The invalid GTIN is flagged and not replaced. The response does not contain an approved repaired file. The existing file-service workflow has a separate explicit approval/export process; API examples do not bypass it.

## Usage and retries

```python
usage = api.call('usage')['data']
```

Check own-account allowance before scaling. A valid-key processing request admitted to validation consumes a request, including input/consent errors, interrupted work or internal processing failure. Parsed/admitted product units are tracked separately. No idempotency deduplication is available. Do not retry timed-out POST requests blindly; use the request ID and usage view to investigate.

Neither source client uploads real data automatically. Set a key only in your local/server environment. Keys in screenshots, public issues or frontend bundles must be rotated.
