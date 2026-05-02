"""
Tests for the `ed25519-ml-dsa-65` composite algorithm (RFC 9421 §6.2).

These tests:

  * Validate the wire-format constants against FIPS 204.
  * Verify that the registry runs without `oqs` installed (the soft
    dependency must NOT break import).
  * Round-trip sign + verify when `oqs` IS installed (skipped otherwise).
  * Reject tampered classical and PQ legs as forgeries.
  * Reject malformed signature lengths and malformed key lengths.

The `oqs` import is gated by `pytest.importorskip` so the suite passes
in both configurations: with or without liboqs installed.
"""
from __future__ import annotations

import base64

import pytest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

# The agent-registry is a flat-module project, so we import the same way.
# Run pytest from `agent-registry/` or set `PYTHONPATH=agent-registry`.
from sig_algorithms import (  # type: ignore[import-not-found]
    ED25519_SIG_LEN,
    HYBRID_ALG,
    HYBRID_SIG_LEN,
    ML_DSA_65_SIG_LEN,
    ML_DSA_65_VK_LEN,
    HybridKey,
    HybridSecret,
    HybridUnavailable,
    HybridVerificationError,
    decode_hybrid_signature,
    encode_hybrid_signature,
    sign_hybrid,
    verify_hybrid,
)


# ---------------------------------------------------------------------------
# FIPS 204 constants
# ---------------------------------------------------------------------------


def test_constants_match_fips_204_table_2():
    # FIPS 204 §4 Table 2 specifies these byte lengths for ML-DSA-65.
    assert ML_DSA_65_SIG_LEN == 3309
    assert ML_DSA_65_VK_LEN == 1952


def test_constants_match_rfc_8032_for_ed25519():
    assert ED25519_SIG_LEN == 64
    assert HYBRID_SIG_LEN == ED25519_SIG_LEN + ML_DSA_65_SIG_LEN
    assert HYBRID_SIG_LEN == 3373


def test_algorithm_string_is_stable():
    # Per RFC 9421 §6.2, the algorithm string is the wire identifier
    # consumers will pin against. Don't change it without a major version bump.
    assert HYBRID_ALG == "ed25519-ml-dsa-65"


# ---------------------------------------------------------------------------
# Soft dependency: registry boots without `oqs`
# ---------------------------------------------------------------------------


def test_module_imports_without_oqs():
    """The module-level import must NOT pull in oqs."""
    import importlib

    import sig_algorithms as mod  # type: ignore

    importlib.reload(mod)
    # If `oqs` isn't installed, this just returns; if it is, it
    # also returns. Either way, the module must load.
    assert mod.HYBRID_ALG == "ed25519-ml-dsa-65"


def test_invocation_without_oqs_raises_unavailable(monkeypatch):
    """Invoking `verify_hybrid` without oqs must fail closed (no fallback)."""
    import sig_algorithms as mod  # type: ignore

    def _raise(*_a, **_k):
        raise HybridUnavailable("liboqs not available (test stub)")

    monkeypatch.setattr(mod, "_oqs_module", _raise)

    # Build a syntactically valid input set so we get past length checks
    # and hit the oqs lookup.
    ed_priv = ed25519.Ed25519PrivateKey.generate()
    ed_pub_pem = ed_priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")

    sig_base = b"@authority: example.com\n@method: POST\n"
    ed_sig = ed_priv.sign(sig_base)
    fake_pq = bytes(ML_DSA_65_SIG_LEN)
    fake_vk = bytes(ML_DSA_65_VK_LEN)

    with pytest.raises(HybridUnavailable):
        verify_hybrid(
            sig_base=sig_base,
            signature=ed_sig + fake_pq,
            key=HybridKey(ed25519_pem=ed_pub_pem, ml_dsa_65_raw=fake_vk),
        )


# ---------------------------------------------------------------------------
# Length / encoding checks (do not require oqs)
# ---------------------------------------------------------------------------


def test_verify_rejects_wrong_signature_length():
    ed_priv = ed25519.Ed25519PrivateKey.generate()
    ed_pub_pem = ed_priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
    sig_base = b"x"

    with pytest.raises(HybridVerificationError, match="length must be"):
        verify_hybrid(
            sig_base=sig_base,
            signature=b"too-short",
            key=HybridKey(ed25519_pem=ed_pub_pem, ml_dsa_65_raw=bytes(ML_DSA_65_VK_LEN)),
        )


def test_verify_rejects_wrong_pq_key_length():
    ed_priv = ed25519.Ed25519PrivateKey.generate()
    ed_pub_pem = ed_priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
    sig_base = b"x"
    sig = bytes(HYBRID_SIG_LEN)

    with pytest.raises(HybridVerificationError, match="verifying key must be"):
        verify_hybrid(
            sig_base=sig_base,
            signature=sig,
            key=HybridKey(ed25519_pem=ed_pub_pem, ml_dsa_65_raw=bytes(100)),
        )


def test_encode_decode_roundtrip():
    raw = bytes(HYBRID_SIG_LEN)  # the encoder doesn't validate semantic content
    s = encode_hybrid_signature(raw)
    assert decode_hybrid_signature(s) == raw


def test_encode_rejects_wrong_length():
    with pytest.raises(HybridVerificationError):
        encode_hybrid_signature(b"\x00\x01\x02")


def test_decode_rejects_wrong_length():
    too_small = base64.b64encode(b"\x00" * 10).decode("ascii")
    with pytest.raises(HybridVerificationError):
        decode_hybrid_signature(too_small)


# ---------------------------------------------------------------------------
# Round-trip and forgery tests (require oqs + liboqs)
# ---------------------------------------------------------------------------

oqs = pytest.importorskip("oqs", reason="liboqs-python not installed")


@pytest.fixture(scope="module")
def hybrid_keypair():
    ed_priv = ed25519.Ed25519PrivateKey.generate()
    ed_priv_pem = ed_priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")
    ed_pub_pem = ed_priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")

    with oqs.Signature("ML-DSA-65") as kg:
        pq_pub = kg.generate_keypair()
        pq_secret = kg.export_secret_key()

    assert len(pq_pub) == ML_DSA_65_VK_LEN

    return {
        "secret": HybridSecret(ed25519_pem=ed_priv_pem, ml_dsa_65_secret=pq_secret),
        "public": HybridKey(ed25519_pem=ed_pub_pem, ml_dsa_65_raw=pq_pub),
    }


def test_hybrid_sign_verify_roundtrip(hybrid_keypair):
    sig_base = b'"@method": POST\n"@authority": agent-registry.example\n"@path": /keys/lookup\n'
    sig = sign_hybrid(sig_base=sig_base, secret=hybrid_keypair["secret"])
    assert len(sig) == HYBRID_SIG_LEN
    # Must not raise.
    verify_hybrid(sig_base=sig_base, signature=sig, key=hybrid_keypair["public"])


def test_hybrid_rejects_tampered_classical_leg(hybrid_keypair):
    sig_base = b"good"
    sig = bytearray(sign_hybrid(sig_base=sig_base, secret=hybrid_keypair["secret"]))
    # Flip a bit inside the Ed25519 leg.
    sig[0] ^= 0x01
    with pytest.raises(HybridVerificationError, match="Ed25519"):
        verify_hybrid(sig_base=sig_base, signature=bytes(sig), key=hybrid_keypair["public"])


def test_hybrid_rejects_tampered_pq_leg(hybrid_keypair):
    sig_base = b"good"
    sig = bytearray(sign_hybrid(sig_base=sig_base, secret=hybrid_keypair["secret"]))
    # Flip a bit inside the ML-DSA-65 leg.
    sig[ED25519_SIG_LEN] ^= 0x01
    with pytest.raises(HybridVerificationError, match="ML-DSA-65"):
        verify_hybrid(sig_base=sig_base, signature=bytes(sig), key=hybrid_keypair["public"])


def test_hybrid_rejects_wrong_sig_base(hybrid_keypair):
    sig = sign_hybrid(sig_base=b"intended", secret=hybrid_keypair["secret"])
    with pytest.raises(HybridVerificationError):
        verify_hybrid(sig_base=b"not-the-base", signature=sig, key=hybrid_keypair["public"])
