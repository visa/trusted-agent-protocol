#!/usr/bin/env python3
# © 2025 Visa.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Sample script to populate the agent registry with initial data
"""

import requests
import json
import base64
from cryptography.hazmat.primitives import serialization

# Agent Registry Service URL
BASE_URL = "http://localhost:9002"

# Sample agent data with multiple keys
sample_agents = [
    {
        "name": "TAP Agent 1",
        "domain": "https://tapagent.com",
        "description": "Official Tap Agent 1 service for merchant verification",
        "contact_email": "support@tapagent.com",
        "is_active": "true",
        "keys": [
            {
                "key_id": "primary",
                "public_key": """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAx4rNYC4ChLr3xvR9K5a9
JGFksUYbVqB2XfVF6QHlU9W0vONUjunKo1V56WkJWxY/diolG0847NTj2y0ksnZv
18e/AuPex4blylGuRXSBOoxsTkN6szMeFB1vsrKqrDqCGxOP0cHeW6biCZbOhQpE
tjWVwEXsJMzbKIYwhx35UrD1RjfRCdsFP6ery/tBu0jnTN47pWQWBq200JXZRpSR
0MfPDeIdQzvTUrHnxIbfGdsBixHvZXnw8Fa3lG9ol5l9QYpi8MN3qoVM4rT4ANcW
FkVaOOsJYd863Bqy3X9vaIUpDqJS0HoOq8l8X26HGtX2LinFi7hcPGZWiznj03v2
ywIDAQAB
-----END PUBLIC KEY-----""",
                "algorithm": "RSA-SHA256",
                "description": "Primary signing key for Test Agent 1",
                "is_active": "true"
            },
            {
                "key_id": "backup-2024",
                "public_key": """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAt+SfMaqEpUwshjfJnQS2
/D0DrXTVfhUP37pcp/eAmGPL1oaYwq0Br3tMiCpHHiTBkt56E4M334DCD+v/umVI
rPMPf9bharUYFAWwJB9DWL6C7UAslnRHsTvjZ02ImStRV9scaTmynQrHQE/oNtiZ
wcVjaXgIGkHuuze1AZ54PrQOUb435CtsFZ74oQmo9t7kMXrFQ19CIWJOXZlxDvoq
YsJYxeRXdQ6c+Ckb7m7l01OCbZmhiLacThHUx62GaZ+uAKrw+9SQ352Wachl1uc9
8BfJYj2P0CuLcSeQt8Xk2aWktvK+cmnrsKIbiZYJ9DXBcU7ZH/jsw46izh58/2fe
TQIDAQAB
-----END PUBLIC KEY-----""",
                "algorithm": "RSA-SHA256",
                "description": "Backup signing key for disaster recovery",
                "is_active": "true"
            },
            {
                "key_id": "primary-ed25519",
                "public_key": "09Xvvs6I2LOkF0EFb3ofNai87g0mWipuEMwVdi78m6E=",
                "algorithm": "ed25519",
                "description": "Primary Ed25519 signing key for modern crypto",
                "is_active": "true"
            }
        ]
    },
    {
        "name": "TAP Agent 2",
        "domain": "https://tapagent2.com",
        "description": "Official TAP Agent 2 service for merchant verification",
        "contact_email": "support@tapagent2.com",
        "is_active": "true",
        "keys": [
            {
                "key_id": "primary",
                "public_key": """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAzQ4ERbP6IED3/GiRs2+h
pvHLKTtXdi+hHkgbVIkTBB2bICzkRX1hRo3/UqWkloVEyqyaMSdnXEzuvcKw/Tec
Q6tx321jKH3X9kcDzrtAHtNVg9CbR6cjBc1gRETW+yyFiGX1X7Jbp+o2/lWXJZvf
M5WuQ1mR2x+LOin2V2UyeSyFjNU3hd1a2ceD7qwPnpDOyCGXQHin9ioh/KHkn6vf
IUAhs5j3rS3lJzqdgn9P+wO31cmAJjKbhHQO8+1Ygw+4Qx0L4HL2y+7mJyzJC4Dv
MC6/FhKmTVggXKkI+Q5/D1hOiBDtAeQ/AmmB3+HFF5Q67atxhMss1qXLWJeZC0iW
swIDAQAB
-----END PUBLIC KEY-----""",
                "algorithm": "RSA-SHA256",
                "description": "Primary signing key for TAP Agent 2",
                "is_active": "true"
            }
        ]
    }
]

def make_agent_from_PEM_files():
    with open("ed25519_public.pem", "rb") as f:
        ed25519_public_key= serialization.load_pem_public_key(f.read())
        ed25519_public_key_b64 = base64.b64encode(ed25519_public_key.public_bytes_raw()).decode("utf-8")
    rsa_public_key = open("rsa_public.pem", "r").read()
    return {
        "name": "My TAP Agent",
        "domain": "https://tapagent.com",
        "description": "Official Tap Agent 1 service for merchant verification",
        "contact_email": "support@tapagent.com",
        "is_active": "true",
        "keys": [
            {
                "key_id": "primary",
                "public_key": rsa_public_key,
                "algorithm": "RSA-SHA256",
                "description": "Primary signing key for Test Agent 1",
                "is_active": "true"
            },
            {
                "key_id": "primary-ed25519",
                "public_key": ed25519_public_key_b64,
                "algorithm": "ed25519",
                "description": "Primary Ed25519 signing key for modern crypto",
                "is_active": "true"
            }
        ]
    }

def register_agent(agent_data):
    """Register a single agent"""
    try:
        response = requests.post(f"{BASE_URL}/agents/register", json=agent_data)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Successfully registered: {agent_data['name']}")
            print(f"   Domain: {agent_data['domain']}")
            print(f"   Message: {result['message']}")
        else:
            print(f"❌ Failed to register {agent_data['name']}: {response.status_code}")
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Error registering {agent_data['name']}: {str(e)}")
    print()

def main():
    """Register all sample agents"""
    print("🚀 Populating Agent Registry with sample data...")
    print(f"📡 Agent Registry URL: {BASE_URL}")
    print()
    
    # Check if service is running
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code != 200:
            print("❌ Agent Registry Service is not responding correctly")
            return
    except Exception as e:
        print(f"❌ Cannot connect to Agent Registry Service: {str(e)}")
        print("   Make sure the service is running on port 9000")
        return
    
    print("✅ Agent Registry Service is running")
    print()
    
    # Register each agent
    for agent in sample_agents:
        register_agent(agent)
    # Register the agent from the PEM files
    register_agent(make_agent_from_PEM_files())

    
    print("🏁 Sample data population completed!")
    
    # List all registered agents
    try:
        response = requests.get(f"{BASE_URL}/agents")
        if response.status_code == 200:
            agents = response.json()
            print(f"📋 Total registered agents: {len(agents)}")
            for agent in agents:
                print(f"   - {agent['name']} (ID: {agent['id']}, Domain: {agent['domain']})")
                print(f"     Keys: {len(agent.get('keys', []))}")
                for key in agent.get('keys', []):
                    print(f"       * {key['key_id']} ({key['algorithm']}) - {key['description']}")
        else:
            print("❌ Failed to retrieve agent list")
    except Exception as e:
        print(f"❌ Error retrieving agents: {str(e)}")

    print()
    print("🔍 Testing agent lookup by ID...")
    
    # Test agent lookup by ID
    try:
        response = requests.get(f"{BASE_URL}/agents")
        if response.status_code == 200:
            agents = response.json()
            if agents:
                test_agent = agents[0]
                agent_id = test_agent['id']
                
                print(f"Testing lookup for agent ID: {agent_id}")
                response = requests.get(f"{BASE_URL}/agents/{agent_id}")
                if response.status_code == 200:
                    agent_info = response.json()
                    print(f"✅ Successfully retrieved agent: {agent_info['name']}")
                    
                    # Test key lookup
                    if agent_info.get('keys'):
                        key_id = agent_info['keys'][0]['key_id']
                        print(f"Testing key lookup for key ID: {key_id}")
                        response = requests.get(f"{BASE_URL}/agents/{agent_id}/keys/{key_id}")
                        if response.status_code == 200:
                            key_info = response.json()
                            print(f"✅ Successfully retrieved key: {key_info['key_id']}")
                        else:
                            print(f"❌ Failed to retrieve key: {response.status_code}")
                else:
                    print(f"❌ Failed to retrieve agent: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing lookups: {str(e)}")

if __name__ == "__main__":
    main()
