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
3. **Fetches Key**: Retrieves public key from Agent Registry using `keyId`
4. **Verifies Signature**: Validates signature using Ed25519 or RSA-PSS-SHA256
5. **Proxies Request**: Forwards verified requests to Merchant Backend

## Example Usage

### Proxy Routes
- `GET /products/1` → Forwards to `http://localhost:8000/products/1`
- `POST /cart/add` → Forwards to `http://localhost:8000/cart/add` (requires signature)
- `GET /orders` → Forwards to `http://localhost:8000/orders` (requires signature)

### Test Signature Verification
```bash
curl -X GET http://localhost:3001/products/1 \
  -H "Signature-Input: sig2=(\"@authority\" \"@path\"); created=1697123456; keyId=\"primary-ed25519\"; alg=\"ed25519\"" \
  -H "Signature: sig2=:base64EncodedSignature:"
```

## Technical Details

### Supported Algorithms
- **Ed25519**: Fast elliptic curve signatures
- **RSA-PSS-SHA256**: Traditional RSA with PSS padding

### RFC 9421 Compliance
Implements HTTP Message Signatures with components:
- `@authority` - Host header
- `@path` - Request path
- `created` - Signature creation time
- `keyId` - Key identifier
- `alg` - Signature algorithm

### Example Headers
```http
Signature-Input: sig2=("@authority" "@path"); created=1697123456; keyId="primary-ed25519"; alg="ed25519"
Signature: sig2=:base64EncodedSignature:
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
