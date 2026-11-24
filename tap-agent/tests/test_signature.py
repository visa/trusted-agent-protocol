import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tap_signature import signature_input, signature_base, url_components


class SignatureTests(unittest.TestCase):
    def test_canonical_parameters(self):
        value = signature_input('agent', 'nonce', 100, 160, 'agent-browser-auth', 'ed25519')
        self.assertEqual(value, '("@authority" "@path");created=100;expires=160;keyid="agent";alg="ed25519";nonce="nonce";tag="agent-browser-auth"')
        self.assertEqual(signature_base('merchant.example', '/product/1', value),
                         f'"@authority": merchant.example\n"@path": /product/1\n"@signature-params": {value}')

    def test_parameter_escaping(self):
        value = signature_input('a"b', 'a\\b', 100, 160, 'agent-payer-auth', 'ed25519')
        self.assertIn('keyid="a\\"b"', value)
        self.assertIn('nonce="a\\\\b"', value)

    def test_invalid_parameters(self):
        for created, expires in [(True, 160), (100, 100), (100, 581), (-1, 100)]:
            with self.subTest(created=created, expires=expires), self.assertRaises(ValueError):
                signature_input('agent', 'nonce', created, expires, 'agent-browser-auth', 'ed25519')
        with self.assertRaises(ValueError):
            signature_input('agent', 'nonce\n', 100, 160, 'agent-browser-auth', 'ed25519')

    def test_url_components(self):
        cases = {
            'https://MERCHANT.example:443/product/1?q=a%2Fb': ('merchant.example', '/product/1'),
            'http://merchant.example:80': ('merchant.example', '/'),
            'http://merchant.example:3001/product/%2f': ('merchant.example:3001', '/product/%2f'),
            'https://[::1]:443/': ('[::1]', '/'),
        }
        for url, expected in cases.items():
            with self.subTest(url=url):
                self.assertEqual(url_components(url), expected)
        for url in ['file:///path', 'https://user:password@merchant.example/', '/product/1']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                url_components(url)


if __name__ == '__main__':
    unittest.main()
