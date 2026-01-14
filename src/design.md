# System Architecture & Protocol Description

## System Overview
The Trusted Agent Protocol (TAP) system consists of five main components designed to facilitate secure, authenticated interactions between AI Agents and Merchant systems using RFC 9421 HTTP Message Signatures and mTLS/Certificate-based identity. The architecture enforces identity verification at the edge (CDN Proxy) before traffic reaches the Merchant application.

**Tech Stack:**
- **Runtime:** Bun
- **Language:** TypeScript
- **UI:** VanJS (No .html files)
- **Signatures:** Standard HTTP Signatures via `@interledger/http-signature-utils` with JWK.
- **PKI:** node-forge for Certificate Authority and CSR operations.

## Components

### 1. TAP Agent (Client)
- **Role**: The end-user acting as an autonomous agent.
- **Functionality**:
  - Generates cryptographic keys (Ed25519, RSA-PSS) stored as JWKs.
  - Registers identity with the **Agent registry**.
  - Requests a Client Certificate from the **Authority Service**.
  - Authenticates via **HTTP Signatures** (RFC 9421) AND **Client Certificates** (RFC 9440 header or mTLS).

### 2. CDN Proxy (Edge Security)
- **Role**: Gatekeeper / Reverse Proxy.
- **Logic**:
  - Intercepts **all** incoming traffic.
  - **Authentication**:
    - Checks `Client-Cert` header or mTLS peer certificate.
    - Validates certificate against **Authority CA**.
    - If valid cert: Extracts Public Key from cert (Optimization: skips Registry lookup).
    - If no cert: Queries **Agent Registry** for Public Key.
  - **Verification**:
    - Verifies RFC 9421 `Signature` using the resolved Public Key.
  - Forwards valid requests to **Merchant Service**.

### 3. Agent Registry (Identity Provider)
- **Role**: Storage for Agent Identities and Public Keys.
- **Logic**:
  - Exposes API for Agent and Key registration.
  - Supports multiple storage backends (Memory, Redis, SQLite).
  - Provides fallback public key lookup for the Proxy.

### 4. Authority Service (CA)
- **Role**: Certificate Authority.
- **Logic**:
  - Issues self-signed CA certificates.
  - Signs Certificate Signing Requests (CSRs) from Agents.
  - Provides CA certificate verification to Proxy.

### 5. Merchant Service (Application)
- **Role**: Unified Resource Server & UI Host.
- **Logic**:
  - Serves static frontend assets (VanJS).
  - Provides a read-only list of products via API.
  - Protected behind the Proxy.

---

## Protocol Flows

### 1. Registration & Provisioning
1.  **Agent** generates Key Pair (JWK).
2.  **Agent** registers with **Registry** (POST `/agents`).
3.  **Agent** generates CSR and requests certificate from **Authority** (POST `/authority/sign`).
4.  **Authority** signs CSR and returns Client Certificate.

### 2. Authenticated Request (Active Flow)
1.  **Agent** constructs request to **Proxy** (`GET /product/1`).
2.  **Agent** adds headers:
    -   `Signature-Input`, `Signature` (RFC 9421)
    -   `Client-Cert` (RFC 9440) containing the received certificate.
3.  **Proxy** receives request:
    -   Verifies `Client-Cert` against **Authority CA**.
    -   Extracts Public Key from `Client-Cert`.
    -   Verifies `Signature` using extracted key.
4.  **Proxy** forwards to **Merchant**.

## System Diagrams

### Architecture

```mermaid
graph TD
    subgraph "Client"
        Agent["TAP Agent"]
    end

    subgraph "Infrastructure"
        Authority["Authority Service (CA)"]
        Registry["Agent Registry"]
        Proxy["CDN Proxy"]
    end

    subgraph MerchantSystem ["Merchant System"]
        Merchant["Merchant Service"]
    end

    Agent -->|1. Register| Registry
    Agent -->|2. Get Cert| Authority
    Agent -->|3. Signed Req + Cert| Proxy
    
    Proxy -.->|Fetch CA Cert| Authority
    Proxy -.->|Fallback Key Lookup| Registry
    
    Proxy -->|4. Validated Req| Merchant
```

## Test Scenarios

### 1. Pure mTLS (No Signature)
*Based on `src/proxy/test/mtls.test.ts`*
This flow demonstrates the efficiency optimization where a valid, trusted mTLS certificate allows the Agent to bypass the application-layer signature check.

```mermaid
sequenceDiagram
    participant A as Agent
    participant P as CDN Proxy
    participant M as Merchant

    Note over A, P: TLS Handshake (Client Cert Sent)
    A->>P: GET /product/1
    P->>P: Verify Peer Certificate (CA)
    P->>P: Check: AuthorizedByCert = true
    Note right of P: Signature headers missing.<br/>Signature check skipped.
    P->>M: Forward Request
    M-->>P: 200 OK
    P-->>A: 200 OK
```

### 2. Dual Auth (Cert Header + Signature)
*Combines mTLS/Client-Cert and Application-Layer Signatures.*
The Agent provides the certificate as an HTTP Header (RFC 9440 style) and includes a signature. The Proxy uses the public key from the header certificate (after verifying it) to validate the signature, avoiding a Registry lookup.

```mermaid
sequenceDiagram
    participant A as Agent
    participant P as CDN Proxy
    participant R as Registry
    participant M as Merchant

    A->>A: Sign Request
    A->>P: GET / (Header: Client-Cert + Signature)
    P->>P: Verify Client-Cert (CA)
    P->>P: Extract Public Key from Cert
    P->>P: Verify Signature (using Extracted Key)
    Note right of P: No Registry Lookup needed
    P->>M: Forward Request
    M-->>P: Response
    P-->>A: Response
```

### 3. Unauthorized Access
*Based on `src/proxy/test/unauthorized.test.ts`*
Requests missing both valid mTLS credentials and valid signatures are rejected.

```mermaid
sequenceDiagram
    participant U as Unknown Client
    participant P as CDN Proxy

    U->>P: GET /api/products (No Auth)
    P->>P: Peer Cert? No.
    P->>P: Signature? No.
    P-->>U: 403 Forbidden
```

