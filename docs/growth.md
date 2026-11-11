# Growth implementation and deployment

## Seller conversion page (branch only; not deployed)

`/file-diagnosis` adds a dedicated page for the existing $29 report-only file service, separate from the API pilot. Under the existing mount it will be `/integrations/file-diagnosis`. It explains real deliverables, original-row limits, excluded work and the existing synthetic finding examples. A browser-local scope guide prepares a private inquiry; it is neither a product validation nor order acceptance. No selections, clicks, product files or identifiers are submitted or stored by this page. Host logs remain separate. Outbound CTA points to the existing Upwork product.

The root developer page links to it. The mount now scopes subpage canonicals as well as the home canonical. Existing API/engine/billing behavior is unchanged. Local Python33/Node9 tests passed; Chrome verified potentially suitable scope, copying, changing selections clearing stale brief, out-of-scope warning, and a 390px viewport with 375px content width. These QA actions are not leads. No conversion uplift is established.

Deployment requires a new reviewed checkout/release and rollback backup using the existing mount instructions below. Keep analytics off, preserve the private state and engine path. After deployment verify both developer and seller canonical URLs, seller JS, inquiry reset/copy and original home/API routes. No new hosting, subscription, customer contact or public deployment occurred in this seller-page change.

Optional developer landing and private ledger; no engine replacement, checkout or deployment.

## Local verification

Python 3.11+ and Node 24+, no extra packages:

```sh
python -m growth.server --analytics --port 8021
python -m unittest discover -s tests -v
node --test tests/growth.test.mjs tests/growth-clients.test.mjs
```

Open http://127.0.0.1:8021. Omitting `--analytics` disables collection. Windows validation: 33 Python unittest methods and 6 Node tests passed. All receipts/data in tests are synthetic temporary fixtures. On 2026-11-09 Chrome verification passed for saved-report display, WooCommerce brief selection, clipboard success, consent/withdrawal/deletion and reload resetting consent. At 390px the document width was 390px; the mobile inquiry CTA was visually inspected. Clipboard denial/offline browser scenarios and production routing still need verification. The earlier browser-disabled blocker was resolved.

## Offer and leads

The page uses the existing saved synthetic diagnosis, manual API pilot contact and separate existing Upwork file-service listing. Copying sends nothing; clicking does not prove inquiry, approval, order or payment. $19/$49 API plans remain hypotheses, not purchasable entitlements.

Explicit visit-scoped opt-in enables `docs_view`, `sample_run` (saved report displayed), `pilot_brief_copied` (clipboard success), `pilot_cta_click`, `file_service_click`. No tracking before consent; reload clears consent/identity. DNT/GPC suppress collection. Withdrawal deletes the session; a hashed suppression marker remains 30 days to reject late events. Failed deletion is reported. Network failure does not block CTA navigation. These client-reported events can be forged and must never drive billing/authorization.

Only allowlisted UTM labels are retained as first touch for the memory-only session. Missing labels mean direct/none; unknown labels become other/unknown. No IP, full URL/referrer, keys or product bodies are stored by this collector. Host logs are separate. Example: `?utm_source=github&utm_medium=referral&utm_campaign=developer_quickstart`. New campaigns require updating both allowlists. Consented sessions are neither all visitors nor unique people; cross-device/external-order attribution is unavailable.

## Trusted SDK usage

Python: optional `on_event=callback, data_kind='real'` constructor arguments. JavaScript: optional third argument `{onEvent: callback, dataKind: 'real'}`. Defaults: no callback, synthetic. Hooks emit redacted timing/count metadata only for consented processing, never health/usage reads. They transmit nowhere automatically and cannot change API results when they fail. Register an actual approved pilot, then wire a trusted server-side callback to `ledger.validation(integration_uuid, metadata)`. No key grants occur; never expose this method to browsers. Existing remote engine remains authoritative.

## Evidence before money

Private CLI: `python -m growth.manage --db /private/path/growth.sqlite3 report`. See `pilot`, `payment`, `refund`, `cost` subcommand `--help`. Record only actual reconciled receipts/refunds, actual fees/costs, evidence references and timestamps. Payment/refund require `--reconciled`, an operator assertion, not provider verification. Never seed production with test receipts. Inquiries/approvals also require private evidence.

Integer minor units; USD/GBP separate. Duplicate IDs are idempotent, conflicting values fail. Refunds cannot exceed receipts. Contribution subtracts recorded fees/refunds/compute/LLM/support; fixed costs separate. Cost completeness/profit are not verified. Cash totals cover all recorded history; telemetry covers retained 30 days. Empty ledger means zero recorded cash, not verified zero external sales. MRR is null; billing_active false. Provider sync, subscription/cancellation metrics, FX and webhooks are not implemented.

## Deployment actions (not performed)

1. Review Draft PR, run CI and complete browser QA above. Existing SDK/OpenAPI/connection examples remain available.
2. Use production WSGI with `growth.server.create_app('/private/state', 'https://YOUR_HOST', analytics=False)`. Never deploy the loopback development server. Configure trusted scheme/Host at the hosting layer. Preserve existing engine routes and home page unless deliberately changing routing after review.
3. Store SQLite outside repo/document root, restrict directory/files to service account, encrypt backups. Pilot/evidence/financial records are private operational records and not telemetry-purged; define their retention separately before customer use.
4. Configure host request/concurrency limits and monitoring. Collector: persistent shared 60 requests/minute, 1 KB body, 50,000 browser-event cap. This is a small pilot, not high-volume analytics; same-origin controls do not prevent scripted forgery.
5. Schedule `python -m growth.manage --db /private/state/growth.sqlite3 purge` daily. Define backup expiry and deletion-on-restore procedures. Enable analytics only after reviewing disclosure and host logs. No third-party scripts/cookies are used.
6. Wire SDK callbacks only on authorized server-side integrations. Reconcile receipts before entries; never expose CLI/database over HTTP. No private engine, customer files or API keys are included.
7. Roll back by restoring previous landing routing and disabling collector. Existing validation/payment infrastructure is unchanged. Keep private records secure.

This branch does not establish conversion lift, production availability, paid subscribers or revenue.

## Preserve the existing site with a dedicated mount

The reviewed deployment target is `/integrations/`, not replacement of the live home page. In the existing host WSGI configuration, after constructing the existing `application`:

```python
from growth.deployment import mount
application = mount(
    application,
    state_dir='/home/gimoon/.feedrescue-growth',
    origin='https://gimoon.pythonanywhere.com',
    prefix='/integrations',
    analytics=False,
)
```

Install the reviewed examples checkout on the host Python path first. The directory above is a proposed new private state location, not an assertion that it exists. This mount delegates home, existing assets, uploads and `/v1/` to the original application. It rewrites only the new page's local assets/config/event URLs and canonical URL. No API keys or original engine database are needed. Prefixes are limited to one dedicated lowercase segment; do not choose one already used by the original application.

Before reload: back up WSGI, record current release, confirm prefix unused, create private state with service-account permissions, run tests on host and retain rollback. After reload: compare old home/upload/API status and new landing/assets/config; config must show enabled=false. Inspect the mounted page on desktop/mobile before enabling analytics. Rollback removes the mount and restores WSGI; keep the private database protected. No production reload, merge or new expense has been performed by this change.
