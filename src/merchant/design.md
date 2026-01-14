# Merchant Service Design

## Goal
Provide a mock "E-commerce" application to serve as the protected resource in the TAP ecosystem. It represents the upstream service that verified Agents interact with.

## Architecture

*   **Runtime**: Bun
*   **Framework**: Native `Bun.serve`
*   **Role**: Upstream Application (Protected by Proxy)

## Functionality

1.  **Static UI**:
    *   Serves zero-build frontend assets (VanJS).
    *   No server-side rendering, purely static delivery.

2.  **Product API**:
    *   `GET /api/products`: Returns a hardcoded list of products.
    *   `GET /api/products/:id`: Returns details for a specific product.

3.  **Security**:
    *   The Merchant Service itself **does not implement authentication**.
    *   It relies entirely on the **CDN Proxy** to filter traffic.
    *   In a real deployment, it would only accept connections from the Proxy's IP (or via mTLS).
