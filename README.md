# Trusted Agent Protocol

*Establishing a universal standard of trust between AI agents and merchants for the next phase of agentic commerce.*

This repository demonstrates local agent request recognition. The proxy checks
HTTP message signatures against keys in the sample registry. Consumer recognition,
payment-container validation, consumer consent and settlement are separate parts
of the broader protocol, with separate implementation and verification requirements.

Use the [TAP merchant specification](https://developer.visa.com/docs/trusted-agent-protocol/trusted-agent-protocol-specifications)
and [RFC 9421](https://www.rfc-editor.org/rfc/rfc9421.html) for the protocol contract.
The local sample registry is separate from Visa's hosted registration services.

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

Visa's **Trusted Agent Protocol** defines cryptographic mechanisms for agent
recognition, consumer recognition and payment containers. A verified request
signature establishes possession of a trusted agent key and integrity of its
covered request components. Consumer permission and payment authorization require
their own checks.

For merchants, the Trusted Agent Protocol describes a standardized set of mechanisms enabling merchants to:

- **Cryptographically Verify Agent Intent:** Instantly distinguish a legitimate, credentialed agent from an anonymous bot. The agent presents a secure signature that includes timestamps, a unique session identifier, key identifier, and algorithm identifier, allowing you to verify that the signature is current and prevent relays or replays. 

- **Check Request Binding:** Verify the components declared in the signature.
  TAP's minimum covers authority and path. Binding a method, query or request
  body requires additional covered components and, for content digests, validation
  against the actual body.

- **Receive Consumer and Payment Data:** The broader TAP specification describes
  separately signed body objects for consumer recognition and payment data. Those
  objects require verification in addition to the request signature.

- **Reduce Fraud:** By trusting the agent's identity and intentions, merchants can create a more seamless path to purchase for customers using agents. This cryptographic proof of identity and intent provides a powerful new tool to reduce fraud and minimize chargebacks from unauthorized transactions.

## Key Benefits

- **Differentiate from Malicious Actors:** The Trusted Agent Protocol provides a definitive way for you to distinguish legitimate, authorized AI agents from other automated traffic. This allows you to confidently welcome agent-driven commerce while protecting your site from harmful bots.

- **Context-Bound Recognition:** The request signature binds the agent to the
  covered components. The minimum host and path binding is an input to merchant
  access policy, not proof of consumer authorization or payment completion.

- **Protection Against Replay Attacks:** The protocol is designed to prevent bad actors from capturing and reusing old requests. Each signature includes unique, time-sensitive elements that ensure every request is fresh and valid only for a single use.

- **Securely Receive Customer & Payment Identifiers:** The protocol defines a standardized way for a verified agent to pass essential customer information directly to merchants. This allows merchants to streamline the checkout process by receiving trusted data to pre-fill forms or identify the customer.

## Example Agent Verification for Payments
![](./assets/trusted-agent-protocol-flow.png)

## Quick Start

This repository contains a local request-recognition demo across several services:

### 🚀 **Running the Sample**

1. **Install Dependencies** (from root directory):
   ```bash
   pip install -r requirements.txt
   ```

2. **Start All Services**:
   ```bash
   # Terminal 1: Agent Registry (port 9002)
   cd agent-registry && python main.py
   
   # Terminal 2: Merchant Backend (port 8000)
   cd merchant-backend && python -m uvicorn app.main:app --reload
   
   # Terminal 3: CDN Proxy (port 3001)
   cd cdn-proxy && npm install && npm start
   
   # Terminal 4: Merchant Frontend (port 3000)
   cd merchant-frontend && npm install && npm run dev
   
   # Terminal 5: TAP Agent (port 8501)
   cd tap-agent && streamlit run agent_app.py
   ```

3. **Try the Demo**:
   - Open the TAP Agent at http://localhost:8501
   - Configure merchant URL: http://localhost:3001
   - Generate signatures and interact with the sample merchant

### 📚 **Component Documentation**

Each component has detailed setup instructions:

- **[TAP Agent](./tap-agent/README.md)** - Streamlit app demonstrating agent signature generation
- **[Merchant Frontend](./merchant-frontend/README.md)** - React e-commerce sample with TAP integration  
- **[Merchant Backend](./merchant-backend/README.md)** - FastAPI storefront and checkout demo
- **[CDN Proxy](./cdn-proxy/README.md)** - Node.js proxy implementing RFC 9421 signature verification
- **[Agent Registry](./agent-registry/README.md)** - Public key registry service for agent verification

### 🏗️ **Architecture Overview**

The sample request-recognition flow uses these services:
1. **TAP Agent** generates HTTP message signatures
2. **Merchant Frontend** provides the e-commerce interface
3. **CDN Proxy** intercepts and verifies agent signatures  
4. **Merchant Backend** serves the storefront API; signature verification belongs to the proxy's configured agent routes
5. **Agent Registry** manages agent public keys and metadata
