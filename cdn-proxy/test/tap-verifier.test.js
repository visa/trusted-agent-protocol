const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { test } = require('node:test');
const { serializeInnerList, serializeDictionary } = require('structured-headers');
const { createVerifier } = require('../tap-verifier');

const clock = 1800000000000;
const seconds = clock / 1000;
const keys = crypto.generateKeyPairSync('ed25519');
const key = {
  key_id: 'agent', is_active: 'true', algorithm: 'ed25519',
  public_key: Buffer.from(keys.publicKey.export({ format: 'jwk' }).x, 'base64url').toString('base64'),
};

// Build the wire input independently of the verifier, with known component values.
function signed({ components = ['@authority', '@path'], metadata = {}, omit = [],
  label = 'agent', signedComponents = components, privateKey = keys.privateKey } = {}) {
  const parameters = new Map(Object.entries({
    created: seconds - 1, expires: seconds + 60, keyid: 'agent', alg: 'ed25519',
    nonce: crypto.randomUUID(), tag: 'agent-browser-auth', ...metadata,
  }).filter(([name]) => !omit.includes(name)));
  const input = [components.map(id => [id, new Map()]), parameters];
  const values = {
    '@authority': 'merchant.example', '@path': '/product/1', '@method': 'GET',
    '@scheme': 'https', '@query': '?q=a%2fb+c&a=1&a=2',
    authorization: 'Payment synthetic-fixture', 'content-digest': 'sha-256=:AA==:',
  };
  const base = [...signedComponents.map(id => `"${id}": ${values[id]}`),
    `"@signature-params": ${serializeInnerList(input)}`].join('\n');
  const signature = crypto.sign(null, Buffer.from(base), privateKey);
  return {
    method: 'GET', protocol: 'https', url: '/product/1?q=a%2fb+c&a=1&a=2',
    headers: {
      host: 'merchant.example', authorization: values.authorization,
      'content-digest': values['content-digest'],
      'signature-input': serializeDictionary(new Map([[label, input]])),
      signature: serializeDictionary(new Map([[label, [signature.buffer.slice(
        signature.byteOffset, signature.byteOffset + signature.byteLength), new Map()]]])),
    },
  };
}

function verifier(options = {}) {
  return createVerifier({ resolveKey: async () => key, now: () => clock, ...options });
}

test('accepts the minimum TAP profile with an arbitrary matching label', async () => {
  assert.equal((await verifier()(signed())).label, 'agent');
});

test('canonicalizes header whitespace while preserving signed parameter order and extensions', async () => {
  const request = signed({ metadata: { extension: 'preserve-me' } });
  request.headers['signature-input'] = request.headers['signature-input'].replaceAll(';', '; ');
  assert.equal((await verifier()(request)).keyId, 'agent');
});

test('accepts Visa example Ed25519 spelling without changing its signed bytes', async () => {
  assert.equal((await verifier()(signed({ metadata: { alg: 'Ed25519' } }))).keyId, 'agent');
});

test('accepts another protocol signature alongside one applicable TAP signature', async () => {
  const request = signed();
  request.headers['signature-input'] += ', other=("@authority");tag="other-protocol"';
  request.headers.signature += ', other=:AA==:';
  assert.equal((await verifier()(request)).label, 'agent');
});

for (const name of ['created', 'expires', 'keyid', 'alg', 'nonce', 'tag']) {
  test(`rejects a missing required ${name} parameter`, async () => {
    await assert.rejects(verifier()(signed({ omit: [name] })));
  });
}

for (const components of [['@authority'], ['@path'], ['@authority', '@path', '@path']]) {
  test(`rejects insufficient or duplicate covered components: ${components.join(', ')}`, async () => {
    await assert.rejects(verifier()(signed({ components })));
  });
}

for (const metadata of [
  { created: true }, { created: '1800000000' }, { created: seconds + 1 },
  { expires: seconds }, { expires: seconds + 480 }, { expires: seconds - 1 },
  { nonce: '' }, { keyid: '' }, { tag: 'another-protocol' }, { alg: 'unsupported' },
]) {
  test(`rejects invalid TAP metadata ${JSON.stringify(metadata)}`, async () => {
    await assert.rejects(verifier()(signed({ metadata })));
  });
}

test('accepts a lifetime of exactly 480 seconds', async () => {
  assert.equal((await verifier()(signed({ metadata: { expires: seconds + 479 } }))).keyId, 'agent');
});

test('does not confuse arbitrary header names with supported derived components', async () => {
  const request = signed({ components: ['@authority', '@path', '@future'],
    signedComponents: ['@authority', '@path'] });
  let lookups = 0;
  await assert.rejects(verifier({ resolveKey() { lookups++; return key; } })(request));
  assert.equal(lookups, 0);
});

test('rejects missing signed HTTP fields rather than inventing their value', async () => {
  const request = signed({ components: ['@authority', '@path', 'content-digest'] });
  delete request.headers['content-digest'];
  await assert.rejects(verifier()(request));
});

test('binds every additionally covered request component and header', async () => {
  const request = signed({ components: ['@authority', '@path', '@method', '@scheme', '@query',
    'authorization', 'content-digest'] });
  assert.equal((await verifier()(request)).keyId, 'agent');
  for (const change of [
    { method: 'POST' }, { protocol: 'http' }, { url: '/other?q=a%2fb+c&a=1&a=2' },
    { url: request.url.replace('a=1&a=2', 'a=2&a=1') },
    { url: request.url.replace('%2f', '%2F') },
    { url: request.url.replace('+', '%20') },
    { headers: { ...request.headers, host: 'another.example' } },
    { headers: { ...request.headers, authorization: 'Payment changed' } },
    { headers: { ...request.headers, 'content-digest': 'sha-256=:AQ==:' } },
  ]) await assert.rejects(verifier()({ ...request, ...change }));
});

test('derives the original path before an Express mount rewrites it', async () => {
  const request = signed();
  request.originalUrl = request.url;
  request.url = '/rewritten';
  assert.equal((await verifier()(request)).keyId, 'agent');
});

test('requires matching signature labels and valid Structured Fields', async () => {
  const request = signed();
  for (const headers of [
    { ...request.headers, signature: 'another=:AA==:' },
    { ...request.headers, 'signature-input': request.headers['signature-input'].replace('keyid=', 'keyId=') },
    { ...request.headers, signature: undefined },
  ]) await assert.rejects(verifier()({ ...request, headers }));
});

test('a bad signature cannot consume a legitimate request nonce', async () => {
  const request = signed();
  const check = verifier();
  await assert.rejects(check({ ...request, headers: { ...request.headers, signature: 'agent=:AA==:' } }));
  assert.equal((await check(request)).keyId, 'agent');
  await assert.rejects(check(request), /already been used/);
});

test('concurrent verification claims a nonce at most once', async () => {
  const request = signed();
  const check = verifier();
  const results = await Promise.allSettled([check(request), check(request)]);
  assert.equal(results.filter(result => result.status === 'fulfilled').length, 1);
  assert.equal(results.filter(result => result.status === 'rejected').length, 1);
});

test('scopes nonces to a key and shares them across TAP intents', async () => {
  const other = crypto.generateKeyPairSync('ed25519');
  const otherKey = { ...key, key_id: 'other', public_key: Buffer.from(
    other.publicKey.export({ format: 'jwk' }).x, 'base64url').toString('base64') };
  const check = verifier({ resolveKey: id => id === 'agent' ? key : otherKey });
  const nonce = 'shared-nonce';
  await check(signed({ metadata: { nonce } }));
  await check(signed({ metadata: { nonce, keyid: 'other' }, privateKey: other.privateKey }));
  await assert.rejects(check(signed({ metadata: { nonce, tag: 'agent-payer-auth' } })), /already been used/);
});

test('expired requests stay rejected after old nonce entries can be purged', async () => {
  let current = clock;
  const check = verifier({ now: () => current });
  const request = signed();
  await check(request);
  current += 3601000;
  await assert.rejects(check(request), /current|expired/);
});

test('reports registry outages as unavailable without consuming the nonce', async () => {
  let available = false;
  const request = signed();
  const check = verifier({ resolveKey() { if (!available) throw new Error('Unavailable'); return key; } });
  await assert.rejects(check(request), error => error.status === 503);
  available = true;
  assert.equal((await check(request)).keyId, 'agent');
});

test('rejects a signature that expires during key resolution', async () => {
  let current = clock;
  const check = verifier({ now: () => current, resolveKey() { current += 61000; return key; } });
  await assert.rejects(check(signed()), /expired/);
});

test('rejects unknown, inactive, mismatched, and algorithm-incompatible keys', async () => {
  for (const candidate of [undefined, { ...key, is_active: 'false' },
    { ...key, key_id: 'other' }, { ...key, algorithm: 'rsa-pss-sha256' }]) {
    await assert.rejects(verifier({ resolveKey: () => candidate })(signed()), error => error.status === 403);
  }
});

for (const algorithm of ['ed25519', 'rsa-pss-sha256']) {
  test(`verifies the actual Python sample ${algorithm} signer`, async () => {
    const fixture = JSON.parse(execFileSync(process.env.PYTHON || 'python3', [
      path.join(__dirname, 'python-signer.py'), algorithm, String(seconds - 1),
    ], { encoding: 'utf8' }));
    const request = { method: 'GET', protocol: 'https', url: '/product/1?unsigned=query',
      headers: { host: 'merchant.example', ...fixture.headers } };
    const check = verifier({ resolveKey: () => fixture.key });
    assert.equal((await check(request)).keyId, 'python-agent');
    await assert.rejects(check(request), /already been used/);
  });
}
