const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const source = fs.readFileSync(path.join(__dirname, '../../deploy/cloudfront_viewer_request.js'), 'utf8');
const auth = 'Basic ' + Buffer.from('synthetic:only-for-tests').toString('base64');
const hash = crypto.createHash('sha256').update(auth).digest('hex');

function setup(render = true, now = '2026-11-13T12:00:00Z', cutoff = String(Date.parse('2026-11-14T12:00:00Z'))) {
  const clockValue = Date.parse(now);
  class Clock extends Date {
    static now() { return clockValue; }
    static parse() { throw new Error('Runtime date-string parsing must not be required'); }
  }
  const code = render ? source.replace('__VIEWER_AUTH_SHA256__', hash)
    .replace('__DEMO_EXPIRES_EPOCH_MS__', cutoff) : source;
  const context = { require: name => { assert.equal(name, 'crypto'); return crypto; }, Date: Clock };
  vm.runInNewContext(code, context);
  return context.handler;
}

for (const uri of ['/', '/assets/app.js', '/health', '/api/exploratory/predict/custom']) {
  test(`protects ${uri} before serving cached content or an origin`, () => {
    const response = setup()({ request: { uri, headers: {} } });
    assert.equal(response.statusCode, 401);
    assert.match(response.headers['cache-control'].value, /no-store/);
    assert.match(response.headers['www-authenticate'].value, /^Basic /);
  });
}

test('authenticated requests retain URI, body hash and method but remove viewer credentials', () => {
  const request = { uri: '/api/exploratory/predict/custom', method: 'POST',
    headers: { authorization: { value: auth }, 'x-amz-content-sha256': { value: 'synthetic-hash' } } };
  assert.equal(setup()({ request }), request);
  assert.equal(request.headers.authorization, undefined);
  assert.equal(request.headers['x-amz-content-sha256'].value, 'synthetic-hash');
  assert.equal(request.method, 'POST');
});

for (const value of ['Bearer invalid', 'Basic d3Jvbmc=', '', auth + ' ']) {
  test('invalid credentials receive the same denial without echoing the input', () => {
    const response = setup()({ request: { headers: { authorization: { value } } } });
    assert.equal(response.statusCode, 401);
    assert.equal(response.body, 'Authentication required.');
  });
}

test('duplicate authorization values are rejected', () => {
  assert.equal(setup()({ request: { headers: { authorization: {
    value: auth, multiValue: [{ value: auth }, { value: auth }],
  } } } }).statusCode, 401);
});

test('unrendered configuration denies access', () => {
  assert.equal(setup(false)({ request: { headers: { authorization: { value: auth } } } }).statusCode, 503);
});

test('cutoff denies even otherwise authenticated access', () => {
  assert.equal(setup(true, '2026-11-14T12:00:00Z')({
    request: { headers: { authorization: { value: auth } } },
  }).statusCode, 503);
});

for (const cutoff of ['invalid', '', '0', '-1', 'Infinity']) {
  test(`invalid numeric cutoff ${JSON.stringify(cutoff)} denies access`, () => {
    assert.equal(setup(true, '2026-11-13T12:00:00Z', cutoff)({
      request: { headers: { authorization: { value: auth } } },
    }).statusCode, 503);
  });
}

test('authenticated access works immediately before the cutoff', () => {
  const request = { uri: '/health', headers: { authorization: { value: auth } } };
  assert.equal(setup(true, '2026-11-14T11:59:59.999Z')({ request }), request);
});
