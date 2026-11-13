"""Minimal fail-closed ASGI controls for the exploratory demo API.

Not a replacement for upstream WAF / rate limiting / authentication. No
patient data, request body, prediction or user identifier is logged or stored.
"""
from __future__ import annotations

from urllib.parse import urlsplit
import os

from starlette.responses import JSONResponse

PREDICTION_PREFIX = '/api/exploratory/predict/custom'
MAX_BODY_BYTES = 8192


class UnsafeConfiguration(ValueError):
    pass


def deployment_config(env=None) -> dict:
    """Local mode by default; production requires explicit exact hosts/origins.

    No wildcard hosts/CORS and no credentialed CORS. Does not configure public
    ingress or guarantee non-billable AWS use. No environment secrets in output.
    """
    env = os.environ if env is None else env
    stage = env.get('FYP_STAGE', 'local')
    if stage not in ('local', 'production'):
        raise UnsafeConfiguration('FYP_STAGE must be local or production')
    if stage == 'local':
        if env.get('FYP_ALLOWED_HOSTS'):
            raise UnsafeConfiguration('Custom hosts require explicit production stage')
        return {'stage':'local','hosts':['localhost','127.0.0.1','testserver'],
                'docs_enabled': True}
    raw_hosts = env.get('FYP_ALLOWED_HOSTS', '')
    raw_origins = env.get('FYP_CORS_ORIGINS', '')
    hosts = [h.strip() for h in raw_hosts.split(',')]
    origins = [o.strip() for o in raw_origins.split(',')]
    if not hosts or any(not h for h in hosts) or len(set(hosts)) != len(hosts):
        raise UnsafeConfiguration('Production requires explicit FYP_ALLOWED_HOSTS')
    for host in hosts:
        if ('*' in host or '://' in host or '/' in host or '@' in host or ':' in host
                or host.lower() != host or host in ('.','..') or '.' not in host
                or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789.-' for c in host)
                or any(not label or label.startswith('-') or label.endswith('-') for label in host.split('.'))):
            raise UnsafeConfiguration('Only exact DNS hostnames allowed')
    if not origins or any(not o for o in origins):
        raise UnsafeConfiguration('Production requires HTTPS FYP_CORS_ORIGINS')
    for origin in origins:
        try:
            u = urlsplit(origin)
            if (u.scheme != 'https' or not u.netloc or not u.hostname or
                    u.username or u.password or u.path or u.query or u.fragment or
                    u.port not in (None,443) or '*' in origin):
                raise UnsafeConfiguration('Production CORS must use exact HTTPS origins')
        except ValueError as exc:
            raise UnsafeConfiguration('Invalid production CORS origin') from exc
    return {'stage':'production','hosts':hosts,'docs_enabled':False}


class BodyLimitMiddleware:
    """Limit actual POST body bytes, even for requests without Content-Length.

    Buffers *at most* 8192 bytes (plus one received frame) before calling the
    application. This is suitable for small JSON records, not file uploads.
    """
    def __init__(self, app, max_body_bytes=MAX_BODY_BYTES):
        self.app=app
        if max_body_bytes < 128 or max_body_bytes > 65536:
            raise ValueError('Unsupported request body limit')
        self.max_body_bytes=max_body_bytes

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope.get('method') != 'POST' or not scope.get('path','').startswith(PREDICTION_PREFIX):
            return await self.app(scope,receive,send)
        headers={}
        for k,v in scope.get('headers',[]):
            key=k.lower()
            if key in (b'content-length',b'content-type') and key in headers:
                return await self._reject(scope,receive,send,400,'Invalid request headers')
            headers[key]=v
        typ=headers.get(b'content-type',b'').split(b';',1)[0].strip().lower()
        if typ != b'application/json':
            return await self._reject(scope,receive,send,415,'JSON required')
        if b'content-length' in headers:
            raw=headers[b'content-length']
            if not raw.isdigit():
                return await self._reject(scope,receive,send,400,'Invalid Content-Length')
            if int(raw)>self.max_body_bytes:
                return await self._reject(scope,receive,send,413,'Request body too large')
        parts=[]
        size=0
        while True:
            message=await receive()
            if message['type']=='http.disconnect':
                return
            if message['type']!='http.request':
                return await self._reject(scope,receive,send,400,'Invalid request frame')
            part=message.get('body',b'')
            size+=len(part)
            if size>self.max_body_bytes:
                return await self._reject(scope,receive,send,413,'Request body too large')
            parts.append(part)
            if not message.get('more_body',False):
                break
        body=b''.join(parts)
        called=False
        async def replay():
            nonlocal called
            if not called:
                called=True
                return {'type':'http.request','body':body,'more_body':False}
            return {'type':'http.disconnect'}
        return await self.app(scope,replay,send)

    async def _reject(self,scope,receive,send,status,detail):
        response=JSONResponse({'detail':detail},status_code=status,headers={
            'Cache-Control':'private, no-store','Pragma':'no-cache',
            'X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer',
            'X-Frame-Options':'DENY',
        })
        return await response(scope,receive,send)
