"""API regression tests with mocked model registry; no real patient/model files."""
import asyncio
import ast
import json
from pathlib import Path

import api.main as api
import pytest
from src.privacy import ConfigurationError, allowed_origins
from src.security import BodyLimitMiddleware, UnsafeConfiguration, deployment_config




def test_refuse_unknown_host(client):
    r = client.get('/health', headers={'host': 'hostile.example'})
    assert r.status_code == 400


def test_local_preflight_accepts_signed_json_headers(client):
    r = client.options('/api/exploratory/predict/custom', headers={
        'origin': 'http://localhost:5173',
        'access-control-request-method': 'POST',
        'access-control-request-headers': 'content-type,x-amz-content-sha256',
    })
    assert r.status_code == 200
    assert r.headers['access-control-allow-origin'] == 'http://localhost:5173'
    assert 'x-amz-content-sha256' in r.headers['access-control-allow-headers'].lower()


def test_signed_header_does_not_relax_origin_allowlist(client):
    r = client.options('/api/exploratory/predict/custom', headers={
        'origin': 'https://untrusted.example',
        'access-control-request-method': 'POST',
        'access-control-request-headers': 'content-type,x-amz-content-sha256',
    })
    assert r.status_code == 400
    assert 'access-control-allow-origin' not in r.headers


def test_prediction_json_required(client):
    r = client.post('/api/exploratory/predict/custom', content='x', headers={'content-type': 'text/plain'})
    assert r.status_code == 415
    assert r.headers['cache-control'] == 'private, no-store'


def test_prediction_too_large(client):
    r = client.post('/api/exploratory/predict/custom', json={'filler': 'x' * 9000})
    assert r.status_code == 413
    assert 'filler' not in r.text


@pytest.mark.parametrize('size,status', [(8192, 422), (8193, 413)])
def test_api_body_limit_at_the_exact_boundary(client, size, status):
    # The empty object reaches schema validation at the limit, but not above it.
    response = client.post('/api/exploratory/predict/custom',
                           content=b'{}' + b' ' * (size-2),
                           headers={'content-type': 'application/json'})
    assert response.status_code == status


def test_normal_payload_uses_existing_endpoint(client, patient_input):
    # Models absent: a syntactically valid request reaches the normal
    # unavailable-model check. No new threshold or inference path introduced.
    api.ml_registry.update({'models': {}, 'metrics': [], 'thresholds': {}, 'latest_run_dir': None, 'active_run_id': None})
    r = client.post('/api/exploratory/predict/custom', json=patient_input)
    assert r.status_code == 503
    assert r.headers['x-content-type-options'] == 'nosniff'
    assert r.headers['referrer-policy'] == 'no-referrer'


@pytest.mark.parametrize('endpoint', [ '/api/models/UNKNOWN/shap/global', '/api/models/UNKNOWN/interpretation'])
def test_model_path_name_allowlisted(client, endpoint):
    r = client.get(endpoint)
    assert r.status_code == 404
    assert r.json()['detail'] == 'Unknown model.'


def test_development_and_production_configuration():
    assert deployment_config({}) == {
        'stage': 'local', 'hosts': ['localhost', '127.0.0.1', 'testserver'],
        'docs_enabled': True,
    }
    config = deployment_config({
        'FYP_STAGE': 'production', 'FYP_ALLOWED_HOSTS': 'demo.example.com,api.example.com',
        'FYP_CORS_ORIGINS': 'https://demo.example.com',
    })
    assert config == {'stage': 'production', 'hosts': ['demo.example.com', 'api.example.com'], 'docs_enabled': False}


@pytest.mark.parametrize('env', [
    {'FYP_STAGE': 'staging'},
    {'FYP_ALLOWED_HOSTS': 'demo.example.com'},
    {'FYP_STAGE': 'production'},
    {'FYP_STAGE': 'production', 'FYP_ALLOWED_HOSTS': 'demo.example.com'},
])
def test_incomplete_or_implicit_production_configuration_is_rejected(env):
    with pytest.raises(UnsafeConfiguration):
        deployment_config(env)


@pytest.mark.parametrize('host', [
    '*', '*.example.com', 'https://demo.example.com', 'demo.example.com/path',
    'user@example.com', 'demo.example.com:443', 'Demo.example.com',
    '-demo.example.com', 'demo..example.com', 'demo.example.com,demo.example.com', '',
])
def test_production_hosts_must_be_explicit_dns_names(host):
    with pytest.raises(UnsafeConfiguration):
        deployment_config({'FYP_STAGE': 'production', 'FYP_ALLOWED_HOSTS': host,
                           'FYP_CORS_ORIGINS': 'https://demo.example.com'})


@pytest.mark.parametrize('origin', [
    '', '*', 'http://demo.example.com', 'https://*.example.com',
    'https://user:password@demo.example.com', 'https://demo.example.com/path',
    'https://demo.example.com?x=1', 'https://demo.example.com#fragment',
    'https://demo.example.com:8443', 'https://demo.example.com:invalid',
])
def test_production_origins_must_be_exact_https_origins(origin):
    with pytest.raises(UnsafeConfiguration):
        deployment_config({'FYP_STAGE': 'production', 'FYP_ALLOWED_HOSTS': 'demo.example.com',
                           'FYP_CORS_ORIGINS': origin})


def test_origin_parser_preserves_exact_order_and_removes_duplicates():
    assert allowed_origins(None) == ['http://localhost:5173', 'http://127.0.0.1:5173']
    assert allowed_origins('https://demo.example.com, https://api.example.com,https://demo.example.com') == [
        'https://demo.example.com', 'https://api.example.com',
    ]


@pytest.mark.parametrize('origin', [
    '', 'https://demo.example.com,', '*', 'demo.example.com',
    'http://demo.example.com', 'https://user:password@demo.example.com',
    'https://demo.example.com/path', 'https://demo.example.com?x=1',
    'https://demo.example.com#fragment',
])
def test_origin_parser_rejects_unsafe_configuration(origin):
    with pytest.raises(ConfigurationError):
        allowed_origins(origin)


def _body_request(chunks, headers=None):
    observed = {'app_called': False, 'body': None}
    replies = []
    messages = [{'type': 'http.request', 'body': chunk, 'more_body': i < len(chunks)-1}
                for i, chunk in enumerate(chunks)]

    async def receive():
        return messages.pop(0) if messages else {'type': 'http.disconnect'}

    async def send(message):
        replies.append(message)

    async def application(scope, receive, send):
        observed['app_called'] = True
        message = await receive()
        observed['body'] = message['body']
        assert message['more_body'] is False
        assert (await receive())['type'] == 'http.disconnect'
        await send({'type': 'http.response.start', 'status': 200, 'headers': []})
        await send({'type': 'http.response.body', 'body': b'ok'})

    scope = {'type': 'http', 'method': 'POST', 'path': '/api/exploratory/predict/custom',
             'headers': headers if headers is not None else [(b'content-type', b'application/json')]}
    asyncio.run(BodyLimitMiddleware(application, max_body_bytes=128)(scope, receive, send))
    return observed, replies


@pytest.mark.parametrize('chunks', [[b'{}'], [b'a' * 64, b'b' * 64]])
def test_body_without_content_length_is_replayed_once_within_limit(chunks):
    observed, replies = _body_request(chunks)
    assert observed == {'app_called': True, 'body': b''.join(chunks)}
    assert replies[0]['status'] == 200


@pytest.mark.parametrize('headers', [
    [(b'content-type', b'application/json')],
    [(b'content-type', b'application/json'), (b'content-length', b'2')],
])
def test_actual_streamed_bytes_enforce_limit_even_with_missing_or_small_length(headers):
    observed, replies = _body_request([b'a' * 64, b'b' * 65], headers)
    assert observed['app_called'] is False
    assert replies[0]['status'] == 413
    assert dict(replies[0]['headers'])[b'cache-control'] == b'private, no-store'
    assert json.loads(replies[1]['body']) == {'detail': 'Request body too large'}


@pytest.mark.parametrize('duplicate', [
    [(b'content-length', b'2'), (b'Content-Length', b'2')],
    [(b'Content-Type', b'application/json')],
])
def test_duplicate_body_headers_are_rejected_before_application(duplicate):
    observed, replies = _body_request([b'{}'], [(b'content-type', b'application/json'), *duplicate])
    assert observed['app_called'] is False
    assert replies[0]['status'] == 400


def test_script_entrypoint_binds_to_loopback():
    source = Path(__file__).resolve().parents[1] / 'api/main.py'
    calls = [n for n in ast.walk(ast.parse(source.read_text(encoding='utf-8')))
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and isinstance(n.func.value, ast.Name) and n.func.value.id == 'uvicorn'
             and n.func.attr == 'run']
    assert len(calls) == 1
    host = next(k.value for k in calls[0].keywords if k.arg == 'host')
    assert ast.literal_eval(host) == '127.0.0.1'
