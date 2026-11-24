"""Exercise the sample's actual signing functions without starting Streamlit."""
import ast
import base64
import contextlib
import io
import json
from pathlib import Path
import sys

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, padding, rsa

agent_dir = Path(__file__).resolve().parents[2] / 'tap-agent'
sys.path.insert(0, str(agent_dir))
from tap_signature import signature_input, signature_base

algorithm, created = sys.argv[1], int(sys.argv[2])
private = (ed25519.Ed25519PrivateKey.generate() if algorithm == 'ed25519'
           else rsa.generate_private_key(public_exponent=65537, key_size=2048))
public = private.public_key()
if algorithm == 'ed25519':
    raw = private.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
                                serialization.NoEncryption())
    public_value = base64.b64encode(public.public_bytes(serialization.Encoding.Raw,
                                   serialization.PublicFormat.Raw)).decode()
else:
    public_value = public.public_bytes(serialization.Encoding.PEM,
                                      serialization.PublicFormat.SubjectPublicKeyInfo).decode()


class UI:
    def error(self, message):
        raise RuntimeError(message)


namespace = {
    'base64': base64, 'serialization': serialization, 'hashes': hashes,
    'padding': padding, 'default_backend': default_backend, 'st': UI(),
    '_signature_input': signature_input, '_signature_base': signature_base,
    'get_ed25519_keys_from_env': lambda: (base64.b64encode(raw).decode(), public_value),
}
tree = ast.parse((agent_dir / 'agent_app.py').read_text())
functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and
             node.name in ('create_http_message_signature', 'create_ed25519_signature')]
exec(compile(ast.Module(body=functions, type_ignores=[]), 'agent_app.py', 'exec'), namespace)
name = ('create_ed25519_signature' if algorithm == 'ed25519'
        else 'create_http_message_signature')
pem = ('' if algorithm == 'ed25519' else private.private_bytes(serialization.Encoding.PEM,
       serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode())
with contextlib.redirect_stdout(io.StringIO()):
    input_header, signature_header = namespace[name](pem, 'merchant.example', '/product/1',
        'python-agent', 'python-signer-nonce', created, created + 60, 'agent-browser-auth')
print(json.dumps({'headers': {'signature-input': input_header, 'signature': signature_header},
                 'key': {'key_id': 'python-agent', 'public_key': public_value,
                         'is_active': 'true', 'algorithm': algorithm}}))
