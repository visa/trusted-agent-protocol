# TAP Agent Client

The End-User client for the Trusted Agent Protocol (TAP).
It generates keys, registers with the Registry, and signs HTTP requests to access the Merchant via the CDN Proxy.

## Features
-   **Identity Management**: Generates ephemeral Ed25519 keys (JWK).
-   **Registration**: Automates registration with the Agent Registry.
-   **RFC 9421 Signing**: Automatically signs requests with `Signature` and `Signature-Input` headers.

## Usage (CLI)

The `agent` module runs a demonstration scenario:
1.  Creates a new Agent Identity.
2.  Registers it.
3.  Fetches `/product/1` from the Merchant via the Proxy.

```bash
bun run agent
```

## Configuration
-   `AGENT_REGISTRY_URL`: Default `http://localhost:9002`
-   `CDN_PROXY_URL`: Default `http://localhost:3001`
-   `DEBUG`: `true` for verbose logs.

## Testing
```bash
bun run test:agent
```
