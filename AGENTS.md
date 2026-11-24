# Working in this repository

This is a local TAP **agent request-recognition sample**. A successful HTTP
signature is not consumer consent, payment authorization, or settlement.

## Get oriented

1. Read [README.md](README.md) for scope and the service map.
2. Read [the documentation index](docs/README.md) and choose the task-specific path.
3. Read [the protocol guide](docs/protocol.md) before changing signing, verification,
   registry lookup, or protected routing.
4. Use [the development guide](docs/development.md) for checks and change boundaries.
5. For a running example, follow [the quickstart](docs/quickstart.md).

Read the relevant source and tests before proposing a change. The guides are
navigation aids; they do not override the implementation or the protocol sources.

## Find the implementation

| Task | Start here | Validate with |
| --- | --- | --- |
| HTTP signature verification | `cdn-proxy/tap-verifier.js` | `cdn-proxy/test/tap-verifier.test.js` |
| Python signature construction | `tap-agent/tap_signature.py`, signing functions in `tap-agent/agent_app.py` | `tap-agent/tests/`, Python-to-Node fixtures in proxy tests |
| Protected API routing | `cdn-proxy/agent-api.js`, middleware order in `cdn-proxy/server.js` | `cdn-proxy/test/agent-api.test.js` |
| Key lookup and agent revocation | `agent-registry/main.py`, `schemas.py`, `models.py` | `agent-registry/tests/test_key_lookup.py` |
| Storefront API and checkout | `merchant-backend/app/routes/`, `app/schemas.py` | Backend `/docs`; use demo data |
| Browser requests and cart state | `merchant-frontend/src/services/api.js`, `src/context/`, `src/pages/` | Frontend build and manual browser check |
| Browser automation | `tap-agent/agent_app.py` | Manual Streamlit/Playwright exercise |
| Setup and documentation | `docs/quickstart.md`, component READMEs, `.env.example` files | `python scripts/check.py --docs-only` |

## Preserve the protocol boundaries

- Use [Visa's merchant specification](https://developer.visa.com/docs/trusted-agent-protocol/trusted-agent-protocol-specifications)
  for TAP policy, [RFC 9421](https://www.rfc-editor.org/rfc/rfc9421.html) for HTTP
  signature construction, and [IANA's registry](https://www.iana.org/assignments/http-message-signature/)
  for registered algorithm names. When examples disagree, describe the discrepancy
  and follow the normative rule; do not silently broaden acceptance.
- HTTP wire metadata uses lowercase `keyid`. Registry JSON uses `key_id`; the
  Streamlit UI also has an internal `keyId` JSON field. They are different layers.
- Reconstruct every declared covered component or reject it. `@path` excludes
  the query. Cover `@method` and `@query` when an operation depends on them.
- The local verifier supports Ed25519 and the sample's legacy RSA-PSS/SHA-256
  maximum-salt convention. Do not equate the latter with `rsa-pss-sha512`, assume
  hosted Visa algorithm support is implemented here, or change salt rules silently.
- Claim a nonce after cryptographic verification; keep the check and claim atomic
  in the single-process store. Do not claim cross-worker replay protection.
- `/agent-api/...` is protected; `/api/...` remains the public storefront API.
  Verify the external request before rewriting its target or Host.
- The local registry is not hosted VARS. Its integer IDs and domains are not
  Visa-issued identifiers or evidence of hosted registration policy. Use authorized
  hosted API documentation for those questions; do not publish private exports.
- Registry mutation endpoints and merchant demo endpoints do not provide a
  complete production authorization system. The legacy `/api/auth` helpers do
  not protect the product/cart/order routers.

## Make and verify changes

From the repository root, after installing the dependencies in the quickstart:

```bash
python scripts/check.py
npm --prefix merchant-frontend run build
```

The check runner performs local documentation checks, proxy tests, Python signing
tests, and registry SQLite tests. It does not contact hosted Visa services or
process payments. It sets `PYTHON` for the Node fixtures to the running interpreter.
Use the development guide to run only the relevant checks during iteration.

Keep changes focused. Update the relevant guide and `.env.example` when behavior
or configuration changes. Preserve existing user work. Never log, commit, or
paste private signing keys; generate throwaway keys for tests.

## Keep these guides useful

Keep this file short enough to read on entry. Put explanations in `docs/` and link
them from the index. Add new modules and tests to the task table when ownership
changes. Describe observed behavior separately from protocol requirements and
future work. Do not claim that an unrun browser/payment flow passed because the
signature unit tests passed.
