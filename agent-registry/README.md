# Agent registry

A local FastAPI/SQLAlchemy sample for registering agents and public keys. It
supplies keys to the proxy; it does not verify incoming merchant signatures itself
and is not Visa's hosted VARS service.

## Run

Install the root Python requirements in a Python 3.11 venv as described in the
[quickstart](../docs/quickstart.md). Then, from this directory:

```bash
python main.py
```

The API listens on http://localhost:9002; inspect its actual schemas at
http://localhost:9002/docs. Startup creates tables. No public-key seed is needed
for the [signed request example](../scripts/demo_request.py).

| Configuration input | Behavior |
| --- | --- |
| `DATABASE_URL` | Defaults to `sqlite:///./agent_registry.db`, relative to this directory |
| Listen address/port | `python main.py` uses `0.0.0.0:9002`; `HOST`/`PORT` env values are not read |

To bind only to loopback with the same API port:

```bash
python -m uvicorn main:app --host 127.0.0.1 --port 9002
```

The sample endpoints have no authenticated registration/admin control plane.
An HTTP 200 here does not establish hosted Visa approval or merchant trust policy.

## API shape

| Operation | Endpoint |
| --- | --- |
| Register or update by domain | `POST /agents/register` |
| List agents | `GET /agents` |
| Read/update/deactivate an agent | `GET`, `PUT`, `DELETE /agents/{agent_id}` |
| Add a key | `POST /agents/{agent_id}/keys` |
| Read an agent's key | `GET /agents/{agent_id}/keys/{key_id}` |
| Proxy's key-only lookup | `GET /keys/{key_id}` |
| Legacy domain lookup | `GET /agents/domain/{domain}` |

Registration uses a **keys array**, not top-level key fields. Example shape
(`BASE64_RAW_32_BYTE_PUBLIC_KEY` must be replaced with your generated public key):

```json
{
  "name": "Local demo agent",
  "domain": "https://local-demo.example",
  "is_active": "true",
  "keys": [
    {
      "key_id": "unique-demo-key",
      "algorithm": "ed25519",
      "public_key": "BASE64_RAW_32_BYTE_PUBLIC_KEY",
      "is_active": "true"
    }
  ]
}
```

The response wraps the agent as `{"success": true, "message": "...", "agent": {...}}`.
Registering an existing domain updates that agent and matching key IDs; it is not
an append-only operation. The active-state values are strings, not JSON booleans.

## Keys and revocation

- Ed25519 public keys are raw 32-byte values encoded in standard Base64, not
  Base64url or PEM. Agent private keys never belong in registration payloads.
- Legacy RSA public keys are PEM `BEGIN PUBLIC KEY` values. The proxy's legacy
  RSA-PSS/SHA-256 convention is described in the [protocol guide](../docs/protocol.md).
- Key lookups require both an active key and active parent agent. Agent
  reactivation preserves independently disabled key flags.
- Key-only lookup is first-match, while stored key IDs are scoped to agents.
  Use globally unique IDs for independent agents to avoid ambiguous lookup.
- Validation checks format, not proof of private-key possession or domain control.

`populate_sample_data.py` posts fixture public keys to a running registry; it does
not generate private keys matching your local agent. Use the quickstart's
throwaway-key example instead of assuming those fixtures can sign requests.

## Optional UI and checks

From this directory, with root dependencies installed:

```bash
python -m streamlit run registry_ui.py --server.port 8502
```

The UI at http://localhost:8502 calls the API on port 9002. It is a separate process,
not a `/ui` route on the API server.

From the repository root:

```bash
python -m unittest discover -s agent-registry/tests -v
```

The tests use actual route functions and in-memory SQLite. For architecture and
ownership, see [AGENTS.md](../AGENTS.md).
