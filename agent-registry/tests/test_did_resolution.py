"""
Tests for the DID resolver dispatch and the two reference resolvers.

These tests do NOT hit the network. The W3C did:web fetch and the
Tenzro JSON-RPC call are stubbed via a fake `requests.Session` so the
suite stays hermetic.

Pytest is the existing test framework for agent-registry; no new
fixtures or plugins are required.
"""
from __future__ import annotations

import base64
import json
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

# The agent-registry is a flat-module project (`from database import Base`,
# etc.), so we import the same way. Run pytest from `agent-registry/`
# or set `PYTHONPATH=agent-registry` so the modules resolve.
from did_resolver import (  # type: ignore[import-not-found]
    DIDResolutionError,
    DIDResolverNotRegistered,
    DIDResolverRegistry,
    ResolvedKey,
    TenzroDIDResolver,
    WebDIDResolver,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


# A 32-byte Ed25519 raw public key (deterministic test vector — NOT a
# real key; just 32 bytes that decode cleanly through cryptography).
ED25519_RAW = bytes(range(32))
# A 1952-byte ML-DSA-65 raw verifying key placeholder. The verifier in
# `sig_algorithms.py` checks length only when actually invoked, so a
# byte-pattern of the right length is fine for resolver tests.
ML_DSA_65_RAW = bytes((i % 256 for i in range(1952)))


def _multibase_b58(raw: bytes) -> str:
    import base58  # test dep, declared in test requirements

    return "z" + base58.b58encode(raw).decode("ascii")


def _did_doc_with_ed25519_only(did: str) -> Dict[str, Any]:
    return {
        "@context": ["https://www.w3.org/ns/did/v1"],
        "id": did,
        "verificationMethod": [
            {
                "id": f"{did}#key-1",
                "type": "Ed25519VerificationKey2020",
                "controller": did,
                "publicKeyMultibase": _multibase_b58(ED25519_RAW),
            }
        ],
        "authentication": [f"{did}#key-1"],
    }


def _did_doc_with_hybrid(did: str) -> Dict[str, Any]:
    doc = _did_doc_with_ed25519_only(did)
    doc["verificationMethod"].append(
        {
            "id": f"{did}#pq-key-1",
            "type": "MlDsa65VerificationKey2026",
            "controller": did,
            "publicKeyMultibase": _multibase_b58(ML_DSA_65_RAW),
        }
    )
    return doc


# ---------------------------------------------------------------------------
# Registry dispatch
# ---------------------------------------------------------------------------


def test_registry_rejects_unregistered_method():
    reg = DIDResolverRegistry()
    with pytest.raises(DIDResolverNotRegistered):
        reg.resolve("did:key:zABC")


def test_registry_rejects_non_did_uri():
    reg = DIDResolverRegistry()
    with pytest.raises(DIDResolutionError):
        reg.resolve("https://example.com/agent")


def test_registry_dispatches_by_method():
    reg = DIDResolverRegistry()
    fake = MagicMock(spec=WebDIDResolver)
    fake.method = "web"
    fake.resolve.return_value = ResolvedKey(
        algorithm="ed25519",
        classical_pem="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----\n",
    )
    reg.register(fake)

    out = reg.resolve("did:web:agent.example.com")
    assert out.algorithm == "ed25519"
    fake.resolve.assert_called_once_with("did:web:agent.example.com")


def test_registry_method_hint_overrides_did_prefix():
    """A row with did_method='tenzro' must dispatch to the tenzro resolver."""
    reg = DIDResolverRegistry()
    web = MagicMock(spec=WebDIDResolver)
    web.method = "web"
    tenzro = MagicMock(spec=TenzroDIDResolver)
    tenzro.method = "tenzro"
    tenzro.resolve.return_value = ResolvedKey(
        algorithm="ed25519-ml-dsa-65",
        classical_pem="pem",
        pq_public_key_bytes=ML_DSA_65_RAW,
    )
    reg.register(web)
    reg.register(tenzro)

    out = reg.resolve("did:tenzro:machine:01j8", method_hint="tenzro")
    assert out.algorithm == "ed25519-ml-dsa-65"
    tenzro.resolve.assert_called_once()
    web.resolve.assert_not_called()


# ---------------------------------------------------------------------------
# WebDIDResolver
# ---------------------------------------------------------------------------


class _FakeResp:
    def __init__(self, status_code: int, body: Any):
        self.status_code = status_code
        self._body = body

    def json(self):
        if isinstance(self._body, str):
            raise ValueError("not json")
        return self._body


class _FakeSession:
    def __init__(self, get_response: _FakeResp):
        self._get_response = get_response
        self.last_url = None

    def get(self, url, timeout=None):
        self.last_url = url
        return self._get_response

    def post(self, url, json=None, timeout=None):
        self.last_url = url
        self.last_body = json
        return self._get_response


def test_web_resolver_uses_well_known_path_for_bare_host():
    did = "did:web:agent.example.com"
    sess = _FakeSession(_FakeResp(200, _did_doc_with_ed25519_only(did)))
    r = WebDIDResolver(session=sess)  # type: ignore[arg-type]

    out = r.resolve(did)
    assert sess.last_url == "https://agent.example.com/.well-known/did.json"
    assert out.algorithm == "ed25519"
    assert "BEGIN PUBLIC KEY" in out.classical_pem


def test_web_resolver_uses_path_form_for_subpath_did():
    did = "did:web:example.com:agents:alice"
    sess = _FakeSession(_FakeResp(200, _did_doc_with_ed25519_only(did)))
    r = WebDIDResolver(session=sess)  # type: ignore[arg-type]

    r.resolve(did)
    assert sess.last_url == "https://example.com/agents/alice/did.json"


def test_web_resolver_promotes_to_hybrid_when_pq_method_present():
    did = "did:web:agent.example.com"
    sess = _FakeSession(_FakeResp(200, _did_doc_with_hybrid(did)))
    r = WebDIDResolver(session=sess)  # type: ignore[arg-type]

    out = r.resolve(did)
    assert out.algorithm == "ed25519-ml-dsa-65"
    assert out.pq_public_key_bytes == ML_DSA_65_RAW


def test_web_resolver_propagates_http_errors():
    did = "did:web:agent.example.com"
    sess = _FakeSession(_FakeResp(404, ""))
    r = WebDIDResolver(session=sess)  # type: ignore[arg-type]

    with pytest.raises(DIDResolutionError):
        r.resolve(did)


def test_web_resolver_rejects_non_did_web():
    r = WebDIDResolver(session=_FakeSession(_FakeResp(200, {})))  # type: ignore[arg-type]
    with pytest.raises(DIDResolutionError):
        r.resolve("did:tenzro:machine:01j8")


# ---------------------------------------------------------------------------
# TenzroDIDResolver
# ---------------------------------------------------------------------------


def test_tenzro_resolver_calls_jsonrpc_with_correct_method():
    did = "did:tenzro:machine:01j8...:01j9..."
    envelope = {"jsonrpc": "2.0", "id": 1, "result": _did_doc_with_hybrid(did)}
    sess = _FakeSession(_FakeResp(200, envelope))
    r = TenzroDIDResolver(rpc_url="https://rpc.tenzro.network", session=sess)  # type: ignore[arg-type]

    out = r.resolve(did)
    assert sess.last_url == "https://rpc.tenzro.network"
    assert sess.last_body["method"] == "tenzro_resolveDidDocument"
    assert sess.last_body["params"] == {"did": did}
    assert out.algorithm == "ed25519-ml-dsa-65"
    assert out.pq_public_key_bytes == ML_DSA_65_RAW


def test_tenzro_resolver_propagates_jsonrpc_error():
    did = "did:tenzro:machine:bogus"
    envelope = {"jsonrpc": "2.0", "id": 1, "error": {"code": -32000, "message": "not found"}}
    sess = _FakeSession(_FakeResp(200, envelope))
    r = TenzroDIDResolver(rpc_url="https://rpc.tenzro.network", session=sess)  # type: ignore[arg-type]

    with pytest.raises(DIDResolutionError) as ei:
        r.resolve(did)
    assert "not found" in str(ei.value)


def test_tenzro_resolver_rejects_missing_result():
    did = "did:tenzro:machine:01j8"
    envelope = {"jsonrpc": "2.0", "id": 1}
    sess = _FakeSession(_FakeResp(200, envelope))
    r = TenzroDIDResolver(rpc_url="https://rpc.tenzro.network", session=sess)  # type: ignore[arg-type]

    with pytest.raises(DIDResolutionError):
        r.resolve(did)


def test_tenzro_resolver_rejects_non_tenzro_did():
    sess = _FakeSession(_FakeResp(200, {}))
    r = TenzroDIDResolver(rpc_url="https://rpc.tenzro.network", session=sess)  # type: ignore[arg-type]
    with pytest.raises(DIDResolutionError):
        r.resolve("did:web:agent.example.com")


# ---------------------------------------------------------------------------
# Document parsing edge cases
# ---------------------------------------------------------------------------


def test_document_without_ed25519_method_fails():
    did = "did:web:agent.example.com"
    doc = {
        "id": did,
        "verificationMethod": [
            {
                "id": f"{did}#x",
                "type": "X25519KeyAgreementKey2020",
                "controller": did,
                "publicKeyMultibase": _multibase_b58(ED25519_RAW),
            }
        ],
    }
    sess = _FakeSession(_FakeResp(200, doc))
    r = WebDIDResolver(session=sess)  # type: ignore[arg-type]

    with pytest.raises(DIDResolutionError):
        r.resolve(did)
