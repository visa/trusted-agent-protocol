#!/usr/bin/env python3
"""
Generate RSA and Ed25519 signing keys for the TAP Agent and write them to .env.

Creates:
  - An RSA-2048 key pair (for RSA-PSS-SHA256 signatures)
  - An Ed25519 key pair (for Ed25519 signatures)
  - Copies .env.example → .env if .env doesn't exist, then upserts key values

Run once:  python setup_keys.py
"""

import base64
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ed25519

ENV_PATH = Path(__file__).parent / ".env"
ENV_EXAMPLE_PATH = Path(__file__).parent / ".env.example"


def _pem_oneline(pem_bytes: bytes) -> str:
    """Convert a multi-line PEM to a single-line string with literal \\n."""
    return pem_bytes.decode().replace("\n", "\\n").strip()


def generate_rsa_keypair() -> tuple[str, str]:
    """Return (private_pem_oneline, public_pem_oneline)."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return _pem_oneline(private_pem), _pem_oneline(public_pem)


def generate_ed25519_keypair() -> tuple[str, str]:
    """Return (private_b64, public_b64) as base64-encoded raw bytes."""
    private_key = ed25519.Ed25519PrivateKey.generate()

    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(private_bytes).decode(), base64.b64encode(public_bytes).decode()


def upsert_env(key: str, value: str):
    """Insert or update a key=value in .env, preserving other content."""
    lines = []
    found = False

    if ENV_PATH.exists():
        lines = ENV_PATH.read_text().splitlines(keepends=True)
        new_lines = []
        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith(f"{key}=") or stripped.startswith(f"{key} ="):
                new_lines.append(f'{key}="{value}"\n')
                found = True
            else:
                new_lines.append(line)
        lines = new_lines

    if not found:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines.append(f'{key}="{value}"\n')

    ENV_PATH.write_text("".join(lines))


def main():
    print("=== TAP Agent Key Setup ===\n")

    # Bootstrap .env from .env.example if it doesn't exist yet
    if not ENV_PATH.exists() and ENV_EXAMPLE_PATH.exists():
        ENV_PATH.write_text(ENV_EXAMPLE_PATH.read_text())
        print(f"Created {ENV_PATH} from .env.example\n")

    # --- RSA ---
    rsa_priv, rsa_pub = generate_rsa_keypair()
    upsert_env("RSA_PRIVATE_KEY", rsa_priv)
    upsert_env("RSA_PUBLIC_KEY", rsa_pub)
    print("RSA-2048 key pair generated")

    # --- Ed25519 ---
    ed_priv, ed_pub = generate_ed25519_keypair()
    upsert_env("ED25519_PRIVATE_KEY", ed_priv)
    upsert_env("ED25519_PUBLIC_KEY", ed_pub)
    print("Ed25519 key pair generated")

    print(f"\nKeys written to {ENV_PATH}")


if __name__ == "__main__":
    main()
