import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from clients.feedrescue_client import FeedRescueClient,FeedRescueAPIError


class MeasuredClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                raw=json.dumps({'data':{'analyzed_products':1,'issues':[{'sku':'private-sku-fixture'}]}}).encode()
                self.send_response(200);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
            do_GET=do_POST
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.url=f'http://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join()

    def test_explicit_callback_receives_metadata_without_key_or_product(self):
        events=[]
        api=FeedRescueClient('private-key-fixture',self.url,on_event=events.append,data_kind='real')
        response=api.call('products/validate',{'processing_consent':True,'product':{'id':'private-sku-fixture','price':'actual-source-fixture'}})
        self.assertEqual(response['data']['analyzed_products'],1)
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]['data_kind'],'real')
        serialized=json.dumps(events)
        for private in ('private-key-fixture','private-sku-fixture','actual-source-fixture'):
            self.assertNotIn(private,serialized)
        api.call('products/validate',{'processing_consent':False,'product':{}})
        self.assertEqual(len(events),1)

    def test_callback_failure_does_not_change_success_or_retry(self):
        def fail(_):raise RuntimeError('synthetic telemetry failure')
        api=FeedRescueClient('private-key-fixture',self.url,on_event=fail)
        self.assertEqual(api.call('products/validate',{'processing_consent':True})['data']['analyzed_products'],1)
