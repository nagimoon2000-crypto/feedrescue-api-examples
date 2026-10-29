"""Dependency-free Python example. Set FEEDRESCUE_API_KEY in your environment."""
import json
import os
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.parse import urlsplit
from urllib.error import HTTPError, URLError

class FeedRescueAPIError(RuntimeError):
    def __init__(self,status,code,request_id=None,retry_after=None):
        self.status,self.code,self.request_id,self.retry_after=status,code,request_id,retry_after
        super().__init__(f'{status or "transport"}: {code}; request_id={request_id or "unavailable"}')

class FeedRescueClient:
    def __init__(self, key, base_url='http://127.0.0.1:8000'):
        url=urlsplit(base_url)
        if not url.hostname or url.username or url.password or url.query or url.fragment or not (url.scheme=='https' or (url.scheme=='http' and url.hostname in {'127.0.0.1','localhost'})):
            raise ValueError('Use HTTPS outside loopback.')
        if not isinstance(key,str) or not key:raise ValueError('Supply a private API key.')
        self.key, self.base_url = key, base_url.rstrip('/')

    def call(self, operation, payload=None):
        allowed={'products/validate','products/batch-validate','products/suggest-fixes','feeds/validate','usage'}
        if operation not in allowed: raise ValueError('Unsupported operation')
        if (operation=='usage' and payload is not None) or (operation!='usage' and not isinstance(payload,dict)):
            raise ValueError('Use no body for usage and a JSON object for processing.')
        req=Request(self.base_url+'/v1/'+operation, data=json.dumps(payload).encode() if payload is not None else None,
                    headers={'X-API-Key':self.key,'Content-Type':'application/json'})
        try:
            class NoRedirect(HTTPRedirectHandler):
                def redirect_request(self,*args,**kwargs): return None
            with build_opener(NoRedirect).open(req,timeout=30) as response:
                try:result=json.load(response)
                except (ValueError,UnicodeError):raise FeedRescueAPIError(response.status,'INVALID_RESPONSE',response.headers.get('X-Request-ID')) from None
                if not isinstance(result,dict) or not isinstance(result.get('data'),dict):
                    raise FeedRescueAPIError(response.status,'INVALID_RESPONSE',response.headers.get('X-Request-ID'))
                return result
        except HTTPError as error:
            # Do not automatically retry billable requests or print credentials/product payloads.
            try:problem=json.load(error)
            except (ValueError,UnicodeError):problem={}
            if not isinstance(problem,dict):problem={}
            detail=problem.get('error');meta=problem.get('meta')
            code=detail.get('code','HTTP_ERROR') if isinstance(detail,dict) else 'HTTP_ERROR'
            request_id=meta.get('request_id') if isinstance(meta,dict) else error.headers.get('X-Request-ID')
            raise FeedRescueAPIError(error.code,code,request_id,error.headers.get('Retry-After')) from None
        except (URLError,TimeoutError):raise FeedRescueAPIError(None,'NETWORK_ERROR') from None

if __name__ == '__main__':
    client=FeedRescueClient(os.environ['FEEDRESCUE_API_KEY'],os.environ.get('FEEDRESCUE_API_URL','http://127.0.0.1:8000'))
    result=client.call('products/validate',{'country':'US','processing_consent':True,'product':{'id':'synthetic-1','title':' Canvas bag ','price':'29.00 USD'}})
    print(json.dumps(result,indent=2))  # Synthetic example only; avoid logging real product responses.
