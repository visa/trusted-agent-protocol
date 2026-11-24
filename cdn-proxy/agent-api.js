const { createProxyMiddleware } = require('http-proxy-middleware');

/**
 * Mount the sample's explicit agent-recognition gateway ahead of public routes.
 * Verify the externally signed path before rewriting it to the backend's /api path.
 */
function mountAgentApi(app, verifySignature, target = 'http://localhost:8000') {
  const proxy = createProxyMiddleware({
    target,
    changeOrigin: true,
    pathRewrite: (path, request) =>
      (request.originalUrl || path).replace(/^\/agent-api(?=\/|\?|$)/i, '/api'),
    logLevel: 'silent',
    onProxyRes(upstream, request) {
      const location = upstream.headers.location;
      if (typeof location !== 'string') return;
      try {
        const backend = new URL(target);
        const destination = new URL(location, new URL(request.url, backend));
        if (destination.origin === backend.origin && /^\/api(?=\/|$)/.test(destination.pathname)) {
          upstream.headers.location = destination.pathname.replace(/^\/api(?=\/|$)/, '/agent-api')
            + destination.search + destination.hash;
        }
      } catch {
        // Leave a non-URL Location value to the client; it is not a backend API redirect.
      }
    },
    onError(error, request, response) {
      if (!response.headersSent) response.writeHead(502, { 'Content-Type': 'text/plain' });
      response.end('The merchant backend is unavailable.');
    },
  });
  app.use('/agent-api', (request, response, next) => {
    const mountedPath = request.url;
    // Express strips the mount prefix. Existing verifiers must see the original target.
    request.url = request.originalUrl;
    const checked = error => {
      request.url = mountedPath;
      next(error);
    };
    try {
      const pending = verifySignature(request, response, checked);
      if (pending && typeof pending.catch === 'function') pending.catch(checked);
    } catch (error) {
      checked(error);
    }
  }, proxy);
}

module.exports = { mountAgentApi };
