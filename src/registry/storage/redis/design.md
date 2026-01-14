# Redis Storage Backend

## Goal
Implement `RegistryService` using Bun's native Redis client.

## Requirements
-   Implement `RegistryService`.
-   Persist Agents in Hash `registry:agent:{id}`.
-   Persist Keys in String `registry:key:{kid}`.
-   Indices:
    -   `registry:agents:index` (Set of IDs).
    -   `registry:lookup:domain:{domain}` (String -> ID).
    -   `registry:agent:{id}:keys` (Set of Kids).

## Architecture
-   `src.ts`: `RedisRegistryService` class.
-   `module.ts`: Exports.
-   `interface.ts`: Re-exports.
