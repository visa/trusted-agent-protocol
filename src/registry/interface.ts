/**
 * Agent Registry Interface Definitions
 */

/**
 * Request DTO for registering a new Agent
 */
export interface RegisterAgentRequest {
    name: string;
    domain: string;
    jwk: JWK;
}

/**
 * Request DTO for adding a key
 */
export interface AddKeyRequest {
    jwk: JWK;
}

/**
 * Service Contract for the Registry
 */
export interface RegistryService {
    listAgents(): Promise<Agent[]>;
    getAgent(id: string): Promise<Agent | null>;
    getAgentByDomain(domain: string): Promise<Agent | null>;
    createAgent(req: RegisterAgentRequest): Promise<Agent>;
    updateAgent(id: string, updates: Partial<Pick<Agent, 'name' | 'status'>>): Promise<Agent>;
    deleteAgent(id: string): Promise<void>;

    addKey(agentId: string, req: AddKeyRequest): Promise<RegistryKey>;
    getKey(kid: string): Promise<RegistryKey | null>;
    getAgentKeys(agentId: string): Promise<RegistryKey[]>;
}

export class RegistryError extends Error {
    constructor(public code: string, message: string, public status: number = 500) {
        super(message);
        this.name = 'RegistryError';
    }
}
