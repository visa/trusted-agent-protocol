"""Check the actual Ed25519 signing function without starting the Streamlit UI."""
import ast
import base64
import contextlib
import io
from pathlib import Path
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


class KeyLoggingTests(unittest.TestCase):
    def test_signing_does_not_log_private_key_material(self):
        private = ed25519.Ed25519PrivateKey.generate()
        private_value = base64.b64encode(private.private_bytes(serialization.Encoding.Raw,
            serialization.PrivateFormat.Raw, serialization.NoEncryption())).decode()
        public_value = base64.b64encode(private.public_key().public_bytes(serialization.Encoding.Raw,
            serialization.PublicFormat.Raw)).decode()

        class UI:
            def error(self, message):
                raise AssertionError(message)

        namespace = {'base64': base64, 'st': UI(),
                     'get_ed25519_keys_from_env': lambda: (private_value, public_value)}
        # The canonical helper is available when this PR is combined with the verifier fix.
        agent_dir = Path(__file__).resolve().parents[1]
        if (agent_dir / 'tap_signature.py').exists():
            import sys
            sys.path.insert(0, str(agent_dir))
            from tap_signature import signature_input, signature_base
            namespace.update(_signature_input=signature_input, _signature_base=signature_base)
        source = ast.parse((agent_dir / 'agent_app.py').read_text())
        functions = [node for node in source.body if isinstance(node, ast.FunctionDef)
                     and node.name == 'create_ed25519_signature']
        exec(compile(ast.Module(body=functions, type_ignores=[]), 'agent_app.py', 'exec'), namespace)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            input_header, signature_header = namespace['create_ed25519_signature'](
                '', 'merchant.example', '/product/1', 'test-key', 'test-nonce',
                100, 160, 'agent-browser-auth')
        self.assertNotIn(private_value, output.getvalue())
        self.assertNotIn(private_value[:20], output.getvalue())
        # Signing must still work, independently of whether the signature format PR is merged.
        parameters = input_header.split('=', 1)[1]
        base = f'"@authority": merchant.example\n"@path": /product/1\n"@signature-params": {parameters}'
        signature = base64.b64decode(signature_header.split(':')[1])
        private.public_key().verify(signature, base.encode())


if __name__ == '__main__':
    unittest.main()
