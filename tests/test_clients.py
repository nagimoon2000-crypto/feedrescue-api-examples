"""Offline SDK smoke/security checks against local synthetic HTTP servers only."""
import json
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from clients.feedrescue_client import FeedRescueClient,FeedRescueAPIError

class ClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class Destination(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                self.server.hits+=1;self.send_response(200);self.end_headers();self.wfile.write(b'{}')
        cls.destination=ThreadingHTTPServer(('127.0.0.1',0),Destination);cls.destination.hits=0
        cls.destination_thread=threading.Thread(target=cls.destination.serve_forever,daemon=True);cls.destination_thread.start()
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                mode=self.server.mode;status=200
                body={'data':{'synthetic':True},'meta':{'request_id':'synthetic-request'}}
                if mode=='limit':status=429;body={'error':{'code':'RATE_LIMITED','message':'do not echo product/secret text'},'meta':{'request_id':'synthetic-request'}}
                if mode=='html-error':status=503
                if mode=='redirect':status=302
                raw=b'<html>synthetic hosting page</html>' if mode in {'html','html-error','redirect'} else json.dumps(body).encode()
                self.send_response(status);self.send_header('Content-Length',str(len(raw)))
                self.send_header('Content-Type','text/html' if mode.startswith('html') else 'application/json')
                self.send_header('X-Request-ID','synthetic-header-request')
                if status==429:self.send_header('Retry-After','60')
                if status==302:self.send_header('Location',f'http://127.0.0.1:{ClientTests.destination.server_port}/capture')
                self.end_headers();self.wfile.write(raw)
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls):
        for server,thread in [(cls.server,cls.thread),(cls.destination,cls.destination_thread)]:server.shutdown();server.server_close();thread.join()
    def setUp(self):self.server.mode='ok';self.client=FeedRescueClient('synthetic-private-test-key',self.base)
    def test_python_success(self):self.assertTrue(self.client.call('usage')['data']['synthetic'])
    def test_python_rate_limit_preserves_metadata_and_no_secret(self):
        self.server.mode='limit'
        with self.assertRaises(FeedRescueAPIError) as caught:self.client.call('usage')
        error=caught.exception;self.assertEqual(error.status,429);self.assertEqual(error.code,'RATE_LIMITED');self.assertEqual(error.retry_after,'60')
        self.assertNotIn('synthetic-private-test-key',str(error));self.assertNotIn('echo product',str(error))
    def test_python_non_json_hosting_responses(self):
        for mode,expected in [('html','INVALID_RESPONSE'),('html-error','HTTP_ERROR')]:
            self.server.mode=mode
            with self.assertRaises(FeedRescueAPIError) as caught:self.client.call('usage')
            self.assertEqual(caught.exception.code,expected)
    def test_python_redirect_does_not_forward_key(self):
        self.server.mode='redirect';before=self.destination.hits
        with self.assertRaises(FeedRescueAPIError):self.client.call('usage')
        self.assertEqual(self.destination.hits,before)
    def test_invalid_usage_method_and_credential_url(self):
        with self.assertRaises(ValueError):self.client.call('usage',{})
        for url in ['https://user:password@example.com','http://example.com','https://example.com?key=value']:
            with self.assertRaises(ValueError):FeedRescueClient('synthetic-key',url)
    def test_javascript_success_and_failures_real_http(self):
        script="""import {FeedRescueClient,FeedRescueAPIError} from './clients/feedrescue-client.mjs';
const api=new FeedRescueClient('synthetic-private-test-key',process.argv[1]);
const expected=process.argv[2];
try { const r=await api.call('usage');if(expected!=='ok'||!r.data.synthetic)process.exit(2); }
catch(e) { if(!(e instanceof FeedRescueAPIError)||e.code!==expected||e.message.includes('synthetic-private-test-key'))process.exit(3); }
"""
        for mode,expected in [('ok','ok'),('limit','RATE_LIMITED'),('html','INVALID_RESPONSE'),('html-error','INVALID_RESPONSE'),('redirect','NETWORK_ERROR')]:
            self.server.mode=mode;before=self.destination.hits
            result=subprocess.run(['node','--input-type=module','-e',script,self.base,expected],cwd=ROOT,capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,f'JavaScript {mode} check failed: {result.stderr}');self.assertEqual(self.destination.hits,before)

if __name__=='__main__':unittest.main()
