export * from '../interface';

/**
 * Agent Registry Interface Definitions
 */

/**
 * Standard JSON Web Key interface (simplified/compatible with RFC 7517)
 */
export interface JWK {
    kty: string;
    kid?: string;
    use?: string;
    alg?: string;
    n?: string;
    e?: string;
    x?: string;
    y?: string;
    crv?: string;
    [key: string]: unknown;
}

/**
 * Extended Key object stored in Registry
 */
export interface RegistryKey extends JWK {
    kid: string; // kid is required for Registry keys
    agent_id: string;
    created_at: number;
    status: 'active' | 'revoked';
}

/**
 * Agent entity
 */
export interface Agent {
    id: string;
    name: string;
    domain: string;
    status: 'active' | 'inactive';
    created_at: number;
    updated_at: number;
}
