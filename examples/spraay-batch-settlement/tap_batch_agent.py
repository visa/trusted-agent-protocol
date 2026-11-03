#!/usr/bin/env python3
"""
TAP-verified agent settling a multi-recipient batch payment via Spraay on Base.

Flow
----
1. The agent holds a TAP identity key (Ed25519) registered in the TAP agent-registry.
2. Every request to the Spraay gateway carries RFC 9421 `Signature-Input` /
   `Signature` headers built exactly like the repo's `tap-agent` does
   (components `@authority` + `@path`, `created`, `expires`, `keyId`, `alg`,
   `nonce`, `tag`). A TAP-aware CDN proxy in front of the gateway can verify
   the agent before the batch is processed.
3. Free endpoints (`/free/prices`, `/free/estimate-batch`) give a rough quote.
4. Paid endpoints (`/api/v1/batch/estimate` $0.001, `/api/v1/batch/execute`
   $0.02) are gated by x402 v2: the gateway answers HTTP 402 with a
   base64-encoded `payment-required` header; the agent signs an EIP-3009
   USDC authorization on Base and retries with a `PAYMENT-SIGNATURE` header.
5. `batch/execute` returns an unsigned transaction targeting the Spraay batch
   contract. The agent approves USDC (if needed), signs, broadcasts, and prints
   the Base transaction hash as the settlement receipt.

Modes
-----
    python tap_batch_agent.py --generate-keys          # new Ed25519 TAP identity
    python tap_batch_agent.py --register               # register key in local agent-registry
    python tap_batch_agent.py                          # dry run: TAP signing + free endpoints + show 402 terms
    python tap_batch_agent.py --pay                    # also pay x402 for live estimate + unsigned execute tx
    python tap_batch_agent.py --pay --broadcast        # also approve + broadcast the batch on Base

Nothing is paid or broadcast unless `--pay` / `--broadcast` are given.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import secrets
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from dotenv import load_dotenv

# --------------------------------------------------------------------------
# Constants (verified against the live gateway)
# --------------------------------------------------------------------------
GATEWAY_URL = "https://gateway.spraay.app"
X402_MANIFEST_URL = f"{GATEWAY_URL}/.well-known/x402.json"
SPRAAY_BATCH_CONTRACT_BASE = "0x1646452F98E36A3c9Cfc3eDD8868221E207B5eEC"
USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
X402_PAY_TO = "0xAd62f03C7514bb8c51f1eA70C2b75C37404695c8"
BASE_CHAIN_ID = 8453
BASE_CAIP2 = f"eip155:{BASE_CHAIN_ID}"
SUPPORTED_CHAINS = ("base", "peaq")
MAX_RECIPIENTS = 200
DEFAULT_BASE_RPC = "https://mainnet.base.org"
DEFAULT_REGISTRY_URL = "http://localhost:9002"
DEFAULT_KEY_ID = "spraay-batch-agent-ed25519"
# The repo's tap-agent uses "agent-payer-auth" for payment/checkout actions.
TAP_TAG = "agent-payer-auth"

HERE = Path(__file__).resolve().parent


# --------------------------------------------------------------------------
# TAP identity: RFC 9421 HTTP Message Signatures
# (mirrors create_ed25519_signature / parse_url_components in tap-agent/agent_app.py,
#  without the Streamlit dependency)
# --------------------------------------------------------------------------
def parse_url_components(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    path = parsed.path
    if parsed.query:
        path += f"?{parsed.query}"
    return parsed.netloc, path


def _signature_params(created: int, expires: int, keyid: str, nonce: str, tag: str) -> str:
    return (
        f'("@authority" "@path"); created={created}; expires={expires}; '
        f'keyId="{keyid}"; alg="ed25519"; nonce="{nonce}"; tag="{tag}"'
    )


def _signature_base(authority: str, path: str, params: str) -> str:
    return "\n".join(
        [
            f'"@authority": {authority}',
            f'"@path": {path}',
            f'"@signature-params": {params}',
        ]
    )


def create_tap_signature_headers(
    private_key_b64: str, url: str, keyid: str, tag: str = TAP_TAG, ttl_seconds: int = 8 * 60
) -> dict[str, str]:
    """Return {Signature-Input, Signature} headers for one request (fresh nonce each call)."""
    authority, path = parse_url_components(url)
    created = int(time.time())
    expires = created + ttl_seconds
    nonce = str(uuid.uuid4())
    params = _signature_params(created, expires, keyid, nonce, tag)
    base = _signature_base(authority, path, params)

    key = ed25519.Ed25519PrivateKey.from_private_bytes(base64.b64decode(private_key_b64))
    sig_b64 = base64.b64encode(key.sign(base.encode("utf-8"))).decode()
    return {"Signature-Input": f"sig2={params}", "Signature": f"sig2=:{sig_b64}:"}


def verify_tap_signature(public_key_b64: str, url: str, headers: dict[str, str]) -> bool:
    """What a TAP-aware CDN proxy does: rebuild the signature base and verify it."""
    authority, path = parse_url_components(url)
    params = headers["Signature-Input"].split("=", 1)[1]
    sig_b64 = headers["Signature"].split("=", 1)[1].strip(":")
    expires = int(params.split("expires=")[1].split(";")[0])
    if expires < time.time():
        return False
    pub = ed25519.Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64))
    try:
        pub.verify(base64.b64decode(sig_b64), _signature_base(authority, path, params).encode())
        return True
    except Exception:
        return False


def generate_ed25519_keypair() -> tuple[str, str]:
    key = ed25519.Ed25519PrivateKey.generate()
    priv = key.private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()
    )
    pub = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return base64.b64encode(priv).decode(), base64.b64encode(pub).decode()


def register_agent(registry_url: str, public_key_b64: str, keyid: str) -> dict:
    """Register this agent's TAP key with the repo's agent-registry (POST /agents/register)."""
    body = {
        "name": "Spraay Batch Settlement Agent",
        "domain": os.getenv("AGENT_DOMAIN", "https://spraay.app"),
        "description": "TAP-authenticated agent that settles multi-recipient USDC batches on Base via Spraay",
        "keys": [
            {
                "key_id": keyid,
                "public_key": public_key_b64,
                "algorithm": "ed25519",
                "description": "TAP identity key for Spraay batch settlement",
            }
        ],
    }
    r = requests.post(f"{registry_url}/agents/register", json=body, timeout=15)
    r.raise_for_status()
    return r.json()


# --------------------------------------------------------------------------
# TAP-signed HTTP client for the Spraay gateway, with x402 v2 support
# --------------------------------------------------------------------------
class TapSpraayClient:
    def __init__(self, tap_private_key_b64: str, keyid: str, payer=None, verbose: bool = True):
        self.tap_key = tap_private_key_b64
        self.keyid = keyid
        self.payer = payer  # eth_account LocalAccount, only needed for paid calls
        self.verbose = verbose
        self.session = requests.Session()

    def _headers(self, url: str, extra: dict | None = None) -> dict:
        h = {"Accept": "application/json", **create_tap_signature_headers(self.tap_key, url, self.keyid)}
        if extra:
            h.update(extra)
        if self.verbose:
            print(f"  TAP Signature-Input: {h['Signature-Input']}")
        return h

    def get(self, path: str) -> requests.Response:
        url = f"{GATEWAY_URL}{path}"
        return self.session.get(url, headers=self._headers(url), timeout=30)

    def post(self, path: str, body: dict, pay: bool) -> requests.Response:
        """POST with TAP headers. On HTTP 402, pay via x402 (if allowed) and retry once."""
        url = f"{GATEWAY_URL}{path}"
        r = self.session.post(url, json=body, headers=self._headers(url), timeout=60)
        if r.status_code != 402 or not pay:
            return r
        requirements = decode_payment_required(r)
        payment_header = build_x402_payment(self.payer, requirements)
        # Fresh TAP signature (new nonce) on the paid retry.
        r = self.session.post(
            url, json=body, headers=self._headers(url, {"PAYMENT-SIGNATURE": payment_header}), timeout=120
        )
        settle = r.headers.get("PAYMENT-RESPONSE") or r.headers.get("X-PAYMENT-RESPONSE")
        if settle and self.verbose:
            try:
                print(f"  x402 settlement: {json.loads(base64.b64decode(settle))}")
            except Exception:
                print(f"  x402 settlement header: {settle}")
        return r


def decode_payment_required(resp: requests.Response) -> dict:
    """x402 v2: requirements are base64 JSON in the `payment-required` header (body mirrors it)."""
    header = resp.headers.get("payment-required")
    if header:
        return json.loads(base64.b64decode(header))
    return resp.json()


def select_base_usdc_requirement(requirements: dict) -> dict:
    for acc in requirements.get("accepts", []):
        if (
            acc.get("scheme") == "exact"
            and acc.get("network") == BASE_CAIP2
            and acc.get("asset", "").lower() == USDC_BASE.lower()
        ):
            return acc
    raise RuntimeError("Gateway did not offer an 'exact' USDC-on-Base x402 option")


def build_x402_payment(payer, requirements: dict) -> str:
    """Sign an EIP-3009 transferWithAuthorization for USDC on Base (x402 v2 'exact' scheme)."""
    if payer is None:
        raise RuntimeError("PAYER_PRIVATE_KEY is required for paid endpoints")
    from eth_account.messages import encode_typed_data

    req = select_base_usdc_requirement(requirements)
    now = int(time.time())
    authorization = {
        "from": payer.address,
        "to": req["payTo"],
        "value": str(req["amount"]),
        "validAfter": str(now - 600),
        "validBefore": str(now + int(req.get("maxTimeoutSeconds", 300))),
        "nonce": "0x" + secrets.token_hex(32),
    }
    typed = {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "TransferWithAuthorization": [
                {"name": "from", "type": "address"},
                {"name": "to", "type": "address"},
                {"name": "value", "type": "uint256"},
                {"name": "validAfter", "type": "uint256"},
                {"name": "validBefore", "type": "uint256"},
                {"name": "nonce", "type": "bytes32"},
            ],
        },
        "primaryType": "TransferWithAuthorization",
        "domain": {
            "name": req["extra"]["name"],
            "version": req["extra"]["version"],
            "chainId": BASE_CHAIN_ID,
            "verifyingContract": req["asset"],
        },
        "message": {
            "from": authorization["from"],
            "to": authorization["to"],
            "value": int(authorization["value"]),
            "validAfter": int(authorization["validAfter"]),
            "validBefore": int(authorization["validBefore"]),
            "nonce": bytes.fromhex(authorization["nonce"][2:]),
        },
    }
    signed = payer.sign_message(encode_typed_data(full_message=typed))
    payload = {
        "x402Version": 2,
        "resource": requirements.get("resource"),
        "accepted": req,
        "payload": {"signature": _hex(signed.signature), "authorization": authorization},
    }
    return base64.b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()


def _hex(b) -> str:
    h = bytes(b).hex()
    return h if h.startswith("0x") else "0x" + h


# --------------------------------------------------------------------------
# On-chain settlement on Base (minimal JSON-RPC, no web3 dependency)
# --------------------------------------------------------------------------
class BaseRpc:
    def __init__(self, url: str):
        self.url = url

    def call(self, method: str, params: list):
        r = requests.post(self.url, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, timeout=30)
        r.raise_for_status()
        out = r.json()
        if "error" in out:
            raise RuntimeError(f"{method}: {out['error']}")
        return out["result"]

    def fees(self) -> tuple[int, int]:
        base_fee = int(self.call("eth_getBlockByNumber", ["latest", False])["baseFeePerGas"], 16)
        prio = int(self.call("eth_maxPriorityFeePerGas", []), 16)
        return base_fee * 2 + prio, prio

    def send(self, account, to: str, data: str, gas: int, value: int = 0) -> str:
        max_fee, prio = self.fees()
        tx = {
            "type": 2,
            "chainId": BASE_CHAIN_ID,
            "nonce": int(self.call("eth_getTransactionCount", [account.address, "pending"]), 16),
            "to": to,
            "value": value,
            "data": data,
            "gas": gas,
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": prio,
        }
        signed = account.sign_transaction(tx)
        raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
        return self.call("eth_sendRawTransaction", [_hex(raw)])

    def wait(self, tx_hash: str, timeout: int = 120) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            receipt = self.call("eth_getTransactionReceipt", [tx_hash])
            if receipt:
                return receipt
            time.sleep(2)
        raise TimeoutError(f"No receipt for {tx_hash} after {timeout}s")


def _addr_word(addr: str) -> str:
    return addr.lower().replace("0x", "").rjust(64, "0")


def ensure_allowance(rpc: BaseRpc, account, approval: dict) -> None:
    """approvalRequired.amount is RAW base units: pass verbatim as the ERC-20 allowance."""
    token, spender, amount = approval["token"], approval["spender"], int(approval["amount"])
    current = int(
        rpc.call(
            "eth_call",
            [{"to": token, "data": "0xdd62ed3e" + _addr_word(account.address) + _addr_word(spender)}, "latest"],
        ),
        16,
    )
    if current >= amount:
        print(f"  Allowance OK ({current} >= {amount})")
        return
    data = "0x095ea7b3" + _addr_word(spender) + hex(amount)[2:].rjust(64, "0")
    gas = int(rpc.call("eth_estimateGas", [{"from": account.address, "to": token, "data": data}]), 16)
    tx_hash = rpc.send(account, token, data, int(gas * 1.2))
    print(f"  approve() sent: {tx_hash} ({approval.get('amountFormatted')} USDC incl. fee)")
    receipt = rpc.wait(tx_hash)
    if receipt.get("status") != "0x1":
        raise RuntimeError(f"approve() reverted: {tx_hash}")


# --------------------------------------------------------------------------
# Batch helpers
# --------------------------------------------------------------------------
def load_batch(path: Path, sender: str | None) -> dict:
    raw = json.loads(path.read_text())
    batch = {k: v for k, v in raw.items() if not k.startswith("_")}
    if sender:
        batch["sender"] = sender
    for field in ("token", "recipients", "amounts", "sender"):
        if field not in batch:
            raise ValueError(f"batch file missing required field '{field}'")
    if len(batch["recipients"]) != len(batch["amounts"]):
        raise ValueError("recipients[] and amounts[] must be the same length")
    if not 0 < len(batch["recipients"]) <= MAX_RECIPIENTS:
        raise ValueError(f"batch must have 1..{MAX_RECIPIENTS} recipients")
    if not all(isinstance(a, str) and a.isdigit() for a in batch["amounts"]):
        raise ValueError("amounts[] must be RAW base-unit integer strings (e.g. \"1500000\" = 1.50 USDC)")
    if batch.get("chain", "base") not in SUPPORTED_CHAINS:
        raise ValueError(f"chain must be one of {SUPPORTED_CHAINS}")
    return batch


def fmt_usdc(raw: int) -> str:
    return f"{raw / 1_000_000:,.6f}".rstrip("0").rstrip(".")


def section(title: str) -> None:
    print(f"\n=== {title} ===")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main() -> int:
    load_dotenv()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--batch", default=str(HERE / "example_batch.json"), help="batch payload JSON")
    ap.add_argument("--generate-keys", action="store_true", help="print a new Ed25519 TAP keypair and exit")
    ap.add_argument("--register", action="store_true", help="register the TAP key with the agent-registry and exit")
    ap.add_argument("--pay", action="store_true", help="pay x402 for /api/v1/batch/estimate and /api/v1/batch/execute")
    ap.add_argument("--broadcast", action="store_true", help="approve USDC and broadcast the batch tx on Base")
    args = ap.parse_args()

    if args.generate_keys:
        priv, pub = generate_ed25519_keypair()
        print(f'ED25519_PRIVATE_KEY="{priv}"\nED25519_PUBLIC_KEY="{pub}"')
        return 0

    tap_priv = os.getenv("ED25519_PRIVATE_KEY")
    tap_pub = os.getenv("ED25519_PUBLIC_KEY")
    keyid = os.getenv("TAP_KEY_ID", DEFAULT_KEY_ID)
    if not tap_priv or not tap_pub:
        print("ED25519_PRIVATE_KEY / ED25519_PUBLIC_KEY not set. Run with --generate-keys and add them to .env.")
        return 1

    if args.register:
        registry = os.getenv("AGENT_REGISTRY_URL", DEFAULT_REGISTRY_URL)
        print(json.dumps(register_agent(registry, tap_pub, keyid), indent=2, default=str))
        return 0

    if args.broadcast and not args.pay:
        ap.error("--broadcast requires --pay (the unsigned tx comes from the paid execute endpoint)")

    payer = None
    if args.pay:
        from eth_account import Account

        pk = os.getenv("PAYER_PRIVATE_KEY")
        if not pk:
            print("PAYER_PRIVATE_KEY is required with --pay (Base wallet holding USDC + a little ETH for gas).")
            return 1
        payer = Account.from_key(pk)

    batch = load_batch(Path(args.batch), payer.address if payer else None)
    total_raw = sum(int(a) for a in batch["amounts"])
    client = TapSpraayClient(tap_priv, keyid, payer)

    section("1. TAP identity")
    probe_url = f"{GATEWAY_URL}/api/v1/batch/execute"
    probe = create_tap_signature_headers(tap_priv, probe_url, keyid)
    print(f"  keyId: {keyid}  tag: {TAP_TAG}")
    print(f"  Local verification (as a TAP CDN proxy would): {verify_tap_signature(tap_pub, probe_url, probe)}")

    section("2. Batch")
    print(f"  token={batch['token']} chain={batch.get('chain', 'base')} sender={batch['sender']}")
    for to, amt in zip(batch["recipients"], batch["amounts"]):
        print(f"    {to}  {amt:>12} raw  ({fmt_usdc(int(amt))} USDC)")
    fee_raw = total_raw * 30 // 10_000
    print(f"  total {fmt_usdc(total_raw)} USDC + 0.3% protocol fee ~{fmt_usdc(fee_raw)} USDC")

    section("3. Free tier: /free/prices + /free/estimate-batch")
    prices = client.get("/free/prices").json()
    print(f"  USDC=${prices['prices']['USDC']['usd']}  ETH=${prices['prices']['ETH']['usd']}  (cached={prices.get('cached')})")
    n = len(batch["recipients"])
    est = client.get(f"/free/estimate-batch?recipients={n}&token={batch['token']}").json()["estimate"]
    print(
        f"  chain={est['chain']} recipients={est['recipients']} feeBps={est['protocolFeeBps']} "
        f"estimatedGasUSD={est['estimatedGasUSD']} supported={est['supported']} chains={est['supportedChains']}"
    )

    section("4. Paid: POST /api/v1/batch/estimate ($0.001 via x402)")
    r = client.post("/api/v1/batch/estimate", batch, pay=args.pay)
    if r.status_code == 402:
        req = select_base_usdc_requirement(decode_payment_required(r))
        print(f"  HTTP 402 Payment Required -> {req['amount']} raw USDC to {req['payTo']} on {req['network']}")
        print(f"  Manifest: {X402_MANIFEST_URL}")
        print("\nDry run complete. Re-run with --pay to get a live quote and the unsigned batch transaction.")
        return 0
    r.raise_for_status()
    quote = r.json()
    print(
        f"  totalAmount={quote.get('totalAmount')} fee={quote.get('fee')} "
        f"totalWithFee={quote.get('totalWithFee')} suggestedGasLimit={quote.get('suggestedGasLimit')}"
    )

    section("5. Paid: POST /api/v1/batch/execute ($0.02 via x402)")
    r = client.post("/api/v1/batch/execute", batch, pay=True)
    r.raise_for_status()
    ex = r.json()
    tx = ex["transaction"]
    print(f"  contract={ex.get('contract')} to={tx['to']} chainId={tx['chainId']} gasLimit={tx['gasLimit']}")
    print(f"  batch: {json.dumps(ex.get('batch'))}")
    if ex.get("approvalRequired"):
        a = ex["approvalRequired"]
        print(f"  approvalRequired: {a['amount']} raw ({a['amountFormatted']} USDC) for spender {a['spender']}")
    if tx["to"].lower() != SPRAAY_BATCH_CONTRACT_BASE.lower():
        print(f"  WARNING: tx target {tx['to']} is not the known Spraay batch contract {SPRAAY_BATCH_CONTRACT_BASE}")
        return 1

    if not args.broadcast:
        print("\nUnsigned transaction ready. Re-run with --pay --broadcast to settle on Base.")
        return 0

    section("6. Settlement on Base")
    rpc = BaseRpc(os.getenv("BASE_RPC_URL", DEFAULT_BASE_RPC))
    if ex.get("approvalRequired"):
        ensure_allowance(rpc, payer, ex["approvalRequired"])
    tx_hash = rpc.send(payer, tx["to"], tx["data"], int(tx["gasLimit"], 16), int(tx.get("value", "0")))
    receipt = rpc.wait(tx_hash)
    ok = receipt.get("status") == "0x1"
    print(f"  Batch tx: {tx_hash}  status={'success' if ok else 'reverted'}  block={int(receipt['blockNumber'], 16)}")
    print(f"  Receipt: https://basescan.org/tx/{tx_hash}")
    print(f"  {n} recipients settled in one transaction, authorized by TAP key '{keyid}'.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
