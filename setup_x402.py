#!/usr/bin/env python3
"""
x402 Payment Setup — generates wallets, creates token accounts, and waits
for the user to fund them via testnet faucets.

Polls the blockchain every 15 seconds so the user can fund wallets in the
background while the script waits.

Usage:  python setup_x402.py
"""

import logging
import os
import subprocess
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# Suppress python-dotenv warnings about PEM keys it can't parse
logging.getLogger("dotenv.main").setLevel(logging.ERROR)

ROOT = Path(__file__).parent

# ---------------------------------------------------------------------------
# Network constants
# ---------------------------------------------------------------------------
SOLANA_RPC = "https://api.devnet.solana.com"
BASE_SEPOLIA_RPC = "https://sepolia.base.org"

USDC_MINT_DEVNET = "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU"
USDC_CONTRACT_BASE_SEPOLIA = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"

POLL_INTERVAL = 15  # seconds

# ANSI escape helpers
CLEAR_LINE = "\033[2K"
MOVE_UP = "\033[A"


# ---------------------------------------------------------------------------
# RPC helpers
# ---------------------------------------------------------------------------
def solana_sol_balance(address: str) -> float:
    """Return SOL balance for *address* (in SOL, not lamports)."""
    resp = requests.post(
        SOLANA_RPC,
        json={"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": [address]},
        timeout=10,
    )
    lamports = resp.json()["result"]["value"]
    return lamports / 1e9


def solana_usdc_balance(owner: str) -> float:
    """Return USDC (SPL) balance for *owner* on Solana devnet."""
    resp = requests.post(
        SOLANA_RPC,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenAccountsByOwner",
            "params": [
                owner,
                {"mint": USDC_MINT_DEVNET},
                {"encoding": "jsonParsed"},
            ],
        },
        timeout=10,
    )
    accounts = resp.json()["result"]["value"]
    if not accounts:
        return 0.0
    info = accounts[0]["account"]["data"]["parsed"]["info"]["tokenAmount"]
    return float(info["uiAmount"] or 0)


def evm_usdc_balance(address: str) -> float:
    """Return USDC balance for *address* on Base Sepolia (6 decimals)."""
    # balanceOf(address) selector = 0x70a08231
    addr_padded = address.lower().replace("0x", "").zfill(64)
    data = f"0x70a08231{addr_padded}"
    resp = requests.post(
        BASE_SEPOLIA_RPC,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_call",
            "params": [{"to": USDC_CONTRACT_BASE_SEPOLIA, "data": data}, "latest"],
        },
        timeout=10,
    )
    hex_val = resp.json().get("result", "0x0")
    return int(hex_val, 16) / 1e6


# ---------------------------------------------------------------------------
# Polling
# ---------------------------------------------------------------------------
def wait_for_balance(label: str, faucet_url: str, address: str, check_fn, threshold=0.0):
    """Poll *check_fn(address)* until the balance exceeds *threshold*.

    Uses a single line that rewrites itself for both countdown and status.
    """
    print(f"\n    Fund {label}:")
    print(f"      {faucet_url}")
    print(f"      Address: {address}")

    try:
        balance = check_fn(address)
    except Exception:
        balance = 0.0

    if balance > threshold:
        print(f"    Balance: {balance} — already funded!")
        return balance

    while True:
        for i in range(POLL_INTERVAL, 0, -1):
            sys.stdout.write(f"\r{CLEAR_LINE}    Waiting for deposit... (next check in {i}s)")
            sys.stdout.flush()
            time.sleep(1)
        sys.stdout.write(f"\r{CLEAR_LINE}    Checking...")
        sys.stdout.flush()
        try:
            balance = check_fn(address)
        except Exception:
            balance = 0.0
        if balance > threshold:
            sys.stdout.write(f"\r{CLEAR_LINE}    Balance: {balance} — funded!\n")
            sys.stdout.flush()
            return balance


def wait_for_all_usdc(wallets: list[tuple[str, str, callable]]):
    """Poll multiple wallets until all have USDC, rewriting status in place."""
    print("\n    Fund all wallets with testnet USDC:")
    print(f"      https://faucet.circle.com")

    n = len(wallets)
    balances = {}
    funded = {}

    # Print address list
    for label, address, _ in wallets:
        print(f"      {label}: {address}")
    print()

    def check_all():
        for label, address, check_fn in wallets:
            if funded.get(address):
                continue
            try:
                bal = check_fn(address)
            except Exception:
                bal = 0.0
            balances[address] = bal
            funded[address] = bal > 0

    def print_status():
        for label, address, _ in wallets:
            marker = "x" if funded.get(address) else " "
            bal = balances.get(address, 0.0)
            status = f"{bal} USDC" if funded.get(address) else "waiting..."
            print(f"    [{marker}] {label}: {status}")

    # Initial check
    check_all()
    print_status()

    while not all(funded.values()):
        # Countdown on the line below the status block
        for i in range(POLL_INTERVAL, 0, -1):
            sys.stdout.write(f"\r{CLEAR_LINE}    Next check in {i}s...")
            sys.stdout.flush()
            time.sleep(1)

        check_all()

        # Clear countdown line, move up over status lines, clear and reprint
        sys.stdout.write(f"\r{CLEAR_LINE}")
        for _ in range(n):
            sys.stdout.write(f"{MOVE_UP}{CLEAR_LINE}")
        sys.stdout.flush()
        print_status()

    print("\n    All wallets funded!")


# ---------------------------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------------------------
def run_script(description: str, script: str, cwd: Path, interactive: bool = False) -> str:
    """Run a Python script and return stdout.

    If *interactive* is True, stdin/stdout/stderr are inherited so the
    subprocess can prompt the user directly (output is not captured).
    """
    print(f"\n==> {description}")
    if interactive:
        result = subprocess.run(
            [sys.executable, script],
            cwd=cwd,
        )
        if result.returncode != 0:
            print(f"    (script exited with code {result.returncode})")
        return ""

    result = subprocess.run(
        [sys.executable, script],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    output = result.stdout.strip()
    if output:
        for line in output.splitlines():
            print(f"    {line}")
    if result.returncode != 0:
        stderr = result.stderr.strip()
        if stderr:
            for line in stderr.splitlines():
                print(f"    {line}")
        print(f"    (script exited with code {result.returncode})")
    return output


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 50)
    print("  x402 Payment Setup (Testnet)")
    print("=" * 50)

    # ---- 1. Generate merchant wallets --------------------------------------
    run_script(
        "Generating merchant wallets...",
        "setup_x402_wallet.py",
        ROOT / "merchant-backend",
        interactive=True,
    )

    # Read addresses from .env (most reliable source)
    load_dotenv(ROOT / "merchant-backend" / ".env", override=True)
    merchant_svm = os.getenv("X402_SVM_ADDRESS")
    merchant_evm = os.getenv("X402_EVM_ADDRESS")

    # ---- 2. Wait for SOL funding (needed for ATA creation) -----------------
    if merchant_svm:
        wait_for_balance(
            label="merchant Solana wallet with devnet SOL",
            faucet_url="https://faucet.solana.com/",
            address=merchant_svm,
            check_fn=solana_sol_balance,
        )

    # ---- 3. Create merchant USDC token account (ATA) ----------------------
    run_script(
        "Creating merchant USDC token account (ATA)...",
        "create_solana_ata.py",
        ROOT / "merchant-backend",
    )

    # ---- 4. Generate agent wallets -----------------------------------------
    run_script(
        "Generating agent wallets...",
        "setup_x402_wallet.py",
        ROOT / "tap-agent",
        interactive=True,
    )

    # Derive agent addresses from private keys in .env
    agent_svm = None
    agent_evm = None
    load_dotenv(ROOT / "tap-agent" / ".env", override=True)
    try:
        from solders.keypair import Keypair
        svm_key = os.getenv("SVM_PRIVATE_KEY", "")
        if svm_key:
            agent_svm = str(Keypair.from_base58_string(svm_key).pubkey())
    except (ImportError, Exception):
        pass
    try:
        from eth_account import Account
        evm_key = os.getenv("EVM_PRIVATE_KEY", "")
        if evm_key:
            agent_evm = Account.from_key(evm_key).address
    except (ImportError, Exception):
        pass

    # ---- 5. Wait for USDC funding on agent wallets -------------------------
    usdc_wallets = []
    if agent_svm:
        usdc_wallets.append(("Agent Solana", agent_svm, solana_usdc_balance))
    if agent_evm:
        usdc_wallets.append(("Agent EVM", agent_evm, evm_usdc_balance))

    if usdc_wallets:
        wait_for_all_usdc(usdc_wallets)

    # ---- Done --------------------------------------------------------------
    print()
    print("=" * 50)
    print("  x402 setup complete!")
    print()
    print("  Restart these services to pick up the new config:")
    print("    - Merchant Backend  (cd merchant-backend && python -m uvicorn app.main:app --reload)")
    print("    - TAP Agent         (cd tap-agent && streamlit run agent_app.py)")
    print("=" * 50)


if __name__ == "__main__":
    main()
