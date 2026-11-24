const crypto = require('node:crypto');
const {
  isInnerList, parseDictionary, serializeInnerList, serializeItem,
} = require('structured-headers');

const TAP_TAGS = new Set(['agent-browser-auth', 'agent-payer-auth']);
const ED25519_SPKI = Buffer.from('302a300506032b6570032100', 'hex');

/** A refusal, or a temporary inability to check the presented TAP signature. */
class VerificationError extends Error {
  constructor(message, status = 403) {
    super(message);
    this.status = status;
  }
}

/**
 * Create a TAP agent-recognition verifier for the sample registry.
 * Nonces are claimed after verification, scoped to their key, and retained until expiry.
 * The in-memory store is for one process; multiple workers need a shared atomic store.
 */
function createVerifier({ resolveKey, now = Date.now }) {
  const nonces = new Map();
  return async function verify(request) {
    const inputHeader = request.headers['signature-input'];
    const signatureHeader = request.headers.signature;
    if (typeof inputHeader !== 'string' || typeof signatureHeader !== 'string') {
      throw new VerificationError('Signature-Input and Signature are required.');
    }
    let inputs, signatures;
    try {
      inputs = parseDictionary(inputHeader);
      signatures = parseDictionary(signatureHeader);
    } catch {
      throw new VerificationError('The HTTP message signature is malformed.');
    }
    if (inputs.size !== signatures.size || [...inputs.keys()].some(key => !signatures.has(key))) {
      throw new VerificationError('Signature-Input and Signature labels must match.');
    }
    const candidates = [...inputs].filter(([, entry]) =>
      isInnerList(entry) && TAP_TAGS.has(entry[1].get('tag')));
    if (candidates.length !== 1) {
      throw new VerificationError('Exactly one applicable TAP signature is required.');
    }
    const [label, input] = candidates[0];
    const [components, parameters] = input;
    const signature = signatures.get(label);
    if (isInnerList(signature) || !(signature[0] instanceof ArrayBuffer) || signature[1].size) {
      throw new VerificationError('The signature must be a byte sequence without parameters.');
    }
    const created = parameters.get('created');
    const expires = parameters.get('expires');
    const keyId = parameters.get('keyid');
    const nonce = parameters.get('nonce');
    const declaredAlgorithm = parameters.get('alg');
    // Visa's public examples use this spelling. Preserve it in the signed parameters.
    const algorithm = declaredAlgorithm === 'Ed25519' ? 'ed25519' : declaredAlgorithm;
    if (typeof keyId !== 'string' || !keyId || typeof nonce !== 'string' || !nonce ||
        typeof algorithm !== 'string' || !['ed25519', 'rsa-pss-sha256'].includes(algorithm)) {
      throw new VerificationError('The TAP keyid, nonce, or algorithm is missing or unsupported.');
    }
    const current = Math.floor(now() / 1000);
    if (!Number.isSafeInteger(created) || !Number.isSafeInteger(expires) || created < 0 ||
        created > current || expires <= current || expires <= created || expires - created > 480) {
      throw new VerificationError('TAP signatures must be current and valid for at most eight minutes.');
    }
    if (!['@authority', '@path'].every(required =>
      components.some(([id, qualifiers]) => id === required && qualifiers.size === 0))) {
      throw new VerificationError('The TAP signature must cover @authority and @path.');
    }
    const identifiers = components.map(serializeItem);
    if (new Set(identifiers).size !== identifiers.length) {
      throw new VerificationError('Covered components must not be repeated.');
    }
    const url = requestUrl(request);
    const base = components.map((component, index) =>
      `${identifiers[index]}: ${componentValue(request, url, component)}`);
    base.push(`"@signature-params": ${serializeInnerList(input)}`);

    let key;
    try {
      key = await resolveKey(keyId);
    } catch {
      throw new VerificationError('The agent registry is unavailable.', 503);
    }
    if (!key || key.key_id !== keyId || key.is_active !== 'true') {
      throw new VerificationError('No active trusted key is available for this keyid.');
    }
    // RSA-SHA256 is the sample registry's historical name for its RSA-PSS keys.
    const registeredAlgorithm = String(key.algorithm).toLowerCase().replace(/^rsa-sha256$/, 'rsa-pss-sha256');
    if (registeredAlgorithm !== algorithm) {
      throw new VerificationError('The registered key does not support the declared algorithm.');
    }
    let valid = false;
    try {
      if (algorithm === 'ed25519') {
        if (!/^[A-Za-z0-9+/]+={0,2}$/.test(key.public_key)) throw new Error('Invalid key.');
        const raw = Buffer.from(key.public_key, 'base64');
        if (raw.length !== 32) throw new Error('Invalid key.');
        const publicKey = crypto.createPublicKey({
          key: Buffer.concat([ED25519_SPKI, raw]), format: 'der', type: 'spki',
        });
        valid = crypto.verify(null, Buffer.from(base.join('\n')), publicKey, Buffer.from(signature[0]));
      } else {
        const publicKey = crypto.createPublicKey(key.public_key);
        if (!['rsa', 'rsa-pss'].includes(publicKey.asymmetricKeyType)) throw new Error('Invalid key.');
        // Preserve the sample's existing RSA-PSS/SHA-256 maximum-salt convention.
        valid = crypto.verify('sha256', Buffer.from(base.join('\n')), {
          key: publicKey, padding: crypto.constants.RSA_PKCS1_PSS_PADDING,
          saltLength: crypto.constants.RSA_PSS_SALTLEN_MAX_SIGN,
        }, Buffer.from(signature[0]));
      }
    } catch {
      valid = false;
    }
    if (!valid) throw new VerificationError('The HTTP message signature is invalid.');
    const checkedAt = now();
    if (expires * 1000 <= checkedAt) throw new VerificationError('The TAP signature has expired.');
    for (const [key, expiry] of nonces) {
      if (expiry <= checkedAt) nonces.delete(key);
    }
    const replayKey = JSON.stringify([keyId, nonce]);
    // No asynchronous work between the check and claim in this single-process store.
    if (nonces.has(replayKey)) throw new VerificationError('The TAP signature nonce has already been used.');
    nonces.set(replayKey, expires * 1000);
    return { keyId, tag: parameters.get('tag'), label, created, expires };
  };
}

/** Derive the external request URL before a proxy or Express mount rewrites its path. */
function requestUrl(request) {
  const host = request.headers.host;
  const scheme = request.protocol || (request.socket?.encrypted ? 'https' : 'http');
  const target = request.originalUrl || request.url;
  if (typeof host !== 'string' || !host || !['http', 'https'].includes(scheme) ||
      typeof target !== 'string' || !target.startsWith('/') || target.includes('#')) {
    throw new VerificationError('The request URL cannot be derived.');
  }
  try {
    const authority = new URL(`${scheme}://${host}`);
    if (authority.username || authority.password || authority.pathname !== '/' || authority.search || authority.hash) {
      throw new Error('Invalid authority.');
    }
    return new URL(`${authority.origin}${target}`);
  } catch {
    throw new VerificationError('The request URL cannot be derived.');
  }
}

/** Rebuild every declared component; unavailable components must fail verification. */
function componentValue(request, url, [id, parameters]) {
  if (typeof id !== 'string') throw new VerificationError('Covered components must be strings.');
  const derived = {
    '@authority': url.host, '@path': url.pathname, '@method': request.method,
    '@scheme': url.protocol.slice(0, -1), '@query': url.search || '?',
  };
  if (id.startsWith('@')) {
    if (!Object.hasOwn(derived, id) || parameters.size) {
      throw new VerificationError('An unsupported derived component or parameter was declared.');
    }
    return derived[id];
  }
  if (!/^[!#$%&'*+.^_`|~0-9a-z-]+$/.test(id)) {
    throw new VerificationError('Signed HTTP field names must be lowercase.');
  }
  let value = request.headers[id];
  if (Array.isArray(value)) value = value.join(', ');
  if (typeof value !== 'string' || !/^[\x20-\x7e]*$/.test(value)) {
    throw new VerificationError('A signed HTTP field is missing or unsupported.');
  }
  if (!parameters.size) return value.trim();
  if (parameters.size !== 1 || typeof parameters.get('key') !== 'string') {
    throw new VerificationError('A signed HTTP field parameter is unsupported.');
  }
  try {
    const member = parseDictionary(value).get(parameters.get('key'));
    if (!member) throw new Error('Missing member.');
    return isInnerList(member) ? serializeInnerList(member) : serializeItem(member);
  } catch {
    throw new VerificationError('A signed dictionary member is missing or malformed.');
  }
}

module.exports = { createVerifier, VerificationError };
