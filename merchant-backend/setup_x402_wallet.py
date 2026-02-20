#!/usr/bin/env python3
"""
Generate merchant receiving wallets for x402 payments and write them to .env.

Creates:
  - A Solana keypair (prints the address for ATA creation)
  - An EVM account (prints the address for funding)
  - Appends/updates X402_* vars in .env

Run once:  python setup_x402_wallet.py
"""

import os
import sys
from pathlib import Path

ENV_PATH = Path(__file__).parent / ".env"


def generate_solana_keypair():
    """Return (base58_private_key, base58_public_address)."""
    from solders.keypair import Keypair  # installed via x402[svm]

    kp = Keypair()
    return str(kp), str(kp.pubkey())


def generate_evm_account():
    """Return (hex_private_key_with_0x, hex_address)."""
    from eth_account import Account  # installed via eth-account

    acct = Account.create()
    return acct.key.hex(), acct.address


def upsert_env(key: str, value: str):
    """Insert or update a key=value in .env, preserving other content."""
    lines = []
    found = False

    if ENV_PATH.exists():
        lines = ENV_PATH.read_text().splitlines(keepends=True)
        new_lines = []
        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith(f"{key}="):
                new_lines.append(f"{key}={value}\n")
                found = True
            else:
                new_lines.append(line)
        lines = new_lines

    if not found:
        # Ensure trailing newline before appending
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines.append(f"{key}={value}\n")

    ENV_PATH.write_text("".join(lines))


def read_env(key: str) -> str | None:
    """Return the value of *key* from .env, or None if not found."""
    if not ENV_PATH.exists():
        return None
    for line in ENV_PATH.read_text().splitlines():
        stripped = line.lstrip()
        if stripped.startswith(f"{key}="):
            return stripped.split("=", 1)[1].strip()
    return None


def confirm_overwrite(label: str, key: str) -> bool:
    """Prompt the user to confirm overwriting an existing private key."""
    existing = read_env(key)
    if not existing or existing in ("", "<your-evm-private-key>", "<your-solana-private-key-base58>"):
        return True
    answer = input(f"{label} private key already exists in .env. Overwrite? [y/N] ").strip().lower()
    return answer == "y"


def main():
    print("=== x402 Merchant Wallet Setup ===\n")

    # --- Solana ---
    try:
        if confirm_overwrite("Solana", "X402_SVM_PRIVATE_KEY"):
            svm_privkey, svm_address = generate_solana_keypair()
            print(f"Solana address:     {svm_address}")
            print(f"  (private key stored in .env as X402_SVM_PRIVATE_KEY)")
            upsert_env("X402_SVM_ADDRESS", svm_address)
            upsert_env("X402_SVM_PRIVATE_KEY", svm_privkey)
        else:
            svm_address = read_env("X402_SVM_ADDRESS")
            print(f"Solana address:     {svm_address} (existing)")
    except ImportError:
        print("Skipping Solana — 'solders' not installed (pip install x402[svm])")
        svm_address = None

    # --- EVM ---
    try:
        if confirm_overwrite("EVM", "X402_EVM_PRIVATE_KEY"):
            evm_privkey, evm_address = generate_evm_account()
            print(f"EVM address:        {evm_address}")
            print(f"  (private key stored in .env as X402_EVM_PRIVATE_KEY)")
            upsert_env("X402_EVM_ADDRESS", evm_address)
            upsert_env("X402_EVM_PRIVATE_KEY", evm_privkey)
        else:
            evm_address = read_env("X402_EVM_ADDRESS")
            print(f"EVM address:        {evm_address} (existing)")
    except ImportError:
        print("Skipping EVM — 'eth_account' not installed (pip install eth-account)")
        evm_address = None

    # --- Defaults ---
    upsert_env("X402_ENABLED", "true")
    upsert_env("X402_FACILITATOR_URL", "https://x402.org/facilitator")
    upsert_env("X402_SVM_NETWORK", "solana:EtWTRABZaYq6iMfeYKouRu166VU2xqa1")
    upsert_env("X402_EVM_NETWORK", "eip155:84532")

    print(f"\nWrote configuration to {ENV_PATH}")


if __name__ == "__main__":
    main()
