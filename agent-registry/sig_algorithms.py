"""
Signature algorithm dispatch for the agent registry.

This module is a small, additive layer on top of the existing
PEM-based Ed25519 / RSA-PSS-SHA256 verifiers shipped in
`agent-registry/`. It introduces one new algorithm string,
``ed25519-ml-dsa-65``, defined per the RFC 9421 §6.2 algorithm registry
extension pattern (see https://www.rfc-editor.org/rfc/rfc9421#section-6.2).

The composite algorithm signs and verifies the SAME RFC 9421 Sig-Base
twice — once with Ed25519 (RFC 8032), once with ML-DSA-65 (NIST
FIPS 204) — and BOTH legs must validate for the verification to succeed.
The wire signature is the concatenation:

    sig = ed25519_sig (64 bytes) || ml_dsa_65_sig (3309 bytes)

This matches the construction Tenzro Network ships in production for its
hybrid-PQ migration window and follows NIST SP 800-227 PQC transition
guidance: an attacker must break BOTH the classical curve AND the
lattice scheme to forge.

Soft dependency
---------------

ML-DSA support is provided by ``oqs`` (the Python binding for Open
Quantum Safe's liboqs, https://github.com/open-quantum-safe/liboqs-python).
``oqs`` is NOT a hard dependency of the agent registry: the import is
done lazily inside `_oqs_module()`, and any verification call against
``ed25519-ml-dsa-65`` raises `HybridUnavailable` (which the registry
maps to a 503) if liboqs isn't installed. All other algorithms continue
to work unaffected.

Operators who want to enable hybrid PQ verification install with::

    pip install oqs

(and ensure liboqs is installed at the system level — see the
liboqs-python README).

Wire format
-----------

The hybrid signature on the wire is a single Base64-encoded blob: the
concatenation of the two raw signatures, fixed-width by spec:

    [ ed25519: 64 bytes ][ ml_dsa_65: 3309 bytes ]
    => total: 3373 bytes raw, 4500 chars Base64.

The classical and PQ public keys are stored separately on the
`AgentKey` row (`public_key` for the Ed25519 PEM, `pq_public_key` for
the ML-DSA-65 raw verifying key, Base64-encoded). When the key is
sourced from a DID Document, both legs come out of `ResolvedKey`.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Optional

# `cryptography` is already a dep of agent-registry for the existing
# Ed25519 / RSA-PSS verification paths.
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


# ---------------------------------------------------------------------------
# Constants (FIPS 204 §4 Table 2 — ML-DSA-65 parameter set)
# ---------------------------------------------------------------------------

#: Algorithm string registered per RFC 9421 §6.2 extension pattern.
HYBRID_ALG = "ed25519-ml-dsa-65"

#: Ed25519 raw signature length (RFC 8032 §3.1, fixed).
ED25519_SIG_LEN = 64

#: ML-DSA-65 signature length in bytes (FIPS 204 §4 Table 2).
ML_DSA_65_SIG_LEN = 3309

#: ML-DSA-65 verifying-key length in bytes (FIPS 204 §4 Table 2).
ML_DSA_65_VK_LEN = 1952

#: Combined hybrid signature length on the wire (raw, pre-Base64).
HYBRID_SIG_LEN = ED25519_SIG_LEN + ML_DSA_65_SIG_LEN  # 3373

#: liboqs algorithm identifier for the FIPS 204 standardized scheme.
#: liboqs uses "ML-DSA-65" (with hyphen) in its Signature constructor.
_OQS_ALG_NAME = "ML-DSA-65"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class HybridUnavailable(RuntimeError):
    """
    Raised when ``ed25519-ml-dsa-65`` is invoked but `oqs` (and therefore
    liboqs) is not installed. Operators MUST install ``oqs`` to enable
    hybrid PQ. The error is fail-closed by design — silently falling
    back to classical-only would defeat the point of registering a
    hybrid algorithm.
    """


class HybridVerificationError(Exception):
    """
    Raised when either leg of the hybrid signature fails to verify, or
    when input lengths/encodings are wrong. Both legs MUST pass for
    success; anything else is a hard fail.
    """


# ---------------------------------------------------------------------------
# Soft import of `oqs`
# ---------------------------------------------------------------------------


def _oqs_module():
    """
    Lazy import so the agent registry runs without `oqs` installed.

    Returns the `oqs` module on success; raises `HybridUnavailable`
    otherwise. Callers MUST handle the exception — the dispatcher in
    `main.py` maps it to a 503.
    """
    try:
        import oqs  # type: ignore
    except ImportError as exc:
        raise HybridUnavailable(
            "Hybrid algorithm 'ed25519-ml-dsa-65' requires the `oqs` Python "
            "package and a system-level liboqs install. See "
            "https://github.com/open-quantum-safe/liboqs-python."
        ) from exc
    return oqs


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HybridKey:
    """
    A pair of public keys used by the verifier.

    `ed25519_pem` is a PEM-encoded SubjectPublicKeyInfo holding the
    Ed25519 verifying key (32 bytes raw). This is the same encoding the
    registry already uses for ``algorithm == 'ed25519'``.

    `ml_dsa_65_raw` is the raw 1952-byte ML-DSA-65 verifying key per
    FIPS 204 §4 Table 2. Stored Base64-encoded on the `AgentKey` row
    (column ``pq_public_key``); decode before passing here.
    """

    ed25519_pem: str
    ml_dsa_65_raw: bytes


# ---------------------------------------------------------------------------
# Verifier
# ---------------------------------------------------------------------------


def verify_hybrid(
    *,
    sig_base: bytes,
    signature: bytes,
    key: HybridKey,
) -> None:
    """
    Verify a composite ``ed25519-ml-dsa-65`` signature.

    Per RFC 9421 §3.3, both signatures are computed over the SAME
    Sig-Base bytes (the canonicalized signature input string the
    verifier reconstructs from the request). Both MUST verify for
    success. Returns `None` on success; raises `HybridVerificationError`
    on any failure.

    Parameters
    ----------
    sig_base
        The exact bytes of the RFC 9421 Sig-Base string. The caller is
        responsible for canonicalization — this function is pure crypto.
    signature
        Raw concatenation: ed25519_sig (64B) || ml_dsa_65_sig (3309B).
        Total length MUST be exactly `HYBRID_SIG_LEN` (3373).
    key
        Both verifying keys.
    """
    if len(signature) != HYBRID_SIG_LEN:
        raise HybridVerificationError(
            f"Hybrid signature length must be {HYBRID_SIG_LEN} bytes "
            f"({ED25519_SIG_LEN} ed25519 + {ML_DSA_65_SIG_LEN} ml-dsa-65); "
            f"got {len(signature)}"
        )
    if len(key.ml_dsa_65_raw) != ML_DSA_65_VK_LEN:
        raise HybridVerificationError(
            f"ML-DSA-65 verifying key must be {ML_DSA_65_VK_LEN} bytes; "
            f"got {len(key.ml_dsa_65_raw)}"
        )

    ed_sig = signature[:ED25519_SIG_LEN]
    pq_sig = signature[ED25519_SIG_LEN:]

    # --- Classical leg ---
    try:
        ed_pub = serialization.load_pem_public_key(key.ed25519_pem.encode("ascii"))
    except (ValueError, TypeError) as exc:
        raise HybridVerificationError(f"invalid Ed25519 PEM: {exc}") from exc
    if not isinstance(ed_pub, ed25519.Ed25519PublicKey):
        raise HybridVerificationError(
            "PEM is not an Ed25519 public key; check `algorithm` column"
        )
    try:
        ed_pub.verify(ed_sig, sig_base)
    except InvalidSignature as exc:
        raise HybridVerificationError("Ed25519 signature did not verify") from exc

    # --- Post-quantum leg ---
    oqs = _oqs_module()
    # liboqs's Python binding uses a context manager and reuses one
    # `Signature` instance per verification.
    with oqs.Signature(_OQS_ALG_NAME) as verifier:
        if not verifier.verify(sig_base, pq_sig, key.ml_dsa_65_raw):
            raise HybridVerificationError("ML-DSA-65 signature did not verify")


# ---------------------------------------------------------------------------
# Signer (reference implementation, used by tests and tooling — the
# registry itself is verify-only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HybridSecret:
    """
    Pair of secrets used by the reference signer. Not used by the
    agent-registry server itself (which only verifies); kept here so
    the test suite and any operator tooling have a single place to
    compose hybrid signatures correctly.
    """

    ed25519_pem: str  # PEM-encoded PKCS#8 private key
    ml_dsa_65_secret: bytes  # raw ML-DSA-65 secret-key bytes


def sign_hybrid(*, sig_base: bytes, secret: HybridSecret) -> bytes:
    """
    Produce a composite signature: ed25519_sig || ml_dsa_65_sig.

    Both signatures are computed over the same `sig_base` (RFC 9421
    §3.3). The caller is responsible for canonicalization.
    """
    # Classical leg
    try:
        ed_priv = serialization.load_pem_private_key(
            secret.ed25519_pem.encode("ascii"), password=None
        )
    except (ValueError, TypeError) as exc:
        raise HybridVerificationError(f"invalid Ed25519 PEM private key: {exc}") from exc
    if not isinstance(ed_priv, ed25519.Ed25519PrivateKey):
        raise HybridVerificationError("PEM is not an Ed25519 private key")
    ed_sig = ed_priv.sign(sig_base)
    if len(ed_sig) != ED25519_SIG_LEN:
        # cryptography always returns 64 bytes for Ed25519, but be defensive.
        raise HybridVerificationError("Ed25519 sign produced wrong-length signature")

    # PQ leg
    oqs = _oqs_module()
    with oqs.Signature(_OQS_ALG_NAME, secret.ml_dsa_65_secret) as signer:
        pq_sig = signer.sign(sig_base)
    if len(pq_sig) != ML_DSA_65_SIG_LEN:
        raise HybridVerificationError(
            f"ML-DSA-65 sign produced {len(pq_sig)} bytes, expected {ML_DSA_65_SIG_LEN}"
        )

    return ed_sig + pq_sig


# ---------------------------------------------------------------------------
# Convenience encoders
# ---------------------------------------------------------------------------


def encode_hybrid_signature(sig: bytes) -> str:
    """Base64-encode a raw hybrid signature for HTTP transport."""
    if len(sig) != HYBRID_SIG_LEN:
        raise HybridVerificationError(
            f"refusing to encode hybrid signature of wrong length {len(sig)}"
        )
    return base64.b64encode(sig).decode("ascii")


def decode_hybrid_signature(b64: str) -> bytes:
    """Decode a Base64 hybrid signature; validates length on the way out."""
    try:
        raw = base64.b64decode(b64, validate=True)
    except (ValueError, TypeError) as exc:
        raise HybridVerificationError(f"hybrid signature is not valid Base64: {exc}") from exc
    if len(raw) != HYBRID_SIG_LEN:
        raise HybridVerificationError(
            f"decoded hybrid signature is {len(raw)} bytes, expected {HYBRID_SIG_LEN}"
        )
    return raw


__all__ = [
    "HYBRID_ALG",
    "HYBRID_SIG_LEN",
    "ED25519_SIG_LEN",
    "ML_DSA_65_SIG_LEN",
    "ML_DSA_65_VK_LEN",
    "HybridKey",
    "HybridSecret",
    "HybridUnavailable",
    "HybridVerificationError",
    "verify_hybrid",
    "sign_hybrid",
    "encode_hybrid_signature",
    "decode_hybrid_signature",
]
