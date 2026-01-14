# CDN Proxy Design

## Goal
Implement a secure "Edge" Proxy that intercepts HTTP traffic and enforces the Trusted Agent Protocol. It supports dual-layer authentication: mutual TLS (or Application-Layer Client Certificates) AND HTTP Message Signatures (RFC 9421).

## Architecture

*   **Runtime**: Bun
*   **Protocol**: HTTPS (TLS)
*   **Dependencies**: `@interledger/http-signature-utils`, `node-forge`

## Authentication Logic

The Proxy supports flexible authentication strategies to balance security, performance, and standard compliance:

1.  **Layer 1: Identity (Certificate)**
    *   Checks for **mTLS** peer certificate OR `Client-Cert` header.
    *   **Validation**: Verifies certificate chain against the **Authority Service** CA.
    *   **Optimization**: If a valid certificate is presented, the Proxy trusts the Agent ID and extracts the Public Key directly from the certificate, bypassing the need for a Registry lookup.

2.  **Layer 2: proof-of-Possession (Signature)**
    *   Checks for RFC 9421 `Signature` and `Signature-Input` headers.
    *   **Key Resolution**:
        *   If Layer 1 succeeded (Valid Cert): Use Key from Cert.
        *   If Layer 1 failed/missing: Lookup Public Key from **Registry** using `keyId`.
    *   **Verification**: Validates the HTTP request signature using the resolved Public Key.

## Proxy Logic

1.  **Startup**:
    *   Fetch and cache Root CA from **Authority Service**.
    *   Start TLS Server.

2.  **Request Handling**:
    *   `GET /test-proxy`: Return 200 OK (Bypass).
    *   **All Other Requests**:
        *   Authenticate (Cert + Sig).
        *   If valid: Rewrite path (if needed) and forward to **Merchant**.
        *   If invalid: Return 401/403.

## Configuration

*   `port`: Listening port (default 3001).
*   `authorityUrl`: URL to fetch CA cert.
*   `registryUrl`: URL for fallback key lookup.
*   `merchantUrl`: Upstream destination.
*   `tls`: Server TLS configuration (Key/Cert).
