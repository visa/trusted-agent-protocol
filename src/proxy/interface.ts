/**
 * Configuration for the CDN Proxy Service
 */
export interface ProxyConfig {
    /** Port to listen on */
    port: number;
    /** URL of the upstream Merchant Service */
    merchantUrl: string;
    /** URL of the Agent Registry Service */
    registryUrl: string;
    /** URL of the Authority Service */
    authorityUrl: string;
    /** Enable debug logging */
    debug?: boolean;
    /** TLS Options for HTTPS/mTLS */
    tls?: {
        /** Server certificate (PEM) */
        cert: string;
        /** Server private key (PEM) */
        key: string;
        /** Trusted CA certificates for client verification (PEM) */
        ca?: string;
    };
}

/**
 * Interface for the Proxy Service
 */
export interface ProxyService {
    /** Port the proxy is listening on */
    readonly port: number;

    /**
     * Starts the proxy server
     * @returns The server instance
     */
    start(): void;

    /**
     * Stops the proxy server
     */
    stop(): void;
}
