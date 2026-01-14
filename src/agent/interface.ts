export interface AgentConfig {
    /** Name of the agent */
    name: string;
    /** URL of the Agent Registry */
    registryUrl: string;
    /** URL of the Authority Service */
    authorityUrl?: string;
    /** URL of the CDN Proxy */
    proxyUrl: string;
    /** Enable debug logging */
    debug?: boolean;
    /** Domain reported by the agent (must be unique in registry) */
    domain?: string;
    /** Authentication mode: 'mTLS' or 'signature' (default) */
    authMode?: 'mTLS' | 'signature';
    /** TLS configuration for mTLS or HTTPS proxy */
    tls?: {
        cert?: string;
        key?: string;
        ca?: string;
        /** For testing: allow self-signed certs */
        rejectUnauthorized?: boolean;
    };
}

export interface IAgent {
    /** Generates a new identity key pair */
    generateKey(keyId?: string, type?: 'ed25519' | 'rsa'): void;
    /** Registers the agent with the registry */
    register(): Promise<void>;
    /** Requests a certificate from the authority */
    requestCertificate(): Promise<void>;
    /** Makes an authenticated request to the proxy */
    fetch(path: string, options?: RequestInit): Promise<Response>;
}
