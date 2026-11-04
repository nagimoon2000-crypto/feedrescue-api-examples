# Google Merchant Center GTIN errors: reading a feed diagnosis

FeedRescue checks submitted product data structure. Use this walkthrough to assess whether the API fits your importer before requesting access. This is a synthetic example, not a merchant result or a Google approval decision.

## One product, two different actions

The [synthetic product](../samples/single-product.json) contains `title: " Canvas bag "` and `gtin: "4006381333932"`. The GTIN has an invalid check digit; do not replace it with a guessed digit. Obtain the actual identifier from the seller/manufacturer and confirm it belongs to this product.

The [generated sample diagnosis](../samples/sample-diagnosis.json) comes from the same FeedRescue engine used by the service. A surrounding-title-whitespace proposal preserves the supplied meaning. The API proposes changes; it does not apply them or produce an approved repaired feed. Other findings may remain after a formatting suggestion.

| Finding | Safe next action | Outside this check |
|---|---|---|
| Invalid GTIN syntax or check digit | Request the real product identifier | Ownership, authenticity, guessing a replacement |
| Surrounding title whitespace | Review the before/after proposal | Rewriting unverified product attributes |
| Duplicate ID in a batch | Review the seller's ID/variant mapping | Inventing unique IDs automatically |
| Price formatting issue | Verify formatting against supplied facts | Choosing a different selling price |

Do not infer a site's actual price, stock, image accessibility or account status from a file-only result. See [Google's GTIN attribute documentation](https://support.google.com/merchants/answer/6324461) and [product data specification](https://support.google.com/merchants/answer/7052112).

## Request a free API pilot

Contact the provider via the [Upwork profile](https://www.upwork.com/freelancers/~0169e4dcdc3c4f3f65). Keep platform-originated communication and agreements on the platform. Copy this short brief into the private conversation:

```text
FeedRescue API pilot request
Platform: Shopify / WooCommerce / custom importer
Target: US / GB
Approximate SKU count and checks per month:
Language: Python / JavaScript / other
Needed endpoint: single / batch / feed / suggestions
Problem to detect (no private product data):
Where I found FeedRescue: GitHub / Pinterest / other
I can start with synthetic data and understand that Google approval is not guaranteed.
```

Free pilot hypothesis: 100 processing attempts/500 product units per UTC month, 10 processing requests/minute, at most 25 products per request. Access is manual, subject to capacity and agreed scope. Do not buy a file-service package expecting API access. No automatic overage charges or public paid API subscription are active.

## Need a reviewed file instead?

The [separate file-service offer](https://www.upwork.com/services/product/2113612758971436241) is for a bounded diagnosis or approved safe repairs. Diagnosis is report-only; repair packages include separate outputs after review. Confirm current scope, SKU limits and delivery timing on Upwork before ordering. No store credentials are needed for the initial file assessment.

## When to choose another solution

If your need is live Shopify/WooCommerce synchronization, account reinstatement, automatic website price verification or Google approval, the current file/API pilot does not provide it. A platform's native integration may already meet your needs.
