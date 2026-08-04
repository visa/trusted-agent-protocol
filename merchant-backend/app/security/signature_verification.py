# © 2025 Visa.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import re
import time
from typing import Dict, Optional, Tuple
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature
import base64

publicKey = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAysHJFJ9uoVvU1sH2x3TV
bwW3nfyp34eOb8w177Ei/Bx8pk+8Ibu1yulV0nCBl/c9insg1k2x7dw1jRDZHJBG
wIpCdRL0GKm6qIdtsjeOcMnkI5ET0zGpxkhuRUwRblYW3LAdAq1Gja1WSPQKRT8r
EhUsmSlDWgAf0rFna15Ok6zOO3q21LtrEjnJSrgO+cr33YH0IAdALD7hqtPYK7+/
7dD/XIgGW9cX0USMxdDBUt8TnN2TYar5YXetpMnFOPpQHiGpKTkDwrRggcthUyuC
e1CoL/9a/DWilJwd481QkurvZqGaKegX5DlI+jLNvfi8TWMS3jCjknyOLg54KU86
LQIDAQAB
-----END PUBLIC KEY-----"""

# Replay cache to prevent nonce reuse (in production this would be a shared/
# persistent store; an in-memory map suffices for the single-process reference
# merchant backend). Each nonce is retained until the expiry of the signature
# that used it: while the signature is still valid the nonce blocks a replay,
# and once it expires the timestamp check rejects it regardless, so the entry
# is purged. Keying retention to the signature's own expiry (rather than a fixed
# TTL) closes the replay window that opens when a signature outlives the TTL.
_nonce_cache: Dict[str, int] = {}


def _purge_expired_nonces(now: int) -> None:
    for nonce, expires_at in list(_nonce_cache.items()):
        if expires_at < now:
            del _nonce_cache[nonce]


class SignatureVerifier:
    def __init__(self):
        # In production, these would be loaded from secure storage/config
        self.trusted_agents = {
            "https://directory.example.com": {
                "public_key": self._load_public_key("example"),
                "name": "Example Directory"
            },
            "https://payment.sample.org": {
                "public_key": self._load_public_key("sample"),
                "name": "Sample Payment Directory"
            }
        }

    def _load_public_key(self, agent_name: str):
        """Load public key for the agent. In production, load from secure storage."""

        if agent_name == "example":
            return serialization.load_pem_public_key(publicKey.encode("utf-8"))
        elif agent_name == "sample":
            # Replace with actual sample public key in production
            return serialization.load_pem_public_key(publicKey.encode("utf-8"))
        else:
            raise ValueError(f"Unknown agent name: {agent_name}")

    def parse_signature_headers(self, signature_agent: str, signature_input: str, signature: str) -> Optional[Dict]:
        """Parse the RFC 9421 signature headers and extract components.

        Accepts the standard RFC 9421 wire form used by the CDN proxy reference,
        e.g.:
            Signature-Input: sig2=("@authority" "@path"); created=...; expires=...;
                             keyid="..."; alg="rsa-pss-sha256"; nonce="..."; tag="..."
            Signature:       sig2=:<base64>:
        The covered-component list is a space separated list of individually
        quoted identifiers (RFC 9421 sec 2.1), the signature parameters are
        unordered, and the label (sig1/sig2/...) is arbitrary.
        """
        try:
            agent_url = signature_agent.strip('"')

            # <label>=(<components>); <params...>
            input_match = re.match(r'^\s*(\w+)=\(([^)]*)\);\s*(.+)$', signature_input.strip())
            if not input_match:
                return None
            label, components_blob, attr_string = input_match.groups()

            # Covered components: split on whitespace and strip quotes. This
            # accepts the RFC 9421 individually-quoted form ("a" "b") as the
            # CDN proxy emits.
            signature_params = [p.strip('"') for p in components_blob.split() if p.strip()]

            # Signature parameters are unordered structured-field members.
            attributes: Dict[str, object] = {}
            for key, value in re.findall(r'(\w+)=("[^"]*"|\d+)', attr_string):
                if value.startswith('"') and value.endswith('"'):
                    attributes[key] = value[1:-1]
                else:
                    attributes[key] = int(value)

            if "created" not in attributes or "expires" not in attributes:
                return None

            # keyId (camelCase, as the CDN proxy emits) or keyid.
            keyid = attributes.get("keyId") or attributes.get("keyid")
            algorithm = str(attributes.get("alg", "rsa-pss-sha256")).lower()

            # Signature value: <label>=:<base64>:
            sig_match = re.match(r'^\s*(\w+)=:([^:]+):\s*$', signature.strip())
            if not sig_match:
                return None
            signature_value = sig_match.group(2)

            return {
                "label": label,
                "agent_url": agent_url,
                "signature_params": signature_params,
                "nonce": attributes.get("nonce"),
                "created": int(attributes["created"]),
                "expires": int(attributes["expires"]),
                "keyid": keyid,
                "algorithm": algorithm,
                "tag": attributes.get("tag"),
                "signature": signature_value,
                # The verbatim Signature-Input value is required to reconstruct
                # the @signature-params line of the signature base.
                "signature_input_raw": signature_input.strip(),
            }
        except Exception as e:
            print(f"Error parsing signature headers: {e}")
            return None

    def verify_signature(self, parsed_data: Dict, request_data: Dict) -> Tuple[bool, str]:
        """Verify the signature against the request data."""
        try:
            agent_url = parsed_data["agent_url"]

            # Check if agent is trusted
            if agent_url not in self.trusted_agents:
                return False, f"Unknown agent: {agent_url}"

            # Check timestamp validity (allow small clock skew on created, as the
            # CDN proxy does, to tolerate minor client/server drift).
            current_time = int(time.time())
            if current_time + 60 < parsed_data["created"]:
                return False, "Signature created in the future"
            if current_time > parsed_data["expires"]:
                return False, "Signature expired"

            # Replay protection: a nonce is required and may be seen only once.
            nonce = parsed_data.get("nonce")
            if not nonce:
                return False, "Missing nonce"
            _purge_expired_nonces(current_time)
            if nonce in _nonce_cache:
                return False, "Replay detected: nonce already used"

            # Build the RFC 9421 signature base and verify it BEFORE recording
            # the nonce, so an invalid signature cannot burn a valid nonce.
            signature_string = self._build_signature_string(
                parsed_data["signature_params"],
                request_data,
                parsed_data["signature_input_raw"],
            )

            public_key = self.trusted_agents[agent_url]["public_key"]
            signature_bytes = base64.b64decode(parsed_data["signature"])
            algorithm = parsed_data.get("algorithm", "rsa-pss-sha256")

            try:
                if algorithm == "rsa-pss-sha256":
                    if not isinstance(public_key, RSAPublicKey):
                        return False, "Key does not match rsa-pss-sha256 algorithm"
                    public_key.verify(
                        signature_bytes,
                        signature_string.encode("utf-8"),
                        padding.PSS(
                            mgf=padding.MGF1(hashes.SHA256()),
                            salt_length=padding.PSS.MAX_LENGTH,
                        ),
                        hashes.SHA256(),
                    )
                elif algorithm == "ed25519":
                    if not isinstance(public_key, Ed25519PublicKey):
                        return False, "Key does not match ed25519 algorithm"
                    public_key.verify(signature_bytes, signature_string.encode("utf-8"))
                else:
                    return False, f"Unsupported algorithm: {algorithm}"
            except InvalidSignature:
                return False, "Invalid signature"

            # Signature is valid: record the nonce (retained until the signature
            # expires) to block replays within its validity window.
            _nonce_cache[nonce] = parsed_data["expires"]
            return True, f"Verified agent: {self.trusted_agents[agent_url]['name']}"

        except Exception as e:
            return False, f"Verification error: {str(e)}"

    def _build_signature_string(self, params: list, request_data: Dict, signature_input_raw: str) -> str:
        """Build the RFC 9421 signature base string.

        Mirrors the CDN proxy reference (buildRFC9421SignatureString): each
        covered component is emitted as `"<name>": <value>`, and the base ends
        with the mandatory `"@signature-params"` line (RFC 9421 sec 2.5) carrying
        the verbatim signature parameters. Without that final line the base can
        never match a conformant signer's, so every RFC 9421 signature would be
        rejected.
        """
        components = []

        for param in params:
            if param == "@authority":
                components.append(f'"@authority": {request_data.get("authority", "")}')
            elif param == "@path":
                components.append(f'"@path": {request_data.get("path", "")}')
            elif param == "content-type":
                content_type = request_data.get("contentType") or request_data.get("content-type") or "application/json"
                components.append(f'"content-type": {content_type}')
            elif param == "host":
                host = request_data.get("host") or request_data.get("authority", "")
                components.append(f'"host": {host}')
            else:
                # Custom covered header (e.g. directory-agent, query-param).
                value = request_data.get(param)
                if value:
                    components.append(f'"{param}": {value}')

        # @signature-params is the verbatim parameters portion of Signature-Input
        # (the label and leading '=' removed), added as the final line.
        signature_params = signature_input_raw
        eq_index = signature_params.find("=")
        if eq_index != -1:
            signature_params = signature_params[eq_index + 1:]
        components.append(f'"@signature-params": {signature_params}')

        return "\n".join(components)

    def is_trusted_agent(self, signature_agent: str, signature_input: str, signature: str, request_data: Dict) -> Tuple[bool, str]:
        """Main method to verify if the request is from a trusted agent."""
        parsed_data = self.parse_signature_headers(signature_agent, signature_input, signature)

        if not parsed_data:
            return False, "Invalid signature format"

        return self.verify_signature(parsed_data, request_data)


# Global instance
signature_verifier = SignatureVerifier()
