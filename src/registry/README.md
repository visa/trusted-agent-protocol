# Agent Registry Service

Service for managing TAP (Trusted Agent Protocol) agents and their public keys, demonstrating RFC 9421 signature verification using **JWKs** and **@interledger/http-signature-utils**.

## Key Features

- **JWK Support** - All public keys are managed as JSON Web Keys (RFC 7517).
- **Standardized Verification** - Uses `@interledger/http-signature-utils` for robust HTTP Signature verification.
- **Agent Management** - CRUD operations for TAP agents.
- **Key Rotation** - Supports multiple keys per agent via unique `kid` (Key ID).

## Sample API Endpoints

### Agent Management
- `GET /agents` - List all registered agents
- `POST /agents` - Register new agent with an initial JWK
- `GET /agents/:agent_id` - Get agent details
- `PUT /agents/:agent_id` - Update agent information
- `DELETE /agents/:agent_id` - Deactivate agent

### Key Management
- `POST /agents/:agent_id/keys` - Add new JWK to existing agent
- `GET /agents/:agent_id/keys/:key_id` - Get specific key for agent
- `GET /keys/:key_id` - **Global Key Lookup** (used by Verifiers/Proxies)

## Key Management with JWKs

The Registry uses the JSON Web Key (JWK) format for all key operations. This eliminates the need for separate algorithm fields or raw PEM parsing, as the JWK is self-describing.

### 1. Register Agent with Initial Key

```bash
curl -X POST http://localhost:9002/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sample Payment Directory",
    "domain": "https://directory.example.com",
    "jwk": {
      "kty": "RSA",
      "kid": "primary-rsa",
      "use": "sig",
      "alg": "PS256",
      "n": "m2J...",
      "e": "AQAB"
    }
  }'
```

### 2. Add Additional Keys (e.g., Ed25519)

```bash
curl -X POST http://localhost:9002/agents/1/keys \
  -H "Content-Type: application/json" \
  -d '{
    "jwk": {
      "kty": "OKP",
      "kid": "backup-ed25519",
      "use": "sig",
      "alg": "EdDSA",
      "crv": "Ed25519",
      "x": "11qY..."
    }
  }'
```

### 3. Key Lookup for Verification

The proxy or verifier retrieves the key by `kid` to verify signatures.

```bash
curl http://localhost:9002/keys/primary-rsa
```

Returns the JWK directly:

```json
{
  "kty": "RSA",
  "kid": "primary-rsa",
  "use": "sig",
  "alg": "PS256",
  "n": "m2J...",
  "e": "AQAB",
  "agent_id": "1"
}
```

## Architecture

- **Runtime**: Bun
- **Language**: TypeScript
- **Core Library**: [`@interledger/http-signature-utils`](https://www.npmjs.com/package/@interledger/http-signature-utils) for key import/export and verification.

## Storage Backends

The registry supports pluggable storage backends configured via `REGISTRY_STORAGE` environment variable:

1.  **Memory** (`memory`) - Default. Ephemeral storage for testing/dev.
2.  **Redis** (`redis`) - Native Bun Redis. Requires a running Redis instance.
3.  **SQLite** (`sqlite`) - Native Bun SQLite. Persistent file storage.

Configuration:
-   `REGISTRY_STORAGE`: `memory` | `redis` | `sqlite`
-   `REGISTRY_DB_PATH`: Path for SQLite DB (default `registry.db`)

### Development

```bash
# Install dependencies
bun install

# Run the registry service (Memory)
REGISTRY_STORAGE=memory bun run src/registry/module.ts

# Run with SQLite
REGISTRY_STORAGE=sqlite bun run src/registry/module.ts
```
