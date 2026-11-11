import io
import tempfile
import unittest
from growth.deployment import mount


class DeploymentTests(unittest.TestCase):
    def test_mount_preserves_existing_routes_and_rewrites_owned_assets(self):
        calls=[]
        def existing(env,start):
            calls.append(env['PATH_INFO']); start('200 OK',[]); return [b'original']
        with tempfile.TemporaryDirectory() as state:
            app=mount(existing,state,'https://pilot.test')
            def request(path,method='GET'):
                response={}
                def start(status,headers): response.update(status=status,headers=dict(headers))
                response['body']=b''.join(app({'PATH_INFO':path,'REQUEST_METHOD':method,
                    'HTTP_HOST':'pilot.test','wsgi.url_scheme':'https','wsgi.input':io.BytesIO()},start))
                return response
            for path in ('/','/v1/products/validate','/assets/site.mjs','/integrations-other'):
                self.assertEqual(request(path)['body'],b'original')
            page=request('/integrations/')['body']
            self.assertIn(b'href="/integrations/assets/site.css"',page)
            self.assertIn(b'https://pilot.test/integrations/',page)
            self.assertIn(b'https://www.upwork.com/',page)
            seller=request('/integrations/file-diagnosis')['body']
            self.assertIn(b'https://pilot.test/integrations/file-diagnosis',seller)
            self.assertIn(b'/integrations/assets/seller.mjs',seller)
            self.assertIn(b'https://www.upwork.com/services/product/2113612758971436241',seller)
            self.assertEqual(request('/integrations/assets/seller.mjs')['status'],'200 OK')
            js=request('/integrations/assets/site.mjs')['body']
            self.assertIn(b"'/integrations/growth/config'",js)
            tracker=request('/integrations/assets/tracking.mjs')['body']
            self.assertIn(b"'/integrations/growth/events'",tracker)
            self.assertEqual(request('/integrations/growth/config')['body'],b'{"enabled": false, "retention_days": 30}')
            self.assertEqual(request('/integrations/', 'HEAD')['body'],b'')
            self.assertEqual(len(calls),4)

    def test_invalid_prefix_or_relative_state_fails_before_mount(self):
        for prefix in ('/','/v1/x','//host','/X'):
            with self.assertRaises(ValueError): mount(None,'/private/state','https://pilot.test',prefix)
        with self.assertRaises(ValueError): mount(None,'relative','https://pilot.test')
