# Validate a Shopify product feed before sending it to Merchant Center

Start with the exact source value and error, not a promise to fix every disapproval. Shopify's Google & YouTube channel can report missing descriptions/images, unavailable landing pages and identifier problems. An offline feed validator can explain structural issues, while store configuration and live product facts need separate evidence.

## 1. Trace one affected variant

Record its exported item ID, target country, feed source and exact variant URL. Confirm permission to export/process the data. Use synthetic data for the first integration test. Never include customer orders or store passwords.

## 2. Submit related products together

Use `products/batch-validate` to detect duplicated IDs and submitted variant inconsistencies. A single-product call cannot compare against your complete catalog. For a file, use `feeds/validate` with CSV, TSV or Google RSS/Atom XML. Keep the original export unchanged.

## 3. Separate formatting from product identity

Synthetic input title `"  Canvas bag  "` can yield a whitespace suggestion. An invalid GTIN check digit must remain an error until the actual manufacturer's identifier is supplied. Do not “repair” a checksum by inventing a plausible replacement; it could refer to a different product. Missing brands and stock values require evidence too.

## 4. Verify live mismatches outside file QA

Google compares submitted prices against landing-page/structured-data prices. Check the exact variant, currency, sale timing and source update timing. A syntactically correct `29.00 USD` does not establish that 29 dollars is the current selling price. API file diagnosis does not update Shopify, crawl your store or settle account-policy issues.

## 5. Review findings before an import

Keep the affected IDs, issue codes, sources and proposed before/after values. Obtain explicit approval before applying any change through your own integration. FeedRescue's suggestion endpoint itself applies nothing. Track unresolved findings and product-data provenance; Google makes the final review decision.

This is a technical integration example, not client work or evidence of improved ad performance. Start with the [pilot quickstart](../README.md), confirm scope and inspect account usage before processing more products.

Official references checked 2026-10-29:

- [Shopify product synchronization and troubleshooting](https://help.shopify.com/en/manual/online-sales-channels/marketplaces/google/getting-setup/syncing-products)
- [Google product data specification](https://support.google.com/merchants/answer/7052112?hl=en)
- [Google price mismatch troubleshooting](https://support.google.com/merchants/answer/12159029)
- [Google GTIN requirements](https://support.google.com/merchants/answer/6324461?hl=en)
