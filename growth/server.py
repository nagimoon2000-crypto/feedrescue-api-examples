"""Optional same-origin, opt-in collector + a static developer landing page.

Run locally: python -m growth.server --analytics --port 8021 --state .growth-data
Production: explicit HTTPS origin + private state directory; see docs/growth.md.
This server never proxies product payloads, keys or payment operations.
"""
import argparse
import io
import json
import os
from html import escape
from pathlib import Path
from socketserver import ThreadingMixIn
from urllib.parse import urlsplit
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler, make_server
from .ledger import GrowthLedger

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    '/file-diagnosis': ('growth/web/file-diagnosis.html','text/html; charset=utf-8'),
    '/assets/seller.mjs': ('growth/web/seller.mjs','text/javascript; charset=utf-8'),
    '/': ('growth/web/index.html','text/html; charset=utf-8'),
    '/assets/site.css': ('growth/web/site.css','text/css; charset=utf-8'),
    '/assets/site.mjs': ('growth/web/site.mjs','text/javascript; charset=utf-8'),
    '/assets/tracking.mjs': ('growth/web/tracking.mjs','text/javascript; charset=utf-8'),
    '/sample-diagnosis.json': ('samples/sample-diagnosis.json','application/json'),
}


def create_app(state_dir, origin, analytics=False, allow_loopback_http=False):
    url = urlsplit(origin)
    loopback = url.hostname in {'127.0.0.1','localhost'} and allow_loopback_http
    if url.username or url.password or url.query or url.fragment or url.path not in ('','/') or not url.hostname:
        raise ValueError('Configure one origin, never credentials or a path.')
    if url.scheme != 'https' and not (url.scheme=='http' and loopback):
        raise ValueError('HTTPS is required outside explicit local preview.')
    origin = origin.rstrip('/')
    state = Path(state_dir).resolve()
    if state == ROOT or ROOT in state.parents:
        # Runtime state is allowed only in an ignored local preview folder.
        if not loopback or state != ROOT/'.growth-data':
            raise ValueError('Keep production state outside the repository/document root.')
    ledger = GrowthLedger(state/'growth.sqlite3')

    def app(env, start):
        def respond(status, body=b'', kind='application/json', extra=None):
            if isinstance(body,dict): body=json.dumps(body).encode()
            headers={'Content-Type':kind, 'Content-Length':str(len(body)), 'Cache-Control':'no-store',
                     'X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','X-Frame-Options':'DENY',
                     'Content-Security-Policy':"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
                     'Permissions-Policy':'camera=(), microphone=(), geolocation=()'}
            if url.scheme=='https': headers['Strict-Transport-Security']='max-age=31536000'
            if path.startswith('/growth/'): headers['X-Robots-Tag']='noindex, nofollow'
            headers.update(extra or {})
            start(status,list(headers.items()))
            return [b'' if env.get('REQUEST_METHOD')=='HEAD' else body]
        path, method = env.get('PATH_INFO',''), env.get('REQUEST_METHOD','GET')
        if env.get('HTTP_HOST') != url.netloc: return respond('400 Bad Request',{'error':'unexpected_host'})
        if env.get('wsgi.url_scheme') != url.scheme: return respond('426 Upgrade Required',{'error':'direct_https_required'})
        if path == '/growth/config' and method=='GET':
            return respond('200 OK',{'enabled':analytics,'retention_days':30})
        if path in FILES:
            if method not in {'GET','HEAD'}: return respond('405 Method Not Allowed',extra={'Allow':'GET, HEAD'})
            name, kind = FILES[path]
            body=(ROOT/name).read_bytes()
            if kind.startswith('text/html'):body=body.replace(b'__ORIGIN__',escape(origin,quote=True).encode())
            return respond('200 OK',body,kind,{'Cache-Control':'no-cache'})
        if path not in {'/growth/events','/growth/forget'}: return respond('404 Not Found')
        if not analytics: return respond('503 Service Unavailable',{'error':'measurement_not_enabled'})
        if method!='POST': return respond('405 Method Not Allowed',extra={'Allow':'POST'})
        if env.get('HTTP_ORIGIN')!=origin: return respond('403 Forbidden',{'error':'same_origin_required'})
        if env.get('HTTP_SEC_GPC')=='1' or env.get('HTTP_DNT')=='1':
            # Deletion still works for an existing consented session.
            if path!='/growth/forget': return respond('204 No Content')
        if env.get('HTTP_TRANSFER_ENCODING'): return respond('400 Bad Request')
        if env.get('CONTENT_TYPE','').split(';')[0].strip().lower()!='application/json':
            return respond('415 Unsupported Media Type')
        try:
            size=int(env.get('CONTENT_LENGTH','0'))
            if not 0<size<=1024: return respond('413 Payload Too Large')
            if not ledger.edge(): return respond('429 Too Many Requests',extra={'Retry-After':'60'})
            raw=env['wsgi.input'].read(size)
            if len(raw)!=size: return respond('400 Bad Request')
            payload=json.loads(raw)
            if path=='/growth/events': ledger.event(payload)
            else:
                if not isinstance(payload,dict) or set(payload)!={'session_id'}: raise ValueError('Unexpected fields.')
                ledger.forget(payload['session_id'])
            return respond('204 No Content')
        except (ValueError, UnicodeError, TypeError, KeyError):
            return respond('400 Bad Request',{'error':'invalid_measurement_schema'})
        except OverflowError:
            return respond('503 Service Unavailable',{'error':'measurement_storage_limit'})
        except Exception:
            return respond('503 Service Unavailable',{'error':'measurement_unavailable'})
    app.ledger=ledger
    return app


class PreviewServer(ThreadingMixIn, WSGIServer):
    daemon_threads=True
    def get_request(self):
        conn,address=super().get_request()
        conn.settimeout(10)
        return conn,address


class RedactedHandler(WSGIRequestHandler):
    def log_message(self,*args): pass  # No path/query/body logs in this preview.


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8021)
    parser.add_argument('--state',type=Path,default=ROOT/'.growth-data')
    parser.add_argument('--analytics',action='store_true',help='Enable collector; visitor consent is still required')
    args=parser.parse_args()
    origin=f'http://127.0.0.1:{args.port}'
    app=create_app(args.state,origin,args.analytics,allow_loopback_http=True)
    print('Local URL: '+origin,flush=True)
    with make_server('127.0.0.1',args.port,app,server_class=PreviewServer,handler_class=RedactedHandler) as server:
        server.serve_forever()


if __name__=='__main__': main()
