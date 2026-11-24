# Local quickstart

Run commands from the repository root unless a block explicitly changes directory.
Use Python 3.11 and Node.js 22 or 24, matching the regression CI. The shell examples
use macOS/Linux syntax. No Visa developer credentials or real payment data are
needed for the request-recognition demo.

## Install once

```bash
git clone https://github.com/visa/trusted-agent-protocol.git
cd trusted-agent-protocol
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
npm --prefix cdn-proxy install
npm --prefix merchant-frontend install
```

For a PR checkout, fetch/check out the relevant branch instead of assuming its
changes are already on `main`. The full guides and check runner describe the
verifier, revocation, protected gateway, and documentation fixes together.

The service defaults work without copying `.env.example` files. If customizing,
create each `.env` in its service directory and set only documented variables.
Never overwrite an existing `.env` or database as part of setup.

## Check the code without services

```bash
python scripts/check.py
npm --prefix merchant-frontend run build
```

The checks generate throwaway keys and use ephemeral servers/in-memory SQLite.
They do not start the full storefront, open a browser, or contact hosted services.
For documentation-only work: `python scripts/check.py --docs-only` uses only the
Python standard library. See [development](development.md) for focused commands.

## Run a signed API request

Only three services are needed. In each new terminal, start at the repository root
and activate `.venv` before changing directory.

Terminal 1 — local key registry:

```bash
source .venv/bin/activate
cd agent-registry
python main.py
```

Terminal 2 — merchant API, including sample products:

```bash
source .venv/bin/activate
cd merchant-backend
python create_sample_data.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal 3 — proxy:

```bash
cd cdn-proxy
npm start
```

In a fourth terminal at the repository root:

```bash
source .venv/bin/activate
curl --fail http://localhost:9002/
curl --fail http://localhost:8000/health
python scripts/demo_request.py
```

Expected result: `PASS: unsigned=403, signed=200, replay=403`, followed by local
agent/key IDs. The script registers one new local agent per run, keeps its
throwaway private key in memory, signs the external `/agent-api/products/` path,
and checks replay rejection. It uses only loopback HTTP URLs and does not follow
redirects. It is a request-recognition demonstration, not a checkout test.

The old `populate_sample_data.py` registers fixture public keys. It does not
generate matching private keys for your agent and is not needed for this flow.

## Add the storefront

In a new terminal at the repository root:

```bash
cd merchant-frontend
npm run dev
```

Open http://localhost:3001 for the proxied storefront; Vite itself listens on
3000. The frontend's development API base should be empty or unset so `/api/...`
uses the current origin. A previously configured absolute
`VITE_API_BASE_URL=http://localhost:8000` bypasses the proxy; update that local
setting if you want to exercise the proxy. Ordinary browser calls remain public.

## Optional Streamlit browser agent

Start with a fresh local registry and no existing `tap-agent/.env`. This UI's
Ed25519 path uses the hardcoded registry key ID `primary-ed25519`; changing the
displayed Agent ID does not select a different signing key.

```bash
python scripts/demo_request.py --keyid primary-ed25519 --agent-env tap-agent/.env
python -m playwright install chromium
cd tap-agent
python -m streamlit run agent_app.py --server.port 8501
```

The script refuses to overwrite an existing env file or an already resolvable
active key ID. It creates the env file with mode 0600. Open http://localhost:8501,
choose Ed25519 and merchant URL `http://localhost:3001/product/1`, and use the
reported local agent ID. Generate/reset fresh input before another attempt.
Only Ed25519 keys are configured by this command; RSA requires a separately
generated matching PEM pair and a registry key named `primary`.

The browser automation is a separate manual flow. It reuses configured signature
headers; do not assume every API call or navigation gets a fresh operation-bound
proof. Extending it to protected API calls requires per-request signing.

## Diagnose failures

| Symptom | Check |
| --- | --- |
| Missing module or incompatible Python | Activate the Python 3.11 venv; install root requirements |
| Full check runner reports missing fix files | Confirm this checkout includes the complete PR series |
| Registry connection refused | Registry port 9002, working directory, and process output |
| 503 from protected route | Registry availability and valid JSON key lookup response |
| 403 for a fresh signed request | Exact authority/path, clock, key ID, key/parent active flags, algorithm, fresh nonce |
| 307/308 response | Use the canonical slash-terminated collection URL; sign redirects afresh |
| Gateway/backend unavailable | Backend port 8000; storefront additionally needs Vite on 3000 |
| Empty catalog or missing product | Run `create_sample_data.py` from `merchant-backend`; query `/api/products/` |
| Key exists or env file exists | Reuse your existing configuration manually or choose a fresh key ID; do not overwrite keys |
| Playwright executable missing | Run `python -m playwright install chromium` in the active venv |
| Port 8001 facilitator errors | That separate payment service is not included in this repository |

Stop servers with Ctrl-C. Keep local databases/keys out of commits. See the
[configuration tables](../cdn-proxy/README.md) and component guides for details.
