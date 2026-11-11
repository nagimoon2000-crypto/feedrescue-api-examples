"""Separate consented browser activity, trusted validation metadata and reconciled cash.

SQLite belongs outside the public document root. No product bodies, keys, IPs or
full referrers are accepted by the public event schema.
"""
import hashlib
import math
from contextlib import contextmanager
from pathlib import Path
import sqlite3
import time
import uuid
from datetime import datetime, timezone

BROWSER_EVENTS = frozenset({'docs_view', 'sample_run', 'pilot_cta_click', 'pilot_brief_copied', 'file_service_click'})
SOURCES = frozenset({'direct', 'github', 'pinterest', 'upwork', 'search', 'other'})
MEDIUMS = frozenset({'direct', 'referral', 'organic', 'organic_social', 'other'})
CAMPAIGNS = frozenset({'none', 'unknown', 'gtin_tool_20261110', 'developer_quickstart'})
OPERATIONS = frozenset({'products/validate', 'products/batch-validate', 'products/suggest-fixes', 'feeds/validate'})


def identifier(value):
    if not isinstance(value, str):
        raise ValueError('Expected an opaque UUID.')
    try: parsed = uuid.UUID(value)
    except (ValueError, AttributeError): raise ValueError('Expected an opaque UUID.') from None
    if str(parsed) != value or parsed.version != 4:
        raise ValueError('Expected a canonical random UUID.')
    return value


def integer(value, minimum=0):
    if type(value) is not int or value < minimum or value > 10**12:
        raise ValueError('Expected bounded integer units.')
    return value


def reference(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 160 or any(ord(c) < 32 for c in value):
        raise ValueError('A bounded reconciliation reference is required.')
    return value


def timestamp(value):
    try: result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (ValueError, AttributeError): raise ValueError('Use an ISO timestamp with timezone.') from None
    if result.tzinfo is None or result.timestamp() > time.time() + 60:
        raise ValueError('Use an actual past timestamp with timezone.')
    return result.timestamp()


class GrowthLedger:
    def __init__(self, db):
        self.db = Path(db)
        self.db.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as c:
            c.executescript("""
              CREATE TABLE IF NOT EXISTS sessions(
                id TEXT PRIMARY KEY, source TEXT, medium TEXT, campaign TEXT, created REAL);
              CREATE TABLE IF NOT EXISTS events(
                id TEXT PRIMARY KEY, session TEXT, event TEXT, created REAL);
              CREATE TABLE IF NOT EXISTS pilots(
                id TEXT PRIMARY KEY, qualified INTEGER, approved INTEGER, evidence TEXT, created REAL);
              CREATE TABLE IF NOT EXISTS validations(
                id TEXT PRIMARY KEY, integration TEXT, kind TEXT, success INTEGER,
                products INTEGER, latency REAL, created REAL);
              CREATE TABLE IF NOT EXISTS payments(
                provider TEXT, transaction_id TEXT, currency TEXT, amount INTEGER,
                fee INTEGER, evidence TEXT, received REAL, PRIMARY KEY(provider, transaction_id));
              CREATE TABLE IF NOT EXISTS refunds(
                provider TEXT, refund_id TEXT, transaction_id TEXT, amount INTEGER,
                evidence TEXT, received REAL, PRIMARY KEY(provider, refund_id));
              CREATE TABLE IF NOT EXISTS costs(
                id TEXT PRIMARY KEY, currency TEXT, kind TEXT, amount INTEGER, evidence TEXT, received REAL);
              CREATE TABLE IF NOT EXISTS edge(bucket INTEGER PRIMARY KEY, n INTEGER);
              CREATE TABLE IF NOT EXISTS forgotten(digest TEXT PRIMARY KEY, expires REAL);
            """)

    @contextmanager
    def connect(self):
        c = sqlite3.connect(self.db, timeout=5)
        c.row_factory = sqlite3.Row
        try:
            with c: yield c
        finally: c.close()

    def purge(self, now=None):
        cutoff = (time.time() if now is None else now) - 30 * 86400
        with self.connect() as c:
            c.execute('DELETE FROM events WHERE created < ?', (cutoff,))
            c.execute('DELETE FROM events WHERE session IN (SELECT id FROM sessions WHERE created < ?)', (cutoff,))
            c.execute('DELETE FROM sessions WHERE created < ?', (cutoff,))
            c.execute('DELETE FROM validations WHERE created < ?', (cutoff,))
            c.execute('DELETE FROM forgotten WHERE expires < ?', (cutoff+30*86400,))

    def edge(self, now=None):
        bucket = int((time.time() if now is None else now) // 60)
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            c.execute('DELETE FROM edge WHERE bucket < ?', (bucket - 1,))
            c.execute('INSERT OR IGNORE INTO edge VALUES (?, 0)', (bucket,))
            if c.execute('SELECT n FROM edge WHERE bucket=?', (bucket,)).fetchone()[0] >= 60:
                return False
            c.execute('UPDATE edge SET n=n+1 WHERE bucket=?', (bucket,))
            return True

    def event(self, payload, now=None):
        if not isinstance(payload, dict) or set(payload) != {'event', 'event_id', 'session_id', 'consent', 'attribution'}:
            raise ValueError('Unexpected event fields.')
        if payload['consent'] is not True or payload['event'] not in BROWSER_EVENTS:
            raise ValueError('Explicit consent and a browser-event name are required.')
        event_id, session = identifier(payload['event_id']), identifier(payload['session_id'])
        attrs = payload['attribution']
        if not isinstance(attrs, dict) or set(attrs) != {'source', 'medium', 'campaign'}:
            raise ValueError('Unexpected attribution fields.')
        if attrs['source'] not in SOURCES or attrs['medium'] not in MEDIUMS or attrs['campaign'] not in CAMPAIGNS:
            raise ValueError('Unsupported attribution label.')
        created = time.time() if now is None else now
        self.purge(created)
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            digest=hashlib.sha256(session.encode()).hexdigest()
            if c.execute('SELECT 1 FROM forgotten WHERE digest=?', (digest,)).fetchone():
                return False
            prior = c.execute('SELECT session,event FROM events WHERE id=?', (event_id,)).fetchone()
            if prior:
                if tuple(prior) != (session, payload['event']): raise ValueError('Event ID conflict.')
                return False
            if c.execute('SELECT COUNT(*) FROM events').fetchone()[0] >= 50000:
                raise OverflowError('Measurement storage cap reached.')
            c.execute('INSERT OR IGNORE INTO sessions VALUES (?,?,?,?,?)',
                      (session, attrs['source'], attrs['medium'], attrs['campaign'], created))
            c.execute('INSERT INTO events VALUES (?,?,?,?)', (event_id, session, payload['event'], created))
            return True

    def forget(self, session):
        session = identifier(session)
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            c.execute('DELETE FROM events WHERE session=?', (session,))
            c.execute('DELETE FROM sessions WHERE id=?', (session,))
            c.execute('INSERT OR REPLACE INTO forgotten VALUES (?,?)',
                      (hashlib.sha256(session.encode()).hexdigest(),time.time()+30*86400))

    def pilot(self, integration, qualified, approved, evidence):
        identifier(integration); reference(evidence)
        if type(qualified) is not bool or type(approved) is not bool or (approved and not qualified):
            raise ValueError('Approval requires an actual qualified request.')
        with self.connect() as c:
            c.execute('INSERT INTO pilots VALUES (?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET qualified=excluded.qualified, approved=excluded.approved, evidence=excluded.evidence',
                      (integration, qualified, approved, evidence, time.time()))

    def validation(self, integration, metadata, now=None):
        """Trusted operator/SDK hook, never called by the public collector."""
        identifier(integration)
        if not isinstance(metadata, dict) or set(metadata) != {'event_id', 'operation', 'data_kind', 'processing_consent', 'success', 'products', 'latency_ms'}:
            raise ValueError('Unexpected validation metadata.')
        identifier(metadata['event_id'])
        if metadata['operation'] not in OPERATIONS or metadata['data_kind'] not in {'synthetic', 'real'}:
            raise ValueError('Only processing operations can count as validations.')
        if type(metadata['success']) is not bool or metadata['processing_consent'] is not True:
            raise ValueError('Explicit processing consent is required.')
        products = integer(metadata['products'])
        latency = metadata['latency_ms']
        if type(latency) not in (int, float) or not math.isfinite(latency) or not 0 <= latency <= 300000:
            raise ValueError('Invalid latency.')
        created = time.time() if now is None else now
        with self.connect() as c:
            if not c.execute('SELECT 1 FROM pilots WHERE id=? AND approved=1', (integration,)).fetchone():
                raise ValueError('Register a qualified, approved pilot before measuring integration use.')
            c.execute('INSERT OR IGNORE INTO validations VALUES (?,?,?,?,?,?,?)',
                      (metadata['event_id'], integration, metadata['data_kind'], metadata['success'], products, latency, created))

    def payment(self, provider, transaction, currency, amount, fee, evidence, received):
        """Operator-reconciled receipt only. There is intentionally no browser endpoint."""
        reference(provider); reference(transaction); reference(evidence)
        if currency not in {'USD', 'GBP'}: raise ValueError('Record currencies separately: USD or GBP.')
        integer(amount, 1); integer(fee)
        if fee > amount: raise ValueError('Fee exceeds collected amount.')
        row = (provider, transaction, currency, amount, fee, evidence, timestamp(received))
        with self.connect() as c:
            prior = c.execute('SELECT * FROM payments WHERE provider=? AND transaction_id=?', (provider, transaction)).fetchone()
            if prior:
                if tuple(prior) != row: raise ValueError('Transaction conflict; reconcile before changing cash.')
                return False
            c.execute('INSERT INTO payments VALUES (?,?,?,?,?,?,?)', row)
            return True

    def refund(self, provider, refund_id, transaction, amount, evidence, received):
        reference(provider); reference(refund_id); reference(transaction); reference(evidence); integer(amount, 1)
        row = (provider, refund_id, transaction, amount, evidence, timestamp(received))
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            prior = c.execute('SELECT * FROM refunds WHERE provider=? AND refund_id=?', (provider, refund_id)).fetchone()
            if prior:
                if tuple(prior) != row: raise ValueError('Refund conflict.')
                return False
            payment = c.execute('SELECT amount FROM payments WHERE provider=? AND transaction_id=?', (provider, transaction)).fetchone()
            refunded = c.execute('SELECT COALESCE(SUM(amount),0) FROM refunds WHERE provider=? AND transaction_id=?', (provider, transaction)).fetchone()[0]
            if not payment or refunded + amount > payment[0]: raise ValueError('Refund exceeds recorded receipt.')
            c.execute('INSERT INTO refunds VALUES (?,?,?,?,?,?)', row)
            return True

    def cost(self, cost_id, currency, kind, amount, evidence, received):
        identifier(cost_id); reference(evidence); integer(amount)
        if currency not in {'USD', 'GBP'} or kind not in {'compute', 'llm', 'support', 'fixed'}:
            raise ValueError('Unsupported cost currency or category.')
        row = (cost_id, currency, kind, amount, evidence, timestamp(received))
        with self.connect() as c:
            prior = c.execute('SELECT * FROM costs WHERE id=?', (cost_id,)).fetchone()
            if prior:
                if tuple(prior) != row: raise ValueError('Cost conflict.')
                return False
            c.execute('INSERT INTO costs VALUES (?,?,?,?,?,?)', row)
            return True

    def report(self, now=None):
        current = time.time() if now is None else now
        self.purge(current)
        with self.connect() as c:
            funnel = {name: c.execute('SELECT COUNT(DISTINCT session) FROM events WHERE event=?', (name,)).fetchone()[0] for name in sorted(BROWSER_EVENTS)}
            denominator = funnel['docs_view']
            cohorts = [dict(row) for row in c.execute("""
              SELECT source,medium,campaign,COUNT(DISTINCT CASE WHEN event='docs_view' THEN session END) AS measured_sessions,
                COUNT(DISTINCT CASE WHEN event='pilot_cta_click' THEN session END) AS pilot_click_sessions
              FROM sessions JOIN events ON sessions.id=events.session GROUP BY source,medium,campaign""")]
            real = c.execute("SELECT * FROM validations WHERE kind='real' ORDER BY created").fetchall()
            successful = [row for row in real if row['success'] and row['products']>0]
            dates = {}
            for row in successful: dates.setdefault(row['integration'], []).append(row['created'])
            repeat = sum(any(b-a <= 7*86400 and datetime.fromtimestamp(a,timezone.utc).date()!=datetime.fromtimestamp(b,timezone.utc).date()
                             for a,b in zip(times,times[1:])) for times in dates.values())
            paired = {event:c.execute("SELECT COUNT(DISTINCT session) FROM events WHERE event=? AND session IN (SELECT session FROM events WHERE event='docs_view')", (event,)).fetchone()[0]
                      for event in ('pilot_cta_click','sample_run')}
            latency = sorted(row['latency'] for row in real)
            percentile = lambda p: latency[max(0, math.ceil(len(latency)*p)-1)] if latency else None
            money = {}
            for currency in ('USD', 'GBP'):
                gross, fees, count = c.execute('SELECT COALESCE(SUM(amount),0),COALESCE(SUM(fee),0),COUNT(*) FROM payments WHERE currency=?', (currency,)).fetchone()
                refunds = c.execute('SELECT COALESCE(SUM(refunds.amount),0) FROM refunds JOIN payments USING(provider,transaction_id) WHERE currency=?', (currency,)).fetchone()[0]
                costs = {kind: c.execute('SELECT COALESCE(SUM(amount),0) FROM costs WHERE currency=? AND kind=?', (currency,kind)).fetchone()[0] for kind in ('compute','llm','support','fixed')}
                contribution = gross-fees-refunds-costs['compute']-costs['llm']-costs['support']
                money[currency] = dict(recorded_receipts=count, collected_minor=gross, fees_minor=fees, refunds_minor=refunds,
                                       costs_minor=costs, contribution_minor=contribution, after_fixed_minor=contribution-costs['fixed'],
                                       realized_mrr_minor=None, reconciliation='operator-entered evidence; not provider-synchronized')
                money[currency]['cost_completeness']='not asserted; contribution subtracts recorded costs only'
                money[currency]['profit_verified']=False
            return {'measurement':'consented sessions in retained last 30 days; not unique people or all visitors',
                    'browser_sessions':funnel, 'attribution_cohorts':cohorts,
                    'measured_stage_sessions_with_docs_view':paired,
                    'pilot_click_rate':paired['pilot_cta_click']/denominator if denominator else None,
                    'sample_completion_rate':paired['sample_run']/denominator if denominator else None,
                    'qualified_pilot_requests':c.execute('SELECT COUNT(*) FROM pilots WHERE qualified=1').fetchone()[0],
                    'approved_pilots':c.execute('SELECT COUNT(*) FROM pilots WHERE approved=1').fetchone()[0],
                    'real_validations':len(real), 'successful_real_integrations':len(dates),
                    'repeat_integrations_7d':repeat, 'validated_products':sum(row['products'] for row in successful),
                    'synthetic_validations':c.execute("SELECT COUNT(*) FROM validations WHERE kind='synthetic'").fetchone()[0],
                    'error_rate':sum(not row['success'] for row in real)/len(real) if real else None,
                    'latency_ms':{'p50':percentile(.5),'p95':percentile(.95)},
                    'billing_active':False, 'money':money,
                    'money_coverage':'Recorded receipts/costs only, all time in this local ledger. Empty means zero recorded cash, not verified zero external sales. MRR unavailable: subscription billing is not connected.'}
