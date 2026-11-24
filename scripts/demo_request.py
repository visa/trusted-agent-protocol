#!/usr/bin/env python3
"""Register a throwaway local agent and exercise the TAP-protected gateway."""

import argparse
import base64
import json
import os
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import build_opener, HTTPRedirectHandler, Request
import uuid

ROOT = Path(__file__).resolve().parents[1]


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, file, code, message, headers, new_url):
        # A different target needs a newly signed proof.
        return None


def send(url, *, headers=None, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    request = Request(url, data=data, headers=headers or {})
    try:
        with build_opener(NoRedirect).open(request, timeout=10) as response:
            return response.status, response.read()
    except HTTPError as error:
        return error.code, error.read()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', default='http://localhost:9002', help='local registry origin')
    parser.add_argument('--url', default='http://localhost:3001/agent-api/products/',
                        help='local protected GET target; redirects are not followed')
    parser.add_argument('--keyid', help='unique registry key ID; default: a random demo ID')
    parser.add_argument('--agent-env', type=Path,
                        help='optionally save raw Ed25519 keys to a NEW dotenv file, mode 0600')
    args = parser.parse_args()
    for address in (args.registry, args.url):
        parsed = urlsplit(address)
        if (parsed.scheme != 'http' or parsed.hostname not in ('localhost', '127.0.0.1', '::1')
                or parsed.username or parsed.password or parsed.fragment):
            parser.error('This demo requires HTTP loopback URLs without credentials or fragments.')
    if args.agent_env and args.agent_env.exists():
        parser.error('The agent env file already exists; existing keys will not be overwritten.')

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    sys.path.insert(0, str(ROOT / 'tap-agent'))
    try:
        from tap_signature import signature_base, signature_input, url_components
    except ImportError:
        parser.error('This example requires the canonical signer helper from the verifier fix.')

    unsigned, _ = send(args.url)
    if unsigned != 403:
        raise RuntimeError(f'Expected unsigned GET to return 403; received {unsigned}. Check route policy.')
    keyid = args.keyid or f'demo-{uuid.uuid4().hex}'
    # The sample's global key lookup is first-match; never create an ambiguous demo ID.
    from urllib.parse import quote
    lookup_status, _ = send(f'{args.registry.rstrip("/")}/keys/{quote(keyid, safe="")}')
    if lookup_status != 404:
        raise RuntimeError(f'Key lookup returned {lookup_status}; use a fresh unique keyid in a local registry.')
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    payload = {
        'name': 'Local TAP demo', 'domain': f'https://demo-{uuid.uuid4().hex}.example',
        'keys': [{'key_id': keyid, 'algorithm': 'ed25519',
                  'public_key': base64.b64encode(public).decode(), 'is_active': 'true'}],
    }
    status, body = send(f'{args.registry.rstrip("/")}/agents/register',
                        headers={'Content-Type': 'application/json'}, payload=payload)
    if status != 200:
        raise RuntimeError(f'Local registration failed with HTTP {status}. Check registry logs.')
    agent_id = json.loads(body)['agent']['id']
    if args.agent_env:
        private_raw = private.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
                                            serialization.NoEncryption())
        descriptor = os.open(args.agent_env, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'w') as output:
            output.write(f'ED25519_PRIVATE_KEY={base64.b64encode(private_raw).decode()}\n'
                         f'ED25519_PUBLIC_KEY={base64.b64encode(public).decode()}\n')
        print(f'Wrote local agent keys to {args.agent_env}; private key material is not printed.')
    created = int(time.time())
    parameters = signature_input(keyid, str(uuid.uuid4()), created, created + 120,
                                 'agent-browser-auth', 'ed25519')
    authority, path = url_components(args.url)
    signature = private.sign(signature_base(authority, path, parameters).encode())
    headers = {'Signature-Input': f'proof={parameters}',
               'Signature': f'proof=:{base64.b64encode(signature).decode()}:'}
    accepted, _ = send(args.url, headers=headers)
    replayed, _ = send(args.url, headers=headers)
    if (accepted, replayed) != (200, 403):
        raise RuntimeError(f'Expected signed/replayed statuses 200/403; received {accepted}/{replayed}.')
    print(f'PASS: unsigned=403, signed=200, replay=403; local agent ID={agent_id}, keyid={keyid}')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (RuntimeError, URLError, OSError) as error:
        print(f'Demo failed: {error}', file=sys.stderr)
        raise SystemExit(1)
