#!/bin/bash

# Generate RSA keys (optional - for RSA-PSS-SHA256)
openssl genrsa -out rsa_private.pem 2048
openssl rsa -in rsa_private.pem -pubout -out rsa_public.pem

# Generate Ed25519 keys (optional - for Ed25519)
openssl genpkey -algorithm Ed25519 -out ed25519_private.pem
openssl pkey -in ed25519_private.pem -pubout -out ed25519_public.pem

# Copy public keys to merchant-backend/
cp ed25519_public.pem rsa_public.pem merchant-backend/

# Copy public keys to agent-registry/
cp ed25519_public.pem rsa_public.pem agent-registry/

# Copy public and private keys to tap-agent/
cp ed25519_public.pem ed25519_private.pem rsa_public.pem rsa_private.pem tap-agent/

# Remove private keys from top-level directory
rm rsa_private.pem rsa_public.pem ed25519_private.pem ed25519_public.pem