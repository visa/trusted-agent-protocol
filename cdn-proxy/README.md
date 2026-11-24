# CDN proxy

A local Express proxy that verifies the sample TAP request-recognition profile
on configured routes. Read the [protocol guide](../docs/protocol.md) before
changing verification or canonicalization.

## Run and configuration

From this directory, using Node 22 or 24:

```bash
npm install
npm start
```

| Setting | Actual behavior |
| --- | --- |
| `PORT` | Read from this directory's `.env` or process environment; defaults to 3001 |
| Registry | Fixed `http://localhost:9002` in `server.js` |
| Backend | Fixed `http://localhost:8000` in `server.js`; gateway helper accepts a target argument |
| Frontend | Fixed `http://localhost:3000` in `server.js` |

`MERCHANT_API_URL`, `MERCHANT_BACKEND_URL`, `AGENT_REGISTRY_URL`, and `DEBUG` env
variables do not configure the current server. Change the source deliberately if
adapting upstream addresses. Only registry/backend are needed for a signed API
request; storefront pages additionally need Vite. `npm run dev` uses nodemon.

## Route policy

| Route on port 3001 | Policy | Destination |
| --- | --- | --- |
| `/agent-api/products/...` | TAP required | Backend `/api/products/...` |
| `/agent-api/cart/...` | TAP required | Backend `/api/cart/...` |
| `/agent-api/orders/...` | TAP required | Backend `/api/orders/...` |
| `/api/...` | Public storefront API | Backend `/api/...` |
| `/product/:id` | TAP-gated document request | React frontend |
| Other storefront pages | Public | React frontend |
| `/test-proxy` | Public diagnostic | Proxy itself |

The gateway applies to the whole `/agent-api` prefix, including any backend API
route mounted beneath it. Public `/api` remains available and serves the same
catalog. Recognition does not provide catalog confidentiality, consumer consent,
or payment authorization. The React frontend does not add signatures to its API
calls, and client-side navigation does not enforce the product document gate.

Sign the **external** `/agent-api/...` path and authority. Verification happens
before path/Host rewriting. Backend API redirects retain the protected prefix,
but the redirected target needs a fresh signature. Prefer canonical
slash-terminated collection URLs such as `/agent-api/products/`.

## Verification behavior

`tap-verifier.js` parses Structured Fields dictionaries, requires matching labels
and one applicable TAP signature, and reconstructs canonical signature parameters.
It requires `@authority`, `@path`, integer timestamps with a maximum 480-second
lifetime, nonempty `keyid`/nonce, an algorithm, and a supported TAP tag.

Supported coverage also includes `@method`, `@scheme`, `@query`, lowercase HTTP
fields, and Structured Fields dictionary members via `;key="member"`. Missing or
unsupported coverage is rejected instead of skipped. `@path` excludes query;
method case and encoded query values are preserved.

Supported algorithms are Ed25519 and the sample's legacy RSA-PSS/SHA-256,
MGF1-SHA-256, maximum-salt convention. The latter is distinct from the registered
`rsa-pss-sha512`. Visa's `Ed25519` spelling is accepted while preserving the
spelling in canonical parameters; the Python signer emits `ed25519`.

The registry must return an active matching key. Key metadata must match the
algorithm. The server's key cache has a five-millisecond TTL; it is not a hosted
key-discovery or long-term revocation-cache design. Registry lookup has a
five-second timeout. Temporary lookup failures return 503; invalid/unknown keys,
invalid or expired signatures, and replays return 403.

Nonce claims happen after signature verification and are scoped to `(keyid,
nonce)` until expiry. Expiry is rechecked after key lookup/crypto. The in-memory
store is single-process and lost on restart; multi-worker deployments need a
shared atomic store. Rate-limiting code in `server.js` is currently disabled.
The proxy does not automatically validate body digests or consumer/payment
containers. See [architecture](../docs/architecture.md) for deployment boundaries.

## Run a real signed request and tests

With the registry, backend, and proxy running, from the repository root:

```bash
python scripts/demo_request.py
```

It generates a fresh key, registers it locally, and checks unsigned/signed/replayed
responses. No copied static signature or hosted credentials are needed.

After installing Python signing dependencies, from this directory:

```bash
npm test
```

The tests generate throwaway keys and verify the actual Python signing functions
in Node, plus real HTTP gateway routing. From the root, `python scripts/check.py`
runs these together with signing and registry checks. No services are needed for
the automated suites. See [development](../docs/development.md).
