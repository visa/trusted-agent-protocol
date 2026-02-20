#!/usr/bin/env python3
"""
Create a USDC Associated Token Account (ATA) for the merchant's Solana wallet.

Reads X402_SVM_PRIVATE_KEY and X402_SVM_NETWORK from .env.
The wallet must already be funded with SOL to pay for the account creation.

Usage:  python create_solana_ata.py
"""

import base64
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH)

# USDC mint addresses per network
USDC_MINTS = {
    "solana:EtWTRABZaYq6iMfeYKouRu166VU2xqa1": "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU",  # devnet
    "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # mainnet
}

RPC_URLS = {
    "solana:EtWTRABZaYq6iMfeYKouRu166VU2xqa1": "https://api.devnet.solana.com",
    "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp": "https://api.mainnet-beta.solana.com",
}

TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
ASSOCIATED_TOKEN_PROGRAM = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
SYSTEM_PROGRAM = "11111111111111111111111111111111"


def rpc(url: str, method: str, params=None):
    """Make a Solana JSON-RPC call."""
    import httpx

    resp = httpx.post(
        url,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []},
        timeout=30,
    )
    body = resp.json()
    if "error" in body:
        raise RuntimeError(f"RPC {method} failed: {body['error']}")
    return body["result"]


def main():
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey
    from solders.instruction import Instruction, AccountMeta
    from solders.hash import Hash
    from solders.message import Message
    from solders.transaction import Transaction

    # --- Read config ---
    private_key = os.getenv("X402_SVM_PRIVATE_KEY", "")
    network = os.getenv("X402_SVM_NETWORK", "solana:EtWTRABZaYq6iMfeYKouRu166VU2xqa1")

    if not private_key:
        print("Error: X402_SVM_PRIVATE_KEY not found in .env")
        print("Run  python setup_x402_wallet.py  first.")
        sys.exit(1)

    if network not in USDC_MINTS:
        print(f"Error: Unknown network '{network}'")
        print(f"Supported: {', '.join(USDC_MINTS.keys())}")
        sys.exit(1)

    rpc_url = RPC_URLS[network]
    usdc_mint = Pubkey.from_string(USDC_MINTS[network])
    token_program = Pubkey.from_string(TOKEN_PROGRAM)
    ata_program = Pubkey.from_string(ASSOCIATED_TOKEN_PROGRAM)
    sys_program = Pubkey.from_string(SYSTEM_PROGRAM)

    payer = Keypair.from_base58_string(private_key)
    wallet = payer.pubkey()

    print(f"Network:    {network}")
    print(f"RPC:        {rpc_url}")
    print(f"Wallet:     {wallet}")
    print(f"USDC mint:  {usdc_mint}")

    # --- Derive ATA address ---
    ata, _bump = Pubkey.find_program_address(
        [bytes(wallet), bytes(token_program), bytes(usdc_mint)],
        ata_program,
    )
    print(f"ATA:        {ata}")

    # --- Check if ATA already exists ---
    info = rpc(rpc_url, "getAccountInfo", [str(ata), {"encoding": "base64"}])
    if info["value"] is not None:
        print("\nATA already exists — nothing to do.")
        return

    # --- Check SOL balance ---
    balance = rpc(rpc_url, "getBalance", [str(wallet)])
    lamports = balance["value"]
    print(f"SOL balance: {lamports / 1e9:.4f} SOL")
    if lamports < 10_000_000:  # ~0.01 SOL minimum for ATA creation
        print("\nError: Insufficient SOL. Fund this wallet first:")
        print(f"  https://faucet.solana.com/  (address: {wallet})")
        sys.exit(1)

    # --- Build CreateAssociatedTokenAccount instruction ---
    ix = Instruction(
        program_id=ata_program,
        data=bytes(),  # no instruction data needed
        accounts=[
            AccountMeta(wallet, is_signer=True, is_writable=True),    # payer
            AccountMeta(ata, is_signer=False, is_writable=True),      # ATA
            AccountMeta(wallet, is_signer=False, is_writable=False),  # wallet owner
            AccountMeta(usdc_mint, is_signer=False, is_writable=False),
            AccountMeta(sys_program, is_signer=False, is_writable=False),
            AccountMeta(token_program, is_signer=False, is_writable=False),
        ],
    )

    # --- Get recent blockhash ---
    bh_result = rpc(rpc_url, "getLatestBlockhash")
    blockhash = Hash.from_string(bh_result["value"]["blockhash"])

    # --- Build, sign, send transaction ---
    msg = Message.new_with_blockhash([ix], wallet, blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.partial_sign([payer], blockhash)

    tx_bytes = bytes(tx)
    tx_b64 = base64.b64encode(tx_bytes).decode()

    print("\nSending transaction...")
    sig = rpc(rpc_url, "sendTransaction", [tx_b64, {"encoding": "base64"}])
    print(f"Transaction signature: {sig}")
    print(f"\nUSDC ATA created successfully: {ata}")


if __name__ == "__main__":
    main()
