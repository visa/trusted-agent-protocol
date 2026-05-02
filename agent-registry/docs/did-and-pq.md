# DID-based key IDs and post-quantum hybrid signatures

This document describes two additive extensions to the agent registry:

1. A `did:` URI as a `key_id`, resolved through a pluggable
   `DIDResolver` interface.
2. A composite `ed25519-ml-dsa-65` signing algorithm registered per the
   RFC 9421 §6.2 algorithm-registry extension pattern.

Both extensions are strictly additive. Existing registrations using
`algorithm: "ed25519"` or `algorithm: "rsa-pss-sha256"` with a PEM
public key keep working with no changes. No fields were removed; no
defaults changed.

---

## 1. DIDs as `key_id`

### Why

The v1 registry keys every row by `(domain, key_id)`, which couples
agent identity to DNS ownership. That is fine for short-lived,
domain-scoped agents; it breaks down for:

- Agents that move between domains (a payments agent that operates from
  multiple merchant subdomains under one logical identity)
- Agents whose principal does not own a stable domain (autonomous
  agents, subprocess agents inside hosted services)
- Long-lived agent identities that need to outlive any one DNS lease

W3C DIDs ([did-core 1.0](https://www.w3.org/TR/did-core/)) decouple
identifier from infrastructure, and most production agent frameworks
already issue DIDs to agents.

### Wire model

When `key_type == "did"`:

- `key_id` is a DID URI (e.g. `did:web:agent.example.com`,
  `did:tenzro:machine:01j8...:01j9...`).
- `public_key` is `null`.
- `did_method` selects the resolver (`web`, `tenzro`, ...).

The CDN proxy (`cdn-proxy/`) does not need to change: when it asks the
registry for a key it gets back a normal response with a PEM
`public_key` (and optionally `pq_public_key`). The DID is resolved
inside the registry.

### Resolver registration

There is **no default resolver list**. Operators register resolvers
explicitly at startup. The `did:web:` resolver is registered by default
because it is a pure W3C standard with no third-party trust
assumption; `did:tenzro:` is opt-in via environment variable:

```
# enable did:tenzro: resolution against the public Tenzro testnet
TAP_ENABLE_DID_TENZRO=1

# (optional) point at a self-hosted Tenzro RPC node
TAP_TENZRO_RPC_URL=https://rpc.your-tenzro-node.example
```

To plug in a new method, subclass `DIDResolver` and call
`registry.register(YourResolver())`.

### Reference: `did:web:`

`did:web:` is the W3C
[did:web spec](https://w3c-ccg.github.io/did-method-web/). The resolver
fetches `https://{host}/.well-known/did.json` (or the path-suffixed
variant) and extracts the first usable Ed25519 verification method.

CLI registration example:

```
curl -X POST http://localhost:8080/keys/ \
  -H 'Content-Type: application/json' \
  -d '{
    "domain": "merchant.example.com",
    "key_id": "did:web:agent.example.com",
    "key_type": "did",
    "did_method": "web",
    "algorithm": "ed25519"
  }'
```

### Reference: `did:tenzro:`

`did:tenzro:` resolves against the
[Tenzro Network TDIP](https://github.com/tenzro/tenzro-network) identity
registry. The resolver issues a JSON-RPC call to the Tenzro node:

```json
{
  "jsonrpc": "2.0",
  "method": "tenzro_resolveDidDocument",
  "params": {"did": "did:tenzro:machine:01j8..."},
  "id": 1
}
```

The response is a W3C DID Document. The Tenzro implementation always
emits both an Ed25519 verification method and an ML-DSA-65
verification method (suite `MlDsa65VerificationKey2026`), so a
`did:tenzro:` row registered with `algorithm: "ed25519"` will be
upgraded to `ed25519-ml-dsa-65` automatically when the resolver finds
both methods in the document.

```
curl -X POST http://localhost:8080/keys/ \
  -H 'Content-Type: application/json' \
  -d '{
    "domain": "merchant.example.com",
    "key_id": "did:tenzro:machine:01j8...:01j9...",
    "key_type": "did",
    "did_method": "tenzro",
    "algorithm": "ed25519"
  }'
```

`did:tenzro:` is **one** supported method; the resolver interface is
pluggable for any DID method (did:key, did:plc, did:ion, did:ethr, etc.).

---

## 2. Hybrid `ed25519-ml-dsa-65`

### Why

The NIST PQC standardization process culminated in FIPS 203 (ML-KEM)
and FIPS 204 (ML-DSA) in 2024–2025. NIST SP 800-227 calls for a
classical+PQ hybrid window during migration so that a CRQC
(cryptographically relevant quantum computer) cannot retrospectively
forge signatures, but a flaw in the PQ scheme alone does not give an
attacker a forgery either. Both legs must verify.

The same construction is already in production at Tenzro Network for
its consensus signatures; this PR ports just the algorithm dispatcher
into TAP so any agent registry deployment can opt in.

### Algorithm string (RFC 9421 §6.2)

The string `ed25519-ml-dsa-65` is registered following the RFC 9421
§6.2 pattern (algorithm names are application-defined and selected by
the registry/verifier; the spec only requires that all parties agree).
Both signatures cover the same Sig-Base bytes per RFC 9421 §3.3.

### Wire format

The HTTP `Signature` header carries one Base64 blob: the concatenation
of the two raw signatures, fixed-width by spec.

```
sig_raw = ed25519_sig (64 bytes) || ml_dsa_65_sig (3309 bytes)
        = 3373 bytes total
sig_b64 = base64(sig_raw)        // 4500 chars
```

Public keys:

- `public_key`: PEM-encoded Ed25519 SubjectPublicKeyInfo (32 bytes raw).
- `pq_public_key`: Base64-encoded raw ML-DSA-65 verifying key (1952
  bytes per FIPS 204 §4 Table 2).

### Soft dependency: `oqs`

ML-DSA-65 verification uses
[`liboqs-python`](https://github.com/open-quantum-safe/liboqs-python)
(`pip install oqs`, plus a system-level liboqs install). It is **not**
a hard dependency of the agent registry: the import is lazy and
hybrid verification fails closed (HTTP 503) when `oqs` is absent. All
other algorithms continue to work unaffected.

### Algorithm fallback rule

Hybrid is fail-closed by design: if either leg fails, verification
fails. If `oqs` is not installed, the registry rejects hybrid
verification with 503 — it does NOT fall back to classical-only,
because that would defeat the point of registering a hybrid algorithm.

### Registration example

```
curl -X POST http://localhost:8080/keys/ \
  -H 'Content-Type: application/json' \
  -d '{
    "domain": "merchant.example.com",
    "key_id": "agent-2026-pq",
    "key_type": "pem",
    "algorithm": "ed25519-ml-dsa-65",
    "public_key": "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEA...\n-----END PUBLIC KEY-----\n",
    "pq_public_key": "<base64 of 1952-byte ML-DSA-65 vk>"
  }'
```

---

## 3. Migration notes

Existing rows are unaffected:

| Existing column | After this PR | Behavior |
|---|---|---|
| `domain` | unchanged | unchanged |
| `key_id` | widened from 255 to 1024 | DID URIs fit |
| `algorithm` | unchanged | new value `ed25519-ml-dsa-65` accepted alongside existing |
| `public_key` | now nullable | required when `key_type == 'pem'` |
| `key_type` (NEW) | defaults to `'pem'` via `server_default` | existing rows materialize as `'pem'` |
| `did_method` (NEW) | nullable | NULL for `'pem'` rows |
| `pq_public_key` (NEW) | nullable | NULL unless registering hybrid PEM |

A database migration that just runs `ALTER TABLE ... ADD COLUMN ...
DEFAULT 'pem'` over the existing schema covers all existing rows. No
data backfill is required.

---

## 4. References

- RFC 9421 — HTTP Message Signatures: https://www.rfc-editor.org/rfc/rfc9421
  - §3.3 Signing Algorithms
  - §6.2 Signature Algorithms registry extension pattern
  - §7 Security Considerations
- RFC 8032 — Edwards-Curve Digital Signature Algorithm (Ed25519): https://www.rfc-editor.org/rfc/rfc8032
- NIST FIPS 204 — ML-DSA: https://csrc.nist.gov/pubs/fips/204/final
- NIST SP 800-227 — Post-Quantum Cryptography Migration Guidance
- W3C did-core 1.0: https://www.w3.org/TR/did-core/
- W3C did:web spec: https://w3c-ccg.github.io/did-method-web/
- liboqs-python: https://github.com/open-quantum-safe/liboqs-python
