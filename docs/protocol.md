# TAP and HTTP signature guide

## Sources and precedence

| Question | Authoritative starting point |
| --- | --- |
| TAP interaction fields and merchant policy | [Visa TAP merchant specifications](https://developer.visa.com/docs/trusted-agent-protocol/trusted-agent-protocol-specifications) |
| HTTP signature base, Structured Fields, derived components | [RFC 9421](https://www.rfc-editor.org/rfc/rfc9421.html), especially sections 2, 3, and 7 |
| RFC status and errata | [RFC Editor information page](https://www.rfc-editor.org/info/rfc9421/) |
| Registered algorithms and metadata names | [IANA HTTP Message Signature registry](https://www.iana.org/assignments/http-message-signature/) |
| Local behavior | Source and regression tests in this checkout |
| Hosted Visa registration and key lifecycle | The authorized hosted API documentation for the environment in question |

Public sources were checked on 2026-11-24. Recheck them when changing protocol
behavior. This date records a review, not a guarantee that remote pages stay fixed.
Do not infer hosted capabilities from this local registry or copy private API
exports into the public repository.

Visa's public page contains examples with inconsistent `keyId`/`keyid`, timestamp
intervals, and signature-base formatting. Follow its stated eight-minute maximum
and RFC 9421's serialization rules. Keep the discrepancy explicit in an issue or
test instead of copying an illustrative base string verbatim.

## The local request-recognition profile

The proxy requires `Signature-Input` and `Signature` dictionaries with matching
labels, and exactly one applicable TAP signature. Other protocol signatures may
coexist. The TAP signature must cover unparameterized `@authority` and `@path` and
include `created`, `expires`, `keyid`, `alg`, `nonce`, and `tag`.

- Timestamps are integer epoch seconds. Creation cannot be in the future; expiry
  must be in the future and later than creation. Lifetime is at most 480 seconds.
- Tags are `agent-browser-auth` or `agent-payer-auth`. A payer tag alone does not
  authorize a charge or prove consumer consent.
- The key and parent agent must be active. Key algorithm metadata must match the
  selected algorithm. The local registry uses the strings `"true"` and `"false"`.
- A nonce is scoped to its signing key, claimed after signature verification,
  and retained until expiry. The store is single-process and is lost on restart.
- Registry transport failures produce 503; invalid, expired, or replayed proofs
  are rejected with 403. Retrying after an outage requires a still-current proof.

## Construct the base correctly

`Signature-Input` holds a dictionary member such as
`proof=("@authority" "@path");created=...;...`. The label `proof=` is **not** part
of the serialized Inner List used for the `@signature-params` line.

An illustrative base has this shape; placeholders are not a usable signature:

```text
"@authority": localhost:3001
"@path": /agent-api/products/
"@signature-params": ("@authority" "@path");created=...;expires=...;keyid="...";alg="ed25519";nonce="...";tag="agent-browser-auth"
```

Sign the canonical base bytes. Formatting whitespace in a received HTTP header
is not copied verbatim into the signed parameters. Preserve parameter order and
values while serializing them. Both headers must use the same signature label.

The Python helper `tap-agent/tap_signature.py` builds the minimum profile. The
Node verifier uses a Structured Fields parser and serializer. Its tests verify
the actual Python signing functions with independently generated keys.

## Supported coverage and key formats

| Item | Sample behavior |
| --- | --- |
| `@authority` | Host and non-default port derived from the external request |
| `@path` | Encoded absolute path, excluding query |
| `@method`, `@scheme`, `@query` | Reconstructed when covered; method case and encoded query are preserved |
| Lowercase HTTP fields | Reconstructed when present; a Structured Fields dictionary member may use `;key="member"` |
| Other components or qualifiers | Rejected when unsupported; never silently skipped |
| Ed25519 | Raw 32-byte public key in standard Base64; private UI key is raw 32-byte Base64 |
| Legacy RSA-PSS/SHA-256 | PEM public/private keys, SHA-256/MGF1-SHA-256 and maximum salt |

The sample accepts `alg="Ed25519"` from Visa's examples without changing that
declared spelling in canonical parameters; its signer emits `ed25519`. The
registry's historical `RSA-SHA256` metadata aliases its existing legacy RSA-PSS
keys. This is **not** the registered `rsa-pss-sha512` algorithm. Algorithms listed
in hosted documentation or IANA are not automatically implemented by this sample.

Wire `keyid`, registry `key_id`, and the browser UI's internal `keyId` are
different representations. Keep the HTTP spelling lowercase.

## Bind the operation you mean to authorize

The minimum signature does not cover method, query, or body. If these affect an
operation, define additional coverage and verification policy. Signing a
`Content-Digest` field also requires checking that digest against the received
body; this sample does not perform that body check automatically. Separately
signed consumer/payment body objects require their own verification.

Sign the external `/agent-api/...` path, not its rewritten backend `/api/...`
path. Redirects change the target and need new proofs. A proxy deployment must
derive the external authority/scheme from a trusted configuration; accepting
arbitrary forwarded headers is not a solution.

Use [the local demonstration](quickstart.md) to verify the supported request
recognition flow. Use the actual hosted API documentation for hosted lifecycle,
TRID, registration, or additional algorithm questions.
