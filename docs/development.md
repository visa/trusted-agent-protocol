# Development and validation

Read [AGENTS.md](../AGENTS.md) and the [architecture](architecture.md) first.
Use Python 3.11 and Node 22/24. Dependency versions in the manifests are the
repository's current declarations, not a claim that they are the latest releases.
Dependency upgrades should be reviewed and tested separately from protocol fixes.

## One local entry point

After [installation](quickstart.md):

```bash
python scripts/check.py
```

This checks local Markdown file links and balanced code fences, then runs the
Node proxy suite, Python signing tests, and registry SQLite tests. The command
works from any working directory. It does not install dependencies, run browser
automation, or contact hosted Visa services. Node's Python signing fixtures use
the interpreter running this command through the `PYTHON` environment variable.

## Focused checks

Run from the repository root:

| Change | Command |
| --- | --- |
| Documentation | `python scripts/check.py --docs-only` |
| Signature verification and Python interop | `npm --prefix cdn-proxy test` |
| Gateway routing only | `node --test cdn-proxy/test/agent-api.test.js` |
| Signing and private-key logging | `python -m unittest discover -s tap-agent/tests -v` |
| Registry lifecycle | `python -m unittest discover -s agent-registry/tests -v` |
| Frontend | `npm --prefix merchant-frontend run build` plus a browser exercise |
| Complete running request flow | `python scripts/demo_request.py` with registry, backend, and proxy running |

When invoking the Node suite directly, activate the intended Python venv or set
`PYTHON` to its interpreter. Browser automation requires Playwright Chromium and
the full storefront; signature unit tests alone do not validate that flow.

For CI-equivalent core tests without Streamlit/Playwright, create the same Python
3.11 venv and install only:

```bash
python -m pip install -r agent-registry/requirements-test.txt 'cryptography>=43.0.1'
npm --prefix cdn-proxy install --ignore-scripts
python scripts/check.py
```

The test suites generate their own keys, and registry tests use in-memory SQLite.
They do not rely on a developer's `.env`, persisted database, or sample key seed.

## Review expectations

- For protocol changes, cite the public TAP rule and RFC section. Add a test that
  fails for the concrete previous behavior; test both refusal and valid interop.
- For route changes, verify the original external target before rewriting and
  check that refused requests never reach the backend. Keep ordinary storefront
  policy explicit.
- For registry changes, exercise actual route functions with SQLite and preserve
  independently disabled key state across agent reactivation.
- For signing/logging changes, verify emitted signatures and confirm private key
  bytes and prefixes never enter captured output.
- Update the owning README, `.env.example`, task map, and guide when their facts
  change. `--docs-only` checks local file targets/fences, not remote links or prose
  accuracy; inspect routes and configuration reads as well.

Describe exactly which checks ran and which behavior remains manual. Do not
present a mock checkout, decoded JWT, or signature over only authority/path as a
verified consumer/payment authorization flow.

## CI and contributions

Workflows under `.github/workflows/` cover proxy conformance, gateway routing,
registry lookup, key logging, and documentation. Review the workflow files for
the exact runtime matrix. Tests can also run in a fork when upstream execution
is unavailable; report the distinction in the PR.

Use a focused branch and PR. Do not commit `.env` files, private keys, SQLite
databases, dependency directories, or generated frontend builds. This repository
has a tracked frontend `.env` containing public development defaults only; never
add credentials to it. The repository
currently ignores npm lockfiles; changing dependency reproducibility policy
requires a separate deliberate change. Follow [LICENSE.md](../LICENSE.md).
