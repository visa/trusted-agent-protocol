"""
Pluggable DID resolution for the agent registry.

When an `AgentKey` row has `key_type == 'did'`, the registry does not store
the public key locally — instead, it stores the DID URI as the `key_id` and
resolves the corresponding DID Document at verification time.

This module defines:

  * `ResolvedKey`        — the normalized output of resolution: classical
                           algorithm + classical key bytes, plus an optional
                           ML-DSA-65 PQ key for hybrid signatures.
  * `DIDResolver`        — the abstract resolver interface.
  * `DIDResolverRegistry` — the dispatcher used by the registry. Operators
                           register resolvers explicitly per DID method.
  * `WebDIDResolver`     — reference resolver for `did:web:` per the W3C
                           DID Web spec (https://w3c-ccg.github.io/did-method-web/).
  * `TenzroDIDResolver`  — reference resolver for `did:tenzro:` against
                           Tenzro's TDIP identity registry over JSON-RPC.

`did:tenzro:` is included as ONE supported DID method, not THE supported
method. The dispatcher works for any DID method registered against it; the
two reference resolvers are illustrative.

Wire format references:
  - W3C did-core 1.0:        https://www.w3.org/TR/did-core/
  - W3C did:web spec:        https://w3c-ccg.github.io/did-method-web/
  - Tenzro TDIP DID format:  did:tenzro:human:{uuid} | did:tenzro:machine:{controller}:{uuid}
"""
from __future__ import annotations

import abc
import base64
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import quote

# `requests` is a top-level dependency of the agent-registry already
# (used elsewhere in the project for upstream calls). If it isn't, the
# resolvers below can be swapped to httpx/aiohttp without changing the
# DIDResolver interface.
import requests


# ---------------------------------------------------------------------------
# Resolution output
# ---------------------------------------------------------------------------

# Verification suite types we know how to map onto a signature algorithm.
# This list is intentionally small; resolvers MAY return others, in which
# case the registry's algorithm dispatcher decides whether it can use them.
_ED25519_SUITES = {
    "Ed25519VerificationKey2020",
    "Ed25519VerificationKey2018",
    "JsonWebKey2020",  # disambiguated by JWK `crv`
}
_ML_DSA_65_SUITES = {
    # Draft suite names tracked by the W3C VC working group / NIST PQC.
    "MlDsa65VerificationKey2026",
    "MlDsaVerificationKey2026",
    "MultikeyMlDsa65",
}


@dataclass
class ResolvedKey:
    """
    A normalized key ready to be handed to a signature verifier.

    `algorithm` is the RFC 9421 §6.2 algorithm string the registry would
    have stored had this key been registered as PEM (e.g. ``"ed25519"``,
    ``"ed25519-ml-dsa-65"``).

    `classical_pem` is a PEM-encoded public key (Ed25519 only in this
    reference impl) — same shape the rest of the registry already
    consumes for PEM-stored keys, so verification can stay protocol-
    agnostic.

    `pq_public_key_bytes` is the raw 1952-byte ML-DSA-65 verifying key
    when the resolved DID Document advertises one, or `None` otherwise.
    """

    algorithm: str
    classical_pem: str
    pq_public_key_bytes: Optional[bytes] = None
    raw_did_document: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class DIDResolutionError(Exception):
    """Raised when a DID cannot be resolved or its document is malformed."""


class DIDResolverNotRegistered(DIDResolutionError):
    """Raised when no resolver is registered for the requested DID method."""


# ---------------------------------------------------------------------------
# Abstract resolver interface
# ---------------------------------------------------------------------------


class DIDResolver(abc.ABC):
    """
    Abstract resolver. One instance per DID method.

    Implementors should be stateless and thread-safe; the registry shares
    a single instance across requests.
    """

    #: The DID method this resolver handles, e.g. "web", "tenzro".
    method: str

    @abc.abstractmethod
    def resolve(self, did: str) -> ResolvedKey:
        """
        Resolve a DID URI to a `ResolvedKey`.

        Implementations MUST raise `DIDResolutionError` on any failure
        (network error, malformed document, no usable verification
        method). They MUST NOT swallow errors — the registry decides
        the failure semantics (404 vs 500 vs cached fallback).
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Dispatch registry
# ---------------------------------------------------------------------------


class DIDResolverRegistry:
    """
    Operator-configured map of DID method -> resolver instance.

    The agent registry constructs one of these at startup and registers
    only the methods the deployment wants to support. There is no default
    list — resolvers must be registered explicitly. This is by design:
    a registry that silently resolves arbitrary DID methods is a privacy
    and supply-chain hazard.
    """

    def __init__(self) -> None:
        self._resolvers: Dict[str, DIDResolver] = {}

    def register(self, resolver: DIDResolver) -> None:
        if not resolver.method:
            raise ValueError("DIDResolver.method must be a non-empty string")
        self._resolvers[resolver.method] = resolver

    def resolve(self, did: str, method_hint: Optional[str] = None) -> ResolvedKey:
        method = method_hint or self._method_from_did(did)
        try:
            resolver = self._resolvers[method]
        except KeyError as exc:
            raise DIDResolverNotRegistered(
                f"No DIDResolver registered for method 'did:{method}:'"
            ) from exc
        return resolver.resolve(did)

    @staticmethod
    def _method_from_did(did: str) -> str:
        # did URI grammar: "did:" method ":" method-specific-id
        if not did.startswith("did:"):
            raise DIDResolutionError(f"Not a DID URI: {did!r}")
        parts = did.split(":", 2)
        if len(parts) < 3 or not parts[1]:
            raise DIDResolutionError(f"Malformed DID URI: {did!r}")
        return parts[1]


# ---------------------------------------------------------------------------
# Reference: did:web resolver
# ---------------------------------------------------------------------------


class WebDIDResolver(DIDResolver):
    """
    Resolves `did:web:example.com[:path:to:agent]` per the W3C DID Web spec.

    The DID `did:web:example.com` resolves to
    ``https://example.com/.well-known/did.json``; with a path component
    (``did:web:example.com:agents:alice``) it resolves to
    ``https://example.com/agents/alice/did.json``.

    This resolver is intentionally minimal — production deployments may
    want to add caching, retries, allowlists, etc.
    """

    method = "web"

    def __init__(self, *, timeout_s: float = 5.0, session: Optional[requests.Session] = None):
        self._timeout = timeout_s
        self._session = session or requests.Session()

    def resolve(self, did: str) -> ResolvedKey:
        url = self._did_to_url(did)
        try:
            resp = self._session.get(url, timeout=self._timeout)
        except requests.RequestException as exc:
            raise DIDResolutionError(f"did:web fetch failed for {did}: {exc}") from exc
        if resp.status_code != 200:
            raise DIDResolutionError(
                f"did:web fetch returned HTTP {resp.status_code} for {did} ({url})"
            )
        try:
            doc = resp.json()
        except ValueError as exc:
            raise DIDResolutionError(f"did:web document at {url} is not JSON: {exc}") from exc
        return _did_document_to_resolved_key(doc)

    @staticmethod
    def _did_to_url(did: str) -> str:
        if not did.startswith("did:web:"):
            raise DIDResolutionError(f"Not a did:web URI: {did!r}")
        rest = did[len("did:web:") :]
        # did:web allows percent-encoded host; canonical form is lowercase.
        # Path components are colon-separated in the DID; slash-separated
        # in the URL.
        if ":" in rest:
            host, *path = rest.split(":")
            path_str = "/" + "/".join(quote(p, safe="") for p in path) + "/did.json"
        else:
            host = rest
            path_str = "/.well-known/did.json"
        return f"https://{host}{path_str}"


# ---------------------------------------------------------------------------
# Reference: did:tenzro resolver
# ---------------------------------------------------------------------------


class TenzroDIDResolver(DIDResolver):
    """
    Resolves `did:tenzro:` against the Tenzro Network TDIP registry.

    Tenzro DIDs follow one of:
      - ``did:tenzro:human:{uuid}``
      - ``did:tenzro:machine:{controller}:{uuid}``
      - ``did:tenzro:machine:{uuid}``  (autonomous)

    The reference resolver calls the Tenzro JSON-RPC method
    ``tenzro_resolveDidDocument`` on a public RPC endpoint (default
    ``https://rpc.tenzro.network``), which returns a W3C DID Document
    matching the same shape this resolver consumes for did:web.

    Operators may point this resolver at any Tenzro RPC endpoint
    (testnet, mainnet, self-hosted node) by passing `rpc_url`. There is
    no implicit default beyond the public testnet — production deployments
    SHOULD use their own RPC node.
    """

    method = "tenzro"

    DEFAULT_RPC_URL = "https://rpc.tenzro.network"

    def __init__(
        self,
        *,
        rpc_url: str = DEFAULT_RPC_URL,
        timeout_s: float = 5.0,
        session: Optional[requests.Session] = None,
    ):
        self._rpc_url = rpc_url.rstrip("/")
        self._timeout = timeout_s
        self._session = session or requests.Session()

    def resolve(self, did: str) -> ResolvedKey:
        if not did.startswith("did:tenzro:"):
            raise DIDResolutionError(f"Not a did:tenzro URI: {did!r}")
        body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tenzro_resolveDidDocument",
            "params": {"did": did},
        }
        try:
            resp = self._session.post(self._rpc_url, json=body, timeout=self._timeout)
        except requests.RequestException as exc:
            raise DIDResolutionError(
                f"did:tenzro RPC call failed for {did} at {self._rpc_url}: {exc}"
            ) from exc
        if resp.status_code != 200:
            raise DIDResolutionError(
                f"did:tenzro RPC returned HTTP {resp.status_code} for {did}"
            )
        try:
            envelope = resp.json()
        except ValueError as exc:
            raise DIDResolutionError(f"did:tenzro RPC response not JSON: {exc}") from exc
        if "error" in envelope and envelope["error"]:
            raise DIDResolutionError(f"did:tenzro RPC error for {did}: {envelope['error']}")
        doc = envelope.get("result")
        if not isinstance(doc, dict):
            raise DIDResolutionError(
                f"did:tenzro RPC returned no DID Document for {did}"
            )
        return _did_document_to_resolved_key(doc)


# ---------------------------------------------------------------------------
# Shared DID Document → ResolvedKey extraction
# ---------------------------------------------------------------------------


def _did_document_to_resolved_key(doc: Dict[str, Any]) -> ResolvedKey:
    """
    Pull the first usable Ed25519 verification method out of a W3C DID
    Document, plus an ML-DSA-65 method if present, and project them onto
    a `ResolvedKey`.

    This implementation handles the two encodings the reference Tenzro
    impl emits today:
      * ``publicKeyMultibase`` (base58btc with leading 'z')
      * raw bytes via the W3C did-core "Multibase" rules

    JWK-based methods are deferred to a follow-up; the registry will
    raise `DIDResolutionError` if it can't find a usable key.
    """
    methods = doc.get("verificationMethod") or []
    if not isinstance(methods, list):
        raise DIDResolutionError("DID Document has no verificationMethod array")

    classical_pem: Optional[str] = None
    pq_bytes: Optional[bytes] = None

    for m in methods:
        mtype = m.get("type")
        key_bytes = _extract_key_bytes(m)
        if key_bytes is None:
            continue
        if mtype in _ED25519_SUITES and classical_pem is None:
            classical_pem = _ed25519_raw_to_pem(key_bytes)
        elif mtype in _ML_DSA_65_SUITES and pq_bytes is None:
            pq_bytes = key_bytes

    if classical_pem is None:
        raise DIDResolutionError(
            "DID Document has no Ed25519 verificationMethod the registry can use"
        )

    algorithm = "ed25519-ml-dsa-65" if pq_bytes is not None else "ed25519"
    return ResolvedKey(
        algorithm=algorithm,
        classical_pem=classical_pem,
        pq_public_key_bytes=pq_bytes,
        raw_did_document=doc,
    )


def _extract_key_bytes(method: Dict[str, Any]) -> Optional[bytes]:
    """Decode `publicKeyMultibase` (base58btc with 'z' prefix) into raw bytes."""
    mb = method.get("publicKeyMultibase")
    if isinstance(mb, str) and mb.startswith("z"):
        # Lazy import: base58 is not a transitive dep of agent-registry.
        try:
            import base58  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise DIDResolutionError(
                "did_resolver requires `base58` to decode publicKeyMultibase; "
                "install with `pip install base58`."
            ) from exc
        return bytes(base58.b58decode(mb[1:]))
    # Some implementations carry raw base64 instead. Tolerate it for
    # interop, but multibase is preferred.
    raw_b64 = method.get("publicKeyBase64")
    if isinstance(raw_b64, str):
        try:
            return base64.b64decode(raw_b64)
        except (ValueError, TypeError):
            return None
    return None


def _ed25519_raw_to_pem(raw32: bytes) -> str:
    """
    Wrap a 32-byte raw Ed25519 public key in a SubjectPublicKeyInfo PEM
    so the rest of the registry — which already speaks PEM — can verify
    against it without a separate code path.
    """
    if len(raw32) != 32:
        raise DIDResolutionError(
            f"Ed25519 raw public key must be 32 bytes, got {len(raw32)}"
        )
    # Lazy import: cryptography is already a dep of agent-registry for
    # PEM/Ed25519 verification, but importing at module load would couple
    # this file to it. Keeping it local makes the resolver testable in
    # isolation.
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519

    pubkey = ed25519.Ed25519PublicKey.from_public_bytes(raw32)
    pem = pubkey.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return pem.decode("ascii")


__all__ = [
    "DIDResolver",
    "DIDResolverRegistry",
    "DIDResolutionError",
    "DIDResolverNotRegistered",
    "ResolvedKey",
    "TenzroDIDResolver",
    "WebDIDResolver",
]
