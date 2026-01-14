# Authority Service Design

## Goal
Implement a standalone Certificate Authority (CA) service for the TAP ecosystem. This service is responsible for establishing a root of trust, issuing certificates to agents, and enabling certificate-based authentication (mTLS/RFC 9440) at the Proxy.

## Architecture

*   **Runtime**: Bun
*   **Cryptography**: `node-forge` (for CA generation and CSR signing)
*   **API**: HTTP (Bun.serve)

## Core Responsibilities

1.  **Root CA Management**:
    *   Generates a self-signed Root CA certificate upon startup (or loads persistence if implemented).
    *   Exposes the CA certificate publicly for trust establishment.

2.  **Certificate Issuance**:
    *   Accepts Certificate Signing Requests (CSRs) from Agents.
    *   Validates CSR signature.
    *   Issues a Client Certificate signed by the Root CA.
    *   Embeds the Agent ID in the certificate Subject (Common Name).

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/authority/cert` | **Public**: Get the Root CA Certificate (PEM format) |
| `POST` | `/authority/sign` | **Protected**: Sign a CSR. Body: `{ csr: string, agentId: string }` |

## Data Flow

1.  **Startup**: Authority generates `caCert` and `caKey`.
2.  **Trust**: Proxy fetches `/authority/cert` to verify future client connections.
3.  **Issuance**:
    *   Agent creates KeyPair + CSR.
    *   Agent sends CSR to `/authority/sign`.
    *   Authority validates CSR and signs it with `caKey`.
    *   Returns Client Certificate (PEM) to Agent.
