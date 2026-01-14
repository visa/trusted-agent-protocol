# Merchant Service

A lightweight Merchant Application for the Trusted Agent Protocol (TAP).
Serves a static VanJS UI and a read-only Product API.

## Features
-   **No Database**: Uses in-memory static data for simplicity.
-   **VanJS UI**: Lightweight, client-side UI served from the root.
-   **API**: Provides product listings and details.

## Configuration
Environment variables:
-   `PORT`: Port to listen on (Default: 3000).
-   `DEBUG`: Enable debug logging (Default: false).

## API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Serves Static UI |
| `GET` | `/api/products` | List all products |
| `GET` | `/api/products/:id` | Get product details |

## Development

```bash
# Start the service
bun run merchant

# Run tests
bun run test:merchant
```
