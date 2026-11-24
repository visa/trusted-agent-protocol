# CDN Proxy

A sample Node.js Express server demonstrating RFC 9421 HTTP Message Signature verification for the Trusted Agent Protocol (TAP).

## Environment Configuration

Create a `.env` file in the root directory:

```bash
# Server Configuration
PORT=3001

# Upstream Services
MERCHANT_BACKEND_URL=http://localhost:8000
AGENT_REGISTRY_URL=http://localhost:8081

# Debug Configuration
DEBUG=true
```

## Features

- 🔐 **RFC 9421 Signature Verification**: Validates HTTP Message Signatures
- 🎭 **Multi-Algorithm Support**: Ed25519 and RSA-PSS-SHA256 algorithms
- 🌐 **Request Proxying**: Routes verified requests to merchant backend
- 🔑 **Dynamic Key Retrieval**: Fetches public keys from Agent Registry
- 📊 **Request Logging**: Detailed logging for debugging
- 🛡️ **Security Demo**: Shows secure error handling patterns

## Quick Start

```bash
# Install dependencies
npm install

# Start the server
npm start
```

The CDN Proxy will be available at http://localhost:3001

> **Note**: Requires Agent Registry (port 8080) and Merchant Backend (port 8000) to be running

## How It Works

1. **Receives Request**: Client sends request with RFC 9421 signature headers
2. **Extracts Signature**: Parses `Signature-Input` and `Signature` headers
3. **Fetches Key**: Retrieves an active public key from Agent Registry using `keyid`
4. **Verifies Signature**: Validates signature using Ed25519 or RSA-PSS-SHA256
5. **Proxies Request**: Forwards verified requests to Merchant Backend

## Example Usage

### Proxy Routes
- `GET /products/1` → Forwards to `http://localhost:8000/products/1`
- `POST /cart/add` → Forwards to `http://localhost:8000/cart/add` (requires signature)
- `GET /orders` → Forwards to `http://localhost:8000/orders` (requires signature)

### Test Signature Verification

Generate fresh signatures with the sample agent. The verifier requires the TAP
minimum components, timestamps with a lifetime of at most 480 seconds, a nonce,
an algorithm, and either `agent-browser-auth` or `agent-payer-auth` as the tag.
Request signatures identify an agent; they do not authorize a consumer payment.

Run the regression tests after installing the root Python dependencies:

```bash
npm test
# From the repository root:
python -m unittest discover -s tap-agent/tests -v
```

The tests generate throwaway keys and verify signatures produced by the actual
Python agent functions against the Node verifier. No services need to be running.

## Technical Details

### Supported Algorithms
- **Ed25519**: Fast elliptic curve signatures
- **RSA-PSS-SHA256**: The sample's existing SHA-256/MGF1-SHA-256, maximum-salt
  convention. This is distinct from RFC 9421's registered `rsa-pss-sha512` algorithm.

### RFC 9421 Compliance
Implements HTTP Message Signatures with components:
- `@authority` - Host header
- `@path` - Encoded request path, excluding the query
- `created` - Signature creation time
- `expires` - Signature expiry, at most 480 seconds after creation
- `keyid` - Key identifier
- `alg` - Signature algorithm
- `nonce` - Non-empty, single-use nonce scoped to the signing key
- `tag` - Browsing or payment interaction intent

Additional covered `@method`, `@scheme`, `@query`, and HTTP fields are rebuilt
when declared. Unavailable components and unsupported parameters are rejected.
Method case and query encodings are preserved. Header fields can also select a
Structured Fields dictionary member with `;key="member"`.

The sample accepts one applicable TAP signature with any matching label, and can
coexist with signatures carrying other protocol tags. It parses Structured Fields
and rebuilds canonical signature parameters instead of signing raw header spacing.
The `Ed25519` algorithm spelling shown in Visa's examples is accepted without
changing the signed parameter bytes; the sample agent emits lowercase `ed25519`.

Replay protection is in memory and applies to one proxy process. A multi-worker
deployment needs a shared atomic nonce store. A registry outage returns 503;
unknown or inactive keys, invalid signatures, and replays are refused.

### Example Headers

These illustrative values are not a reusable signed request. Use fresh values
and the agent's generated signature for an actual request.

```http
Signature-Input: sig2=("@authority" "@path");created=1800000000;expires=1800000060;keyid="primary-ed25519";alg="ed25519";nonce="example-nonce";tag="agent-browser-auth"
Signature: sig2=:AA==:
```

## Development

```bash
# Auto-reload for development
npm run dev

# Enable debug logging
DEBUG=true npm start
```

## Architecture

This is a sample implementation showing how to:
- Parse RFC 9421 signature headers
- Retrieve public keys from a registry
- Verify signatures with multiple algorithms
- Proxy requests based on verification results
