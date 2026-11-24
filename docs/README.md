# Documentation map

Start with the task you need to perform, then read the linked source and tests.

| Goal | Read in order | Finish with |
| --- | --- | --- |
| Understand the project quickly | [Root README](../README.md), [architecture](architecture.md) | Identify the five services and which routes require TAP |
| Run a signed request | [Quickstart](quickstart.md), [proxy guide](../cdn-proxy/README.md) | `python scripts/demo_request.py` |
| Change signing or verification | [Protocol guide](protocol.md), [agent guide](../tap-agent/README.md), [proxy guide](../cdn-proxy/README.md) | Proxy and signing regression tests |
| Change registration or revocation | [Registry guide](../agent-registry/README.md), [protocol guide](protocol.md) | Registry SQLite regression tests |
| Change commerce behavior | [Backend guide](../merchant-backend/README.md), [frontend guide](../merchant-frontend/README.md) | Backend API inspection, frontend build, manual browser check |
| Contribute a fix | [Agent instructions](../AGENTS.md), [development guide](development.md) | `python scripts/check.py` and relevant manual validation |

The public protocol sources and their interpretation are listed in the
[protocol guide](protocol.md). These documents describe the code in this checkout;
they are not a replacement for hosted Visa API documentation.

For maintenance, update the owning guide when a route, dependency command, key
format, or configuration input changes. `python scripts/check.py --docs-only`
checks relative Markdown file links and code-fence balance without installing
application dependencies or contacting the network.
