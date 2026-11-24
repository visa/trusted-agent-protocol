"""Canonical RFC 9421 parameters for the sample's minimum TAP signing profile."""

import json
from urllib.parse import urlsplit


def _string(value: str) -> str:
    if not isinstance(value, str) or not all(0x20 <= ord(c) <= 0x7E for c in value):
        raise ValueError("Signature parameter strings must contain printable ASCII.")
    return json.dumps(value, ensure_ascii=True)


def signature_input(keyid: str, nonce: str, created: int, expires: int,
                    tag: str, algorithm: str) -> str:
    """Serialize the signed Inner List; HTTP header whitespace is not signed verbatim."""
    if (type(created) is not int or type(expires) is not int or created < 0
            or not 0 < expires - created <= 480):
        raise ValueError("TAP signature lifetimes must be between one and 480 seconds.")
    if tag not in ("agent-browser-auth", "agent-payer-auth"):
        raise ValueError("Unsupported TAP intent tag.")
    if algorithm not in ("ed25519", "rsa-pss-sha256") or not keyid or not nonce:
        raise ValueError("A supported algorithm, keyid, and nonce are required.")
    return ('("@authority" "@path")'
            f';created={created};expires={expires};keyid={_string(keyid)}'
            f';alg={_string(algorithm)};nonce={_string(nonce)};tag={_string(tag)}')


def signature_base(authority: str, path: str, parameters: str) -> str:
    """Build the minimum TAP base with an absolute path that excludes the query."""
    if (not authority or not path.startswith('/') or '?' in path or '#' in path
            or any(c in authority + path for c in '\r\n')):
        raise ValueError("Invalid authority or absolute path for signing.")
    return f'"@authority": {authority}\n"@path": {path}\n"@signature-params": {parameters}'


def url_components(url: str) -> tuple[str, str]:
    """Return normalized authority and encoded path, as defined by RFC 9421."""
    parsed = urlsplit(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("A merchant HTTP or HTTPS URL without user information is required.")
    host = parsed.hostname.lower()
    if ':' in host:
        host = f'[{host}]'
    port = parsed.port
    if port is not None and port != (443 if parsed.scheme == 'https' else 80):
        host += f':{port}'
    return host, parsed.path or '/'
