# SQLite Storage Backend

## Goal
Implement `RegistryService` using Bun's native SQLite client.

## Requirements
-   Implement `RegistryService`.
-   Persist Agents and Keys in SQL tables.
-   Tables: `agents`, `keys`.
-   Persistent file storage (default `registry.db`).

## Architecture
-   `src.ts`: `SqliteRegistryService` class.
-   `module.ts`: Exports.
-   `interface.ts`: Re-exports.
