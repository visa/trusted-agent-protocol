import { generateKeyPairSync } from 'node:crypto';
import { createSignatureHeaders } from '@interledger/http-signature-utils';
import type { AgentConfig, IAgent } from './interface';
import forge from 'node-forge';

export class Agent implements IAgent {
    private config: AgentConfig;
    private keyId: string | null = null;
    private agentId: string | null = null;
    private keyPair: { publicKey: any; privateKey: any; publicJwk: any; privateJwk: any } | null = null;
    private certificate: string | null = null;

    constructor(config: AgentConfig) {
        this.config = config;
    }

    /**
     * Generates a new Key Pair (supports ed25519 and rsa)
     */
    public generateKey(keyId: string = 'primary-key', type: 'ed25519' | 'rsa' = 'ed25519') {
        if (this.config.debug) console.log(`[Agent] Generating ${type} key pair...`);

        let publicKey, privateKey;
        if (type === 'ed25519') {
            const keys = generateKeyPairSync('ed25519');
            publicKey = keys.publicKey;
            privateKey = keys.privateKey;
        } else {
            const keys = generateKeyPairSync('rsa', { modulusLength: 2048 });
            publicKey = keys.publicKey;
            privateKey = keys.privateKey;
        }

        const publicJwk = publicKey.export({ format: 'jwk' });
        const privateJwk = privateKey.export({ format: 'jwk' });

        // Add required metadata for TAP
        const alg = type === 'ed25519' ? 'EdDSA' : 'RS256';
        const kty = type === 'ed25519' ? 'OKP' : 'RSA';

        Object.assign(publicJwk, { kid: keyId, kty, alg, use: 'sig' });
        if (type === 'ed25519') Object.assign(publicJwk, { crv: 'Ed25519' });

        Object.assign(privateJwk, { kid: keyId, kty, alg, use: 'sig' });
        if (type === 'ed25519') Object.assign(privateJwk, { crv: 'Ed25519' });

        this.keyId = keyId;
        this.keyPair = { privateKey, publicKey, publicJwk, privateJwk };

        if (this.config.debug) console.log(`[Agent] Key generated. KeyID: ${keyId}`);
    }

    /**
     * Registers the agent and key with the Registry
     */
    public async register() {
        if (!this.keyPair) throw new Error("No keys generated. Call generateKey() first.");

        if (this.config.debug) console.log(`[Agent] Registering with ${this.config.registryUrl}...`);

        // 1. Create Agent
        const agentRes = await fetch(`${this.config.registryUrl}/agents`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: this.config.name,
                domain: this.config.domain || `https://${this.config.name.toLowerCase().replace(/\s+/g, '-')}.example.com`,
                jwk: this.keyPair.publicJwk
            })
        });

        if (!agentRes.ok) {
            const txt = await agentRes.text();
            throw new Error(`Registration failed: ${agentRes.status} ${txt}`);
        }

        const agentData = await agentRes.json() as any;
        this.agentId = agentData.id;
        if (this.config.debug) console.log(`[Agent] Registered. AgentID: ${this.agentId}`);
    }

    /**
     * Requests a certificate from the Registry Authority
     */
    public async requestCertificate() {
        if (!this.keyPair || !this.agentId) {
            throw new Error("Agent must be registered before requesting a certificate.");
        }

        if (this.config.debug) console.log(`[Agent] Requesting certificate for ${this.agentId}...`);

        // Generate CSR
        const csr = forge.pki.createCertificationRequest();

        // Convert node:crypto keys to forge keys for CSR generation
        // For simplicity, we'll use forge to generate a temporary key if needed or export/import
        // But since we have the private key, we can use forge to sign
        const privateKeyPem = this.keyPair.privateKey.export({ format: 'pem', type: 'pkcs8' });
        const publicKeyPem = this.keyPair.publicKey.export({ format: 'pem', type: 'spki' });

        const forgePrivateKey = forge.pki.privateKeyFromPem(privateKeyPem);
        const forgePublicKey = forge.pki.publicKeyFromPem(publicKeyPem);

        csr.publicKey = forgePublicKey;
        csr.setSubject([{
            name: 'commonName',
            value: this.agentId
        }]);

        csr.sign(forgePrivateKey);
        const csrPem = forge.pki.certificationRequestToPem(csr);

        const authUrl = this.config.authorityUrl || this.config.registryUrl;
        const res = await fetch(`${authUrl}/authority/sign`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                csr: csrPem,
                agentId: this.agentId
            })
        });

        if (!res.ok) {
            const txt = await res.text();
            throw new Error(`Certificate request failed: ${res.status} ${txt}`);
        }

        this.certificate = await res.text();
        if (this.config.debug) console.log(`[Agent] Certificate received.`);
    }

    /**
     * Makes a request to the Proxy using the configured authentication mode
     */
    public async fetch(path: string, options: RequestInit = {}) {
        const authMode = this.config.authMode || 'signature';
        const method = options.method || 'GET';
        const url = `${this.config.proxyUrl}${path}`;
        const urlObj = new URL(url);

        if (this.config.debug) console.log(`[Agent] Requesting via ${authMode}: ${method} ${url}...`);

        let headers: Record<string, string> = {
            host: urlObj.host,
            ...((options.headers as any) || {})
        };

        // Add Client-Cert header if available (RFC 9440)
        if (this.certificate) {
            // RFC 9440 expects the certificate to be base64 encoded DER, 
            // but often implementations just pass the PEM without the boundaries or the PEM itself.
            // We'll pass the PEM for simplicity as many proxies handle it.
            headers['client-cert'] = this.certificate
                .replace(/-----BEGIN CERTIFICATE-----/, '')
                .replace(/-----END CERTIFICATE-----/, '')
                .replace(/\s+/g, '');
        }

        const fetchOptions: any = {
            ...options,
            headers
        };

        // 1. Signature Auth
        if (authMode === 'signature') {
            if (!this.keyPair || !this.keyId) {
                throw new Error("Agent keys not generated. Necessary for signature auth.");
            }

            const requestToSign = {
                method,
                url,
                headers
            };

            const signedHeaders = await createSignatureHeaders({
                request: requestToSign,
                privateKey: this.keyPair.privateKey,
                keyId: this.keyId
            });

            fetchOptions.headers = {
                ...headers,
                ...signedHeaders
            };
        }

        // Apply TLS configuration (Bun specific)
        if (this.config.tls) {
            fetchOptions.tls = {
                cert: this.config.tls.cert,
                key: this.config.tls.key,
                ca: this.config.tls.ca,
                rejectUnauthorized: this.config.tls.rejectUnauthorized !== undefined
                    ? this.config.tls.rejectUnauthorized
                    : true
            };
        } else if (urlObj.protocol === 'https:') {
            // Default for HTTPS proxy without explicit TLS config
            fetchOptions.tls = { rejectUnauthorized: false };
        }

        return fetch(url, fetchOptions);
    }
}
