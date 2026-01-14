# Trusted Agent Protocol (TAP) Reference Implementation

A secure, edge-enforced system for authenticating Autonomous AI Agents using the **Trusted Agent Protocol**.

## Overview

This project implements a reference architecture where a **CDN Proxy** sits between AI Agents and Merchant Applications, enforcing identity and security at the edge.

It supports multiple standard authentication mechanisms to ensure compatibility, compliance, and scalability:
1.  **Mutual TLS / Client Certificates** (RFC 9440) for scalable, connection-level identity verification by the CA.
2.  **HTTP Message Signatures** (RFC 9421) for fine-grained, request-level proof-of-possession and compatibility with application-layer signing.

For detailed architecture and protocol diagrams, see [src/design.md](src/design.md).

## Components

*   **Agent**: The client representing the AI user. Manages keys, requests certificates, and signs requests.
*   **CDN Proxy**: The edge gatekeeper. Verifies mTLS certificates and HTTP Signatures before forwarding traffic.
*   **Registry**: The Identity Provider. Stores Agent DID documents and public keys.
*   **Authority**: A private Certificate Authority (CA) that issues short-lived authentication certificates to registered Agents.

## Getting Started

### Prerequisites
*   [Bun](https://bun.sh) (v1.0+)

### Installation
```bash
bun install
```

### Running Tests
Run the full test suite:
```bash
bun test
```

> [!WARNING]
> **Known Issue with Bun Test Runner**
> You may encounter failing tests when running the full suite (`bun test`) due to how Bun handles client certificates or parallel execution context.
>
> If this happens, run the proxy tests in isolation to verify correctness:
> ```bash
> bun test src/proxy/_test.ts
> ```

## Project Status

**Alpha / Experimental**

This is a proof-of-concept reference implementation. It works end-to-end but is not yet hardened for production use.

### Caveats
*   **Self-Signed CA**: The `Authority` service generates a fresh self-signed Root CA on every restart (unless persistence is added).
*   **In-Memory Storage**: The `Registry` defaults to in-memory storage. Restarting the service wipes registered agents.
*   **Protocol Support**: Implements a subset of RFC 9421 (Signatures) and RFC 9440 (Client-Cert Headers) sufficient for demonstration.
