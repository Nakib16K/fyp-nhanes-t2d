const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');
const ts = require('typescript');

const file = path.join(__dirname, '../src/utils/api.ts');
const source = fs.readFileSync(file, 'utf8')
  .replace('import.meta.env.VITE_API_URL', '"https://demo.example.com"');
const code = ts.transpileModule(source, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
}).outputText;

function setup(options = {}) {
  const calls = [];
  const context = {
    exports: {}, Headers, TextEncoder, Uint8Array,
    crypto: Object.hasOwn(options, 'crypto') ? options.crypto : crypto.webcrypto,
    fetch: async (url, init) => {
      calls.push({ url, init });
      return options.response || { ok: true, json: async () => ({ accepted: true }) };
    },
  };
  vm.runInNewContext(code, context, { filename: file });
  return { client: context.exports, calls };
}

test('prediction sends the original JSON bytes and their SHA-256 once', async () => {
  const { client, calls } = setup();
  const input = { age_years: 45, note: 'synthetic café 測試' };
  await client.api.predictCustom(input);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, 'https://demo.example.com/api/exploratory/predict/custom');
  assert.equal(calls[0].init.body, JSON.stringify(input));
  assert.equal(calls[0].init.headers.get('x-amz-content-sha256'),
    crypto.createHash('sha256').update(calls[0].init.body, 'utf8').digest('hex'));
});

test('local explanation uses the same signing path', async () => {
  const { client, calls } = setup();
  await client.api.getLocalShap('XGB', { age_years: 45 });
  assert.match(calls[0].url, /\/shap\/XGB$/);
  assert.match(calls[0].init.headers.get('x-amz-content-sha256'), /^[a-f0-9]{64}$/);
});

for (const format of ['object', 'tuples', 'Headers']) {
  test(`preserves ${format} caller headers and replaces an incorrect body hash`, async () => {
    const { client, calls } = setup();
    const values = { 'X-Demo': 'synthetic', 'x-amz-content-sha256': 'incorrect' };
    const headers = format === 'tuples' ? Object.entries(values) : format === 'Headers' ? new Headers(values) : values;
    await client.fetchJSON('/test', { method: 'post', headers, body: '{}' });
    assert.equal(calls[0].init.headers.get('x-demo'), 'synthetic');
    assert.equal(calls[0].init.headers.get('content-type'), 'application/json');
    assert.equal(calls[0].init.headers.get('x-amz-content-sha256'),
      crypto.createHash('sha256').update('{}').digest('hex'));
    assert.equal(new Headers(headers).get('x-amz-content-sha256'), 'incorrect');
  });
}

test('read requests do not require browser crypto', async () => {
  const { client, calls } = setup({ crypto: undefined });
  await client.api.healthCheck();
  assert.equal(calls[0].init.headers.has('x-amz-content-sha256'), false);
});

test('missing secure crypto stops a prediction before sending', async () => {
  const { client, calls } = setup({ crypto: undefined });
  await assert.rejects(client.api.predictCustom({ age_years: 45 }), /HTTPS or localhost/);
  assert.equal(calls.length, 0);
});

test('non-string body is rejected before sending an unverified payload', async () => {
  const { client, calls } = setup();
  await assert.rejects(client.fetchJSON('/test', { method: 'POST', body: new Uint8Array([1]) }), /string body/);
  assert.equal(calls.length, 0);
});

test('a failed response is reported without retrying the request', async () => {
  const { client, calls } = setup({ response: { ok: false, status: 503, statusText: 'Unavailable' } });
  await assert.rejects(client.api.predictCustom({ age_years: 45 }), /503 Unavailable/);
  assert.equal(calls.length, 1);
});
