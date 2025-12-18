# © 2025 Visa.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import re
import time
import json
from typing import Dict, Optional, Tuple
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.exceptions import InvalidSignature
import base64
import hashlib

with open("rsa_public.pem", "r") as f:
    publicKey_rsa = f.read()

with open("ed25519_public.pem", "r") as f:
    publicKey_ed25519 = f.read()

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
            return serialization.load_pem_public_key(publicKey_rsa.encode("utf-8"))
        elif agent_name == "sample":
            # Replace with actual sample public key in production
            return serialization.load_pem_public_key(publicKey_rsa.encode("utf-8"))
        else:
            raise ValueError(f"Unknown agent name: {agent_name}")

    
    def parse_signature_headers(self, signature_agent: str, signature_input: str, signature: str) -> Optional[Dict]:
        """Parse the signature headers and extract components."""
        try:
            # Parse Signature-Agent
            agent_url = signature_agent.strip('"')
            
            # Parse Signature-Input
            signature_input_pattern = r'sig1=\("([^"]+)"\);\s*nonce="([^"]+)";\s*created=(\d+);\s*expires=(\d+);\s*keyid="([^"]+)";\s*tag="([^"]+)"'
            match = re.match(signature_input_pattern, signature_input.strip())
            
            if not match:
                return None
            
            signature_params, nonce, created, expires, keyid, tag = match.groups()
            
            # Parse Signature
            signature_pattern = r'sig1=:([^:]+):'
            sig_match = re.match(signature_pattern, signature.strip())
            
            if not sig_match:
                return None
            
            signature_value = sig_match.group(1)
            
            return {
                "agent_url": agent_url,
                "signature_params": signature_params.split(" "),
                "nonce": nonce,
                "created": int(created),
                "expires": int(expires),
                "keyid": keyid,
                "tag": tag,
                "signature": signature_value
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
            
            # Check timestamp validity
            current_time = int(time.time())
            if current_time < parsed_data["created"]:
                return False, "Signature created in the future"
            
            if current_time > parsed_data["expires"]:
                return False, "Signature expired"
            
            # Build signature string
            signature_string = self._build_signature_string(
                parsed_data["signature_params"],
                request_data,
                parsed_data["nonce"],
                parsed_data["created"],
                parsed_data["expires"]
            )
            
            # Verify signature
            public_key = self.trusted_agents[agent_url]["public_key"]
            signature_bytes = base64.b64decode(parsed_data["signature"])
            
            try:
                public_key.verify(
                    signature_bytes,
                    signature_string.encode('utf-8'),
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH
                    ),
                    hashes.SHA256()
                )
                return True, f"Verified agent: {self.trusted_agents[agent_url]['name']}"
            except InvalidSignature:
                return False, "Invalid signature"
                
        except Exception as e:
            return False, f"Verification error: {str(e)}"
    
    def _build_signature_string(self, params: list, request_data: Dict, nonce: str, created: int, expires: int) -> str:
        """Build the signature string from the parameters."""
        signature_parts = []
        
        for param in params:
            if param == "@authority":
                signature_parts.append(f'"@authority": "{request_data.get("authority", "")}"')
            elif param == "@path":
                signature_parts.append(f'"@path": "{request_data.get("path", "")}"')
            elif param == "directory-agent":
                signature_parts.append(f'"directory-agent": "{request_data.get("directory-agent", "")}"')
            elif param == "query-param":
                signature_parts.append(f'"query-param": "{request_data.get("query-param", "")}"')
        
        signature_parts.extend([
            f'"nonce": "{nonce}"',
            f'"created": {created}',
            f'"expires": {expires}'
        ])
        
        return "\n".join(signature_parts)
    
    def is_trusted_agent(self, signature_agent: str, signature_input: str, signature: str, request_data: Dict) -> Tuple[bool, str]:
        """Main method to verify if the request is from a trusted agent."""
        # Parse headers
        parsed_data = self.parse_signature_headers(signature_agent, signature_input, signature)
        
        if not parsed_data:
            return False, "Invalid signature format"
        
        # Verify signature
        return self.verify_signature(parsed_data, request_data)

# Global instance
signature_verifier = SignatureVerifier()
