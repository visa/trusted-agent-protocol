# TAP Agent Design

## Goal
Implement a reference Client capable of acting as an autonomous agent in the TAP ecosystem. The Agent manages its own identity, cryptographic keys, and executes secure protocol flows.

## Architecture

*   **Runtime**: Bun
*   **Core Class**: `Agent` (implements `IAgent`)
*   **Storage**: In-memory (Keys/Certificates)

## Core Capabilities

1.  **Identity Management**:
    *   **Key Generation**: Supports Ed25519 and RSA-2048 key pairs.
    *   **Registration**: Registers identity (DID/URL) and Public Keys with the **Registry**.

2.  **Certificate Provisioning**:
    *   Generates a Certificate Signing Request (CSR) locally.
    *   Submits CSR to the **Authority**.
    *   Stores the returned Client Certificate.

3.  **Authenticated Interactions**:
    *   Wraps `fetch` to automatically apply authentication headers.
    *   **Modes**:
        *   `signature`: Adds RFC 9421 `Signature` headers.
        *   `Client-Cert`: Adds RFC 9440 `Client-Cert` header (containing the provisioned certificate).

## Workflow

1.  `agent.generateKey('my-key')`
2.  `agent.register()` -> Registry
3.  `agent.requestCertificate()` -> Authority
4.  `agent.fetch('/path')`:
    *   Sign Request (using Private Key).
    *   Attach Cert (if available).
    *   Send to Proxy.
