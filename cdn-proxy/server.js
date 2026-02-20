/* © 2025 Visa.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

require('dotenv').config();
const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const crypto = require('crypto');
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

// Nonce cache to prevent replay attacks
const nonceCache = new Map();
const NONCE_TTL = 3600000; // 1 hour - nonces older than this are purged

// Cleanup old nonces periodically to prevent memory leaks
setInterval(() => {
  const now = Date.now();
  for (const [nonce, timestamp] of nonceCache.entries()) {
    if (now - timestamp > NONCE_TTL) {
      nonceCache.delete(nonce);
    }
  }
}, 60000); // Clean up every minute

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
    const response = await axios.get(`${AGENT_REGISTRY_URL}/keys/${keyId}`);
    
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
    console.error('❌ Error fetching key:', sanitizeLogOutput(error.message));
    return null;
  }
}



// Parse RFC 9421 signature input string to extract components
function parseRFC9421SignatureInput(signatureInput) {
  try {
    // Parse RFC 9421 format: sig2=("@authority" "@path"); created=1735689600; expires=1735693200; keyId="key-id"; alg="rsa-pss-sha256"; nonce="123"; tag="agent-payment-auth"
    const signatureMatch = signatureInput.match(/sig2=\(([^)]+)\);\s*(.+)/);
    
    if (!signatureMatch) {
      throw new Error('Invalid RFC 9421 signature input format - must start with sig2=()');
    }
    
    const [, paramString, attributesString] = signatureMatch;
    
    // Parse parameters (what's being signed)
    const params = paramString.split(/\s+/).map(p => p.replace(/['"]/g, ''));
    
    // Parse attributes
    const attributes = {};
    const attributeMatches = attributesString.matchAll(/(\w+)=("[^"]*"|\d+)/g);
    
    for (const match of attributeMatches) {
      const [, key, value] = match;
      if (value.startsWith('"') && value.endsWith('"')) {
        attributes[key] = value.slice(1, -1); // Remove quotes
      } else {
        attributes[key] = parseInt(value); // Parse numbers
      }
    }
    
    console.log('🔍 Parsed RFC 9421 signature input:');
    console.log('  - params:', params?.map(p => sanitizeLogOutput(p)));
    console.log('  - attributes:', Object.fromEntries(
      Object.entries(attributes).map(([k, v]) => [k, typeof v === 'string' ? sanitizeLogOutput(v) : v])
    ));
    console.log('  - original signatureInput:', sanitizeLogOutput(signatureInput));
    
    return {
      params,
      nonce: attributes.nonce,
      created: attributes.created,
      expires: attributes.expires,
      keyId: attributes.keyId,
      algorithm: attributes.alg,
      tag: attributes.tag
    };
  } catch (error) {
    console.error('Failed to parse RFC 9421 signature input:', sanitizeLogOutput(error.message));
    return null;
  }
}

// Build RFC 9421 signature base string from request components
function buildRFC9421SignatureString(params, requestData, signatureInputHeader) {
  const components = [];
  
  // Add the signed components first
  for (const param of params) {
    switch (param) {
      case '@authority':
        components.push(`"@authority": ${requestData.authority}`);
        break;
      case '@path':
        components.push(`"@path": ${requestData.path}`);
        break;
      case 'content-type':
        components.push(`"content-type": ${requestData.contentType || 'application/json'}`);
        break;
      case 'host':
        components.push(`"host": ${requestData.host || requestData.authority}`);
        break;
      default:
        // Handle custom headers if needed
        if (requestData[param]) {
          components.push(`"${param}": ${requestData[param]}`);
        }
        break;
    }
  }
  
  // Add @signature-params as the last component (RFC 9421 requirement)
  // Extract just the parameters part (remove sig2= prefix if present)
  let signatureParams = signatureInputHeader;
  if (signatureInputHeader.startsWith('sig2=')) {
    signatureParams = signatureInputHeader.substring(5); // Remove 'sig2=' prefix
  }
  components.push(`"@signature-params": ${signatureParams}`);
  
  const signatureBaseString = components.join('\n');
  
  console.log('🔍 RFC 9421 Signature Base String:');
  console.log('---BEGIN SIGNATURE BASE STRING---');
  console.log(sanitizeLogOutput(signatureBaseString));
  console.log('---END SIGNATURE BASE STRING---');
  console.log('📏 Signature base string length:', signatureBaseString.length);
  
  return signatureBaseString;
}

// Verify RSA signature with PSS padding (to match Python cryptography library)
async function verifyRSASignature(publicKeyPem, signatureBase64, signatureString) {
  try {
    console.log('🔍 RSA Verification:');
    console.log('- Signature string length:', signatureString.length);
    console.log('- Signature base64 length:', signatureBase64.length);
    console.log('- First 100 chars of signature string:', sanitizeLogOutput(signatureString.substring(0, 100)));
    
    // Create public key object with explicit PSS padding
    const publicKey = crypto.createPublicKey({
      key: publicKeyPem,
      format: 'pem',
      type: 'spki'
    });
    
    // Decode base64 signature
    const signatureBuffer = Buffer.from(signatureBase64, 'base64');
    
    // Create verifier with PSS padding to match Python's PSS padding
    const verifier = crypto.createVerify('RSA-SHA256');
    verifier.update(signatureString, 'utf-8');
    
    // Verify with PSS padding options (matching Python's PSS.MAX_LENGTH)
    const isValid = verifier.verify({
      key: publicKey,
      padding: crypto.constants.RSA_PKCS1_PSS_PADDING,
      saltLength: crypto.constants.RSA_PSS_SALTLEN_MAX_SIGN
    }, signatureBuffer);
    
    console.log('🎯 Verification result:', isValid ? 'VALID ✅' : 'INVALID ❌');
    return isValid;
  } catch (error) {
    console.error('❌ Signature verification error:', sanitizeLogOutput(error.message));
    return false;
  }
}

// Verify Ed25519 signature
async function verifyEd25519Signature(publicKeyBase64, signatureBase64, signatureString) {
  try {
    console.log('🔍 Ed25519 Verification:');
    console.log('- Signature string length:', signatureString.length);
    console.log('- Signature base64 length:', signatureBase64.length);
    console.log('- Public key base64 length:', publicKeyBase64.length);
    console.log('- First 100 chars of signature string:', sanitizeLogOutput(signatureString.substring(0, 100)));
    
    // Create Ed25519 public key from base64 raw bytes
    const publicKeyBuffer = Buffer.from(publicKeyBase64, 'base64');
    console.log('- Public key buffer length:', publicKeyBuffer.length);
    
    // Ed25519 public keys should be exactly 32 bytes
    if (publicKeyBuffer.length !== 32) {
      throw new Error(`Ed25519 public key must be 32 bytes, got ${publicKeyBuffer.length} bytes`);
    }
    
    // Create public key object using DER format for Ed25519
    // Ed25519 public key in DER format: 30 2a 30 05 06 03 2b 65 70 03 21 00 + 32 bytes of key
    const derPrefix = Buffer.from([0x30, 0x2a, 0x30, 0x05, 0x06, 0x03, 0x2b, 0x65, 0x70, 0x03, 0x21, 0x00]);
    const derPublicKey = Buffer.concat([derPrefix, publicKeyBuffer]);
    
    const publicKey = crypto.createPublicKey({
      key: derPublicKey,
      format: 'der',
      type: 'spki'
    });
    
    // Decode base64 signature
    const signatureBuffer = Buffer.from(signatureBase64, 'base64');
    console.log('- Signature buffer length:', signatureBuffer.length);
    
    // Ed25519 signatures should be exactly 64 bytes
    if (signatureBuffer.length !== 64) {
      throw new Error(`Ed25519 signature must be 64 bytes, got ${signatureBuffer.length} bytes`);
    }
    
    // Verify Ed25519 signature (no hashing needed, Ed25519 is pure)
    const isValid = crypto.verify(null, Buffer.from(signatureString, 'utf-8'), publicKey, signatureBuffer);
    
    console.log('🎯 Ed25519 Verification result:', isValid ? 'VALID ✅' : 'INVALID ❌');
    return isValid;
  } catch (error) {
    console.error('❌ Ed25519 signature verification error:', sanitizeLogOutput(error.message));
    console.error('❌ Error stack:', error.stack);
    return false;
  }
}

// Signature verification middleware (simulates CDN)
const verifySignature = async (req, res, next) => {
  console.log('🔍 CDN Proxy: Checking request headers...');
  console.log(`📍 Request: ${sanitizeLogOutput(req.method)} ${sanitizeLogOutput(req.url)}`);
  
  const signatureInput = req.headers['signature-input'];
  const signature = req.headers['signature'];

  console.log('🔍 CDN Proxy: headers are', {
    'signature-input': signatureInput ? `${sanitizeLogOutput(signatureInput.substring(0, 50))}...` : sanitizeLogOutput(signatureInput),
    'signature': signature ? `${sanitizeLogOutput(signature.substring(0, 30))}...` : sanitizeLogOutput(signature)
  });

let signatureData;

// Parse RFC 9421 signature input
try {
  signatureData = parseRFC9421SignatureInput(signatureInput);
  if (!signatureData) {
    throw new Error('Failed to parse RFC 9421 signature input');
  }
} catch (err) {
  console.log('❌ Failed to parse RFC 9421 signature-input:', sanitizeLogOutput(err.message));
  return sendErrorResponse(res, 403, '🔐 Invalid RFC 9421 Signature Input', 
    'Could not parse signature-input header. Expected RFC 9421 format.', err.message);
}

const signatureKeyId = signatureData.keyId;

  // Validate keyId format to prevent injection attacks
  if (!validateKeyId(signatureKeyId)) {
    console.log('❌ CDN: Invalid keyId format - blocking');
    return sendErrorResponse(res, 403, '🔑 Invalid Key ID Format', 
      'The key ID contains invalid characters or is too long.', null);
  }
  
  // Log incoming headers for demo (with sanitization)
  console.log('Headers received:', {
    'signature-key-id': sanitizeLogOutput(signatureKeyId),
    'signature-input': sanitizeLogOutput(signatureInput),
    'signature': sanitizeLogOutput(signature),
    'user-agent': sanitizeLogOutput(req.headers['user-agent'])
  });
  
  // Bot detection simulation
  if (!signatureKeyId || !signatureInput || !signature) {
    console.log('❌ CDN: Missing signature headers - blocking bot traffic');
    return sendErrorResponse(res, 403, '🤖 Bot Traffic Detected', 
      'This site requires verification from trusted payment directory agents.',
      'Missing required signature headers: signature-input, signature');
  }
  
  try {
    // Fetch the key directly by keyId
    const keyInfo = await getKeyById(signatureKeyId);
    
    if (!keyInfo) {
      console.log('❌ CDN: Key not found - blocking');
      return sendErrorResponse(res, 403, '🔑 Key Not Found', 
        'The specified key ID was not found in the registry.', `Key ID: ${signatureKeyId}`);
    }
    
    // Check if key is active
    if (keyInfo.is_active !== 'true') {
      console.log('❌ CDN: Inactive key - blocking');
      return sendErrorResponse(res, 403, '🔑 Inactive Key', 
        'The specified key is not currently active.', `Key ID: ${keyInfo.key_id}`);
    }
    
    console.log('✅ Key validated:', {
      keyId: sanitizeLogOutput(keyInfo.key_id),
      algorithm: sanitizeLogOutput(keyInfo.algorithm)
    });
    
    // Validate signature timing
    const now = Math.floor(Date.now() / 1000);
    if (signatureData.created && signatureData.created > now + 60) {
      console.log('❌ CDN: Signature created time is in the future');
      return sendErrorResponse(res, 403, '🕐 Invalid Timestamp', 
        'Signature created time is in the future.', null);
    }
    
    if (signatureData.expires && signatureData.expires < now) {
      console.log('❌ CDN: Signature has expired');
      return sendErrorResponse(res, 403, '⏰ Signature Expired', 
        'The signature has expired and is no longer valid.', 
        `Expired at: ${new Date(signatureData.expires * 1000).toISOString()}`);
    }
    
    // Validate nonce to prevent replay attacks
    const nonce = signatureData.nonce;
    if (!nonce) {
      console.log('❌ CDN: Missing nonce in signature');
      return sendErrorResponse(res, 403, '🔐 Missing Nonce', 
        'Signature must include a nonce to prevent replay attacks.', null);
    }
    
    // Check if nonce has been used before
    if (nonceCache.has(nonce)) {
      const previousUse = nonceCache.get(nonce);
      console.log('❌ CDN: Replay attack detected - nonce already used');
      console.log('  - Nonce:', sanitizeLogOutput(nonce));
      console.log('  - First seen:', new Date(previousUse).toISOString());
      console.log('  - Current time:', new Date().toISOString());
      return sendErrorResponse(res, 403, '🚫 Replay Attack Detected', 
        'This signature has already been used. Each request must have a unique nonce.',
        `Nonce was previously used at ${new Date(previousUse).toISOString()}`);
    }
    
    // Store nonce with current timestamp
    nonceCache.set(nonce, Date.now());
    console.log('✅ Nonce validated and cached:', sanitizeLogOutput(nonce));
    
    // Build request data for signature verification
    const requestData = {
      authority: req.get('host') || req.headers.host,
      path: req.url,
      contentType: req.get('content-type'),
      host: req.get('host') || req.headers.host
    };
    
    console.log('🔍 Request data for verification:', {
      authority: sanitizeLogOutput(requestData.authority),
      path: sanitizeLogOutput(requestData.path),
      contentType: sanitizeLogOutput(requestData.contentType),
      host: sanitizeLogOutput(requestData.host)
    });
    console.log('🔍 Signature data parsed:', {
      params: signatureData.params?.map(p => sanitizeLogOutput(p)),
      keyId: sanitizeLogOutput(signatureData.keyId),
      algorithm: sanitizeLogOutput(signatureData.algorithm),
      created: signatureData.created,
      expires: signatureData.expires
    });
    
    // Build RFC 9421 signature base string
    const signatureBaseString = buildRFC9421SignatureString(
      signatureData.params,
      requestData,
      signatureInput
    );
    
    // Extract signature value (remove sig2=: wrapper)
    let signatureBase64 = signature;
    const signatureMatch = signature.match(/sig2=:([^:]+):/);
    if (signatureMatch) {
      signatureBase64 = signatureMatch[1];
    } else {
      console.log('❌ CDN: Invalid signature format - expected sig2=:base64:');
      return sendErrorResponse(res, 403, '🔐 Invalid Signature Format', 
        'The signature format is invalid.', 'Expected RFC 9421 signature format: sig2=:base64:');
    }
    
    // Verify RFC 9421 signature
    const publicKey = keyInfo.public_key;
    console.log('🔐 Verifying RFC 9421 signature...');
    console.log('🔑 Using public key from agent registry for verification');
    console.log('📋 Key info:', { keyId: sanitizeLogOutput(keyInfo.key_id), algorithm: sanitizeLogOutput(keyInfo.algorithm) });
    console.log('🔍 Signature base64 to verify:', sanitizeLogOutput(signatureBase64.substring(0, 50)) + '...');
    
    // Choose verification method based on algorithm
    let isValidSignature = false;
    const algorithm = signatureData.algorithm.toLowerCase();
    
    if (algorithm === 'rsa-pss-sha256') {
      console.log('🔐 Using RSA-PSS-SHA256 verification...');
      isValidSignature = await verifyRSASignature(publicKey, signatureBase64, signatureBaseString);
    } else if (algorithm === 'ed25519') {
      console.log('🔐 Using Ed25519 verification...');
      isValidSignature = await verifyEd25519Signature(publicKey, signatureBase64, signatureBaseString);
    } else {
      console.log(`❌ CDN: Unsupported algorithm: ${algorithm}`);
      return sendErrorResponse(res, 400, '🔐 Unsupported Algorithm', 
        `The signature algorithm '${algorithm}' is not supported.`, `Supported algorithms: rsa-pss-sha256, ed25519`);
    }
    
    if (!isValidSignature) {
      console.log(`❌ CDN: ${algorithm} signature verification failed`);
      return sendErrorResponse(res, 403, '🔐 Signature Verification Failed', 
        'The signature could not be verified against the provided key.', `Key ID: ${keyInfo.key_id}, Algorithm: ${algorithm}`);
    }
    
    console.log('✅ CDN: RFC 9421 signature verification successful!');
    console.log('🎯 Authenticated request with:', {
      keyId: sanitizeLogOutput(keyInfo.key_id),
      algorithm: sanitizeLogOutput(signatureData.algorithm),
      tag: sanitizeLogOutput(signatureData.tag),
      nonce: sanitizeLogOutput(signatureData.nonce)
    });
    
    console.log('✅ CDN: RFC 9421 signature verification successful!');
    console.log('🎯 Request authenticated with:', {
      keyId: sanitizeLogOutput(keyInfo.key_id),
      algorithm: sanitizeLogOutput(signatureData.algorithm),
      tag: sanitizeLogOutput(signatureData.tag),
      nonce: sanitizeLogOutput(signatureData.nonce)
    });
    
    // Signature is valid - just forward the request as-is (no headers needed)
    console.log('� Signature valid - forwarding request without modification');
    
    next();
  } catch (error) {
    console.error('❌ CDN: Signature verification error:', sanitizeLogOutput(error.message));
    return sendErrorResponse(res, 500, '🛠️ Server Error', 
      'An internal error occurred during signature verification.', null);
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
  },
  onProxyRes: (proxyRes, req, res) => {
    // Log x402 payment headers for debugging
    const paymentRequired = proxyRes.headers['payment-required'];
    const paymentResponse = proxyRes.headers['payment-response'];
    if (paymentRequired) {
      console.log(`💰 x402 PAYMENT-REQUIRED header present on response for ${sanitizeLogOutput(req.path)}`);
    }
    if (paymentResponse) {
      console.log(`✅ x402 PAYMENT-RESPONSE header present on response for ${sanitizeLogOutput(req.path)}`);
    }
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
