# Merchant backend

A FastAPI/SQLAlchemy product, cart, and checkout demonstration. TAP request
recognition belongs to the proxy's configured routes. The backend product/cart/
order routers do not enforce TAP themselves.

## Run

Install root Python requirements in the Python 3.11 venv from the
[quickstart](../docs/quickstart.md). From this directory:

```bash
python create_sample_data.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Startup creates tables. `create_sample_data.py` creates sample products and skips
seeding when products already exist. Inspect actual route schemas at
http://localhost:8000/docs or `/redoc`; health is `GET /health`.

| Environment input | Default |
| --- | --- |
| `DATABASE_URL` | `sqlite:///./merchant.db`, relative to this directory |
| `ALLOWED_ORIGINS` | Local browser origins; use comma-separated explicit values |

`.env` is loaded at startup. `DEBUG`, `LOG_LEVEL`, JWT secrets, and token-expiry
env examples are not configuration inputs for the current app. Console logging
is configured in `app/main.py`; the sample does not create a `logs/` file.

## Routes

| Operation | Backend endpoint |
| --- | --- |
| Search/list/create products | `GET`, `POST /api/products/` |
| Read a product | `GET /api/products/{product_id}` |
| Create/read/clear cart | `POST /api/cart/`; `GET`, `DELETE /api/cart/{session_id}` |
| Add a cart item | `POST /api/cart/{session_id}/items` |
| Update/remove an item | `PUT`, `DELETE /api/cart/{session_id}/items/{product_id}` |
| Sample card checkout | `POST /api/cart/{session_id}/checkout` |
| List/read orders | `GET /api/orders/`, `/api/orders/{order_id}` |
| Order-number lookup | `GET /api/orders/number/{order_number}` |
| Update/cancel an order | `PUT /api/orders/{order_id}/status`; `DELETE /api/orders/{order_id}` |

Examples from a separate terminal:

```bash
curl --fail http://localhost:8000/health
curl --fail http://localhost:8000/api/products/
curl --fail -X POST http://localhost:8000/api/cart/
```

Use the returned `session_id` for subsequent cart operations. The gateway exposes
these paths as `/agent-api/...` on port 3001; the ordinary `/api/...` proxy paths
remain public. See [the proxy guide](../cdn-proxy/README.md).

## Authorization and payment boundaries

There is no implemented JWT login/refresh or password-authentication system for
these commerce routes. The `/api/auth/verify-signature` utility calls the older
`app/security/signature_verification.py` helper using supplied JSON.
`/api/auth/check-verification` inspects signature-related request data. Neither
endpoint is middleware that gates the product/cart/order routers, nor a complete
consumer authorization system. The Node proxy is the maintained request-
recognition path in this series.

Card checkout performs local validation and uses a mock processor. Additional
`finalize`, `fulfill`, `/api/cart/{session_id}/x402/checkout`, and
`/api/products/premium/search` paths contain payment/facilitator scaffolding.
Some call a separate service at `http://localhost:8001`; that service is not
included in this repository. These routes are not evidence of a deployed,
verified TAP payment-container or settlement implementation. Do not use real
card/customer data for this local demonstration.

## Database maintenance and validation

Run from this directory so all tools address the same `merchant.db` file.
`update_database.py` adds selected historical order columns to that local SQLite
file. It is not a general migration framework. Back up an existing database
before applying schema changes; do not delete it as a routine setup step.

Use `/docs` to exercise changed endpoints with demo data. Build and manually
exercise the frontend when changing checkout schemas. The signature/registry
regression suites do not constitute a complete backend commerce test suite.
See [development](../docs/development.md) and [architecture](../docs/architecture.md).
