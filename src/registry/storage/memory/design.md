# Memory Storage Backend

## Goal
Implement `RegistryService` using in-memory `Map`s for ephemeral storage.

## Requirements
-   Implement `RegistryService`.
-   Use `Map<string, Agent>` and `Map<string, RegistryKey>`.
-   No persistence (data lost on restart).
-   Fast and synchronous-like (but async API).

## Architecture
-   `src.ts`: Contains `MemoryRegistryService` class.
-   `module.ts`: Exports the class.
-   `interface.ts`: Re-exports core interfaces.
