# Agent Registry Service Design

## Goal
Implement a Registry Service for TAP agents that manages Agents and their public keys (JWKs). It acts as the source of truth for agent identities and provides key lookup for the Proxy (fallback mechanism).

## Architecture

*   **Runtime**: Bun
*   **Storage**: Pluggable Strategy Pattern
    *   **Memory**: For testing/local dev (Default).
    *   **Redis**: For production/shared state.
    *   **SQLite**: File-based persistence.
*   **API**: HTTP (Bun.serve) with CORS support.

## Data Model

### Entities
*   **Agent**:
    *   `id`: UUID
    *   `name`: string
    *   `domain`: string (Unique)
    *   `status`: "active" | "inactive" | "revoked"
    *   `created_at`: timestamp
    *   `updated_at`: timestamp
*   **Key**:
    *   `kid`: string (Key ID)
    *   `agent_id`: string (FK)
    *   `publicKey`: JWK Object
    *   `status`: "active" | "revoked"

## Module Structure

*   `interface.ts`: Defines `IRegistryService` interface and data types (`Agent`, `RegistryKey`).
*   `module.ts`: HTTP Server implementation mapping routes to service methods.
*   `storage/`: Directory containing storage implementations.
    *   `memory/`: In-memory Map implementation.
    *   `redis/`: Redis-backed implementation.
    *   `sqlite/`: SQLite-backed implementation.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/agents` | List all agents |
| `POST` | `/agents` | Create Agent (requires JWK) |
| `GET` | `/agents/:id` | Get Agent details |
| `PUT` | `/agents/:id` | Update Agent |
| `DELETE` | `/agents/:id` | Deactivate/Delete Agent |
| `POST` | `/agents/:id/keys` | Add new Key to Agent |
| `GET` | `/agents/:id/keys` | List Agent Keys |
| `GET` | `/keys/:kid` | **Global Key Lookup** (Used by Proxy) |
