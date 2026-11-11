"""Mount the optional landing without replacing an existing WSGI application."""
import re
from pathlib import Path
from .server import create_app


def mount(existing, state_dir, origin, prefix='/integrations', analytics=False):
    if not re.fullmatch(r'/[a-z][a-z0-9-]*', prefix):
        raise ValueError('Use one lowercase, dedicated path segment.')
    if not Path(state_dir).is_absolute():
        raise ValueError('Production state needs an absolute private path.')
    growth = create_app(state_dir, origin, analytics=analytics)

    def application(env, start):
        path = env.get('PATH_INFO', '')
        if path != prefix and not path.startswith(prefix + '/'):
            return existing(env, start)
        scoped = dict(env, PATH_INFO=path[len(prefix):] or '/')
        captured = {}
        def capture(status, headers, exc_info=None):
            captured.update(status=status, headers=headers)
        iterable = growth(scoped, capture)
        try:
            body = b''.join(iterable)
        finally:
            if hasattr(iterable, 'close'): iterable.close()
        headers = dict(captured['headers'])
        kind = headers.get('Content-Type', '')
        if kind.startswith(('text/html', 'text/javascript')):
            # Rewrite only our static root-relative URLs, never external links.
            for quote in (b'"', b"'"):
                body = body.replace(quote+b'/', quote+prefix.encode()+b'/')
            if kind.startswith('text/html'):
                marker = '<link rel="canonical" href="' + origin.rstrip('/') + '/'
                body = body.replace(marker.encode(),
                                    (marker[:-1]+prefix+'/').encode())
            # HEAD has no body; preserve the transformed GET length instead.
            if env.get('REQUEST_METHOD') != 'HEAD': headers['Content-Length'] = str(len(body))
            else: headers.pop('Content-Length', None)
        start(captured['status'], list(headers.items()))
        return [body]
    return application
