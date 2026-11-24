/* © 2025 Visa.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

require('dotenv').config();
const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const { createVerifier, VerificationError } = require('./tap-verifier');
const axios = require('axios');


// HTML escaping function to prevent XSS
function escapeHtml(unsafe) {
  if (typeof unsafe !== 'string') {
    return String(unsafe);
  }
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Safe HTML error response function
function sendErrorResponse(res, statusCode, title, message, details = null) {
  const safeTitle = escapeHtml(title);
  const safeMessage = escapeHtml(message);
  const safeDetails = details ? escapeHtml(details) : null;
  
  const html = `
    <!DOCTYPE html>
    <html lang="en">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>${safeTitle}</title>
        <style>
          body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background-color: #f8f9fa; }
          .container { max-width: 600px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
          h1 { color: #dc3545; margin-bottom: 20px; }
          p { color: #6c757d; line-height: 1.5; margin-bottom: 15px; }
          .details { background-color: #f8f9fa; padding: 15px; border-radius: 4px; font-family: monospace; color: #495057; }
        </style>
      </head>
      <body>
        <div class="container">
          <h1>${safeTitle}</h1>
          <p>${safeMessage}</p>
          ${safeDetails ? `<div class="details">Details: ${safeDetails}</div>` : ''}
        </div>
      </body>
    </html>
  `;
  
  res.status(statusCode).send(html);
}

// Input validation functions
function validateKeyId(keyId) {
  // Key IDs should be alphanumeric with limited special characters
  if (typeof keyId !== 'string' || keyId.length > 100 || !/^[a-zA-Z0-9._-]+$/.test(keyId)) {
    return false;
  }
  return true;
}

function sanitizeLogOutput(input) {
  // Sanitize data for logging to prevent log injection
  if (input === null || input === undefined) {
    return '[null]';
  }
  if (typeof input !== 'string') {
    input = String(input);
  }
  // Remove control characters, newlines, tabs that could be used for log injection
  // Also limit length to prevent log flooding
  return input
    .replace(/[\x00-\x1F\x7F-\x9F]/g, '') // Remove control characters
    .replace(/[\r\n\t]/g, ' ') // Replace line breaks with spaces
    .replace(/\s+/g, ' ') // Collapse multiple spaces
    .trim()
    .substring(0, 200); // Limit length
}

const app = express();
const PORT = process.env.PORT || 3001; // Proxy runs on 3001, React on 3000

// Security middleware - Add CSP and other security headers
app.use((req, res, next) => {
  // Content Security Policy to prevent XSS (allow external images for product images)
  res.setHeader('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https: http:; font-src 'self'; connect-src 'self' ws: wss:; frame-ancestors 'none';");
  
  // Additional security headers
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('X-XSS-Protection', '1; mode=block');
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
  
  next();
});

// Simple rate limiting to prevent abuse (TEMPORARILY DISABLED FOR DEBUGGING)
/*
const requestCounts = new Map();
const RATE_LIMIT_WINDOW = 60000; // 1 minute
const RATE_LIMIT_MAX = 100; // requests per window

app.use((req, res, next) => {
  const clientIP = req.ip || req.connection.remoteAddress || 'unknown';
  const now = Date.now();
  
  // Clean up old entries
  for (const [ip, data] of requestCounts.entries()) {
    if (now - data.windowStart > RATE_LIMIT_WINDOW) {
      requestCounts.delete(ip);
    }
  }
  
  // Check rate limit
  const clientData = requestCounts.get(clientIP) || { count: 0, windowStart: now };
  
  if (now - clientData.windowStart > RATE_LIMIT_WINDOW) {
    // Reset window
    clientData.count = 1;
    clientData.windowStart = now;
  } else {
    clientData.count++;
  }
  
  requestCounts.set(clientIP, clientData);
  
  if (clientData.count > RATE_LIMIT_MAX) {
    console.log(`❌ Rate limit exceeded for IP: ${sanitizeLogOutput(clientIP)}`);
    return sendErrorResponse(res, 429, '🚫 Rate Limit Exceeded', 
      'Too many requests. Please try again later.', null);
  }
  
  next();
});
*/

// Agent Registry API base URL
const AGENT_REGISTRY_URL = 'http://localhost:9002';

// Cache for fetched keys to avoid repeated API calls
const keyCache = new Map();
const CACHE_TTL = 5 ; // 5 milliseconds

// Function to fetch key directly by keyId from Agent Registry
async function getKeyById(keyId) {
  const cacheKey = `key:${keyId}`;
  
  // Check cache first
  if (keyCache.has(cacheKey)) {
    const cached = keyCache.get(cacheKey);
    if (Date.now() - cached.timestamp < CACHE_TTL) {
      console.log('📋 Using cached key for keyId', sanitizeLogOutput(keyId));
      return cached.key;
    } else {
      // Remove expired cache entry
      keyCache.delete(cacheKey);
    }
  }
  
  try {
    console.log('🔍 Fetching key from Agent Registry - KeyId:', sanitizeLogOutput(keyId));
    const response = await axios.get(`${AGENT_REGISTRY_URL}/keys/${encodeURIComponent(keyId)}`, { timeout: 5000 });
    
    if (response.status === 200) {
      const keyData = response.data;
      console.log('✅ Retrieved key data:', { keyId: sanitizeLogOutput(keyData.key_id), algorithm: sanitizeLogOutput(keyData.algorithm) });
      
      // Cache the key
      keyCache.set(cacheKey, {
        key: keyData,
        timestamp: Date.now()
      });
      
      return keyData;
    } else {
      console.log('❌ Failed to fetch key - Status:', response.status);
      return null;
    }
  } catch (error) {
    if (error.response?.status === 404) return null;
    throw new Error('The agent registry is unavailable.');
  }
}



// This gate establishes agent recognition; it is not payment authorization.
const verifyTap = createVerifier({
  resolveKey: keyId => validateKeyId(keyId) ? getKeyById(keyId) : undefined
});

const verifySignature = async (req, res, next) => {
  try {
    req.tap = await verifyTap(req);
    next();
  } catch (error) {
    const status = error instanceof VerificationError ? error.status : 500;
    return sendErrorResponse(res, status, 'TAP verification failed',
      error instanceof VerificationError ? error.message : 'The request could not be checked.');
  }
};

// Add a test endpoint that bypasses signature verification
app.get('/test-proxy', (req, res) => {
  const currentTime = escapeHtml(new Date().toISOString());
  res.send(`
    <!DOCTYPE html>
    <html lang="en">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>CDN Proxy Test</title>
        <style>
          body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background-color: #f8f9fa; }
          .container { max-width: 600px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
          h1 { color: #28a745; margin-bottom: 20px; }
          p { color: #6c757d; line-height: 1.5; margin-bottom: 15px; }
          a { color: #007bff; text-decoration: none; }
          a:hover { text-decoration: underline; }
        </style>
      </head>
      <body>
        <div class="container">
          <h1>✅ CDN Proxy is working!</h1>
          <p>This request bypassed signature verification</p>
          <p>Time: ${currentTime}</p>
          <p><a href="/">Try to access React frontend</a></p>
        </div>
      </body>
    </html>
  `);
});

// Signature verification for /products/ URLs
app.use((req, res, next) => {
  console.log(`🚀 CDN-Proxy received: ${sanitizeLogOutput(req.method)} ${sanitizeLogOutput(req.url)} from ${sanitizeLogOutput(req.get('host'))}`);
  console.log(`🔍 Request headers: ${Object.keys(req.headers).join(', ')}`);
  
  const url = req.url.toLowerCase();
  const hasSignatureHeaders = req.headers['signature-input'] && req.headers['signature'];
  const isProductsApiRoute = url.startsWith('/product/');

  if (isProductsApiRoute) {
    // /products/ route - signature is required
    if (!hasSignatureHeaders) {
      console.log(`❌ /products/ route requires signatures - rejecting: ${sanitizeLogOutput(req.url)}`);
      return sendErrorResponse(res, 403, '🔐 Signature Required', 
        'Access to /products/ requires verification from trusted payment directory agents.',
        'Missing required signature headers: signature-input, signature');
    }
    
    // Signature headers provided - verify them
    console.log(`🔐 /products/ route with signatures - verifying: ${sanitizeLogOutput(req.url)}`);
    verifySignature(req, res, next).catch(next);
  } else {
    // Non-/product/ route without signatures - allow
    next();
  }
});

// Proxy API requests to backend (simple passthrough)
app.use('/api', createProxyMiddleware({
  target: 'http://localhost:8000',
  changeOrigin: true,
  logLevel: 'debug',
  onProxyReq: (proxyReq, req, res) => {
    console.log(`🔄 Forwarding API request to backend: ${sanitizeLogOutput(req.path)}`);
    // Simple passthrough - no header manipulation needed
  }
}));

// Proxy everything else to React (simple passthrough)
app.use('/', createProxyMiddleware({
  target: 'http://localhost:3000',
  changeOrigin: true,
  logLevel: 'debug',
  onProxyReq: (proxyReq, req, res) => {
    console.log(`🔄 Forwarding request to React: ${sanitizeLogOutput(req.method)} ${sanitizeLogOutput(req.path)}`);
  },
  onError: (err, req, res) => {
    console.error('❌ Proxy error forwarding to React:', sanitizeLogOutput(err.message));
  }
}));

app.listen(PORT, () => {
  console.log(`
🚀 Demo CDN Proxy running on http://localhost:${PORT}

Architecture:
  Browser → Proxy:3001 (RFC 9421 CDN simulation) → React:3000 & Backend:8000

RFC 9421 HTTP Message Signatures Support:
  ✅ Signature Input parsing: sig2=("@authority" "@path"); created=...; expires=...; keyId="..."; alg="rsa-pss-sha256"
  ✅ Signature parsing: sig2=:base64-signature:
  ✅ RSA-PSS-SHA256 verification
  ✅ Timestamp validation
  ✅ Agent Registry integration

Test URLs:
  🌐 Normal access: http://localhost:${PORT}
  🔐 With RFC 9421 headers: curl -H "signature-input: sig2=(\\"@authority\\" \\"@path\\"); created=...; keyId=\\"key-id\\"" \\
                                 -H "signature: sig2=:base64-signature:" \\
                                 http://localhost:${PORT}/product/1

  `);
});

module.exports = app;
