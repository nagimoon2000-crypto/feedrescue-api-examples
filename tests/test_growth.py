"""Synthetic, isolated fixtures only. These tests never create real revenue evidence."""
import io
import json
import sqlite3
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
from growth.ledger import GrowthLedger
from growth.server import create_app


def uid(): return str(uuid.uuid4())


def event(name='docs_view', session=None, **changes):
    return dict(event=name,event_id=uid(),session_id=session or uid(),consent=True,
                attribution=dict(source='pinterest',medium='organic_social',campaign='gtin_tool_20261110'),**changes)


class GrowthTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.ledger=GrowthLedger(Path(self.tmp.name)/'growth.sqlite3')
    def tearDown(self): self.tmp.cleanup()

    def test_empty_money_is_recorded_zero_with_unknown_mrr_and_no_checkout(self):
        report=self.ledger.report()
        self.assertIsNone(report['pilot_click_rate'])
        self.assertFalse(report['billing_active'])
        for values in report['money'].values():
            self.assertEqual(values['collected_minor'],0)
            self.assertIsNone(values['realized_mrr_minor'])
            self.assertFalse(values['profit_verified'])

    def test_click_is_not_pilot_approval_validation_or_payment(self):
        session=uid()
        self.ledger.event(event(session=session))
        self.ledger.event(event('pilot_cta_click',session))
        r=self.ledger.report()
        self.assertEqual(r['pilot_click_rate'],1)
        self.assertEqual(r['qualified_pilot_requests'],0)
        self.assertEqual(r['real_validations'],0)
        self.assertEqual(r['money']['USD']['collected_minor'],0)

    def test_browser_cannot_forge_revenue_approval_or_extra_private_fields(self):
        for name in ('paid_started','cancelled','pilot_approved','first_successful_validation','pilot_request'):
            with self.assertRaises(ValueError):self.ledger.event(event(name))
        for extra in ('api_key','product','url','referrer','email','amount'):
            payload=event();payload[extra]='sensitive-fixture'
            with self.assertRaises(ValueError):self.ledger.event(payload)
        for source in ('secret@example.test','https://private.test/path?token=secret','__proto__'):
            payload=event();payload['attribution']['source']=source
            with self.assertRaises(ValueError):self.ledger.event(payload)
        payload=event();payload['consent']=False
        with self.assertRaises(ValueError):self.ledger.event(payload)
        self.assertNotIn(b'sensitive-fixture',self.ledger.db.read_bytes())

    def test_session_event_dedup_and_first_touch_are_stable(self):
        payload=event()
        self.assertTrue(self.ledger.event(payload))
        self.assertFalse(self.ledger.event(payload))
        second=event('sample_run',payload['session_id'])
        second['attribution']=dict(source='github',medium='referral',campaign='developer_quickstart')
        self.ledger.event(second)
        r=self.ledger.report()
        self.assertEqual(r['browser_sessions']['docs_view'],1)
        self.assertEqual(r['attribution_cohorts'][0]['source'],'pinterest')
        self.assertEqual(r['sample_completion_rate'],1)

    def test_missing_docs_view_does_not_inflate_conversion_denominator(self):
        self.ledger.event(event())
        self.ledger.event(event('pilot_cta_click'))  # Different consent session.
        r=self.ledger.report()
        self.assertEqual(r['browser_sessions']['pilot_cta_click'],1)
        self.assertEqual(r['pilot_click_rate'],0)

    def test_withdrawal_removes_actions_and_blocks_late_inflight_events(self):
        payload=event()
        self.ledger.event(payload)
        self.ledger.forget(payload['session_id'])
        self.assertFalse(self.ledger.event(event('sample_run',payload['session_id'])))
        with self.ledger.connect() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM events').fetchone()[0],0)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM sessions').fetchone()[0],0)
            self.assertNotEqual(c.execute('SELECT digest FROM forgotten').fetchone()[0],payload['session_id'])

    def test_retention_and_persistent_edge_limit(self):
        now=time.time()
        self.ledger.event(event(),now=now-31*86400)
        self.ledger.purge(now)
        self.assertEqual(self.ledger.report()['browser_sessions']['docs_view'],0)
        for _ in range(60):self.assertTrue(self.ledger.edge(now))
        self.assertFalse(GrowthLedger(self.ledger.db).edge(now))
        self.assertTrue(self.ledger.edge(now+61))

    def validation(self, kind='real', **changes):
        result=dict(event_id=uid(),operation='products/validate',data_kind=kind,
                    processing_consent=True,success=True,products=2,latency_ms=20)
        result.update(changes)
        return result

    def test_real_validation_requires_operator_approved_pilot(self):
        integration=uid()
        with self.assertRaises(ValueError):self.ledger.validation(integration,self.validation())
        with self.assertRaises(ValueError):self.ledger.pilot(integration,False,True,'synthetic inquiry reference')
        self.ledger.pilot(integration,True,True,'synthetic inquiry reference')
        for invalid in (dict(processing_consent=False),dict(operation='usage'),dict(latency_ms=float('nan'))):
            with self.assertRaises(ValueError):self.ledger.validation(integration,self.validation(**invalid))

    def test_synthetic_checks_never_count_as_real_and_repeat_is_distinct_day(self):
        integration=uid();self.ledger.pilot(integration,True,True,'synthetic evidence')
        now=time.time()
        self.ledger.validation(integration,self.validation('synthetic'),now-86400)
        self.assertEqual(self.ledger.report()['successful_real_integrations'],0)
        metadata=self.validation()
        self.ledger.validation(integration,metadata,now-86400)
        self.ledger.validation(integration,metadata,now-86400)  # Same result, not a second call.
        self.ledger.validation(integration,self.validation(),now-86399)
        self.assertEqual(self.ledger.report()['repeat_integrations_7d'],0)
        self.ledger.validation(integration,self.validation(latency_ms=80),now)
        self.ledger.validation(integration,self.validation(success=False,products=0,latency_ms=100),now)
        r=self.ledger.report()
        self.assertEqual(r['real_validations'],4)
        self.assertEqual(r['repeat_integrations_7d'],1)
        self.assertEqual(r['synthetic_validations'],1)
        self.assertEqual(r['error_rate'],.25)
        self.assertEqual(r['latency_ms']['p95'],100)

    def test_reconciled_receipts_refunds_costs_are_deduped_and_currency_separate(self):
        when='2026-01-01T00:00:00Z'
        receipt=('synthetic-provider','synthetic-transaction','USD',2900,300,'synthetic receipt fixture',when)
        self.assertTrue(self.ledger.payment(*receipt))
        self.assertFalse(self.ledger.payment(*receipt))
        with self.assertRaises(ValueError):self.ledger.payment(*receipt[:3],7900,*receipt[4:])
        self.ledger.payment('synthetic-provider','synthetic-gbp','GBP',1000,100,'synthetic receipt',when)
        self.assertTrue(self.ledger.refund('synthetic-provider','refund-test','synthetic-transaction',500,'synthetic refund fixture',when))
        self.assertFalse(self.ledger.refund('synthetic-provider','refund-test','synthetic-transaction',500,'synthetic refund fixture',when))
        with self.assertRaises(ValueError):self.ledger.refund('synthetic-provider','excess','synthetic-transaction',2500,'synthetic refund',when)
        cost=uid()
        self.ledger.cost(cost,'USD','support',200,'synthetic support allocation',when)
        self.assertFalse(self.ledger.cost(cost,'USD','support',200,'synthetic support allocation',when))
        self.ledger.cost(uid(),'USD','fixed',100,'synthetic hosting invoice',when)
        r=self.ledger.report()['money']
        self.assertEqual(r['USD']['contribution_minor'],1900)
        self.assertEqual(r['USD']['after_fixed_minor'],1800)
        self.assertEqual(r['GBP']['collected_minor'],1000)
        self.assertIsNone(r['USD']['realized_mrr_minor'])


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.app=create_app(self.tmp.name,'https://pilot.test',analytics=True)
    def tearDown(self):self.tmp.cleanup()
    def call(self,path='/growth/events',payload=None,method='POST',**extra):
        raw=json.dumps(payload).encode() if payload is not None else b''
        env={'HTTP_HOST':'pilot.test','wsgi.url_scheme':'https','PATH_INFO':path,
             'REQUEST_METHOD':method,'HTTP_ORIGIN':'https://pilot.test','CONTENT_TYPE':'application/json',
             'CONTENT_LENGTH':str(len(raw)),'wsgi.input':io.BytesIO(raw)}
        env.update(extra);response={}
        def start(status,headers):response.update(status=int(status.split()[0]),headers=dict(headers))
        response['body']=b''.join(self.app(env,start))
        return response
    def test_enabled_collector_and_actual_deletion(self):
        payload=event()
        self.assertEqual(self.call(payload=payload)['status'],204)
        self.assertEqual(self.app.ledger.report()['browser_sessions']['docs_view'],1)
        self.assertEqual(self.call('/growth/forget',{'session_id':payload['session_id']})['status'],204)
        self.assertEqual(self.app.ledger.report()['browser_sessions']['docs_view'],0)
    def test_default_disabled_has_no_event_writes(self):
        self.app=create_app(self.tmp.name,'https://pilot.test')
        self.assertEqual(self.call(payload=event())['status'],503)
        self.assertEqual(self.app.ledger.report()['browser_sessions']['docs_view'],0)
    def test_origin_https_schema_size_and_privacy_signals(self):
        for change,expected in [({'HTTP_ORIGIN':'https://evil.test'},403),
                                ({'wsgi.url_scheme':'http'},426),({'HTTP_HOST':'evil.test'},400),
                                ({'CONTENT_LENGTH':'1025'},413),({'CONTENT_TYPE':'text/plain'},415),
                                ({'HTTP_TRANSFER_ENCODING':'chunked'},400)]:
            self.assertEqual(self.call(payload=event(),**change)['status'],expected)
        for header in ('HTTP_DNT','HTTP_SEC_GPC'):
            self.assertEqual(self.call(payload=event(),**{header:'1'})['status'],204)
        self.assertEqual(self.app.ledger.report()['browser_sessions']['docs_view'],0)
    def test_public_collector_has_no_money_or_admin_endpoint(self):
        for path in ('/growth/payment','/growth/pilot','/growth/report','/.growth-data/growth.sqlite3','/../GROWTH_PLAYBOOK.md'):
            self.assertEqual(self.call(path,{},method='POST')['status'],404)
        self.assertEqual(self.call(payload={'event':'paid_started','amount':1900})['status'],400)
    def test_actual_routes_and_sample_are_truthful_and_no_cookie(self):
        for path in ('/','/assets/tracking.mjs','/assets/site.mjs','/sample-diagnosis.json'):
            result=self.call(path,method='GET')
            self.assertEqual(result['status'],200)
            self.assertNotIn('Set-Cookie',result['headers'])
        page=self.call('/',method='GET')['body']
        self.assertIn(b'https://pilot.test/',page)
        self.assertIn(b'2113612758971436241',page)
        self.assertNotIn(b'__ORIGIN__',page)
        sample=json.loads(self.call('/sample-diagnosis.json',method='GET')['body'])
        self.assertTrue(sample['synthetic'])
        self.assertFalse(sample['changes_applied'])
    def test_edge_limit_storage_failure_and_invalid_json_do_not_fake_success(self):
        with patch.object(self.app.ledger,'edge',return_value=False):
            self.assertEqual(self.call(payload=event())['status'],429)
        with patch.object(self.app.ledger,'event',side_effect=sqlite3.OperationalError('private database error')):
            result=self.call(payload=event())
            self.assertEqual(result['status'],503)
            self.assertNotIn(b'private database',result['body'])
        self.assertEqual(self.call(CONTENT_LENGTH='1',**{'wsgi.input':io.BytesIO(b'{')})['status'],400)
