import base64
import json
import typing as ty
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ed25519, padding

def get_ed25519_keys():
    """Get Ed25519 keys from environment ed25519_private.pem and ed25519_public.pem"""
    with open("./ed25519_private.pem", "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)
        assert isinstance(private_key, ed25519.Ed25519PrivateKey)
    
    with open("./ed25519_public.pem", "rb") as f:
        public_key = serialization.load_pem_public_key(f.read())
        assert isinstance(public_key, ed25519.Ed25519PublicKey)
    
    return private_key, public_key

def get_rsa_keys():
    """Get RSA keys from environment rsa_private.pem and rsa_public.pem"""
    with open("./rsa_private.pem", "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)
        assert isinstance(private_key, rsa.RSAPrivateKey)
    
    with open("./rsa_public.pem", "rb") as f:
        public_key = serialization.load_pem_public_key(f.read())
        assert isinstance(public_key, rsa.RSAPublicKey)
    
    return private_key, public_key

def create_http_message_signature(private_key: ty.Union[rsa.RSAPrivateKey, ed25519.Ed25519PrivateKey], authority: str, path: str, keyid: str, nonce: str, created: int, expires: int, tag: str) -> ty.Tuple[str, str]:
    """Create HTTP Message Signature following RFC 9421 syntax"""
    try:
        # Create signature parameters string
        signature_params = f'("@authority" "@path"); created={created}; expires={expires}; keyId="{keyid}"; alg="rsa-pss-sha256"; nonce="{nonce}"; tag="{tag}"'
        
        # Create the signature base string following RFC 9421 format
        signature_base_lines = [
            f'"@authority": {authority}',
            f'"@path": {path}',
            f'"@signature-params": {signature_params}'
        ]
        signature_base = '\n'.join(signature_base_lines)
        
        print(f"🔐 RFC 9421 Signature Base String:\n{signature_base}")
        print(f"🌐 Authority: {authority}")
        print(f"📍 Path: {path}")
        print(f"📋 Signature Params: {signature_params}")

        
        # Sign the signature base string using RSA-PSS (matching the algorithm declared)
        signature = private_key.sign(
            signature_base.encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        
        # Format the signature-input header (RFC 9421 format)
        signature_input_header = f'sig2=("@authority" "@path"); created={created}; expires={expires}; keyId="{keyid}"; alg="rsa-pss-sha256"; nonce="{nonce}"; tag="{tag}"'
        
        # Format the signature header (RFC 9421 format)
        signature_header = f'sig2=:{signature_b64}:'
        
        print(f"✅ Created RFC 9421 compliant signature")
        print(f"📤 Signature-Input: {signature_input_header}")
        print(f"🔒 Signature: {signature_header}")
        
        return signature_input_header, signature_header
        
    except Exception as e:
        print(f"❌ Error creating HTTP message signature: {str(e)}")
        return "", ""

def create_ed25519_signature(private_key: ed25519.Ed25519PrivateKey, authority: str, path: str, keyid: str, nonce: str, created: int, expires: int, tag: str) -> ty.Tuple[str, str]:
    """Create HTTP Message Signature using Ed25519 following RFC 9421"""
    try:
        from cryptography.hazmat.primitives.asymmetric import ed25519
        
        print(f"🔐 Creating Ed25519 signature...")
        print(f"🌐 Authority: {authority}")
        print(f"📍 Path: {path}")
        
        # Create signature parameters string
        signature_params = f'("@authority" "@path"); created={created}; expires={expires}; keyId="{keyid}"; alg="ed25519"; nonce="{nonce}"; tag="{tag}"'
        
        # Create the signature base string
        signature_base_lines = [
            f'"@authority": {authority}',
            f'"@path": {path}',
            f'"@signature-params": {signature_params}'
        ]
        signature_base = '\n'.join(signature_base_lines)
        
        print(f"🔐 Ed25519 Signature Base String:\n{signature_base}")
        
        # Sign with Ed25519 (no padding needed)
        signature = private_key.sign(signature_base.encode('utf-8'))
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        
        # Format headers
        signature_input_header = f'sig2=("@authority" "@path"); created={created}; expires={expires}; keyId="{keyid}"; alg="ed25519"; nonce="{nonce}"; tag="{tag}"'
        signature_header = f'sig2=:{signature_b64}:'
        
        print(f"✅ Created Ed25519 signature")
        print(f"📤 Signature-Input: {signature_input_header}")
        print(f"🔒 Signature: {signature_header}")
        
        return signature_input_header, signature_header
        
    except Exception as e:
        print(f"❌ Error creating Ed25519 signature: {str(e)}")
        return "", ""

def parse_url_components(url: str) -> ty.Tuple[str, str]:
    """Parse URL to extract authority and path components for RFC 9421"""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        
        # Authority is the host (and port if not default)
        authority = parsed.netloc
        
        # Path includes the path and query parameters
        path = parsed.path
        if parsed.query:
            path += f"?{parsed.query}"
        
        print(f"🔍 Parsed URL: {url}")
        print(f"🌐 Authority: {authority}")
        print(f"📍 Path: {path}")
        
        return authority, path
    except Exception as e:
        print(f"❌ Error parsing URL: {str(e)}")
        return "", ""
