const assert = require('node:assert/strict');
const http = require('node:http');
const { once } = require('node:events');
const { test } = require('node:test');
const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const { mountAgentApi } = require('../agent-api');

async function gateway(t, verify, reply) {
  const received = [];
  const backend = http.createServer((request, response) => {
    received.push({ method: request.method, url: request.url });
    if (reply) return reply(request, response);
    response.setHeader('Content-Type', 'application/json');
    response.end(JSON.stringify(received.at(-1)));
  });
  backend.listen(0, '127.0.0.1');
  await once(backend, 'listening');
  const target = `http://127.0.0.1:${backend.address().port}`;
  const app = express();
  // Verification is injected to test the HTTP routing boundary independently of cryptography.
  mountAgentApi(app, verify, target);
  app.use('/api', createProxyMiddleware({ target, logLevel: 'silent' }));
  app.use((request, response) => response.send('storefront'));
  app.use((error, request, response, next) => response.status(500).send('Verification unavailable'));
  const server = app.listen(0, '127.0.0.1');
  await once(server, 'listening');
  t.after(async () => {
    await Promise.all([server, backend].map(instance => new Promise((resolve, reject) => {
      instance.close(error => error ? reject(error) : resolve());
      instance.closeAllConnections();
    })));
  });
  return { received, url: `http://127.0.0.1:${server.address().port}` };
}

test('unsigned and spoofed requests never reach the agent backend', async t => {
  let checks = 0;
  const app = await gateway(t, (request, response) => {
    checks++;
    response.status(403).send('Signature required');
  });
  for (const path of ['/agent-api/products/1', '/agent-api/cart/1/items', '/agent-api/orders']) {
    const response = await fetch(app.url + path, { headers: { 'X-Tap-Verified': 'true' } });
    assert.equal(response.status, 403);
  }
  assert.equal(checks, 3);
  assert.equal(app.received.length, 0);
});

test('verification sees the external URL before the backend path is rewritten', async t => {
  const checked = [];
  const app = await gateway(t, (request, response, next) => {
    checked.push({ url: request.url, originalUrl: request.originalUrl, method: request.method });
    next();
  });
  const path = '/agent-api/products/7?sku=a%2Fb&sku=c+d';
  const response = await fetch(app.url + path, { method: 'POST' });
  assert.equal(response.status, 200);
  assert.deepEqual(checked, [{ url: path, originalUrl: path, method: 'POST' }]);
  assert.deepEqual(await response.json(), { url: '/api/products/7?sku=a%2Fb&sku=c+d', method: 'POST' });
  assert.equal(app.received.length, 1);
});

test('public storefront and API paths retain their existing behavior', async t => {
  let checks = 0;
  const app = await gateway(t, () => { checks++; throw new Error('Unexpected verification'); });
  assert.equal(await (await fetch(app.url + '/')).text(), 'storefront');
  const response = await fetch(app.url + '/api/products/1');
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { method: 'GET', url: '/api/products/1' });
  assert.equal(checks, 0);
});

test('lookalike public paths do not enter the agent gateway', async t => {
  let checks = 0;
  const app = await gateway(t, () => { checks++; });
  assert.equal(await (await fetch(app.url + '/agent-api-public')).text(), 'storefront');
  assert.equal(checks, 0);
});

test('asynchronous verifier failures are handled without forwarding', async t => {
  const app = await gateway(t, async () => { throw new Error('Verification unavailable'); });
  const response = await fetch(app.url + '/agent-api/products/1');
  assert.equal(response.status, 500);
  assert.equal(app.received.length, 0);
});

for (const absolute of [false, true]) {
  test(`backend redirects remain inside the protected gateway (${absolute ? 'absolute' : 'relative'})`, async t => {
    const checked = [];
    const app = await gateway(t, (request, response, next) => {
      checked.push(request.url);
      next();
    }, (request, response) => {
      response.writeHead(307, { Location: `${absolute ? `http://${request.headers.host}` : ''}/api/orders/?page=2` });
      response.end();
    });
    const response = await fetch(app.url + '/agent-api/orders', { redirect: 'manual' });
    assert.equal(response.status, 307);
    assert.equal(response.headers.get('location'), '/agent-api/orders/?page=2');
    assert.deepEqual(checked, ['/agent-api/orders']);
  });
}
