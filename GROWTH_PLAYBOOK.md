# Growth execution plan — FeedRescue API

> Status: implementation proposal only. Do not present pilot interest, conversions, testimonials or paid subscribers as achieved.

## Offer: sell the outcome, not a JSON endpoint
**Audience:** Shopify/WooCommerce integrators and small feed agencies who need pre-submission data checks.

**Core promise:** "Catch actionable product-feed errors before your next Google Merchant Center submission, with field-level findings and source-safe repair suggestions." This is **not** a promise of Google approval, account reinstatement, merchant revenue, or live store checks.

**Evidence to show:** a reproducible synthetic GTIN-check-digit error, missing attributes, invalid price, and a sample response with a documented reason, suggested change when certain, and limitations. Do not invent GTINs, stock, product claims or customer evidence.

**Offer ladder:**
1. Free: no-key anonymous health/OpenAPI check and synthetic demo; manually reviewed pilot-key access, limited real-product validations under explicit consent.
2. Paid hypothesis A: $19/month with measured call limit, fair-use policy and email support.
3. Paid hypothesis B: $49/month with higher measured limits, batch endpoint, exportable diagnosis and prioritized support.
4. Agency: custom allowance for multiple stores; only introduce when agency demand is verified.
All prices are experiments. Billing is **not active** until verified and connected.

## Leads: existing purchase intent first
- Upwork Merchant Center feed troubleshooting jobs: manual, tailored proposals; differentiate file-service package from API integration.
- Developer landing page: demo payload → reproducible result → pilot request; only one clear CTA per step.
- GitHub: self-contained Python/JS examples, realistic synthetic examples, integration guides, no API key in browser.
- Communities: answer real product-data questions without automated unsolicited messaging.
- Analytics events: `docs_view`, `sample_run`, `pilot_request`, `pilot_approved`, `first_successful_validation`, `repeat_validation_7d`, `paid_started`, `cancelled`; instrument only with a privacy-safe setup. Do not confuse health checks with product validations.

## Money model and unit economics
Track:
- qualified pilot requests, approved pilots, active integrations, validated products, repeat callers, paid conversions;
- request count, error rates, P50/P95 latency, compute/LLM cost per 1k checks, support time, refunds;
- realized MRR, fees and hosting expense separately.
Do not market "always on" or an SLA without operating data.

Gross contribution formula: realized subscription revenue - marketplace/payment fees - variable compute - support allocation - refunds. Fixed operations are separate.

## Engineering backlog for Codex
- [ ] Verify public README, OpenAPI and deployment status before copy changes.
- [ ] Add privacy-safe event instrumentation with opt-in and no customer product content in analytics.
- [ ] Add a clear pilot CTA and conversion attribution, with no pretend checkout.
- [ ] Track real validation events separately from anonymous checks and synthetic demos.
- [ ] Add example responses with verifiable source and unsupported-check warning.
- [ ] Add quota/plan enforcement only after billing mechanism and entitlements are reviewed.
- [ ] Add deployment monitoring and budget guardrails.
- [ ] Write automated tests for no fabricated GTIN, price, brand or stock.

## 14-day validation (targets, not forecasts)
Week 1: audit 10 competitor alternatives and 15 qualified live buyer requests; publish proof demo and an honest pilot offer.
Week 2: deliver 5 tailored invitations/proposals where appropriate, aim for 3 qualified pilots, measure integration completion and obtain explicit paid feedback.

**Go/no-go:** Continue API monetization only when at least 2 independent developers complete a real permitted validation and one agrees to a specific paid pilot or deposit. Otherwise revise the customer/offer; do not add more endpoints as a substitute for demand.

## Safety and truthfulness
Never publish private keys, store data, fabricated testimonials, fake discounts or fake purchase badges. Google Merchant Center approval is controlled by Google. Any live data handling needs consent, deletion policy and access limits.
