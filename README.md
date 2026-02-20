# Trusted Agent Protocol

*Establishing a universal standard of trust between AI agents and merchants for the next phase of agentic commerce.*


## The Challenge

AI agents are becoming part of everyday commerce, capable of executing complex tasks like booking travel or managing subscriptions. As agent capabilities evolve, merchants need visibility into their identities and actions more than ever.

**For an agent to make a purchase, merchants must answer:**

-  Is this a legitimate, trusted, and recognized AI agent?
-  Is it acting on behalf of a specific, authenticated user?
-  Does the agent carry valid instructions from the user to make this purchase?

**Without a standard, merchants face an impossible choice:**
-  Block potentially valuable agent-driven commerce
-  Accept significant operational and security risks from unverified agents

## The Solution

Visa's **Trusted Agent Protocol** provides a standardized, cryptographic method for an AI agent to prove its identity and associated authorization directly to merchants. By presenting a secure digital signature with every interaction, a merchant can verify that an agent is legitimate and has the user's permission to act.

For merchants, the Trusted Agent Protocol describes a standardized set of mechanisms enabling merchants to:

- **Cryptographically Verify Agent Intent:** Instantly distinguish a legitimate, credentialed agent from an anonymous bot. The agent presents a secure signature that includes timestamps, a unique session identifier, key identifier, and algorithm identifier, allowing you to verify that the signature is current and prevent relays or replays. 

- **Confirm Transaction-Specific Authorization:** Ensure the agent is authorized for the specific action it is taking  (browsing or payment) as the signature is bound to your domain and the specific operation being performed.

- **Receive Trusted User & Payment Identifiers:** Securely receive key information needed for checkout via query parameters. This can include, as consented by the consumer, verifiable consumer identifiers, Payment Account References (PARs) for cards on file, or other identifiers like loyalty numbers, emails and phone numbers, allowing you to streamline or pre-fill the customer experience.

- **Reduce Fraud:** By trusting the agent's identity and intentions, merchants can create a more seamless path to purchase for customers using agents. This cryptographic proof of identity and intent provides a powerful new tool to reduce fraud and minimize chargebacks from unauthorized transactions.

## Key Benefits

- **Differentiate from Malicious Actors:** The Trusted Agent Protocol provides a definitive way for you to distinguish legitimate, authorized AI agents from other automated traffic. This allows you to confidently welcome agent-driven commerce while protecting your site from harmful bots.

- **Context-Bound Security:** Every request from a trusted agent is cryptographically locked to a merchant's specific website and the exact page with which the agent is interacting . This ensures that an agent's authorization cannot be misused elsewhere.

- **Protection Against Replay Attacks:** The protocol is designed to prevent bad actors from capturing and reusing old requests. Each signature includes unique, time-sensitive elements that ensure every request is fresh and valid only for a single use.

- **Securely Receive Customer & Payment Identifiers:** The protocol defines a standardized way for a verified agent to pass essential customer information directly to merchants. This allows merchants to streamline the checkout process by receiving trusted data to pre-fill forms or identify the customer.

## Example Agent Verification for Payments
![](./assets/trusted-agent-protocol-flow.png)

## Quick Start

This repository contains a complete sample implementation demonstrating the Trusted Agent Protocol across multiple components:

### 🚀 **Running the Sample**

1. **Install Dependencies** (from root directory):
   ```bash
   pip install -r requirements.txt
   ```

2. **Generate Agent Keys** (one-time setup):
   ```bash
   cd tap-agent && python setup_keys.py
   ```
   This creates RSA and Ed25519 signing keys in `tap-agent/.env`.

3. **Start All Services**:
   ```bash
   # Terminal 1: Agent Registry (port 8001)
   cd agent-registry && python main.py

   # Terminal 2: Merchant Backend (port 8000)
   cd merchant-backend && python -m uvicorn app.main:app --reload

   # Terminal 3: CDN Proxy (port 3002)
   cd cdn-proxy && npm install && npm start

   # Terminal 4: Merchant Frontend (port 3001)
   cd merchant-frontend && npm install && npm run dev

   # Terminal 5: TAP Agent (port 8501)
   cd tap-agent && streamlit run agent_app.py
   ```

4. **Try the Demo**:
   - Open the TAP Agent at http://localhost:8501
   - Configure merchant URL: http://localhost:3001
   - Generate signatures and interact with the sample merchant

### 📚 **Component Documentation**

Each component has detailed setup instructions:

- **[TAP Agent](./tap-agent/README.md)** - Streamlit app demonstrating agent signature generation
- **[Merchant Frontend](./merchant-frontend/README.md)** - React e-commerce sample with TAP integration  
- **[Merchant Backend](./merchant-backend/README.md)** - FastAPI backend with signature verification
- **[CDN Proxy](./cdn-proxy/README.md)** - Node.js proxy implementing RFC 9421 signature verification
- **[Agent Registry](./agent-registry/README.md)** - Public key registry service for agent verification

### 💰 **x402 Payment Setup (Optional)**

The sample includes an x402 payment flow as an alternative to the browser-based credit card checkout. This uses USDC on Solana and Base.

#### Quick Setup (Testnet)

```bash
python setup_x402.py
```

This interactive script generates merchant and agent wallets (Solana + EVM), then walks you through funding each wallet. It polls the blockchain every 15 seconds so you can open the faucets in your browser while the script waits:

1. Generates merchant wallets and waits for devnet SOL funding (https://faucet.solana.com/)
2. Creates the merchant's USDC token account (ATA) on Solana
3. Generates agent wallets
4. Waits for testnet USDC funding on agent wallets (https://faucet.circle.com)

Each setup script creates Solana + EVM keypairs and writes them to the local `.env`. The `create_solana_ata.py` script creates the USDC Associated Token Account that the merchant needs to receive Solana payments.

#### Manual Configuration

If you prefer to use existing wallets, set these in `merchant-backend/.env`:
```bash
X402_FACILITATOR_URL=https://x402.org/facilitator
X402_SVM_ADDRESS=<your-solana-wallet-address>
X402_EVM_ADDRESS=<your-evm-wallet-address>
X402_SVM_NETWORK=solana:EtWTRABZaYq6iMfeYKouRu166VU2xqa1
X402_EVM_NETWORK=eip155:84532
X402_ENABLED=true
```

And in `tap-agent/.env`:
```bash
EVM_PRIVATE_KEY=<your-evm-private-key>
SVM_PRIVATE_KEY=<your-solana-private-key-base58>
```

The agent reuses the existing `MERCHANT_API_URL` env var (default `http://localhost:8000`).

#### Facilitators

A facilitator verifies and settles x402 payments on behalf of the merchant. Both production facilitators offer a free tier of 1,000 settlements per month.

| Facilitator | URL | Docs |
|---|---|---|
| **x402.org** (default) | `https://x402.org/facilitator` | Testnet only |
| **PayAI** | `https://facilitator.payai.network` | [docs.payai.network](https://docs.payai.network/x402/quickstart#facilitator) |
| **Coinbase CDP** | `https://api.cdp.coinbase.com/platform/v2/x402` | [docs.cdp.coinbase.com](https://docs.cdp.coinbase.com/x402/quickstart-for-sellers#running-on-mainnet) |

The default `https://x402.org/facilitator` is a public good suitable for testnet development. For production, switch to PayAI or Coinbase CDP.

#### Moving to Production

To accept real payments, update your `merchant-backend/.env` with mainnet values:

| Setting | Testnet | Mainnet |
|---|---|---|
| `X402_SVM_NETWORK` | `solana:EtWTRABZaYq6iMfeYKouRu166VU2xqa1` | `solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp` |
| `X402_EVM_NETWORK` | `eip155:84532` (Base Sepolia) | `eip155:8453` (Base) |
| USDC mint (Solana) | `4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU` | `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v` |
| USDC contract (Base) | `0x036CbD53842c5426634e7929541eC2318f3dCF7e` | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |

Switch `X402_FACILITATOR_URL` to either PayAI or Coinbase CDP and refer to their docs for credential setup.

#### Testing x402 Payments

1. Make sure all services are running (see [Quick Start](#-running-the-sample))
2. Open the TAP Agent at http://localhost:8501
3. Under **Action Selection**, choose **x402 Checkout**
4. Enter a **Product ID** (e.g. `21` for a digital product) and **Quantity**
5. Click **Pay with USDC (x402)**

The agent will create a cart, send a checkout request (receives HTTP 402 with payment requirements), sign the USDC payment, and settle on-chain via the facilitator.

### 🏗️ **Architecture Overview**

The sample demonstrates a complete TAP ecosystem:
1. **TAP Agent** generates RFC 9421 compliant signatures
2. **Merchant Frontend** provides the e-commerce interface
3. **CDN Proxy** intercepts and verifies agent signatures  
4. **Merchant Backend** processes verified requests
5. **Agent Registry** manages agent public keys and metadata
